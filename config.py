from pathlib import Path
import os

# ===== App Info =====
APP_NAME = "Payroll System"
APP_VERSION = "1.7.0"

# ===== Rates =====
FIXED_RATE = 8  # €/hour

# ===== Paths =====
# Используем LOCALAPPDATA для хранения БД (работает и в EXE)
LOCAL_APPDATA = os.getenv("LOCALAPPDATA")
APP_DATA_DIR = Path(LOCAL_APPDATA) / "PayrollSystem"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = APP_DATA_DIR / "payroll.db"