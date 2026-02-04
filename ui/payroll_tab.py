import tkinter as tk
from tkinter import ttk
from datetime import timedelta
from pathlib import Path

from tkcalendar import DateEntry

from ui.styles import COLORS
from core.models import Employee
from services.payroll_service import (
    calculate_fixed_payroll,
    calculate_custom_payroll,
)
from services.report_service import generate_payroll_pdf


class Card(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db, templates_dir):
        super().__init__(parent, style="App.TFrame")

        self.db = db
        self.templates_dir = Path(templates_dir)

        self.employees: list[Employee] = []

        self.current_days = []
        self.hour_vars = []

        # rate & deductions
        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_var = tk.BooleanVar()
        self.rental_var = tk.BooleanVar()

        # summary vars
        self.total_hours_var = tk.StringVar(value="0.00")
        self.gross_var = tk.StringVar(value="0.00 €")
        self.utilities_var_ui = tk.StringVar(value="0.00 €")
        self.rental_var_ui = tk.StringVar(value="0.00 €")
        self.net_var = tk.StringVar(value="0.00 €")

        self._init_styles()
        self._build_ui()
        self._load_employees()

    # ======================================================
    # REQUIRED BY app.py
    # ======================================================

    def refresh_employees(self):
        current = self.employee_cb.get()
        self._load_employees()
        if current in self.employee_cb["values"]:
            self.employee_cb.set(current)

    # ======================================================
    # STYLES
    # ======================================================

    def _init_styles(self):
        style = ttk.Style()
        style.configure("App.TFrame", background=COLORS["app_bg"])
        style.configure(
            "Card.TFrame",
            background=COLORS["card_bg"],
            relief="solid",
            borderwidth=1,
        )
        style.configure("CardTitle.TLabel", font=("Segoe UI", 10, "bold"))

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        # ---------- SETTINGS CARD ----------
        settings = Card(self)
        settings.pack(fill="x", padx=12, pady=8)

        ttk.Label(settings, text="Payroll settings", style="CardTitle.TLabel") \
            .pack(anchor="w", padx=12, pady=(8, 4))

        form = ttk.Frame(settings)
        form.pack(fill="x", padx=12, pady=8)

        ttk.Label(form, text="Employee").grid(row=0, column=0, sticky="w")
        self.employee_cb = ttk.Combobox(form, state="readonly", width=28)
        self.employee_cb.grid(row=0, column=1, padx=8)

        ttk.Label(form, text="From").grid(row=1, column=0, sticky="w", pady=4)
        self.from_date = DateEntry(form, width=12)
        self.from_date.grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="To").grid(row=1, column=2, sticky="w", padx=12)
        self.to_date = DateEntry(form, width=12)
        self.to_date.grid(row=1, column=3, sticky="w")

        ttk.Button(form, text="Generate period", command=self.generate_period) \
            .grid(row=1, column=4, padx=12)

        # ---------- RATE CARD ----------
        rate = Card(self)
        rate.pack(fill="x", padx=12, pady=8)

        ttk.Label(rate, text="Rate", style="CardTitle.TLabel") \
            .pack(anchor="w", padx=12, pady=(8, 4))

        rate_body = ttk.Frame(rate)
        rate_body.pack(fill="x", padx=12, pady=8)

        ttk.Radiobutton(
            rate_body,
            text="Fixed rate (8 €/h)",
            variable=self.rate_mode,
            value="fixed",
            command=self._on_rate_change,
        ).pack(side="left", padx=8)

        ttk.Radiobutton(
            rate_body,
            text="Custom employee rate",
            variable=self.rate_mode,
            value="custom",
            command=self._on_rate_change,
        ).pack(side="left", padx=8)

        # ---------- DEDUCTIONS CARD ----------
        ded = Card(self)
        ded.pack(fill="x", padx=12, pady=8)

        ttk.Label(ded, text="Deductions", style="CardTitle.TLabel") \
            .pack(anchor="w", padx=12, pady=(8, 4))

        body = ttk.Frame(ded)
        body.pack(fill="x", padx=12, pady=8)

        ttk.Checkbutton(
            body, text="Utilities deduction",
            variable=self.utilities_var,
            command=self._recalculate_totals
        ).grid(row=0, column=0, sticky="w")

        self.utilities_entry = tk.Entry(body, width=10)
        self.utilities_entry.grid(row=0, column=1, padx=6)

        ttk.Checkbutton(
            body, text="Rental deduction",
            variable=self.rental_var,
            command=self._recalculate_totals
        ).grid(row=0, column=2, sticky="w", padx=(20, 0))

        self.rental_entry = tk.Entry(body, width=10)
        self.rental_entry.grid(row=0, column=3, padx=6)

        # ---------- TABLE CARD ----------
        table_card = Card(self)
        table_card.pack(fill="both", expand=True, padx=12, pady=8)

        ttk.Label(table_card, text="Working hours", style="CardTitle.TLabel") \
            .pack(anchor="w", padx=12, pady=(8, 4))

        self.table_container = ttk.Frame(table_card)
        self.table_container.pack(fill="both", expand=True, padx=12, pady=8)

        # ---------- SUMMARY CARD ----------
        summary = Card(self)
        summary.pack(fill="x", padx=12, pady=8)

        ttk.Label(summary, text="Summary", style="CardTitle.TLabel") \
            .pack(anchor="w", padx=12, pady=(8, 4))

        grid = ttk.Frame(summary)
        grid.pack(fill="x", padx=12, pady=8)

        self._summary_row(grid, "Total hours", self.total_hours_var, 0)
        self._summary_row(grid, "Gross amount", self.gross_var, 1)
        self._summary_row(grid, "Utilities", self.utilities_var_ui, 2, negative=True)
        self._summary_row(grid, "Rental", self.rental_var_ui, 3, negative=True)
        self._summary_row(grid, "Net amount", self.net_var, 4, bold=True)

        self._on_rate_change()

    # ======================================================
    # HELPERS
    # ======================================================

    def _summary_row(self, parent, label, var, row, negative=False, bold=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        fg = COLORS["negative"] if negative else COLORS["positive"]
        font = ("Segoe UI", 10, "bold") if bold else ("Segoe UI", 10)
        tk.Label(parent, textvariable=var, font=font,
                 fg=fg, bg=COLORS["card_bg"]) \
            .grid(row=row, column=1, sticky="e", padx=8)

    def _on_rate_change(self):
        custom = self.rate_mode.get() == "custom"
        state = "normal" if custom else "disabled"

        self.utilities_entry.configure(state=state)
        self.rental_entry.configure(state=state)

        if not custom:
            self.utilities_var.set(False)
            self.rental_var.set(False)
            self.utilities_entry.delete(0, tk.END)
            self.rental_entry.delete(0, tk.END)

        self._recalculate_totals()

    # ======================================================
    # DATA
    # ======================================================

    def _load_employees(self):
        rows = self.db.get_employees()
        self.employees = [
            Employee(
                id=r["id"],
                name=r["name"],
                rate=r["rate"],
                bank_name=r["bank_name"],
                iban=r["iban"],
                bic=r["bic"],
                has_bank_account=bool(r["iban"] or r["bic"]),
            )
            for r in rows
        ]
        self.employee_cb["values"] = [e.name for e in self.employees]
        if self.employees:
            self.employee_cb.current(0)

    # ======================================================
    # PERIOD / TABLE / TOTALS (без изменений логики)
    # ======================================================

    def generate_period(self):
        start = self.from_date.get_date()
        end = self.to_date.get_date()

        self.current_days.clear()
        d = start
        while d <= end:
            self.current_days.append(d)
            d += timedelta(days=1)

        self._build_table()

    def _build_table(self):
        for w in self.table_container.winfo_children():
            w.destroy()

        self.hour_vars.clear()

        for i, day in enumerate(self.current_days):
            ttk.Label(
                self.table_container,
                text=f"{day.strftime('%d.%m.%Y')} — {day.strftime('%A')}",
            ).grid(row=i, column=0, sticky="w", pady=2)

            var = tk.DoubleVar(value=0.0)
            spin = tk.Spinbox(
                self.table_container,
                from_=0, to=24, increment=0.5,
                width=6, textvariable=var,
                command=self._recalculate_totals
            )
            spin.grid(row=i, column=1, pady=2)
            self.hour_vars.append(var)

        self._recalculate_totals()

    def _recalculate_totals(self):
        if not self.current_days:
            return

        hours_map = {
            d.strftime("%Y-%m-%d"): float(v.get())
            for d, v in zip(self.current_days, self.hour_vars)
        }

        employee = self.employees[self.employee_cb.current()]

        utilities = float(self.utilities_entry.get() or 0) if self.utilities_var.get() else 0.0
        rental = float(self.rental_entry.get() or 0) if self.rental_var.get() else 0.0

        if self.rate_mode.get() == "fixed":
            _, summary = calculate_fixed_payroll(employee, hours_map)
        else:
            _, summary = calculate_custom_payroll(
                employee,
                hours_map,
                housing=rental,
                utilities=utilities,
            )

        self.total_hours_var.set(f"{summary.total_hours:.2f}")
        self.gross_var.set(f"{summary.gross_amount:.2f} €")
        self.utilities_var_ui.set(f"-{summary.utilities_deduction:.2f} €")
        self.rental_var_ui.set(f"-{summary.housing_deduction:.2f} €")
        self.net_var.set(f"{summary.net_amount:.2f} €")

