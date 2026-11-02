"""Quiet, flat desktop styling shared across PayrollSystem."""
from tkinter import ttk

COLORS={
    'bg':'#F3F6FA','card':'#FFFFFF','border':'#DFE6EF',
    'zebra_odd':'#F7F9FC','zebra_even':'#FFFFFF',
    'text':'#172B46','text_secondary':'#62748B','muted':'#62748B',
    'accent':'#2864D7','accent_hover':'#1D50B5',
    'positive':'#167552','positive_hover':'#116144',
    'negative':'#B54444','negative_hover':'#973535',
    'warning':'#98651F','warning_hover':'#7B5016',
    'neutral':'#52677F','neutral_hover':'#3E526A',
    'disabled_bg':'#F0F3F7','disabled_text':'#91A0B2',
}


def setup_styles(root):
    style=ttk.Style(root)
    style.theme_use('clam')
    style.configure('.',font=('Segoe UI',10),foreground=COLORS['text'],background=COLORS['card'])
    style.configure('TFrame',background=COLORS['card'])
    style.configure('App.TFrame',background=COLORS['bg'])
    style.configure('StatusBar.TFrame',background=COLORS['card'],borderwidth=0)
    style.configure('Card.TFrame',background=COLORS['card'],bordercolor=COLORS['border'],
                    lightcolor=COLORS['card'],darkcolor=COLORS['card'],borderwidth=1,relief='solid')
    style.configure('TLabel',background=COLORS['card'],foreground=COLORS['text'],font=('Segoe UI',10))
    style.configure('Muted.TLabel',foreground=COLORS['muted'])
    style.configure('TNotebook',background=COLORS['bg'],borderwidth=0,tabmargins=(0,0,0,10))
    style.configure('TNotebook.Tab',padding=(18,9),font=('Segoe UI',10,'bold'),background=COLORS['bg'],
                    foreground=COLORS['muted'],borderwidth=0,lightcolor=COLORS['bg'],darkcolor=COLORS['bg'])
    style.map('TNotebook.Tab',background=[('selected',COLORS['card']),('active','#EAF0F8')],
              foreground=[('selected',COLORS['accent']),('active',COLORS['text'])])
    style.configure('TButton',font=('Segoe UI',9),padding=(12,7),background=COLORS['card'],
                    foreground=COLORS['text'],bordercolor=COLORS['border'],borderwidth=1,relief='solid',
                    lightcolor=COLORS['card'],darkcolor=COLORS['card'],focuscolor=COLORS['accent'])
    style.map('TButton',background=[('disabled',COLORS['disabled_bg']),('pressed','#E5ECF6'),('active','#EEF3FA')],
              foreground=[('disabled',COLORS['disabled_text'])],bordercolor=[('focus',COLORS['accent']),('active','#B5C8E3')])
    for name in ('Accent.TButton','Success.TButton'):
        style.configure(name,background=COLORS['accent'],foreground='white',bordercolor=COLORS['accent'],
                        font=('Segoe UI',9,'bold'),padding=(12,8))
        style.map(name,background=[('disabled',COLORS['disabled_bg']),('pressed','#17469F'),('active',COLORS['accent_hover'])],
                  foreground=[('disabled',COLORS['disabled_text']),('!disabled','white')],
                  bordercolor=[('disabled',COLORS['border']),('!disabled',COLORS['accent'])])
    style.configure('Warning.TButton',foreground=COLORS['accent'])
    style.configure('Neutral.TButton',foreground=COLORS['neutral'])
    style.configure('Danger.TButton',foreground=COLORS['negative'])
    style.map('Danger.TButton',foreground=[('disabled',COLORS['disabled_text']),('!disabled',COLORS['negative'])])
    style.configure('Quiet.TButton',borderwidth=0,foreground=COLORS['accent'],padding=(8,4))
    style.configure('PayrollSecondary.TButton',font=('Segoe UI',9),padding=(10,6),background='#F8FAFD',bordercolor='#D2DCEB')
    for name in ('TEntry','TCombobox','TSpinbox'):
        style.configure(name,padding=(9,6),fieldbackground=COLORS['card'],background=COLORS['card'],
                        bordercolor=COLORS['border'],lightcolor=COLORS['card'],darkcolor=COLORS['card'],
                        arrowcolor=COLORS['muted'],insertcolor=COLORS['text'],relief='flat')
        style.map(name,bordercolor=[('focus',COLORS['accent'])],
                  fieldbackground=[('disabled',COLORS['disabled_bg']),('readonly',COLORS['card'])],
                  foreground=[('disabled',COLORS['disabled_text']),('readonly',COLORS['text'])])
    style.configure('TRadiobutton',background=COLORS['card'],font=('Segoe UI',9),padding=(0,2))
    style.configure('TCheckbutton',background=COLORS['card'],font=('Segoe UI',9))
    style.configure('Treeview',font=('Segoe UI',10),rowheight=34,background=COLORS['card'],
                    fieldbackground=COLORS['card'],foreground=COLORS['text'],borderwidth=0,
                    bordercolor=COLORS['border'],lightcolor=COLORS['card'],darkcolor=COLORS['card'],relief='flat')
    style.map('Treeview',background=[('selected','#E8F0FF')],foreground=[('selected','#173F7E')])
    style.configure('Treeview.Heading',font=('Segoe UI',9,'bold'),padding=(10,8),background='#EFF3F8',
                    foreground=COLORS['muted'],bordercolor='#EFF3F8',lightcolor='#EFF3F8',darkcolor='#EFF3F8',relief='flat')
    style.map('Treeview.Heading',background=[('active','#E8EEF7')])
    for name in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
        style.configure(name,background='#CAD5E4',troughcolor=COLORS['card'],bordercolor=COLORS['card'],
                        lightcolor='#CAD5E4',darkcolor='#CAD5E4',arrowcolor=COLORS['muted'],arrowsize=11,borderwidth=0)
        style.map(name,background=[('active','#9BADBF'),('pressed','#899DB5')])
    style.configure('TSeparator',background=COLORS['border'])
    style.configure('PayrollCard.TFrame',background=COLORS['card'])
    style.configure('PayrollHeading.TLabel',font=('Segoe UI',11,'bold'))
    style.configure('PayrollBody.TLabel',font=('Segoe UI',9))
    style.configure('PayrollHint.TLabel',foreground=COLORS['muted'],font=('Segoe UI',9))
    style.configure('PayrollStatus.TLabel',foreground=COLORS['muted'],font=('Segoe UI',9))
    style.configure('PayrollNet.TLabel',font=('Segoe UI',24,'bold'),foreground=COLORS['accent'])
    style.configure('PayrollTotal.TFrame',background='#EEF4FF')
    style.configure('PayrollTotalCaption.TLabel',background='#EEF4FF',foreground='#5A75A0',font=('Segoe UI',9,'bold'))
    style.configure('PayrollTotalValue.TLabel',background='#EEF4FF',foreground='#2359B8',font=('Segoe UI',24,'bold'))
    style.configure('Payroll.TRadiobutton',font=('Segoe UI',9))
    style.configure('Payroll.Treeview',rowheight=34)
    style.configure('Payroll.Treeview.Heading',font=('Segoe UI',9,'bold'),padding=(9,8))
    for suffix,foreground,background in [('Yes','#17634B','#E7F5EE'),('No','#54657A','#EDF1F6'),('Unknown','#875D20','#FFF3DA')]:
        style.configure('Account'+suffix+'.TLabel',foreground=foreground,background=background,
                        font=('Segoe UI',9,'bold'),padding=(10,5))
