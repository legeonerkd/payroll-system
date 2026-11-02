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


def test_pins_exclusions_range_survive_save_reload_and_distribution(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab.to_entry.set_date(date(2026,5,4))
    tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.messagebox.askyesno',lambda *a:True)
    monkeypatch.setattr('ui.payroll_tab.messagebox.showinfo',lambda *a:None)
    tab.tree.selection_set('2026-05-01');tab._toggle_day_rule('locked')
    tab.tree.selection_set('2026-05-02');tab._toggle_day_rule('excluded')
    tab.distribution_min_var.set('8');tab.distribution_max_var.set('12')
    tab.distribution_hours_var.set('20')
    tab._distribute_hours()
    assert tab.days_data=={'2026-05-01':10,'2026-05-02':0,'2026-05-03':0,'2026-05-04':10}
    assert tab._locked_days=={'2026-05-01'} and tab._excluded_days=={'2026-05-02'}
    assert not db.load_day_rules(first,'2026-05-01','2026-05-04')
    tab._save_draft();tab._generate_period()
    assert tab._locked_days=={'2026-05-01'} and tab._excluded_days=={'2026-05-02'}
    assert db.load_distribution_settings(first)==(8,12)
    original=dict(tab.days_data)
    errors=[]
    monkeypatch.setattr('ui.payroll_tab.messagebox.showerror',lambda *a:errors.append(a))
    tab.distribution_hours_var.set('30');tab._distribute_hours()
    assert errors and tab.days_data==original
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save')
    assert db.load_day_rules(first,'2026-05-01','2026-05-04')['2026-05-01']['locked']


def test_date_locks_do_not_leak_when_switching_employee(ui,monkeypatch):
    tab,db,first,second=ui
    select(tab,first);tab._generate_period()
    tab.tree.selection_set('2026-05-01');tab._toggle_day_rule('locked')
    monkeypatch.setattr('ui.payroll_tab.messagebox.showinfo',lambda *a:None)
    tab._save_draft()
    select(tab,second);tab._employee_changed()
    assert not tab._locked_days and not tab._excluded_days
    assert tab._distribution_settings()==(0,24)


def test_excluded_date_must_be_included_before_edit_or_lock(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    warnings=[]
    monkeypatch.setattr('ui.payroll_tab.messagebox.showwarning',lambda *a:warnings.append(a))
    monkeypatch.setattr('ui.payroll_tab.messagebox.showerror',lambda *a:warnings.append(a))
    tab.tree.selection_set('2026-05-01');tab._toggle_day_rule('excluded')
    tab._toggle_day_rule('locked')
    assert warnings and not tab._locked_days
    tab._editor=tk.Spinbox(tab.tree)
    tab._editor.delete(0,'end');tab._editor.insert(0,'8')
    tab._save_hours('2026-05-01')
    assert tab.days_data['2026-05-01']==0 and tab._editor is not None
    tab._cancel_hours_edit()
    tab._toggle_day_rule('excluded')
    assert not tab._excluded_days and tab.days_data['2026-05-01']==0


def test_fractional_pin_incompatible_total_keeps_entire_table(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab.to_entry.set_date(date(2026,5,2));tab._generate_period()
    tab._editor=tk.Spinbox(tab.tree)
    tab._editor.delete(0,'end');tab._editor.insert(0,'8.5')
    tab._save_hours('2026-05-01')
    tab.tree.selection_set('2026-05-01');tab._toggle_day_rule('locked')
    original=dict(tab.days_data)
    messages=[]
    monkeypatch.setattr('ui.payroll_tab.messagebox.showerror',lambda *a:messages.append(a))
    monkeypatch.setattr('ui.payroll_tab.messagebox.askyesno',lambda *a:True)
    tab.distribution_hours_var.set('18');tab._distribute_hours()
    assert messages and tab.days_data==original and tab._locked_days=={'2026-05-01'}
    tab.distribution_hours_var.set('18.5');tab._distribute_hours()
    assert tab.days_data['2026-05-01']==8.5 and tab.days_data['2026-05-02']==10


def test_existing_statement_open_or_cancel_never_writes(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save')
    pid=db.get_payrolls()[0]['id']
    tab.utilities_var.set('10')
    monkeypatch.setattr('ui.payroll_tab.choose_existing_payroll',lambda *a:None)
    assert tab._call_pdf('save') is None
    assert len(db.get_payrolls())==1 and tab.has_unsaved_changes()
    monkeypatch.setattr('ui.payroll_tab.choose_existing_payroll',lambda *a:('open',pid))
    monkeypatch.setattr('ui.payroll_tab.preview_payroll_pdf_from_history',lambda *a:'existing.pdf')
    assert tab._call_pdf('save')=='existing.pdf'
    assert not tab._last_pdf_saved and len(db.get_payrolls())==1 and tab.has_unsaved_changes()


def test_ui_explicit_correction_records_new_current_version(ui,monkeypatch):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save');first_pid=db.get_payrolls()[0]['id']
    tab.utilities_var.set('10')
    monkeypatch.setattr('ui.payroll_tab.choose_existing_payroll',lambda *a:('correct',[first_pid]))
    tab._call_pdf('save')
    assert len(db.get_payrolls())==2 and len(db.get_payrolls(current_only=True))==1
    assert db.get_payrolls()[0]['corrects']==str(first_pid)
    assert tab._last_pdf_saved and not tab.has_unsaved_changes()


def test_history_race_removes_only_newly_generated_pdf(ui,monkeypatch,tmp_path):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    pdf=tmp_path/'Payroll_unique_attempt.pdf'
    def competing_save(**kwargs):
        db.save_payroll(first,tab.days_data,tab.rate_mode.get(),'2026-05-01','2026-05-01')
        pdf.write_bytes(b'test')
        return str(pdf)
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',competing_save)
    with pytest.raises(ValueError,match='history changed'):tab._call_pdf('save')
    assert not pdf.exists() and len(db.get_payrolls())==1 and tab.has_unsaved_changes()


@pytest.mark.parametrize('field',['rate','name','bank'])
def test_employee_card_refresh_marks_changed_calculation_unsaved(ui,monkeypatch,field):
    tab,db,first,_=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save')
    before=dict(db.get_payrolls()[0]);hours=dict(tab.days_data)
    if field=='rate':db.update_employee_rate(first,30)
    elif field=='name':db.update_employee_name(first,'Renamed')
    else:db.update_employee_bank(first,True,'Changed bank','TEST','TEST')
    tab.refresh_employees()
    assert tab.has_unsaved_changes() and tab.save_status_var.get()=='Unsaved changes'
    assert tab.days_data==hours and dict(db.get_payrolls()[0])==before


def test_unrelated_employee_refresh_keeps_saved_status(ui,monkeypatch):
    tab,db,first,second=ui
    select(tab,first);tab._generate_period()
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save');db.update_employee_rate(second,50);tab.refresh_employees()
    assert not tab.has_unsaved_changes() and tab.save_status_var.get()=='Payroll saved'


def test_searching_employees_clears_stale_details(ui):
    from ui.employees_tab import EmployeesTab
    tab,db,first,_=ui
    editor=EmployeesTab(tab.winfo_toplevel(),db)
    editor.tree.selection_set(str(first));editor._on_select(None)
    assert editor.selected_id==first and editor.name_var.get()
    editor.search_var.set('no matching employee')
    tab.winfo_toplevel().update()
    assert editor.selected_id is None
    assert editor.name_var.get()=='' and editor.bank_var.get()==''
    assert not editor.tree.get_children()
    editor.destroy()


def test_employee_search_cancel_keeps_edits_and_active_filter(ui,monkeypatch):
    from ui.employees_tab import EmployeesTab
    tab,db,first,_=ui;editor=EmployeesTab(tab.winfo_toplevel(),db)
    editor.tree.selection_set(str(first));editor._on_select(None)
    editor.name_var.set('Unsaved name')
    monkeypatch.setattr('ui.employees_tab.messagebox.askyesno',lambda *a,**k:False)
    editor.search_var.set('another query')
    assert editor.search_var.get()=='' and editor.selected_id==first
    assert editor.name_var.get()=='Unsaved name' and len(editor.tree.get_children())==2
    monkeypatch.setattr('ui.employees_tab.messagebox.askyesno',lambda *a,**k:True)
    editor.search_var.set('no match')
    assert not editor.tree.get_children() and editor.name_var.get()==''
    editor._load()
    assert not editor.tree.get_children()
    editor.destroy()


def test_employee_switch_cancel_and_clear_preserve_or_discard_edits(ui,monkeypatch):
    from ui.employees_tab import EmployeesTab
    tab,db,first,second=ui;editor=EmployeesTab(tab.winfo_toplevel(),db)
    editor.tree.selection_set(str(first));editor._on_select(None)
    editor.bank_var.set('Unsaved bank')
    monkeypatch.setattr('ui.employees_tab.messagebox.askyesno',lambda *a,**k:False)
    editor.tree.selection_set(str(second));editor._on_select(None)
    assert editor.tree.selection()==(str(first),) and editor.selected_id==first
    assert editor.bank_var.get()=='Unsaved bank'
    editor._request_clear()
    assert editor.bank_var.get()=='Unsaved bank'
    monkeypatch.setattr('ui.employees_tab.messagebox.askyesno',lambda *a,**k:True)
    editor._request_clear()
    assert editor.selected_id is None and not editor.has_unsaved_changes()
    editor.destroy()


def test_archive_warning_mentions_unsaved_payroll_and_uses_saved_name(ui,monkeypatch):
    from ui.employees_tab import EmployeesTab
    from app import PayrollApp
    from types import SimpleNamespace
    tab,db,first,_=ui;select(tab,first);tab._generate_period()
    owner=SimpleNamespace(payroll_tab=tab)
    editor=EmployeesTab(tab.winfo_toplevel(),db,archive_warning=lambda eid:PayrollApp._archive_warning(owner,eid))
    editor.tree.selection_set(str(first));editor._on_select(None)
    editor.name_var.set('Unsaved replacement name')
    questions=[]
    monkeypatch.setattr('ui.employees_tab.messagebox.askyesno',lambda title,text,**k:questions.append(text) or False)
    editor._delete()
    assert 'Unsaved Payroll' in questions[0] and 'Unsaved replacement name' not in questions[0]
    assert not db.get_employee(first)['archived'] and tab.days_data
    editor.destroy()


@pytest.mark.parametrize('external_change',['bank','archive'])
def test_external_employee_change_cannot_be_overwritten_by_stale_form(ui,monkeypatch,external_change):
    from ui.employees_tab import EmployeesTab
    tab,db,first,_=ui;editor=EmployeesTab(tab.winfo_toplevel(),db)
    editor.tree.selection_set(str(first));editor._on_select(None)
    editor.rate_var.set('25')
    if external_change=='bank':db.update_employee_bank(first,True,'External bank','NEW','NEW')
    else:db.delete_employee(first)
    errors=[]
    monkeypatch.setattr('ui.employees_tab.messagebox.showerror',lambda *a,**k:errors.append(a))
    editor._update()
    assert errors
    if external_change=='bank':assert db.get_employee(first)['bank']=='External bank'
    else:assert db.get_employee(first)['archived']
    assert db.get_employee(first)['rate']==20 and editor.has_unsaved_changes()
    editor.destroy()


def test_fixed_rate_ignores_unrelated_custom_rate_change(ui,monkeypatch):
    tab,db,first,_=ui;select(tab,first);tab._generate_period();tab.rate_mode.set('fixed')
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:'synthetic.pdf')
    tab._call_pdf('save');db.update_employee_rate(first,50);tab.refresh_employees()
    assert not tab.has_unsaved_changes() and tab.save_status_var.get()=='Payroll saved'


def test_invalid_month_restores_filter_matching_displayed_summary(ui,monkeypatch):
    from ui.monthly_summary import MonthlySummary
    tab,db,first,_=ui
    db.save_payroll(first,{'2026-05-01':8},'custom','2026-05-01','2026-05-01')
    view=MonthlySummary(tab.winfo_toplevel(),db)
    view.month.set('2026-05');view._load()
    errors=[]
    monkeypatch.setattr('ui.monthly_summary.messagebox.showerror',lambda *a,**k:errors.append(a))
    view.month.set('2026-13');view._load()
    assert errors and view.month.get()=='2026-05' and view.data['totals']['net']==160
    view.destroy()


def test_close_cancel_keeps_unsaved_employee_details(ui,monkeypatch):
    from app import PayrollApp
    from ui.employees_tab import EmployeesTab
    from types import SimpleNamespace
    tab,db,first,_=ui;editor=EmployeesTab(tab.winfo_toplevel(),db)
    editor.name_var.set('Unsaved new employee')
    closed=[]
    owner=SimpleNamespace(payroll_tab=tab,employees_tab=editor,winfo_children=lambda:[],
        db=SimpleNamespace(close=lambda:closed.append(True)),destroy=lambda:closed.append(True))
    monkeypatch.setattr('app.messagebox.askyesno',lambda *a,**k:False)
    PayrollApp._close(owner)
    assert not closed and editor.name_var.get()=='Unsaved new employee'
    editor.destroy()


def test_payroll_bank_info_switches_refreshes_and_masks(ui,monkeypatch):
    tab,db,first,second=ui
    db.update_employee_bank(first,True,'Example Bank','SECRET-1234','SECRET')
    db.update_employee_bank(second,False,None,None,None)
    tab.refresh_employees();select(tab,first);tab._employee_changed()
    assert tab.bank_account_var.get()=='Bank account: Yes'
    assert '1234' in tab.bank_detail_var.get() and 'SECRET' not in tab.bank_detail_var.get()
    monkeypatch.setattr('ui.payroll_tab.messagebox.askyesno',lambda *a,**k:True)
    select(tab,second);tab._employee_changed()
    assert tab.bank_account_var.get()=='Bank account: No'
    assert '1234' not in tab.bank_detail_var.get()
    e=db.get_employee(second)
    db.update_employee(second,e['name'],e['rate'],bank_account_state='unknown')
    tab.refresh_employees()
    assert tab.bank_account_var.get()=='Bank account: Not specified'


def test_editor_account_choice_saves_and_no_account_pdf_omits_details(ui,monkeypatch):
    from ui.employees_tab import EmployeesTab
    tab,db,first,_=ui;editor=EmployeesTab(tab.winfo_toplevel(),db)
    editor.tree.selection_set(str(first));editor._on_select(None)
    editor.bank_var.set('Example Bank');editor.iban_var.set('TEST-1234');editor.bank_account_var.set('No')
    editor._update()
    assert db.get_employee(first)['bank_account_state']=='no' and db.get_employee(first)['iban']=='TEST-1234'
    tab.refresh_employees();select(tab,first);tab._generate_period()
    arguments=[]
    monkeypatch.setattr('ui.payroll_tab.generate_payroll_pdf',lambda **kw:arguments.append(kw) or 'synthetic.pdf')
    tab._call_pdf('preview')
    assert arguments[0]['bank_name'] is None and arguments[0]['iban'] is None
    editor.destroy()


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
