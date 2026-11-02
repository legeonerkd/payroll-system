from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest
from pypdf import PdfReader
from database.db import Database,PeriodClosedError,SCHEMA_VERSION
from core.payroll_checks import payroll_checks
from services import report_service as reports
from services import paired_payroll_service as pairs
from services.excel_import_service import process_import,EmployeeData

DAY='2026-11-02';HOURS={DAY:8}


@pytest.fixture
def operations():
    db=Database(':memory:');eid=db.add_employee('Synthetic',15,bank_account_state='no',rental_amount=50)
    fixed=db.save_payroll(eid,HOURS,'fixed',DAY,DAY)
    custom=db.save_payroll(eid,HOURS,'custom',DAY,DAY,rental=50,utilities=4)
    db.register_payroll_pair(fixed,custom)
    yield db,eid,fixed,custom
    db.close()


def test_journal_records_actual_changes_atomically_without_bank_details():
    db=Database(':memory:');eid=db.add_employee('Synthetic',15,iban='SECRET-1234',bank_account_state='no',rental_amount=50)
    assert len(db.get_employee_changes(eid))==3
    db.update_employee(eid,'Renamed',16,iban='NEW-SECRET',bank_account_state='yes',rental_amount=75)
    changes=db.get_employee_changes(eid)
    assert len(changes)==6
    assert {r['field']:(r['old_value'],r['new_value']) for r in changes[:3]}=={
        'rate':('15.0','16.0'),'rental_amount':('50.0','75.0'),'bank_account_state':('no','yes')}
    assert 'SECRET' not in str([dict(r) for r in changes])
    db.update_employee(eid,'Renamed',16,iban='NEW-SECRET',bank_account_state='yes',rental_amount=75)
    assert len(db.get_employee_changes(eid))==6
    db.conn.execute("CREATE TRIGGER fail_journal BEFORE INSERT ON employee_changes BEGIN SELECT RAISE(ABORT,'synthetic journal failure'); END;")
    with pytest.raises(sqlite3.IntegrityError):db.update_employee_rate(eid,17)
    assert db.get_employee(eid)['rate']==16 and len(db.get_employee_changes(eid))==6
    db.close()


def test_migration_eight_preserves_original_rows_and_does_not_invent_old_changes(tmp_path):
    path=tmp_path/'v8.db';db=Database(path);eid=db.add_employee('Synthetic',15,rental_amount=50)
    db.save_payroll(eid,HOURS,'custom',DAY,DAY,rental=50)
    tables=('employees','work_hours','payrolls','payroll_days','payroll_content_keys','payroll_revision_links','payroll_pairs')
    before={table:[tuple(r) for r in db.conn.execute('SELECT * FROM '+table)] for table in tables}
    db.conn.executescript('DROP TABLE employee_changes; DROP TABLE closed_periods; PRAGMA user_version=8;');db.close()
    db=Database(path)
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    assert before=={table:[tuple(r) for r in db.conn.execute('SELECT * FROM '+table)] for table in tables}
    assert not db.get_employee_changes() and not db.get_closed_periods(active_only=False)
    backup=sqlite3.connect(db.last_backup)
    assert backup.execute('PRAGMA user_version').fetchone()[0]==8
    assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    backup.close();db.close()


