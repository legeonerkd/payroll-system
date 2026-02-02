import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import sqlite3
from datetime import datetime, timedelta
from fpdf import FPDF
from pathlib import Path
import json
import os

# ======================================================
# APP INFO
# ======================================================
APP_NAME = "Payroll System"
APP_VERSION = "1.3.1"

# ======================================================
# FILE SYSTEM
# ======================================================
APP_DIR = os.path.join(os.path.expanduser("~"), "Documents", "PayrollSystem")
PAYROLL_DIR = os.path.join(APP_DIR, "Payroll")
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

os.makedirs(PAYROLL_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

DB_PATH = os.path.join(APP_DIR, "salary.db")
DEFAULT_TEMPLATE = "report_excel_like.json"

# ======================================================
# DATABASE
# ======================================================
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    rate REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS daily_hours (
    employee_id INTEGER,
    work_date TEXT,
    hours REAL,
    PRIMARY KEY (employee_id, work_date)
)
""")

conn.commit()

# ======================================================
# UTILS
# ======================================================
def ui_to_iso(d):
    return datetime.strptime(d, "%d-%m-%Y").strftime("%Y-%m-%d")

def iso_to_ui(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%d-%m-%Y")

def generate_days(start, end):
    d = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    while d <= e:
        yield d.strftime("%Y-%m-%d"), d.strftime("%A")
        d += timedelta(days=1)

def pdf_safe(text):
    return str(text).replace("—", "-").replace("€", "EUR")

def open_file(path):
    if os.name == "nt":
        os.startfile(path)

# ======================================================
# TEMPLATE LOADING
# ======================================================
def list_templates():
    return [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".json")]

def load_template(name):
    path = os.path.join(TEMPLATES_DIR, name)
    if not os.path.exists(path):
        messagebox.showerror("Template error", f"Template not found:\n{path}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ======================================================
# PDF RENDERING
# ======================================================
def render_header(pdf, header, data):
    for item in header:
        text = item.get("text", "")
        for k, v in data.items():
            text = text.replace(f"{{{k}}}", str(v))
        pdf.set_font("Helvetica", "B" if item.get("bold") else "", item.get("size", 10))
        pdf.cell(0, 7, pdf_safe(text), ln=True)
    pdf.ln(3)

def render_table(pdf, table, rows):
    pdf.set_font("Helvetica", "B", 9)
    for col in table["columns"]:
        pdf.cell(col["width"], 7, col["title"], border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for row in rows:
        for col in table["columns"]:
            pdf.cell(col["width"], 7, pdf_safe(row.get(col["key"], "")), border=1)
        pdf.ln()
    pdf.ln(3)

def render_summary(pdf, summary, data):
    pdf.set_font("Helvetica", "", 10)
    for item in summary:
        value = item["value"]
        for k, v in data.items():
            value = value.replace(f"{{{k}}}", str(v))
        pdf.cell(60, 7, f"{item['label']}:", 0)
        pdf.cell(40, 7, pdf_safe(value), ln=True)
    pdf.ln(5)

def render_signatures(pdf, signatures):
    pdf.ln(10)
    for s in signatures:
        pdf.cell(80, 7, f"{s['label']}:", 0)
        pdf.cell(40, 7, "__________________", ln=True)

# ======================================================
# GUI
# ======================================================
root = tk.Tk()
root.title(f"{APP_NAME} v{APP_VERSION}")
root.geometry("1100x700")

tabs = ttk.Notebook(root)
tab_emp = ttk.Frame(tabs)
tab_pay = ttk.Frame(tabs)

tabs.add(tab_emp, text="Employees")
tabs.add(tab_pay, text="Payroll")
tabs.pack(fill="both", expand=True)

# ======================================================
# EMPLOYEES TAB
# ======================================================
emp_tree = ttk.Treeview(tab_emp, columns=("name", "rate"), show="headings")
emp_tree.heading("name", text="Name")
emp_tree.heading("rate", text="Rate")
emp_tree.pack(fill="both", expand=True, pady=10)

form = ttk.Frame(tab_emp)
form.pack(pady=5)

name_entry = ttk.Entry(form, width=25)
rate_entry = ttk.Entry(form, width=10)

ttk.Label(form, text="Name").grid(row=0, column=0)
ttk.Label(form, text="Rate").grid(row=0, column=1)

name_entry.grid(row=1, column=0, padx=5)
rate_entry.grid(row=1, column=1, padx=5)

def load_employees():
    emp_tree.delete(*emp_tree.get_children())
    rows = cur.execute("SELECT name, rate FROM employees ORDER BY name").fetchall()
    for r in rows:
        emp_tree.insert("", "end", values=r)

    employee_combo["values"] = [r[0] for r in rows]
    if rows:
        employee_combo.current(0)

def add_employee():
    try:
        cur.execute(
            "INSERT INTO employees (name, rate) VALUES (?, ?)",
            (name_entry.get(), float(rate_entry.get()))
        )
        conn.commit()
        load_employees()
        name_entry.delete(0, tk.END)
        rate_entry.delete(0, tk.END)
    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Employee already exists")

def remove_employee():
    sel = emp_tree.selection()
    if not sel:
        return
    name = emp_tree.item(sel[0])["values"][0]
    cur.execute("DELETE FROM employees WHERE name=?", (name,))
    conn.commit()
    load_employees()

ttk.Button(form, text="Add", command=add_employee).grid(row=2, column=0, pady=5)
ttk.Button(form, text="Remove", command=remove_employee).grid(row=2, column=1, pady=5)

# ======================================================
# PAYROLL TAB
# ======================================================
employee_var = tk.StringVar()
template_var = tk.StringVar()

ttk.Label(tab_pay, text="Employee").pack()
employee_combo = ttk.Combobox(tab_pay, textvariable=employee_var, state="readonly")
employee_combo.pack()

ttk.Label(tab_pay, text="Template").pack(pady=(10, 0))
template_combo = ttk.Combobox(tab_pay, textvariable=template_var, state="readonly")
template_combo.pack()

start_entry = DateEntry(tab_pay, date_pattern="dd-mm-yyyy")
end_entry = DateEntry(tab_pay, date_pattern="dd-mm-yyyy")
start_entry.pack(pady=2)
end_entry.pack(pady=2)

daily = ttk.Treeview(tab_pay, columns=("date", "hours"), show="headings")
daily.heading("date", text="Date")
daily.heading("hours", text="Hours")
daily.pack(fill="x", pady=10)

def generate_period():
    daily.delete(*daily.get_children())
    for d, _ in generate_days(ui_to_iso(start_entry.get()), ui_to_iso(end_entry.get())):
        daily.insert("", "end", values=(iso_to_ui(d), 0))

def generate_pdf(preview=True):
    template = load_template(template_var.get())
    if not template:
        return

    row = cur.execute(
        "SELECT id, rate FROM employees WHERE name=?",
        (employee_var.get(),)
    ).fetchone()
    if not row:
        messagebox.showerror("Error", "Select employee")
        return

    emp_id, rate = row

    rows = []
    total_hours = 0
    total_amount = 0

    for r in daily.get_children():
        date_ui, h = daily.item(r)["values"]
        h = float(h)
        rows.append({
            "day": datetime.strptime(date_ui, "%d-%m-%Y").strftime("%A"),
            "date": date_ui,
            "regular": h,
            "overtime": "",
            "sick": "",
            "vacation": "",
            "total": h
        })
        total_hours += h
        total_amount += h * rate

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    data = {
        "employee": employee_var.get(),
        "project": "SunRock Residences",
        "period_start": start_entry.get(),
        "period_end": end_entry.get(),
        "total_hours": total_hours,
        "rate": rate,
        "total_amount": total_amount
    }

    render_header(pdf, template["header"], data)
    render_table(pdf, template["table"], rows)
    render_summary(pdf, template["summary"], data)
    render_signatures(pdf, template["signatures"])

    path = Path(PAYROLL_DIR) / ("preview.pdf" if preview else f"{employee_var.get()}_report.pdf")
    pdf.output(str(path))
    open_file(path)

ttk.Button(tab_pay, text="Generate period", command=generate_period).pack()
ttk.Button(tab_pay, text="Preview PDF", command=lambda: generate_pdf(True)).pack(pady=5)
ttk.Button(tab_pay, text="Generate PDF", command=lambda: generate_pdf(False)).pack()

# ======================================================
# INIT
# ======================================================
load_employees()
template_combo["values"] = list_templates()
if DEFAULT_TEMPLATE in template_combo["values"]:
    template_combo.set(DEFAULT_TEMPLATE)

root.mainloop()
