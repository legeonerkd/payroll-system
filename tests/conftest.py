import sys
import os
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
os.environ['PAYROLL_DATA_DIR'] = str(ROOT_DIR / '.pytest_cache' / 'isolated-data')
os.environ['PAYROLL_OUTPUT_DIR'] = str(ROOT_DIR / '.pytest_cache' / 'isolated-pdfs')
