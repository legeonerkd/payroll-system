import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv

from core.models import Employee


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change

        self.employees: list[Employee] = []
        self.selected_employee: Employee | None = None

        self._build_ui()
        self._load_employees()

    # ==================================================
    # UI
    # ==================================================
    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ---------- Add employee ----------
        add = ttk.LabelFrame(self, text="Add employee")
        add.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        add.columnconfigure(1, weight=1)

        ttk.Label(add, text="Name").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.add_name_entry = ttk.Entry(add)
        self.add_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=4)
        self.add_name_entry.focus()

        ttk.Label(add, text="Hourly rate (€)").grid(row=0, column=2, sticky="w", padx=5)
        self.add_rate_entry = ttk.Entry(add, width=10)
        self.add_rate_entry.grid(row=0, column=3, sticky="w", padx=5)

        self.add_btn = ttk.Button(add, text="Add", command=self._add_employee)
        self.add_btn.grid(row=0, column=4, padx=10)

        # ---------- Employees list ----------
        list_frame = ttk.LabelFrame(self, text="Employees")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        list_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("name", "rate", "bank"),
            show="headings",
            height=10,
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate (€)")
        self.tree.heading("bank", text="Bank")

        self.tree.column("name", width=240)
        self.tree.column("rate", width=100, anchor="center")
        self.tree.column("bank", width=100, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- Details ----------
        details = ttk.LabelFrame(self, text="Employee details")
        details.grid(row=2, column=0, sticky="ew", padx=10, pady=8)
        details.columnconfigure(1, weight=1)

        ttk.Label(details, text="Name").grid(row=0, column=0, sticky="w", padx=5)
        self.name_entry = ttk.Entry(details)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(details, text="Hourly rate (€)").grid(row=1, column=0, sticky="w", padx=5)
        self.rate_entry = ttk.Entry(details, width=10)
        self.rate_entry.grid(row=1, column=1, sticky="w", padx=5)

        # ---------- Bank ----------
        bank = ttk.LabelFrame(self, text="Bank details")
        bank.grid(row=3, column=0, sticky="ew", padx=10, pady=8)
        bank.columnconfigure(1, weight=1)

        self.has_bank_var = tk.BooleanVar()
        self.has_bank_var.trace_add("write", self._toggle_bank_fields)

        ttk.Checkbutton(
            bank,
            text="Employee has bank account",
            variable=self.has_bank_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=4)

        ttk.Label(bank, text="Bank").grid(row=1, column=0, sticky="w", padx=5)
        ttk.Label(bank, text="IBAN").grid(row=2, column=0, sticky="w", padx=5)
        ttk.Label(bank, text="BIC").grid(row=3, column=0, sticky="w", padx=5)

        self.bank_entry = ttk.Entry(bank)
        self.iban_entry = ttk.Entry(bank)
        self.bic_entry = ttk.Entry(bank)

        self.bank_entry.grid(row=1, column=1, sticky="ew", padx=5)
        self.iban_entry.grid(row=2, column=1, sticky="ew", padx=5)
        self.bic_entry.grid(row=3, column=1, sticky="ew", padx=5)

        # ---------- Buttons ----------
        buttons = ttk.Frame(self)
        buttons.grid(row=4, column=0, sticky="ew", padx=10, pady=10)

        ttk.Button(buttons, text="Export employees", command=self._export_employees)\
            .pack(side="left")

        self.save_btn = ttk.Button(buttons, text="Save changes", command=self._save_changes)
        self.save_btn.pack(side="right", padx=5)

        self.delete_btn = ttk.Button(buttons, text="Delete employee", command=self._delete_employee)
        self.delete_btn.pack(side="right", padx=5)

        self._set_details_enabled(False)

    # ==================================================
    # UX helpers
    # ==================================================
    def _set_details_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for w in (
            self.name_entry,
            self.rate_entry,
            self.bank_entry,
            self.iban_entry,
            self.bic_entry,
            self.save_btn,
            self.delete_btn,
        ):
            w.config(state=state)

    def _toggle_bank_fields(self, *_):
        state = "normal" if self.has_bank_var.get() else "disabled"
        for w in (self.bank_entry, self.iban_entry, self.bic_entry):
            w.config(state=state)

    # ==================================================
    # DATA
    # ==================================================
    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())
        self.employees = [Employee.from_row(r) for r in self.db.get_employees()]
        self.selected_employee = None
        self._set_details_enabled(False)

        for e in self.employees:
            self.tree.insert(
                "",
                "end",
                iid=str(e.id),
                values=(e.name, f"{e.rate:.2f}", "Yes" if e.has_bank_account else "No"),
            )

        if self.on_change:
            self.on_change()

    # ==================================================
    # ACTIONS
    # ==================================================
    def _add_employee(self):
        name = self.add_name_entry.get().strip()
        if not name:
            messagebox.showwarning("Employee", "Please enter employee name")
            self.add_name_entry.focus()
            return

        try:
            rate = float(self.add_rate_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Employee", "Hourly rate must be a number")
            self.add_rate_entry.focus()
            return

        self.db.add_employee(name, rate)
        self.add_name_entry.delete(0, "end")
        self.add_rate_entry.delete(0, "end")
        self.add_name_entry.focus()
        self._load_employees()

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = int(sel[0])
        self.selected_employee = next(
            (e for e in self.employees if e.id == emp_id), None
        )
        if not self.selected_employee:
            return

        e = self.selected_employee
        self._set_details_enabled(True)

        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, e.name)
        self.rate_entry.delete(0, "end")
        self.rate_entry.insert(0, str(e.rate))

        self.has_bank_var.set(e.has_bank_account)
        self.bank_entry.delete(0, "end")
        self.bank_entry.insert(0, e.bank_name or "")
        self.iban_entry.delete(0, "end")
        self.iban_entry.insert(0, e.iban or "")
        self.bic_entry.delete(0, "end")
        self.bic_entry.insert(0, e.bic or "")

    def _save_changes(self):
        if not self.selected_employee:
            return

        try:
            rate = float(self.rate_entry.get() or 0)
        except ValueError:
            messagebox.showerror("Employee", "Hourly rate must be a number")
            self.rate_entry.focus()
            return

        self.db.update_employee(
            emp_id=self.selected_employee.id,
            name=self.name_entry.get().strip(),
            rate=rate,
            has_bank=self.has_bank_var.get(),
            bank_name=self.bank_entry.get().strip(),
            iban=self.iban_entry.get().strip(),
            bic=self.bic_entry.get().strip(),
        )
        self._load_employees()

    def _delete_employee(self):
        if not self.selected_employee:
            return

        if not messagebox.askyesno(
            "Delete employee",
            f"Delete {self.selected_employee.name}?",
        ):
            return

        self.db.delete_employee(self.selected_employee.id)
        self._load_employees()

    def _export_employees(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Rate", "Has bank", "Bank", "IBAN", "BIC"])
            for e in self.employees:
                writer.writerow([
                    e.name,
                    e.rate,
                    e.has_bank_account,
                    e.bank_name or "",
                    e.iban or "",
                    e.bic or "",
                ])
