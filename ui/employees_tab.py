import tkinter as tk
from tkinter import ttk, messagebox
from core.validation import employee_values
from decimal import Decimal,InvalidOperation
from core.banking import ACCOUNT_LABELS
from ui.scrollable_card import ScrollableCard
from core.rental import rental_amount


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, db, on_change=None,archive_warning=None):
        super().__init__(parent)
        self.configure(style='App.TFrame')
        self.db = db
        self.on_change = on_change
        self.archive_warning=archive_warning

        self.selected_id = None
        self._loaded_record=None

        self.name_var = tk.StringVar()
        self.rate_var = tk.StringVar()
        self.bank_var = tk.StringVar()
        self.iban_var = tk.StringVar()
        self.bic_var = tk.StringVar()
        self.bank_account_var=tk.StringVar(value='Not specified')
        self.rental_var=tk.StringVar(value='0.00')
        self.search_var = tk.StringVar()
        self._last_search=''
        self._search_reset=False
        self._form_snapshot=self._form_values()
        self.search_var.trace("w", self._on_search)

        self._build_ui()
        self._load()

    # ======================================================
    # UI
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        # ---------- LEFT PANEL (TABLE + SEARCH) ----------
        left_panel = ttk.Frame(self,style='Card.TFrame',padding=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        left_panel.rowconfigure(1, weight=1)
        left_panel.columnconfigure(0, weight=1)

        # Search bar
        search_frame = ttk.Frame(left_panel)
        search_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search_frame.columnconfigure(1, weight=1)

        ttk.Label(search_frame, text="Search employees").grid(row=0, column=0, padx=(0, 8))
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew")

        # Table
        self.table_frame = ttk.Frame(left_panel)
        self.table_frame.grid(row=1, column=0, sticky="nsew")

        self.tree = ttk.Treeview(
            self.table_frame,
            columns=("name", "rate",'account','rental', "bank", "iban", "bic"),
            show="headings"
        )

        self.tree.heading("name", text="Name")
        self.tree.heading("rate", text="Rate €/h")
        self.tree.heading('account',text='Bank account')
        self.tree.heading('rental',text='Rental (€)')
        self.tree.heading("bank", text="Bank")
        self.tree.heading("iban", text="IBAN")
        self.tree.heading("bic", text="BIC")

        self.tree.column("name", width=200)
        self.tree.column("rate", width=90, anchor="center")
        self.tree.column('account',width=115,minwidth=100)
        self.tree.column('rental',width=95,minwidth=85,anchor='e')
        self.tree.column("bank", width=150)
        self.tree.column("iban", width=220)
        self.tree.column("bic", width=120)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.table_frame.rowconfigure(0,weight=1);self.table_frame.columnconfigure(0,weight=1)
        horizontal=ttk.Scrollbar(self.table_frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set,xscrollcommand=horizontal.set)
        self.tree.grid(row=0,column=0,sticky='nsew');scrollbar.grid(row=0,column=1,sticky='ns')
        horizontal.grid(row=1,column=0,sticky='ew')

        # Zebra stripes
        self.tree.tag_configure("oddrow", background="#F7F9FC")
        self.tree.tag_configure("evenrow", background="#ffffff")

        # Привязываем события
        self.table_frame.bind("<Button-1>", self._on_frame_click)

        # ---------- RIGHT PANEL (FORM) ----------
        # Используем Card.TFrame для карточки
        form_card = ScrollableCard(self,padding=16,min_width=300)
        self.form_scroller=form_card
        form_card.grid(row=0, column=1, sticky="nsew", padx=12, pady=12)
        
        # Внутренний контейнер с отступами
        form_inner = form_card.content
        form_inner.columnconfigure(1, weight=1)

        # Заголовок
        title_label = ttk.Label(form_inner, text="Employee Details", font=("Segoe UI", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))

        def row(label, var, r):
            ttk.Label(form_inner, text=label,style='PayrollHint.TLabel').grid(row=r, column=0, sticky="w", pady=6, padx=(0, 10))
            entry = ttk.Entry(form_inner, textvariable=var,width=18)
            entry.grid(row=r, column=1, sticky="ew", pady=6)

        row("Full name *", self.name_var, 1)
        row("Hourly rate €/h *", self.rate_var, 2)
        row('Rental / statement (€)',self.rental_var,3)
        ttk.Label(form_inner,text='Bank account').grid(row=4,column=0,sticky='w',pady=8,padx=(0,10))
        ttk.Combobox(form_inner,textvariable=self.bank_account_var,values=list(ACCOUNT_LABELS.values()),state='readonly',width=18).grid(row=4,column=1,sticky='ew',pady=8)
        row("Bank (optional)", self.bank_var, 5)
        row("IBAN (optional)", self.iban_var, 6)
        row("BIC (optional)", self.bic_var, 7)

        # ---------- BUTTONS (HORIZONTAL) ----------
        btns = ttk.Frame(form_inner)
        btns.grid(row=8, column=0, columnspan=2, pady=(16, 0), sticky="ew")
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)

        self.add_btn = ttk.Button(btns, text="Add", command=self._add, style="Success.TButton")
        self.add_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.update_btn = ttk.Button(btns, text="Update", command=self._update, style="Warning.TButton")
        self.update_btn.grid(row=0, column=1, sticky="ew", padx=4)

        self.delete_btn = ttk.Button(btns, text="Archive", command=self._delete, style="Danger.TButton")
        self.delete_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Button(form_inner,text='New / clear',command=self._request_clear).grid(row=9,column=0,columnspan=2,sticky='ew',pady=(10,0))
        form_card.bind_controls()

        self._set_button_state(new_mode=True)

        # bind только после создания кнопок
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        # Правая кнопка мыши - сброс выделения
        self.tree.bind("<Button-3>", self._on_right_click)

    # ======================================================
    # SEARCH
    # ======================================================

    def _on_search(self, *args):
        if self._search_reset:return
        if not self._confirm_form_discard():
            self._search_reset=True
            try:self.search_var.set(self._last_search)
            finally:self._search_reset=False
            return
        self._new_employee_mode()
        self._last_search=self.search_var.get()
        self._render_table()

    def _render_table(self):
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
                    ACCOUNT_LABELS[r['bank_account_state']],
                    f"{r['rental_amount']:.2f}",
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
        self._request_clear()
        return "break"
    
    def _on_frame_click(self, event):
        """Обработка клика по фрейму (вне таблицы)"""
        self._request_clear()
    
    def _force_clear(self):
        """Принудительная очистка формы"""
        self._new_employee_mode()

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
        if not self._confirm_form_discard():return
        self._new_employee_mode()
        self._render_table()

    def _on_select(self, event):
        selected = self.tree.selection()

        if not selected:
            if self.selected_id is None:return
            if not self._confirm_form_discard():
                if self.tree.exists(str(self.selected_id)):self.tree.selection_set(str(self.selected_id))
                return
            self._new_employee_mode()
            return

        emp_id = int(selected[0])
        if emp_id==self.selected_id:return
        if not self._confirm_form_discard():
            self.tree.selection_set(str(self.selected_id)) if self.selected_id is not None and self.tree.exists(str(self.selected_id)) else self.tree.selection_set(())
            return
        r = next((e for e in self.db.get_employees() if e["id"] == emp_id),None)
        if r is None:
            self._new_employee_mode();return

        self.selected_id = emp_id
        self._loaded_record={key:r[key] for key in ('name','rate','bank','iban','bic','bank_account_state','rental_amount')}
        self.name_var.set(r["name"])
        self.rate_var.set(str(r["rate"]))
        self.bank_var.set(r["bank"] or "")
        self.iban_var.set(r["iban"] or "")
        self.bic_var.set(r["bic"] or "")
        self.bank_account_var.set(ACCOUNT_LABELS[r['bank_account_state']])
        self.rental_var.set(f"{r['rental_amount']:.2f}")
        self._form_snapshot=self._form_values()
        
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
        self._loaded_record=None

        self.name_var.set("")
        self.rate_var.set("")
        self.bank_var.set("")
        self.iban_var.set("")
        self.bic_var.set("")
        self.bank_account_var.set('Not specified')
        self.rental_var.set('0.00')
        self._form_snapshot=self._form_values()

        self._set_button_state(new_mode=True)

    def _form_values(self):
        values=[v.get().strip() for v in (self.name_var,self.rate_var,self.bank_var,self.iban_var,self.bic_var)]
        try:
            rate=Decimal(values[1])
            if rate.is_finite():values[1]=rate
        except InvalidOperation:pass
        try:rental=rental_amount(self.rental_var.get() or 0)
        except ValueError:rental=self.rental_var.get().strip()
        return tuple(values)+(self.bank_account_var.get(),rental)

    def _account_state(self):
        return next(key for key,label in ACCOUNT_LABELS.items() if label==self.bank_account_var.get())

    def has_unsaved_changes(self):
        return self._form_values()!=self._form_snapshot

    def _confirm_form_discard(self):
        return not self.has_unsaved_changes() or messagebox.askyesno('Unsaved employee details','Discard unsaved employee details?')

    def _request_clear(self):
        if self._confirm_form_discard():self._new_employee_mode()

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
            _, value = employee_values(self.name_var.get() or 'Employee', raw)
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
        try:rental=rental_amount(self.rental_var.get() or 0)
        except ValueError as exc:
            messagebox.showerror('Rental deduction',str(exc));return

        if not self.name_var.get().strip():
            messagebox.showerror("Missing data", "Employee name is required.")
            return

        self.db.add_employee(
            name=self.name_var.get().strip(),
            rate=rate,
            bank=self.bank_var.get().strip() or None,
            iban=self.iban_var.get().strip() or None,
            bic=self.bic_var.get().strip() or None,
            bank_account_state=self._account_state(),
            rental_amount=rental,
        )

        self._new_employee_mode()
        self._load()

        if self.on_change:
            self.on_change()

    def _update(self):
        if not self.selected_id:
            return

        rate = self._parse_rate()
        if rate is None:
            return

        if not self.name_var.get().strip():
            messagebox.showerror("Missing data", "Employee name is required.")
            return

        try:
            self.db.update_employee(
                emp_id=self.selected_id,
                name=self.name_var.get().strip(),
                rate=rate,
                bank=self.bank_var.get().strip() or None,
                iban=self.iban_var.get().strip() or None,
                bic=self.bic_var.get().strip() or None,
                expected=self._loaded_record,
                bank_account_state=self._account_state(),
                rental_amount=rental_amount(self.rental_var.get() or 0),
            )
        except ValueError as exc:
            messagebox.showerror('Employee update',str(exc));return

        self._new_employee_mode()
        self._load()

        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self.selected_id:
            return

        # Улучшенный confirmation dialog
        employee_name = self.db.get_employee(self.selected_id)['name']
        notice='\n\nUnsaved employee details will be discarded.' if self.has_unsaved_changes() else ''
        if self.archive_warning:
            extra=self.archive_warning(self.selected_id)
            if extra:notice+='\n\n'+extra
        result = messagebox.askyesno(
            "Archive Employee",
            f"Archive employee:\n\n{employee_name}\n\nThey will be hidden from active lists. Hours and payroll history will be preserved."+notice,
            icon="warning"
        )
        
        if not result:
            return

        self.db.delete_employee(self.selected_id)
        self._new_employee_mode()
        self._load()

        if self.on_change:
            self.on_change()
