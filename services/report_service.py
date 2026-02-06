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


# ======================================================
# PUBLIC API — FROM PAYROLL TAB
# ======================================================

def preview_payroll_pdf(
    employee_name: str,
    employee_rate: float,
    rows: list,
    rate_mode: str,
    utilities: str | None,
    rental: str | None,
    period_from: str,
    period_to: str,
    bank_name: str | None,
    iban: str | None,
    bic: str | None,
):
    rate = FIXED_RATE if rate_mode == "fixed" else float(employee_rate)

    parsed_rows = []
    gross = 0.0

    for date, day, hours in rows:
        h = float(hours) if hours else 0.0
        amount = h * rate
        gross += amount

        parsed_rows.append((
            date,
            day,
            f"{h:.1f}",
            f"{rate:.2f} €",
            f"{amount:.2f} €"
        ))

    _render_pdf(
        employee_name=employee_name,
        period_from=period_from,
        period_to=period_to,
        created_at=datetime.now().strftime("%d-%m-%Y"),
        bank=bank_name,
        iban=iban,
        bic=bic,
        rows=parsed_rows,
        gross=gross,
        utilities=float(utilities) if utilities else None,
        rental=float(rental) if rental else None,
    )


# ======================================================
# PUBLIC API — FROM HISTORY
# ======================================================

def preview_payroll_pdf_from_history(payroll, days):
    rate = payroll["rate"]

    parsed_rows = []
    gross = 0.0

    for d in days:
        h = d["hours"]
        amount = h * rate
        gross += amount

        day_name = datetime.strptime(d["work_date"], "%d-%m-%Y").strftime("%A")

        parsed_rows.append((
            d["work_date"],
            day_name,
            f"{h:.1f}",
            f"{rate:.2f} €",
            f"{amount:.2f} €"
        ))

    _render_pdf(
        employee_name=payroll["name"],
        period_from=payroll["period_from"],
        period_to=payroll["period_to"],
        created_at=payroll["created_at"],
        bank=payroll["bank"],
        iban=payroll["iban"],
        bic=payroll["bic"],
        rows=parsed_rows,
        gross=gross,
        utilities=payroll["utilities"],
        rental=payroll["rental"],
    )


# ======================================================
# CORE PDF RENDER (FINAL)
# ======================================================

def _render_pdf(
    employee_name,
    period_from,
    period_to,
    created_at,
    bank,
    iban,
    bic,
    rows,
    gross,
    utilities,
    rental
):
    path = os.path.join(
        tempfile.gettempdir(),
        f"Payroll_{employee_name}.pdf"
    )

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    # ---------- HEADER ----------
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, y, "Blue Reef Development LTD")
    y -= 10 * mm

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, "PAYROLL STATEMENT")
    y -= 14 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Employee: {employee_name}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Period: {period_from} – {period_to}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"Generated on: {created_at}")
    y -= 8 * mm

    # ---------- BANK ----------
    if bank or iban or bic:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(20 * mm, y, "Bank details:")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        if bank:
            c.drawString(20 * mm, y, f"Bank: {bank}")
            y -= 6 * mm
        if iban:
            c.drawString(20 * mm, y, f"IBAN: {iban}")
            y -= 6 * mm
        if bic:
            c.drawString(20 * mm, y, f"BIC: {bic}")
            y -= 6 * mm
        y -= 6 * mm

    # ---------- TABLE ----------
    table_data = [["Date", "Day", "Hours", "Hourly rate", "Amount"]] + list(rows)

    table = Table(
        table_data,
        colWidths=[30 * mm, 36 * mm, 20 * mm, 34 * mm, 26 * mm]
    )

    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),

        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),

        # Body
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])

    # Highlight Sundays
    for idx, row in enumerate(rows, start=1):
        if row[1].lower().startswith("sun"):
            style.add(
                "BACKGROUND",
                (0, idx),
                (-1, idx),
                colors.lavenderblush
            )

    table.setStyle(style)
    table.wrapOn(c, width, height)
    table.drawOn(c, 20 * mm, y - table._height)
    y -= table._height + 12 * mm

    # ---------- TOTALS ----------
    net = gross - (utilities or 0) - (rental or 0)

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"Gross amount: {gross:.2f} €")
    y -= 6 * mm

    if utilities:
        c.drawString(20 * mm, y, f"Utilities deduction: -{utilities:.2f} €")
        y -= 6 * mm
    if rental:
        c.drawString(20 * mm, y, f"Rental deduction: -{rental:.2f} €")
        y -= 6 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(20 * mm, y, f"Net amount: {net:.2f} €")
    y -= 14 * mm

    # ---------- SIGNATURES ----------
    c.setFont("Helvetica", 10)

    c.drawString(20 * mm, y, "Employee signature:")
    c.drawString(120 * mm, y, "Manager signature:")
    y -= 12 * mm

    c.line(20 * mm, y, 90 * mm, y)
    c.line(120 * mm, y, 190 * mm, y)
    y -= 8 * mm

    c.drawString(20 * mm, y, f"Date: {created_at}")
    c.drawString(120 * mm, y, f"Date: {created_at}")

    c.save()
    _open_file(path)


# ======================================================
# OPEN FILE
# ======================================================

def _open_file(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform.startswith("darwin"):
        subprocess.call(["open", path])
    else:
        subprocess.call(["xdg-open", path])

