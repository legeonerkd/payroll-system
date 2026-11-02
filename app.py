import tkinter as tk
from tkinter import ttk, messagebox
from calendar import monthrange
from datetime import date

from database.db import Database
from core.version import APP_NAME, APP_VERSION

from ui.styles import setup_styles,COLORS
from ui.employees_tab import EmployeesTab
from ui.payroll_tab import PayrollTab
from ui.payroll_history import PayrollHistory
from ui.monthly_summary import MonthlySummary
from ui.backup_manager import BackupManager
from ui.hours_export import HoursExportWindow
from ui.excel_import import ExcelImportWindow
from config import DATABASE_PATH, APP_DATA_DIR
from core.backup import backup_db,prepare_restore,install_restore
import logging
import sys
from pathlib import Path


class PayrollApp(tk.Tk):
    def __init__(self):
        super().__init__()

        # ---------- WINDOW ----------
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1120x780")
        self.minsize(900, 600)
        self.configure(cursor="arrow",background=COLORS['bg'])
        
        # ---------- ICON ----------
        try:
            self.iconbitmap(str(Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'icon.ico'))
        except:
            pass  # Если иконка не найдена, продолжаем без неё

        # ---------- STYLES ----------
        setup_styles(self)

        # ---------- DATABASE ----------
        self.db = Database(DATABASE_PATH)
        self.protocol('WM_DELETE_WINDOW',self._close)


        # ---------- NOTEBOOK ----------
        notebook = ttk.Notebook(self)
        self.notebook=notebook
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.employees_tab = EmployeesTab(notebook, self.db, on_change=self._on_employees_changed,archive_warning=self._archive_warning)
        notebook.add(self.employees_tab, text="Employees")

        self.payroll_tab = PayrollTab(notebook, self.db,on_edit_employee=self._edit_employee_from_payroll)
        notebook.add(self.payroll_tab, text="Payroll")
        notebook.select(self.payroll_tab)

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
        history_menu.add_command(label='Monthly summary',command=lambda:MonthlySummary(self,self.db,self._open_month_timesheet))
        data_menu=tk.Menu(menubar,tearoff=0)
        menubar.add_cascade(label='Data',menu=data_menu)
        data_menu.add_command(label='Create database backup',command=self._backup)
        data_menu.add_command(label='Backups and restore',command=lambda:BackupManager(self,DATABASE_PATH,self._restore_database))

        # ---------- STATUS BAR ----------
        self.status_bar = ttk.Frame(self,style='StatusBar.TFrame')
        self.status_bar.pack(side="bottom", fill="x")
        
        self.status_label = ttk.Label(
            self.status_bar, 
            text='Ready',
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
        self.employee_count_label.config(text=f"Employees: {count}")
    
    def _on_employees_changed(self):
        """Обработчик изменений в списке сотрудников"""
        self._update_status()
        self.payroll_tab.refresh_employees()
        self.employees_tab._load()

    def _archive_warning(self,emp_id):
        tab=self.payroll_tab
        if tab._context and tab._context[0]==emp_id and (tab.has_unsaved_changes() or tab._editor is not None):
            return 'Unsaved Payroll hours and settings for this employee will be discarded.'
        return ''

    def _edit_employee_from_payroll(self,emp_id):
        editor=self.employees_tab
        if not editor._confirm_form_discard():return
        editor._new_employee_mode()
        editor._search_reset=True
        try:editor.search_var.set('');editor._last_search=''
        finally:editor._search_reset=False
        editor._render_table()
        if editor.tree.exists(str(emp_id)):
            editor.tree.selection_set(str(emp_id));editor._on_select(None);editor.tree.see(str(emp_id))
            self.notebook.select(editor)

    def _backup(self):
        try:
            path=backup_db(DATABASE_PATH)
            messagebox.showinfo('Backup',f'Verified backup saved to:\n{path}\nCopy it to a separate drive for independent storage.')
        except Exception as exc:
            messagebox.showerror('Backup failed',str(exc))

    def _open_month_timesheet(self,emp_id,month):
        label=next((label for label,e in self.payroll_tab.employee_map.items() if e['id']==emp_id),None)
        if label is None:
            messagebox.showinfo('Timesheet','This employee is archived. Their saved statements remain available in history.');return False
        tab=self.payroll_tab
        if (tab.has_unsaved_changes() or tab._editor is not None) and not messagebox.askyesno('Unsaved changes','Discard unsaved changes and open this timesheet?'):return False
        tab._cancel_hours_edit()
        tab._dirty=False;tab._payroll_dirty=False;tab._distribution_dirty=False
        year,number=map(int,month.split('-'))
        tab.employee_cb.set(label)
        tab.from_entry.set_date(date(year,number,1));tab.to_entry.set_date(date(year,number,monthrange(year,number)[1]))
        tab._employee_changed();self.notebook.select(tab)
        return True

    def _reset_data_views(self):
        for window in list(self.winfo_children()):
            if isinstance(window,tk.Toplevel):window.destroy()
        self.employees_tab.destroy();self.payroll_tab.destroy()
        self.employees_tab=EmployeesTab(self.notebook,self.db,on_change=self._on_employees_changed,archive_warning=self._archive_warning)
        self.notebook.add(self.employees_tab,text='Employees')
        self.payroll_tab=PayrollTab(self.notebook,self.db,on_edit_employee=self._edit_employee_from_payroll)
        self.notebook.add(self.payroll_tab,text='Payroll');self.notebook.select(self.payroll_tab)
        self._update_status()

    def _restore_database(self,path):
        if any(isinstance(w,ExcelImportWindow) and w._running for w in self.winfo_children()):
            messagebox.showinfo('Import running','Wait for the import to finish before restoring.');return False
        try:
            with prepare_restore(DATABASE_PATH,path) as (staged,info):
                question=(f'Restore this verified backup?\n{info["employees"]} employees, {info["hours"]} hour entries, '
                    f'{info["payrolls"]} statements.\n\nThis replaces the working database and discards unsaved edits. '
                    'Other data windows will close. A verified copy of the current database will be kept first. '
                    'Close other PayrollSystem instances before continuing.')
                if not messagebox.askyesno('Confirm restore',question):return False
                self.payroll_tab._cancel_hours_edit()
                self.db.close()
                try:
                    protected=install_restore(DATABASE_PATH,staged)
                finally:
                    self.db=Database(DATABASE_PATH,create_backup=False)
                    self._reset_data_views()
            messagebox.showinfo('Restore complete',f'Database restored and reopened.\nPrevious data backup:\n{protected}')
            return True
        except Exception as exc:
            messagebox.showerror('Restore failed',str(exc));return False

    def _close(self):
        if any(isinstance(w,ExcelImportWindow) and w._running for w in self.winfo_children()):
            messagebox.showinfo('Import running','Wait for the import to finish before closing the application.')
            return
        if (self.employees_tab.has_unsaved_changes() or self.payroll_tab.has_unsaved_changes() or self.payroll_tab._editor is not None) and not messagebox.askyesno('Unsaved changes','Close and discard unsaved employee details, hours and payroll settings?'):
            return
        self.db.close()
        self.destroy()

    def report_callback_exception(self,exc_type,exc,tb):
        # Do not log arbitrary exception text or locals containing payroll data.
        logging.error('Unhandled UI exception: %s',exc_type.__name__)
        messagebox.showerror('PayrollSystem',f'{exc_type.__name__}: {exc}')


if __name__ == "__main__":
    logging.basicConfig(filename=APP_DATA_DIR/'errors.log',level=logging.ERROR,
                        format='%(asctime)s %(levelname)s %(message)s')
    try:
        PayrollApp().mainloop()
    except Exception as exc:
        logging.error('Startup failed: %s',type(exc).__name__)
        messagebox.showerror('PayrollSystem startup failed',str(exc))

