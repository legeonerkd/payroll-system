from pathlib import Path
import shutil
from datetime import datetime


def backup_db(db_path: Path):
    if not db_path.exists():
        return

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = backup_dir / f"salary_backup_{ts}.db"

    shutil.copy2(db_path, dst)
