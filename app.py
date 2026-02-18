import tkinter as tk
from tkinter import ttk
import os

from database.db import Database
from core.version import APP_NAME, APP_VERSION

from ui.styles import setup_styles
from ui.employees_tab import EmployeesTab
from ui.payroll_tab import PayrollTab
from ui.payroll_history import PayrollHistory


class PayrollApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ---------- WINDOW ----------
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1000x650")
        self.minsize(900, 600)
        self.configure(cursor="arrow")

        # ---------- STYLES ----------
        setup_styles(self)

        # ---------- DATABASE ----------
        local_appdata = os.getenv("LOCALAPPDATA")
        db_dir = os.path.join(local_appdata, "PayrollSystem")
        db_path = os.path.join(db_dir, "payroll.db")
        os.makedirs(db_dir, exist_ok=True)

        self.db = Database()


        # ---------- NOTEBOOK ----------
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.employees_tab = EmployeesTab(notebook, self.db, on_change=None)
        notebook.add(self.employees_tab, text="Employees")

        self.payroll_tab = PayrollTab(notebook, self.db)
        notebook.add(self.payroll_tab, text="Payroll")

        # ---------- MENU ----------
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        history_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="History", menu=history_menu)
        history_menu.add_command(
            label="Payroll history",
            command=lambda: PayrollHistory(self, self.db)
        )


if __name__ == "__main__":
    PayrollApp().mainloop()

