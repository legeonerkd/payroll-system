import tkinter as tk
from tkinter import ttk, messagebox


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change

        self.selected_id = None

        self.name_var = tk.StringVar()
        self.rate_var = tk.StringVar()
        self.bank_var = tk.StringVar()
        self.iban_var = tk.StringVar()
        self.bic_var = tk.StringVar()

        self._build_ui()
        self._load()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)

        # ---------- TABLE ----------
        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("name", "rate", "bank", "iban", "bic"),
            show="headings",
            height=20
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("bank", text="Bank")
        self.tree.heading("iban", text="IBAN")
        self.tree.heading("bic", text="BIC")

        self.tree.column("name", width=180)
        self.tree.column("rate", width=80, anchor="center")
        self.tree.column("bank", width=140)
        self.tree.column("iban", width=200)
        self.tree.column("bic", width=100)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- FORM ----------
        form = ttk.LabelFrame(self, text="Employee details")
        form.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        def row(label, var, r):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=4)
            ttk.Entry(form, textvariable=var).grid(row=r, column=1, sticky="ew", pady=4)

        row("Full name *", self.name_var, 0)
        row("Hourly rate €/h *", self.rate_var, 1)
        row("Bank (optional)", self.bank_var, 2)
        row("IBAN (optional)", self.iban_var, 3)
        row("BIC (optional)", self.bic_var, 4)

        form.columnconfigure(1, weight=1)

        # ---------- BUTTONS ----------
        btns = ttk.Frame(form)
        btns.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Button(btns, text="Add", command=self._add).pack(fill="x", pady=2)
        ttk.Button(btns, text="Update", command=self._update).pack(fill="x", pady=2)
        ttk.Button(btns, text="Delete", command=self._delete).pack(fill="x", pady=2)

    # ======================================================
    # DATA
    # ======================================================

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.get_employees():
            self.tree.insert(
                "",
                "end",
                iid=r["id"],
                values=(
                    r["name"],
                    f"{r['rate']:.2f}",
                    r["bank"] or "",
                    r["iban"] or "",
                    r["bic"] or "",
                )
            )

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        r = next(e for e in self.db.get_employees() if e["id"] == emp_id)

        self.selected_id = emp_id
        self.name_var.set(r["name"])
        self.rate_var.set(str(r["rate"]))
        self.bank_var.set(r["bank"] or "")
        self.iban_var.set(r["iban"] or "")
        self.bic_var.set(r["bic"] or "")

    # ======================================================
    # ACTIONS
    # ======================================================

    def _parse_rate(self):
        raw = self.rate_var.get().strip()
        try:
            value = float(raw)
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            messagebox.showerror(
                "Invalid rate",
                "Hourly rate must be a positive number.\nExample: 8 or 10.5"
            )
            return None

    def _add(self):
        rate = self._parse_rate()
        if rate is None:
            return

        if not self.name_var.get().strip():
            messagebox.showerror("Missing data", "Employee name is required.")
            return

        self.db.add_employee(
            name=self.name_var.get().strip(),
            rate=rate,
            bank=self.bank_var.get().strip() or None,
            iban=self.iban_var.get().strip() or None,
            bic=self.bic_var.get().strip() or None,
        )

        self._load()
        if self.on_change:
            self.on_change()

    def _update(self):
        if not self.selected_id:
            return

        rate = self._parse_rate()
        if rate is None:
            return

        self.db.update_employee(
            emp_id=self.selected_id,
            name=self.name_var.get().strip(),
            rate=rate,
            bank=self.bank_var.get().strip() or None,
            iban=self.iban_var.get().strip() or None,
            bic=self.bic_var.get().strip() or None,
        )

        self._load()
        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self.selected_id:
            return

        if not messagebox.askyesno("Delete employee", "Are you sure?"):
            return

        self.db.delete_employee(self.selected_id)
        self.selected_id = None
        self._load()

        self.name_var.set("")
        self.rate_var.set("")
        self.bank_var.set("")
        self.iban_var.set("")
        self.bic_var.set("")

        if self.on_change:
            self.on_change()

