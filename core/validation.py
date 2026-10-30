"""Shared validation and deterministic monetary rounding."""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal('0.01')


def number(value, label, *, minimum=0, maximum=None):
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{label} must be a number') from None
    if not result.is_finite() or result < minimum:
        raise ValueError(f'{label} must be finite and at least {minimum}')
    if abs(result) > Decimal('1000000000000'):
        raise ValueError(f'{label} is too large')
    if maximum is not None and result > maximum:
        raise ValueError(f'{label} must not exceed {maximum}')
    return result


def money(value):
    return number(value, 'Amount').quantize(CENT, rounding=ROUND_HALF_UP)


def iso_date(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Date must use YYYY-MM-DD')
    return value


def hours_map(values):
    return {iso_date(day): float(number(hours, 'Hours', maximum=24)) for day, hours in values.items()}


def employee_values(name, rate):
    if not isinstance(name,str):
        raise ValueError('Employee name must be text')
    name = name.strip()
    if not name:
        raise ValueError('Employee name is required')
    return name, float(number(rate, 'Hourly rate', minimum=Decimal('0.01')))
