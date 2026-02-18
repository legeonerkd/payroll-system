import tkinter as tk
from tkinter import ttk, messagebox


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None):
        super().__init__(parent)
        self.db = db
        self.on_change = on_change

        self.selected_id = None

        self.name_var = tk.StringVar()
        self.rate_var = tk.StringVar()
        self.bank_var = tk.StringVar()
        self.iban_var = tk.StringVar()
        self.bic_var = tk.StringVar()

        self._build_ui()
        self._load()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)  # Растягиваем строку на всю высоту

        # ---------- TABLE ----------
        table_frame = ttk.Frame(self)
        table_frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("name", "rate", "bank", "iban", "bic"),
            show="headings"
            # Убрали height=18, чтобы таблица растягивалась
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading("bank", text="Bank")
        self.tree.heading("iban", text="IBAN")
        self.tree.heading("bic", text="BIC")

        self.tree.column("name", width=200)
        self.tree.column("rate", width=90, anchor="center")
        self.tree.column("bank", width=150)
        self.tree.column("iban", width=220)
        self.tree.column("bic", width=120)

        self.tree.pack(fill="both", expand=True)

        # ---------- FORM ----------
        form = ttk.LabelFrame(self, text="Employee details")
        form.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)

        form.columnconfigure(1, weight=1)

        def row(label, var, r):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=6)
            entry = ttk.Entry(form, textvariable=var)
            entry.grid(row=r, column=1, sticky="ew", pady=6)

        row("Full name *", self.name_var, 0)
        row("Hourly rate €/h *", self.rate_var, 1)
        row("Bank (optional)", self.bank_var, 2)
        row("IBAN (optional)", self.iban_var, 3)
        row("BIC (optional)", self.bic_var, 4)

        # ---------- BUTTONS ----------
        btns = ttk.Frame(form)
        btns.grid(row=5, column=0, columnspan=2, pady=12, sticky="ew")

        self.new_btn = ttk.Button(btns, text="Add New", command=self._new_employee_mode)
        self.new_btn.pack(fill="x", pady=3)

        self.add_btn = ttk.Button(btns, text="Add", command=self._add)
        self.add_btn.pack(fill="x", pady=3)

        self.update_btn = ttk.Button(btns, text="Update", command=self._update)
        self.update_btn.pack(fill="x", pady=3)

        self.delete_btn = ttk.Button(btns, text="Delete", command=self._delete)
        self.delete_btn.pack(fill="x", pady=3)

        self._set_button_state(new_mode=True)

        # bind только после создания кнопок
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<ButtonRelease-1>", self._on_tree_click)


    # ======================================================
    # TABLE CLICK HANDLING
    # ======================================================

    def _on_tree_click(self, event):
        """Обработка клика по таблице - сброс выделения при клике на пустое место"""
        # Используем after для выполнения после TreeviewSelect
        self.after(10, lambda: self._check_empty_click(event))
    
    def _check_empty_click(self, event):
        """Проверка клика на пустом месте с задержкой"""
        row_id = self.tree.identify_row(event.y)
        
        # Если клик не на строке и нет выделения - переключаем в режим добавления
        if not row_id and not self.tree.selection():
            self._clear_selection()
            self._set_button_state(new_mode=True)

    def _clear_selection(self):
        self.tree.selection_set(())
        self.selected_id = None

        self.name_var.set("")
        self.rate_var.set("")
        self.bank_var.set("")
        self.iban_var.set("")
        self.bic_var.set("")


    # ======================================================
    # DATA
    # ======================================================

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.get_employees():
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

    def _on_select(self, event):
        selected = self.tree.selection()

        if not selected:
            self._set_button_state(new_mode=True)
            return

        emp_id = int(selected[0])
        r = next(e for e in self.db.get_employees() if e["id"] == emp_id)

        self.selected_id = emp_id
        self.name_var.set(r["name"])
        self.rate_var.set(str(r["rate"]))
        self.bank_var.set(r["bank"] or "")
        self.iban_var.set(r["iban"] or "")
        self.bic_var.set(r["bic"] or "")
        
        # Переключаем в режим редактирования
        self._set_button_state(new_mode=False)


    def _clear_form(self):
        self.name_var.set("")
        self.rate_var.set("")
        self.bank_var.set("")
        self.iban_var.set("")
        self.bic_var.set("")

    # ======================================================
    # MODES
    # ======================================================

    def _new_employee_mode(self):
        self.tree.selection_remove(self.tree.selection())
        self.selected_id = None

        self.name_var.set("")
        self.rate_var.set("")
        self.bank_var.set("")
        self.iban_var.set("")
        self.bic_var.set("")

        self._set_button_state(new_mode=True)

    def _set_button_state(self, new_mode):
        if new_mode:
            self.add_btn.configure(state="normal")
            self.update_btn.configure(state="disabled")
            self.delete_btn.configure(state="disabled")
        else:
            self.add_btn.configure(state="disabled")
            self.update_btn.configure(state="normal")
            self.delete_btn.configure(state="normal")

    # ======================================================
    # VALIDATION
    # ======================================================

    def _parse_rate(self):
        raw = self.rate_var.get().strip()
        try:
            value = float(raw)
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            messagebox.showerror(
                "Invalid rate",
                "Hourly rate must be a positive number.\nExample: 8 or 10.5"
            )
            return None

    # ======================================================
    # ACTIONS
    # ======================================================

    def _add(self):
        rate = self._parse_rate()
        if rate is None:
            return

        if not self.name_var.get().strip():
            messagebox.showerror("Missing data", "Employee name is required.")
            return

        self.db.add_employee(
            name=self.name_var.get().strip(),
            rate=rate,
            bank=self.bank_var.get().strip() or None,
            iban=self.iban_var.get().strip() or None,
            bic=self.bic_var.get().strip() or None,
        )

        self._load()
        self._new_employee_mode()

        if self.on_change:
            self.on_change()

    def _update(self):
        if not self.selected_id:
            return

        rate = self._parse_rate()
        if rate is None:
            return

        self.db.update_employee(
            emp_id=self.selected_id,
            name=self.name_var.get().strip(),
            rate=rate,
            bank=self.bank_var.get().strip() or None,
            iban=self.iban_var.get().strip() or None,
            bic=self.bic_var.get().strip() or None,
        )

        self._load()

        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self.selected_id:
            return

        if not messagebox.askyesno("Delete employee", "Are you sure?"):
            return

        self.db.delete_employee(self.selected_id)
        self._load()
        self._new_employee_mode()

        if self.on_change:
            self.on_change()
