import sqlite3
from pathlib import Path
import pytest

from database.db import Database, SCHEMA_VERSION
from core.models import Employee


@pytest.fixture
def db():
    db=Database(':memory:')
    yield db
    db.close()


def test_zero_correction_and_batch_rollback(db):
    eid=db.add_employee('Synthetic',12)
    db.save_hours(eid,'2026-05-01',8)
    db.save_hours_batch(eid,{'2026-05-01':0})
    assert db.load_hours(eid,'2026-05-01','2026-05-01')[0]['hours']==0
    with pytest.raises(ValueError):
        db.save_hours_batch(eid,{'2026-05-01':4,'2026-05-02':25})
    assert db.get_all_hours()[0]['hours']==0
    assert db.conn.execute('PRAGMA foreign_keys').fetchone()[0]==1


def test_snapshot_survives_card_updates_and_archive(db):
    eid=db.add_employee('Synthetic',15,'Test Bank','TEST-IBAN','TEST-BIC')
    pid=db.save_payroll(eid,{'2026-05-01':8},'fixed','2026-05-01','2026-05-01',utilities=4,rental=10)
    assert db.save_payroll(eid,{'2026-05-01':8},'fixed','2026-05-01','2026-05-01',utilities=4,rental=10)==pid
    db.update_employee(eid,'Renamed',30,'New Bank','NEW','NEW')
    db.delete_employee(eid)
    p,days=db.get_payroll_full(pid)
    assert (p['name'],p['rate'],p['bank'],p['gross_amount'],p['net_amount'])==('Synthetic',8,'Test Bank',64,50)
    assert days[0]['amount']==64
    assert db.get_all_hours()[0]['rate']==8
    assert len(db.get_employees())==0
    assert len(db.get_employees(include_archived=True))==1
    assert len(db.load_hours(eid,'2026-05-01','2026-05-01'))==1


def test_nested_transaction_rolls_back_all_rows(db):
    with pytest.raises(RuntimeError):
        with db.transaction():
            eid=db.add_employee('Synthetic',12)
            db.save_hours(eid,'2026-05-01',8)
            raise RuntimeError('Synthetic failure')
    assert not db.get_employees()
    assert not db.get_all_hours()


@pytest.mark.parametrize('rate',[0,-1,'nan','inf','-inf','bad','1e1000'])
def test_invalid_employee_rate_rejected(db,rate):
    with pytest.raises(ValueError):db.add_employee('Synthetic',rate)
    assert not db.get_employees()


def test_bank_model_and_csv_do_not_use_current_rate(db,tmp_path):
    eid=db.add_employee('=Synthetic',15,'Bank','IBAN','BIC')
    db.update_employee_bank(eid,True,'Updated Bank','IBAN','BIC')
    assert Employee.from_row(db.get_employee(eid)).bank_name=='Updated Bank'
    db.save_hours(eid,'2026-05-01',8,rate=15)
    db.update_employee_rate(eid,30)
    target=tmp_path/'hours.csv';db.export_hours_to_csv(target)
    text=target.read_text(encoding='utf-8-sig')
    assert "'=Synthetic" in text
    assert '120.00' in text
    assert '240.00' not in text


def legacy_db(path,conflict=False):
    c=sqlite3.connect(path)
    c.executescript('''CREATE TABLE employees(id INTEGER PRIMARY KEY,name TEXT NOT NULL,rate REAL NOT NULL,
        has_bank_account INTEGER DEFAULT 0,bank_name TEXT,iban TEXT,bic TEXT);
        INSERT INTO employees VALUES(1,'Synthetic',12,1,'Legacy Bank','TEST','TEST');
        CREATE TABLE daily_hours(employee_id INTEGER,work_date TEXT,hours REAL);
        INSERT INTO daily_hours VALUES(1,'2026-05-01',8);''')
    if conflict:
        c.execute("INSERT INTO daily_hours VALUES(999,'2026-05-02',8)")
    c.commit();c.close()


def test_legacy_migration_and_backup_are_repeatable(tmp_path):
    path=tmp_path/'legacy.db';legacy_db(path)
    db=Database(path)
    backup=db.last_backup
    assert backup.exists()
    assert db.get_employee(1)['bank']=='Legacy Bank'
    assert db.load_hours(1,'2026-05-01','2026-05-01')[0]['hours']==8
    assert db.get_all_hours()[0]['rate'] is None
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    db.add_employee('New Synthetic',15)
    db.close()
    db=Database(path)
    assert len(db.get_all_hours())==1
    db.close()
    original=sqlite3.connect(backup)
    assert original.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert original.execute('SELECT count(*) FROM daily_hours').fetchone()[0]==1
    original.close()


