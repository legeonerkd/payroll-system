from tkinter import ttk

COLORS = {
    # Backgrounds
    "bg": "#F4F6F8",
    "card": "#FFFFFF",
    "border": "#DADDE1",

    # Text
    "text": "#212529",
    "text_secondary": "#6C757D",
    "muted": "#6C757D",

    # Accents
    "accent": "#2C7BE5",
    "accent_hover": "#1C6ED5",
    "positive": "#2FB344",
    "negative": "#E03131",
    "warning": "#F08C00",

    # Disabled
    "disabled_bg": "#E9ECEF",
    "disabled_text": "#ADB5BD",
}


def setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("default")

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
            ("active", "#28A03C"),
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
            ("active", "#D67D00"),
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
            ("active", "#C82828"),
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
