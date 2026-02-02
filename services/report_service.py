from pathlib import Path
from datetime import datetime
from fpdf import FPDF
import re


COMPANY_NAME = "Blue Reef Development LTD"


def _safe_filename(text: str) -> str:
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate_payroll_pdf(
    employee,
    rows,
    summary,
    template,
    period_start_ui,
    period_end_ui,
    output_path: Path,
):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    base_dir = Path(__file__).resolve().parents[1]

    # ---------- document date ----------
    document_date = datetime.now().strftime("%d.%m.%Y")

    # ---------- font (unicode) ----------
    font_path = base_dir / "fonts" / "DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", str(font_path), uni=True)

    pdf.add_page()
    pdf.set_font("DejaVu", size=11)

    # ---------- header ----------
    pdf.set_font("DejaVu", size=14)
    pdf.cell(0, 8, COMPANY_NAME, ln=True, align="C")

    pdf.set_font("DejaVu", size=16)
    pdf.cell(0, 10, "PAYROLL STATEMENT", ln=True, align="C")

    pdf.ln(5)
    pdf.set_font("DejaVu", size=11)

    pdf.cell(0, 7, f"Employee: {employee.name}", ln=True)
    pdf.cell(0, 7, f"Period: {period_start_ui} – {period_end_ui}", ln=True)
    pdf.cell(0, 7, f"Generated on: {document_date}", ln=True)

    # ---------- bank details ----------
    if employee.has_bank_account:
        pdf.ln(4)
        pdf.cell(0, 7, "Bank details:", ln=True)

        if employee.bank_name:
            pdf.cell(0, 6, f"Bank: {employee.bank_name}", ln=True)
        if employee.iban:
            pdf.cell(0, 6, f"IBAN: {employee.iban}", ln=True)
        if employee.bic:
            pdf.cell(0, 6, f"BIC: {employee.bic}", ln=True)

    pdf.ln(6)

    # ---------- table header ----------
    pdf.set_font("DejaVu", size=10)
    pdf.set_fill_color(220, 220, 220)

    pdf.cell(28, 8, "Date", 1, fill=True)
    pdf.cell(38, 8, "Day", 1, fill=True)
    pdf.cell(22, 8, "Hours", 1, align="R", fill=True)
    pdf.cell(30, 8, "Hourly rate (€)", 1, align="R", fill=True)
    pdf.cell(32, 8, "Amount (€)", 1, align="R", fill=True)
    pdf.ln()

    # ---------- table rows ----------
    pdf.set_font("DejaVu", size=10)

    for r in rows:
        # Sunday highlighting
        if r.weekday.lower() == "sunday":
            pdf.set_fill_color(255, 230, 230)  # light red
            fill = True
        else:
            pdf.set_fill_color(255, 255, 255)
            fill = True

        pdf.cell(28, 8, r.date_ui, 1, fill=fill)
        pdf.cell(38, 8, r.weekday, 1, fill=fill)
        pdf.cell(22, 8, f"{r.hours:.2f}", 1, align="R", fill=fill)
        pdf.cell(30, 8, f"{r.rate:.2f}", 1, align="R", fill=fill)
        pdf.cell(32, 8, f"{r.amount:.2f}", 1, align="R", fill=fill)
        pdf.ln()

    pdf.ln(6)

    # ---------- summary ----------
    pdf.set_font("DejaVu", size=11)
    pdf.cell(0, 7, f"Total hours: {summary.total_hours:.2f}", ln=True)
    pdf.cell(0, 7, f"Gross amount: {summary.gross_amount:.2f} €", ln=True)

    # ---------- signatures ----------
    pdf.ln(15)
    pdf.cell(90, 8, "Employee signature:", ln=0)
    pdf.cell(0, 8, "Authorized manager signature:", ln=True)

    pdf.ln(12)
    pdf.cell(90, 8, "______________________________", ln=0)
    pdf.cell(0, 8, "______________________________", ln=True)

    pdf.ln(6)
    pdf.cell(90, 7, f"Date: {document_date}", ln=0)
    pdf.cell(0, 7, f"Date: {document_date}", ln=True)

    # ---------- filename ----------
    rate_value = rows[0].rate if rows else employee.rate
    filename = _safe_filename(f"{employee.name}_{int(rate_value)} per hour.pdf")

    if output_path.is_dir():
        final_path = output_path / filename
    else:
        final_path = output_path.parent / filename

    final_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(final_path))

    return final_path
