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


@pytest.mark.parametrize('days',[1,28,31,60])
def test_complete_statement_fits_one_page(tmp_path,monkeypatch,days):
    path=pdf(tmp_path,monkeypatch,days,name='Иван Тестовый ' * 8)
    pages=PdfReader(path).pages
    text='\n'.join(p.extract_text() for p in pages)
    assert len(pages)==1
    assert text.count('Employee signature:')==1
    assert text.count('Date:')==2
    assert text.count('Hourly rate')==1
    assert f'Total hours: {days*.5:g} h' in text
    for i in range(days):
        assert (date(2026,5,1)+timedelta(days=i)).strftime('%d.%m.%Y') in text
    assert 'Manager signature:' in text


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


def test_distribute_then_manually_edit_and_save_draft(ui,monkeypatch):
    tab,db,first,_ = ui
    select(tab,first)
    tab.to_entry.set_date(date(2026,5,4))
    tab.distribution_hours_var.set('10')
    tab._distribute_hours()
    assert sum(tab.days_data.values()) == 10
    assert all(isinstance(h,int) for h in tab.days_data.values())
    assert tab.days_data['2026-05-03'] == 0
    assert tab.total_hours_var.get() == '10'
    assert not db.get_all_hours()
    before_edit = tab.days_data['2026-05-02']
    tab._editor = tk.Spinbox(tab.tree)
    tab._editor.delete(0,'end');tab._editor.insert(0,'4.25')
    tab._save_hours('2026-05-02')
    assert tab.days_data['2026-05-02'] == 4.25
    assert tab.total_hours_var.get() == f'{10-before_edit+4.25:g}'
    monkeypatch.setattr('ui.payroll_tab.messagebox.showinfo',lambda *a:None)
    tab._save_draft()
    saved = {r['work_date']:r['hours'] for r in db.load_hours(first,'2026-05-01','2026-05-04')}
    assert saved == tab.days_data
    tab._generate_period()
    assert tab.days_data == saved
    assert not tab._manual_days


def test_manual_mark_and_escape_preserve_saved_hours(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first)
    db.save_hours(first,'2026-05-01',8)
    tab._generate_period()
    assert tab.save_status_var.get()=='Hours loaded · draft'
    tab._editor=tk.Spinbox(tab.tree)
    tab._editor.delete(0,'end');tab._editor.insert(0,'9')
    tab._cancel_hours_edit()
    tab._save_hours('2026-05-01')
    assert tab.days_data['2026-05-01']==8
    assert not tab.has_unsaved_changes()
    tab._editor=tk.Spinbox(tab.tree)
    tab._editor.delete(0,'end');tab._editor.insert(0,'9')
    tab._save_hours('2026-05-01')
    assert tab.tree.item('2026-05-01','values')[3]=='Manual edit'
    assert tab.save_status_var.get()=='Unsaved changes'
    monkeypatch.setattr('ui.payroll_tab.messagebox.showinfo',lambda *a:None)
    tab._save_draft()
    assert tab.save_status_var.get()=='Hours saved · draft'


def test_payroll_settings_stay_pending_after_hours_save(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    tab.utilities_var.set('30')
    assert tab.has_unsaved_changes()
    monkeypatch.setattr('ui.payroll_tab.messagebox.showinfo',lambda *a:None)
    tab._save_draft()
    assert not tab._dirty and tab._payroll_dirty
    assert tab.save_status_var.get()=='Hours saved · payroll settings pending'
    assert not db.get_payrolls()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save')
    assert not tab.has_unsaved_changes()
    assert tab.save_status_var.get()=='Payroll saved'
    assert len(db.get_payrolls())==1
    tab.utilities_var.set('31')
    assert tab.save_status_var.get()=='Unsaved changes'


@pytest.mark.parametrize('action',['preview','print'])
def test_preview_and_print_never_save_a_payroll(ui,monkeypatch,action):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf(action)
    assert not db.get_all_hours() and not db.get_payrolls()
    assert tab.has_unsaved_changes()


def test_period_change_requires_reload_and_does_not_change_data(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    original=dict(tab.days_data)
    tab.to_entry.set_date(date(2026,5,2))
    tab._update_save_status()
    assert tab.save_status_var.get()=='Period changed: load or distribute'
    with pytest.raises(ValueError):tab._call_pdf('save')
    assert tab.days_data==original and not db.get_all_hours()


def test_cancel_switch_keeps_unsaved_deductions(ui,monkeypatch):
    tab,db,first,second=ui
    select(tab,first)
    db.save_hours(first,'2026-05-01',8)
    tab._generate_period()
    tab.utilities_var.set('25')
    monkeypatch.setattr('ui.payroll_tab.messagebox.askyesno',lambda *a:False)
    select(tab,second);tab._employee_changed()
    assert tab.employee_map[tab.employee_cb.get()]['id']==first
    assert tab.utilities_var.get()=='25'


def test_cancel_or_invalid_distribution_preserves_hours(ui,monkeypatch):
    tab,db,first,_ = ui
    select(tab,first)
    db.save_hours(first,'2026-05-01',7)
    tab._generate_period()
    original = dict(tab.days_data)
    monkeypatch.setattr('ui.payroll_tab.messagebox.askyesno',lambda *a:False)
    tab.distribution_hours_var.set('8')
    tab._distribute_hours()
    assert tab.days_data == original
    errors = []
    monkeypatch.setattr('ui.payroll_tab.messagebox.showerror',lambda *a:errors.append(a))
    tab.distribution_hours_var.set('999')
    tab._distribute_hours()
    assert errors and tab.days_data == original
    assert db.load_hours(first,'2026-05-01','2026-05-01')[0]['hours'] == 7


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
