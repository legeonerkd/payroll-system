from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import datetime
import tempfile, os, sys, subprocess

FIXED_RATE = 8.0


def preview_payroll_pdf(
    employee_name,
    employee_rate,
    rows,
    rate_mode,
    utilities,
    rental,
    period_from,
    period_to,
    templates_dir=None,
):
    file_path = os.path.join(
        tempfile.gettempdir(),
        f"Payroll_{employee_name}.pdf"
    )

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    # ---------- HEADER ----------
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, "Payroll Report")
    y -= 10 * mm

    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y, f"Employee: {employee_name}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Period: {period_from} — {period_to}")
    y -= 8 * mm

    # ---------- TABLE ----------
    data = [["Date", "Day", "Hours"]]
    total_hours = 0.0

    for d, day, h in rows:
        h = float(h)
        total_hours += h
        data.append([d, day, f"{h:.1f}"])

    table = Table(data, colWidths=[55 * mm, 65 * mm, 25 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, 20 * mm, y - table._height)
    y -= table._height + 8 * mm

    # ---------- CALC ----------
    rate = FIXED_RATE if rate_mode == "fixed" else float(employee_rate)
    gross = total_hours * rate
    util = float(utilities) if utilities else 0.0
    rent = float(rental) if rental else 0.0
    net = gross - util - rent

    # ---------- SUMMARY ----------
    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, "Summary")
    y -= 6 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Total hours: {total_hours:.1f}")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Rate: {rate:.2f} €/h")
    y -= 5 * mm
    c.drawString(20 * mm, y, f"Gross: {gross:.2f} €")
    y -= 5 * mm

    if util:
        c.drawString(20 * mm, y, f"Utilities: -{util:.2f} €")
        y -= 5 * mm
    if rent:
        c.drawString(20 * mm, y, f"Rental: -{rent:.2f} €")
        y -= 5 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, f"Net total: {net:.2f} €")

    # ---------- FOOTER ----------
    c.setFont("Helvetica", 8)
    c.drawRightString(
        width - 20 * mm,
        15 * mm,
        f"Generated {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    )

    c.save()
    _open(file_path)


def _open(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform.startswith("darwin"):
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])