def test_failed_migration_retains_original(tmp_path):
    path=tmp_path/'legacy.db';legacy_db(path,True)
    with pytest.raises(RuntimeError):Database(path)
    original=sqlite3.connect(path)
    assert original.execute('SELECT count(*) FROM daily_hours').fetchone()[0]==2
    assert 'bank' not in [r[1] for r in original.execute('pragma table_info(employees)')]
    original.close()


def test_legacy_display_date_is_normalized(tmp_path):
    path=tmp_path/'legacy.db';legacy_db(path)
    c=sqlite3.connect(path);c.execute("UPDATE daily_hours SET work_date='01-05-2026'");c.commit();c.close()
    db=Database(path)
    assert db.get_all_hours()[0]['work_date']=='2026-05-01'
    db.update_employee(1,'Synthetic',12,None,None,None)
    db.close()
    db=Database(path)
    assert db.get_employee(1)['bank'] is None
    db.close()


def test_conflicting_legacy_hours_abort_instead_of_overwriting(tmp_path):
    path=tmp_path/'legacy.db';legacy_db(path)
    c=sqlite3.connect(path)
    c.executescript('''CREATE TABLE work_hours(id INTEGER PRIMARY KEY,employee_id INTEGER,
        work_date TEXT,hours REAL,UNIQUE(employee_id,work_date));
        INSERT INTO work_hours VALUES(1,1,'2026-05-01',6);''')
    c.close()
    with pytest.raises(RuntimeError):Database(path)
    c=sqlite3.connect(path)
    assert c.execute('SELECT hours FROM work_hours').fetchone()[0]==6
    assert c.execute('SELECT hours FROM daily_hours').fetchone()[0]==8
    c.close()


def test_newer_schema_is_not_downgraded(tmp_path):
    path=tmp_path/'future.db'
    c=sqlite3.connect(path);c.execute('PRAGMA user_version=999');c.close()
    with pytest.raises(RuntimeError):Database(path)


def legacy_history_tables(path, populated=False):
    c=sqlite3.connect(path)
    c.executescript('''CREATE TABLE payrolls(id INTEGER PRIMARY KEY,employee_id INTEGER,
        period_from TEXT,period_to TEXT,created_at TEXT,rate REAL,utilities REAL,rental REAL,
        total_hours REAL,net_amount REAL);
        CREATE TABLE payroll_days(id INTEGER PRIMARY KEY,payroll_id INTEGER REFERENCES payrolls(id),
        work_date TEXT,hours REAL);''')
    if populated:
        c.execute("INSERT INTO payrolls VALUES(1,1,'2026-05-01','2026-05-01','2026-05-02',12,0,0,8,96)")
        c.execute("INSERT INTO payroll_days VALUES(1,1,'2026-05-01',8)")
    c.commit();c.close()


@pytest.mark.parametrize('version',[0,2])
def test_empty_legacy_history_is_rebuilt_and_usable(tmp_path,version):
    path=tmp_path/'legacy.db';legacy_db(path);legacy_history_tables(path)
    c=sqlite3.connect(path);c.execute(f'PRAGMA user_version={version}');c.close()
    db=Database(path)
    assert db.last_backup.exists()
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    pid=db.save_payroll(1,{'2026-05-01':8},'custom','2026-05-01','2026-05-01')
    p,days=db.get_payroll_full(pid)
    assert p['net_amount']==96
    assert days[0]['amount']==96
    assert db.load_hours(1,'2026-05-01','2026-05-01')[0]['hours']==8
    db.close()


def test_populated_unsupported_history_is_preserved(tmp_path):
    path=tmp_path/'legacy.db';legacy_db(path);legacy_history_tables(path,populated=True)
    with pytest.raises(RuntimeError,match='unsupported schema'):Database(path)
    c=sqlite3.connect(path)
    assert c.execute('SELECT net_amount FROM payrolls').fetchone()[0]==96
    assert c.execute('SELECT hours FROM payroll_days').fetchone()[0]==8
    assert c.execute('PRAGMA user_version').fetchone()[0]==0
    assert 'archived' not in [r[1] for r in c.execute('PRAGMA table_info(employees)')]
    c.close()


def test_schema_two_upgrade_does_not_restore_cleared_bank(tmp_path):
    path=tmp_path/'schema2.db';legacy_db(path)
    db=Database(path);db.update_employee(1,'Synthetic',12,None,None,None)
    db.conn.execute('PRAGMA user_version=2');db.close()
    db=Database(path)
    assert db.get_employee(1)['bank'] is None
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    db.close()
