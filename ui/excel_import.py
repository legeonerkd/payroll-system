import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from threading import Thread
from queue import Queue, Empty
from database.db import Database
from core.validation import number
from core.models import Employee
from services.payroll_service import calculate_payroll

from services.excel_import_service import (
    import_excel_file, 
    ExcelImportError, 
    EmployeeData,
    get_import_summary
)
from services.excel_import_service import process_import
from services.report_service import generate_payroll_pdf
from config import FIXED_RATE


class ExcelImportWindow(tk.Toplevel):
    """Окно импорта данных из Excel и автогенерации зарплатных ведомостей"""
    
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Import from Excel & Auto-Generate Payrolls")
        self.geometry("1000x700")
        self.db = db
        
        self.imported_employees = []
        self.selected_file = None
        self._events = Queue()
        self._running = False
        self.protocol('WM_DELETE_WINDOW',self._close)
        
        self._build_ui()
    
    def _build_ui(self):
        """Построение интерфейса"""
        # Заголовок
        header = ttk.Frame(self, style="Card.TFrame", padding=12)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(
            header, 
            text="📊 Excel Import & Auto-Generate Payrolls", 
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        
        # Панель выбора файла
        self._build_file_panel()
        
        # Вкладки: Preview и Settings
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Вкладка Preview
        self.preview_frame = ttk.Frame(notebook)
        notebook.add(self.preview_frame, text="📋 Preview Data")
        self._build_preview_tab()
        
        # Вкладка Settings
        self.settings_frame = ttk.Frame(notebook)
        notebook.add(self.settings_frame, text="⚙️ Generation Settings")
        self._build_settings_tab()
        
        # Нижняя панель с кнопками
        self._build_action_panel()
    
    def _build_file_panel(self):
        """Панель выбора файла"""
        panel = ttk.Frame(self, style="Card.TFrame", padding=12)
        panel.pack(fill="x", padx=10, pady=(0, 10))
        
        ttk.Label(panel, text="Excel File:", font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=(0, 10)
        )
        
        self.file_label = ttk.Label(
            panel, 
            text="No file selected", 
            font=("Segoe UI", 9),
            foreground="#6C757D"
        )
        self.file_label.pack(side="left", padx=(0, 10))
        
        ttk.Button(
            panel,
            text="📁 Browse...",
            command=self._browse_file,
            style="Accent.TButton"
        ).pack(side="right", padx=5)
        
        ttk.Button(
            panel,
            text="📖 Template",
            command=self._download_template,
            style="Neutral.TButton"
        ).pack(side="right")
    
    def _build_preview_tab(self):
        """Вкладка предпросмотра данных"""
        # Инфо панель
        info_frame = ttk.Frame(self.preview_frame, style="Card.TFrame", padding=10)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.info_label = ttk.Label(
            info_frame,
            text="No data loaded. Please select an Excel file.",
            font=("Segoe UI", 9),
            foreground="#6C757D"
        )
        self.info_label.pack()
        
        # Таблица предпросмотра
        table_frame = ttk.Frame(self.preview_frame)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")
        
        # Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=("employee", "rate", "bank", "hours", "period", "amount"),
            show="headings",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        
        # Заголовки
        self.tree.heading("employee", text="Employee")
        self.tree.heading("rate", text="Rate (€/h)")
        self.tree.heading("bank", text="Bank")
        self.tree.heading("hours", text="Total Hours")
        self.tree.heading("period", text="Period")
        self.tree.heading("amount", text="Gross Amount (€)")
        
        # Ширина колонок
        self.tree.column("employee", width=200, anchor="w")
        self.tree.column("rate", width=100, anchor="center")
        self.tree.column("bank", width=150, anchor="w")
        self.tree.column("hours", width=100, anchor="center")
        self.tree.column("period", width=200, anchor="center")
        self.tree.column("amount", width=120, anchor="e")
        
        self.tree.pack(fill="both", expand=True)
        
        # Zebra stripes
        self.tree.tag_configure("odd", background="#f9f9f9")
        self.tree.tag_configure("even", background="#ffffff")
    
    def _build_settings_tab(self):
        """Вкладка настроек генерации"""
        settings_inner = ttk.Frame(self.settings_frame)
        settings_inner.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Rate Type
        rate_card = ttk.Frame(settings_inner, style="Card.TFrame", padding=15)
        rate_card.pack(fill="x", pady=(0, 15))
        
        ttk.Label(
            rate_card, 
            text="💰 Rate Type", 
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self.rate_mode = tk.StringVar(value="custom")
        
        ttk.Radiobutton(
            rate_card,
            text=f"Use Fixed Rate ({FIXED_RATE} €/h) for all employees",
            variable=self.rate_mode,
            value="fixed",
        ).pack(anchor="w", pady=3)
        
        ttk.Radiobutton(
            rate_card,
            text="Use Custom Rate from Excel file",
            variable=self.rate_mode,
            value="custom",
        ).pack(anchor="w", pady=3)
        
        # Deductions
        deduct_card = ttk.Frame(settings_inner, style="Card.TFrame", padding=15)
        deduct_card.pack(fill="x", pady=(0, 15))
        
        ttk.Label(
            deduct_card, 
            text="📉 Deductions", 
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # Utilities
        util_frame = ttk.Frame(deduct_card)
        util_frame.pack(fill="x", pady=5)
        ttk.Label(util_frame, text="Utilities (€):").pack(side="left", padx=(0, 10))
        self.utilities_var = tk.StringVar(value="0.00")
        ttk.Entry(util_frame, textvariable=self.utilities_var, width=15).pack(side="left")
        
        # Rental
        rent_frame = ttk.Frame(deduct_card)
        rent_frame.pack(fill="x", pady=5)
        ttk.Label(rent_frame, text="Rental (€):").pack(side="left", padx=(0, 10))
        self.rental_var = tk.StringVar(value="0.00")
        ttk.Entry(rent_frame, textvariable=self.rental_var, width=15).pack(side="left")
        
        # Output Options
        output_card = ttk.Frame(settings_inner, style="Card.TFrame", padding=15)
        output_card.pack(fill="x", pady=(0, 15))
        
        ttk.Label(
            output_card, 
            text="📁 Output Options", 
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        self.save_to_db_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            output_card,
            text="Save hours to database",
            variable=self.save_to_db_var
        ).pack(anchor="w", pady=3)
        
        self.create_pdf_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            output_card,
            text="Generate PDF files",
            variable=self.create_pdf_var
        ).pack(anchor="w", pady=3)
        
        self.update_employees_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            output_card,
            text="Update existing employees (rate, bank info)",
            variable=self.update_employees_var
        ).pack(anchor="w", pady=3)
        for variable in (self.rate_mode,self.utilities_var,self.rental_var):
            variable.trace_add('write',lambda *args:self._display_preview())
    
    def _build_action_panel(self):
        """Панель действий"""
        panel = ttk.Frame(self, style="Card.TFrame", padding=12)
        panel.pack(fill="x", padx=10, pady=(0, 10))
        
        self.progress_label = ttk.Label(
            panel,
            text="",
            font=("Segoe UI", 9),
            foreground="#2563eb"
        )
        self.progress_label.pack(side="left")
        
        ttk.Button(
            panel,
            text="❌ Cancel",
            command=self._close,
            style="Neutral.TButton",
            width=12
        ).pack(side="right", padx=5)
        
        self.generate_btn = ttk.Button(
            panel,
            text="⚡ Generate All Payrolls",
            command=self._generate_payrolls,
            style="Success.TButton",
            width=20,
            state="disabled"
        )
        self.generate_btn.pack(side="right")
    
    def _browse_file(self):
        """Выбор Excel файла"""
        if self._running:
            return
        filepath = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[
                ("Excel files", "*.xlsx"),
                ("All files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        self.selected_file = filepath
        filename = os.path.basename(filepath)
        self.file_label.config(text=filename, foreground="#000000")
        
        # Загружаем и отображаем данные
        self._load_excel_data()
    
    def _load_excel_data(self):
        """Загрузка данных из Excel"""
        if not self.selected_file:
            return
        
        try:
            self.progress_label.config(text="Loading Excel file...")
            self.update()
            
            # Импортируем данные
            self.imported_employees = import_excel_file(self.selected_file)
            
            # Отображаем предпросмотр
            self._display_preview()
            
            self.progress_label.config(text=f"✅ Loaded {len(self.imported_employees)} employees")
            self.generate_btn.config(state="normal")
        
        except ExcelImportError as e:
            messagebox.showerror("Import Error", str(e))
            self.progress_label.config(text="❌ Import failed")
            self.generate_btn.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error:\n{str(e)}")
            self.progress_label.config(text="❌ Import failed")
            self.generate_btn.config(state="disabled")
    
    def _display_preview(self):
        """Отображение предпросмотра данных"""
        # Очищаем таблицу
        self.tree.delete(*self.tree.get_children())
        
        if not self.imported_employees:
            return
        
        # Получаем сводку
        summary = get_import_summary(self.imported_employees)
        
        # Обновляем инфо
        date_from, date_to = summary['date_range']
        self.info_label.config(
            text=f"📊 {summary['employee_count']} employees | "
                 f"⏱ {summary['total_hours']:.1f} total hours | "
                 f"📅 Period: {date_from} to {date_to}",
            foreground="#2563eb"
        )
        
        # Заполняем таблицу
        for idx, emp in enumerate(self.imported_employees):
            total_hours = emp.get_total_hours()
            rate = emp.rate
            try:
                _,summary=calculate_payroll(Employee(0,emp.name,emp.rate),emp.hours_by_date,self.rate_mode.get(),
                    utilities=self.utilities_var.get() or 0,housing=self.rental_var.get() or 0)
                gross=summary.gross_amount
                rate=FIXED_RATE if self.rate_mode.get()=='fixed' else emp.rate
            except ValueError:
                self.info_label.config(text='Enter valid, non-negative deductions',foreground='#dc2626')
                return
            
            date_from, date_to = emp.get_date_range()
            period = f"{date_from} to {date_to}" if date_from else "N/A"
            
            tag = "odd" if idx % 2 == 0 else "even"
            
            self.tree.insert(
                "",
                "end",
                values=(
                    emp.name,
                    f"{rate:.2f}",
                    emp.bank or "—",
                    f"{total_hours:.1f}",
                    period,
                    f"{gross:.2f}"
                ),
                tags=(tag,)
            )
    
    def _download_template(self):
        """Создание Excel шаблона"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            initialfile="payroll_template.xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save Template"
        )
        
        if not filepath:
            return
        
        try:
            import pandas as pd
            from datetime import datetime, timedelta
            
            # Создаём пример данных
            start_date = datetime(2026, 5, 1)
            dates = [(start_date + timedelta(days=i)).strftime("%d-%m-%Y") for i in range(10)]
            
            data = {
                'Employee Name': ['John Doe', 'Jane Smith'],
                'Hourly Rate': [12.50, 15.00],
                'Bank': ['ABC Bank', 'XYZ Bank'],
                'IBAN': ['DE89370400440532013000', 'DE89370400440532013001'],
                'BIC': ['COBADEFFXXX', 'COBADEFFYYY'],
            }
            
            # Добавляем колонки с датами
            for date in dates:
                data[date] = [8.0, 10.0]
            
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False, engine='openpyxl')
            
            result = messagebox.askyesno(
                "Template Created",
                f"Template saved to:\n{filepath}\n\nOpen the file?",
                icon="info"
            )
            
            if result:
                os.startfile(filepath)
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create template:\n{str(e)}")
    
    def _close(self):
        if self._running:
            messagebox.showinfo('Import running','Please wait for the batch to finish before closing this window.')
            return
        self.destroy()

    def _generate_payrolls(self):
        if self._running or not self.imported_employees:
            return
        try:
            options = dict(rate_mode=self.rate_mode.get(),
                utilities=str(number(self.utilities_var.get() or 0,'Utilities deduction')),
                rental=str(number(self.rental_var.get() or 0,'Rental deduction')),
                save_to_db=self.save_to_db_var.get(),create_pdf=self.create_pdf_var.get(),
                update_existing=self.update_employees_var.get())
            if not options['save_to_db'] and not options['create_pdf']:
                raise ValueError('Select saving hours or generating PDF files')
        except ValueError as exc:
            messagebox.showerror('Import settings',str(exc))
            return
        if not messagebox.askyesno('Confirm import',
            f'Process {len(self.imported_employees)} employees?\nThe entire batch will be rolled back if any row fails.'):
            return
        self._running = True
        self.grab_set()
        self.generate_btn.config(state='disabled')
        Thread(target=self._generate_thread,args=(self.db.path,tuple(self.imported_employees),options,self._events),daemon=False).start()
        self.after(100,self._poll_import)

    @staticmethod
    def _generate_thread(db_path,employees,options,events):
        db = None
        try:
            db = Database(db_path,create_backup=False)
            result=process_import(db,employees,options,lambda i,n:events.put(('progress',(i,n))))
            events.put(('done',result))
        except Exception as exc:
            events.put(('error',str(exc)))
        finally:
            if db is not None:
                db.close()

    def _poll_import(self):
        try:
            while True:
                kind,payload=self._events.get_nowait()
                if kind=='progress':
                    self.progress_label.config(text=f'Processing {payload[0]}/{payload[1]}')
                else:
                    self._running=False
                    self.grab_release()
                    self.generate_btn.config(state='normal')
                    if kind=='done':
                        self.progress_label.config(text=f'Completed: {payload["employees"]} employees')
                        callback=getattr(self.master,'_on_employees_changed',None)
                        if callback:
                            callback()
                        messagebox.showinfo('Import complete',f'Processed {payload["employees"]} employees; created {len(payload["files"])} PDFs.')
                    else:
                        self.progress_label.config(text='Batch failed; database changes rolled back')
                        messagebox.showerror('Import failed',payload)
                    return
        except Empty:
            pass
        self.after(100,self._poll_import)
