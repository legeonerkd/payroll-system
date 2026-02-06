import tkinter as tk
from tkinter import ttk, messagebox
from datetime import timedelta
from tkcalendar import DateEntry

FIXED_RATE = 8.0


class Card(ttk.Frame):
    def __init__(self, parent, padding=14):
        super().__init__(parent, style="Card.TFrame")
        self.inner = ttk.Frame(self, padding=padding)
        self.inner.pack(fill="both", expand=True)


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.employee_map = {}

        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_enabled = tk.BooleanVar(value=False)
        self.utilities_value = tk.StringVar(value="0")
        self.rent_enabled = tk.BooleanVar(value=False)
        self.rent_value = tk.StringVar(value="0")

        self._build_ui()
        self._load_employees()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # ---------- CARD 1: EMPLOYEE / PERIOD ----------
        card_top = Card(self)
        card_top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        c = card_top.inner

        ttk.Label(c, text="Employee").grid(row=0, column=0, sticky="w")
        self.employee_cb = ttk.Combobox(c, state="readonly", width=32)
        self.employee_cb.grid(row=1, column=0, padx=(0, 18), pady=(4, 0))

        ttk.Label(c, text="From").grid(row=0, column=1, sticky="w")
        self.from_entry = DateEntry(c, width=14, date_pattern="dd-mm-yyyy")
        self.from_entry.grid(row=1, column=1, pady=(4, 0))

        ttk.Label(c, text="To").grid(row=0, column=2, sticky="w")
        self.to_entry = DateEntry(c, width=14, date_pattern="dd-mm-yyyy")
        self.to_entry.grid(row=1, column=2, padx=(8, 18), pady=(4, 0))

        ttk.Button(c, text="Generate", command=self._generate_period)\
            .grid(row=1, column=3, sticky="s")

        # ---------- CARD 2: RATE ----------
        card_rate = Card(self)
        card_rate.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        r = card_rate.inner

        ttk.Label(r, text="Rate").grid(row=0, column=0, sticky="w")

        ttk.Radiobutton(
            r, text="Fixed (8 €/h)",
            variable=self.rate_mode, value="fixed",
            command=self._update_deductions_state
        ).grid(row=1, column=0, padx=(0, 30), sticky="w")

        ttk.Radiobutton(
            r, text="Custom employee rate",
            variable=self.rate_mode, value="custom",
            command=self._update_deductions_state
        ).grid(row=1, column=1, sticky="w")

        # ---------- CARD 3: DEDUCTIONS ----------
        card_ded = Card(self)
        card_ded.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        d = card_ded.inner

        ttk.Label(d, text="Deductions").grid(row=0, column=0, sticky="w")

        self.util_cb = ttk.Checkbutton(d, text="Utilities", variable=self.utilities_enabled)
        self.util_cb.grid(row=1, column=0, sticky="w")

        self.util_entry = ttk.Entry(d, width=14, textvariable=self.utilities_value)
        self.util_entry.grid(row=1, column=1, padx=(8, 24))

        self.rent_cb = ttk.Checkbutton(d, text="Rental", variable=self.rent_enabled)
        self.rent_cb.grid(row=1, column=2, sticky="w")

        self.rent_entry = ttk.Entry(d, width=14, textvariable=self.rent_value)
        self.rent_entry.grid(row=1, column=3, padx=(8, 0))

        self._update_deductions_state()

        # ---------- CARD 4: TABLE ----------
        card_table = Card(self)
        card_table.grid(row=3, column=0, sticky="nsew", padx=12, pady=6)
        card_table.inner.columnconfigure(0, weight=1)
        card_table.inner.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            card_table.inner,
            columns=("date", "day", "hours"),
            show="headings"
        )

        self.tree.heading("date", text="Date", anchor="center")
        self.tree.heading("day", text="Day", anchor="center")
        self.tree.heading("hours", text="Hours", anchor="center")

        self.tree.column("date", anchor="center", width=140)
        self.tree.column("day", anchor="center", width=160)
        self.tree.column("hours", anchor="center", width=100)

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._edit_hours)

        # ---------- CARD 5: ACTIONS ----------
        card_actions = Card(self)
        card_actions.grid(row=4, column=0, sticky="e", padx=12, pady=(6, 12))
        a = card_actions.inner

        ttk.Button(a, text="Preview PDF", command=self._preview_pdf)\
            .grid(row=0, column=0, padx=8)
        ttk.Button(a, text="Save", command=self._save)\
            .grid(row=0, column=1)

    # ======================================================
    # LOGIC
    # ======================================================

    def _update_deductions_state(self):
        state = "normal" if self.rate_mode.get() == "custom" else "disabled"
        for w in (self.util_cb, self.util_entry, self.rent_cb, self.rent_entry):
            w.configure(state=state)

    def _load_employees(self):
        self.employee_map = {r["name"]: r for r in self.db.get_employees()}
        self.employee_cb["values"] = list(self.employee_map.keys())

    def _generate_period(self):
        if not self.employee_cb.get():
            messagebox.showwarning("Payroll", "Select employee")
            return

        self.tree.delete(*self.tree.get_children())

        cur = self.from_entry.get_date()
        end = self.to_entry.get_date()

        while cur <= end:
            self.tree.insert(
                "", "end",
                values=(
                    cur.strftime("%d-%m-%Y"),
                    cur.strftime("%A"),
                    "10.0" if cur.weekday() < 6 else "0"
                )
            )
            cur += timedelta(days=1)

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
            justify="center",
            width=6
        )
        spin.place(x=x, y=y, width=w, height=h)
        spin.set(self.tree.set(item, "hours"))

        def save(_=None):
            self.tree.set(item, "hours", spin.get())
            spin.destroy()

        spin.bind("<Return>", save)
        spin.bind("<FocusOut>", save)

    # ------------------------------------------------------

    def _save(self):
        messagebox.showinfo("Payroll", "Saved")

    def _preview_pdf(self):
        messagebox.showinfo("PDF", "Preview")

