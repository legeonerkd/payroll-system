import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from tkcalendar import DateEntry
from services.report_service import generate_payroll_pdf
from services.report_service import preview_payroll_pdf_from_history
from ui.payroll_conflicts import choose_existing_payroll
from pathlib import Path
from services.payroll_service import calculate_fixed_payroll, calculate_custom_payroll
from core.models import Employee
from core.banking import account_caption,payment_details
from core.rental import rental_for_rate,rental_hint,utilities_for_rate,deduction_mode
from core.payroll_checks import payroll_checks
from ui.payroll_history import PayrollHistory
from services.paired_payroll_service import pair_plans,save_payroll_pair,print_payroll_pair,PairPrintError
from config import FIXED_RATE
from core.validation import number
from services.hours_distribution import distribute_hours, MAX_DISTRIBUTED_HOURS

DEFAULT_HOURS = 10.0
HOUR_STEP = 0.5


class PayrollTab(ttk.Frame):
    def __init__(self, parent, db,on_edit_employee=None):
        super().__init__(parent)
        self.configure(style='App.TFrame')
        self.db = db
        self.on_edit_employee=on_edit_employee
        self.period_write_controls=[]
        self.bank_account_var=tk.StringVar(value='Bank account: —')
        self.bank_detail_var=tk.StringVar(value='Select an employee')
        self.bank_edit_button=None

        self.employee_map = {}
        self.days_data = {}

        self.rate_mode = tk.StringVar(value="fixed")
        self.utilities_var = tk.StringVar(value="0.00")
        self.rental_var = tk.StringVar(value="0.00")
        self.rental_hint_var=tk.StringVar()
        self.distribution_hours_var = tk.StringVar(value="")
        self.distribution_min_var = tk.StringVar(value='0')
        self.distribution_max_var = tk.StringVar(value=str(MAX_DISTRIBUTED_HOURS))
        self._locked_days = set()
        self._excluded_days = set()
        self._distribution_dirty=False
        self._loading_distribution_settings=False

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
        self.distribution_min_var.trace_add('write',self._distribution_settings_changed)
        self.distribution_max_var.trace_add('write',self._distribution_settings_changed)

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
        account=ttk.Frame(header,style='PayrollCard.TFrame')
        account.grid(row=2,column=0,columnspan=4,sticky='ew',pady=(12,0))
        self.bank_status_label=ttk.Label(account,textvariable=self.bank_account_var,style='AccountUnknown.TLabel')
        self.bank_status_label.pack(side='left')
        self.bank_detail_label=ttk.Label(account,textvariable=self.bank_detail_var,style='PayrollHint.TLabel',wraplength=460)
        self.bank_detail_label.pack(side='left',padx=(12,0))
        if self.on_edit_employee:
            self.bank_edit_button=ttk.Button(account,text='Edit employee',command=self._edit_employee,style='Quiet.TButton')
            self.bank_edit_button.pack(side='right',padx=(10,0))

    def _update_bank_information(self):
        selected=self.employee_map.get(self.employee_cb.get())
        status,detail,state=account_caption(selected)
        try:has_utilities=number(self.utilities_var.get() or 0,'Utilities deduction')>0
        except ValueError:has_utilities=False
        if state=='unknown' and selected is not None and (selected['rental_amount']>0 or has_utilities):
            detail='Set Bank account to Yes or No in Employee Details to apply deductions.'
        self.bank_account_var.set(status);self.bank_detail_var.set(detail)
        self.bank_status_label.configure(style={'yes':'AccountYes.TLabel','no':'AccountNo.TLabel','unknown':'AccountUnknown.TLabel'}[state])
        if self.bank_edit_button is not None:self.bank_edit_button.configure(state='normal' if selected is not None else 'disabled')

    def _edit_employee(self):
        selected=self.employee_map.get(self.employee_cb.get())
        if selected is not None and self.on_edit_employee:self.on_edit_employee(selected['id'])

    def _build_content(self):
        content = ttk.Frame(self,style='App.TFrame')
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
        ttk.Label(allocation,text='Total hours (incl. locked)',style='PayrollHint.TLabel').grid(row=0,column=0,sticky='w')
        total_entry=ttk.Entry(allocation,textvariable=self.distribution_hours_var,width=13)
        total_entry.grid(row=1,column=0,sticky='w',pady=(4,0),padx=(0,12));self.period_write_controls.append(total_entry)
        for column,(text,variable) in enumerate([('Preferred min',self.distribution_min_var),('Preferred max',self.distribution_max_var)],1):
            ttk.Label(allocation,text=text,style='PayrollHint.TLabel').grid(row=0,column=column,sticky='w',padx=(0,10))
            entry=ttk.Spinbox(allocation,from_=0,to=MAX_DISTRIBUTED_HOURS,textvariable=variable,width=4)
            entry.grid(row=1,column=column,pady=(4,0),padx=(0,12));self.period_write_controls.append(entry)
        distribute=ttk.Button(allocation,text='Distribute Mon-Sat',command=self._distribute_hours,style='PayrollSecondary.TButton')
        distribute.grid(row=1,column=3,pady=(4,0))
        self.period_write_controls.append(distribute)
        def fit_distribution(event):
            # Keep controls compact on desktop and wrap the action at narrow widths.
            required=sum(allocation.grid_bbox(column,1)[2] for column in range(3))+distribute.winfo_reqwidth()
            if event.width<required:
                distribute.grid_configure(row=2,column=0,columnspan=3,sticky='w',pady=(8,0))
            else:
                distribute.grid_configure(row=1,column=3,columnspan=1,sticky='',pady=(4,0))
        allocation.bind('<Configure>',fit_distribution)
        range_hint=ttk.Label(table_frame,text='Daily range adjusts to match the total, up to 14 h/day. Locked dates keep their hours; excluded dates stay at 0.',style='PayrollHint.TLabel',wraplength=600)
        range_hint.grid(row=2,column=0,sticky='ew',pady=(7,2))
        range_hint.bind('<Configure>',lambda event:range_hint.configure(wraplength=max(100,event.width)))
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
        actions=ttk.Frame(table_frame,style='PayrollCard.TFrame')
        actions.grid(row=6,column=0,sticky='ew',pady=(8,0))
        for text,rule in [('Lock / unlock','locked'),('Exclude / include','excluded')]:
            button=ttk.Button(actions,text=text,command=lambda rule=rule:self._toggle_day_rule(rule),style='PayrollSecondary.TButton')
            button.pack(side='left',padx=(0,8));self.period_write_controls.append(button)

    def _build_right_panel(self,parent):
        shell=ttk.Frame(parent,style='Card.TFrame')
        shell.grid(row=0,column=1,sticky='nsew')
        shell.rowconfigure(0,weight=1)
        shell.columnconfigure(0,weight=1)
        self.sidebar_canvas=tk.Canvas(shell,background='white',highlightthickness=0,borderwidth=0,width=265,height=1)
        self.sidebar_canvas.grid(row=0,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(shell,orient='vertical',command=self.sidebar_canvas.yview)
        self.sidebar_canvas.configure(yscrollcommand=scrollbar.set)
        right=ttk.Frame(self.sidebar_canvas,style='PayrollCard.TFrame',padding=14)
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
        self.preflight_var=tk.StringVar()
        self.preflight_label=ttk.Label(card,textvariable=self.preflight_var,style='AccountUnknown.TLabel',wraplength=205)
        self.utilities_reminder=ttk.Label(card,text='Utilities reminder: check the entered amount; 0 is allowed. Rental is deducted. Printing continues.',style='AccountUnknown.TLabel',wraplength=205)
        for notice in (self.preflight_label,self.utilities_reminder):
            notice.bind('<Configure>',lambda event,notice=notice:notice.configure(wraplength=max(100,event.width-20)))
        self.rate_heading=ttk.Label(card,text='Hourly rate',style='PayrollHeading.TLabel')
        self.rate_heading.pack(anchor='w',pady=(0,4))
        ttk.Radiobutton(card,text=f'Fixed rate ({FIXED_RATE} €/h)',variable=self.rate_mode,value='fixed',style='Payroll.TRadiobutton').pack(anchor='w')
        self.custom_rate_label=ttk.Radiobutton(card,text='Employee rate',variable=self.rate_mode,value='custom',style='Payroll.TRadiobutton')
        self.custom_rate_label.pack(anchor='w')

    def _build_deductions_card(self,parent):
        card=ttk.Frame(parent,style='PayrollCard.TFrame')
        card.grid(row=1,column=0,sticky='ew',pady=(10,0))
        card.columnconfigure((0,1),weight=1)
        ttk.Label(card,text='Deductions',style='PayrollHeading.TLabel').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,4))
        ttk.Label(card,text='Utilities (€)',style='PayrollHint.TLabel').grid(row=1,column=0,columnspan=2,sticky='w')
        entry=ttk.Entry(card,textvariable=self.utilities_var,width=11)
        entry.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(3,0));self.period_write_controls.append(entry)
        self.utilities_scope_var=tk.StringVar()
        scope=ttk.Label(card,textvariable=self.utilities_scope_var,style='PayrollHint.TLabel',wraplength=205)
        scope.grid(row=3,column=0,columnspan=2,sticky='ew',pady=(6,0))
        scope.bind('<Configure>',lambda event:scope.configure(wraplength=max(100,event.width)))

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
        payout=ttk.Frame(card,style='PayrollTotal.TFrame',padding=(12,10))
        payout.grid(row=4,column=0,columnspan=2,sticky='ew',pady=(12,0))
        ttk.Label(payout,text='NET PAY',style='PayrollTotalCaption.TLabel').pack(anchor='w')
        ttk.Label(payout,textvariable=self.net_var,style='PayrollTotalValue.TLabel').pack(anchor='w',pady=(3,0))

    def _build_pdf_actions(self,parent):
        card=ttk.Frame(parent,style='PayrollCard.TFrame')
        card.grid(row=3,column=0,sticky='ew',pady=(10,0))
        card.columnconfigure(0,weight=1)
        def action(text,command,row,style):
            button=ttk.Button(card,text=text,command=command,style=style)
            button.grid(row=row,column=0,sticky='ew',pady=(0 if row==0 else 5,0))
            self.period_write_controls.append(button)
        action('Save hours',self._save_draft,0,'PayrollSecondary.TButton')
        ttk.Label(card,text='Save a draft. No payroll is issued.',style='PayrollHint.TLabel').grid(row=1,column=0,sticky='w',pady=(3,8))
        action('Save & print both PDFs',self._save_and_print_both,2,'Accent.TButton')
        action('Save both PDFs',self._save_both_pdf,3,'PayrollSecondary.TButton')
        action('Save payroll + PDF',self._save_pdf,4,'PayrollSecondary.TButton')
        secondary=ttk.Frame(card,style='PayrollCard.TFrame')
        secondary.grid(row=5,column=0,sticky='ew',pady=(5,0))
        secondary.columnconfigure((0,1),weight=1)
        for column,(text,command) in enumerate([('Preview PDF',self._preview_pdf),('Print',self._print_pdf)]):
            button=ttk.Button(secondary,text=text,command=command,style='PayrollSecondary.TButton')
            button.grid(row=0,column=column,sticky='ew',padx=(0,5) if column==0 else 0);self.period_write_controls.append(button)
        ttk.Label(card,text='Preview / Print selected do not save changes.',style='PayrollHint.TLabel').grid(row=6,column=0,sticky='w',pady=(5,0))
        period_actions=ttk.Frame(card);period_actions.grid(row=7,column=0,sticky='ew',pady=(10,0))
        period_actions.columnconfigure((0,1),weight=1)
        self.close_period_button=ttk.Button(period_actions,text='Close period',command=self._toggle_period,style='PayrollSecondary.TButton')
        self.close_period_button.grid(row=0,column=0,sticky='ew',padx=(0,5))
        ttk.Button(period_actions,text='History',command=self._open_history,style='PayrollSecondary.TButton').grid(row=0,column=1,sticky='ew')

    def _selected_context(self):
        employee=self.employee_map.get(self.employee_cb.get())
        if employee is None:return None
        try:return employee['id'],self.from_entry.get_date().isoformat(),self.to_entry.get_date().isoformat()
        except (ValueError,tk.TclError):return None

    def _is_closed(self):
        context=self._context or self._selected_context()
        return bool(context and self.db.period_is_closed(*context))

    def _update_period_controls(self):
        closed=self._is_closed()
        for control in self.period_write_controls:control.configure(state='disabled' if closed else 'normal')
        context=self._selected_context()
        exact=next((r for r in self.db.get_closed_periods(context[0]) if (r['period_from'],r['period_to'])==context[1:]),None) if context else None
        self.close_period_button.configure(text='Reopen period' if exact else 'Close period',
            state='normal' if exact or (context==self._context and self.days_data and not closed) else 'disabled')

    def _open_history(self):
        context=self._selected_context()
        if context:PayrollHistory(self,self.db,employee_id=context[0],period=context[1:])

    def _toggle_period(self):
        context=self._selected_context()
        if context is None:return
        exact=next((r for r in self.db.get_closed_periods(context[0]) if (r['period_from'],r['period_to'])==context[1:]),None)
        try:
            if exact:
                if not messagebox.askyesno('Reopen period?','Allow edits and corrected statements for '+context[1]+' — '+context[2]+'? Originals stay in history.'):return
                self.db.reopen_period(exact['id'])
            else:
                if self._context!=context or not self.days_data:raise ValueError('Load this exact period first')
                if self.has_unsaved_changes() or self._editor is not None:raise ValueError('Save the statements and finish editing before closing this period')
                if not messagebox.askyesno('Close period?','Protect '+context[1]+' — '+context[2]+' for this employee from hour edits and corrected statements? Saved PDFs remain available in History.'):return
                self.db.close_period(*context)
            self.utilities_reminder.pack_forget();self._auto_recalculate();self._update_save_status()
        except ValueError as exc:messagebox.showerror('Period',str(exc))

    def _guard_period_edit(self):
        if not self._is_closed():return True
        messagebox.showwarning('Closed period','Reopen the period explicitly before editing. Reprint original statements from History.')
        return False

    def _update_preflight(self,modes=None):
        if self._is_closed():
            notices=['Closed period — read-only. Open History to view or reprint the original saved amounts.']
        else:
            employee=self.employee_map.get(self.employee_cb.get())
            try:notices=payroll_checks(employee,self.days_data,self.utilities_var.get() or 0,modes or (self.rate_mode.get(),)) if employee is not None and self.days_data else []
            except ValueError:notices=[]
        self.preflight_var.set(' '.join(notices))
        if notices:self.preflight_label.pack(fill='x',before=self.rate_heading,pady=(0,8))
        else:self.preflight_label.pack_forget()

    def _show_preflight(self,modes=None):
        self._update_preflight(modes);self.update_idletasks()
        if self.preflight_var.get():
            self._ensure_sidebar_visible(SimpleNamespace(widget=self.preflight_label));self.update_idletasks()


    def _load_employees(self):
        """Загрузка списка сотрудников в combobox"""
        self.utilities_reminder.pack_forget()
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
            updated=self.employee_map[selected]
            keys=('name',)+ (('rate',) if self.rate_mode.get()=='custom' else ())
            if old is not None and self.days_data and not self._is_closed() and (any(old[key]!=updated[key] for key in keys) or payment_details(old)!=payment_details(updated)
                or rental_for_rate(old,self.rate_mode.get())!=rental_for_rate(updated,self.rate_mode.get())
                or deduction_mode(old)!=deduction_mode(updated)):
                self._payroll_dirty=True
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
            self._distribution_dirty=False
            self._manual_days.clear()
            self._update_total_hours()
        self._auto_recalculate()
        self._update_save_status()
        self._update_bank_information()
        if self._context is None and not self._distribution_dirty:
            current=self.employee_map.get(self.employee_cb.get())
            if current is not None: self._load_distribution_settings(current['id'])

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
        self._distribution_dirty=False
        self.days_data.clear()
        self.tree.delete(*self.tree.get_children())
        self._context = None
        self.utilities_reminder.pack_forget()
        self.utilities_var.set('0.00')
        self.rental_var.set('0.00')
        if selected is not None:
            self._load_distribution_settings(selected['id'])
            self._generate_period()
        self._update_save_status()
        self._update_bank_information()
    
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
        if self.days_data and self.has_unsaved_changes() and not messagebox.askyesno('Load period', 'Load saved hours and discard unsaved daily edits and day rules? Payroll settings and daily range will be kept.'):
            return
        stored = {r['work_date']:r['hours'] for r in self.db.load_hours(selected['id'],start.isoformat(),end.isoformat())}
        rules=self.db.load_day_rules(selected['id'],start.isoformat(),end.isoformat())
        self._display_period(start, end, selected, stored, dirty=not bool(stored),rules=rules)

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
            self.db.ensure_period_open(selected['id'],start.isoformat(),end.isoformat())
            stored = self.db.load_hours(selected['id'],start.isoformat(),end.isoformat())
            context=(selected['id'],start.isoformat(),end.isoformat())
            if self._context==context:
                rules=self._day_rules()
                previous=self.days_data
            else:
                rules=self.db.load_day_rules(selected['id'],context[1],context[2])
                previous={r['work_date']:r['hours'] for r in stored}
            lo,hi=self._distribution_settings()
            locked={d:previous[d] for d,r in rules.items() if r['locked']}
            excluded={d for d,r in rules.items() if r['excluded']}
            values = distribute_hours(start,end,self.distribution_hours_var.get(),minimum=lo,maximum=hi,locked=locked,excluded=excluded)
        except ValueError as exc:
            messagebox.showerror('Distribute hours', str(exc))
            return
        question='Redistribute unlocked Monday-Saturday hours? Locked dates stay unchanged. Excluded dates and unlocked Sundays stay at zero. Other daily edits will be replaced. Save to update the database.'
        allocated=[hours for day,hours in values.items() if day not in locked and day not in excluded and date.fromisoformat(day).weekday()<6]
        if allocated and (min(allocated)<lo or max(allocated)>hi):
            question=f'The preferred daily range will be adjusted to fit the requested total (allocated: {min(allocated):g}–{max(allocated):g} hours/day). '+question
        if self._context!=context and self.has_unsaved_changes():
            question='The selected period differs from the displayed period. Unsaved daily edits and day rules will be discarded. Saved locks for the selected period will be used. '+question
        if (self._dirty or stored or self.days_data) and not messagebox.askyesno('Replace hours?',question):
            return
        self._display_period(start, end, selected, values, dirty=True,rules=rules)

    def _display_period(self, start, end, selected, stored, *, dirty,rules=None):
        self.tree.delete(*self.tree.get_children())
        self.days_data.clear()
        self._context = (selected['id'],start.isoformat(),end.isoformat())
        self._dirty = dirty or self._distribution_dirty
        self._saved_kind = 'loaded'
        self._manual_days.clear()
        rules=rules or {}
        self._locked_days={d for d,r in rules.items() if r['locked']}
        self._excluded_days={d for d,r in rules.items() if r['excluded']}

        # Configure zebra tags
        self.tree.tag_configure("odd", background="#F7F9FC")
        self.tree.tag_configure("even", background="#ffffff")
        self.tree.tag_configure("weekend", background="#F5F1EA", foreground="#7B6851")

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

        for key in self.days_data: self._refresh_day_label(key)

        self._update_total_hours()
        self._auto_recalculate()
        self._update_save_status()

    def _load_distribution_settings(self,emp_id):
        lo,hi=self.db.load_distribution_settings(emp_id)
        self._loading_distribution_settings=True
        try:
            self.distribution_min_var.set(str(min(lo,MAX_DISTRIBUTED_HOURS)))
            self.distribution_max_var.set(str(min(hi,MAX_DISTRIBUTED_HOURS)))
        finally:
            self._loading_distribution_settings=False

    def _distribution_settings(self):
        lo=number(self.distribution_min_var.get(),'Minimum daily hours',maximum=MAX_DISTRIBUTED_HOURS)
        hi=number(self.distribution_max_var.get(),'Maximum daily hours',maximum=MAX_DISTRIBUTED_HOURS)
        if lo!=lo.to_integral_value() or hi!=hi.to_integral_value() or lo>hi:
            raise ValueError('Daily range must use whole numbers with 0 <= Min <= Max <= 14')
        return int(lo),int(hi)

    def _distribution_settings_changed(self,*args):
        if self._loading_distribution_settings: return
        self._distribution_dirty=True
        if self.days_data: self._dirty=True
        self._update_save_status()

    def _day_rules(self):
        return {d:{'locked':d in self._locked_days,'excluded':d in self._excluded_days}
                for d in self.days_data if d in self._locked_days or d in self._excluded_days}

    def _refresh_day_label(self,day):
        label='Locked' if day in self._locked_days else 'Excluded' if day in self._excluded_days else 'Sunday' if datetime.fromisoformat(day).weekday()==6 else ''
        if day in self._manual_days:
            label='Locked · edited' if day in self._locked_days else 'Manual edit'
        self.tree.set(day,'changes',label)

    def _toggle_day_rule(self,rule):
        if not self._guard_period_edit():return
        selected=self.employee_map.get(self.employee_cb.get())
        context=None if selected is None else (selected['id'],self.from_entry.get_date().isoformat(),self.to_entry.get_date().isoformat())
        if self._editor is not None or context!=self._context or not self.days_data:
            messagebox.showwarning('Day rules','Load this period and finish editing first')
            return
        days=self.tree.selection()
        if not days:
            messagebox.showinfo('Day rules','Select one or more dates in the table first')
            return
        own=self._locked_days if rule=='locked' else self._excluded_days
        other=self._excluded_days if rule=='locked' else self._locked_days
        remove=all(d in own for d in days)
        if not remove and any(d in other for d in days):
            messagebox.showwarning('Day rules','Include excluded dates before locking them, or unlock dates before excluding them')
            return
        for day in days:
            if remove: own.discard(day)
            else:
                own.add(day)
                if rule=='excluded':
                    self.days_data[day]=0
                    self.tree.set(day,'hours','0')
                    self._manual_days.discard(day)
            self._refresh_day_label(day)
        self._dirty=True
        self._update_total_hours();self._auto_recalculate();self._update_save_status()

    # ======================================================
    # HOURS EDITING
    # ======================================================

    def _start_edit_hours(self, event):
        if not self._guard_period_edit():return
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
        if self._is_closed():
            self._cancel_hours_edit();self._guard_period_edit();return

        try:
            val = float(number(self._editor.get(), 'Hours', maximum=24))
            if row_id in self._excluded_days and val!=0:
                raise ValueError('Include this date before entering non-zero hours')
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
        self._refresh_day_label(row_id)

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
        return self._dirty or self._payroll_dirty or self._distribution_dirty

    def _parameters_changed(self, *args):
        self.utilities_reminder.pack_forget()
        if self.days_data and not self._is_closed():
            self._payroll_dirty = True
        self._auto_recalculate()
        self._update_bank_information()
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
        if self._is_closed():text='Closed · read-only'
        self.save_status_var.set(text)
        self.save_status_label.configure(foreground='#986119' if self.has_unsaved_changes() else '#526276')
        self._update_period_controls()

    def _auto_recalculate(self):
        """Автоматический пересчёт Net при изменении параметров"""
        self._sync_rental()
        self._update_preflight()
        if self._is_closed():
            self.gross_var.set('See History');self.net_var.set('See History');self.deductions_var.set('See History')
            return
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
            utilities = float(utilities_for_rate(emp_data,self.rate_mode.get(),self.utilities_var.get() or 0))
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

    def _sync_rental(self):
        employee=self.employee_map.get(self.employee_cb.get())
        self.rental_var.set(f'{rental_for_rate(employee,self.rate_mode.get()):.2f}')
        self.rental_hint_var.set(rental_hint(employee,self.rate_mode.get()))
        target=deduction_mode(employee)
        self.utilities_scope_var.set('Utilities apply to '+('Fixed rate only.' if target=='fixed' else 'Employee rate only.') if target else 'Set Bank account to Yes or No to apply utilities.')

    def _show_utilities_reminder(self):
        # An inline notice has no modal dialog, grab, answer or required value.
        self.utilities_reminder.pack(fill='x',before=self.rate_heading,pady=(0,8))
        self.update_idletasks()
        self._ensure_sidebar_visible(SimpleNamespace(widget=self.utilities_reminder));self.update_idletasks()

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
            if self._last_pdf_saved:
                messagebox.showinfo("Payroll saved", f"Payroll and PDF saved to:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("PDF Save", str(e))

    def _current_output_employee(self):
        selected=self.employee_map.get(self.employee_cb.get())
        if selected is None:raise ValueError('Employee not selected')
        current=self.db.get_employee(selected['id'])
        if current['archived']:raise ValueError('Employee is archived. Select an active employee.')
        if dict(current)!=dict(selected):self.refresh_employees()
        return current

    def _save_both_pdf(self):
        try:
            result=self._call_both_pdfs()
            if result:messagebox.showinfo('Both payrolls saved','Fixed rate:\n'+result['files']['fixed']+'\n\nEmployee rate:\n'+result['files']['custom'])
        except Exception as exc:messagebox.showerror('Save both PDFs',str(exc))

    def _save_and_print_both(self):
        try:
            result=self._call_both_pdfs(print_after=True)
            if result:messagebox.showinfo('Both PDFs sent','Both payrolls are saved. Fixed and Employee rate PDFs were sent to the print application.')
        except PairPrintError as exc:
            labels={'fixed':'Fixed rate','custom':'Employee rate'}
            sent=', '.join(labels[m] for m in exc.submitted) or 'None'
            pending=', '.join(labels[m] for m in exc.pending)
            messagebox.showwarning('Printing incomplete','Payrolls remain saved.\nSent: '+sent+'\nNot sent: '+pending+
                '\n\nCheck the saved PDFs and retry only the reports not sent. Do not resend the complete pair if one was already submitted.')
        except Exception as exc:messagebox.showerror('Save & print both PDFs',str(exc))

    def _call_both_pdfs(self,*,print_after=False):
        employee=self._current_output_employee()
        if self._editor is not None:raise ValueError('Finish editing hours with Enter before creating PDFs')
        start,end=self.from_entry.get_date().isoformat(),self.to_entry.get_date().isoformat()
        if not self.days_data or self._context!=(employee['id'],start,end):
            raise ValueError('Generate the selected period before creating PDFs')
        utilities=number(self.utilities_var.get() or 0,'Utilities deduction')
        self._show_preflight(('fixed','custom'))
        settings=self._distribution_settings()
        plans=pair_plans(self.db,employee,self.days_data,start,end,utilities)
        if any(plan['exact'] or plan['overlaps'] for plan in plans.values()):
            existing='\n'.join(f'{mode}: '+', '.join('#'+str(p['id']) for p in plan['exact']+plan['overlaps'])
                               for mode,plan in plans.items() if plan['exact'] or plan['overlaps'])
            if not messagebox.askyesno('Save both payrolls?',
                'Existing current statements:\n'+existing+'\n\nCreate both PDFs? Statements for the same rate and exact period will be corrected; originals stay in history. Other overlapping periods remain in monthly totals and will be flagged for review.'):
                return None
        result=save_payroll_pair(self.db,employee,self.days_data,start,end,utilities,plans=plans,
                                day_rules=self._day_rules(),settings=settings)
        self._dirty=False;self._payroll_dirty=False;self._distribution_dirty=False
        self._saved_kind='payroll';self._update_save_status()
        if print_after:
            if any(self.db.get_payroll_full(pid)[0]['rental']>0 for pid in result['ids'].values()):
                self._show_utilities_reminder()
            result['submitted']=print_payroll_pair(result['files'])
        return result

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
        self._last_pdf_saved=False
        name = self.employee_cb.get()
        if not name:
            raise ValueError("Employee not selected")

        emp = self._current_output_employee()

        if self._editor is not None:
            raise ValueError('Finish editing hours with Enter before creating a PDF')
        context = (emp['id'], self.from_entry.get_date().isoformat(), self.to_entry.get_date().isoformat())
        self.db.ensure_period_open(*context)
        if not self.days_data or self._context != context:
            raise ValueError('Generate the selected period before creating a PDF')
        rows = [(day, '', hours) for day,hours in sorted(self.days_data.items())]
        utilities = utilities_for_rate(emp,self.rate_mode.get(),self.utilities_var.get() or 0)
        rental = rental_for_rate(emp,self.rate_mode.get())
        settings=self._distribution_settings() if action=='save' else None
        self._show_preflight()
        details=payment_details(emp)
        replaces_ids=()
        expected_ids=None
        allow_overlap=False
        if action=='save':
            other=[p for p in self.db.get_payrolls(current_only=True) if p['employee_id']==emp['id'] and p['period_from']==context[1]
                   and p['period_to']==context[2] and p['rate_mode']!=self.rate_mode.get()]
            if other:
                raise ValueError('This period already has the other rate statement. Use Save both PDFs to save or correct both parts together.')
            plan=self.db.payroll_save_plan(emp['id'],self.days_data,self.rate_mode.get(),context[1],context[2],str(utilities),str(rental))
            expected_ids=[p['id'] for p in plan['exact']]
            if plan['exact']:
                choice=choose_existing_payroll(self,plan['exact'])
                if choice is None:return None
                if choice[0]=='open':
                    payroll,days=self.db.get_payroll_full(choice[1])
                    return preview_payroll_pdf_from_history(payroll,days)
                replaces_ids=choice[1]
            if plan['overlaps']:
                overlap_details='\n'.join(f'#{p["id"]}: {p["period_from"]} — {p["period_to"]}' for p in plan['overlaps'])
                if not messagebox.askyesno('Overlapping periods',
                    'This period overlaps current statements:\n'+overlap_details+'\n\nSave anyway? Both statements will be included in monthly totals and marked for overlap review.'):
                    return None
                allow_overlap=True

        if action=='print' and rental>0:self._show_utilities_reminder()
        pdf_path = generate_payroll_pdf(
            employee_name=emp["name"],
            employee_rate=emp["rate"],
            rows=rows,
            rate_mode=self.rate_mode.get(),
            utilities=str(utilities),
            rental=str(rental),
            period_from=self.from_entry.get(),
            period_to=self.to_entry.get(),
            bank_name=details['bank'],
            iban=details['iban'],
            bic=details['bic'],
            action=action,
            employee_id=emp['id'],
        )
        if action == 'save':
            try:
                self.db.save_payroll(emp['id'], self.days_data, self.rate_mode.get(), context[1], context[2],
                    utilities=str(utilities),rental=str(rental),pdf_path=pdf_path,
                    day_rules=self._day_rules(),distribution_settings=settings,replaces_ids=replaces_ids,
                    allow_overlap=allow_overlap,expected_current_ids=expected_ids)
            except Exception:
                # Only remove the unique file just generated by this attempt.
                if Path(pdf_path).name.startswith('Payroll_'):Path(pdf_path).unlink(missing_ok=True)
                raise
            self._dirty = False
            self._payroll_dirty = False
            self._distribution_dirty=False
            self._saved_kind = 'payroll'
            self._update_save_status()
            self._last_pdf_saved=True
        return pdf_path

    def _save_draft(self):
        try:
            emp = self.employee_map.get(self.employee_cb.get())
            context = None if emp is None else (emp['id'],self.from_entry.get_date().isoformat(),self.to_entry.get_date().isoformat())
            if not self.days_data or context != self._context or self._editor is not None:
                raise ValueError('Generate this period and finish editing before saving hours')
            self._save_hours_to_database(emp['id'])
            self._dirty = False
            self._distribution_dirty=False
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
        self.db.save_period_hours(emp_id,self.days_data,self._day_rules(),self._distribution_settings())