def test_close_blocks_all_writes_but_preserves_reports_and_allows_other_dates(operations):
    db,eid,fixed,custom=operations
    before=[dict(p) for p in db.get_payrolls()]
    pid=db.close_period(eid,DAY,DAY)
    assert db.close_period(eid,DAY,DAY)==pid and db.period_is_closed(eid,DAY,DAY)
    for operation in (
        lambda:db.save_hours(eid,DAY,9),
        lambda:db.save_hours_batch(eid,{DAY:9,'2026-11-03':4}),
        lambda:db.save_period_hours(eid,HOURS,{DAY:{'locked':True,'excluded':False}},(8,12)),
        lambda:db.save_payroll(eid,HOURS,'fixed',DAY,DAY,replaces_ids=[fixed]),
        lambda:db.payroll_save_plan(eid,HOURS,'custom',DAY,DAY),
        lambda:db.register_payroll_pair(fixed,custom)):
        with pytest.raises(PeriodClosedError):operation()
    assert [dict(p) for p in db.get_payrolls()]==before
    assert not db.load_day_rules(eid,DAY,DAY)
    assert db.load_hours(eid,DAY,'2026-11-03')[0]['hours']==8
    assert len(db.load_hours(eid,DAY,'2026-11-03'))==1
    db.save_hours_batch(eid,{'2026-01-01':1,'2026-12-01':1})
    other=db.add_employee('Other',15);db.save_hours(other,DAY,3)
    assert db.get_month_summary(2026,11)['totals']['net']==130


def test_reopen_is_explicit_retains_close_history_and_allows_corrections(operations):
    db,eid,fixed,custom=operations
    first=db.close_period(eid,DAY,DAY)
    assert db.reopen_period(first) and not db.reopen_period(first)
    assert not db.period_is_closed(eid,DAY,DAY)
    db.save_hours(eid,DAY,9)
    with pytest.raises(ValueError,match='do not match'):db.close_period(eid,DAY,DAY)
    new_fixed=db.save_payroll(eid,{DAY:9},'fixed',DAY,DAY,replaces_ids=[fixed])
    new_custom=db.save_payroll(eid,{DAY:9},'custom',DAY,DAY,rental=50,utilities=4,replaces_ids=[custom])
    db.register_payroll_pair(new_fixed,new_custom)
    second=db.close_period(eid,DAY,DAY)
    assert second!=first and len(db.get_closed_periods(active_only=False))==2
    assert db.get_closed_periods(active_only=False)[1]['reopened_at']


def test_incomplete_or_ambiguous_period_cannot_be_closed():
    db=Database(':memory:');eid=db.add_employee('Synthetic',15)
    with pytest.raises(ValueError,match='Save the statements'):db.close_period(eid,DAY,DAY)
    db.save_payroll(eid,HOURS,'fixed',DAY,DAY)
    db.save_payroll(eid,HOURS,'custom',DAY,DAY)
    with pytest.raises(ValueError,match='linked pair'):db.close_period(eid,DAY,DAY)
    assert not db.get_closed_periods();db.close()


def test_import_on_closed_date_rolls_back_employee_changes_and_journal(operations):
    db,eid,_,_=operations;db.close_period(eid,DAY,DAY)
    before=dict(db.get_employee(eid));journal=[dict(r) for r in db.get_employee_changes()]
    employee=EmployeeData('Renamed',16,employee_id=eid);employee.add_hours(DAY,9)
    with pytest.raises(PeriodClosedError):process_import(db,[employee],dict(save_to_db=True,create_pdf=False,update_existing=True,rate_mode='custom',utilities=0))
    assert dict(db.get_employee(eid))==before and [dict(r) for r in db.get_employee_changes()]==journal


def test_closing_during_pair_generation_keeps_old_pair_and_removes_new_files(operations,tmp_path,monkeypatch):
    db,eid,_,_=operations;employee=db.get_employee(eid)
    plans=pairs.pair_plans(db,employee,HOURS,DAY,DAY,4);generated=[]
    def generate(**kw):
        path=tmp_path/f"Payroll_{kw['rate_mode']}.pdf";path.write_bytes(b'synthetic');generated.append(path)
        if kw['rate_mode']=='custom':db.close_period(eid,DAY,DAY)
        return str(path)
    monkeypatch.setattr(pairs,'generate_payroll_pdf',generate)
    with pytest.raises(PeriodClosedError):pairs.save_payroll_pair(db,employee,HOURS,DAY,DAY,4,plans=plans,day_rules={},settings=(0,14))
    assert len(db.get_payrolls())==2 and not any(path.exists() for path in generated)


