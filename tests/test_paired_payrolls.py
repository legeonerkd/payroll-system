from decimal import Decimal
from pathlib import Path
import pytest
from pypdf import PdfReader
from database.db import Database,PayrollConflictError
from database.db import SCHEMA_VERSION
from services import paired_payroll_service as pairs
from core.rental import utilities_for_rate

HOURS={'2026-11-02':8};START=END='2026-11-02'


@pytest.fixture
def pair_db():
    db=Database(':memory:');eid=db.add_employee('Synthetic',15,bank_account_state='no',rental_amount=50)
    yield db,eid
    db.close()


def save_pair(db,eid,utilities=4,**options):
    employee=db.get_employee(eid)
    plans=pairs.pair_plans(db,employee,HOURS,START,END,utilities)
    return pairs.save_payroll_pair(db,employee,HOURS,START,END,utilities,plans=plans,day_rules={},settings=(0,14),**options)


@pytest.mark.parametrize('state,target',[('yes','fixed'),('no','custom'),('unknown',None)])
def test_pair_produces_two_actual_pdfs_and_routes_each_deduction_once(pair_db,tmp_path,monkeypatch,state,target):
    db,eid=pair_db
    db.update_employee(eid,'Synthetic',8,bank_account_state=state)
    monkeypatch.setenv('PAYROLL_OUTPUT_DIR',str(tmp_path))
    result=save_pair(db,eid)
    assert len(set(result['files'].values()))==2
    for mode,path in result['files'].items():
        assert '_'+mode+'_' in Path(path).name
        reader=PdfReader(path);assert len(reader.pages)==1
        text=reader.pages[0].extract_text()
        assert 'Rental deduction: '+('50.00' if mode==target else '0.00') in text
        assert 'Utilities deduction: '+('4.00' if mode==target else '0.00') in text
    current=db.get_payrolls(current_only=True)
    assert len(current)==2 and {p['rate_mode'] for p in current}=={'fixed','custom'}
    assert sum(p['rental'] for p in current)==(50 if target else 0)
    assert sum(p['utilities'] for p in current)==(4 if target else 0)
    summary=db.get_month_summary(2026,11)
    assert summary['totals']['hours']==8 and summary['totals']['gross']==128
    assert summary['totals']['net']==(74 if target else 128)
    assert not summary['review_ids'] and not summary['overlap_ids']


def fake_generator(tmp_path,monkeypatch):
    generated=[]
    def generate(**kwargs):
        path=tmp_path/f"Payroll_{len(generated)}_{kwargs['rate_mode']}.pdf"
        path.write_bytes(b'test');generated.append(path);return str(path)
    monkeypatch.setattr(pairs,'generate_payroll_pdf',generate)
    return generated


def test_account_appears_both_current_parts_move_deductions_without_changing_originals(pair_db,tmp_path,monkeypatch):
    db,eid=pair_db;fake_generator(tmp_path,monkeypatch)
    first=save_pair(db,eid)
    originals={p['id']:dict(p) for p in db.get_payrolls()}
    old_days={pid:[dict(r) for r in db.get_payroll_full(pid)[1]] for pid in originals}
    assert originals[first['ids']['custom']]['utilities']==4
    db.update_employee(eid,'Renamed',16,bank='Example Bank',iban='TEST1234',bank_account_state='yes')
    second=save_pair(db,eid)
    current={p['rate_mode']:p for p in db.get_payrolls(current_only=True)}
    assert current['fixed']['rental']==50 and current['fixed']['utilities']==4
    assert current['custom']['rental']==current['custom']['utilities']==0
    assert current['fixed']['net_amount']==10 and current['custom']['net_amount']==128
    for mode in pairs.MODES:
        assert current[mode]['corrects']==str(first['ids'][mode])
        p,_=db.get_payroll_full(first['ids'][mode])
        for key,value in originals[p['id']].items():
            if key not in ('corrects','superseded_by'):assert p[key]==value
        assert [dict(r) for r in db.get_payroll_full(p['id'])[1]]==old_days[p['id']]
    summary=db.get_month_summary(2026,11)
    assert summary['totals']['deductions']==54 and summary['totals']['hours']==8
    assert set(summary['included_ids'])==set(second['ids'].values())


