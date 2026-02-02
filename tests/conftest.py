import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
