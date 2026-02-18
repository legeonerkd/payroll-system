import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta

from tkcalendar import DateEntry
from services.report_service import generate_payroll_pdf
from services.payroll_service import calculate_fixed_payroll, calculate_custom_payroll
from core.models import Employee
from config import FIXED_RATE

DEFAULT_HOURS = 10.0
HOUR_STEP = 0.5


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db

        self.employee_map = {}
        self.days_data = {}

        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_var = tk.StringVar(value="0.00")
        self.rental_var = tk.StringVar(value="0.00")

        # Summary variables
        self.total_hours_var = tk.StringVar(value="0.0")
        self.gross_var = tk.StringVar(value="0.00 €")
        self.deductions_var = tk.StringVar(value="0.00 €")
        self.net_var = tk.StringVar(value="0.00 €")

        self._editor = None

        self._build_ui()
        self._load_employees()
        
        # Bind auto-recalculation
        self.rate_mode.trace_add("write", lambda *args: self._auto_recalculate())
        self.utilities_var.trace_add("write", lambda *args: self._auto_recalculate())
        self.rental_var.trace_add("write", lambda *args: self._auto_recalculate())

    # ======================================================
    # UI LAYOUT - 3 ZONES (Header / Content / Summary)
    # ======================================================

    def _build_ui(self):
        """Профессиональный layout с 3 зонами"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=0)  # Header
        self.rowconfigure(1, weight=1)  # Content
        self.rowconfigure(2, weight=0)  # Summary

        # ========== ZONE 1: HEADER ==========
        self._build_header()

        # ========== ZONE 2: CONTENT ==========
        self._build_content()

        # ========== ZONE 3: SUMMARY ==========
        self._build_summary()

    # ======================================================
    # ZONE 1: HEADER (Employee / Period / Generate)
    # ======================================================

    def _build_header(self):
        """Горизонтальная панель управления"""
        header = ttk.Frame(self, style="Card.TFrame", padding=12)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        # Employee
        ttk.Label(header, text="Employee:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 5)
        )
        self.employee_cb = ttk.Combobox(header, state="readonly", width=25)
        self.employee_cb.grid(row=0, column=1, sticky="w", padx=(0, 20))

        # Period From
        ttk.Label(header, text="From:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=2, sticky="w", padx=(0, 5)
        )
        self.from_entry = DateEntry(
            header, date_pattern="dd-mm-yyyy", firstweekday="monday", width=12
        )
        self.from_entry.grid(row=0, column=3, sticky="w", padx=(0, 10))

        # Period To
        ttk.Label(header, text="To:", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=4, sticky="w", padx=(0, 5)
        )
        self.to_entry = DateEntry(
            header, date_pattern="dd-mm-yyyy", firstweekday="monday", width=12
        )
        self.to_entry.grid(row=0, column=5, sticky="w", padx=(0, 20))

        # Generate Button
        ttk.Button(
            header,
            text="⚡ Generate Period",
            command=self._generate_period,
            style="Accent.TButton",
        ).grid(row=0, column=6, sticky="w")

    # ======================================================
    # ZONE 2: CONTENT (Hours Table + Rate + Deductions + PDF)
    # ======================================================

    def _build_content(self):
        """Основная рабочая зона"""
        content = ttk.Frame(self)
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=0)
        content.rowconfigure(0, weight=1)

        # LEFT: Hours Table
        self._build_hours_table(content)

        # RIGHT: Rate + Deductions + PDF
        self._build_right_panel(content)

    def _build_hours_table(self, parent):
        """Улучшенная таблица часов с zebra-стилем и итогами"""
        table_frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        ttk.Label(
            table_frame, text="📅 Working Hours", font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        # Treeview with scrollbar
        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            tree_container,
            columns=("date", "day", "hours"),
            show="headings",
            yscrollcommand=scrollbar.set,
        )
        scrollbar.config(command=self.tree.yview)

        self.tree.heading("date", text="Date", anchor="center")
        self.tree.heading("day", text="Day", anchor="center")
        self.tree.heading("hours", text="Hours", anchor="center")

        self.tree.column("date", width=120, anchor="center")
        self.tree.column("day", width=150, anchor="center")
        self.tree.column("hours", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Bind events
        self.tree.bind("<Double-1>", self._start_edit_hours)
        self.tree.bind("<Button-1>", self.clear_selection_on_click, add="+")

        # Total row label
        self.total_label = ttk.Label(
            table_frame,
            text="Total: 0.0 hours",
            font=("Segoe UI", 10, "bold"),
            foreground="#2563eb",
        )
        self.total_label.pack(anchor="e", pady=(5, 0))

    def _build_right_panel(self, parent):
        """Правая панель: Rate Type + Deductions + PDF"""
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")

        # Rate Type Card
        self._build_rate_card(right)

        # Deductions Card
        self._build_deductions_card(right)

        # PDF Actions
        self._build_pdf_actions(right)

    def _build_rate_card(self, parent):
        """Карточка Rate Type с радиокнопками"""
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="x", pady=(0, 10))

        ttk.Label(card, text="💰 Rate Type", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        ttk.Radiobutton(
            card,
            text=f"Fixed Rate ({FIXED_RATE} €/h)",
            variable=self.rate_mode,
            value="fixed",
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            card,
            text="Employee Custom Rate",
            variable=self.rate_mode,
            value="custom",
        ).pack(anchor="w", pady=2)

    def _build_deductions_card(self, parent):
        """Карточка Deductions с preview расчёта"""
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="x", pady=(0, 10))

        ttk.Label(card, text="📉 Deductions", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        # Utilities
        ttk.Label(card, text="Utilities (€):").pack(anchor="w", pady=(0, 2))
        utilities_entry = ttk.Entry(card, textvariable=self.utilities_var, width=15)
        utilities_entry.pack(anchor="w", pady=(0, 8))

        # Rental
        ttk.Label(card, text="Rental (€):").pack(anchor="w", pady=(0, 2))
        rental_entry = ttk.Entry(card, textvariable=self.rental_var, width=15)
        rental_entry.pack(anchor="w", pady=(0, 8))

        # Preview
        ttk.Separator(card, orient="horizontal").pack(fill="x", pady=8)
        
        preview_frame = ttk.Frame(card)
        preview_frame.pack(fill="x")

        ttk.Label(preview_frame, text="Total Deductions:", font=("Segoe UI", 9)).pack(
            anchor="w"
        )
        self.deductions_preview = ttk.Label(
            preview_frame,
            text="0.00 €",
            font=("Segoe UI", 10, "bold"),
            foreground="#dc2626",
        )
        self.deductions_preview.pack(anchor="w")

    def _build_pdf_actions(self, parent):
        """Горизонтальные PDF кнопки"""
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.pack(fill="x", pady=(0, 10))

        ttk.Label(card, text="📄 PDF Actions", font=("Segoe UI", 11, "bold")).pack(
            anchor="w", pady=(0, 8)
        )

        # Buttons in horizontal layout
        btn_frame = ttk.Frame(card)
        btn_frame.pack(fill="x")

        ttk.Button(
            btn_frame,
            text="👁 Preview",
            command=self._preview_pdf,
            style="Accent.TButton",
            width=10,
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="💾 Save",
            command=self._save_pdf,
            style="Success.TButton",
            width=10,
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            btn_frame,
            text="🖨 Print",
            command=self._print_pdf,
            style="Neutral.TButton",
            width=10,
        ).pack(side="left")

    # ======================================================
    # ZONE 3: SUMMARY PANEL
    # ======================================================

    def _build_summary(self):
        """Summary Panel с итогами расчёта"""
        summary = ttk.Frame(self, style="Card.TFrame", padding=12)
        summary.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))

        ttk.Label(
            summary, text="📊 Payroll Summary", font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 20))

        # Total Hours
        ttk.Label(summary, text="Total Hours:", font=("Segoe UI", 9)).pack(
            side="left", padx=(0, 5)
        )
        ttk.Label(
            summary,
            textvariable=self.total_hours_var,
            font=("Segoe UI", 10, "bold"),
            foreground="#2563eb",
        ).pack(side="left", padx=(0, 20))

        # Gross
        ttk.Label(summary, text="Gross:", font=("Segoe UI", 9)).pack(
            side="left", padx=(0, 5)
        )
        ttk.Label(
            summary,
            textvariable=self.gross_var,
            font=("Segoe UI", 10, "bold"),
            foreground="#16a34a",
        ).pack(side="left", padx=(0, 20))

        # Deductions
        ttk.Label(summary, text="Deductions:", font=("Segoe UI", 9)).pack(
            side="left", padx=(0, 5)
        )
        ttk.Label(
            summary,
            textvariable=self.deductions_var,
            font=("Segoe UI", 10, "bold"),
            foreground="#dc2626",
        ).pack(side="left", padx=(0, 20))

        # Net
        ttk.Label(summary, text="NET SALARY:", font=("Segoe UI", 10, "bold")).pack(
            side="left", padx=(0, 5)
        )
        ttk.Label(
            summary,
            textvariable=self.net_var,
            font=("Segoe UI", 12, "bold"),
            foreground="#2563eb",
        ).pack(side="left")

    # ======================================================
    # DATA
    # ======================================================

    def _load_employees(self):
        self.employee_map.clear()
        names = []

        for e in self.db.get_employees():
            self.employee_map[e["name"]] = e
            names.append(e["name"])

        self.employee_cb["values"] = names
        if names:
            self.employee_cb.current(0)

    # ======================================================
    # PERIOD GENERATION
    # ======================================================

    def _generate_period(self):
        """Генерация периода с zebra-стилем и подсветкой выходных"""
        self.tree.delete(*self.tree.get_children())
        self.days_data.clear()

        start = self.from_entry.get_date()
        end = self.to_entry.get_date()

        # Configure zebra tags
        self.tree.tag_configure("odd", background="#f9f9f9")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("weekend", background="#fee2e2", foreground="#991b1b")

        d = start
        row_index = 0
        while d <= end:
            is_weekend = d.weekday() in [5, 6]  # Saturday, Sunday
            hours = 0.0 if is_weekend else DEFAULT_HOURS

            key = d.strftime("%Y-%m-%d")
            self.days_data[key] = hours

            # Determine tag
            if is_weekend:
                tag = "weekend"
            else:
                tag = "odd" if row_index % 2 == 0 else "even"

            self.tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    d.strftime("%d-%m-%Y"),
                    d.strftime("%A"),
                    f"{hours:.1f}",
                ),
                tags=(tag,),
            )

            d += timedelta(days=1)
            row_index += 1

        self._update_total_hours()
        self._auto_recalculate()

    # ======================================================
    # HOURS EDITING
    # ======================================================

    def _start_edit_hours(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        if column != "#3":
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        bbox = self.tree.bbox(row_id, column)
        if not bbox:
            return

        x, y, w, h = bbox
        value = self.days_data.get(row_id, 0.0)

        self._editor = tk.Spinbox(
            self.tree, from_=0, to=24, increment=HOUR_STEP, justify="center"
        )
        self._editor.delete(0, "end")
        self._editor.insert(0, f"{value:.1f}")
        self._editor.place(x=x, y=y, width=w, height=h)
        self._editor.focus()

        self._editor.bind("<Return>", lambda e: self._save_hours(row_id))
        self._editor.bind("<FocusOut>", lambda e: self._save_hours(row_id))

    def _save_hours(self, row_id):
        if not self._editor:
            return

        try:
            val = float(self._editor.get())
            val = round(val / HOUR_STEP) * HOUR_STEP
            if val < 0:
                val = 0.0
        except Exception:
            val = self.days_data.get(row_id, 0.0)

        self.days_data[row_id] = val

        values = list(self.tree.item(row_id, "values"))
        values[2] = f"{val:.1f}"
        self.tree.item(row_id, values=values)

        self._editor.destroy()
        self._editor = None

        self._update_total_hours()
        self._auto_recalculate()

    def clear_selection_on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        item = self.tree.identify_row(event.y)

        if not item:
            self.tree.selection_remove(self.tree.selection())

        return None

    # ======================================================
    # AUTO-RECALCULATION
    # ======================================================

    def _update_total_hours(self):
        """Обновление итогов часов"""
        total = sum(self.days_data.values())
        self.total_hours_var.set(f"{total:.1f}")
        self.total_label.config(text=f"Total: {total:.1f} hours")

    def _auto_recalculate(self):
        """Автоматический пересчёт Net при изменении параметров"""
        if not self.days_data:
            return

        name = self.employee_cb.get()
        if not name:
            return

        emp_data = self.employee_map[name]
        emp = Employee(
            id=emp_data["id"],
            name=emp_data["name"],
            rate=emp_data["rate"],
        )

        try:
            utilities = float(self.utilities_var.get() or 0)
        except ValueError:
            utilities = 0.0

        try:
            rental = float(self.rental_var.get() or 0)
        except ValueError:
            rental = 0.0

        # Calculate
        if self.rate_mode.get() == "fixed":
            rows, summary = calculate_fixed_payroll(
                emp, self.days_data, utilities=utilities, housing=rental
            )
        else:
            rows, summary = calculate_custom_payroll(
                emp, self.days_data, utilities=utilities, housing=rental
            )

        # Update summary
        self.total_hours_var.set(f"{summary.total_hours:.1f}")
        self.gross_var.set(f"{summary.gross_amount:.2f} €")
        
        total_deductions = summary.housing_deduction + summary.utilities_deduction
        self.deductions_var.set(f"{total_deductions:.2f} €")
        self.net_var.set(f"{summary.net_amount:.2f} €")

        # Update deductions preview
        self.deductions_preview.config(text=f"{total_deductions:.2f} €")

    # ======================================================
    # PDF ACTIONS
    # ======================================================

    def _preview_pdf(self):
        """Просмотр PDF"""
        try:
            self._call_pdf(action="preview")
        except Exception as e:
            messagebox.showerror("PDF Preview", str(e))

    def _save_pdf(self):
        """Сохранение PDF в папку по периоду"""
        try:
            pdf_path = self._call_pdf(action="save")
            messagebox.showinfo("PDF Saved", f"PDF saved to:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("PDF Save", str(e))

    def _print_pdf(self):
        """Печать PDF"""
        try:
            self._call_pdf(action="print")
            messagebox.showinfo("PDF Print", "PDF sent to printer")
        except Exception as e:
            messagebox.showerror("PDF Print", str(e))

    def _call_pdf(self, action="preview"):
        """
        Генерирует PDF с указанным действием
        action: "preview", "save", "print"
        """
        name = self.employee_cb.get()
        if not name:
            raise ValueError("Employee not selected")

        emp = self.employee_map[name]

        rows = []
        for iid in self.tree.get_children():
            date, day, hours = self.tree.item(iid)["values"]
            rows.append((date, day, hours))

        pdf_path = generate_payroll_pdf(
            employee_name=emp["name"],
            employee_rate=emp["rate"],
            rows=rows,
            rate_mode=self.rate_mode.get(),
            utilities=self.utilities_var.get() or None,
            rental=self.rental_var.get() or None,
            period_from=self.from_entry.get(),
            period_to=self.to_entry.get(),
            bank_name=emp["bank"] if "bank" in emp.keys() else None,
            iban=emp["iban"] if "iban" in emp.keys() else None,
            bic=emp["bic"] if "bic" in emp.keys() else None,
            action=action,
        )

        return pdf_path
