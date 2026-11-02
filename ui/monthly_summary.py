import tkinter as tk
from tkinter import ttk,messagebox
from datetime import date,datetime
from ui.payroll_history import PayrollHistory


class MonthlySummary(tk.Toplevel):
    def __init__(self,parent,db,on_open_employee=None):
        super().__init__(parent)
        self.title('Monthly summary');self.geometry('1020x550');self.minsize(780,400)
        self.db=db;self.on_open_employee=on_open_employee
        self.month=tk.StringVar(value=date.today().strftime('%Y-%m'))
        self.totals=tk.StringVar();self.notice=tk.StringVar();self.data=None
        header=ttk.Frame(self,padding=12);header.pack(fill='x')
        ttk.Label(header,text='Month (YYYY-MM)').pack(side='left')
        ttk.Entry(header,textvariable=self.month,width=10).pack(side='left',padx=8)
        ttk.Button(header,text='Refresh',command=self._load).pack(side='left')
        ttk.Label(header,text='Saved current statements · by period end').pack(side='right')
        frame=ttk.Frame(self)
        frame.columnconfigure(0,weight=1);frame.rowconfigure(0,weight=1)
        columns=('employee','hours','gross','deductions','net','draft','status')
        self.tree=ttk.Treeview(frame,columns=columns,show='headings')
        for col,text,width in [('employee','Employee',210),('hours','Issued hours',100),('gross','Gross pay',110),('deductions','Deductions',110),('net','Net pay',110),('draft','Draft hours',100),('status','Status',180)]:
            self.tree.heading(col,text=text);self.tree.column(col,width=width,minwidth=65,anchor='w' if col in ('employee','status') else 'e')
        self.tree.grid(row=0,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(frame,command=self.tree.yview);vertical.grid(row=0,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=self.tree.xview);horizontal.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        footer=ttk.Frame(self,padding=12);footer.pack(fill='x')
        total_label=ttk.Label(footer,textvariable=self.totals,font=('Segoe UI',10,'bold'),wraplength=950)
        total_label.pack(anchor='w')
        notice_label=ttk.Label(footer,textvariable=self.notice,wraplength=950)
        notice_label.pack(anchor='w',pady=8)
        footer.bind('<Configure>',lambda e:(total_label.configure(wraplength=max(100,e.width-24)),notice_label.configure(wraplength=max(100,e.width-24))))
        actions=ttk.Frame(footer);actions.pack(fill='x')
        ttk.Button(actions,text='Open employee history',command=self._history).pack(side='left')
        if on_open_employee:ttk.Button(actions,text='Open timesheet',command=self._timesheet).pack(side='left',padx=8)
        footer.pack_configure(side='bottom')
        frame.pack(fill='both',expand=True,padx=12)
        self.tree.bind('<Double-1>',lambda e:self._history())
        self._load()

    def _load(self):
        try:
            month=datetime.strptime(self.month.get(),'%Y-%m')
            self.data=self.db.get_month_summary(month.year,month.month)
            self.month.set(self.data['month'])
        except (ValueError,OverflowError):
            if self.data is not None:self.month.set(self.data['month'])
            messagebox.showerror('Month','Enter a valid month as YYYY-MM',parent=self);return
        self.tree.delete(*self.tree.get_children())
        for e in self.data['rows']:
            status=[]
            if e['review_ids']:status.append('Needs review')
            if set(e['payroll_ids'])&set(self.data['overlap_ids']):status.append('Overlap included')
            if e['draft_days']:status.append('Draft hours')
            self.tree.insert('','end',iid=str(e['employee_id']),values=(f'{e["name"]} [#{e["employee_id"]}]',f'{e["hours"]:g}',
                f'{e["gross"]:.2f} €',f'{e["deductions"]:.2f} €',f'{e["net"]:.2f} €',f'{e["draft_hours"]:g}',' · '.join(status) or 'Current'))
        t=self.data['totals']
        self.totals.set(f'Issued hours: {t["hours"]:g}    Gross: {t["gross"]:.2f} €    Deductions: {t["deductions"]:.2f} €    Net pay: {t["net"]:.2f} €')
        self.notice.set(f'{len(self.data["included_ids"])} current statements included. '
            f'{len(self.data["review_ids"])} duplicate-period statements excluded pending review. '
            f'{len(self.data["overlap_ids"])} overlapping statements included. Draft hours are separate from pay totals.')

    def _selected(self):
        selected=self.tree.selection()
        if not selected:
            messagebox.showinfo('Monthly summary','Select an employee first',parent=self);return None
        return int(selected[0])

    def _history(self):
        eid=self._selected()
        if eid is not None:PayrollHistory(self,self.db,employee_id=eid,period_end_month=self.data['month'])

    def _timesheet(self):
        eid=self._selected()
        if eid is not None and self.on_open_employee(eid,self.data['month']):self.destroy()