def test_second_pdf_failure_leaves_no_first_pdf_or_payroll(pair_db,tmp_path,monkeypatch):
    db,eid=pair_db;generated=[]
    def generate(**kw):
        if kw['rate_mode']=='custom':raise OSError('Synthetic PDF failure')
        path=tmp_path/'Payroll_first.pdf';path.write_bytes(b'test');generated.append(path);return str(path)
    monkeypatch.setattr(pairs,'generate_payroll_pdf',generate)
    with pytest.raises(OSError):save_pair(db,eid)
    assert not any(p.exists() for p in generated)
    assert not db.get_payrolls() and not db.get_all_hours()


def test_second_database_save_failure_rolls_back_both_and_removes_new_files(pair_db,tmp_path,monkeypatch):
    db,eid=pair_db;generated=fake_generator(tmp_path,monkeypatch)
    original_save=db.save_payroll
    def fail_second(*args,**kw):
        if args[2]=='custom':raise RuntimeError('Synthetic save failure')
        return original_save(*args,**kw)
    monkeypatch.setattr(db,'save_payroll',fail_second)
    with pytest.raises(RuntimeError):save_pair(db,eid)
    assert not db.get_payrolls() and not db.get_all_hours()
    assert not any(p.exists() for p in generated)


def test_card_update_during_pdf_generation_is_detected_and_new_files_removed(pair_db,tmp_path,monkeypatch):
    db,eid=pair_db;generated=[]
    def generate(**kw):
        path=tmp_path/f"Payroll_{kw['rate_mode']}.pdf";path.write_bytes(b'test');generated.append(path)
        if kw['rate_mode']=='custom':db.update_employee(eid,'Synthetic',15,bank_account_state='yes')
        return str(path)
    monkeypatch.setattr(pairs,'generate_payroll_pdf',generate)
    with pytest.raises(PayrollConflictError,match='Employee details changed'):save_pair(db,eid)
    assert not db.get_payrolls() and not any(p.exists() for p in generated)


def test_opposite_modes_do_not_replace_each_other_and_mismatched_hours_need_review(pair_db):
    db,eid=pair_db
    fixed=db.save_payroll(eid,HOURS,'fixed',START,END)
    custom=db.save_payroll(eid,{'2026-11-02':9},'custom',START,END)
    assert len(db.get_payrolls(current_only=True))==2
    summary=db.get_month_summary(2026,11)
    assert set(summary['review_ids'])=={fixed,custom}
    assert summary['totals']['net']==0
    with pytest.raises(PayrollConflictError):
        db.save_payroll(eid,HOURS,'fixed',START,END,replaces_ids=[custom])


def test_pair_failure_during_correction_preserves_original_current_pair(pair_db,tmp_path,monkeypatch):
    db,eid=pair_db;generated=fake_generator(tmp_path,monkeypatch)
    first=save_pair(db,eid);before=[dict(p) for p in db.get_payrolls()]
    db.conn.execute("CREATE TRIGGER fail_custom BEFORE INSERT ON payrolls WHEN NEW.rate_mode='custom' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END;")
    with pytest.raises(Exception,match='synthetic failure'):save_pair(db,eid,utilities=7)
    assert [dict(p) for p in db.get_payrolls()]==before
    assert all(Path(path).exists() for path in first['files'].values())
    assert not any(p.exists() for p in generated[2:])


