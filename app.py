import tkinter as tk
from tkinter import ttk
from pathlib import Path

from core.db import Database
from core.backup import backup_db

from ui.employees_tab import EmployeesTab
from ui.payroll_tab import PayrollTab


class PayrollApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Payroll System")
        self.geometry("900x700")
        self.minsize(900, 700)

        # ---------- database ----------
        self.db = Database("salary.db")

        # ---------- ui ----------
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        base_dir = Path(__file__).resolve().parent
        templates_dir = base_dir / "templates"

        # ---------- payroll tab ----------
        self.payroll_tab = PayrollTab(notebook, self.db, templates_dir)
        notebook.add(self.payroll_tab, text="Payroll")

        # ---------- employees tab ----------
        self.employees_tab = EmployeesTab(
            notebook,
            self.db,
            on_change=self.payroll_tab.refresh_employees,
        )
        notebook.add(self.employees_tab, text="Employees")

        # ---------- close handler ----------
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            backup_db("salary.db")
        except Exception:
            pass

        try:
            self.db.close()
        except Exception:
            pass

        self.destroy()


if __name__ == "__main__":
    app = PayrollApp()
    app.mainloop()
