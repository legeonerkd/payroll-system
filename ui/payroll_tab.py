import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import os
from datetime import datetime, timedelta

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
        top = ttk.Frame(self)
        top.pack(fill="x", pady=5)

        ttk.Label(top, text="Employee").pack(side="left")
        self.employee_combo = ttk.Combobox(top, state="readonly", width=30)
        self.employee_combo.pack(side="left", padx=5)

        # ---------- period ----------
        period = ttk.Frame(self)
        period.pack(fill="x", pady=5)

        ttk.Label(period, text="From").pack(side="left")
        self.start_entry = DateEntry(period, width=12, date_pattern="yyyy-mm-dd")
        self.start_entry.pack(side="left", padx=5)

        ttk.Label(period, text="To").pack(side="left")
        self.end_entry = DateEntry(period, width=12, date_pattern="yyyy-mm-dd")
        self.end_entry.pack(side="left", padx=5)

        ttk.Button(
            period,
            text="Generate period",
            command=self._generate_period,
        ).pack(side="left", padx=10)

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

        # ---------- table ----------
        self.tree = ttk.Treeview(
            self,
            columns=("date", "day", "hours"),
            show="headings",
            height=10,
        )
        self.tree.heading("date", text="Date")
        self.tree.heading("day", text="Day")
        self.tree.heading("hours", text="Hours")

        self.tree.column("date", width=120)
        self.tree.column("day", width=120)
        self.tree.column("hours", width=80, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=10)

        self.tree.bind("<Double-1>", self._edit_hours)

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
        name = self.employee_combo.get()
        return next((e for e in self.employees if e.name == name), None)

    # ==================================================
    # PERIOD GENERATION
    # ==================================================
    def _generate_period(self):
        self.tree.delete(*self.tree.get_children())

        employee = self._get_selected_employee()
        if not employee:
            return

        start = self.start_entry.get_date()
        end = self.end_entry.get_date()

        if start > end:
            messagebox.showerror("Period", "Start date is after end date")
            return

        # load existing hours from DB
        db_rows = self.db.load_hours(
            employee.id,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
        )
        hours_map = {r["work_date"]: r["hours"] for r in db_rows}

        current = start
        while current <= end:
            iso = current.strftime("%Y-%m-%d")
            ui = current.strftime("%d.%m.%Y")
            day = current.strftime("%A")
            hours = hours_map.get(iso, 0)

            self.tree.insert(
                "",
                "end",
                iid=iso,
                values=(ui, day, hours),
            )

            current += timedelta(days=1)

    # ==================================================
    # EDIT HOURS
    # ==================================================
    def _edit_hours(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        if column != "#3" or not item:
            return

        x, y, w, h = self.tree.bbox(item, column)
        value = self.tree.set(item, "hours")

        entry = ttk.Entry(self.tree, width=6)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, value)
        entry.focus()

        def save(_):
            try:
                val = float(entry.get())
            except ValueError:
                val = 0
            self.tree.set(item, "hours", val)
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)

    # ==================================================
    # PDF
    # ==================================================
    def _generate_pdf(self, preview: bool):
        employee = self._get_selected_employee()
        if not employee:
            messagebox.showwarning("Employee", "Select employee first")
            return

        hours_map = {}
        for iid in self.tree.get_children():
            hours = float(self.tree.set(iid, "hours"))
            if hours > 0:
                hours_map[iid] = hours

        if not hours_map:
            messagebox.showwarning("Hours", "No hours in selected period")
            return

        if self.rate_mode.get() == "fixed":
            rows, summary = calculate_fixed_payroll(
                employee,
                hours_map,
                None,
                None,
            )
        else:
            rows, summary = calculate_custom_payroll(
                employee,
                hours_map,
                None,
                None,
            )

        output_dir = Path("Payroll")
        output_dir.mkdir(exist_ok=True)

        pdf_path = generate_payroll_pdf(
            employee=employee,
            rows=rows,
            summary=summary,
            template=None,
            period_start_ui=self.start_entry.get(),
            period_end_ui=self.end_entry.get(),
            output_path=output_dir,
        )

        if preview and pdf_path and pdf_path.exists():
            os.startfile(str(pdf_path))

