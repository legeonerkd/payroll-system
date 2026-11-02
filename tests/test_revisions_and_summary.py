from decimal import Decimal
import pytest
from database.db import Database,PayrollConflictError


@pytest.fixture
def ledger():
    db=Database(':memory:');eid=db.add_employee('Synthetic',15)
    yield db,eid
    db.close()


def save(db,eid,hours=8,**kwargs):
    return db.save_payroll(eid,{'2026-11-02':hours},'custom','2026-11-02','2026-11-02',**kwargs)


def test_changed_exact_period_requires_explicit_correction(ledger):
    db,eid=ledger;pid=save(db,eid)
    assert save(db,eid)==pid
    with pytest.raises(PayrollConflictError):save(db,eid,9)
    assert len(db.get_payrolls())==1
    assert db.load_hours(eid,'2026-11-02','2026-11-02')[0]['hours']==8


def test_correction_chain_preserves_original_and_can_revert_values(ledger):
    db,eid=ledger;first=save(db,eid,pdf_path='original.pdf')
    before=tuple(db.conn.execute('SELECT * FROM payrolls WHERE id=?',(first,)).fetchone())
    old_days=[tuple(r) for r in db.get_payroll_full(first)[1]]
    second=save(db,eid,9,replaces_ids=[first])
    third=save(db,eid,8,replaces_ids=[second])
    assert first!=third and save(db,eid)==third
    assert tuple(db.conn.execute('SELECT * FROM payrolls WHERE id=?',(first,)).fetchone())==before
    assert [tuple(r) for r in db.get_payroll_full(first)[1]]==old_days
    all_rows={r['id']:r for r in db.get_payrolls()}
    assert all_rows[first]['superseded_by']==second and all_rows[second]['superseded_by']==third
    assert all_rows[third]['corrects']==str(second)
    assert [r['id'] for r in db.get_payrolls(current_only=True)]==[third]
    assert db.get_month_summary(2026,11)['totals']['net']==Decimal('120')


def test_stale_or_wrong_correction_cannot_replace_another_statement(ledger):
    db,eid=ledger;first=save(db,eid)
    second=save(db,eid,9,replaces_ids=[first])
    for kwargs in ({'replaces_ids':[first]}, {'expected_current_ids':[first]}, {'replaces_ids':[999]}):
        with pytest.raises(PayrollConflictError):save(db,eid,10,**kwargs)
    assert len(db.get_payrolls())==2 and db.get_payrolls(current_only=True)[0]['id']==second


def test_overlap_requires_confirmation_and_is_flagged_in_summary(ledger):
    db,eid=ledger;save(db,eid)
    options=dict(emp_id=eid,values={'2026-11-03':4},rate_mode='custom',start='2026-11-01',end='2026-11-04')
    with pytest.raises(PayrollConflictError):db.save_payroll(**options)
    pid=db.save_payroll(**options,allow_overlap=True)
    summary=db.get_month_summary(2026,11)
    assert len(summary['overlap_ids'])==2 and pid in summary['included_ids']
    assert summary['totals']['net']==180


def test_period_end_month_and_snapshot_rates_and_drafts(ledger):
    db,eid=ledger
    pid=db.save_payroll(eid,{'2026-10-25':8,'2026-11-02':4},'custom','2026-10-20','2026-11-05',utilities=10,rental=20)
    db.update_employee_rate(eid,100)
    db.save_hours(eid,'2026-11-02',5)
    db.save_hours(eid,'2026-11-15',2)
    october=db.get_month_summary(2026,10)
    november=db.get_month_summary(2026,11)
    assert not october['included_ids'] and october['totals']['net']==0
    assert november['included_ids']==[pid]
    assert november['totals']['hours']==12 and november['totals']['gross']==180
    assert november['totals']['deductions']==30 and november['totals']['net']==150
    assert november['totals']['draft_hours']==7
    db.delete_employee(eid)
    assert db.get_month_summary(2026,11)['totals']['net']==150


def test_legacy_duplicate_period_excluded_until_explicitly_resolved(ledger):
    db,eid=ledger;first=save(db,eid)
    original=dict(db.conn.execute('SELECT * FROM payrolls WHERE id=?',(first,)).fetchone())
    original.pop('id');original['fingerprint']='legacy-other';original['net_amount']=99
    with db.transaction():
        keys=','.join(original);marks=','.join('?' for _ in original)
        second=db.conn.execute(f'INSERT INTO payrolls({keys}) VALUES({marks})',tuple(original.values())).lastrowid
        db.conn.execute('INSERT INTO payroll_content_keys VALUES(?,?)',(second,'legacy-other'))
    summary=db.get_month_summary(2026,11)
    assert set(summary['review_ids'])=={first,second} and summary['totals']['net']==0
    with pytest.raises(PayrollConflictError):save(db,eid,9,replaces_ids=[first])
    corrected=save(db,eid,9,replaces_ids=[first,second])
    summary=db.get_month_summary(2026,11)
    assert summary['included_ids']==[corrected] and not summary['review_ids']
    assert summary['totals']['net']==135


def test_schema_four_upgrade_preserves_original_rows(tmp_path):
    import sqlite3
    from database.db import SCHEMA_VERSION
    path=tmp_path/'v4.db';db=Database(path);eid=db.add_employee('Synthetic',15)
    save(db,eid,pdf_path='original.pdf')
    tables=('employees','work_hours','payrolls','payroll_days')
    before={t:[tuple(r) for r in db.conn.execute('SELECT * FROM '+t)] for t in tables}
    db.conn.executescript('DROP TABLE payroll_revision_links; DROP TABLE payroll_content_keys; PRAGMA user_version=4;')
    db.close();db=Database(path)
    assert before=={t:[tuple(r) for r in db.conn.execute('SELECT * FROM '+t)] for t in tables}
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    old=sqlite3.connect(db.last_backup)
    assert old.execute('PRAGMA user_version').fetchone()[0]==4
    old.close();db.close()
