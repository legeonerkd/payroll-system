import tkinter as tk
from tkinter import ttk, messagebox

from core.models import Employee


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.employees: list[Employee] = []

        self._build_ui()
        self._load_employees()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        # ---------- list ----------
        self.tree = ttk.Treeview(
            self,
            columns=("name", "rate", "bank"),
            show="headings",
            height=12,
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Hourly rate (€)")
        self.tree.heading("bank", text="Bank account")

        self.tree.column("name", width=220)
        self.tree.column("rate", width=120, anchor="center")
        self.tree.column("bank", width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- edit panel ----------
        edit = ttk.LabelFrame(self, text="Employee details")
        edit.pack(fill="x", pady=10)

        ttk.Label(edit, text="Name").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(edit, text="Hourly rate (€)").grid(row=1, column=0, sticky="w", padx=5, pady=5)

        self.name_entry = ttk.Entry(edit, width=30, state="readonly")
        self.rate_entry = ttk.Entry(edit, width=10)

        self.name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.rate_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # ---------- bank details ----------
        bank = ttk.LabelFrame(self, text="Bank details")
        bank.pack(fill="x", pady=10)

        self.has_bank_var = tk.BooleanVar()

        ttk.Checkbutton(
            bank,
            text="Has bank account",
            variable=self.has_bank_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)

        ttk.Label(bank, text="Bank").grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(bank, text="IBAN").grid(row=2, column=0, sticky="w", padx=5)
        ttk.Label(bank, text="BIC").grid(row=3, column=0, sticky="w", padx=5)

        self.bank_entry = ttk.Entry(bank, width=30)
        self.iban_entry = ttk.Entry(bank, width=30)
        self.bic_entry = ttk.Entry(bank, width=20)

        self.bank_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        self.iban_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        self.bic_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Button(
            self,
            text="Save changes",
            command=self._save_changes,
        ).pack(anchor="e", padx=10, pady=10)

    # ==================================================
    # DATA
    # ==================================================
    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())
        self.employees = [Employee.from_row(r) for r in self.db.get_employees()]

        for e in self.employees:
            self.tree.insert(
                "",
                "end",
                iid=str(e.id),
                values=(
                    e.name,
                    f"{e.rate:.2f}",
                    "Yes" if e.has_bank_account else "No",
                ),
            )

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        employee = next(e for e in self.employees if e.id == emp_id)

        # name
        self.name_entry.config(state="normal")
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, employee.name)
        self.name_entry.config(state="readonly")

        # rate
        self.rate_entry.delete(0, tk.END)
        self.rate_entry.insert(0, f"{employee.rate:.2f}")

        # bank
        self.has_bank_var.set(employee.has_bank_account)

        self.bank_entry.delete(0, tk.END)
        self.iban_entry.delete(0, tk.END)
        self.bic_entry.delete(0, tk.END)

        if employee.bank_name:
            self.bank_entry.insert(0, employee.bank_name)
        if employee.iban:
            self.iban_entry.insert(0, employee.iban)
        if employee.bic:
            self.bic_entry.insert(0, employee.bic)

    # ==================================================
    # SAVE
    # ==================================================
    def _save_changes(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Employee", "Select employee first")
            return

        emp_id = int(sel[0])

        # rate validation
        try:
            new_rate = float(self.rate_entry.get())
            if new_rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Rate", "Hourly rate must be a positive number")
            return

        # save rate
        self.db.update_employee_rate(emp_id, new_rate)

        # save bank
        self.db.update_employee_bank(
            emp_id,
            self.has_bank_var.get(),
            self.bank_entry.get(),
            self.iban_entry.get(),
            self.bic_entry.get(),
        )

        messagebox.showinfo("Saved", "Employee data updated")

        self._load_employees()
        self.tree.selection_set(str(emp_id))
        self._on_select(None)

