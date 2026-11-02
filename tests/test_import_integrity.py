from queue import Queue
from threading import Thread
import pandas as pd
import pytest

from database.db import Database
from services.excel_import_service import EmployeeData, ExcelImportError, import_excel_file, process_import
from ui.excel_import import ExcelImportWindow


def make_xlsx(tmp_path,rows,dates=None):
    path=tmp_path/'input.xlsx'
    pd.DataFrame(rows,columns=['Employee Name','Hourly Rate','Bank','IBAN','BIC']+(dates or ['01-05-2026'])).to_excel(path,index=False)
    return path


@pytest.mark.parametrize('rate',[None,0,-1,'nan','inf'])
def test_missing_or_nonfinite_rate_rejected(tmp_path,rate):
    path=make_xlsx(tmp_path,[['Synthetic',rate,None,None,None,8]])
    with pytest.raises(ExcelImportError):import_excel_file(path)


@pytest.mark.parametrize('dates',[['01-05-2026','01.05.2026'],['01-05-2026','01-05-2026']])
def test_duplicate_date_headers_rejected(tmp_path,dates):
    path=make_xlsx(tmp_path,[['Synthetic',12,None,None,None,8,6]],dates)
    with pytest.raises(ExcelImportError):import_excel_file(path)


def test_explicit_zero_and_fractional_hours_preserved(tmp_path):
    path=make_xlsx(tmp_path,[['Synthetic',12,None,None,None,0,8.25]],['01-05-2026','02-05-2026'])
    assert import_excel_file(path)[0].hours_by_date=={'2026-05-01':0,'2026-05-02':8.25}


def options(**updates):
    result=dict(save_to_db=True,create_pdf=False,update_existing=True,rate_mode='custom',utilities='0',rental='0')
    result.update(updates);return result


@pytest.mark.parametrize('save_to_db',[True,False])
@pytest.mark.parametrize('state,mode,expected',[
    ('yes','fixed',50),('yes','custom',0),('no','fixed',0),
    ('no','custom',50),('unknown','fixed',0),('unknown','custom',0)])
def test_import_uses_saved_rental_and_preserves_employee_setting(tmp_path,monkeypatch,save_to_db,state,mode,expected):
    db=Database(':memory:')
    eid=db.add_employee('Synthetic',12,bank_account_state=state,rental_amount=50)
    emp=employee(employee_id=eid)
    captured=[]
    def pdf(*args,**kwargs):
        captured.append(args);path=tmp_path/'synthetic.pdf';path.write_bytes(b'test');return str(path)
    monkeypatch.setattr('services.excel_import_service.generate_payroll_pdf',pdf)
    process_import(db,[emp],options(save_to_db=save_to_db,create_pdf=True,rate_mode=mode))
    assert float(captured[0][5])==expected
    assert db.get_employee(eid)['rental_amount']==50
    if save_to_db:assert db.get_payrolls()[0]['rental']==expected
    else:assert not db.get_payrolls() and not db.get_all_hours()
    db.close()


def employee(name='Synthetic',rate=12,employee_id=None):
    e=EmployeeData(name,rate,employee_id=employee_id);e.add_hours('2026-05-01',8.25);return e


def test_worker_owns_its_connection(tmp_path):
    path=tmp_path/'worker.db';db=Database(path)
    events=Queue()
    t=Thread(target=ExcelImportWindow._generate_thread,args=(str(path),[employee()],options(),events))
    t.start();t.join(timeout=15)
    assert not t.is_alive()
    messages=[]
    while not events.empty():messages.append(events.get())
    assert messages[-1][0]=='done',messages
    assert db.get_all_hours()[0]['hours']==8.25
    db.close()


def test_import_cannot_overwrite_excluded_date_and_rolls_back_other_employees():
    db=Database(':memory:')
    eid=db.add_employee('Excluded employee',12)
    db.save_period_hours(eid,{'2026-05-01':0},{'2026-05-01':{'locked':False,'excluded':True}},(0,24))
    with pytest.raises(ValueError,match='excluded'):
        process_import(db,[employee('New employee'),employee('Excluded employee',employee_id=eid)],options())
    assert len(db.get_employees())==1
    assert db.get_all_hours()[0]['hours']==0
    assert db.load_day_rules(eid,'2026-05-01','2026-05-01')['2026-05-01']['excluded']
    db.close()


