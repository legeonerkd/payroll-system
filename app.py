import tkinter as tk
from tkinter import ttk
from pathlib import Path

from core.db import Database
from ui.employees_tab import EmployeesTab
from ui.payroll_tab import PayrollTab


# ==================================================
# PATHS (CRITICAL FIX)
# ==================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "salary.db"
TEMPLATES_DIR = BASE_DIR / "templates"


# ==================================================
# APP
# ==================================================
class PayrollApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Payroll System")
        self.geometry("900x650")

        # ---- Database (SINGLE SOURCE OF TRUTH) ----
        self.db = Database(DB_PATH)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        notebook.add(
            EmployeesTab(notebook, self.db),
            text="Employees"
        )

        notebook.add(
            PayrollTab(notebook, self.db, TEMPLATES_DIR),
            text="Payroll"
        )

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.db.close()
        self.destroy()


# ==================================================
# ENTRY POINT
# ==================================================
if __name__ == "__main__":
    app = PayrollApp()
    app.mainloop()

