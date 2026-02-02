from datetime import datetime, timedelta
from typing import List, Optional

from core.models import PayrollRow, PayrollSummary, Employee

FIXED_RATE = 8.0


# ======================================================
# DATE HELPERS
# ======================================================
def generate_days(start_iso: str, end_iso: str):
    """
    Генератор дат между start и end (ISO format)
    """
    d = datetime.strptime(start_iso, "%Y-%m-%d")
    e = datetime.strptime(end_iso, "%Y-%m-%d")
    while d <= e:
        yield d
        d += timedelta(days=1)


def iso_to_ui(date_iso: str) -> str:
    return datetime.strptime(date_iso, "%Y-%m-%d").strftime("%d-%m-%Y")


# ======================================================
# PAYROLL BUILDERS
# ======================================================
def build_payroll_rows(
    employee: Employee,
    hours_map: dict,
    start_iso: str,
    end_iso: str,
    rate: float,
) -> List[PayrollRow]:
    """
    Формирует список PayrollRow по диапазону дат

    hours_map:
        {
            "2026-01-01": 8,
            "2026-01-02": 6.5
        }
    """
    rows: List[PayrollRow] = []

    for d in generate_days(start_iso, end_iso):
        iso = d.strftime("%Y-%m-%d")
        ui = iso_to_ui(iso)
        weekday = d.strftime("%A")
        hours = float(hours_map.get(iso, 0))

        rows.append(
            PayrollRow(
                date_iso=iso,
                date_ui=ui,
                weekday=weekday,
                hours=hours,
                rate=rate,
            )
        )

    return rows


# ======================================================
# FIXED REPORT (8 €/hour)
# ======================================================
def calculate_fixed_payroll(
    employee: Employee,
    hours_map: dict,
    start_iso: str,
    end_iso: str,
) -> tuple[list[PayrollRow], PayrollSummary]:
    """
    Фиксированный отчёт: всегда 8 €/час, без вычетов
    """
    rows = build_payroll_rows(
        employee=employee,
        hours_map=hours_map,
        start_iso=start_iso,
        end_iso=end_iso,
        rate=FIXED_RATE,
    )

    total_hours = sum(r.hours for r in rows)
    gross = round(total_hours * FIXED_RATE, 2)

    summary = PayrollSummary(
        total_hours=total_hours,
        rate=FIXED_RATE,
        gross_amount=gross,
    )

    return rows, summary


# ======================================================
# CUSTOM REPORT (rate + optional deductions)
# ======================================================
def calculate_custom_payroll(
    employee: Employee,
    hours_map: dict,
    start_iso: str,
    end_iso: str,
    rate: float,
    housing_deduction: Optional[float] = 0.0,
    utilities_deduction: Optional[float] = 0.0,
) -> tuple[list[PayrollRow], PayrollSummary]:
    """
    Кастомный отчёт:
    - задаваемый тариф
    - опциональные вычеты
    """
    rows = build_payroll_rows(
        employee=employee,
        hours_map=hours_map,
        start_iso=start_iso,
        end_iso=end_iso,
        rate=rate,
    )

    total_hours = sum(r.hours for r in rows)
    gross = round(total_hours * rate, 2)

    summary = PayrollSummary(
        total_hours=total_hours,
        rate=rate,
        gross_amount=gross,
        housing_deduction=housing_deduction or 0.0,
        utilities_deduction=utilities_deduction or 0.0,
    )

    return rows, summary
