from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import csv
import hashlib
import json
import sqlite3

from config import DATABASE_PATH
from core.backup import backup_db
from core.models import Employee
from core.banking import validate_account_state,payment_details
from core.validation import CENT, employee_values, hours_map, number, iso_date
from services.payroll_service import calculate_payroll

SCHEMA_VERSION = 6


class PayrollConflictError(ValueError):
    pass


class Database:
    def __init__(self, path=None, *, create_backup=True):
        self.path = str(path if path is not None else DATABASE_PATH)
        exists = self.path != ':memory:' and Path(self.path).exists()
        self.conn = sqlite3.connect(self.path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self._depth = 0
        try:
            version = self.conn.execute('PRAGMA user_version').fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError('This database was created by a newer PayrollSystem version')
            if exists and (create_backup or version < SCHEMA_VERSION):
                self.conn.close()
                self.last_backup = backup_db(Path(self.path))
                self.conn = sqlite3.connect(self.path, timeout=30)
                self.conn.row_factory = sqlite3.Row
                self.cur = self.conn.cursor()
            else:
                self.last_backup = None
            self.conn.execute('PRAGMA foreign_keys=ON')
            self._init_db()
        except Exception:
            self.conn.close()
            raise

    @contextmanager
    def transaction(self):
        """Nested callers share one transaction; any error rolls back the unit."""
        outer = self._depth == 0
        if outer:
            self.conn.execute('BEGIN IMMEDIATE')
        self._depth += 1
        try:
            yield
            if outer:
                self.conn.commit()
        except Exception:
            if outer:
                self.conn.rollback()
            raise
        finally:
            self._depth -= 1

    def _columns(self, table):
        return {r['name'] for r in self.conn.execute(f'PRAGMA table_info({table})')}

    def _init_db(self):
        with self.transaction():
            self.conn.execute('''CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                rate REAL NOT NULL CHECK(rate>0), bank TEXT, iban TEXT, bic TEXT,
                archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1)))''')
            columns = self._columns('employees')
            if 'bank' not in columns:
                self.conn.execute('ALTER TABLE employees ADD COLUMN bank TEXT')
            if 'bank_name' in columns and self.conn.execute('PRAGMA user_version').fetchone()[0] < 2:
                self.conn.execute("UPDATE employees SET bank=bank_name WHERE (bank IS NULL OR bank='') AND bank_name IS NOT NULL")
            if 'archived' not in columns:
                self.conn.execute('ALTER TABLE employees ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
            if 'bank_account_state' not in self._columns('employees'):
                self.conn.execute("ALTER TABLE employees ADD COLUMN bank_account_state TEXT NOT NULL DEFAULT 'unknown' CHECK(bank_account_state IN ('unknown','yes','no'))")
                self.conn.execute("UPDATE employees SET bank_account_state='yes' WHERE TRIM(COALESCE(iban,''))<>''")
            self.conn.execute('''CREATE TABLE IF NOT EXISTS work_hours (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                work_date TEXT NOT NULL, hours REAL NOT NULL CHECK(hours>=0 AND hours<=24),
                rate REAL CHECK(rate>0), UNIQUE(employee_id,work_date))''')
            if 'rate' not in self._columns('work_hours'):
                self.conn.execute('ALTER TABLE work_hours ADD COLUMN rate REAL')
            # Retain NULL for legacy rates; today's card cannot establish past pay.
            if self._columns('daily_hours'):
                from services.report_service import _date
                for old in self.conn.execute('SELECT employee_id,work_date,hours FROM daily_hours').fetchall():
                    try:
                        self.get_employee(old['employee_id'])
                        day = _date(old['work_date']).isoformat()
                        h = float(number(old['hours'],'Legacy hours',maximum=24))
                        existing = self.conn.execute('SELECT hours FROM work_hours WHERE employee_id=? AND work_date=?',
                                                     (old['employee_id'],day)).fetchone()
                        if existing is not None and Decimal(str(existing['hours'])) != Decimal(str(h)):
                            raise ValueError('Conflicting legacy and current hours')
                        self.conn.execute('''INSERT INTO work_hours(employee_id,work_date,hours) VALUES(?,?,?)
                            ON CONFLICT(employee_id,work_date) DO NOTHING''',(old['employee_id'],day,h))
                    except ValueError as exc:
                        raise RuntimeError('Legacy hours could not be migrated safely; original database was backed up') from exc
                self.conn.execute('DROP TABLE daily_hours')
            # Early releases created unused tables with the same names but a
            # different shape. CREATE IF NOT EXISTS cannot upgrade those tables.
            required_payroll = {'id','employee_id','name','rate','rate_mode','period_from','period_to',
                                'created_at','bank','iban','bic','utilities','rental','total_hours',
                                'gross_amount','net_amount','pdf_path','fingerprint'}
            required_days = {'payroll_id','work_date','hours','rate','amount'}
            old_payroll = self._columns('payrolls')
            old_days = self._columns('payroll_days')
            incompatible = ((old_payroll and not required_payroll.issubset(old_payroll)) or
                            (old_days and not required_days.issubset(old_days)))
            if incompatible:
                counts = [self.conn.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
                          for name, cols in [('payrolls',old_payroll),('payroll_days',old_days)] if cols]
                if any(counts):
                    raise RuntimeError('Legacy payroll history contains records in an unsupported schema. '
                                       'Migration stopped without changing data; a backup was created. '
                                       'A separate history migration is required.')
                self.conn.execute('DROP TABLE IF EXISTS payroll_days')
                self.conn.execute('DROP TABLE IF EXISTS payrolls')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS payrolls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL REFERENCES employees(id),
                name TEXT NOT NULL, rate REAL NOT NULL, rate_mode TEXT NOT NULL,
                period_from TEXT NOT NULL, period_to TEXT NOT NULL,
                created_at TEXT NOT NULL, bank TEXT, iban TEXT, bic TEXT,
                utilities REAL NOT NULL, rental REAL NOT NULL,
                total_hours REAL NOT NULL, gross_amount REAL NOT NULL, net_amount REAL NOT NULL,
                pdf_path TEXT, fingerprint TEXT NOT NULL UNIQUE)''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS payroll_days (
                payroll_id INTEGER NOT NULL REFERENCES payrolls(id),
                work_date TEXT NOT NULL, hours REAL NOT NULL, rate REAL NOT NULL,
                amount REAL NOT NULL, PRIMARY KEY(payroll_id,work_date))''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS hour_day_rules (
                employee_id INTEGER NOT NULL REFERENCES employees(id), work_date TEXT NOT NULL,
                locked INTEGER NOT NULL CHECK(locked IN (0,1)), excluded INTEGER NOT NULL CHECK(excluded IN (0,1)),
                CHECK(NOT (locked=1 AND excluded=1)), PRIMARY KEY(employee_id,work_date))''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS distribution_settings (
                employee_id INTEGER PRIMARY KEY REFERENCES employees(id),
                min_hours INTEGER NOT NULL CHECK(min_hours>=0 AND min_hours<=24),
                max_hours INTEGER NOT NULL CHECK(max_hours>=min_hours AND max_hours<=24))''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS payroll_revision_links (
                payroll_id INTEGER NOT NULL REFERENCES payrolls(id),
                replaces_id INTEGER NOT NULL UNIQUE REFERENCES payrolls(id),
                CHECK(payroll_id>replaces_id), PRIMARY KEY(payroll_id,replaces_id))''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS payroll_content_keys (
                payroll_id INTEGER PRIMARY KEY REFERENCES payrolls(id), content_hash TEXT NOT NULL)''')
            self.conn.execute('''INSERT INTO payroll_content_keys(payroll_id,content_hash)
                SELECT p.id,p.fingerprint FROM payrolls p WHERE NOT EXISTS
                (SELECT 1 FROM payroll_content_keys k WHERE k.payroll_id=p.id)''')
            self.conn.execute(f'PRAGMA user_version={SCHEMA_VERSION}')

    def get_employees(self, include_archived=False):
        query = 'SELECT * FROM employees'
        if not include_archived:
            query += ' WHERE archived=0'
        return self.conn.execute(query + ' ORDER BY name,id').fetchall()

    def get_employee(self, emp_id):
        row = self.conn.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
        if row is None:
            raise ValueError('Employee not found')
        return row

    def add_employee(self, name, rate, bank=None, iban=None, bic=None,*,bank_account_state=None):
        name, rate = employee_values(name, rate)
        state=validate_account_state(bank_account_state if bank_account_state is not None else ('yes' if str(iban or '').strip() else 'unknown'))
        with self.transaction():
            cur = self.conn.execute('INSERT INTO employees(name,rate,bank,iban,bic,bank_account_state) VALUES(?,?,?,?,?,?)',
                                    (name, rate, bank, iban, bic,state))
            return cur.lastrowid

    def update_employee(self, emp_id, name, rate, bank=None, iban=None, bic=None,*,expected=None,bank_account_state=None):
        name, rate = employee_values(name, rate)
        with self.transaction():
            current=self.get_employee(emp_id)
            if expected is not None and (current['archived'] or any(current[key]!=expected.get(key) for key in ('name','rate','bank','iban','bic','bank_account_state'))):
                raise ValueError('Employee details changed after this form was loaded. Clear and select the employee again before updating.')
            state=current['bank_account_state'] if bank_account_state is None else validate_account_state(bank_account_state)
            if bank_account_state is None and state=='unknown' and not str(current['iban'] or '').strip() and str(iban or '').strip():state='yes'
            self.conn.execute('UPDATE employees SET name=?,rate=?,bank=?,iban=?,bic=?,bank_account_state=? WHERE id=?',
                              (name, rate, bank, iban, bic,state,emp_id))

    def delete_employee(self, emp_id):
        # Keep financial and timesheet history intact.
        with self.transaction():
            self.conn.execute('UPDATE employees SET archived=1 WHERE id=?', (emp_id,))

    def update_employee_name(self, emp_id, name):
        e = self.get_employee(emp_id)
        self.update_employee(emp_id, name, e['rate'], e['bank'], e['iban'], e['bic'])

    def update_employee_rate(self, emp_id, rate):
        e = self.get_employee(emp_id)
        self.update_employee(emp_id, e['name'], rate, e['bank'], e['iban'], e['bic'])

    def update_employee_bank(self, emp_id, has_bank, bank_name, iban, bic):
        e = self.get_employee(emp_id)
        self.update_employee(emp_id, e['name'], e['rate'], bank_name if has_bank else None,
                             iban if has_bank else None, bic if has_bank else None,bank_account_state='yes' if has_bank else 'no')

    def load_hours(self, emp_id, start, end):
        iso_date(start); iso_date(end)
        return self.conn.execute('''SELECT work_date,hours,rate FROM work_hours
            WHERE employee_id=? AND work_date BETWEEN ? AND ? ORDER BY work_date''',
                                 (emp_id, start, end)).fetchall()

    def save_hours(self, emp_id, date, hours, rate=None):
        self.save_hours_batch(emp_id, {date: hours}, rate=rate)

    def save_hours_batch(self, emp_id, values, rate=None):
        values = hours_map(values)
        if rate is not None:
            rate = float(number(rate, 'Hourly rate', minimum=Decimal('0.01')))
        with self.transaction():
            e = self.get_employee(emp_id)
            if e['archived']:
                raise ValueError('Employee is archived')
            excluded={r['work_date'] for r in self.conn.execute('SELECT work_date FROM hour_day_rules WHERE employee_id=? AND excluded=1',(emp_id,))}
            if any(d in excluded and h!=0 for d,h in values.items()):
                raise ValueError('Include excluded dates before saving non-zero hours for them')
            self.conn.executemany('''INSERT INTO work_hours(employee_id,work_date,hours,rate)
                VALUES(?,?,?,?) ON CONFLICT(employee_id,work_date)
                DO UPDATE SET hours=excluded.hours,rate=excluded.rate''',
                [(emp_id, day, h, rate) for day, h in values.items()])

    def load_day_rules(self,emp_id,start,end):
        iso_date(start);iso_date(end)
        return {r['work_date']:{'locked':bool(r['locked']),'excluded':bool(r['excluded'])}
                for r in self.conn.execute('SELECT * FROM hour_day_rules WHERE employee_id=? AND work_date BETWEEN ? AND ?',
                                            (emp_id,start,end))}

    def load_distribution_settings(self,emp_id):
        row=self.conn.execute('SELECT min_hours,max_hours FROM distribution_settings WHERE employee_id=?',(emp_id,)).fetchone()
        return (row['min_hours'],row['max_hours']) if row else (0,24)

    def save_period_hours(self,emp_id,values,day_rules,settings,rate=None):
        values=hours_map(values)
        checked={}
        for day,rule in day_rules.items():
            iso_date(day)
            if day not in values or set(rule)!={'locked','excluded'} or any(type(v) is not bool for v in rule.values()):
                raise ValueError('Day rules must use boolean flags for dates in the saved hours')
            if rule['locked'] and rule['excluded']:
                raise ValueError('A date cannot be both locked and excluded')
            if rule['excluded'] and values[day]!=0:
                raise ValueError('Excluded dates must have zero hours')
            if rule['locked'] or rule['excluded']: checked[day]=rule
        lo,hi=[number(v,'Daily range',maximum=24) for v in settings]
        if lo!=lo.to_integral_value() or hi!=hi.to_integral_value() or lo>hi:
            raise ValueError('Daily range must use whole numbers with Min <= Max')
        with self.transaction():
            self.conn.executemany('DELETE FROM hour_day_rules WHERE employee_id=? AND work_date=?',[(emp_id,d) for d in values])
            self.conn.executemany('INSERT INTO hour_day_rules(employee_id,work_date,locked,excluded) VALUES(?,?,?,?)',
                [(emp_id,d,int(r['locked']),int(r['excluded'])) for d,r in checked.items()])
            self.save_hours_batch(emp_id,values,rate=rate)
            self.conn.execute('''INSERT INTO distribution_settings(employee_id,min_hours,max_hours) VALUES(?,?,?)
                ON CONFLICT(employee_id) DO UPDATE SET min_hours=excluded.min_hours,max_hours=excluded.max_hours''',
                (emp_id,int(lo),int(hi)))

    def payroll_save_plan(self,emp_id,values,rate_mode,start,end,utilities=0,rental=0):
        self._prepare_payroll(emp_id,values,rate_mode,start,end,utilities,rental)
        current=self.get_payrolls(current_only=True)
        exact=[p for p in current if p['employee_id']==emp_id and p['period_from']==start and p['period_to']==end]
        overlaps=[p for p in current if p['employee_id']==emp_id and p['period_from']<=end and p['period_to']>=start
                  and not(p['period_from']==start and p['period_to']==end)]
        return {'exact':exact,'overlaps':overlaps}

    def _prepare_payroll(self,emp_id,values,rate_mode,start,end,utilities,rental):
        iso_date(start); iso_date(end)
        values = hours_map(values)
        if start > end or not values or any(not start <= d <= end for d in values):
            raise ValueError('Hours must belong to the selected non-empty period')
        e=self.get_employee(emp_id)
        if e['archived']: raise ValueError('Employee is archived')
        rows,summary=calculate_payroll(Employee.from_row(e),values,rate_mode,utilities=utilities,housing=rental)
        rate=rows[0].rate
        details=payment_details(e)
        snapshot=dict(employee_id=emp_id,name=e['name'],rate=rate,rate_mode=rate_mode,
            period_from=start,period_to=end,**details,
            utilities=summary.utilities_deduction,rental=summary.housing_deduction,
            total_hours=summary.total_hours,gross_amount=summary.gross_amount,net_amount=summary.net_amount)
        key=hashlib.sha256(json.dumps([snapshot,sorted(values.items())],sort_keys=True).encode()).hexdigest()
        return values,rows,snapshot,key

    def save_payroll(self, emp_id, values, rate_mode, start, end, utilities=0, rental=0, pdf_path=None, *, day_rules=None,
                     distribution_settings=(0,24),replaces_ids=(),allow_overlap=False,expected_current_ids=None):
        with self.transaction():
            values,rows,snapshot,content_hash=self._prepare_payroll(emp_id,values,rate_mode,start,end,utilities,rental)
            plan=self.payroll_save_plan(emp_id,values,rate_mode,start,end,utilities,rental)
            current_ids={p['id'] for p in plan['exact']}
            replaces_ids=set(replaces_ids)
            if expected_current_ids is not None and set(expected_current_ids)!=current_ids:
                raise PayrollConflictError('Payroll history changed. Review the current statements and try again.')
            existing=None
            if replaces_ids:
                if replaces_ids!=current_ids:
                    raise PayrollConflictError('A correction must replace all current statements for this employee and exact period.')
            elif current_ids:
                if len(current_ids)==1:
                    candidate=next(iter(current_ids))
                    key=self.conn.execute('SELECT content_hash FROM payroll_content_keys WHERE payroll_id=?',(candidate,)).fetchone()[0]
                    if key==content_hash: existing=candidate
                if existing is None:
                    raise PayrollConflictError('A statement already exists for this period. Open it or explicitly create a corrected version in Payroll.')
            if plan['overlaps'] and not allow_overlap:
                raise PayrollConflictError('This period overlaps another current statement. Review and explicitly confirm the overlap in Payroll.')
            rate=rows[0].rate
            if day_rules is None:
                self.save_hours_batch(emp_id, values, rate=rate)
            else:
                self.save_period_hours(emp_id,values,day_rules,distribution_settings,rate=rate)
            if existing is not None: return existing
            fingerprint=hashlib.sha256(json.dumps([content_hash,sorted(replaces_ids)]).encode()).hexdigest() if replaces_ids else content_hash
            snapshot.update(created_at=datetime.now().isoformat(timespec='seconds'), pdf_path=pdf_path, fingerprint=fingerprint)
            columns = ','.join(snapshot)
            marks = ','.join('?' for _ in snapshot)
            cur = self.conn.execute(f'INSERT INTO payrolls({columns}) VALUES({marks})', tuple(snapshot.values()))
            payroll_id = cur.lastrowid
            self.conn.execute('INSERT INTO payroll_content_keys(payroll_id,content_hash) VALUES(?,?)',(payroll_id,content_hash))
            self.conn.executemany('INSERT INTO payroll_revision_links(payroll_id,replaces_id) VALUES(?,?)',[(payroll_id,pid) for pid in replaces_ids])
            self.conn.executemany('INSERT INTO payroll_days(payroll_id,work_date,hours,rate,amount) VALUES(?,?,?,?,?)',
                                 [(payroll_id,r.date,r.hours,r.rate,r.amount) for r in rows])
            return payroll_id

    def get_payrolls(self,current_only=False):
        query='''SELECT p.*,
            (SELECT GROUP_CONCAT(replaces_id, ', ') FROM payroll_revision_links WHERE payroll_id=p.id) AS corrects,
            (SELECT payroll_id FROM payroll_revision_links WHERE replaces_id=p.id) AS superseded_by
            FROM payrolls p'''
        if current_only: query+=' WHERE NOT EXISTS(SELECT 1 FROM payroll_revision_links l WHERE l.replaces_id=p.id)'
        return self.conn.execute(query+' ORDER BY p.id DESC').fetchall()

    def get_month_summary(self,year,month):
        from calendar import monthrange
        from datetime import date
        first=date(year,month,1).isoformat();last=date(year,month,monthrange(year,month)[1]).isoformat()
        current=self.get_payrolls(current_only=True)
        selected=[p for p in current if first<=p['period_to']<=last]
        groups={}
        for p in current:
            groups.setdefault((p['employee_id'],p['period_from'],p['period_to']),[]).append(p)
        ambiguous={p['id'] for g in groups.values() if len(g)>1 for p in g}
        employees={}
        def employee(eid):
            if eid not in employees:
                e=self.get_employee(eid)
                employees[eid]={'employee_id':eid,'name':e['name'],'hours':Decimal(0),'gross':Decimal(0),
                    'deductions':Decimal(0),'net':Decimal(0),'draft_hours':Decimal(0),'draft_days':0,'payroll_ids':[],'review_ids':[]}
            return employees[eid]
        included=[];review=[];overlaps=[]
        for p in selected:
            e=employee(p['employee_id'])
            if p['id'] in ambiguous:
                review.append(p['id']);e['review_ids'].append(p['id']);continue
            included.append(p['id']);e['payroll_ids'].append(p['id'])
            for key,column in [('hours','total_hours'),('gross','gross_amount'),('net','net_amount')]:
                e[key]+=Decimal(str(p[column]))
            e['deductions']+=Decimal(str(p['utilities']))+Decimal(str(p['rental']))
            if any(q['id']!=p['id'] and q['employee_id']==p['employee_id'] and q['period_from']<=p['period_to'] and q['period_to']>=p['period_from'] for q in current):
                overlaps.append(p['id'])
        issued={}
        for r in self.conn.execute('''SELECT p.employee_id,d.work_date,d.hours FROM payroll_days d JOIN payrolls p ON p.id=d.payroll_id
                WHERE NOT EXISTS(SELECT 1 FROM payroll_revision_links l WHERE l.replaces_id=p.id)'''):
            issued.setdefault((r['employee_id'],r['work_date']),set()).add(Decimal(str(r['hours'])))
        for w in self.conn.execute('SELECT employee_id,work_date,hours FROM work_hours WHERE work_date BETWEEN ? AND ?',(first,last)):
            if Decimal(str(w['hours'])) not in issued.get((w['employee_id'],w['work_date']),set()):
                e=employee(w['employee_id']);e['draft_hours']+=Decimal(str(w['hours']));e['draft_days']+=1
        totals={key:sum((e[key] for e in employees.values()),Decimal(0)) for key in ('hours','gross','deductions','net','draft_hours')}
        return {'rows':sorted(employees.values(),key=lambda e:(e['name'],e['employee_id'])), 'totals':totals,
                'included_ids':included,'review_ids':review,'overlap_ids':overlaps,'month':f'{year:04d}-{month:02d}'}

    def get_payroll_full(self, payroll_id):
        p = self.conn.execute('SELECT * FROM payrolls WHERE id=?', (payroll_id,)).fetchone()
        if p is None:
            raise ValueError('Payroll not found')
        days = self.conn.execute('SELECT * FROM payroll_days WHERE payroll_id=? ORDER BY work_date', (payroll_id,)).fetchall()
        return p, days

    def get_all_hours(self):
        return self.conn.execute('''SELECT e.id AS employee_id,e.name AS employee_name,
            w.work_date,w.hours,w.rate FROM work_hours w JOIN employees e ON e.id=w.employee_id
            ORDER BY w.work_date DESC,e.name,e.id''').fetchall()

    def export_hours_to_csv(self, filepath):
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['Employee ID','Employee','Date','Hours','Applied rate (EUR/h)','Gross amount (EUR)'])
            for row in self.get_all_hours():
                name = row['employee_name']
                if name.lstrip().startswith(('=','+','-','@')):
                    name = "'" + name
                rate = row['rate']
                amount = '' if rate is None else str((Decimal(str(row['hours']))*Decimal(str(rate))).quantize(CENT, rounding=ROUND_HALF_UP))
                writer.writerow([row['employee_id'],name,row['work_date'],row['hours'],'' if rate is None else rate,amount])
        return filepath

    def close(self):
        self.conn.close()
