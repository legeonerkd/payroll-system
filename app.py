import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from core.db import Database
from ui.employees_tab import EmployeesTab
from ui.payroll_tab import PayrollTab


# ======================================================
# PYINSTALLER RESOURCE HELPER
# ======================================================
def resource_path(relative: str) -> Path:
    """
    Корректно возвращает путь:
    - при обычном запуске Python
    - при запуске из PyInstaller .exe
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(relative)


# ======================================================
# APP INFO
# ======================================================
APP_NAME = "Payroll System"
APP_VERSION = "1.4"


# ======================================================
# FILE SYSTEM
# ======================================================
# Рабочая папка (данные пользователя)
BASE_DIR = Path.home() / "Documents" / "PayrollSystem"
PAYROLL_DIR = BASE_DIR / "Payroll"

# Ресурсы (упаковываются в exe)
TEMPLATES_DIR = resource_path("templates")

DB_PATH = BASE_DIR / "salary.db"

BASE_DIR.mkdir(exist_ok=True)
PAYROLL_DIR.mkdir(exist_ok=True)


# ======================================================
# MAIN
# ======================================================
def main():
    db = Database(DB_PATH)

    root = tk.Tk()
    root.title(f"{APP_NAME} v{APP_VERSION}")
    root.geometry("1100x720")

    tabs = ttk.Notebook(root)
    tabs.pack(fill="both", expand=True)

    tabs.add(EmployeesTab(tabs, db), text="Employees")
    tabs.add(PayrollTab(tabs, db, TEMPLATES_DIR), text="Payroll")

    root.mainloop()
    db.close()


if __name__ == "__main__":
    main()

