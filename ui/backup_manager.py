import os
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from core.backup import backup_db,verify_database,latest_backup,remember_backup_location


class BackupManager(tk.Toplevel):
    def __init__(self,parent,db_path,on_restore):
        super().__init__(parent)
        self.title('Backups and restore');self.geometry('760x420');self.minsize(760,420)
        self.db_path=Path(db_path);self.on_restore=on_restore
        self.status=tk.StringVar();self.location=tk.StringVar()
        box=ttk.Frame(self,padding=18);box.pack(fill='both',expand=True)
        ttk.Label(box,text='Last verified backup',font=('Segoe UI',12,'bold')).pack(anchor='w')
        ttk.Label(box,textvariable=self.status,wraplength=660).pack(anchor='w',pady=(10,4))
        ttk.Label(box,textvariable=self.location,wraplength=660).pack(anchor='w')
        actions=ttk.Frame(box);actions.pack(fill='x',pady=18)
        ttk.Button(actions,text='Create backup',command=self._create).pack(side='left')
        ttk.Button(actions,text='Save to another location',command=self._save_elsewhere).pack(side='left',padx=8)
        ttk.Button(actions,text='Open backup folder',command=self._open_folder).pack(side='left')
        ttk.Separator(box).pack(fill='x',pady=(0,15))
        ttk.Label(box,text='Restore replaces the working database. A verified copy of the current data is kept first. PDF files are stored separately.',wraplength=660).pack(anchor='w')
        ttk.Button(box,text='Choose backup to restore…',command=self._restore).pack(anchor='w',pady=12)
        self._refresh()

    def _refresh(self):
        latest=latest_backup(self.db_path)
        if latest is None:
            self.status.set('No backup found. Create one before updating the program.');self.location.set('');return
        self.location.set(str(latest))
        try:
            info=verify_database(latest)
            self.status.set(f'{datetime.fromtimestamp(latest.stat().st_mtime):%Y-%m-%d %H:%M} · Integrity verified · '
                            f'{info["employees"]} employees, {info["hours"]} hour entries, {info["payrolls"]} statements')
        except Exception as exc:self.status.set('Latest backup could not be verified: '+str(exc))

    def _create(self):
        try:
            path=backup_db(self.db_path)
            self._refresh();messagebox.showinfo('Backup saved',f'Verified backup:\n{path}',parent=self)
        except Exception as exc:messagebox.showerror('Backup failed',str(exc),parent=self)

    def _save_elsewhere(self):
        path=filedialog.asksaveasfilename(parent=self,title='Save a verified database backup',defaultextension='.db',
            initialfile=f'payroll_backup_{datetime.now():%Y%m%d_%H%M%S_%f}.db',filetypes=[('Database backup','*.db')])
        if not path:return
        try:
            backup_db(self.db_path,path)
            remember_backup_location(self.db_path,path)
            self._refresh()
            messagebox.showinfo('Backup saved',f'Verified backup:\n{path}',parent=self)
        except Exception as exc:messagebox.showerror('Backup failed',str(exc),parent=self)

    def _open_folder(self):
        latest=latest_backup(self.db_path)
        folder=latest.parent if latest else self.db_path.parent/'backups';folder.mkdir(exist_ok=True)
        if os.name=='nt':os.startfile(str(folder))

    def _restore(self):
        path=filedialog.askopenfilename(parent=self,title='Choose a database backup',initialdir=str(self.db_path.parent/'backups'),filetypes=[('Database backup','*.db'),('All files','*.*')])
        if path:self.on_restore(path)
