import tkinter as tk
from tkinter import ttk,messagebox
from datetime import date
import webbrowser
from core.cyprus_holidays import cyprus_holidays,SOURCE_URL,CHECKED_ON


class CyprusHolidays(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent)
        self.title('Cyprus holidays');self.geometry('820x560');self.minsize(660,390)
        self.year=tk.StringVar(value=str(date.today().year))
        header=ttk.Frame(self,padding=12);header.pack(fill='x')
        ttk.Label(header,text='Year').pack(side='left')
        ttk.Spinbox(header,from_=2000,to=2100,textvariable=self.year,width=7,command=self._load).pack(side='left',padx=8)
        ttk.Button(header,text='Show calendar',command=self._load).pack(side='left')
        ttk.Button(header,text='Official source',command=lambda:webbrowser.open(SOURCE_URL)).pack(side='right')
        footer=ttk.Frame(self,padding=12);footer.pack(side='bottom',fill='x')
        note=ttk.Label(footer,text='Automatic distribution skips these dates. Manual hours are allowed; lock them to preserve them on redistribution. '
            'Company-specific days can use Exclude. Calendar: Visit Cyprus, checked '+CHECKED_ON+'. '
            'Movable dates follow Orthodox Easter (Pentecost is Easter + 50 days). Bank-only Easter Tuesday is not included.',wraplength=770)
        note.pack(fill='x');note.bind('<Configure>',lambda event:note.configure(wraplength=max(100,event.width)))
        box=ttk.Frame(self,padding=(12,0));box.pack(fill='both',expand=True)
        box.columnconfigure(0,weight=1);box.rowconfigure(0,weight=1)
        self.tree=ttk.Treeview(box,columns=('date','day','name'),show='headings')
        for col,label,width in [('date','Date',130),('day','Day',130),('name','Holiday',430)]:
            self.tree.heading(col,text=label);self.tree.column(col,width=width,minwidth=95)
        self.tree.grid(row=0,column=0,sticky='nsew')
        v=ttk.Scrollbar(box,command=self.tree.yview);v.grid(row=0,column=1,sticky='ns')
        h=ttk.Scrollbar(box,orient='horizontal',command=self.tree.xview);h.grid(row=1,column=0,sticky='ew')
        self.tree.configure(yscrollcommand=v.set,xscrollcommand=h.set)
        self._load()

    def _load(self):
        try:days=cyprus_holidays(int(self.year.get()))
        except (ValueError,OverflowError):messagebox.showerror('Cyprus holidays','Enter a valid year from 1 to 9999',parent=self);return
        self.tree.delete(*self.tree.get_children())
        for day,name in days.items():self.tree.insert('','end',iid=day.isoformat(),values=(day.strftime('%d-%m-%Y'),day.strftime('%A'),name))
