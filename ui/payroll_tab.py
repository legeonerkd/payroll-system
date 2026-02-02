import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json
import os

from tkcalendar import DateEntry

from core.models import Employee
from services.payroll_service import (
    calculate_fixed_payroll,
    calculate_custom_payroll,
)
from services.report_service import generate_payroll_pdf


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db, templates_dir):
        super().__init__(parent)
        self.db = db
        self.templates_dir = templates_dir

        self.employee: Employee | None = None
        self.employees: list[Employee] = []
        self.hours_map: dict[str, float] = {}

        self._build_ui()
        self._load_employees()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        ttk.Label(self, text="Employee").pack(anchor="w")
        self.employee_combo = ttk.Combobox(self, state="readonly")
        self.employee_combo.pack(fill="x")
        self.employee_combo.bind("<<ComboboxSelected>>", self._on_employee_change)

        ttk.Label(self, text="Report type").pack(anchor="w", pady=(10, 0))
        self.report_type = tk.StringVar(value="fixed")

        ttk.Radiobutton(
            self, text="Fixed (8 €/hour)",
            variable=self.report_type, value="fixed",
            command=self._on_report_type_change
        ).pack(anchor="w")

        ttk.Radiobutton(
            self, text="Custom",
            variable=self.report_type, value="custom",
            command=self._on_report_type_change
        ).pack(anchor="w")

        self.rate_frame = ttk.Frame(self)
        ttk.Label(self.rate_frame, text="Rate (€ / hour)").pack(anchor="w")
        self.rate_entry = ttk.Entry(self.rate_frame)
        self.rate_entry.pack(fill="x")

        self.deductions_frame = ttk.LabelFrame(self, text="Deductions")

        self.housing_var = tk.BooleanVar()
        self.utilities_var = tk.BooleanVar()

        ttk.Checkbutton(
            self.deductions_frame, text="Housing",
            variable=self.housing_var,
            command=self._toggle_deductions
        ).grid(row=0, column=0, sticky="w")

        ttk.Checkbutton(
            self.deductions_frame, text="Utilities",
            variable=self.utilities_var,
            command=self._toggle_deductions
        ).grid(row=1, column=0, sticky="w")

        self.housing_entry = ttk.Entry(self.deductions_frame)
        self.utilities_entry = ttk.Entry(self.deductions_frame)

        self.housing_entry.grid(row=0, column=1)
        self.utilities_entry.grid(row=1, column=1)

        ttk.Label(self, text="Period").pack(anchor="w", pady=(10, 0))
        self.start_entry = DateEntry(self, date_pattern="dd-mm-yyyy")
        self.end_entry = DateEntry(self, date_pattern="dd-mm-yyyy")
        self.start_entry.pack(fill="x")
        self.end_entry.pack(fill="x")

        self.tree = ttk.Treeview(
            self,
            columns=("date", "weekday", "hours"),
            show="headings",
            height=10
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("weekday", text="Day")
        self.tree.heading("hours", text="Hours")
        self.tree.pack(fill="both", expand=True, pady=10)

        self.tree.bind("<Double-1>", self._edit_hours)

        ttk.Button(self, text="Generate period", command=self._generate_period).pack(fill="x")
        ttk.Button(self, text="Preview PDF", command=lambda: self._generate_pdf(True)).pack(fill="x")
        ttk.Button(self, text="Generate PDF", command=lambda: self._generate_pdf(False)).pack(fill="x")

        self._on_report_type_change()
        self._toggle_deductions()

    # ==================================================
    # DATA
    # ==================================================
    def _load_employees(self):
        rows = self.db.get_employees()
        self.employees = [Employee.from_row(r) for r in rows]

        self.employee_combo["values"] = [e.name for e in self.employees]
        if self.employees:
            self.employee_combo.current(0)
            self._on_employee_change()

    def _on_employee_change(self, *_):
        name = self.employee_combo.get()
        self.employee = next(e for e in self.employees if e.name == name)

    # ==================================================
    # PERIOD
    # ==================================================
    def _generate_period(self):
        if not self.employee:
            return

        self.tree.delete(*self.tree.get_children())
        self.hours_map.clear()

        start = datetime.strptime(self.start_entry.get(), "%d-%m-%Y")
        end = datetime.strptime(self.end_entry.get(), "%d-%m-%Y")

        d = start
        while d <= end:
            iso = d.strftime("%Y-%m-%d")
            ui = d.strftime("%d-%m-%Y")
            weekday = d.strftime("%A")

            saved = self.db.load_hours(self.employee.id, iso, iso)
            hours = saved[0]["hours"] if saved else 0.0

            self.hours_map[iso] = hours
            self.tree.insert("", "end", iid=iso, values=(ui, weekday, hours))
            d += timedelta(days=1)

    def _edit_hours(self, event):
        row = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if col != "#3":
            return

        x, y, w, h = self.tree.bbox(row, col)
        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, self.tree.set(row, "hours"))
        entry.focus()

        def save(_):
            try:
                val = float(entry.get())
            except ValueError:
                val = 0.0

            self.tree.set(row, "hours", val)
            self.hours_map[row] = val
            self.db.save_hours(self.employee.id, row, val)
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    # ==================================================
    # OPTIONS
    # ==================================================
    def _on_report_type_change(self):
        if self.report_type.get() == "custom":
            self.rate_frame.pack(fill="x", pady=5)
            self.deductions_frame.pack(fill="x", pady=5)
        else:
            self.rate_frame.pack_forget()
            self.deductions_frame.pack_forget()

    def _toggle_deductions(self):
        self.housing_entry.config(state="normal" if self.housing_var.get() else "disabled")
        self.utilities_entry.config(state="normal" if self.utilities_var.get() else "disabled")

    # ==================================================
    # PDF
    # ==================================================
    def _generate_pdf(self, preview: bool):
        if not self.hours_map or not self.employee:
            messagebox.showwarning("No data", "Generate period first")
            return

        start_iso = datetime.strptime(self.start_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")
        end_iso = datetime.strptime(self.end_entry.get(), "%d-%m-%Y").strftime("%Y-%m-%d")

        if self.report_type.get() == "fixed":
            rows, summary = calculate_fixed_payroll(
                self.employee, self.hours_map, start_iso, end_iso
            )
            template_name = "report_fixed.json"
        else:
            rate = float(self.rate_entry.get())
            housing = float(self.housing_entry.get() or 0) if self.housing_var.get() else 0
            utilities = float(self.utilities_entry.get() or 0) if self.utilities_var.get() else 0

            rows, summary = calculate_custom_payroll(
                self.employee, self.hours_map,
                start_iso, end_iso,
                rate, housing, utilities
            )
            template_name = "report_custom.json"

        with open(self.templates_dir / template_name, encoding="utf-8") as f:
            template = json.load(f)

        filename = f"{self.employee.name}_{start_iso}_{end_iso}.pdf"
        output = self.templates_dir.parent / "Payroll" / filename

        generate_payroll_pdf(
            employee=self.employee,
            rows=rows,
            summary=summary,
            template=template,
            period_start_ui=self.start_entry.get(),
            period_end_ui=self.end_entry.get(),
            output_path=output,
        )

        if preview and os.name == "nt":
            os.startfile(output)

