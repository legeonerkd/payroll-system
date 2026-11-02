"""Route recurring rental and entered utilities by declared bank-account status."""
from decimal import Decimal,ROUND_HALF_UP
from core.banking import account_state
from core.validation import number,CENT


def rental_amount(value):
    return number(value,'Saved rental deduction').quantize(CENT,rounding=ROUND_HALF_UP)


def deduction_mode(employee):
    return {'yes':'fixed','no':'custom'}.get(account_state(employee)) if employee is not None else None


def utilities_for_rate(employee,rate_mode,amount):
    if rate_mode not in ('fixed','custom'):raise ValueError('Unknown rate mode')
    amount=number(amount,'Utilities deduction').quantize(CENT,rounding=ROUND_HALF_UP)
    return amount if rate_mode==deduction_mode(employee) else Decimal(0)


def rental_for_rate(employee,rate_mode):
    if rate_mode not in ('fixed','custom'):raise ValueError('Unknown rate mode')
    if employee is None:return Decimal(0)
    employee=dict(employee)
    amount=rental_amount(employee.get('rental_amount',0))
    target=deduction_mode(employee)
    return amount if rate_mode==target else Decimal(0)


def rental_hint(employee,rate_mode):
    if employee is None:return 'Set rental in Employee Details.'
    amount=rental_amount(dict(employee).get('rental_amount',0))
    if not amount:return 'No saved rental deduction.'
    state=account_state(employee)
    if state=='unknown':return 'Set Bank account to Yes or No in Employee Details to apply rental.'
    target='Fixed rate' if state=='yes' else 'Employee rate'
    return f'Saved rental: {amount:.2f} €. Deducted in each {target} statement.'
