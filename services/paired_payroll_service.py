"""Save a fixed/custom pair atomically, keeping independently named PDF files."""
from pathlib import Path
from core.banking import payment_details
from core.rental import rental_for_rate,utilities_for_rate
from core.validation import hours_map,number
from database.db import PayrollConflictError
from services.report_service import generate_payroll_pdf,_print_file

MODES=('fixed','custom')


class PairPrintError(RuntimeError):
    def __init__(self,submitted,failed):
        self.submitted=tuple(submitted)
        self.failed=failed
        self.pending=tuple(mode for mode in MODES if mode not in submitted)
        super().__init__('Could not submit '+failed+' PDF to the print application')


def print_payroll_pair(files):
    """Submit both saved PDFs; do not retry already submitted jobs on failure."""
    for mode in MODES:
        if not Path(files[mode]).is_file():raise PairPrintError((),mode)
    submitted=[]
    for mode in MODES:
        try:_print_file(str(files[mode]))
        except Exception as exc:raise PairPrintError(submitted,mode) from exc
        submitted.append(mode)
    return tuple(submitted)


def pair_plans(db,employee,values,start,end,utilities):
    return {mode:db.payroll_save_plan(employee['id'],values,mode,start,end,
            utilities_for_rate(employee,mode,utilities),rental_for_rate(employee,mode)) for mode in MODES}


def save_payroll_pair(db,employee,values,start,end,utilities,*,plans,day_rules,settings):
    employee=dict(employee);values=hours_map(values)
    utilities=number(utilities,'Utilities deduction')
    files={}
    try:
        details=payment_details(employee)
        for mode in MODES:
            files[mode]=generate_payroll_pdf(employee_name=employee['name'],employee_rate=employee['rate'],
                rows=[(day,'',hours) for day,hours in sorted(values.items())],rate_mode=mode,
                utilities=str(utilities_for_rate(employee,mode,utilities)),rental=str(rental_for_rate(employee,mode)),
                period_from=start,period_to=end,bank_name=details['bank'],iban=details['iban'],bic=details['bic'],
                action='save',employee_id=employee['id'])
        with db.transaction():
            current=dict(db.get_employee(employee['id']))
            if current!=employee:raise PayrollConflictError('Employee details changed. Refresh the employee and try again.')
            actual=pair_plans(db,current,values,start,end,utilities)
            for mode in MODES:
                for kind in ('exact','overlaps'):
                    if {p['id'] for p in actual[mode][kind]}!={p['id'] for p in plans[mode][kind]}:
                        raise PayrollConflictError('Payroll history changed. Review both statements and try again.')
            ids={}
            for mode in MODES:
                replaces=[p['id'] for p in plans[mode]['exact']]
                ids[mode]=db.save_payroll(employee['id'],values,mode,start,end,
                    utilities=str(utilities_for_rate(current,mode,utilities)),rental=str(rental_for_rate(current,mode)),
                    pdf_path=files[mode],day_rules=day_rules,distribution_settings=settings,
                    replaces_ids=replaces,expected_current_ids=replaces,allow_overlap=bool(plans[mode]['overlaps']))
            db.register_payroll_pair(ids['fixed'],ids['custom'])
        return {'files':files,'ids':ids}
    except Exception:
        # The generator returns a unique new path for every call.
        for path in files.values():Path(path).unlink(missing_ok=True)
        raise
