import sqlite3
import pytest

from core.rental import rental_for_rate
from database.db import Database,SCHEMA_VERSION


@pytest.mark.parametrize('state,mode,expected',[
    ('yes','fixed',125),('yes','custom',0),('no','fixed',0),
    ('no','custom',125),('unknown','fixed',0),('unknown','custom',0)])
def test_account_status_selects_exactly_one_rental_statement(state,mode,expected):
    assert rental_for_rate({'bank_account_state':state,'rental_amount':125},mode)==expected


def test_rental_persists_and_other_card_updates_preserve_it(tmp_path):
    path=tmp_path/'rental.db';db=Database(path)
    eid=db.add_employee('Synthetic',15,bank_account_state='yes',rental_amount='125.335')
    old=dict(db.get_employee(eid))
    assert old['rental_amount']==125.34
    db.update_employee_rate(eid,16)
    db.close();db=Database(path)
    assert db.get_employee(eid)['rental_amount']==125.34
    with pytest.raises(ValueError,match='rental changed'):
        db.update_employee(eid,'Synthetic',16,expected=dict(db.get_employee(eid),rental_amount=0),rental_amount=130)
    assert db.get_employee(eid)['rental_amount']==125.34
    db.close()


@pytest.mark.parametrize('amount',[-1,'nan','inf','bad'])
def test_invalid_saved_rental_is_rejected(amount):
    db=Database(':memory:')
    with pytest.raises(ValueError):db.add_employee('Synthetic',15,rental_amount=amount)
    assert not db.get_employees();db.close()


def test_schema_six_migration_keeps_rows_snapshots_and_original_backup(tmp_path):
    path=tmp_path/'v6.db';db=Database(path)
    eid=db.add_employee('Synthetic',15,bank_account_state='no')
    db.save_payroll(eid,{'2026-11-02':8},'custom','2026-11-02','2026-11-02',rental=35)
    db.conn.executescript('ALTER TABLE employees DROP COLUMN rental_amount; PRAGMA user_version=6;')
    columns=[r[1] for r in db.conn.execute('PRAGMA table_info(employees)')]
    employees=[tuple(r) for r in db.conn.execute('SELECT * FROM employees')]
    payrolls=[tuple(r) for r in db.conn.execute('SELECT * FROM payrolls')]
    db.close();db=Database(path)
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    assert employees==[tuple(r) for r in db.conn.execute('SELECT '+','.join(columns)+' FROM employees')]
    assert db.get_employee(eid)['rental_amount']==0
    assert payrolls==[tuple(r) for r in db.conn.execute('SELECT * FROM payrolls')]
    backup=sqlite3.connect(db.last_backup)
    assert backup.execute('PRAGMA user_version').fetchone()[0]==6
    assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    backup.close();db.close()


