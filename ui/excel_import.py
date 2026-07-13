import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
from threading import Thread

from services.excel_import_service import (
    import_excel_file, 
    ExcelImportError, 
    EmployeeData,
    get_import_summary
)
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
            command=self.destroy,
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
        filepath = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
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
            gross = total_hours * rate
            
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
    
    def _generate_payrolls(self):
        """Генерация всех зарплатных ведомостей"""
        if not self.imported_employees:
            messagebox.showwarning("No Data", "No employees to process")
            return
        
        # Подтверждение
        result = messagebox.askyesno(
            "Confirm Generation",
            f"Generate payroll PDFs for {len(self.imported_employees)} employees?\n\n"
            f"This may take some time.",
            icon="question"
        )
        
        if not result:
            return
        
        # Отключаем кнопку
        self.generate_btn.config(state="disabled")
        
        # Запускаем генерацию в отдельном потоке
        thread = Thread(target=self._generate_thread, daemon=True)
        thread.start()
    
    def _generate_thread(self):
        """Поток генерации PDF"""
        rate_mode = self.rate_mode.get()
        utilities = self.utilities_var.get() or "0"
        rental = self.rental_var.get() or "0"
        save_to_db = self.save_to_db_var.get()
        create_pdf = self.create_pdf_var.get()
        update_existing = self.update_employees_var.get()
        
        success_count = 0
        error_count = 0
        errors = []
        
        for idx, emp in enumerate(self.imported_employees, 1):
            try:
                self.progress_label.config(
                    text=f"Processing {idx}/{len(self.imported_employees)}: {emp.name}..."
                )
                self.update()
                
                # Проверяем/создаём сотрудника в БД
                db_employees = {e['name']: e for e in self.db.get_employees()}
                
                if emp.name in db_employees:
                    # Сотрудник существует
                    db_emp = db_employees[emp.name]
                    emp_id = db_emp['id']
                    
                    if update_existing:
                        # Обновляем данные
                        self.db.update_employee(
                            emp_id=emp_id,
                            name=emp.name,
                            rate=emp.rate,
                            bank=emp.bank,
                            iban=emp.iban,
                            bic=emp.bic
                        )
                else:
                    # Создаём нового сотрудника
                    self.db.add_employee(
                        name=emp.name,
                        rate=emp.rate,
                        bank=emp.bank,
                        iban=emp.iban,
                        bic=emp.bic
                    )
                    # Получаем ID
                    db_employees = {e['name']: e for e in self.db.get_employees()}
                    emp_id = db_employees[emp.name]['id']
                
                # Сохраняем часы в БД
                if save_to_db:
                    self.db.save_hours_batch(emp_id, emp.hours_by_date)
                
                # Генерируем PDF
                if create_pdf:
                    date_from, date_to = emp.get_date_range()
                    
                    # Формируем rows для PDF
                    rows = []
                    for date_str in sorted(emp.hours_by_date.keys()):
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                        hours = emp.hours_by_date[date_str]
                        rows.append((
                            date_obj.strftime("%d-%m-%Y"),
                            date_obj.strftime("%A"),
                            f"{hours:.1f}"
                        ))
                    
                    # Преобразуем даты для PDF
                    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
                    date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
                    
                    generate_payroll_pdf(
                        employee_name=emp.name,
                        employee_rate=emp.rate,
                        rows=rows,
                        rate_mode=rate_mode,
                        utilities=utilities,
                        rental=rental,
                        period_from=date_from_obj.strftime("%d-%m-%Y"),
                        period_to=date_to_obj.strftime("%d-%m-%Y"),
                        bank_name=emp.bank,
                        iban=emp.iban,
                        bic=emp.bic,
                        action="save"
                    )
                
                success_count += 1
            
            except Exception as e:
                error_count += 1
                errors.append(f"{emp.name}: {str(e)}")
        
        # Показываем результат
        self.progress_label.config(
            text=f"✅ Done: {success_count} successful, {error_count} errors"
        )
        
        if errors:
            error_msg = "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... and {len(errors) - 10} more"
            messagebox.showwarning(
                "Generation Complete with Errors",
                f"Successfully generated: {success_count}\nErrors: {error_count}\n\n{error_msg}"
            )
        else:
            messagebox.showinfo(
                "Success",
                f"✅ Successfully generated {success_count} payroll PDFs!"
            )
        
        self.generate_btn.config(state="normal")
