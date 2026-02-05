import tkinter as tk
from tkinter import ttk, filedialog

from ui.styles import COLORS


# ======================================================
# PLACEHOLDER ENTRY
# ======================================================

class PlaceholderEntry(ttk.Entry):
    def __init__(self, master, placeholder, **kwargs):
        super().__init__(master, **kwargs)
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

    def _on_focus_in(self, _):
        self._hide_placeholder()

    def _on_focus_out(self, _):
        if not self.get():
            self._show_placeholder()

    def get_value(self):
        return "" if self._has_placeholder else self.get()


# ======================================================
# CARD
# ======================================================

class Card(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, style="Card.TFrame")


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

        # --- Treeview fonts ---
        style.configure(
            "Employees.Treeview",
            font=("Segoe UI", 11),
            rowheight=28
        )
        style.configure(
            "Employees.Treeview.Heading",
            font=("Segoe UI", 11, "bold")
        )

        style.configure("Icon.TLabel", font=("Segoe UI Emoji", 11))
        style.configure(
            "FormTitle.Add.TLabel",
            foreground=COLORS["positive"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "FormTitle.Edit.TLabel",
            foreground=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
        )

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # ---------- LIST CARD ----------
        list_card = Card(self)
        list_card.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
        list_card.rowconfigure(1, weight=1)
        list_card.columnconfigure(0, weight=1)

        ttk.Label(
            list_card,
            text="Employees",
            style="CardTitle.TLabel"
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        tree_frame = ttk.Frame(list_card)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("name", "rate", "iban"),
            show="headings",
            style="Employees.Treeview"
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("iban", text="IBAN")

        self.tree.column("name", anchor="w", stretch=True, width=200)
        self.tree.column("rate", anchor="center", stretch=False, width=90)
        self.tree.column("iban", anchor="w", stretch=False, width=280)

        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # ---------- FORM CARD ----------
        self.form_card = Card(self)
        self.form_card.grid(row=0, column=1, sticky="nsew", padx=12, pady=8)
        self.form_card.columnconfigure(1, weight=1)

        self.form_title = ttk.Label(
            self.form_card,
            text="Add new employee",
            style="FormTitle.Add.TLabel",
        )
        self.form_title.grid(
            row=0, column=0, columnspan=2,
            sticky="w", padx=16, pady=(8, 4)
        )

        form = ttk.Frame(self.form_card)
        form.grid(row=1, column=0, columnspan=2,
                  sticky="nsew", padx=16, pady=8)
        form.columnconfigure(1, weight=1)

        self._icon_field(form, "👤", "name", "Full name", 0)
        self._icon_field(form, "💶", "rate", "Hourly rate (€/h)", 1)
        self._icon_field(form, "🏦", "iban", "IBAN (optional)", 2)
        self._icon_field(form, "🧾", "bic", "BIC (optional)", 3)

        btns = ttk.Frame(self.form_card)
        btns.grid(row=2, column=0, columnspan=2,
                  sticky="ew", padx=16, pady=(8, 12))
        btns.columnconfigure(0, weight=1)

        self.add_btn = ttk.Button(btns, text="Add", command=self._add_employee)
        self.add_btn.grid(row=0, column=0, sticky="ew", pady=2)

        self.update_btn = ttk.Button(btns, text="Update", command=self._update_employee)
        self.update_btn.grid(row=1, column=0, sticky="ew", pady=2)
        self.update_btn.state(["disabled"])

        ttk.Button(btns, text="Delete", command=self._delete_employee)\
            .grid(row=2, column=0, sticky="ew", pady=2)

    # ======================================================
    # EVENTS / DATA
    # ======================================================

    def _icon_field(self, parent, icon, attr, placeholder, row):
        ttk.Label(parent, text=icon, style="Icon.TLabel")\
            .grid(row=row, column=0, sticky="w", pady=6)
        entry = PlaceholderEntry(parent, placeholder)
        entry.grid(row=row, column=1, sticky="ew", pady=6)
        setattr(self, f"{attr}_entry", entry)

    def _on_global_click(self, event):
        if event.widget == self.tree or str(event.widget).startswith(str(self.tree)):
            return
        if self.selected_employee_id:
            self.tree.selection_remove(self.tree.selection())
            self._clear_form()
            self._set_add_mode()

    def _on_select(self, _):
        sel = self.tree.selection()
        if not sel:
            return
        row = self.employee_cache.get(sel[0])
        if not row:
            return

        self.selected_employee_id = sel[0]
        self._clear_form()

        self.name_entry.insert(0, row["name"])
        self.rate_entry.insert(0, row["rate"])
        self.iban_entry.insert(0, row["iban"] or "")
        self.bic_entry.insert(0, row["bic"] or "")

        self.form_title.configure(
            text="Edit employee",
            style="FormTitle.Edit.TLabel"
        )
        self.update_btn.state(["!disabled"])

    def _clear_form(self):
        for e in (
            self.name_entry,
            self.rate_entry,
            self.iban_entry,
            self.bic_entry,
        ):
            e.delete(0, tk.END)
            e._show_placeholder()

    def _set_add_mode(self):
        self.selected_employee_id = None
        self.form_title.configure(
            text="Add new employee",
            style="FormTitle.Add.TLabel"
        )
        self.update_btn.state(["disabled"])

    def _load_employees(self):
        self.tree.delete(*self.tree.get_children())
        self.employee_cache.clear()
        for r in self.db.get_employees():
            eid = str(r["id"])
            self.employee_cache[eid] = r
            self.tree.insert(
                "", "end", iid=eid,
                values=(r["name"], r["rate"], r["iban"] or "")
            )

    def _add_employee(self):
        self.db.add_employee(
            name=self.name_entry.get_value(),
            rate=float(self.rate_entry.get_value()),
            iban=self.iban_entry.get_value(),
            bic=self.bic_entry.get_value(),
        )
        self._after_change()

    def _update_employee(self):
        if not self.selected_employee_id:
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
        if self.selected_employee_id:
            self.db.delete_employee(self.selected_employee_id)
            self._after_change()

    def _after_change(self):
        self._clear_form()
        self._set_add_mode()
        self._load_employees()
        if self.on_change:
            self.on_change()
