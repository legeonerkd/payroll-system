from datetime import datetime
from typing import Dict
from config import FIXED_RATE


from core.models import Employee, PayrollRow, PayrollSummary


# ==================================================
# HELPERS
# ==================================================
def _weekday_name(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")


def _date_ui(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")


# ==================================================
# ROW BUILDER
# ==================================================
def build_payroll_rows(
    hours_map: Dict[str, float],
    rate: float,
):
    rows: list[PayrollRow] = []

    for date in sorted(hours_map.keys()):
        hours = hours_map[date]
        amount = round(hours * rate, 2)

        rows.append(
            PayrollRow(
                date=date,
                date_ui=_date_ui(date),
                weekday=_weekday_name(date),
                hours=hours,
                rate=rate,
                amount=amount,
            )
        )

    return rows


# ==================================================
# FIXED RATE (8 €/h) — ❌ NO DEDUCTIONS
# ==================================================
def calculate_fixed_payroll(
    employee: Employee,
    hours_map: Dict[str, float],
    _start=None,
    _end=None,
    *,
    housing: float = 0.0,
    utilities: float = 0.0,
):
    rate = FIXED_RATE
    rows = build_payroll_rows(hours_map, rate)

    total_hours = sum(r.hours for r in rows)
    gross = round(sum(r.amount for r in rows), 2)

    summary = PayrollSummary(
        total_hours=total_hours,
        gross_amount=gross,
        housing_deduction=0.0,
        utilities_deduction=0.0,
        net_amount=gross,
    )

    return rows, summary


# ==================================================
# CUSTOM RATE (EMPLOYEE) — ✅ DEDUCTIONS APPLY
# ==================================================
def calculate_custom_payroll(
    employee: Employee,
    hours_map: Dict[str, float],
    _start=None,
    _end=None,
    *,
    housing: float = 0.0,
    utilities: float = 0.0,
):
    rate = employee.rate
    rows = build_payroll_rows(hours_map, rate)

    total_hours = sum(r.hours for r in rows)
    gross = round(sum(r.amount for r in rows), 2)

    housing = round(housing, 2)
    utilities = round(utilities, 2)
    net = round(gross - housing - utilities, 2)

    summary = PayrollSummary(
        total_hours=total_hours,
        gross_amount=gross,
        housing_deduction=housing,
        utilities_deduction=utilities,
        net_amount=net,
    )

    return rows, summary
