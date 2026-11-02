import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from decimal import Decimal

from tkcalendar import DateEntry
from services.report_service import generate_payroll_pdf
from services.payroll_service import calculate_fixed_payroll, calculate_custom_payroll
from core.models import Employee
from config import FIXED_RATE
from core.validation import number
from services.hours_distribution import distribute_hours

DEFAULT_HOURS = 10.0
HOUR_STEP = 0.5


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db

        self.employee_map = {}
        self.days_data = {}

        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_var = tk.StringVar(value="0.00")
        self.rental_var = tk.StringVar(value="0.00")
        self.distribution_hours_var = tk.StringVar(value="")

        # Summary variables
        self.total_hours_var = tk.StringVar(value="0.0")
        self.gross_var = tk.StringVar(value="0.00 €")
        self.deductions_var = tk.StringVar(value="0.00 €")
        self.net_var = tk.StringVar(value="0.00 €")

        self._editor = None
        self._context = None
        self._dirty = False
        self._payroll_dirty = False
        self._saved_kind = 'loaded'
        self._manual_days = set()
        self._editing_row = None
        self.save_status_var = tk.StringVar(value='Load a period to begin')

        self._build_ui()
        self._load_employees()
        
        # Bind auto-recalculation
        self.rate_mode.trace_add("write", self._parameters_changed)
        self.utilities_var.trace_add("write", self._parameters_changed)
        self.rental_var.trace_add("write", self._parameters_changed)

    # ======================================================
    # UI LAYOUT - 3 ZONES (Header / Content / Summary)
    # ======================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_header()
        self._build_content()

    def _build_header(self):
        header = ttk.Frame(self, style='Card.TFrame', padding=12)
        header.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 5))
        header.columnconfigure(0, weight=1)
        for column, text in enumerate(('Employee', 'From', 'To')):
            ttk.Label(header, text=text, style='PayrollHint.TLabel').grid(row=0, column=column, sticky='w', padx=(0,12))
        self.employee_cb = ttk.Combobox(header, state='readonly', width=24)
        self.employee_cb.grid(row=1, column=0, sticky='ew', padx=(0,12), pady=(4,0))
        self.employee_cb.bind('<<ComboboxSelected>>', self._employee_changed)
        self.from_entry = DateEntry(header, date_pattern='dd-mm-yyyy', firstweekday='monday', width=12)
        self.to_entry = DateEntry(header, date_pattern='dd-mm-yyyy', firstweekday='monday', width=12)
        self.from_entry.grid(row=1, column=1, padx=(0,12), pady=(4,0))
        self.to_entry.grid(row=1, column=2, padx=(0,12), pady=(4,0))
        for entry in (self.from_entry,self.to_entry):
            entry.bind('<<DateEntrySelected>>', lambda e:self._update_save_status(), add='+')
            entry.bind('<FocusOut>', lambda e:self._update_save_status(), add='+')
        ttk.Button(header, text='Load period', command=self._generate_period, style='PayrollSecondary.TButton').grid(row=1,column=3,pady=(4,0))

    def _build_content(self):
        content = ttk.Frame(self)
        content.grid(row=1,column=0,sticky='nsew',padx=10,pady=(5,10))
        content.columnconfigure(0,weight=1)
        content.rowconfigure(0,weight=1)
        self._build_hours_table(content)
        self._build_right_panel(content)

    def _build_hours_table(self,parent):
        table_frame = ttk.Frame(parent,style='Card.TFrame',padding=12)
        table_frame.grid(row=0,column=0,sticky='nsew',padx=(0,12))
        table_frame.columnconfigure(0,weight=1)
        table_frame.rowconfigure(4,weight=1)
        heading=ttk.Frame(table_frame,style='PayrollCard.TFrame')
        heading.grid(row=0,column=0,sticky='ew',pady=(0,10))
        ttk.Label(heading,text='Working hours',style='PayrollHeading.TLabel').pack(side='left')
        self.save_status_label=ttk.Label(heading,textvariable=self.save_status_var,style='PayrollStatus.TLabel',wraplength=210,justify='right')
        self.save_status_label.pack(side='right',padx=(8,0))
        allocation=ttk.Frame(table_frame,style='PayrollCard.TFrame')
        allocation.grid(row=1,column=0,sticky='ew')
        ttk.Label(allocation,text='Total to distribute',style='PayrollHint.TLabel').grid(row=0,column=0,sticky='w')
        ttk.Entry(allocation,textvariable=self.distribution_hours_var,width=13).grid(row=1,column=0,sticky='w',pady=(4,0),padx=(0,10))
        ttk.Button(allocation,text='Distribute Mon-Sat',command=self._distribute_hours,style='PayrollSecondary.TButton').grid(row=1,column=1,pady=(4,0))
        ttk.Label(table_frame,text='Whole hours with variation. Sundays stay at 0.',style='PayrollHint.TLabel').grid(row=2,column=0,sticky='w',pady=(7,2))
        ttk.Label(table_frame,text='Double-click hours to edit. Enter to confirm, Esc to cancel.',style='PayrollHint.TLabel').grid(row=3,column=0,sticky='w',pady=(0,10))
        container=ttk.Frame(table_frame,style='PayrollCard.TFrame')
        container.grid(row=4,column=0,sticky='nsew')
        container.rowconfigure(0,weight=1)
        container.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(container,columns=('date','day','hours','changes'),show='headings',height=5,style='Payroll.Treeview')
        scrollbar=ttk.Scrollbar(container,orient='vertical',command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0,column=0,sticky='nsew')
        scrollbar.grid(row=0,column=1,sticky='ns')
        for column,label,width in [('date','Date',105),('day','Day',100),('hours','Hours',65),('changes','Changes',100)]:
            self.tree.heading(column,text=label,anchor='e' if column=='hours' else 'w')
            self.tree.column(column,width=width,minwidth=60,anchor='e' if column=='hours' else 'w',stretch=column!='hours')
        self.tree.bind('<Double-1>',self._start_edit_hours)
        self.tree.bind('<Button-1>',self.clear_selection_on_click,add='+')
        self.total_label=ttk.Label(table_frame,text='Total: 0 hours',style='PayrollHeading.TLabel')
        self.total_label.grid(row=5,column=0,sticky='e',pady=(10,0))

    def _build_right_panel(self,parent):
        shell=ttk.Frame(parent,style='Card.TFrame')
        shell.grid(row=0,column=1,sticky='nsew')
        shell.rowconfigure(0,weight=1)
        shell.columnconfigure(0,weight=1)
        self.sidebar_canvas=tk.Canvas(shell,background='white',highlightthickness=0,borderwidth=0,width=265,height=1)
        self.sidebar_canvas.grid(row=0,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(shell,orient='vertical',command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=scrollbar.set)
        right=ttk.Frame(self.sidebar_canvas,style='PayrollCard.TFrame',padding=10)
        window=self.sidebar_canvas.create_window(0,0,anchor='nw',window=right)
        self.sidebar_content=right
        def resize(event=None):
            self.sidebar_canvas.configure(width=max(245,right.winfo_reqwidth()))
            self.sidebar_canvas.itemconfigure(window,width=max(self.sidebar_canvas.winfo_width(),right.winfo_reqwidth()))
            self.sidebar_canvas.configure(scrollregion=self.sidebar_canvas.bbox('all'))
            if right.winfo_reqheight()>self.sidebar_canvas.winfo_height():
                scrollbar.grid(row=0,column=1,sticky='ns')
            else:
                scrollbar.grid_remove()
                self.sidebar_canvas.yview_moveto(0)
        self.sidebar_canvas.bind('<Configure>',resize)
        right.bind('<Configure>',resize)
        right.columnconfigure(0,weight=1)
        self._build_rate_card(right)
        self._build_deductions_card(right)
        self._build_summary(right)
        self._build_pdf_actions(right)
        def bind_scroll(widget):
            widget.bind('<MouseWheel>',self._scroll_sidebar,add='+')
            widget.bind('<FocusIn>',self._ensure_sidebar_visible,add='+')
            for child in widget.winfo_children(): bind_scroll(child)
        bind_scroll(right)

    def _scroll_sidebar(self,event):
        if self.sidebar_canvas.yview()!=(0.0,1.0):
            self.sidebar_canvas.yview_scroll(-1 if event.delta>0 else 1,'units')
            return 'break'

    def _ensure_sidebar_visible(self,event):
        canvas=self.sidebar_canvas
        total=self.sidebar_content.winfo_height()
        if total<=canvas.winfo_height(): return
        top=event.widget.winfo_rooty()-self.sidebar_content.winfo_rooty()
        bottom=top+event.widget.winfo_height()
        visible_top=canvas.canvasy(0)
        if top<visible_top: canvas.yview_moveto(top/total)
        elif bottom>visible_top+canvas.winfo_height():
            canvas.yview_moveto((bottom-canvas.winfo_height())/total)

    def _build_rate_card(self,parent):
        card=ttk.Frame(parent,style='PayrollCard.TFrame')
        card.grid(row=0,column=0,sticky='ew')
        ttk.Label(card,text='Hourly rate',style='PayrollHeading.TLabel').pack(anchor='w',pady=(0,4))
        ttk.Radiobutton(card,text=f'Fixed rate ({FIXED_RATE} €/h)',variable=self.rate_mode,value='fixed',style='Payroll.TRadiobutton').pack(anchor='w')
        self.custom_rate_label=ttk.Radiobutton(card,text='Employee rate',variable=self.rate_mode,value='custom',style='Payroll.TRadiobutton')
        self.custom_rate_label.pack(anchor='w')

    def _build_deductions_card(self,parent):
        card=ttk.Frame(parent,style='PayrollCard.TFrame')
        card.grid(row=1,column=0,sticky='ew',pady=(10,0))
        card.columnconfigure((0,1),weight=1)
        ttk.Label(card,text='Deductions',style='PayrollHeading.TLabel').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,4))
        for column,(label,variable) in enumerate([('Utilities (€)',self.utilities_var),('Rental (€)',self.rental_var)]):
            ttk.Label(card,text=label,style='PayrollHint.TLabel').grid(row=1,column=column,sticky='w')
            ttk.Entry(card,textvariable=variable,width=11).grid(row=2,column=column,sticky='ew',pady=(3,0),padx=(0,8) if column==0 else 0)

    def _build_summary(self,parent):
        card=ttk.Frame(parent,style='PayrollCard.TFrame')
        card.grid(row=2,column=0,sticky='ew',pady=(10,0))
        card.columnconfigure(1,weight=1)
        ttk.Separator(card).grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,7))
        for row,(label,variable) in enumerate([('Total hours',self.total_hours_var),('Gross pay',self.gross_var),('Deductions',self.deductions_var)],1):
            ttk.Label(card,text=label,style='PayrollHint.TLabel').grid(row=row,column=0,sticky='w',pady=1)
            value=ttk.Label(card,textvariable=variable,style='PayrollBody.TLabel')
            value.grid(row=row,column=1,sticky='e')
            if label=='Deductions': self.deductions_preview=value
        ttk.Label(card,text='Net pay',style='PayrollHeading.TLabel').grid(row=4,column=0,sticky='w',pady=(8,0))
        ttk.Label(card,textvariable=self.net_var,style='PayrollNet.TLabel').grid(row=4,column=1,sticky='e',pady=(8,0))

    def _build_pdf_actions(self,parent):
        card=ttk.Frame(parent,style='PayrollCard.TFrame')
        card.grid(row=3,column=0,sticky='ew',pady=(10,0))
        card.columnconfigure(0,weight=1)
        ttk.Button(card,text='Save hours',command=self._save_draft,style='PayrollSecondary.TButton').grid(row=0,column=0,sticky='ew')
        ttk.Label(card,text='Save a draft. No payroll is issued.',style='PayrollHint.TLabel').grid(row=1,column=0,sticky='w',pady=(3,8))
        ttk.Button(card,text='Save payroll + PDF',command=self._save_pdf,style='Accent.TButton').grid(row=2,column=0,sticky='ew')
        secondary=ttk.Frame(card,style='PayrollCard.TFrame')
        secondary.grid(row=3,column=0,sticky='ew',pady=(5,0))
        secondary.columnconfigure((0,1),weight=1)
        ttk.Button(secondary,text='Preview PDF',command=self._preview_pdf,style='PayrollSecondary.TButton').grid(row=0,column=0,sticky='ew',padx=(0,5))
        ttk.Button(secondary,text='Print',command=self._print_pdf,style='PayrollSecondary.TButton').grid(row=0,column=1,sticky='ew')
        ttk.Label(card,text='Preview and print do not save changes.',style='PayrollHint.TLabel').grid(row=4,column=0,sticky='w',pady=(5,0))


    def _load_employees(self):
        """Загрузка списка сотрудников в combobox"""
        old = self.employee_map.get(self.employee_cb.get())
        current_id = old['id'] if old is not None else None
        
        self.employee_map.clear()
        names = []

        for e in self.db.get_employees():
            label = f'{e["name"]} [#{e["id"]}]'
            self.employee_map[label] = e
            names.append(label)

        self.employee_cb["values"] = names
        
        # Пытаемся восстановить предыдущий выбор
        selected = next((label for label,e in self.employee_map.items() if e['id']==current_id),None)
        if selected:
            self.employee_cb.set(selected)
        elif names:
            self.employee_cb.current(0)
        else:
            self.employee_cb.set('')
        if self._context and (not selected or self._context[0] != current_id):
            self.tree.delete(*self.tree.get_children())
            self.days_data.clear()
            self._context = None
            self._dirty = False
            self._payroll_dirty = False
            self._manual_days.clear()
            self._update_total_hours()
        self._auto_recalculate()
        self._update_save_status()

    def _employee_changed(self, event=None):
        selected = self.employee_map.get(self.employee_cb.get())
        if self._editor is not None:
            if self._context:
                self.employee_cb.set(next((label for label,e in self.employee_map.items() if e['id']==self._context[0]),''))
            messagebox.showwarning('Hours editor','Finish editing hours with Enter before switching employee')
            return
        if self.has_unsaved_changes() and not messagebox.askyesno('Unsaved changes', 'Discard unsaved hours and payroll settings and switch employee?'):
            if self._context:
                label = next((label for label,e in self.employee_map.items() if e['id']==self._context[0]),'')
                self.employee_cb.set(label)
            return
        self._dirty = False
        self._payroll_dirty = False
        self.days_data.clear()
        self.tree.delete(*self.tree.get_children())
        self._context = None
        self.utilities_var.set('0.00')
        self.rental_var.set('0.00')
        if selected is not None:
            self._generate_period()
        self._update_save_status()
    
    def refresh_employees(self):
        """Публичный метод для обновления списка сотрудников извне"""
        self._load_employees()

    # ======================================================
    # PERIOD GENERATION
    # ======================================================

    def _generate_period(self):
        """Генерация периода с zebra-стилем и подсветкой выходных"""
        if self._editor is not None:
            messagebox.showwarning('Hours editor','Finish editing hours with Enter before loading a period')
            return
        start = self.from_entry.get_date()
        end = self.to_entry.get_date()
        selected = self.employee_map.get(self.employee_cb.get())
        if selected is None:
            messagebox.showwarning('Employee', 'Select an employee first')
            return
        if start > end or (end-start).days > 365:
            messagebox.showerror('Period', 'Select a period of 1 to 366 days with From before To')
            return
        if self.has_unsaved_changes() and not messagebox.askyesno('Load period', 'Load saved hours and discard unsaved daily edits? Payroll settings will be kept.'):
            return
        stored = {r['work_date']:r['hours'] for r in self.db.load_hours(selected['id'],start.isoformat(),end.isoformat())}
        self._display_period(start, end, selected, stored, dirty=not bool(stored))

    def _distribute_hours(self):
        if self._editor is not None:
            messagebox.showwarning('Hours editor', 'Finish editing hours with Enter before distributing')
            return
        selected = self.employee_map.get(self.employee_cb.get())
        if selected is None:
            messagebox.showwarning('Employee', 'Select an employee first')
            return
        try:
            start, end = self.from_entry.get_date(), self.to_entry.get_date()
            values = distribute_hours(start, end, self.distribution_hours_var.get())
            stored = self.db.load_hours(selected['id'],start.isoformat(),end.isoformat())
        except ValueError as exc:
            messagebox.showerror('Distribute hours', str(exc))
            return
        if (self._dirty or stored or self.days_data) and not messagebox.askyesno(
                'Replace hours?', 'Replace the displayed hours with varied whole hours for Monday-Saturday? '
                'Sundays will be zero. Unsaved edits will be discarded. The database changes only when you save.'):
            return
        self._display_period(start, end, selected, values, dirty=True)

    def _display_period(self, start, end, selected, stored, *, dirty):
        self.tree.delete(*self.tree.get_children())
        self.days_data.clear()
        self._context = (selected['id'],start.isoformat(),end.isoformat())
        self._dirty = dirty
        self._saved_kind = 'loaded'
        self._manual_days.clear()

        # Configure zebra tags
        self.tree.tag_configure("odd", background="#f9f9f9")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("weekend", background="#fee2e2", foreground="#991b1b")

        d = start
        row_index = 0
        while d <= end:
            is_weekend = d.weekday() in [5, 6]  # Saturday, Sunday
            hours = stored.get(d.isoformat(),0.0) if stored else (0.0 if is_weekend else DEFAULT_HOURS)

            key = d.strftime("%Y-%m-%d")
            self.days_data[key] = hours

            # Determine tag
            if d.weekday()==6:
                tag = "weekend"
            else:
                tag = "odd" if row_index % 2 == 0 else "even"

            self.tree.insert(
                "",
                "end",
                iid=key,
                values=(
                    d.strftime("%d-%m-%Y"),
                    d.strftime("%A"),
                    f"{hours:g}",
                    'Sunday' if d.weekday()==6 else '',
                ),
                tags=(tag,),
            )

            d += timedelta(days=1)
            row_index += 1

        self._update_total_hours()
        self._auto_recalculate()
        self._update_save_status()

    # ======================================================
    # HOURS EDITING
    # ======================================================

    def _start_edit_hours(self, event):
        if self._editor is not None:
            self._save_hours(self._editing_row)
            if self._editor is not None:
                return
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        if column != "#3":
            return

        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return

        bbox = self.tree.bbox(row_id, column)
        if not bbox:
            return

        x, y, w, h = bbox
        value = self.days_data.get(row_id, 0.0)

        self._editor = tk.Spinbox(
            self.tree, from_=0, to=24, increment=HOUR_STEP, justify="right",
            highlightthickness=2, highlightbackground='#2563eb', highlightcolor='#2563eb'
        )
        self._editing_row = row_id
        self._editor.delete(0, "end")
        self._editor.insert(0, f"{value:g}")
        self._editor.place(x=x, y=y, width=w, height=h)
        self._editor.focus()

        self._editor.bind("<Return>", lambda e: self._save_hours(row_id))
        self._editor.bind("<FocusOut>", lambda e: self._save_hours(row_id))
        self._editor.bind('<Escape>', self._cancel_hours_edit)

    def _cancel_hours_edit(self, event=None):
        editor,self._editor = self._editor,None
        self._editing_row = None
        if editor is not None:
            editor.destroy()
        self.tree.focus_set()
        return 'break'

    def _save_hours(self, row_id):
        if not self._editor:
            return

        try:
            val = float(number(self._editor.get(), 'Hours', maximum=24))
            if val < 0:
                val = 0.0
        except ValueError as exc:
            messagebox.showerror('Invalid hours', str(exc))
            self._editor.focus()
            return

        changed = self.days_data[row_id] != val
        self.days_data[row_id] = val
        if changed:
            self._dirty = True
            self._manual_days.add(row_id)

        values = list(self.tree.item(row_id, "values"))
        values[2] = f"{val:g}"
        if row_id in self._manual_days:
            values[3] = 'Manual edit'
        self.tree.item(row_id, values=values)

        editor,self._editor = self._editor,None
        self._editing_row = None
        editor.destroy()

        self._update_total_hours()
        self._auto_recalculate()
        self._update_save_status()

    def clear_selection_on_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        item = self.tree.identify_row(event.y)

        if not item:
            self.tree.selection_remove(self.tree.selection())

        return None

    # ======================================================
    # AUTO-RECALCULATION
    # ======================================================

    def _update_total_hours(self):
        """Обновление итогов часов"""
        total = sum((Decimal(str(h)) for h in self.days_data.values()), Decimal(0))
        display = f'{total:.2f}'.rstrip('0').rstrip('.')
        self.total_hours_var.set(display)
        self.total_label.config(text=f"Total: {display} hours")

    def has_unsaved_changes(self):
        return self._dirty or self._payroll_dirty

    def _parameters_changed(self, *args):
        if self.days_data:
            self._payroll_dirty = True
        self._auto_recalculate()
        self._update_save_status()

    def _update_save_status(self):
        selected = self.employee_map.get(self.employee_cb.get())
        if not self.days_data or selected is None:
            text = 'Load a period to begin'
        else:
            try:
                context = (selected['id'],self.from_entry.get_date().isoformat(),self.to_entry.get_date().isoformat())
            except (ValueError,tk.TclError):
                context = None
            if context != self._context:
                text = 'Period changed: load or distribute'
            elif not self._dirty and self._payroll_dirty and self._saved_kind=='draft':
                text = 'Hours saved · payroll settings pending'
            elif self.has_unsaved_changes():
                text = 'Unsaved changes'
            else:
                text = {'loaded':'Hours loaded · draft','draft':'Hours saved · draft','payroll':'Payroll saved'}[self._saved_kind]
        self.save_status_var.set(text)
        self.save_status_label.configure(foreground='#986119' if self.has_unsaved_changes() else '#526276')

    def _auto_recalculate(self):
        """Автоматический пересчёт Net при изменении параметров"""
        if not self.days_data:
            self.gross_var.set('0.00 €')
            self.net_var.set('0.00 €')
            self.deductions_var.set('0.00 €')
            return

        name = self.employee_cb.get()
        if not name:
            return

        emp_data = self.employee_map.get(name)
        if emp_data is None:
            return
        self.custom_rate_label.configure(text=f'Employee rate ({emp_data["rate"]:.2f} €/h)')
        emp = Employee(
            id=emp_data["id"],
            name=emp_data["name"],
            rate=emp_data["rate"],
        )

        try:
            utilities = float(number(self.utilities_var.get() or 0, 'Utilities deduction'))
        except ValueError:
            self.net_var.set('Invalid deduction')
            return

        try:
            rental = float(number(self.rental_var.get() or 0, 'Rental deduction'))
        except ValueError:
            self.net_var.set('Invalid deduction')
            return

        # Calculate
        if self.rate_mode.get() == "fixed":
            rows, summary = calculate_fixed_payroll(
                emp, self.days_data, utilities=utilities, housing=rental
            )
        else:
            rows, summary = calculate_custom_payroll(
                emp, self.days_data, utilities=utilities, housing=rental
            )

        # Update summary
        self._update_total_hours()
        self.gross_var.set(f"{summary.gross_amount:.2f} €")
        
        total_deductions = summary.housing_deduction + summary.utilities_deduction
        self.deductions_var.set(f"{total_deductions:.2f} €")
        self.net_var.set(f"{summary.net_amount:.2f} €")

        # Update deductions preview
        self.deductions_preview.config(text=f"{total_deductions:.2f} €")

    # ======================================================
    # PDF ACTIONS
    # ======================================================

    def _preview_pdf(self):
        """Просмотр PDF"""
        try:
            self._call_pdf(action="preview")
        except Exception as e:
            messagebox.showerror("PDF Preview", str(e))

    def _save_pdf(self):
        """Сохранение PDF в папку по периоду"""
        try:
            pdf_path = self._call_pdf(action="save")
            messagebox.showinfo("PDF Saved", f"PDF saved to:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("PDF Save", str(e))

    def _print_pdf(self):
        """Печать PDF"""
        try:
            self._call_pdf(action="print")
            messagebox.showinfo("PDF Print", "PDF sent to printer. Changes have not been saved by printing.")
        except Exception as e:
            messagebox.showerror("PDF Print", str(e))

    def _call_pdf(self, action="preview"):
        """
        Генерирует PDF с указанным действием
        action: "preview", "save", "print"
        """
        name = self.employee_cb.get()
        if not name:
            raise ValueError("Employee not selected")

        emp = self.employee_map[name]

        if self._editor is not None:
            raise ValueError('Finish editing hours with Enter before creating a PDF')
        context = (emp['id'], self.from_entry.get_date().isoformat(), self.to_entry.get_date().isoformat())
        if not self.days_data or self._context != context:
            raise ValueError('Generate the selected period before creating a PDF')
        rows = [(day, '', hours) for day,hours in sorted(self.days_data.items())]
        utilities = number(self.utilities_var.get() or 0, 'Utilities deduction')
        rental = number(self.rental_var.get() or 0, 'Rental deduction')

        pdf_path = generate_payroll_pdf(
            employee_name=emp["name"],
            employee_rate=emp["rate"],
            rows=rows,
            rate_mode=self.rate_mode.get(),
            utilities=str(utilities),
            rental=str(rental),
            period_from=self.from_entry.get(),
            period_to=self.to_entry.get(),
            bank_name=emp["bank"] if "bank" in emp.keys() else None,
            iban=emp["iban"] if "iban" in emp.keys() else None,
            bic=emp["bic"] if "bic" in emp.keys() else None,
            action=action,
            employee_id=emp['id'],
        )
        if action == 'save':
            self.db.save_payroll(emp['id'], self.days_data, self.rate_mode.get(), context[1], context[2],
                                 utilities=str(utilities),rental=str(rental),pdf_path=pdf_path)
            self._dirty = False
            self._payroll_dirty = False
            self._saved_kind = 'payroll'
            self._update_save_status()
        return pdf_path

    def _save_draft(self):
        try:
            emp = self.employee_map.get(self.employee_cb.get())
            context = None if emp is None else (emp['id'],self.from_entry.get_date().isoformat(),self.to_entry.get_date().isoformat())
            if not self.days_data or context != self._context or self._editor is not None:
                raise ValueError('Generate this period and finish editing before saving hours')
            self._save_hours_to_database(emp['id'])
            self._dirty = False
            self._saved_kind = 'draft'
            self._update_save_status()
            messagebox.showinfo('Saved', 'Draft hours saved. Save the PDF to record the final payroll and deductions.')
        except Exception as exc:
            messagebox.showerror('Save hours',str(exc))
    
    def _save_hours_to_database(self, emp_id: int):
        """Сохранение часов в базу данных"""
        if not self.days_data:
            return
        
        # Сохраняем все отработанные часы
        self.db.save_hours_batch(emp_id, self.days_data)
