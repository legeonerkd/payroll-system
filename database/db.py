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
from core.validation import CENT, employee_values, hours_map, number, iso_date
from services.payroll_service import calculate_payroll

SCHEMA_VERSION = 2


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
            if 'bank_name' in columns and self.conn.execute('PRAGMA user_version').fetchone()[0] < SCHEMA_VERSION:
                self.conn.execute("UPDATE employees SET bank=bank_name WHERE (bank IS NULL OR bank='') AND bank_name IS NOT NULL")
            if 'archived' not in columns:
                self.conn.execute('ALTER TABLE employees ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
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

    def add_employee(self, name, rate, bank=None, iban=None, bic=None):
        name, rate = employee_values(name, rate)
        with self.transaction():
            cur = self.conn.execute('INSERT INTO employees(name,rate,bank,iban,bic) VALUES(?,?,?,?,?)',
                                    (name, rate, bank, iban, bic))
            return cur.lastrowid

    def update_employee(self, emp_id, name, rate, bank=None, iban=None, bic=None):
        name, rate = employee_values(name, rate)
        with self.transaction():
            self.get_employee(emp_id)
            self.conn.execute('UPDATE employees SET name=?,rate=?,bank=?,iban=?,bic=? WHERE id=?',
                              (name, rate, bank, iban, bic, emp_id))

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
                             iban if has_bank else None, bic if has_bank else None)

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
            self.conn.executemany('''INSERT INTO work_hours(employee_id,work_date,hours,rate)
                VALUES(?,?,?,?) ON CONFLICT(employee_id,work_date)
                DO UPDATE SET hours=excluded.hours,rate=excluded.rate''',
                [(emp_id, day, h, rate) for day, h in values.items()])

    def save_payroll(self, emp_id, values, rate_mode, start, end, utilities=0, rental=0, pdf_path=None):
        iso_date(start); iso_date(end)
        values = hours_map(values)
        if start > end or not values or any(not start <= d <= end for d in values):
            raise ValueError('Hours must belong to the selected non-empty period')
        with self.transaction():
            e = self.get_employee(emp_id)
            rows, summary = calculate_payroll(Employee.from_row(e), values, rate_mode, utilities=utilities, housing=rental)
            rate = rows[0].rate
            snapshot = dict(employee_id=emp_id, name=e['name'], rate=rate, rate_mode=rate_mode,
                            period_from=start, period_to=end, bank=e['bank'], iban=e['iban'], bic=e['bic'],
                            utilities=summary.utilities_deduction, rental=summary.housing_deduction,
                            total_hours=summary.total_hours, gross_amount=summary.gross_amount, net_amount=summary.net_amount)
            fingerprint = hashlib.sha256(json.dumps([snapshot, sorted(values.items())], sort_keys=True).encode()).hexdigest()
            existing = self.conn.execute('SELECT id FROM payrolls WHERE fingerprint=?', (fingerprint,)).fetchone()
            self.save_hours_batch(emp_id, values, rate=rate)
            if existing:
                self.conn.execute('UPDATE payrolls SET pdf_path=COALESCE(?,pdf_path) WHERE id=?', (pdf_path, existing['id']))
                return existing['id']
            snapshot.update(created_at=datetime.now().isoformat(timespec='seconds'), pdf_path=pdf_path, fingerprint=fingerprint)
            columns = ','.join(snapshot)
            marks = ','.join('?' for _ in snapshot)
            cur = self.conn.execute(f'INSERT INTO payrolls({columns}) VALUES({marks})', tuple(snapshot.values()))
            payroll_id = cur.lastrowid
            self.conn.executemany('INSERT INTO payroll_days(payroll_id,work_date,hours,rate,amount) VALUES(?,?,?,?,?)',
                                 [(payroll_id,r.date,r.hours,r.rate,r.amount) for r in rows])
            return payroll_id

    def get_payrolls(self):
        return self.conn.execute('SELECT * FROM payrolls ORDER BY id DESC').fetchall()

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