def test_import_cannot_silently_issue_a_changed_statement_for_same_period(monkeypatch,tmp_path):
    from services import excel_import_service as service
    db=Database(':memory:');eid=db.add_employee('Synthetic',12)
    original=db.save_payroll(eid,{'2026-05-01':8},'custom','2026-05-01','2026-05-01')
    monkeypatch.setattr(service,'generate_payroll_pdf',lambda *a,**k:str(tmp_path/'synthetic.pdf'))
    with pytest.raises(ValueError,match='already exists'):
        process_import(db,[employee(employee_id=eid)],options(create_pdf=True))
    assert len(db.get_payrolls())==1 and db.get_payrolls()[0]['id']==original
    assert db.get_all_hours()[0]['hours']==8
    db.close()


@pytest.mark.parametrize('save_to_db',[False,True])
def test_import_respects_declared_no_account_and_preserves_card_details(monkeypatch,tmp_path,save_to_db):
    from services import excel_import_service as service
    db=Database(':memory:')
    eid=db.add_employee('Synthetic',12,'Example Bank','TEST-IBAN','TEST-BIC',bank_account_state='no')
    captured=[]
    monkeypatch.setattr(service,'generate_payroll_pdf',lambda *a,**k:captured.append(a) or str(tmp_path/'synthetic.pdf'))
    process_import(db,[employee(employee_id=eid)],options(create_pdf=True,save_to_db=save_to_db))
    assert captured[0][8:11]==(None,None,None)
    assert db.get_employee(eid)['bank_account_state']=='no' and db.get_employee(eid)['iban']=='TEST-IBAN'
    if save_to_db:assert db.get_payrolls()[0]['iban'] is None
    db.close()


def test_namesakes_require_id_and_blank_banks_are_preserved():
    db=Database(':memory:')
    first=db.add_employee('Synthetic',12,'Bank','IBAN','BIC')
    db.add_employee('Synthetic',15)
    with pytest.raises(ExcelImportError):process_import(db,[employee()],options())
    assert not db.get_all_hours()
    process_import(db,[employee(employee_id=first)],options())
    assert db.get_employee(first)['bank']=='Bank'
    db.close()


def test_later_pdf_failure_rolls_back_database_and_files(tmp_path,monkeypatch):
    from services import excel_import_service as service
    made=[]
    def pdf(*args,**kwargs):
        if made:raise RuntimeError('Synthetic PDF failure')
        path=tmp_path/'synthetic.pdf';path.write_bytes(b'synthetic');made.append(path);return str(path)
    monkeypatch.setattr(service,'generate_payroll_pdf',pdf)
    db=Database(':memory:')
    with pytest.raises(RuntimeError):process_import(db,[employee('First'),employee('Second')],options(create_pdf=True))
    assert not db.get_employees()
    assert not db.get_all_hours()
    assert not made[0].exists()
    db.close()


def test_pdf_only_import_does_not_create_employees(monkeypatch):
    from services import excel_import_service as service
    monkeypatch.setattr(service,'generate_payroll_pdf',lambda *a,**k:'synthetic.pdf')
    db=Database(':memory:')
    result=process_import(db,[employee()],options(save_to_db=False,create_pdf=True))
    assert result['employees']==1
    assert not db.get_employees()
    db.close()


def test_precision_reaches_pdf_and_snapshot(tmp_path,monkeypatch):
    from services import excel_import_service as service
    seen=[]
    def fake_pdf(*args,**kwargs):
        seen.append(args[2]);p=tmp_path/'synthetic.pdf';p.write_bytes(b'fixture');return str(p)
    monkeypatch.setattr(service,'generate_payroll_pdf',fake_pdf)
    db=Database(':memory:')
    process_import(db,[employee()],options(create_pdf=True))
    assert seen[0][0][2]==8.25
    assert db.get_payrolls()[0]['total_hours']==8.25
    db.close()


def test_invalid_later_employee_does_not_commit_first():
    db=Database(':memory:')
    with pytest.raises(ValueError):process_import(db,[employee('New Synthetic'),employee(employee_id=999)],options())
    assert not db.get_employees()
    db.close()
