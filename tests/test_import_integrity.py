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
