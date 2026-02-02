import tkinter as tk
from tkinter import ttk, messagebox

from core.models import Employee
from core.db import Database


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.db = db
        self._build_ui()
        self._load_employees()

    # --------------------------------------------------
    # UI
    # --------------------------------------------------
    def _build_ui(self):
        # ===== Table =====
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

        # ===== Form =====
        form = ttk.Frame(self)
        form.pack(fill="x", pady=5)

        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Label(form, text="Rate").grid(row=0, column=1, sticky="w")

        self.name_entry = ttk.Entry(form, width=25)
        self.rate_entry = ttk.Entry(form, width=10)

        self.name_entry.grid(row=1, column=0, padx=5)
        self.rate_entry.grid(row=1, column=1, padx=5)

        ttk.Button(form, text="Add", command=self._add_employee)\
            .grid(row=2, column=0, pady=5)
        ttk.Button(form, text="Delete", command=self._delete_employee)\
            .grid(row=2, column=1, pady=5)

        # ===== Bank section =====
        bank = ttk.LabelFrame(self, text="Bank details")
        bank.pack(fill="x", pady=10)

        self.has_bank_var = tk.BooleanVar()
        self.has_bank_check = ttk.Checkbutton(
            bank,
            text="Employee has bank account",
            variable=self.has_bank_var,
            command=self._toggle_bank_fields
        )
        self.has_bank_check.grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(bank, text="Bank name").grid(row=1, column=0, sticky="w")
        ttk.Label(bank, text="IBAN").grid(row=2, column=0, sticky="w")
        ttk.Label(bank, text="BIC").grid(row=3, column=0, sticky="w")

        self.bank_name_entry = ttk.Entry(bank, width=30)
        self.iban_entry = ttk.Entry(bank, width=30)
        self.bic_entry = ttk.Entry(bank, width=20)

        self.bank_name_entry.grid(row=1, column=1, padx=5)
        self.iban_entry.grid(row=2, column=1, padx=5)
        self.bic_entry.grid(row=3, column=1, padx=5)

        ttk.Button(
            bank,
            text="Save bank details",
            command=self._save_bank_details
        ).grid(row=4, column=1, sticky="e", pady=5)

        self._toggle_bank_fields()

    # --------------------------------------------------
    # DATA
    # --------------------------------------------------
    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())

        for row in self.db.get_employees():
            emp = Employee.from_row(row)
            bank = "Yes" if emp.has_bank_account else "No"

            self.tree.insert(
                "",
                "end",
                iid=str(emp.id),
                values=(emp.name, emp.rate, bank)
            )

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        row = next(r for r in self.db.get_employees() if r["id"] == emp_id)
        emp = Employee.from_row(row)

        self.has_bank_var.set(emp.has_bank_account)
        self.bank_name_entry.delete(0, tk.END)
        self.iban_entry.delete(0, tk.END)
        self.bic_entry.delete(0, tk.END)

        if emp.has_bank_account:
            self.bank_name_entry.insert(0, emp.bank_name or "")
            self.iban_entry.insert(0, emp.iban or "")
            self.bic_entry.insert(0, emp.bic or "")

        self._toggle_bank_fields()

    # --------------------------------------------------
    # ACTIONS
    # --------------------------------------------------
    def _add_employee(self):
        try:
            self.db.add_employee(
                self.name_entry.get(),
                float(self.rate_entry.get())
            )
            self.name_entry.delete(0, tk.END)
            self.rate_entry.delete(0, tk.END)
            self._load_employees()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _delete_employee(self):
        sel = self.tree.selection()
        if not sel:
            return
        self.db.delete_employee(int(sel[0]))
        self._load_employees()

    def _toggle_bank_fields(self):
        state = "normal" if self.has_bank_var.get() else "disabled"
        for w in (
            self.bank_name_entry,
            self.iban_entry,
            self.bic_entry,
        ):
            w.config(state=state)

    def _save_bank_details(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select employee", "Please select employee")
            return

        self.db.update_employee_bank(
            emp_id=int(sel[0]),
            has_bank=self.has_bank_var.get(),
            bank=self.bank_name_entry.get(),
            iban=self.iban_entry.get(),
            bic=self.bic_entry.get(),
        )

        self._load_employees()