def test_history_changes_during_generation_are_not_overwritten(pair_db,tmp_path,monkeypatch):
    db,eid=pair_db;generated=[]
    def generate(**kw):
        path=tmp_path/f"Payroll_{kw['rate_mode']}.pdf";path.write_bytes(b'test');generated.append(path)
        if kw['rate_mode']=='custom':db.save_payroll(eid,HOURS,'fixed',START,END)
        return str(path)
    monkeypatch.setattr(pairs,'generate_payroll_pdf',generate)
    with pytest.raises(PayrollConflictError,match='history changed'):save_pair(db,eid)
    assert len(db.get_payrolls())==1 and not any(p.exists() for p in generated)


def test_double_charged_legacy_pair_is_excluded_pending_review(pair_db):
    db,eid=pair_db
    fixed=db.save_payroll(eid,HOURS,'fixed',START,END,utilities=4)
    custom=db.save_payroll(eid,HOURS,'custom',START,END,utilities=4)
    summary=db.get_month_summary(2026,11)
    assert set(summary['review_ids'])=={fixed,custom} and summary['totals']['net']==0


def test_deductions_split_across_both_parts_also_need_review(pair_db):
    db,eid=pair_db
    fixed=db.save_payroll(eid,HOURS,'fixed',START,END,rental=50)
    custom=db.save_payroll(eid,HOURS,'custom',START,END,utilities=4)
    assert set(db.get_month_summary(2026,11)['review_ids'])=={fixed,custom}


def test_different_overlapping_periods_are_not_treated_as_a_pair(pair_db):
    db,eid=pair_db
    fixed=db.save_payroll(eid,HOURS,'fixed',START,END)
    with pytest.raises(PayrollConflictError):
        db.save_payroll(eid,{'2026-11-03':4},'custom','2026-11-01','2026-11-04')
    custom=db.save_payroll(eid,{'2026-11-03':4},'custom','2026-11-01','2026-11-04',allow_overlap=True)
    assert set(db.get_month_summary(2026,11)['overlap_ids'])=={fixed,custom}


def test_schema_seven_upgrade_preserves_all_original_rows_and_backup(tmp_path):
    import sqlite3
    path=tmp_path/'version7.db';db=Database(path)
    eid=db.add_employee('Synthetic',15,bank_account_state='no',rental_amount=50)
    db.save_payroll(eid,HOURS,'custom',START,END,rental=50,utilities=4)
    tables=('employees','work_hours','payrolls','payroll_days','payroll_content_keys','payroll_revision_links')
    before={table:[tuple(row) for row in db.conn.execute('SELECT * FROM '+table)] for table in tables}
    db.conn.executescript('DROP TABLE payroll_pairs; PRAGMA user_version=7;');db.close()
    db=Database(path)
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION==8
    assert before=={table:[tuple(row) for row in db.conn.execute('SELECT * FROM '+table)] for table in tables}
    backup=sqlite3.connect(db.last_backup)
    assert backup.execute('PRAGMA user_version').fetchone()[0]==7
    assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    backup.close();db.close()


def test_legacy_opposite_rates_are_not_silently_reclassified_as_an_intentional_pair(pair_db):
    db,eid=pair_db
    fixed=db.save_payroll(eid,HOURS,'fixed',START,END)
    custom=db.save_payroll(eid,HOURS,'custom',START,END)
    summary=db.get_month_summary(2026,11)
    assert set(summary['review_ids'])=={fixed,custom} and summary['totals']['net']==0
    assert not db.conn.execute('SELECT * FROM payroll_pairs').fetchall()


@pytest.mark.parametrize('state,target',[('yes','fixed'),('no','custom'),('unknown',None)])
def test_utilities_have_one_target_and_zero_is_valid(state,target):
    e={'bank_account_state':state}
    assert sum(utilities_for_rate(e,mode,'4.50') for mode in pairs.MODES)==(Decimal('4.50') if target else 0)
    assert all(utilities_for_rate(e,mode,0)==0 for mode in pairs.MODES)
    with pytest.raises(ValueError):utilities_for_rate(e,'fixed',-1)
