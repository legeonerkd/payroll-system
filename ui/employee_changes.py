import tkinter as tk
from tkinter import ttk
from core.banking import ACCOUNT_LABELS


class EmployeeChanges(tk.Toplevel):
    def __init__(self,parent,db,employee_id=None):
        super().__init__(parent)
        self.title('Employee change history');self.geometry('980x470');self.minsize(760,360)
        self.db=db;self.employee_id=employee_id
        header=ttk.Frame(self,padding=12);header.pack(fill='x')
        ttk.Button(header,text='Refresh',command=self._load).pack(side='right')
        note=ttk.Label(header,text='Rate, rental and bank-status changes recorded since this feature was installed.',wraplength=680)
        note.pack(side='left',fill='x',expand=True,padx=(0,12))
        note.bind('<Configure>',lambda event:note.configure(wraplength=max(100,event.width)))
        box=ttk.Frame(self,padding=(12,0,12,12));box.pack(fill='both',expand=True)
        box.columnconfigure(0,weight=1);box.rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(box,columns=('time','employee','field','before','after'),show='headings')
        for col,label,width in [('time','Changed',165),('employee','Employee',250),('field','Field',160),('before','Before',150),('after','After',150)]:
            self.tree.heading(col,text=label);self.tree.column(col,width=width,minwidth=100)
        self.tree.grid(row=0,column=0,sticky='nsew')
        v=ttk.Scrollbar(box,command=self.tree.yview);v.grid(row=0,column=1,sticky='ns')
        h=ttk.Scrollbar(box,orient='horizontal',command=self.tree.xview);h.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=v.set,xscrollcommand=h.set)
        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        labels={'rate':'Hourly rate','rental_amount':'Rental / statement','bank_account_state':'Bank account'}
        for r in self.db.get_employee_changes(self.employee_id):
            def value(raw):
                if raw is None:return 'Initial value'
                return ACCOUNT_LABELS.get(raw,raw) if r['field']=='bank_account_state' else raw+' €'
            self.tree.insert('','end',iid=str(r['id']),values=(r['changed_at'],f'{r["name"]} [#{r["employee_id"]}]',
                labels[r['field']],value(r['old_value']),value(r['new_value'])))
