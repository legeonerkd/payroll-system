import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from ui.styles import COLORS


class Card(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent, style="App.TFrame")

        self.db = db
        self.on_change = on_change

        self.selected_employee_id = None
        self.employee_cache = {}

        self._init_styles()
        self._build_ui()
        self._load_employees()

    # ======================================================
    # STYLES
    # ======================================================

    def _init_styles(self):
        style = ttk.Style()
        style.configure("App.TFrame", background=COLORS["app_bg"])
        style.configure(
            "Card.TFrame",
            background=COLORS["card_bg"],
            relief="solid",
            borderwidth=1,
        )
        style.configure("CardTitle.TLabel", font=("Segoe UI", 10, "bold"))

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        # ---------- LIST CARD ----------
        list_card = Card(self)
        list_card.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        ttk.Label(
            list_card,
            text="Employees",
            style="CardTitle.TLabel"
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.tree = ttk.Treeview(
            list_card,
            columns=("name", "rate", "iban"),
            show="headings",
            height=15
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("iban", text="IBAN")

        self.tree.column("name", width=200, anchor="w")
        self.tree.column("rate", width=80, anchor="center")
        self.tree.column("iban", width=260, anchor="w")

        self.tree.pack(fill="both", expand=True, padx=12, pady=8)

        # ВАЖНО: обрабатываем клик по пустому месту
        self.tree.bind("<Button-1>", self._on_tree_click, add=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- FORM CARD ----------
        form_card = Card(self)
        form_card.pack(side="right", fill="y", padx=12, pady=8)

        ttk.Label(
            form_card,
            text="Employee details",
            style="CardTitle.TLabel"
        ).pack(anchor="w", padx=12, pady=(8, 4))

        form = ttk.Frame(form_card)
        form.pack(fill="x", padx=12, pady=8)

        self._field(form, "Name", "name", 0)
        self._field(form, "Rate €/h", "rate", 1)
        self._field(form, "IBAN", "iban", 2)
        self._field(form, "BIC", "bic", 3)

        # ---------- BUTTONS ----------
        btns = ttk.Frame(form_card)
        btns.pack(fill="x", padx=12, pady=(0, 12))

        self.add_btn = ttk.Button(btns, text="Add", command=self._add_employee)
        self.add_btn.pack(fill="x", pady=2)

        self.update_btn = ttk.Button(btns, text="Update", command=self._update_employee)
        self.update_btn.pack(fill="x", pady=2)

        ttk.Button(btns, text="Delete", command=self._delete_employee)\
            .pack(fill="x", pady=2)

        ttk.Button(btns, text="Export CSV", command=self._export_csv)\
            .pack(fill="x", pady=(8, 2))

        self._update_buttons_state()

    # ======================================================
    # FORM HELPERS
    # ======================================================

    def _field(self, parent, label, attr, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, width=30)
        entry.grid(row=row, column=1, pady=4)
        setattr(self, f"{attr}_entry", entry)

    def _clear_form(self):
        for entry in (
            self.name_entry,
            self.rate_entry,
            self.iban_entry,
            self.bic_entry,
        ):
            entry.delete(0, tk.END)

    # ======================================================
    # TREE EVENTS
    # ======================================================

    def _on_tree_click(self, event):
        """
        Если клик по пустому месту — снимаем выделение
        """
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            self.tree.selection_remove(self.tree.selection())
            self.selected_employee_id = None
            self._clear_form()
            self._update_buttons_state()

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return

        emp_id = sel[0]
        row = self.employee_cache.get(emp_id)
        if not row:
            return

        self.selected_employee_id = emp_id

        self._clear_form()
        self.name_entry.insert(0, row["name"])
        self.rate_entry.insert(0, row["rate"])
        self.iban_entry.insert(0, row["iban"] or "")
        self.bic_entry.insert(0, row["bic"] or "")

        self._update_buttons_state()

    def _update_buttons_state(self):
        if self.selected_employee_id:
            self.update_btn.state(["!disabled"])
        else:
            self.update_btn.state(["disabled"])

    # ======================================================
    # DATA
    # ======================================================

    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())
        self.employee_cache.clear()

        rows = self.db.get_employees()
        for r in rows:
            emp_id = str(r["id"])
            self.employee_cache[emp_id] = r
            self.tree.insert(
                "",
                "end",
                iid=emp_id,
                values=(r["name"], r["rate"], r["iban"] or "")
            )

    # ======================================================
    # CRUD
    # ======================================================

    def _add_employee(self):
        try:
            self.db.add_employee(
                name=self.name_entry.get(),
                rate=float(self.rate_entry.get()),
                iban=self.iban_entry.get(),
                bic=self.bic_entry.get(),
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._after_change()

    def _update_employee(self):
        if not self.selected_employee_id:
            return

        try:
            self.db.update_employee(
                emp_id=self.selected_employee_id,
                name=self.name_entry.get(),
                rate=float(self.rate_entry.get()),
                iban=self.iban_entry.get(),
                bic=self.bic_entry.get(),
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._after_change()

    def _delete_employee(self):
        if not self.selected_employee_id:
            return

        if not messagebox.askyesno("Delete", "Delete selected employee?"):
            return

        self.db.delete_employee(self.selected_employee_id)
        self._after_change()

    # ======================================================
    # EXPORT
    # ======================================================

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return

        self.db.export_employees_csv(path)

    # ======================================================
    # AFTER CHANGE
    # ======================================================

    def _after_change(self):
        self.selected_employee_id = None
        self._clear_form()
        self._load_employees()
        self._update_buttons_state()

        if self.on_change:
            self.on_change()
