from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

import tempfile
import os
import subprocess
import sys


FIXED_RATE = 8.0

PAGE_WIDTH, PAGE_HEIGHT = A4
TOP_MARGIN = 20 * mm
BOTTOM_MARGIN = 20 * mm
LEFT_MARGIN = 20 * mm
RIGHT_MARGIN = 20 * mm

MAX_TABLE_HEIGHT = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN - 90 * mm


def preview_payroll_pdf(
    employee_name: str,
    rows: list,
    rate_mode: str,
    utilities: str | None,
    rental: str | None,
    templates_dir=None,
):
    """
    rows = [
        ["26-01-2026", "Monday", "10.0"],
        ...
    ]
    """

    file_path = os.path.join(
        tempfile.gettempdir(),
        f"Payroll_{employee_name}.pdf"
    )

    c = canvas.Canvas(file_path, pagesize=A4)

    y = PAGE_HEIGHT - TOP_MARGIN

    # ================= HEADER =================
    c.setFont("Helvetica-Bold", 15)
    c.drawString(LEFT_MARGIN, y, "Payroll Report")
    y -= 12 * mm

    c.setFont("Helvetica", 11)
    c.drawString(LEFT_MARGIN, y, f"Employee: {employee_name}")
    y -= 10 * mm

    # ================= TABLE DATA =================
    table_data = [["Date", "Day", "Hours"]]

    total_hours = 0.0
    for date, day, hours in rows:
        h = float(hours) if hours else 0.0
        total_hours += h
        table_data.append([date, day, f"{h:.1f}"])

    # ================= AUTO FIT TABLE =================
    font_size = 10
    row_padding = 6

    while True:
        table = Table(
            table_data,
            colWidths=[
                55 * mm,
                65 * mm,
                25 * mm
            ]
        )

        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", font_size),
            ("FONT", (0, 1), (-1, -1), "Helvetica", font_size),
            ("ALIGN", (2, 1), (2, -1), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), row_padding),
            ("TOPPADDING", (0, 0), (-1, -1), row_padding),
        ]))

        table.wrapOn(c, PAGE_WIDTH, PAGE_HEIGHT)

        if table._height <= MAX_TABLE_HEIGHT or font_size <= 7:
            break

        font_size -= 0.5
        row_padding -= 1

    table.drawOn(c, LEFT_MARGIN, y - table._height)
    y -= table._height + 10 * mm

    # ================= CALCULATION =================
    if rate_mode == "fixed":
        rate = FIXED_RATE
        rate_label = "Fixed rate"
    else:
        rate = FIXED_RATE
        rate_label = "Custom rate"

    gross = total_hours * rate
    utilities_val = float(utilities) if utilities else 0.0
    rental_val = float(rental) if rental else 0.0
    net = gross - utilities_val - rental_val

    # ================= SUMMARY =================
    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT_MARGIN, y, "Summary")
    y -= 6 * mm

    c.setFont("Helvetica", 10)
    c.drawString(LEFT_MARGIN, y, f"Total hours: {total_hours:.1f}")
    y -= 5 * mm

    c.drawString(LEFT_MARGIN, y, f"Rate: {rate_label} ({rate:.2f} €/h)")
    y -= 5 * mm

    c.drawString(LEFT_MARGIN, y, f"Gross amount: {gross:.2f} €")
    y -= 5 * mm

    if utilities:
        c.drawString(LEFT_MARGIN, y, f"Utilities deduction: -{utilities_val:.2f} €")
        y -= 5 * mm

    if rental:
        c.drawString(LEFT_MARGIN, y, f"Rental deduction: -{rental_val:.2f} €")
        y -= 5 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT_MARGIN, y, f"Net total: {net:.2f} €")

    # ================= SAVE =================
    c.save()
    _open_file(file_path)


def _open_file(path: str):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform.startswith("darwin"):
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])
