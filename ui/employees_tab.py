import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

from core.models import Employee


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change  # callback to refresh Payroll
        self.employees: list[Employee] = []

        self._build_ui()
        self._load_employees()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        # ---------- add employee ----------
        add = ttk.LabelFrame(self, text="Add employee")
        add.pack(fill="x", pady=5)

        ttk.Label(add, text="Name").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(add, text="Hourly rate (€)").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.add_name_entry = ttk.Entry(add, width=25)
        self.add_rate_entry = ttk.Entry(add, width=10)

        self.add_name_entry.grid(row=0, column=1, padx=5)
        self.add_rate_entry.grid(row=0, column=3, padx=5)

        ttk.Button(add, text="Add", command=self._add_employee)\
            .grid(row=0, column=4, padx=10)

        # ---------- list ----------
        self.tree = ttk.Treeview(
            self,
            columns=("name", "rate", "bank"),
            show="headings",
            height=10,
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Hourly rate (€)")
        self.tree.heading("bank", text="Bank")

        self.tree.column("name", width=220)
        self.tree.column("rate", width=120, anchor="center")
        self.tree.column("bank", width=120, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- edit ----------
        edit = ttk.LabelFrame(self, text="Employee details")
        edit.pack(fill="x", pady=5)

        ttk.Label(edit, text="Name").grid(row=0, column=0, sticky="w", padx=5)
        ttk.Label(edit, text="Hourly rate (€)").grid(row=1, column=0, sticky="w", padx=5)

        self.name_entry = ttk.Entry(edit, width=30)
        self.rate_entry = ttk.Entry(edit, width=10)

        self.name_entry.grid(row=0, column=1, padx=5)
        self.rate_entry.grid(row=1, column=1, padx=5)

        # ---------- bank ----------
        bank = ttk.LabelFrame(self, text="Bank details")
        bank.pack(fill="x", pady=5)

        self.has_bank_var = tk.BooleanVar()

        ttk.Checkbutton(bank, text="Has bank account",
                        variable=self.has_bank_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=5)

        ttk.Label(bank, text="Bank").grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(bank, text="IBAN").grid(row=2, column=0, sticky="w", padx=5)
        ttk.Label(bank, text="BIC").grid(row=3, column=0, sticky="w", padx=5)

        self.bank_entry = ttk.Entry(bank, width=30)
        self.iban_entry = ttk.Entry(bank, width=30)
        self.bic_entry = ttk.Entry(bank, width=20)

        self.bank_entry.grid(row=1, column=1, padx=5)
        self.iban_entry.grid(row=2, column=1, padx=5)
        self.bic_entry.grid(row=3, column=1, padx=5)

        # ---------- buttons ----------
        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=5)

        ttk.Button(btns, text="Save changes", command=self._save_changes)\
            .pack(side="right", padx=5)
        ttk.Button(btns, text="Delete employee", command=self._delete_employee)\
            .pack(side="right", padx=5)
        ttk.Button(btns, text="Export employees", command=self._export_employees)\
            .pack(side="left", padx=5)

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
                values=(e.name, f"{e.rate:.2f}", "Yes" if e.has_bank_account else "No"),
            )

        if self.on_change:
            self.on_change()

    def _add_employee(self):
        name = self.add_name_entry.get().strip()
        try:
            rate = float(self.add_rate_entry.get())
            if rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid hourly rate")
            return

        if not name:
            messagebox.showerror("Error", "Name required")
            return

        self.db.add_employee(name, rate)
        self.add_name_entry.delete(0, tk.END)
        self.add_rate_entry.delete(0, tk.END)
        self._load_employees()

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        emp = next(e for e in self.employees if e.id == int(sel[0]))

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, emp.name)

        self.rate_entry.delete(0, tk.END)
        self.rate_entry.insert(0, f"{emp.rate:.2f}")

        self.has_bank_var.set(emp.has_bank_account)
        self.bank_entry.delete(0, tk.END)
        self.iban_entry.delete(0, tk.END)
        self.bic_entry.delete(0, tk.END)

        if emp.bank_name:
            self.bank_entry.insert(0, emp.bank_name)
        if emp.iban:
            self.iban_entry.insert(0, emp.iban)
        if emp.bic:
            self.bic_entry.insert(0, emp.bic)

    def _save_changes(self):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        name = self.name_entry.get().strip()

        try:
            rate = float(self.rate_entry.get())
            if rate <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid rate")
            return

        self.db.update_employee_name(emp_id, name)
        self.db.update_employee_rate(emp_id, rate)
        self.db.update_employee_bank(
            emp_id,
            self.has_bank_var.get(),
            self.bank_entry.get(),
            self.iban_entry.get(),
            self.bic_entry.get(),
        )
        self._load_employees()

    def _delete_employee(self):
        sel = self.tree.selection()
        if not sel:
            return

        if not messagebox.askyesno("Confirm", "Delete selected employee?"):
            return

        self.db.delete_employee(int(sel[0]))
        self._load_employees()

    def _export_employees(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Rate", "Bank", "IBAN", "BIC"])
            for e in self.employees:
                writer.writerow([
                    e.name,
                    f"{e.rate:.2f}",
                    e.bank_name or "",
                    e.iban or "",
                    e.bic or "",
                ])

        messagebox.showinfo("Export", "Employees exported successfully")

