
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
import tempfile
import os
import sys
import subprocess

FIXED_RATE = 8.0

PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT = 20 * mm
RIGHT = PAGE_WIDTH - 20 * mm
TOP = PAGE_HEIGHT - 20 * mm
BOTTOM = 20 * mm


def preview_payroll_pdf(
    employee_name: str,
    employee_rate: float,
    rows: list,
    rate_mode: str,
    utilities: str | None,
    rental: str | None,
    period_from: str,
    period_to: str,
    templates_dir=None,
):
    path = os.path.join(
        tempfile.gettempdir(),
        f"Payroll_{employee_name}.pdf"
    )

    c = canvas.Canvas(path, pagesize=A4)
    y = TOP

    # ================= HEADER =================
    c.setFont("Helvetica-Bold", 14)
    c.drawString(LEFT, y, "PAYROLL STATEMENT")
    y -= 10 * mm

    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, f"Employee: {employee_name}")
    y -= 5 * mm

    c.drawString(LEFT, y, f"Period: {period_from} – {period_to}")
    y -= 5 * mm

    rate = FIXED_RATE if rate_mode == "fixed" else float(employee_rate)
    c.drawString(LEFT, y, f"Hourly rate: {rate:.2f} €")
    y -= 8 * mm

    # ================= TABLE =================
    table_data = [["Date", "Day", "Hours"]]
    total_hours = 0.0

    for date, day, hours in rows:
        h = float(hours) if hours else 0.0
        total_hours += h
        table_data.append([date, day, f"{h:.1f}"])

    table = Table(
        table_data,
        colWidths=[40 * mm, 45 * mm, 20 * mm]
    )

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))

    table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)
    table.drawOn(c, LEFT, y - table._height)
    y -= table._height + 6 * mm

    # ================= CALCULATION =================
    gross = total_hours * rate
    utilities_val = float(utilities) if utilities else 0.0
    rental_val = float(rental) if rental else 0.0
    net = gross - utilities_val - rental_val

    # ================= SUMMARY =================
    c.setFont("Helvetica", 10)
    c.drawString(LEFT, y, f"Total hours: {total_hours:.1f}")
    y -= 5 * mm

    c.drawString(LEFT, y, f"Gross amount: {gross:.2f} €")
    y -= 5 * mm

    if utilities:
        c.drawString(LEFT, y, f"Utilities deduction: -{utilities_val:.2f} €")
        y -= 5 * mm

    if rental:
        c.drawString(LEFT, y, f"Rental deduction: -{rental_val:.2f} €")
        y -= 5 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT, y, f"Net amount: {net:.2f} €")
    y -= 10 * mm

    # ================= FOOTER =================
    c.setFont("Helvetica", 8)
    c.drawString(
        LEFT,
        BOTTOM - 5 * mm,
        f"Generated on {datetime.now().strftime('%d-%m-%Y')}"
    )

    c.save()
    _open_file(path)


def _open_file(path: str):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform.startswith("darwin"):
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])
