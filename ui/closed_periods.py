import tkinter as tk
from tkinter import ttk,messagebox
from ui.payroll_history import PayrollHistory


class ClosedPeriods(tk.Toplevel):
    def __init__(self,parent,db,on_change=None):
        super().__init__(parent)
        self.title('Closed periods');self.geometry('980x470');self.minsize(760,380)
        self.db=db;self.on_change=on_change
        header=ttk.Frame(self,padding=12);header.pack(fill='x')
        ttk.Button(header,text='Refresh',command=self._load).pack(side='right')
        note=ttk.Label(header,text='Closed periods are protected. Reopening permits hours and corrected statements again.',wraplength=740)
        note.pack(side='left',fill='x',expand=True,padx=(0,12))
        note.bind('<Configure>',lambda event:note.configure(wraplength=max(100,event.width)))
        actions=ttk.Frame(self,padding=12);actions.pack(side='bottom',fill='x')
        ttk.Button(actions,text='Open saved statements',command=self._history).pack(side='left')
        ttk.Button(actions,text='Reopen selected period',command=self._reopen).pack(side='left',padx=8)
        box=ttk.Frame(self,padding=(12,0));box.pack(fill='both',expand=True)
        box.columnconfigure(0,weight=1);box.rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(box,columns=('employee','period','closed','reopened','status'),show='headings')
        for col,label,width in [('employee','Employee',240),('period','Period',230),('closed','Closed',160),('reopened','Reopened',160),('status','Status',100)]:
            self.tree.heading(col,text=label);self.tree.column(col,width=width,minwidth=90)
        self.tree.grid(row=0,column=0,sticky='nsew')
        v=ttk.Scrollbar(box,command=self.tree.yview);v.grid(row=0,column=1,sticky='ns')
        h=ttk.Scrollbar(box,orient='horizontal',command=self.tree.xview);h.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=v.set,xscrollcommand=h.set)
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children());self.records={}
        for r in self.db.get_closed_periods(active_only=False):
            self.records[str(r['id'])]=r
            self.tree.insert('','end',iid=str(r['id']),values=(f'{r["name"]} [#{r["employee_id"]}]',
                r['period_from']+' — '+r['period_to'],r['closed_at'],r['reopened_at'] or '',
                'Reopened' if r['reopened_at'] else 'Closed'))

    def _selected(self):
        selected=self.tree.selection()
        if not selected:messagebox.showinfo('Closed periods','Select a period first',parent=self);return None
        return self.records[selected[0]]

    def _history(self):
        r=self._selected()
        if r is not None:PayrollHistory(self,self.db,employee_id=r['employee_id'],period=(r['period_from'],r['period_to']))

    def _reopen(self):
        r=self._selected()
        if r is None:return
        if r['reopened_at']:messagebox.showinfo('Closed periods','This period has already been reopened',parent=self);return
        if not messagebox.askyesno('Reopen period?','Allow edits and corrected statements for '+r['period_from']+' — '+r['period_to']+'? Originals stay in history.',parent=self):return
        try:self.db.reopen_period(r['id'])
        except ValueError as exc:messagebox.showerror('Reopen period',str(exc),parent=self);return
        self._load()
        if self.on_change:self.on_change()
