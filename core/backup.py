from datetime import datetime
from pathlib import Path
import sqlite3


def backup_db(db_path):
    """Use SQLite's online backup API, including committed WAL contents."""
    db_path = Path(db_path).resolve()
    if not db_path.exists():
        return None
    backup_dir = db_path.parent / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    dst = backup_dir / f'payroll_backup_{datetime.now():%Y%m%d_%H%M%S_%f}.db'
    source = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)
    target = sqlite3.connect(dst)
    try:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup integrity check failed')
    finally:
        target.close()
        source.close()
    return dst
