"""PDF presentation of the shared calculation or an immutable payroll snapshot."""
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tempfile import mkstemp
from uuid import uuid4
from xml.sax.saxutils import escape
import os
import re
import subprocess
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepInFrame
from config import FIXED_RATE
from core.models import Employee
from services.payroll_service import calculate_payroll


def _date(value):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError('Invalid date')


def _get_payroll_directory(period_from):
    month = _date(period_from).strftime('%Y-%m')
    base = Path(os.environ.get('PAYROLL_OUTPUT_DIR', Path.home() / 'Documents' / 'PayrollSystem' / 'Payroll'))
    directory = base.resolve() / month
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _generate_filename(employee_name, rate_mode, rate, period_from='', period_to='', employee_id=None):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', employee_name).strip(' .')[:70] or 'Employee'
    start = _date(period_from).isoformat() if period_from else 'period'
    end = _date(period_to).isoformat() if period_to else 'period'
    identity = f'id{employee_id}_' if employee_id is not None else ''
    return f'Payroll_{identity}{name}_{start}_{end}_{rate_mode}_{rate:.2f}_{uuid4().hex[:12]}.pdf'


def generate_payroll_pdf(employee_name, employee_rate, rows, rate_mode, utilities, rental,
                         period_from, period_to, bank_name, iban, bic, action='preview', employee_id=None):
    if action not in ('preview', 'save', 'print'):
        raise ValueError('Unknown PDF action')
    start, end = _date(period_from), _date(period_to)
    if start > end or not rows:
        raise ValueError('Generate a valid, non-empty period first')
    values = {}
    for day, _weekday, hours in rows:
        day = _date(day)
        if not start <= day <= end or day.isoformat() in values:
            raise ValueError('PDF dates must be unique and within the selected period')
        values[day.isoformat()] = hours or 0
    calculated, summary = calculate_payroll(Employee(employee_id or 0, employee_name, employee_rate), values,
                                            rate_mode, utilities=utilities or 0, housing=rental or 0)
    rate = calculated[0].rate
    directory = _get_payroll_directory(period_from) if action == 'save' else Path(__import__('tempfile').gettempdir())
    filename = _generate_filename(employee_name, rate_mode, rate, period_from, period_to, employee_id)
    target = directory / filename
    fd, temporary = mkstemp(suffix='.pdf', prefix='payroll-', dir=directory)
    os.close(fd)
    try:
        _render_pdf_to_file(temporary, employee_name, start.strftime('%d-%m-%Y'), end.strftime('%d-%m-%Y'),
                            datetime.now().strftime('%d-%m-%Y'), bank_name, iban, bic,
                            [(r.date_ui, r.weekday, f'{r.hours:g}', f'{r.rate:.2f} €', f'{r.amount:.2f} €') for r in calculated],
                            summary.gross_amount, summary.total_hours, summary.utilities_deduction,
                            summary.housing_deduction, net_amount=summary.net_amount)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    if action == 'preview':
        _open_file(str(target))
    elif action == 'print':
        _print_file(str(target))
    return str(target)


def preview_payroll_pdf(*args, **kwargs):
    return generate_payroll_pdf(*args, **kwargs, action='preview')


def preview_payroll_pdf_from_history(payroll, days):
    fd, path = mkstemp(prefix=f'Payroll_{payroll["id"]}_', suffix='.pdf')
    os.close(fd)
    _render_pdf_to_file(path, payroll['name'], payroll['period_from'], payroll['period_to'], payroll['created_at'],
                        payroll['bank'], payroll['iban'], payroll['bic'],
                        [(_date(d['work_date']).strftime('%d-%m-%Y'), _date(d['work_date']).strftime('%A'),
                          f'{d["hours"]:g}', f'{d["rate"]:.2f} €', f'{d["amount"]:.2f} €') for d in days],
                        payroll['gross_amount'], payroll['total_hours'], payroll['utilities'], payroll['rental'],
                        net_amount=payroll['net_amount'])
    _open_file(path)
    return path


def print_payroll_pdf_from_history(payroll,days):
    """Reprint one original file, or rebuild only from its immutable snapshot."""
    saved=Path(payroll['pdf_path']) if payroll['pdf_path'] else None
    if saved is not None and saved.suffix.lower()=='.pdf' and saved.is_file():
        path=str(saved)
    else:
        directory=_get_payroll_directory(payroll['period_from'])
        fd,path=mkstemp(prefix=f'Payroll_{payroll["id"]}_reprint_',suffix='.pdf',dir=directory)
        os.close(fd)
        try:
            _render_pdf_to_file(path,payroll['name'],payroll['period_from'],payroll['period_to'],payroll['created_at'],
                payroll['bank'],payroll['iban'],payroll['bic'],
                [(_date(d['work_date']).strftime('%d-%m-%Y'),_date(d['work_date']).strftime('%A'),
                  f'{d["hours"]:g}',f'{d["rate"]:.2f} €',f'{d["amount"]:.2f} €') for d in days],
                payroll['gross_amount'],payroll['total_hours'],payroll['utilities'],payroll['rental'],net_amount=payroll['net_amount'])
        except Exception:
            Path(path).unlink(missing_ok=True);raise
    _print_file(path)
    return path


