from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from config import FIXED_RATE
from core.models import PayrollRow, PayrollSummary
from core.validation import CENT, hours_map as validate_hours, number


def build_payroll_rows(hours_map, rate):
    rate = number(rate, 'Hourly rate', minimum=Decimal('0.01'))
    rows = []
    for day, hours in sorted(validate_hours(hours_map).items()):
        d = datetime.strptime(day, '%Y-%m-%d')
        amount = (Decimal(str(hours)) * rate).quantize(CENT, rounding=ROUND_HALF_UP)
        rows.append(PayrollRow(day, d.strftime('%d.%m.%Y'), d.strftime('%A'), hours, float(rate), float(amount)))
    return rows


def calculate_payroll(employee, hours_map, rate_mode='custom', *, housing=0, utilities=0):
    if rate_mode not in ('fixed', 'custom'):
        raise ValueError('Unknown rate mode')
    rows = build_payroll_rows(hours_map, FIXED_RATE if rate_mode == 'fixed' else employee.rate)
    gross = sum((Decimal(str(r.amount)) for r in rows), Decimal(0))
    housing = number(housing, 'Rental deduction').quantize(CENT, rounding=ROUND_HALF_UP)
    utilities = number(utilities, 'Utilities deduction').quantize(CENT, rounding=ROUND_HALF_UP)
    total_hours = sum((Decimal(str(r.hours)) for r in rows), Decimal(0))
    return rows, PayrollSummary(float(total_hours), float(gross), float(housing), float(utilities), float(gross - housing - utilities))


def calculate_fixed_payroll(employee, hours_map, _start=None, _end=None, *, housing=0, utilities=0):
    return calculate_payroll(employee, hours_map, 'fixed', housing=housing, utilities=utilities)


def calculate_custom_payroll(employee, hours_map, _start=None, _end=None, *, housing=0, utilities=0):
    return calculate_payroll(employee, hours_map, 'custom', housing=housing, utilities=utilities)
