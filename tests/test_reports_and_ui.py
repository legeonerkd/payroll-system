from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
import pytest
from pypdf import PdfReader

from core.models import Employee
from services.payroll_service import calculate_custom_payroll
from services import report_service as reports
from database.db import Database
from ui.payroll_tab import PayrollTab


@pytest.mark.parametrize('value',[-1,'nan','inf'])
def test_bad_deductions_rejected(value):
    with pytest.raises(ValueError):calculate_custom_payroll(Employee(1,'Synthetic',12),{'2026-05-01':8},housing=value)


def pdf(tmp_path,monkeypatch,days=2,name='Иван Тестовый'):
    monkeypatch.setenv('PAYROLL_OUTPUT_DIR',str(tmp_path))
    start=date(2026,5,1)
    rows=[((start+timedelta(days=i)).isoformat(),'Friday',.5) for i in range(days)]
    return reports.generate_payroll_pdf(name,8.01,rows,'custom','0','0',rows[0][0],rows[-1][0],
                                        'Synthetic Bank','TEST IBAN','TEST BIC',action='save',employee_id=1)


def test_shared_rounding_unicode_and_unique_paths(tmp_path,monkeypatch):
    first=pdf(tmp_path,monkeypatch)
    second=pdf(tmp_path,monkeypatch)
    assert first!=second
    text='\n'.join(p.extract_text() for p in PdfReader(first).pages)
    _,summary=calculate_custom_payroll(Employee(1,'Synthetic',8.01),{'2026-05-01':.5,'2026-05-02':.5})
    assert summary.gross_amount==8.02
    assert 'Net amount: 8.02' in text
    assert 'Иван Тестовый' in text


def test_month_and_long_period_paginate(tmp_path,monkeypatch):
    for days in (31,60):
        path=pdf(tmp_path,monkeypatch,days)
        pages=PdfReader(path).pages
        text='\n'.join(p.extract_text() for p in pages)
        assert len(pages)>1
        assert text.count('Employee signature:')==1
        assert text.count('Date:')==2
        assert text.count('Hourly rate')==len(pages) or text.count('Hourly rate')==len(pages)-1


def test_unsafe_name_stays_inside_output(tmp_path,monkeypatch):
    path=Path(pdf(tmp_path,monkeypatch,name='../../CON:bad?name'))
    assert path.resolve().is_relative_to(tmp_path.resolve())
    assert path.exists()


def test_snapshot_preview_uses_saved_sums(tmp_path,monkeypatch):
    db=Database(':memory:');eid=db.add_employee('Synthetic',8.01)
    pid=db.save_payroll(eid,{'2026-05-01':.5,'2026-05-02':.5},'custom','2026-05-01','2026-05-02')
    db.update_employee_rate(eid,99)
    payroll,days=db.get_payroll_full(pid)
    monkeypatch.setattr(reports,'_open_file',lambda p:None)
    path=reports.preview_payroll_pdf_from_history(payroll,days)
    try:
        assert 'Net amount: 8.02' in PdfReader(path).pages[0].extract_text()
    finally:
        Path(path).unlink();db.close()


@pytest.fixture(scope='module')
def tk_root():
    try:
        root=tk.Tk()
    except tk.TclError:
        pytest.skip('A display is required for Tk integration tests')
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def ui(tk_root):
    root=tk_root
    db=Database(':memory:')
    first=db.add_employee('Namesake',20);second=db.add_employee('Namesake',30)
    tab=PayrollTab(root,db)
    tab.from_entry.set_date(date(2026,5,1));tab.to_entry.set_date(date(2026,5,1))
    tab.rate_mode.set('custom')
    yield tab,db,first,second
    tab.destroy();root.update_idletasks();db.close()


def select(tab,eid):
    label=next(label for label,e in tab.employee_map.items() if e['id']==eid)
    tab.employee_cb.set(label)


def test_switch_loads_own_hours_and_recalculates(ui):
    tab,db,first,second=ui
    db.save_hours(first,'2026-05-01',8);db.save_hours(second,'2026-05-01',6)
    select(tab,first);tab._generate_period()
    assert tab.days_data=={'2026-05-01':8}
    assert tab.gross_var.get()=='160.00 €'
    select(tab,second);tab._employee_changed()
    assert tab.days_data=={'2026-05-01':6}
    assert tab.gross_var.get()=='180.00 €'


def test_preview_and_failed_pdf_do_not_write_hours(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('preview')
    assert not db.get_all_hours()
    assert not db.get_payrolls()
    tab.utilities_var.set('not a number')
    with pytest.raises(ValueError):tab._call_pdf('save')
    assert not db.get_all_hours()


def test_save_records_snapshot_and_changed_period_is_rejected(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save')
    assert len(db.get_payrolls())==1
    assert db.get_all_hours()[0]['rate']==20
    tab.to_entry.set_date(date(2026,5,2))
    with pytest.raises(ValueError):tab._call_pdf('save')
