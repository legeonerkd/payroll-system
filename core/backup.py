from datetime import datetime
from pathlib import Path
import sqlite3
import os
import shutil
import json
from tempfile import mkstemp,TemporaryDirectory
from contextlib import contextmanager


def verify_database(path,maximum_version=None):
    path=Path(path).resolve()
    if not path.is_file():raise ValueError('Database file not found')
    source=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        source.execute('PRAGMA query_only=ON')
        if source.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('Database integrity check failed')
        if source.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Database contains broken references')
        version=source.execute('PRAGMA user_version').fetchone()[0]
        if maximum_version is not None and version>maximum_version:
            raise ValueError('This backup was created by a newer application version')
        tables={r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        hours='work_hours' if 'work_hours' in tables else 'daily_hours'
        if 'employees' not in tables or hours not in tables:
            raise ValueError('This file is not a PayrollSystem database')
        if not {'id','name','rate'}.issubset({r[1] for r in source.execute('PRAGMA table_info(employees)')}):
            raise ValueError('Unsupported employee table')
        if not {'employee_id','work_date','hours'}.issubset({r[1] for r in source.execute('PRAGMA table_info('+hours+')')}):
            raise ValueError('Unsupported hours table')
        return {'schema':version,'employees':source.execute('SELECT COUNT(*) FROM employees').fetchone()[0],
                'hours':source.execute('SELECT COUNT(*) FROM '+hours).fetchone()[0],
                'payrolls':source.execute('SELECT COUNT(*) FROM payrolls').fetchone()[0] if 'payrolls' in tables else 0}
    finally:source.close()


def backup_db(db_path,destination=None):
    """Use SQLite's online backup API, including committed WAL contents."""
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return None
    backup_dir = Path(destination).resolve().parent if destination else db_path.parent / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = Path(destination).resolve() if destination else backup_dir / f'payroll_backup_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
    if dst==db_path:raise ValueError('Choose a different file for the backup')
    if dst.exists():raise FileExistsError('A file already exists at that location. Choose a new backup name.')
    fd,temporary=mkstemp(prefix='payroll-copy-',suffix='.db',dir=backup_dir)
    os.close(fd)
    source = None
    target = None
    created=False
    try:
        source = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)
        target = sqlite3.connect(temporary)
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup integrity check failed')
        target.close()
        with dst.open('xb') as output,open(temporary,'rb') as prepared:
            created=True
            shutil.copyfileobj(prepared,output)
            output.flush();os.fsync(output.fileno())
        verify_database(dst)
    except Exception:
        if created:dst.unlink(missing_ok=True)
        raise
    finally:
        if target is not None:target.close()
        if source is not None:source.close()
        Path(temporary).unlink(missing_ok=True)
    return dst


def remember_backup_location(db_path,backup_path):
    location=Path(db_path).resolve().parent/'backup-location.json'
    temporary=location.with_suffix('.tmp')
    temporary.write_text(json.dumps({'path':str(Path(backup_path).resolve())}),encoding='utf-8')
    os.replace(temporary,location)


def latest_backup(db_path):
    folder=Path(db_path).resolve().parent
    files=list((folder/'backups').glob('payroll_backup_*.db'))
    try:
        external=Path(json.loads((folder/'backup-location.json').read_text(encoding='utf-8'))['path'])
        if external.is_file():files.append(external)
    except (OSError,ValueError,KeyError,TypeError):pass
    return max(files,key=lambda p:p.stat().st_mtime) if files else None


@contextmanager
def prepare_restore(db_path,backup_path):
    from database.db import Database,SCHEMA_VERSION
    db_path=Path(db_path).resolve();backup_path=Path(backup_path).resolve()
    if backup_path==db_path:raise ValueError('Choose a backup file, not the current working database')
    verify_database(backup_path,SCHEMA_VERSION)
    # This new temporary directory is a child of the explicitly selected data directory.
    with TemporaryDirectory(prefix='payroll-restore-',dir=db_path.parent) as directory:
        staged=Path(directory)/'prepared.db'
        backup_db(backup_path,staged)
        probe=Database(staged,create_backup=False)
        probe.close()
        yield staged,verify_database(staged,SCHEMA_VERSION)


def install_restore(db_path,staged):
    """Caller must close the application's connection and stop import workers first."""
    from database.db import SCHEMA_VERSION
    db_path=Path(db_path).resolve();staged=Path(staged).resolve()
    if staged==db_path:raise ValueError('Restore source must be a separate prepared database')
    manifest=verify_database(staged,SCHEMA_VERSION)
    if manifest['schema']!=SCHEMA_VERSION:raise ValueError('Prepare and migrate the backup before restoring')
    protected=backup_db(db_path)
    if protected is None:raise ValueError('Current database is missing; restore was not applied')
    def apply(source_path):
        import time
        source=sqlite3.connect(Path(source_path).as_uri()+'?mode=ro',uri=True)
        target=sqlite3.connect(db_path,timeout=5)
        deadline=time.monotonic()+10
        def progress(status,remaining,total):
            if status!=sqlite3.SQLITE_DONE and time.monotonic()>deadline:
                raise TimeoutError('Database is busy. Close other PayrollSystem instances and retry.')
        try:
            source.backup(target,pages=256,progress=progress,sleep=0.05)
        finally:
            target.close();source.close()
    # SQLite replaces the contents in one transaction, including its WAL state.
    apply(staged)
    try:
        verify_database(db_path,SCHEMA_VERSION)
    except Exception as exc:
        apply(protected)
        verify_database(db_path,SCHEMA_VERSION)
        raise RuntimeError(f'Restored file failed verification; previous database was recovered. Backup: {protected}') from exc
    return protected
