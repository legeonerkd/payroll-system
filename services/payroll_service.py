from datetime import datetime
from core.models import PayrollRow, PayrollSummary


# ==================================================
# HELPERS
# ==================================================
def _weekday_name(date_obj: datetime) -> str:
    return date_obj.strftime("%A")


# ==================================================
# BUILD ROWS
# ==================================================
def build_payroll_rows(
    hours_map: dict[str, float],
    rate: float,
):
    rows: list[PayrollRow] = []

    for date_iso, hours in sorted(hours_map.items()):
        date_obj = datetime.strptime(date_iso, "%Y-%m-%d")
        amount = round(hours * rate, 2)

        rows.append(
            PayrollRow(
                date_iso=date_iso,
                date_ui=date_obj.strftime("%d.%m.%Y"),
                weekday=_weekday_name(date_obj),
                hours=hours,
                rate=rate,
                amount=amount,
            )
        )

    return rows


# ==================================================
# FIXED RATE PAYROLL (8 EUR/H)
# UI EXPECTS: (employee, hours_map, start, end)
# ==================================================
def calculate_fixed_payroll(
    employee,
    hours_map: dict[str, float],
    period_start=None,
    period_end=None,
):
    rate = 8.0

    rows = build_payroll_rows(hours_map, rate)

    total_hours = sum(r.hours for r in rows)
    gross_amount = round(sum(r.amount for r in rows), 2)

    summary = PayrollSummary(
        total_hours=total_hours,
        gross_amount=gross_amount,
        total_deductions=0.0,
        net_amount=gross_amount,
    )

    return rows, summary


# ==================================================
# CUSTOM RATE PAYROLL
# UI EXPECTS: (employee, hours_map, start, end)
# ==================================================
def calculate_custom_payroll(
    employee,
    hours_map: dict[str, float],
    period_start=None,
    period_end=None,
):
    rate = employee.rate

    rows = build_payroll_rows(hours_map, rate)

    total_hours = sum(r.hours for r in rows)
    gross_amount = round(sum(r.amount for r in rows), 2)

    summary = PayrollSummary(
        total_hours=total_hours,
        gross_amount=gross_amount,
        total_deductions=0.0,
        net_amount=gross_amount,
    )

    return rows, summary

