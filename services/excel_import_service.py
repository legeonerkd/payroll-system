"""Strict XLSX parsing and all-or-nothing batch processing."""
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
import re
import pandas as pd

from core.validation import employee_values, number
from services.payroll_service import calculate_payroll
from core.models import Employee
from services.report_service import generate_payroll_pdf


class ExcelImportError(ValueError):
    pass


class EmployeeData:
    def __init__(self, name, rate, bank=None, iban=None, bic=None, employee_id=None):
        self.name, self.rate = employee_values(name, rate)
        self.bank, self.iban, self.bic = bank, iban, bic
        self.employee_id = employee_id
        self.hours_by_date = {}

    def add_hours(self, day, hours):
        self.hours_by_date[day] = float(number(hours, 'Hours', maximum=24))

    def get_total_hours(self):
        return float(sum((Decimal(str(h)) for h in self.hours_by_date.values()), Decimal(0)))

    def get_date_range(self):
        days = sorted(self.hours_by_date)
        return (days[0], days[-1]) if days else (None, None)


def parse_date_column(value):
    if isinstance(value, (datetime, date)):
        return value.strftime('%Y-%m-%d')
    text = str(value).strip()
    for fmt in ('%d-%m-%Y','%d/%m/%Y','%d.%m.%Y','%Y-%m-%d','%Y/%m/%d','%Y.%m.%d'):
        try:
            return datetime.strptime(text, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None


def _date_columns(df):
    result = {}
    seen = set()
    for col in df.columns[5:]:
        if str(col).strip().casefold() == 'employee id':
            continue
        day = parse_date_column(col)
        # pandas suffixes repeated headers with .1, .2, etc.
        if day is None and parse_date_column(re.sub(r'\.\d+$','',str(col))):
            raise ExcelImportError(f'Duplicate date column: {col}')
        if day is None:
            raise ExcelImportError(f'Unknown date column: {col}')
        if day in seen:
            raise ExcelImportError(f'Duplicate date: {day}')
        seen.add(day)
        result[col] = day
    return result


def validate_excel_structure(df):
    if df.empty or df.shape[1] < 6:
        return False, 'Expected Name, Rate, Bank, IBAN, BIC and at least one date column'
    first, second = (str(c).strip().casefold() for c in df.columns[:2])
    if not any(k in first for k in ('name','employee','имя','сотрудник')):
        return False, 'First column must be Employee Name'
    if not any(k in second for k in ('rate','hourly','ставка')):
        return False, 'Second column must be Hourly Rate'
    try:
        if not _date_columns(df):
            return False, 'No date columns found'
    except ExcelImportError as exc:
        return False, str(exc)
    return True, 'OK'


def import_excel_file(filepath):
    if Path(filepath).suffix.lower() != '.xlsx':
        raise ExcelImportError('Only .xlsx files are supported; save legacy .xls files as .xlsx first')
    try:
        df = pd.read_excel(filepath, engine='openpyxl', dtype=object)
        valid, reason = validate_excel_structure(df)
        if not valid:
            raise ExcelImportError(reason)
        columns = _date_columns(df)
        id_columns = [c for c in df.columns if str(c).strip().casefold()=='employee id']
        employees, identities = [], set()
        def optional(value):
            return None if pd.isna(value) or not str(value).strip() else str(value).strip()
        for idx, row in df.iterrows():
            if optional(row.iloc[0]) is None:
                continue
            try:
                employee_id = None
                if id_columns and optional(row[id_columns[0]]) is not None:
                    numeric_id = number(row[id_columns[0]],'Employee ID',minimum=1)
                    if numeric_id != numeric_id.to_integral_value():
                        raise ValueError('Employee ID must be an integer')
                    employee_id = int(numeric_id)
                employee = EmployeeData(row.iloc[0], row.iloc[1], *(optional(row.iloc[i]) for i in (2,3,4)),employee_id=employee_id)
                identity = ('id',employee_id) if employee_id is not None else ('name',employee.name.casefold())
                if identity in identities:
                    raise ValueError('Duplicate employee row; use separate Employee IDs for namesakes')
                identities.add(identity)
                for col, day in columns.items():
                    value = row[col]
                    if optional(value) is not None:
                        employee.add_hours(day,value)
                if employee.hours_by_date:
                    employees.append(employee)
            except ValueError as exc:
                raise ExcelImportError(f'Row {idx+2}: {exc}') from exc
        if not employees:
            raise ExcelImportError('No employees with explicitly entered hours were found')
        return employees
    except ExcelImportError:
        raise
    except Exception as exc:
        raise ExcelImportError(f'Could not read XLSX: {exc}') from exc


def get_import_summary(employees):
    dates = {d for emp in employees for d in emp.hours_by_date}
    return {'employee_count':len(employees), 'total_hours':sum(e.get_total_hours() for e in employees),
            'date_range':(min(dates),max(dates)) if dates else (None,None), 'unique_dates':dates}


def process_import(db, employees, options, progress=None):
    """Run on a connection created in this same worker; never access Tk here."""
    if not options['save_to_db'] and not options['create_pdf']:
        raise ExcelImportError('Select saving hours or generating PDFs')
    utilities = str(number(options.get('utilities',0),'Utilities deduction'))
    rental = str(number(options.get('rental',0),'Rental deduction'))
    files = []
    try:
        with db.transaction():
            # Preflight the entire batch before creating employees or documents.
            plans = []
            resolved_ids = set()
            new_names = set()
            for emp in employees:
                if emp.employee_id is not None:
                    existing = db.get_employee(emp.employee_id)
                    if existing['archived']:
                        raise ExcelImportError(f'Employee #{emp.employee_id} is archived')
                else:
                    matches = [e for e in db.get_employees(include_archived=True) if e['name'].strip().casefold()==emp.name.casefold()]
                    if len(matches)>1 or (matches and matches[0]['archived']):
                        raise ExcelImportError(f'Ambiguous or archived employee: {emp.name}. Use Employee ID.')
                    existing = matches[0] if matches else None
                if existing is not None:
                    if existing['id'] in resolved_ids:
                        raise ExcelImportError('Multiple import rows resolve to the same employee')
                    resolved_ids.add(existing['id'])
                    if (options['save_to_db'] and options['create_pdf'] and not options.get('update_existing',True)
                        and options['rate_mode']=='custom' and Decimal(str(existing['rate']))!=Decimal(str(emp.rate))):
                        raise ExcelImportError('Excel rate differs from the stored rate; enable employee updates or use PDF-only import')
                elif emp.name.casefold() in new_names:
                    raise ExcelImportError('Duplicate new employee name in batch')
                else:
                    new_names.add(emp.name.casefold())
                # Explicit empty bank fields preserve existing details.
                details = {key:getattr(emp,key) if getattr(emp,key) is not None else (existing[key] if existing is not None else None)
                           for key in ('bank','iban','bic')}
                if existing is not None and not options.get('update_existing',True):
                    details = {key:existing[key] for key in details}
                calculate_payroll(Employee(0,emp.name,emp.rate),emp.hours_by_date,options['rate_mode'],utilities=utilities,housing=rental)
                plans.append((emp,existing,details))
            for index,(emp,existing,details) in enumerate(plans,1):
                # A PDF-only import does not mutate the employee database.
                eid = existing['id'] if existing is not None else None
                if options['save_to_db']:
                    if existing is None:
                        eid = db.add_employee(emp.name,emp.rate,**details)
                    elif options.get('update_existing',True):
                        db.update_employee(eid,emp.name,emp.rate,**details)
                path = None
                if options['create_pdf']:
                    start,end=emp.get_date_range()
                    display_name = existing['name'] if existing is not None and not options.get('update_existing',True) else emp.name
                    path=generate_payroll_pdf(display_name,emp.rate,[(d,'',h) for d,h in sorted(emp.hours_by_date.items())],
                        options['rate_mode'],utilities,rental,start,end,details['bank'],details['iban'],details['bic'],
                        action='save',employee_id=eid)
                    files.append(path)
                if options['save_to_db']:
                    if path:
                        db.save_payroll(eid,emp.hours_by_date,options['rate_mode'],*emp.get_date_range(),utilities=utilities,rental=rental,pdf_path=path)
                    else:
                        db.save_hours_batch(eid,emp.hours_by_date)
                if progress:
                    progress(index,len(plans))
    except Exception:
        # Every filename above is unique and was created by this attempt.
        for filename in files:
            Path(filename).unlink(missing_ok=True)
        raise
    return {'employees':len(employees),'files':files}