def test_preflight_reports_warnings_without_requiring_positive_utilities(operations):
    db,eid,_,_=operations
    employee=dict(db.get_employee(eid),bank_account_state='unknown')
    notices=payroll_checks(employee,{DAY:0},0)
    assert any('not specified' in text for text in notices) and any('zero' in text for text in notices)
    employee.update(bank_account_state='yes',rental_amount=100)
    assert any('Fixed rate has negative' in text for text in payroll_checks(employee,HOURS,0))
    employee['rental_amount']=0
    assert payroll_checks(employee,HOURS,0)==[]


def test_selected_reprint_prefers_original_and_never_changes_database(operations,tmp_path,monkeypatch):
    db,eid,_,custom=operations;original=tmp_path/'original.pdf';original.write_bytes(b'original')
    db.conn.execute('UPDATE payrolls SET pdf_path=? WHERE id=?',(str(original),custom));db.conn.commit()
    db.close_period(eid,DAY,DAY)
    before=[dict(p) for p in db.get_payrolls()];sent=[]
    monkeypatch.setattr(reports,'_print_file',lambda path:sent.append(path))
    payroll,days=db.get_payroll_full(custom)
    assert reports.print_payroll_pdf_from_history(payroll,days)==str(original)
    assert sent==[str(original)] and original.read_bytes()==b'original'
    assert [dict(p) for p in db.get_payrolls()]==before


def test_missing_reprint_file_uses_saved_values_not_updated_card(operations,tmp_path,monkeypatch):
    db,eid,_,custom=operations;db.close_period(eid,DAY,DAY)
    db.update_employee(eid,'Updated',100,bank_account_state='yes',rental_amount=0)
    payroll,days=db.get_payroll_full(custom);sent=[]
    monkeypatch.setenv('PAYROLL_OUTPUT_DIR',str(tmp_path))
    monkeypatch.setattr(reports,'_print_file',lambda path:sent.append(path))
    path=reports.print_payroll_pdf_from_history(payroll,days)
    reader=PdfReader(path);assert len(reader.pages)==1
    text=reader.pages[0].extract_text()
    assert 'Employee: Synthetic' in text and 'Net amount: 66.00' in text
    assert 'Utilities deduction: 4.00' in text and 'Rental deduction: 50.00' in text
    assert sent==[path] and len(db.get_payrolls())==2


def test_pdf_folder_opens_original_location_or_reports_root(operations,tmp_path,monkeypatch):
    db,_,_,custom=operations;payroll=dict(db.get_payroll_full(custom)[0]);opened=[]
    monkeypatch.setattr(reports,'_open_file',lambda path:opened.append(path))
    payroll['pdf_path']=str(tmp_path/'original.pdf')
    assert reports.open_payroll_pdf_folder(payroll)==str(tmp_path)
    root=tmp_path/'reports';monkeypatch.setenv('PAYROLL_OUTPUT_DIR',str(root))
    assert reports.open_payroll_pdf_folder()==str(root)
    assert opened==[str(tmp_path),str(root)]


def test_backup_contains_closed_state_and_change_history(tmp_path):
    from core.backup import backup_db,prepare_restore,install_restore
    path=tmp_path/'live.db';db=Database(path)
    eid=db.add_employee('Synthetic',15)
    db.save_payroll(eid,HOURS,'custom',DAY,DAY)
    period=db.close_period(eid,DAY,DAY);db.update_employee_rate(eid,16)
    before=[dict(r) for r in db.get_employee_changes()]
    backup=tmp_path/'copy.db';backup_db(path,backup)
    db.reopen_period(period);db.update_employee_rate(eid,17);db.close()
    with prepare_restore(path,backup) as (staged,_):install_restore(path,staged)
    db=Database(path,create_backup=False)
    assert db.period_is_closed(eid,DAY,DAY) and db.get_employee(eid)['rate']==16
    assert [dict(r) for r in db.get_employee_changes()]==before
    db.close()
