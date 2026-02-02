from fpdf import FPDF
from pathlib import Path


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

    # ===== REGISTER UNICODE FONT (BEFORE add_page) =====
    font_path = Path(__file__).resolve().parents[1] / "fonts" / "DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", str(font_path), uni=True)

    pdf.add_page()
    pdf.set_font("DejaVu", size=11)

    # ===== HEADER =====
    pdf.set_font("DejaVu", size=14)
    pdf.cell(0, 10, "Payroll Report", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("DejaVu", size=11)
    pdf.cell(0, 8, f"Employee: {employee.name}", ln=True)
    pdf.cell(0, 8, f"Period: {period_start_ui} - {period_end_ui}", ln=True)
    pdf.ln(5)

    # ===== TABLE HEADER =====
    pdf.set_font("DejaVu", size=10)
    pdf.cell(40, 8, "Date", 1)
    pdf.cell(50, 8, "Day", 1)
    pdf.cell(30, 8, "Hours", 1)
    pdf.cell(30, 8, "Amount (€)", 1)
    pdf.ln()

    # ===== TABLE ROWS =====
    for r in rows:
        pdf.cell(40, 8, r.date_ui, 1)
        pdf.cell(50, 8, r.weekday, 1)
        pdf.cell(30, 8, f"{r.hours:.2f}", 1)
        pdf.cell(30, 8, f"{r.amount:.2f} €", 1)
        pdf.ln()

    pdf.ln(5)

    # ===== SUMMARY =====
    pdf.set_font("DejaVu", size=11)
    pdf.cell(0, 8, f"Total hours: {summary.total_hours}", ln=True)
    pdf.cell(0, 8, f"Gross amount: {summary.gross_amount:.2f} €", ln=True)

    if summary.total_deductions > 0:
        pdf.cell(0, 8, f"Deductions: {summary.total_deductions:.2f} €", ln=True)
        pdf.cell(0, 8, f"Net amount: {summary.net_amount:.2f} €", ln=True)

    # ===== SAVE =====
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))

