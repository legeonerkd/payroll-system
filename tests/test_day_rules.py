import sqlite3

import pytest

from database.db import Database, SCHEMA_VERSION


def test_rules_settings_reopen_and_employee_period_isolation(tmp_path):
    path=tmp_path/'test.db'
    db=Database(path)
    first=db.add_employee('Same name',15);second=db.add_employee('Same name',20)
    rules={'2026-05-01':{'locked':True,'excluded':False},'2026-05-02':{'locked':False,'excluded':True}}
    db.save_period_hours(first,{'2026-05-01':8.5,'2026-05-02':0},rules,(8,12))
    db.save_period_hours(first,{'2026-06-01':9},{'2026-06-01':{'locked':True,'excluded':False}},(8,12))
    db.close();db=Database(path)
    assert db.load_day_rules(first,'2026-05-01','2026-05-02')==rules
    assert db.load_distribution_settings(first)==(8,12)
    assert db.load_distribution_settings(second)==(0,24)
    assert not db.load_day_rules(second,'2026-05-01','2026-06-01')
    db.save_period_hours(first,{'2026-05-01':10,'2026-05-02':10},{},(7,11))
    assert not db.load_day_rules(first,'2026-05-01','2026-05-02')
    assert db.load_day_rules(first,'2026-06-01','2026-06-01')['2026-06-01']['locked']
    db.close()


def test_rules_and_hours_rollback_together(tmp_path):
    db=Database(tmp_path/'test.db');eid=db.add_employee('Synthetic',15)
    rules={'2026-05-01':{'locked':True,'excluded':False}}
    db.save_period_hours(eid,{'2026-05-01':8},rules,(8,12))
    db.conn.executescript("CREATE TRIGGER fail_settings BEFORE UPDATE ON distribution_settings BEGIN SELECT RAISE(ABORT,'test rollback'); END;")
    with pytest.raises(sqlite3.IntegrityError):
        db.save_period_hours(eid,{'2026-05-01':10},{},(10,12))
    assert db.load_hours(eid,'2026-05-01','2026-05-01')[0]['hours']==8
    assert db.load_day_rules(eid,'2026-05-01','2026-05-01')==rules
    assert db.load_distribution_settings(eid)==(8,12)
    db.close()


def test_excluded_hours_cannot_be_silently_overwritten():
    db=Database(':memory:');eid=db.add_employee('Synthetic',15)
    rules={'2026-05-01':{'locked':False,'excluded':True}}
    db.save_period_hours(eid,{'2026-05-01':0},rules,(0,24))
    with pytest.raises(ValueError): db.save_hours(eid,'2026-05-01',8)
    with pytest.raises(ValueError): db.save_period_hours(eid,{'2026-05-01':8},rules,(0,24))
    assert db.load_hours(eid,'2026-05-01','2026-05-01')[0]['hours']==0
    db.save_period_hours(eid,{'2026-05-01':8},{},(0,24))
    assert not db.load_day_rules(eid,'2026-05-01','2026-05-01')
    db.close()


def test_schema_three_upgrade_preserves_all_original_rows_and_backup(tmp_path):
    path=tmp_path/'v3.db';db=Database(path)
    eid=db.add_employee('Synthetic',15,'Test bank','TEST','TEST')
    db.save_payroll(eid,{'2026-05-01':8.5},'custom','2026-05-01','2026-05-01',utilities=12,rental=30)
    tables=('employees','work_hours','payrolls','payroll_days')
    before={t:[tuple(r) for r in db.conn.execute('SELECT * FROM '+t)] for t in tables}
    db.conn.executescript('DROP TABLE hour_day_rules; DROP TABLE distribution_settings; PRAGMA user_version=3;')
    db.close();db=Database(path)
    assert db.conn.execute('PRAGMA user_version').fetchone()[0]==SCHEMA_VERSION
    assert db.conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.conn.execute('PRAGMA foreign_key_check').fetchall()
    assert before=={t:[tuple(r) for r in db.conn.execute('SELECT * FROM '+t)] for t in tables}
    backup=sqlite3.connect(db.last_backup)
    assert backup.execute('PRAGMA user_version').fetchone()[0]==3
    assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    backup.close();db.close()
