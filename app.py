import tkinter as tk
from tkinter import ttk
import os

from database.db import Database
from core.version import APP_NAME, APP_VERSION

from ui.styles import setup_styles
from ui.employees_tab import EmployeesTab
from ui.payroll_tab import PayrollTab
from ui.payroll_history import PayrollHistory
from ui.hours_export import HoursExportWindow
from ui.excel_import import ExcelImportWindow


class PayrollApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ---------- WINDOW ----------
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1000x650")
        self.minsize(900, 600)
        self.configure(cursor="arrow")
        
        # ---------- ICON ----------
        try:
            self.iconbitmap("icon.ico")
        except:
            pass  # Если иконка не найдена, продолжаем без неё

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

        self.employees_tab = EmployeesTab(notebook, self.db, on_change=self._on_employees_changed)
        notebook.add(self.employees_tab, text="Employees")

        self.payroll_tab = PayrollTab(notebook, self.db)
        notebook.add(self.payroll_tab, text="Payroll")

        # ---------- MENU ----------
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Import menu
        import_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Import", menu=import_menu)
        import_menu.add_command(
            label="Import from Excel",
            command=lambda: ExcelImportWindow(self, self.db)
        )
        
        # Export menu
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Export", menu=export_menu)
        export_menu.add_command(
            label="Export work hours",
            command=lambda: HoursExportWindow(self, self.db)
        )
        
        # History menu
        history_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="History", menu=history_menu)
        history_menu.add_command(
            label="Payroll history",
            command=lambda: PayrollHistory(self, self.db)
        )

        # ---------- STATUS BAR ----------
        self.status_bar = ttk.Frame(self, relief="sunken", borderwidth=1)
        self.status_bar.pack(side="bottom", fill="x")
        
        self.status_label = ttk.Label(
            self.status_bar, 
            text=f"Ready | Database: {db_path}",
            font=("Segoe UI", 9),
            foreground="#6C757D"
        )
        self.status_label.pack(side="left", padx=10, pady=4)
        
        # Счётчик сотрудников
        self.employee_count_label = ttk.Label(
            self.status_bar,
            text="",
            font=("Segoe UI", 9),
            foreground="#6C757D"
        )
        self.employee_count_label.pack(side="right", padx=10, pady=4)
        
        self._update_status()

    def _update_status(self):
        """Обновление статус-бара"""
        employees = self.db.get_employees()
        count = len(employees)
        self.employee_count_label.config(text=f"👥 Employees: {count}")
    
    def _on_employees_changed(self):
        """Обработчик изменений в списке сотрудников"""
        self._update_status()
        self.payroll_tab.refresh_employees()


if __name__ == "__main__":
    PayrollApp().mainloop()

