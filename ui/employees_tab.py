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
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self._on_search)

        self._build_ui()
        self._load()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        # ---------- LEFT PANEL (TABLE + SEARCH) ----------
        left_panel = ttk.Frame(self)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        left_panel.rowconfigure(1, weight=1)
        left_panel.columnconfigure(0, weight=1)

        # Search bar
        search_frame = ttk.Frame(left_panel)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="🔍 Search:").grid(row=0, column=0, padx=(0, 8))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")

        # Table
        self.table_frame = ttk.Frame(left_panel)
        self.table_frame.grid(row=1, column=0, sticky="nsew")

        self.tree = ttk.Treeview(
            self.table_frame,
            columns=("name", "rate", "bank", "iban", "bic"),
            show="headings"
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

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Zebra stripes
        self.tree.tag_configure("oddrow", background="#f9f9f9")
        self.tree.tag_configure("evenrow", background="#ffffff")

        # Привязываем события
        self.table_frame.bind("<Button-1>", self._on_frame_click)

        # ---------- RIGHT PANEL (FORM) ----------
        # Используем Card.TFrame для карточки
        form_card = ttk.Frame(self, style="Card.TFrame")
        form_card.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        
        # Внутренний контейнер с отступами
        form_inner = ttk.Frame(form_card)
        form_inner.pack(fill="both", expand=True, padx=20, pady=20)
        form_inner.columnconfigure(1, weight=1)

        # Заголовок
        title_label = ttk.Label(form_inner, text="Employee Details", font=("Segoe UI", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        def row(label, var, r):
            ttk.Label(form_inner, text=label).grid(row=r, column=0, sticky="w", pady=8, padx=(0, 10))
            entry = ttk.Entry(form_inner, textvariable=var)
            entry.grid(row=r, column=1, sticky="ew", pady=8)

        row("Full name *", self.name_var, 1)
        row("Hourly rate €/h *", self.rate_var, 2)
        row("Bank (optional)", self.bank_var, 3)
        row("IBAN (optional)", self.iban_var, 4)
        row("BIC (optional)", self.bic_var, 5)

        # ---------- BUTTONS (HORIZONTAL) ----------
        btns = ttk.Frame(form_inner)
        btns.grid(row=6, column=0, columnspan=2, pady=(20, 0), sticky="ew")
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)

        self.add_btn = ttk.Button(btns, text="➕ Add", command=self._add, style="Success.TButton")
        self.add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.update_btn = ttk.Button(btns, text="✏️ Update", command=self._update, style="Warning.TButton")
        self.update_btn.grid(row=0, column=1, sticky="ew", padx=4)

        self.delete_btn = ttk.Button(btns, text="🗑️ Delete", command=self._delete, style="Danger.TButton")
        self.delete_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        self._set_button_state(new_mode=True)

        # bind только после создания кнопок
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        # Правая кнопка мыши - сброс выделения
        self.tree.bind("<Button-3>", self._on_right_click)

    # ======================================================
    # SEARCH
    # ======================================================

    def _on_search(self, *args):
        """Фильтрация таблицы по поисковому запросу"""
        search_text = self.search_var.get().lower().strip()
        
        # Очищаем таблицу
        self.tree.delete(*self.tree.get_children())
        
        # Загружаем отфильтрованные данные
        row_index = 0
        for r in self.db.get_employees():
            # Фильтруем по имени, банку, IBAN или BIC
            if search_text:
                searchable = f"{r['name']} {r['bank'] or ''} {r['iban'] or ''} {r['bic'] or ''}".lower()
                if search_text not in searchable:
                    continue
            
            # Zebra stripes
            tag = "evenrow" if row_index % 2 == 0 else "oddrow"
            
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
                ),
                tags=(tag,)
            )
            row_index += 1

    # ======================================================
    # TABLE CLICK HANDLING
    # ======================================================

    def _on_right_click(self, event):
        """Правая кнопка мыши - сброс выделения"""
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        self._force_clear()
        return "break"
    
    def _on_frame_click(self, event):
        """Обработка клика по фрейму (вне таблицы)"""
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        self._force_clear()
    
    def _force_clear(self):
        """Принудительная очистка формы"""
        self.selected_id = None
        self.name_var.set("")
        self.rate_var.set("")
        self.bank_var.set("")
        self.iban_var.set("")
        self.bic_var.set("")
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
        """Загрузка данных с zebra-стилем"""
        self.tree.delete(*self.tree.get_children())
        row_index = 0
        for r in self.db.get_employees():
            # Zebra stripes
            tag = "evenrow" if row_index % 2 == 0 else "oddrow"
            
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
                ),
                tags=(tag,)
            )
            row_index += 1

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

        # Улучшенный confirmation dialog
        employee_name = self.name_var.get().strip()
        result = messagebox.askyesno(
            "Delete Employee",
            f"Are you sure you want to delete employee:\n\n{employee_name}\n\nThis action cannot be undone.",
            icon="warning"
        )
        
        if not result:
            return

        self.db.delete_employee(self.selected_id)
        self._load()
        self._new_employee_mode()

        if self.on_change:
            self.on_change()
