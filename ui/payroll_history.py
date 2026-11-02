import tkinter as tk
from tkinter import ttk,messagebox
from services.report_service import preview_payroll_pdf_from_history


class PayrollHistory(tk.Toplevel):
    def __init__(self, parent, db,employee_id=None,period_end_month=None):
        super().__init__(parent)
        self.title("Payroll History")
        self.geometry("960x450")
        self.minsize(700,350)

        self.db = db
        self.employee_id=employee_id
        self.period_end_month=period_end_month
        self.current_only=tk.BooleanVar(value=False)
        toolbar=ttk.Frame(self,padding=10);toolbar.pack(fill='x')
        ttk.Label(toolbar,text='Originals remain in history. Corrections replace them in totals.',wraplength=460).pack(side='left')
        ttk.Checkbutton(toolbar,text='Current only',variable=self.current_only,command=self._load).pack(side='right')
        ttk.Button(toolbar,text='Refresh',command=self._load).pack(side='right',padx=8)

        container=ttk.Frame(self);container.pack(fill='both',expand=True,padx=10)
        container.rowconfigure(0,weight=1);container.columnconfigure(0,weight=1)
        self.tree = ttk.Treeview(
            container,
            columns=("id", "employee", "period", "created", "net",'status','corrects'),
            show="headings"
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("employee", text="Employee")
        self.tree.heading("period", text="Period")
        self.tree.heading("created", text="Created")
        self.tree.heading("net", text="Net amount")
        self.tree.heading('status',text='Status')
        self.tree.heading('corrects',text='Corrects')

        self.tree.column("id", width=50, anchor="center")

        for column,width in [('employee',160),('period',200),('created',145),('net',100),('status',150),('corrects',90)]:
            self.tree.column(column,width=width,minwidth=60)
        self.tree.grid(row=0,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(container,command=self.tree.yview);vertical.grid(row=0,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(container,orient='horizontal',command=self.tree.xview);horizontal.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        actions=ttk.Frame(self,padding=10);actions.pack(fill='x')
        ttk.Button(actions,text='Open selected PDF',command=self._open_pdf).pack(side='left')
        ttk.Label(actions,text='Create corrections from the Payroll screen.').pack(side='right')

        self.tree.bind("<Double-1>", self._open_pdf)

        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.get_payrolls(current_only=self.current_only.get()):
            if self.employee_id is not None and r['employee_id']!=self.employee_id:continue
            if self.period_end_month and not r['period_to'].startswith(self.period_end_month):continue
            self.tree.insert(
                "",
                "end",
                iid=str(r['id']),
                values=(
                    r["id"],
                    f'{r["name"]} [#{r["employee_id"]}]',
                    f"{r['period_from']} – {r['period_to']}",
                    r["created_at"],
                    f"{r['net_amount']:.2f} €",
                    f'Superseded by #{r["superseded_by"]}' if r['superseded_by'] else 'Current',
                    r['corrects'] or ''
                )
            )

    def _open_pdf(self, event=None):
        item = self.tree.selection()
        if not item:
            return

        payroll_id = self.tree.item(item[0])["values"][0]
        try:
            payroll, days = self.db.get_payroll_full(payroll_id)
            preview_payroll_pdf_from_history(payroll, days)
        except Exception as exc:messagebox.showerror('Payroll history',str(exc),parent=self)
