import tkinter as tk
from tkinter import ttk, messagebox
from ui.styles import COLORS


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change
        self.selected_id = None

        self._build_ui()
        self._load()

        # глобальный клик → сброс выделения
        self.bind_all("<Button-1>", self._global_click, add="+")

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # ---------- LEFT: LIST ----------
        left = ttk.Frame(self, padding=12)
        left.grid(row=0, column=0, sticky="nsew")

        ttk.Label(left, text="Employees", font=("Segoe UI", 11, "bold"))\
            .pack(anchor="w", pady=(0, 8))

        self.tree = ttk.Treeview(
            left,
            columns=("name", "rate", "iban"),
            show="headings"
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("iban", text="IBAN")

        self.tree.column("name", anchor="w", width=240)
        self.tree.column("rate", anchor="center", width=90)
        self.tree.column("iban", anchor="w", width=260)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- RIGHT: FORM ----------
        right = ttk.Frame(self, padding=16)
        right.grid(row=0, column=1, sticky="nsew")

        ttk.Label(right, text="Add / Edit employee",
                  font=("Segoe UI", 11, "bold"))\
            .grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # Name
        ttk.Label(right, text="Full name").grid(row=1, column=0, sticky="w")
        self.name_entry = ttk.Entry(right, width=32)
        self.name_entry.grid(row=2, column=0, columnspan=2, pady=(2, 10), sticky="ew")

        # Rate
        ttk.Label(right, text="Hourly rate (€ / h)").grid(row=3, column=0, sticky="w")
        self.rate_entry = ttk.Entry(right, width=14)
        self.rate_entry.grid(row=4, column=0, pady=(2, 10), sticky="w")

        # IBAN
        ttk.Label(right, text="IBAN (optional)").grid(row=5, column=0, sticky="w")
        self.iban_entry = ttk.Entry(right, width=32)
        self.iban_entry.grid(row=6, column=0, columnspan=2, pady=(2, 10), sticky="ew")

        # BIC
        ttk.Label(right, text="BIC (optional)").grid(row=7, column=0, sticky="w")
        self.bic_entry = ttk.Entry(right, width=32)
        self.bic_entry.grid(row=8, column=0, columnspan=2, pady=(2, 16), sticky="ew")

        # Buttons
        self.add_btn = ttk.Button(right, text="Add", command=self._add)
        self.add_btn.grid(row=9, column=0, sticky="ew", pady=4)

        self.update_btn = ttk.Button(right, text="Update", command=self._update)
        self.update_btn.grid(row=10, column=0, sticky="ew", pady=4)

        self.delete_btn = ttk.Button(right, text="Delete", command=self._delete)
        self.delete_btn.grid(row=11, column=0, sticky="ew", pady=4)

        self._update_buttons()

    # ======================================================
    # DATA
    # ======================================================

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.get_employees():
            self.tree.insert(
                "", "end", iid=r["id"],
                values=(r["name"], f"{r['rate']:.2f}", r["iban"] or "")
            )

    # ======================================================
    # EVENTS
    # ======================================================

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        row = self.db.get_employee(emp_id)

        self.selected_id = emp_id
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, row["name"])

        self.rate_entry.delete(0, tk.END)
        self.rate_entry.insert(0, row["rate"])

        self.iban_entry.delete(0, tk.END)
        if row["iban"]:
            self.iban_entry.insert(0, row["iban"])

        self.bic_entry.delete(0, tk.END)
        if row["bic"]:
            self.bic_entry.insert(0, row["bic"])

        self._update_buttons()

    def _global_click(self, event):
        # если клик не по Treeview — сбрасываем выделение
        if not str(event.widget).endswith("treeview"):
            self.tree.selection_remove(self.tree.selection())
            self._clear_form()

    # ======================================================
    # ACTIONS
    # ======================================================

    def _add(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Employee", "Name is required")
            return

        self.db.add_employee(
            name=name,
            rate=float(self.rate_entry.get() or 0),
            iban=self.iban_entry.get().strip() or None,
            bic=self.bic_entry.get().strip() or None
        )
        self._clear_form()
        self._load()
        if self.on_change:
            self.on_change()

    def _update(self):
        if not self.selected_id:
            return

        self.db.update_employee(
            emp_id=self.selected_id,
            name=self.name_entry.get().strip(),
            rate=float(self.rate_entry.get() or 0),
            iban=self.iban_entry.get().strip() or None,
            bic=self.bic_entry.get().strip() or None
        )
        self._clear_form()
        self._load()
        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self.selected_id:
            return

        if not messagebox.askyesno("Delete", "Delete this employee?"):
            return

        self.db.delete_employee(self.selected_id)
        self._clear_form()
        self._load()
        if self.on_change:
            self.on_change()

    # ======================================================
    # HELPERS
    # ======================================================

    def _clear_form(self):
        self.selected_id = None
        for e in (self.name_entry, self.rate_entry, self.iban_entry, self.bic_entry):
            e.delete(0, tk.END)
        self._update_buttons()

    def _update_buttons(self):
        has_name = bool(self.name_entry.get().strip())
        has_sel = self.selected_id is not None

        self.add_btn.configure(state="normal" if has_name and not has_sel else "disabled")
        self.update_btn.configure(state="normal" if has_sel else "disabled")
        self.delete_btn.configure(state="normal" if has_sel else "disabled")

