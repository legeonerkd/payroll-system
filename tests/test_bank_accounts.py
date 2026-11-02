import sqlite3
import pytest
from core.banking import account_caption,payment_details
from core.models import Employee
from database.db import Database,SCHEMA_VERSION


@pytest.mark.parametrize('state',['yes','no','unknown'])
def test_declared_account_status_round_trips_without_erasing_details(tmp_path,state):
    path=tmp_path/'accounts.db';db=Database(path)
    eid=db.add_employee('Synthetic',15,'Example Bank','TEST-ACCOUNT-1234','EXAMPLE',bank_account_state=state)
    db.close();db=Database(path)
    e=db.get_employee(eid)
    assert e['bank_account_state']==state and e['iban']=='TEST-ACCOUNT-1234'
    assert Employee.from_row(e).has_bank_account is (True if state=='yes' else False if state=='no' else None)
    assert payment_details(e)['iban']==(None if state=='no' else 'TEST-ACCOUNT-1234')
    db.close()


def test_account_caption_masks_iban_and_distinguishes_missing_details():
    status,detail,state=account_caption({'bank_account_state':'yes','bank':'Example Bank','iban':'TEST-SECRET-1234','bic':'SECRET'})
    assert status=='Bank account: Yes' and '1234' in detail
    assert 'TEST-SECRET' not in detail and 'bic' not in detail.lower()
    assert account_caption({'bank_account_state':'no'})[0]=='Bank account: No'
    assert account_caption({'bank_account_state':'unknown'})[0]=='Bank account: Not specified'
    assert 'Select an employee' in account_caption(None)[1]
    assert 'IBAN not recorded' in account_caption({'bank_account_state':'yes'})[1]


def test_no_account_new_statement_omits_retained_details_and_preserves_original():
    db=Database(':memory:')
    eid=db.add_employee('Synthetic',15,'Example Bank','TEST-IBAN','TEST-BIC')
    first=db.save_payroll(eid,{'2026-11-02':8},'custom','2026-11-02','2026-11-02')
    db.update_employee(eid,'Synthetic',15,'Example Bank','TEST-IBAN','TEST-BIC',bank_account_state='no')
    second=db.save_payroll(eid,{'2026-11-02':8},'custom','2026-11-02','2026-11-02',replaces_ids=[first])
    assert db.get_employee(eid)['iban']=='TEST-IBAN'
    assert db.get_payroll_full(first)[0]['iban']=='TEST-IBAN'
    current=db.get_payroll_full(second)[0]
    assert current['iban'] is None and current['bank'] is None and current['bic'] is None
    db.close()


def test_inference_only_when_recording_an_iban_and_no_default_no():
    db=Database(':memory:')
    unknown=db.add_employee('Unknown',15)
    with_iban=db.add_employee('Recorded',15,iban='TEST-IBAN')
    assert db.get_employee(unknown)['bank_account_state']=='unknown'
    assert db.get_employee(with_iban)['bank_account_state']=='yes'
    with pytest.raises(ValueError):db.add_employee('Invalid',15,bank_account_state='maybe')
    db.close()


def test_schema_five_migration_preserves_original_columns_and_snapshots(tmp_path):
    path=tmp_path/'v5.db';db=Database(path)
    known=db.add_employee('Known',15,'Bank','TEST-IBAN','TEST')
    unknown=db.add_employee('Unknown',15)
    db.save_payroll(known,{'2026-11-02':8},'custom','2026-11-02','2026-11-02')
    db.conn.executescript('ALTER TABLE employees DROP COLUMN bank_account_state; PRAGMA user_version=5;')
    columns=[r[1] for r in db.conn.execute('PRAGMA table_info(employees)')]
    before=[tuple(r) for r in db.conn.execute('SELECT * FROM employees ORDER BY id')]
    payroll=[tuple(r) for r in db.conn.execute('SELECT * FROM payrolls')]
    db.close();db=Database(path)
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    assert before==[tuple(r) for r in db.conn.execute('SELECT '+','.join(columns)+' FROM employees ORDER BY id')]
    assert payroll==[tuple(r) for r in db.conn.execute('SELECT * FROM payrolls')]
    assert db.get_employee(known)['bank_account_state']=='yes'
    assert db.get_employee(unknown)['bank_account_state']=='unknown'
    old=sqlite3.connect(db.last_backup)
    assert old.execute('PRAGMA user_version').fetchone()[0]==5
    assert old.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    old.close();db.close()
