from pathlib import Path

# ===== App Info =====
APP_NAME = "Payroll System"
APP_VERSION = "1.5.0"

# ===== Rates =====
FIXED_RATE = 8  # €/hour

# ===== Paths =====
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "salary.db"