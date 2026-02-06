import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta

from tkcalendar import DateEntry
from services.report_service import preview_payroll_pdf

FIXED_RATE = 8.0
DEFAULT_HOURS = 10.0
HOUR_STEP = 0.5


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db

        self.employee_map = {}
        self.days_data = {}

        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_var = tk.StringVar(value="")
        self.rental_var = tk.StringVar(value="")

        self._editor = None

        self._build_ui()
        self._load_employees()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---------- LEFT ----------
        left = ttk.Frame(self, padding=14, width=320)
        left.grid(row=0, column=0, sticky="ns")
        left.grid_propagate(False)

        ttk.Label(left, text="Employee").pack(anchor="w")
        self.employee_cb = ttk.Combobox(left, state="readonly")
        self.employee_cb.pack(fill="x", pady=(0, 10))

        ttk.Label(left, text="Period").pack(anchor="w")
        self.from_entry = DateEntry(left, date_pattern="dd-mm-yyyy", firstweekday="monday")
        self.to_entry = DateEntry(left, date_pattern="dd-mm-yyyy", firstweekday="monday")
        self.from_entry.pack(fill="x")
        self.to_entry.pack(fill="x", pady=(0, 6))

        ttk.Button(left, text="Generate period", command=self._generate_period)\
            .pack(fill="x", pady=(0, 12))

        ttk.Label(left, text="Rate").pack(anchor="w")
        ttk.Radiobutton(left, text="Fixed 8 €/h",
                        variable=self.rate_mode, value="fixed").pack(anchor="w")
        ttk.Radiobutton(left, text="Employee rate",
                        variable=self.rate_mode, value="custom").pack(anchor="w")

        ttk.Label(left, text="Deductions").pack(anchor="w", pady=(12, 0))
        ttk.Label(left, text="Utilities").pack(anchor="w")
        ttk.Entry(left, textvariable=self.utilities_var).pack(fill="x")
        ttk.Label(left, text="Rental").pack(anchor="w")
        ttk.Entry(left, textvariable=self.rental_var).pack(fill="x")

        ttk.Button(left, text="Preview PDF", command=self._preview_pdf)\
            .pack(fill="x", pady=(18, 4))
        ttk.Button(left, text="Save PDF", command=self._save_pdf)\
            .pack(fill="x")

        # ---------- RIGHT ----------
        right = ttk.Frame(self, padding=12)
        right.grid(row=0, column=1, sticky="nsew")

        self.tree = ttk.Treeview(
            right,
            columns=("date", "day", "hours"),
            show="headings",
        )
        self.tree.heading("date", text="Date", anchor="center")
        self.tree.heading("day", text="Day", anchor="center")
        self.tree.heading("hours", text="Hours", anchor="center")

        self.tree.column("date", width=120, anchor="center")
        self.tree.column("day", width=170, anchor="center")
        self.tree.column("hours", width=80, anchor="center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._start_edit_hours)

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
    # PERIOD
    # ======================================================

    def _generate_period(self):
        self.tree.delete(*self.tree.get_children())
        self.days_data.clear()

        start = self.from_entry.get_date()
        end = self.to_entry.get_date()

        d = start
        while d <= end:
            is_sunday = d.weekday() == 6
            hours = 0.0 if is_sunday else DEFAULT_HOURS

            key = d.strftime("%Y-%m-%d")
            self.days_data[key] = hours

            self.tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    d.strftime("%d-%m-%Y"),
                    d.strftime("%A"),
                    f"{hours:.1f}",
                )
            )
            d += timedelta(days=1)

    # ======================================================
    # HOURS EDIT
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
            self.tree,
            from_=0,
            to=24,
            increment=HOUR_STEP,
            justify="center"
        )
        self._editor.delete(0, "end")
        self._editor.insert(0, f"{value:.1f}")
        self._editor.place(x=x, y=y, width=w, height=h)
        self._editor.focus()

        self._editor.bind("<Return>", lambda e: self._save_hours(row_id))
        self._editor.bind("<FocusOut>", lambda e: self._save_hours(row_id))

    def _save_hours(self, row_id):
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

    # ======================================================
    # PDF
    # ======================================================

    def _preview_pdf(self):
        try:
            self._call_pdf()
        except Exception as e:
            messagebox.showerror("PDF", str(e))

    def _save_pdf(self):
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
            )
            if not path:
                return
            self._call_pdf(save_path=path)
            messagebox.showinfo("PDF", "PDF saved successfully")
        except Exception as e:
            messagebox.showerror("PDF", str(e))

    def _call_pdf(self, save_path=None):
        name = self.employee_cb.get()
        if not name:
            raise ValueError("Employee not selected")

        emp = self.employee_map[name]

        rows = []
        for iid in self.tree.get_children():
            date, day, hours = self.tree.item(iid)["values"]
            rows.append((date, day, hours))

        preview_payroll_pdf(
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
        )
