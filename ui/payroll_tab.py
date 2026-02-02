import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import os

from tkcalendar import DateEntry

from services.payroll_service import (
    calculate_fixed_payroll,
    calculate_custom_payroll,
)
from services.report_service import generate_payroll_pdf
from core.models import Employee


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db, templates_dir: Path):
        super().__init__(parent)
        self.db = db
        self.templates_dir = templates_dir

        self._build_ui()
        self._load_employees()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        # ---------- employee ----------
        emp_frame = ttk.Frame(self)
        emp_frame.pack(fill="x", pady=5)

        ttk.Label(emp_frame, text="Employee").pack(side="left")
        self.employee_combo = ttk.Combobox(emp_frame, state="readonly", width=30)
        self.employee_combo.pack(side="left", padx=5)

        # ---------- period (calendar) ----------
        period = ttk.Frame(self)
        period.pack(fill="x", pady=5)

        ttk.Label(period, text="From").pack(side="left")
        self.start_entry = DateEntry(
            period,
            width=12,
            date_pattern="yyyy-mm-dd"
        )
        self.start_entry.pack(side="left", padx=5)

        ttk.Label(period, text="To").pack(side="left")
        self.end_entry = DateEntry(
            period,
            width=12,
            date_pattern="yyyy-mm-dd"
        )
        self.end_entry.pack(side="left", padx=5)

        # ---------- rate mode ----------
        self.rate_mode = tk.StringVar(value="fixed")

        rate_frame = ttk.Frame(self)
        rate_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            rate_frame,
            text="Fixed rate (8 €/h)",
            variable=self.rate_mode,
            value="fixed",
        ).pack(side="left")

        ttk.Radiobutton(
            rate_frame,
            text="Employee rate",
            variable=self.rate_mode,
            value="custom",
        ).pack(side="left", padx=10)

        # ---------- buttons ----------
        ttk.Button(
            self,
            text="Preview PDF",
            command=lambda: self._generate_pdf(preview=True),
        ).pack(fill="x", pady=10)

    # ==================================================
    # DATA
    # ==================================================
    def _load_employees(self):
        self.employees = [Employee.from_row(r) for r in self.db.get_employees()]
        self.employee_combo["values"] = [e.name for e in self.employees]
        if self.employees:
            self.employee_combo.current(0)

    def _get_selected_employee(self):
        if not self.employee_combo.get():
            return None
        name = self.employee_combo.get()
        return next((e for e in self.employees if e.name == name), None)

    def _period_start(self):
        return self.start_entry.get_date().strftime("%Y-%m-%d")

    def _period_end(self):
        return self.end_entry.get_date().strftime("%Y-%m-%d")

    def _period_start_ui(self):
        return self.start_entry.get_date().strftime("%d.%m.%Y")

    def _period_end_ui(self):
        return self.end_entry.get_date().strftime("%d.%m.%Y")

    def _is_fixed_rate(self):
        return self.rate_mode.get() == "fixed"

    def _get_hours_map(self):
        employee = self._get_selected_employee()
        if not employee:
            return {}

        rows = self.db.load_hours(
            employee.id,
            self._period_start(),
            self._period_end(),
        )

        return {r["work_date"]: r["hours"] for r in rows}

    # ==================================================
    # PDF
    # ==================================================
    def _generate_pdf(self, preview: bool):
        employee = self._get_selected_employee()
        if not employee:
            messagebox.showwarning("Employee", "Select employee first")
            return

        hours_map = self._get_hours_map()
        if not hours_map:
            messagebox.showwarning("Hours", "No hours for selected period")
            return

        if self._is_fixed_rate():
            rows, summary = calculate_fixed_payroll(
                employee,
                hours_map,
                self._period_start(),
                self._period_end(),
            )
        else:
            rows, summary = calculate_custom_payroll(
                employee,
                hours_map,
                self._period_start(),
                self._period_end(),
            )

        output_dir = Path("Payroll")
        output_dir.mkdir(exist_ok=True)

        pdf_path = generate_payroll_pdf(
            employee=employee,
            rows=rows,
            summary=summary,
            template=None,
            period_start_ui=self._period_start_ui(),
            period_end_ui=self._period_end_ui(),
            output_path=output_dir,
        )

        if preview and pdf_path and pdf_path.exists():
            os.startfile(str(pdf_path))
        elif preview:
            messagebox.showerror("PDF", "PDF file was not created")

