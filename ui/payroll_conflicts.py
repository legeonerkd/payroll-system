import tkinter as tk
from tkinter import ttk


def choose_existing_payroll(parent,records):
    """Return an explicit user choice; no database mutation happens here."""
    dialog=tk.Toplevel(parent)
    dialog.title('A payroll already exists')
    dialog.transient(parent.winfo_toplevel())
    dialog.resizable(False,False)
    box=ttk.Frame(dialog,padding=16);box.pack(fill='both',expand=True)
    ttk.Label(box,text='This employee already has a statement for the selected rate and exact period.',wraplength=540).pack(anchor='w')
    ttk.Label(box,text='Open a saved statement, or create a corrected version. Originals remain in history.',wraplength=540).pack(anchor='w',pady=(5,12))
    tree=ttk.Treeview(box,columns=('id','period','net'),show='headings',height=min(5,len(records)))
    for column,text,width in [('id','ID',60),('period','Period',280),('net','Net pay',120)]:
        tree.heading(column,text=text);tree.column(column,width=width)
    for p in records:
        tree.insert('','end',iid=str(p['id']),values=(p['id'],p['period_from']+' — '+p['period_to'],f'{p["net_amount"]:.2f} €'))
    tree.pack(fill='x');tree.selection_set(str(records[0]['id']))
    result=[]
    def finish(action):
        if action=='open':
            selected=tree.selection()
            if not selected:return
            result.append(('open',int(selected[0])))
        elif action=='correct':result.append(('correct',[p['id'] for p in records]))
        dialog.destroy()
    actions=ttk.Frame(box);actions.pack(fill='x',pady=(14,0))
    ttk.Button(actions,text='Open selected',command=lambda:finish('open')).pack(side='left',padx=(0,8))
    ttk.Button(actions,text='Create corrected version',command=lambda:finish('correct')).pack(side='left')
    ttk.Button(actions,text='Cancel',command=lambda:finish('cancel')).pack(side='right')
    dialog.bind('<Escape>',lambda e:finish('cancel'))
    dialog.grab_set();parent.wait_window(dialog)
    return result[0] if result else None
