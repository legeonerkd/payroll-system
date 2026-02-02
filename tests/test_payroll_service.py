from core.models import Employee
from services.payroll_service import (
    calculate_fixed_payroll,
    calculate_custom_payroll
)

# --------------------------------------------------
# FIXTURES
# --------------------------------------------------
def get_employee():
    return Employee(
        id=1,
        name="John Doe",
        rate=15.0
    )


# --------------------------------------------------
# FIXED REPORT TESTS
# --------------------------------------------------
def test_fixed_payroll_single_day():
    employee = get_employee()

    rows, summary = calculate_fixed_payroll(
        employee=employee,
        hours_map={"2026-01-01": 8},
        start_iso="2026-01-01",
        end_iso="2026-01-01"
    )

    assert summary.total_hours == 8
    assert summary.rate == 8.0
    assert summary.gross_amount == 64.0
    assert summary.net_amount == 64.0
    assert len(rows) == 1
    assert rows[0].amount == 64.0


def test_fixed_payroll_multiple_days():
    employee = get_employee()

    rows, summary = calculate_fixed_payroll(
        employee=employee,
        hours_map={
            "2026-01-01": 8,
            "2026-01-02": 6
        },
        start_iso="2026-01-01",
        end_iso="2026-01-02"
    )

    assert summary.total_hours == 14
    assert summary.gross_amount == 112.0


# --------------------------------------------------
# CUSTOM REPORT TESTS
# --------------------------------------------------
def test_custom_payroll_without_deductions():
    employee = get_employee()

    rows, summary = calculate_custom_payroll(
        employee=employee,
        hours_map={"2026-01-01": 10},
        start_iso="2026-01-01",
        end_iso="2026-01-01",
        rate=12.0
    )

    assert summary.total_hours == 10
    assert summary.gross_amount == 120.0
    assert summary.net_amount == 120.0


def test_custom_payroll_with_deductions():
    employee = get_employee()

    rows, summary = calculate_custom_payroll(
        employee=employee,
        hours_map={"2026-01-01": 10},
        start_iso="2026-01-01",
        end_iso="2026-01-01",
        rate=12.0,
        housing_deduction=20,
        utilities_deduction=10
    )

    assert summary.gross_amount == 120.0
    assert summary.total_deductions == 30.0
    assert summary.net_amount == 90.0


# --------------------------------------------------
# EDGE CASES
# --------------------------------------------------
def test_zero_hours():
    employee = get_employee()

    rows, summary = calculate_custom_payroll(
        employee=employee,
        hours_map={},
        start_iso="2026-01-01",
        end_iso="2026-01-01",
        rate=10.0
    )

    assert summary.total_hours == 0
    assert summary.gross_amount == 0
    assert summary.net_amount == 0
