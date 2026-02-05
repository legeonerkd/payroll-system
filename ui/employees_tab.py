import tkinter as tk
from tkinter import ttk, filedialog

from ui.styles import COLORS


# ======================================================
# PLACEHOLDER ENTRY
# ======================================================

class PlaceholderEntry(ttk.Entry):
    def __init__(self, master, placeholder, width=36, **kwargs):
        super().__init__(master, width=width, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = COLORS["text_secondary"]
        self.default_fg = "#000000"
        self._has_placeholder = False

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

        self._show_placeholder()

    def _show_placeholder(self):
        if not self.get():
            self._has_placeholder = True
            self.configure(foreground=self.placeholder_color)
            self.delete(0, tk.END)
            self.insert(0, self.placeholder)

    def _hide_placeholder(self):
        if self._has_placeholder:
            self._has_placeholder = False
            self.configure(foreground=self.default_fg)
            self.delete(0, tk.END)

    def _on_focus_in(self, event):
        self._hide_placeholder()

    def _on_focus_out(self, event):
        if not self.get():
            self._show_placeholder()

    def get_value(self):
        return "" if self._has_placeholder else self.get()


# ======================================================
# CARD
# ======================================================

class Card(ttk.Frame):
    def __init__(self, parent, min_width=None):
        super().__init__(parent, style="Card.TFrame")
        if min_width:
            self.configure(width=min_width)
            self.pack_propagate(False)


# ======================================================
# EMPLOYEES TAB
# ======================================================

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

        self.bind_all("<Button-1>", self._on_global_click, add=True)

    # ======================================================
    # STYLES
    # ======================================================

    def _init_styles(self):
        style = ttk.Style()
        style.configure("FormTitle.Add.TLabel",
                        foreground=COLORS["positive"],
                        font=("Segoe UI", 10, "bold"))
        style.configure("FormTitle.Edit.TLabel",
                        foreground=COLORS["accent"],
                        font=("Segoe UI", 10, "bold"))
        style.configure("Error.TLabel",
                        foreground=COLORS["negative"])

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        # ---------- LIST ----------
        list_card = Card(self)
        list_card.pack(side="left", fill="both", expand=True, padx=12, pady=8)

        ttk.Label(list_card, text="Employees", style="CardTitle.TLabel")\
            .pack(anchor="w", padx=12, pady=(8, 4))

        self.tree = ttk.Treeview(
            list_card,
            columns=("name", "rate", "iban"),
            show="headings",
            height=15
        )
        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("iban", text="IBAN")

        self.tree.column("name", width=200)
        self.tree.column("rate", width=80, anchor="center")
        self.tree.column("iban", width=260)

        self.tree.pack(fill="both", expand=True, padx=12, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- FORM (WIDER) ----------
        self.form_card = Card(self, min_width=420)
        self.form_card.pack(side="right", fill="y", padx=12, pady=8)

        self.form_title = ttk.Label(
            self.form_card,
            text="Add new employee",
            style="FormTitle.Add.TLabel"
        )
        self.form_title.pack(anchor="w", padx=16, pady=(8, 4))

        form = ttk.Frame(self.form_card)
        form.pack(fill="x", padx=16, pady=8)

        self.name_entry = PlaceholderEntry(form, "Full name")
        self.rate_entry = PlaceholderEntry(form, "Hourly rate (€/h)")
        self.iban_entry = PlaceholderEntry(form, "IBAN (optional)")
        self.bic_entry = PlaceholderEntry(form, "BIC (optional)")

        self._field(form, "Name", self.name_entry, 0)
        self._field(form, "Rate €/h", self.rate_entry, 1)
        self._field(form, "IBAN", self.iban_entry, 2)
        self._field(form, "BIC", self.bic_entry, 3)

        self.error_label = ttk.Label(self.form_card, text="", style="Error.TLabel")
        self.error_label.pack(anchor="w", padx=16, pady=(0, 4))

        btns = ttk.Frame(self.form_card)
        btns.pack(fill="x", padx=16, pady=(0, 12))

        self.add_btn = ttk.Button(btns, text="Add", command=self._add_employee)
        self.add_btn.pack(fill="x", pady=2)

        self.update_btn = ttk.Button(btns, text="Update", command=self._update_employee)
        self.update_btn.pack(fill="x", pady=2)

        ttk.Button(btns, text="Delete", command=self._delete_employee)\
            .pack(fill="x", pady=2)

        ttk.Button(btns, text="Export CSV", command=self._export_csv)\
            .pack(fill="x", pady=(8, 2))

        for e in (self.name_entry, self.rate_entry):
            e.bind("<KeyRelease>", lambda _: self._validate_form())

        self._set_add_mode()

    # ======================================================
    # HELPERS / LOGIC (без изменений)
    # ======================================================

    def _field(self, parent, label, entry, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        entry.grid(row=row, column=1, pady=4)

    def _clear_form(self):
        for e in (self.name_entry, self.rate_entry, self.iban_entry, self.bic_entry):
            e.delete(0, tk.END)
            e._show_placeholder()

    def _set_add_mode(self):
        self.selected_employee_id = None
        self.form_title.configure(text="Add new employee", style="FormTitle.Add.TLabel")
        self.update_btn.state(["disabled"])
        self._validate_form()

    def _set_edit_mode(self):
        self.form_title.configure(text="Edit employee", style="FormTitle.Edit.TLabel")
        self.update_btn.state(["!disabled"])
        self._validate_form()

    def _validate_form(self):
        name = self.name_entry.get_value()
        rate = self.rate_entry.get_value()

        if not name:
            self._set_error("Name is required")
            return False

        try:
            if float(rate) <= 0:
                raise ValueError
        except Exception:
            self._set_error("Rate must be a positive number")
            return False

        self._clear_error()
        self.add_btn.state(["!disabled"])
        self.update_btn.state(["!disabled"] if self.selected_employee_id else ["disabled"])
        return True

    def _set_error(self, msg):
        self.error_label.configure(text=msg)
        self.add_btn.state(["disabled"])
        self.update_btn.state(["disabled"])

    def _clear_error(self):
        self.error_label.configure(text="")

    def _on_global_click(self, event):
        if event.widget == self.tree or str(event.widget).startswith(str(self.tree)):
            return
        if self.selected_employee_id:
            self.tree.selection_remove(self.tree.selection())
            self._clear_form()
            self._set_add_mode()

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

        self._set_edit_mode()

    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())
        self.employee_cache.clear()
        for r in self.db.get_employees():
            eid = str(r["id"])
            self.employee_cache[eid] = r
            self.tree.insert("", "end", iid=eid,
                             values=(r["name"], r["rate"], r["iban"] or ""))

    def _add_employee(self):
        if not self._validate_form():
            return
        self.db.add_employee(
            name=self.name_entry.get_value(),
            rate=float(self.rate_entry.get_value()),
            iban=self.iban_entry.get_value(),
            bic=self.bic_entry.get_value(),
        )
        self._after_change()

    def _update_employee(self):
        if not self.selected_employee_id or not self._validate_form():
            return
        self.db.update_employee(
            emp_id=self.selected_employee_id,
            name=self.name_entry.get_value(),
            rate=float(self.rate_entry.get_value()),
            iban=self.iban_entry.get_value(),
            bic=self.bic_entry.get_value(),
        )
        self._after_change()

    def _delete_employee(self):
        if not self.selected_employee_id:
            return
        self.db.delete_employee(self.selected_employee_id)
        self._after_change()

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            self.db.export_employees_csv(path)

    def _after_change(self):
        self._clear_form()
        self._set_add_mode()
        self._load_employees()
        if self.on_change:
            self.on_change()

