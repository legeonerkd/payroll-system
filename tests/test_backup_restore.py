from pathlib import Path
import sqlite3
import hashlib
import pytest
from database.db import Database,SCHEMA_VERSION
from core.backup import backup_db,verify_database,prepare_restore,install_restore


def populated(path,name):
    db=Database(path);eid=db.add_employee(name,15)
    db.save_payroll(eid,{'2026-11-02':8},'custom','2026-11-02','2026-11-02')
    db.save_period_hours(eid,{'2026-11-02':8},{'2026-11-02':{'locked':True,'excluded':False}},(8,12))
    return db


def test_round_trip_restores_snapshots_rules_and_retains_previous_database(tmp_path):
    path=tmp_path/'live.db';db=populated(path,'Original')
    external=tmp_path/'external'/'copy.db';backup_db(path,external)
    digest=hashlib.sha256(external.read_bytes()).hexdigest()
    db.add_employee('Newer employee',20);db.close()
    with prepare_restore(path,external) as (staged,manifest):
        assert manifest['employees']==1 and manifest['schema']==SCHEMA_VERSION
        protected=install_restore(path,staged)
    db=Database(path,create_backup=False)
    assert [e['name'] for e in db.get_employees()]==['Original']
    assert db.get_payrolls()[0]['net_amount']==120
    assert db.load_day_rules(1,'2026-11-02','2026-11-02')['2026-11-02']['locked']
    assert db.load_distribution_settings(1)==(8,12)
    assert verify_database(protected)['employees']==2
    assert hashlib.sha256(external.read_bytes()).hexdigest()==digest
    db.close()


def test_readonly_validation_and_corrupt_or_future_backups_never_replace_live(tmp_path):
    path=tmp_path/'live.db';db=populated(path,'Original');db.close()
    bad=tmp_path/'bad.db';bad.write_bytes(b'not a sqlite database')
    with pytest.raises((ValueError,sqlite3.DatabaseError)):
        with prepare_restore(path,bad):pytest.fail('Invalid backup was accepted')
    future=tmp_path/'future.db';backup_db(path,future)
    conn=sqlite3.connect(future);conn.execute('PRAGMA user_version=999');conn.close()
    with pytest.raises(ValueError,match='newer'):
        with prepare_restore(path,future):pytest.fail('Future backup was accepted')
    assert verify_database(path)['employees']==1
    with pytest.raises(ValueError):
        with prepare_restore(path,path):pytest.fail('Live file accepted as backup')


def test_backup_does_not_overwrite_existing_file(tmp_path):
    path=tmp_path/'live.db';db=populated(path,'Original')
    destination=tmp_path/'keep.db';destination.write_bytes(b'keep me')
    with pytest.raises(FileExistsError):backup_db(path,destination)
    assert destination.read_bytes()==b'keep me'
    db.close()


def test_backup_includes_committed_wal_and_restore_is_atomic(tmp_path):
    path=tmp_path/'live.db';db=populated(path,'Original')
    db.conn.execute('PRAGMA journal_mode=WAL')
    db.add_employee('WAL employee',20)
    copy=backup_db(path)
    assert verify_database(copy)['employees']==2
    db.add_employee('Later',25);db.close()
    with prepare_restore(path,copy) as (staged,info):install_restore(path,staged)
    assert verify_database(path)['employees']==2


def test_older_schema_migrates_only_the_staged_copy(tmp_path):
    live=tmp_path/'live.db';db=populated(live,'Live');db.close()
    old=tmp_path/'old.db';db=populated(old,'Backup')
    db.conn.executescript('DROP TABLE payroll_revision_links; DROP TABLE payroll_content_keys; PRAGMA user_version=4;')
    db.close();before=hashlib.sha256(old.read_bytes()).hexdigest()
    with prepare_restore(live,old) as (staged,info):
        assert info['schema']==SCHEMA_VERSION and info['payrolls']==1
        assert verify_database(live)['employees']==1
    assert hashlib.sha256(old.read_bytes()).hexdigest()==before
    assert verify_database(old)['schema']==4


def test_failed_post_restore_verification_recovers_previous_database(tmp_path,monkeypatch):
    import core.backup as service
    live=tmp_path/'live.db';db=populated(live,'Live');db.close()
    other=tmp_path/'other.db';db=populated(other,'Backup');db.add_employee('Extra',25);db.close()
    with prepare_restore(live,other) as (staged,info):
        original=service.verify_database;calls=[]
        def verify(path,maximum_version=None):
            if Path(path).resolve()==live.resolve():
                calls.append(path)
                if len(calls)==1:raise ValueError('Synthetic verification failure')
            return original(path,maximum_version)
        monkeypatch.setattr(service,'verify_database',verify)
        with pytest.raises(RuntimeError,match='recovered'):install_restore(live,staged)
    db=Database(live,create_backup=False)
    assert [e['name'] for e in db.get_employees()]==['Live']
    db.close()


def test_external_backup_location_can_be_recalled(tmp_path):
    from core.backup import latest_backup,remember_backup_location
    live=tmp_path/'live.db';db=populated(live,'Live');db.close()
    external=tmp_path/'separate-folder'/'saved.db'
    backup_db(live,external);remember_backup_location(live,external)
    assert latest_backup(live)==external
    assert verify_database(latest_backup(live))['employees']==1
