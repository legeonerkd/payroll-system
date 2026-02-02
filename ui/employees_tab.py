import tkinter as tk
from tkinter import ttk, messagebox

from core.db import Database


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.db = db

        self._build_ui()
        self._load_employees()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        self.tree = ttk.Treeview(
            self,
            columns=("name", "rate", "bank"),
            show="headings",
            height=12
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate")
        self.tree.heading("bank", text="Bank account")
        self.tree.pack(fill="both", expand=True, pady=10)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = ttk.Frame(self)
        form.pack(pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=0)
        ttk.Label(form, text="Rate").grid(row=0, column=1)

        self.name_entry = ttk.Entry(form, width=25)
        self.rate_entry = ttk.Entry(form, width=10)

        self.name_entry.grid(row=1, column=0)
        self.rate_entry.grid(row=1, column=1)

        ttk.Button(form, text="Add", command=self._add_employee).grid(row=2, column=0)
        ttk.Button(form, text="Delete", command=self._delete_employee).grid(row=2, column=1)

        bank = ttk.LabelFrame(self, text="Bank details")
        bank.pack(fill="x", pady=10)

        self.has_bank_var = tk.BooleanVar()

        ttk.Checkbutton(
            bank,
            text="Has bank account",
            variable=self.has_bank_var
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(bank, text="Bank").grid(row=1, column=0, sticky="w")
        ttk.Label(bank, text="IBAN").grid(row=2, column=0, sticky="w")
        ttk.Label(bank, text="BIC").grid(row=3, column=0, sticky="w")

        self.bank_entry = ttk.Entry(bank, width=30)
        self.iban_entry = ttk.Entry(bank, width=30)
        self.bic_entry = ttk.Entry(bank, width=20)

        self.bank_entry.grid(row=1, column=1)
        self.iban_entry.grid(row=2, column=1)
        self.bic_entry.grid(row=3, column=1)

        ttk.Button(
            bank,
            text="Save bank details",
            command=self._save_bank
        ).grid(row=4, column=1, sticky="e", pady=5)

    # ==================================================
    # DATA
    # ==================================================
    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())

        for r in self.db.get_employees():
            self.tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(r["name"], r["rate"], "Yes" if r["has_bank_account"] else "No")
            )

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])

        row = self.db.cur.execute(
            "SELECT * FROM employees WHERE id=?",
            (emp_id,)
        ).fetchone()

        self.has_bank_var.set(bool(row["has_bank_account"]))

        self.bank_entry.delete(0, tk.END)
        self.iban_entry.delete(0, tk.END)
        self.bic_entry.delete(0, tk.END)

        if row["bank_name"]:
            self.bank_entry.insert(0, row["bank_name"])
        if row["iban"]:
            self.iban_entry.insert(0, row["iban"])
        if row["bic"]:
            self.bic_entry.insert(0, row["bic"])

    def _save_bank(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select employee", "Select employee first")
            return

        emp_id = int(sel[0])

        self.db.update_employee_bank(
            emp_id,
            bool(self.has_bank_var.get()),
            self.bank_entry.get(),
            self.iban_entry.get(),
            self.bic_entry.get(),
        )

        self._load_employees()
        self.tree.selection_set(str(emp_id))
        self._on_select(None)

    # ==================================================
    # CRUD
    # ==================================================
    def _add_employee(self):
        try:
            self.db.add_employee(
                self.name_entry.get(),
                float(self.rate_entry.get())
            )
            self._load_employees()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_employee(self):
        sel = self.tree.selection()
        if not sel:
            return

        self.db.delete_employee(int(sel[0]))
        self._load_employees()
