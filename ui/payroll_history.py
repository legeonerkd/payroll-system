import tkinter as tk
from tkinter import ttk,messagebox
from services.report_service import preview_payroll_pdf_from_history,print_payroll_pdf_from_history,open_payroll_pdf_folder


class PayrollHistory(tk.Toplevel):
    def __init__(self, parent, db,employee_id=None,period_end_month=None,period=None):
        super().__init__(parent)
        self.title("Payroll History")
        self.geometry("960x450")
        self.minsize(700,350)

        self.db = db
        self.employee_id=employee_id
        self.period_end_month=period_end_month
        self.period=period
        self.current_only=tk.BooleanVar(value=False)
        toolbar=ttk.Frame(self,padding=10);toolbar.pack(fill='x')
        ttk.Label(toolbar,text='Originals remain in history. Corrections replace them in totals.',wraplength=460).pack(side='left')
        ttk.Checkbutton(toolbar,text='Current only',variable=self.current_only,command=self._load).pack(side='right')
        ttk.Button(toolbar,text='Refresh',command=self._load).pack(side='right',padx=8)

        container=ttk.Frame(self)
        container.rowconfigure(0,weight=1);container.columnconfigure(0,weight=1)
        self.tree = ttk.Treeview(
            container,
            columns=("id", "employee", "period",'mode', "created", "net",'status','corrects'),
            show="headings"
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("employee", text="Employee")
        self.tree.heading("period", text="Period")
        self.tree.heading('mode',text='Rate')
        self.tree.column('mode',width=110,minwidth=85)
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
        buttons=ttk.Frame(actions);buttons.pack(fill='x')
        ttk.Button(buttons,text='Open selected PDF',command=self._open_pdf).pack(side='left')
        ttk.Button(buttons,text='Print selected PDF',command=self._print_selected).pack(side='left',padx=8)
        ttk.Button(buttons,text='Open PDF folder',command=self._open_folder).pack(side='left')
        self.notice=tk.StringVar(value='Reprints use saved amounts. Create corrections from Payroll after reopening a closed period.')
        notice=ttk.Label(actions,textvariable=self.notice,wraplength=900)
        notice.pack(fill='x',pady=(8,0))
        notice.bind('<Configure>',lambda event:notice.configure(wraplength=max(100,event.width)))
        actions.pack_configure(side='bottom')
        container.pack(fill='both',expand=True,padx=10)

        self.tree.bind("<Double-1>", self._open_pdf)

        self._load()

    def _load(self):
        self.tree.delete(*self.tree.get_children())
        for r in self.db.get_payrolls(current_only=self.current_only.get()):
            if self.employee_id is not None and r['employee_id']!=self.employee_id:continue
            if self.period_end_month and not r['period_to'].startswith(self.period_end_month):continue
            if self.period and (r['period_from'],r['period_to'])!=self.period:continue
            self.tree.insert(
                "",
                "end",
                iid=str(r['id']),
                values=(
                    r["id"],
                    f'{r["name"]} [#{r["employee_id"]}]',
                    f"{r['period_from']} – {r['period_to']}",
                    'Fixed' if r['rate_mode']=='fixed' else 'Employee',
                    r["created_at"],
                    f"{r['net_amount']:.2f} €",
                    f'Superseded by #{r["superseded_by"]}' if r['superseded_by'] else ('Closed' if self.db.period_is_closed(r['employee_id'],r['period_from'],r['period_to']) else 'Current'),
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

    def _print_selected(self):
        selected=self.tree.selection()
        if not selected:messagebox.showinfo('Print saved PDF','Select one statement first',parent=self);return
        try:
            payroll,days=self.db.get_payroll_full(int(selected[0]))
            if payroll['rental']>0:
                self.notice.set(f'Utilities reminder: this saved statement deducts rental. Saved utilities: {payroll["utilities"]:.2f} € (0 is valid). Reprinting does not change the amounts.')
                self.update_idletasks()
            print_payroll_pdf_from_history(payroll,days)
            if payroll['rental']==0:self.notice.set('Selected saved PDF sent to the print application. No other statement was sent.')
        except Exception as exc:messagebox.showerror('Print saved PDF',str(exc),parent=self)

    def _open_folder(self):
        selected=self.tree.selection()
        try:
            payroll=self.db.get_payroll_full(int(selected[0]))[0] if selected else None
            open_payroll_pdf_folder(payroll)
        except Exception as exc:messagebox.showerror('Open PDF folder',str(exc),parent=self)
