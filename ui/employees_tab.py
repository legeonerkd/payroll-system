import tkinter as tk
from tkinter import ttk, messagebox


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change
        self.selected_id = None
        self.employee_cache = {}

        # vars
        self.name_var = tk.StringVar()
        self.rate_var = tk.StringVar()
        self.bank_var = tk.StringVar()
        self.iban_var = tk.StringVar()
        self.bic_var = tk.StringVar()

        for v in (
            self.name_var,
            self.rate_var,
            self.bank_var,
            self.iban_var,
            self.bic_var,
        ):
            v.trace_add("write", lambda *_: self._update_buttons())

        self._build_ui()
        self._load()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # ---------- LEFT (TABLE) ----------
        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="nsew")

        ttk.Label(
            left,
            text="Employees",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 8))

        self.tree = ttk.Treeview(
            left,
            columns=("name", "rate", "bank", "iban", "bic"),
            show="headings"
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("bank", text="Bank")
        self.tree.heading("iban", text="IBAN")
        self.tree.heading("bic", text="BIC")

        self.tree.column("name", width=180)
        self.tree.column("rate", width=80, anchor="center")
        self.tree.column("bank", width=160)
        self.tree.column("iban", width=220)
        self.tree.column("bic", width=120)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- RIGHT (FORM) ----------
        right = ttk.Frame(self, padding=16)
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Label(
            right,
            text="Add / Edit employee",
            font=("Segoe UI", 11, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(right, text="Full name *").grid(row=1, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.name_var, width=32)\
            .grid(row=2, column=0, columnspan=2, pady=(2, 10), sticky="ew")

        ttk.Label(right, text="Hourly rate (€ / h)").grid(row=3, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.rate_var, width=14)\
            .grid(row=4, column=0, pady=(2, 10), sticky="w")

        ttk.Label(right, text="Bank name (optional)").grid(row=5, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.bank_var, width=32)\
            .grid(row=6, column=0, columnspan=2, pady=(2, 10), sticky="ew")

        ttk.Label(right, text="IBAN (optional)").grid(row=7, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.iban_var, width=32)\
            .grid(row=8, column=0, columnspan=2, pady=(2, 10), sticky="ew")

        ttk.Label(right, text="BIC (optional)").grid(row=9, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.bic_var, width=32)\
            .grid(row=10, column=0, columnspan=2, pady=(2, 16), sticky="ew")

        self.add_btn = ttk.Button(right, text="Add", command=self._add)
        self.add_btn.grid(row=11, column=0, sticky="ew", pady=4)

        self.update_btn = ttk.Button(right, text="Update", command=self._update)
        self.update_btn.grid(row=12, column=0, sticky="ew", pady=4)

        self.delete_btn = ttk.Button(right, text="Delete", command=self._delete)
        self.delete_btn.grid(row=13, column=0, sticky="ew", pady=4)

        self._update_buttons()

    # ======================================================
    # DATA
    # ======================================================

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        self.employee_cache.clear()

        for r in self.db.get_employees():
            self.employee_cache[r["id"]] = r
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

    # ======================================================
    # EVENTS
    # ======================================================

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        r = self.employee_cache.get(emp_id)
        if not r:
            return

        self.selected_id = emp_id

        self.name_var.set(r["name"])
        self.rate_var.set(str(r["rate"]))
        self.bank_var.set(r["bank"] or "")
        self.iban_var.set(r["iban"] or "")
        self.bic_var.set(r["bic"] or "")

        self._update_buttons()

    # ======================================================
    # ACTIONS
    # ======================================================

    def _add(self):
        if not self.name_var.get().strip():
            messagebox.showwarning("Employee", "Name is required")
            return

        self.db.add_employee(
            name=self.name_var.get().strip(),
            rate=float(self.rate_var.get() or 0),
            bank=self.bank_var.get().strip() or None,
            iban=self.iban_var.get().strip() or None,
            bic=self.bic_var.get().strip() or None,
        )
        self._reload()

    def _update(self):
        if not self.selected_id:
            return

        self.db.conn.execute(
            """
            UPDATE employees
            SET name=?, rate=?, bank=?, iban=?, bic=?
            WHERE id=?
            """,
            (
                self.name_var.get().strip(),
                float(self.rate_var.get() or 0),
                self.bank_var.get().strip() or None,
                self.iban_var.get().strip() or None,
                self.bic_var.get().strip() or None,
                self.selected_id,
            )
        )
        self.db.conn.commit()
        self._reload()

    def _delete(self):
        if not self.selected_id:
            return

        if not messagebox.askyesno("Delete", "Delete this employee?"):
            return

        self.db.delete_employee(self.selected_id)
        self._reload()

    # ======================================================
    # HELPERS
    # ======================================================

    def _reload(self):
        self._clear_form()
        self._load()
        if self.on_change:
            self.on_change()

    def _clear_form(self):
        self.selected_id = None
        for v in (
            self.name_var,
            self.rate_var,
            self.bank_var,
            self.iban_var,
            self.bic_var,
        ):
            v.set("")
        self._update_buttons()

    def _update_buttons(self):
        has_name = bool(self.name_var.get().strip())
        has_sel = self.selected_id is not None

        self.add_btn.configure(state="normal" if has_name and not has_sel else "disabled")
        self.update_btn.configure(state="normal" if has_sel else "disabled")
        self.delete_btn.configure(state="normal" if has_sel else "disabled")

