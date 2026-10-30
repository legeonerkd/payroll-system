import os
from pathlib import Path
from core.version import APP_NAME, APP_VERSION
from core.paths import get_app_dir

FIXED_RATE = 8
APP_DATA_DIR = Path(os.environ['PAYROLL_DATA_DIR']) if os.environ.get('PAYROLL_DATA_DIR') else get_app_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = APP_DATA_DIR / 'payroll.db'