def open_payroll_pdf_folder(payroll=None):
    directory=None
    if payroll is not None and payroll['pdf_path']:
        saved=Path(payroll['pdf_path'])
        if saved.is_absolute() and saved.parent.is_dir():directory=saved.parent
    if directory is None:
        directory=Path(os.environ.get('PAYROLL_OUTPUT_DIR',Path.home()/'Documents'/'PayrollSystem'/'Payroll')).resolve()
        directory.mkdir(parents=True,exist_ok=True)
    _open_file(str(directory))
    return str(directory)


def _render_pdf_to_file(path, employee_name, period_from, period_to, created_at, bank, iban, bic,
                         rows, gross, total_hours, utilities, rental, net_amount=None):
    if 'PayrollUnicode' not in pdfmetrics.getRegisteredFontNames():
        root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[1]))
        pdfmetrics.registerFont(TTFont('PayrollUnicode', str(root / 'fonts' / 'DejaVuSans.ttf')))
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('PayrollBody', parent=styles['Normal'], fontName='PayrollUnicode', fontSize=9, leading=11)
    title = ParagraphStyle('PayrollTitle', parent=normal, fontSize=12, leading=15, alignment=1, spaceAfter=3)
    small = ParagraphStyle('PayrollCell', parent=normal, fontSize=8, leading=9)
    def para(text, style=normal):
        return Paragraph(escape(str(text)), style)
    story = [para('Blue Reef Development LTD', title), para('PAYROLL STATEMENT', title), Spacer(1, 2*mm),
             para(f'Employee: {employee_name}'), para(f'Period: {period_from} - {period_to}'),
             para(f'Generated on: {created_at}'), Spacer(1, 2*mm)]
    for label, value in [('Bank',bank),('IBAN',iban),('BIC',bic)]:
        if value:
            story.append(para(f'{label}: {value}'))
    story.append(Spacer(1, 2*mm))
    data = [[para(v, small) for v in ['Date','Day','Hours','Hourly rate','Amount']]]
    data.extend([[para(v, small) for v in row] for row in rows])
    table = Table(data, colWidths=[30*mm,40*mm,20*mm,35*mm,40*mm], repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.4,colors.grey),
                               ('BACKGROUND',(0,0),(-1,0),colors.whitesmoke),
                               ('VALIGN',(0,0),(-1,-1),'TOP'),
                               ('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),1.5)]))
    story.extend([table, Spacer(1, 3*mm)])
    if net_amount is None:
        net_amount = Decimal(str(gross))-Decimal(str(utilities or 0))-Decimal(str(rental or 0))
    totals = [para(f'Total hours: {total_hours:g} h'), para(f'Gross amount: {gross:.2f} €'),
              para(f'Utilities deduction: {utilities or 0:.2f} €'), para(f'Rental deduction: {rental or 0:.2f} €'),
              para(f'Net amount: {net_amount:.2f} €'), Spacer(1, 5*mm)]
    signatures = Table([[para('Employee signature:'),para('Manager signature:')],
                        [para('________________________'),para('________________________')],
                        [para(f'Date: {created_at}'),para(f'Date: {created_at}')]],colWidths=[85*mm,80*mm])
    totals.append(signatures)
    story.extend(totals)
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=20*mm,leftMargin=20*mm,
                            topMargin=18*mm,bottomMargin=18*mm, title='Payroll statement', author='PayrollSystem')
    def page_number(c, document):
        c.setFont('PayrollUnicode',8)
        c.drawRightString(A4[0]-20*mm,10*mm,f'Page {document.page}')
    # Fit the complete statement, including totals and signatures, to one A4 page.
    # Ordinary monthly reports retain their font sizes; longer content shrinks
    # proportionally instead of losing rows or spilling onto a second page.
    content = KeepInFrame(doc.width-12, doc.height-12, story, mode='shrink', hAlign='LEFT', vAlign='TOP')
    doc.build([content],onFirstPage=page_number,onLaterPages=page_number)


def _open_file(path):
    if sys.platform.startswith('win'):
        os.startfile(path)
    else:
        subprocess.run(['open' if sys.platform=='darwin' else 'xdg-open',path],check=True)


def _print_file(path):
    if sys.platform.startswith('win'):
        os.startfile(path,'print')
    else:
        subprocess.run(['lp',path],check=True)
