"""Informational checks; valid zero utilities never block output."""
from decimal import Decimal
from core.banking import account_state
from core.models import Employee
from core.rental import rental_for_rate,utilities_for_rate
from services.payroll_service import calculate_payroll


def payroll_checks(employee,values,utilities,modes=('fixed','custom')):
    notices=[]
    if account_state(employee)=='unknown':
        notices.append('Bank account is not specified; rental and utilities will not be deducted.')
    if sum(Decimal(str(v)) for v in values.values())==0:
        notices.append('Total hours are zero. Check the selected period.')
    for mode in modes:
        _,summary=calculate_payroll(Employee.from_row(employee),values,mode,
            housing=rental_for_rate(employee,mode),utilities=utilities_for_rate(employee,mode,utilities))
        if summary.net_amount<0:
            notices.append(('Fixed rate' if mode=='fixed' else 'Employee rate')+' has negative net pay. Check hours and deductions.')
    return notices
