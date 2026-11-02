import tkinter as tk
from tkinter import ttk


class ScrollableCard(ttk.Frame):
    """A native form that stays reachable at small window sizes and large text scales."""
    def __init__(self,parent,padding=16,min_width=280):
        super().__init__(parent,style='Card.TFrame')
        self.columnconfigure(0,weight=1);self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,background='white',highlightthickness=0,borderwidth=0,width=min_width,height=1)
        self.canvas.grid(row=0,column=0,sticky='nsew')
        scrollbar=ttk.Scrollbar(self,command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.content=ttk.Frame(self.canvas,padding=padding,style='PayrollCard.TFrame')
        window=self.canvas.create_window(0,0,anchor='nw',window=self.content)
        def resize(event=None):
            self.canvas.configure(width=max(min_width,self.content.winfo_reqwidth()))
            self.canvas.itemconfigure(window,width=max(self.canvas.winfo_width(),self.content.winfo_reqwidth()))
            self.canvas.configure(scrollregion=self.canvas.bbox('all'))
            if self.content.winfo_reqheight()>self.canvas.winfo_height():scrollbar.grid(row=0,column=1,sticky='ns')
            else:scrollbar.grid_remove();self.canvas.yview_moveto(0)
        self.canvas.bind('<Configure>',resize);self.content.bind('<Configure>',resize)

    def bind_controls(self):
        def visit(widget):
            widget.bind('<FocusIn>',self.ensure_visible,add='+')
            widget.bind('<MouseWheel>',self._wheel,add='+')
            for child in widget.winfo_children():visit(child)
        visit(self.content)

    def _wheel(self,event):
        if self.canvas.yview()!=(0.0,1.0):
            self.canvas.yview_scroll(-1 if event.delta>0 else 1,'units');return 'break'

    def ensure_visible(self,event):
        total=self.content.winfo_height();height=self.canvas.winfo_height()
        if total<=height:return
        top=event.widget.winfo_rooty()-self.content.winfo_rooty();bottom=top+event.widget.winfo_height()
        current=self.canvas.canvasy(0)
        if top<current:self.canvas.yview_moveto(top/total)
        elif bottom>current+height:self.canvas.yview_moveto((bottom-height)/total)
