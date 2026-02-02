from pathlib import Path
from typing import List
from fpdf import FPDF

from core.models import Employee, PayrollRow, PayrollSummary


# ======================================================
# UTILS
# ======================================================
def pdf_safe(text) -> str:
    return str(text).replace("—", "-").replace("€", "EUR")


# ======================================================
# RENDER HELPERS
# ======================================================
def render_header(pdf: FPDF, header: list, data: dict):
    for item in header:
        text = item.get("text", "")
        for k, v in data.items():
            text = text.replace(f"{{{k}}}", str(v))
        pdf.set_font(
            "Helvetica",
            "B" if item.get("bold") else "",
            item.get("size", 10)
        )
        pdf.cell(0, 7, pdf_safe(text), ln=True)
    pdf.ln(3)


def render_table(pdf: FPDF, table: dict, rows: List[PayrollRow]):
    pdf.set_font("Helvetica", "B", 9)
    for col in table["columns"]:
        pdf.cell(col["width"], 7, col["title"], border=1, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for r in rows:
        for col in table["columns"]:
            key = col["key"]
            value = getattr(r, key)
            pdf.cell(col["width"], 7, pdf_safe(value), border=1)
        pdf.ln()
    pdf.ln(3)


def render_summary(pdf: FPDF, summary: list, data: dict):
    pdf.set_font("Helvetica", "", 10)
    for item in summary:
        value = item["value"]
        for k, v in data.items():
            value = value.replace(f"{{{k}}}", str(v))
        pdf.cell(60, 7, f"{item['label']}:", 0)
        pdf.cell(40, 7, pdf_safe(value), ln=True)
    pdf.ln(5)


def render_signatures(pdf: FPDF, signatures: list):
    pdf.ln(10)
    for s in signatures:
        pdf.cell(80, 7, f"{s['label']}:", 0)
        pdf.cell(40, 7, "__________________", ln=True)


# ======================================================
# MAIN SERVICE
# ======================================================
def generate_payroll_pdf(
    employee: Employee,
    rows: List[PayrollRow],
    summary: PayrollSummary,
    template: dict,
    period_start_ui: str,
    period_end_ui: str,
    output_path: Path,
):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    data = {
        "employee": employee.name,
        "period_start": period_start_ui,
        "period_end": period_end_ui,
        "total_hours": summary.total_hours,
        "rate": summary.rate,
        "gross_amount": summary.gross_amount,
        "housing_deduction": summary.housing_deduction,
        "utilities_deduction": summary.utilities_deduction,
        "net_amount": summary.net_amount,
    }

    render_header(pdf, template["header"], data)
    render_table(pdf, template["table"], rows)
    render_summary(pdf, template["summary"], data)
    render_signatures(pdf, template["signatures"])

    pdf.output(str(output_path))
