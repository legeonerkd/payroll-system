import tkinter as tk
from tkinter import ttk, messagebox
from datetime import timedelta

from tkcalendar import DateEntry
from ui.styles import COLORS


class Card(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db, templates_dir=None):
        super().__init__(parent, style="App.TFrame")

        self.db = db
        self.templates_dir = templates_dir
        self.employee_map = {}

        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_enabled = tk.BooleanVar(value=False)
        self.rent_enabled = tk.BooleanVar(value=False)
        self.utilities_value = tk.StringVar(value="0")
        self.rent_value = tk.StringVar(value="0")

        self._init_styles()
        self._build_ui()
        self._load_employees()

    # ======================================================
    # PUBLIC
    # ======================================================

    def refresh_employees(self):
        self._load_employees()

    # ======================================================
    # STYLES
    # ======================================================

    def _init_styles(self):
        style = ttk.Style()
        style.configure("Payroll.Treeview", font=("Segoe UI", 11), rowheight=26)
        style.configure("Payroll.Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.configure("Summary.TLabel", foreground=COLORS["text_secondary"])

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---------- TOP ----------
        top = Card(self)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=4)

        ttk.Label(top, text="Employee").grid(row=0, column=0, padx=4)
        self.employee_cb = ttk.Combobox(top, state="readonly", width=26)
        self.employee_cb.grid(row=0, column=1, padx=4)

        ttk.Label(top, text="From").grid(row=0, column=2, padx=4)
        self.from_entry = DateEntry(top, width=11, date_pattern="dd-mm-yyyy")
        self.from_entry.grid(row=0, column=3, padx=4)

        ttk.Label(top, text="To").grid(row=0, column=4, padx=4)
        self.to_entry = DateEntry(top, width=11, date_pattern="dd-mm-yyyy")
        self.to_entry.grid(row=0, column=5, padx=4)

        ttk.Button(top, text="Generate", command=self._generate_period)\
            .grid(row=0, column=6, padx=6)

        # ---------- OPTIONS ----------
        opts = Card(self)
        opts.grid(row=1, column=0, sticky="ew", padx=12, pady=4)

        ttk.Radiobutton(opts, text="Fixed (8 €/h)",
                        variable=self.rate_mode, value="fixed")\
            .grid(row=0, column=0, padx=6)

        ttk.Radiobutton(opts, text="Custom rate",
                        variable=self.rate_mode, value="custom")\
            .grid(row=0, column=1, padx=6)

        ttk.Separator(opts, orient="vertical")\
            .grid(row=0, column=2, sticky="ns", padx=8)

        ttk.Checkbutton(opts, text="Utilities",
                        variable=self.utilities_enabled)\
            .grid(row=0, column=3)

        ttk.Entry(opts, width=7, textvariable=self.utilities_value)\
            .grid(row=0, column=4, padx=4)

        ttk.Checkbutton(opts, text="Rental",
                        variable=self.rent_enabled)\
            .grid(row=0, column=5)

        ttk.Entry(opts, width=7, textvariable=self.rent_value)\
            .grid(row=0, column=6, padx=4)

        # ---------- TABLE ----------
        table = Card(self)
        table.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            table,
            columns=("date", "day", "hours"),
            show="headings",
            style="Payroll.Treeview"
        )

        self.tree.heading("date", text="Date")
        self.tree.heading("day", text="Day")
        self.tree.heading("hours", text="Hours")

        self.tree.column("date", stretch=True, minwidth=200, anchor="w")
        self.tree.column("day", stretch=True, minwidth=160, anchor="center")
        self.tree.column("hours", stretch=True, minwidth=120, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=6)

        sb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns", pady=6)
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.bind("<Double-1>", self._edit_hours)

        # ---------- BOTTOM ----------
        bottom = Card(self)
        bottom.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        bottom.columnconfigure(0, weight=1)

        ttk.Button(bottom, text="Save", command=self._save)\
            .grid(row=0, column=0, sticky="e", padx=6)

        ttk.Button(bottom, text="Preview PDF", command=self._preview_pdf)\
            .grid(row=0, column=1, sticky="e", padx=6)

    # ======================================================
    # DATA
    # ======================================================

    def _load_employees(self):
        self.employee_map.clear()
        for r in self.db.get_employees():
            self.employee_map[r["name"]] = r
        self.employee_cb["values"] = list(self.employee_map.keys())

    # ======================================================
    # PERIOD
    # ======================================================

    def _generate_period(self):
        if not self.employee_cb.get():
            messagebox.showwarning("Payroll", "Select employee first")
            return

        start = self.from_entry.get_date()
        end = self.to_entry.get_date()

        self.tree.delete(*self.tree.get_children())

        cur = start
        while cur <= end:
            hours = "10.0" if cur.weekday() < 6 else "0"
            self.tree.insert(
                "",
                "end",
                values=(
                    cur.strftime("%d-%m-%Y"),
                    cur.strftime("%A"),
                    hours
                )
            )
            cur += timedelta(days=1)

    # ======================================================
    # HOURS EDIT
    # ======================================================

    def _edit_hours(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if col != "#3" or not item:
            return

        x, y, w, h = self.tree.bbox(item, col)
        spin = ttk.Spinbox(
            self.tree,
            from_=0,
            to=24,
            increment=0.5,
            justify="center"
        )
        spin.place(x=x, y=y, width=w, height=h)
        spin.set(self.tree.set(item, "hours"))

        def save(_=None):
            self.tree.set(item, "hours", spin.get())
            spin.destroy()

        spin.bind("<Return>", save)
        spin.bind("<FocusOut>", save)

    # ======================================================
    # ACTIONS
    # ======================================================

    def _save(self):
        messagebox.showinfo("Payroll", "Hours saved")

    def _preview_pdf(self):
        if not self.employee_cb.get():
            messagebox.showwarning("PDF", "Select employee first")
            return

        if not self.tree.get_children():
            messagebox.showwarning("PDF", "No data to preview")
            return

        emp = self.employee_map[self.employee_cb.get()]

        iban = emp["iban"] if "iban" in emp.keys() else None
        bic = emp["bic"] if "bic" in emp.keys() else None
        bank_name = emp["bank"] if "bank" in emp.keys() else None

        from services.report_service import preview_payroll_pdf

        preview_payroll_pdf(
            employee_name=emp["name"],
            employee_rate=emp["rate"],
            rows=[self.tree.item(i)["values"] for i in self.tree.get_children()],
            rate_mode=self.rate_mode.get(),
            utilities=self.utilities_value.get() if self.utilities_enabled.get() else None,
            rental=self.rent_value.get() if self.rent_enabled.get() else None,
            period_from=self.from_entry.get(),
            period_to=self.to_entry.get(),
            iban=iban,
            bic=bic,
            bank_name=bank_name,
            templates_dir=self.templates_dir
        )
