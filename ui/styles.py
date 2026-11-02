from tkinter import ttk

COLORS = {
    # Backgrounds (Windows 11 style)
    "bg": "#f4f6f8",
    "card": "#ffffff",
    "border": "#dcdcdc",
    "zebra_odd": "#f9f9f9",
    "zebra_even": "#ffffff",

    # Text
    "text": "#212529",
    "text_secondary": "#6C757D",
    "muted": "#6C757D",

    # Accents (Modern palette)
    "accent": "#2563eb",      # Синий
    "accent_hover": "#1d4ed8",
    "positive": "#16a34a",    # Зелёный
    "positive_hover": "#15803d",
    "negative": "#dc2626",    # Красный
    "negative_hover": "#b91c1c",
    "warning": "#ea580c",     # Оранжевый
    "warning_hover": "#c2410c",
    "neutral": "#64748b",     # Серый
    "neutral_hover": "#475569",

    # Disabled
    "disabled_bg": "#E9ECEF",
    "disabled_text": "#ADB5BD",
}


def setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("default")

    # Payroll screen uses compact controls so the side summary stays visible.
    style.configure('PayrollCard.TFrame',background=COLORS['card'])
    style.configure('PayrollHeading.TLabel',background=COLORS['card'],font=('Segoe UI',10,'bold'))
    style.configure('PayrollBody.TLabel',background=COLORS['card'],font=('Segoe UI',9))
    style.configure('PayrollHint.TLabel',background=COLORS['card'],foreground='#526276',font=('Segoe UI',9))
    style.configure('PayrollStatus.TLabel',background=COLORS['card'],font=('Segoe UI',9))
    style.configure('PayrollNet.TLabel',background=COLORS['card'],font=('Segoe UI',19,'bold'),foreground=COLORS['accent'])
    style.configure('PayrollSecondary.TButton',background=COLORS['card'],foreground=COLORS['text'],font=('Segoe UI',9),padding=(9,5))
    style.map('PayrollSecondary.TButton',background=[('active','#e9eef6')],foreground=[('disabled',COLORS['disabled_text'])])
    style.configure('Payroll.TRadiobutton',background=COLORS['card'],font=('Segoe UI',9))
    style.configure('Payroll.Treeview',font=('Segoe UI',10),rowheight=30)
    style.configure('Payroll.Treeview.Heading',font=('Segoe UI',9,'bold'),padding=(6,5))

    # ---------- Base ----------
    style.configure(
        ".",
        background=COLORS["bg"],
        foreground=COLORS["text"],
        font=("Segoe UI", 10),
    )

    # ---------- Notebook ----------
    style.configure(
        "TNotebook",
        background=COLORS["bg"],
        borderwidth=0,
    )

    style.configure(
        "TNotebook.Tab",
        padding=(14, 7),
        font=("Segoe UI", 10, "bold"),
    )

    # ---------- Card ----------
    style.configure(
        "Card.TFrame",
        background=COLORS["card"],
        borderwidth=1,
        relief="solid",
    )

    # ---------- Labels ----------
    style.configure(
        "TLabel",
        background=COLORS["card"],
        font=("Segoe UI", 10),
    )

    style.configure(
        "Muted.TLabel",
        foreground=COLORS["muted"],
    )

    # ---------- Buttons ----------
    style.configure(
        "TButton",
        padding=(12, 6),
        font=("Segoe UI", 10),
        background=COLORS["accent"],
    )

    style.map(
        "TButton",
        background=[
            ("active", COLORS["accent_hover"]),
            ("disabled", COLORS["disabled_bg"]),
        ],
        foreground=[
            ("disabled", COLORS["disabled_text"]),
        ],
    )
    
    # Accent Button (синяя)
    style.configure(
        "Accent.TButton",
        padding=(12, 6),
        font=("Segoe UI", 10, "bold"),
        background=COLORS["accent"],
        foreground="white",
    )
    
    style.map(
        "Accent.TButton",
        background=[
            ("active", COLORS["accent_hover"]),
            ("disabled", COLORS["disabled_bg"]),
        ],
    )
    
    # Success Button (зелёная)
    style.configure(
        "Success.TButton",
        padding=(12, 6),
        font=("Segoe UI", 10, "bold"),
        background=COLORS["positive"],
        foreground="white",
    )
    
    style.map(
        "Success.TButton",
        background=[
            ("active", COLORS["positive_hover"]),
            ("disabled", COLORS["disabled_bg"]),
        ],
    )
    
    # Warning Button (оранжевая)
    style.configure(
        "Warning.TButton",
        padding=(12, 6),
        font=("Segoe UI", 10, "bold"),
        background=COLORS["warning"],
        foreground="white",
    )
    
    style.map(
        "Warning.TButton",
        background=[
            ("active", COLORS["warning_hover"]),
            ("disabled", COLORS["disabled_bg"]),
        ],
    )
    
    # Danger Button (красная)
    style.configure(
        "Danger.TButton",
        padding=(12, 6),
        font=("Segoe UI", 10, "bold"),
        background=COLORS["negative"],
        foreground="white",
    )
    
    style.map(
        "Danger.TButton",
        background=[
            ("active", COLORS["negative_hover"]),
            ("disabled", COLORS["disabled_bg"]),
        ],
    )
    
    # Neutral Button (серая)
    style.configure(
        "Neutral.TButton",
        padding=(12, 6),
        font=("Segoe UI", 10),
        background=COLORS["neutral"],
        foreground="white",
    )
    
    style.map(
        "Neutral.TButton",
        background=[
            ("active", COLORS["neutral_hover"]),
            ("disabled", COLORS["disabled_bg"]),
        ],
    )

    # ---------- Treeview ----------
    style.configure(
        "Treeview",
        font=("Segoe UI", 10),
        rowheight=30,
        background=COLORS["card"],
        fieldbackground=COLORS["card"],
        bordercolor=COLORS["border"],
        relief="flat",
    )

    style.map(
        "Treeview",
        background=[
            ("selected", COLORS["accent"]),
        ],
        foreground=[
            ("selected", "white"),
        ],
    )

    style.configure(
        "Treeview.Heading",
        font=("Segoe UI", 10, "bold"),
        background=COLORS["bg"],
    )

    # ---------- Disabled Entry ----------
    style.configure(
        "TEntry",
        padding=6,
    )

    style.map(
        "TEntry",
        fieldbackground=[
            ("disabled", COLORS["disabled_bg"]),
        ],
        foreground=[
            ("disabled", COLORS["disabled_text"]),
        ],
    )
