"""Declared account status; missing details do not establish account absence."""
ACCOUNT_LABELS={'unknown':'Not specified','yes':'Yes','no':'No'}


def validate_account_state(value):
    if value not in ACCOUNT_LABELS:raise ValueError('Bank account status must be Yes, No or Not specified')
    return value


def account_state(row):
    if row is None:return 'unknown'
    values=dict(row)
    return values.get('bank_account_state') or ('yes' if str(values.get('iban') or '').strip() else 'unknown')


def payment_details(row):
    values=dict(row)
    return {key:None if account_state(row)=='no' else values.get(key) for key in ('bank','iban','bic')}


def account_caption(row):
    if row is None:return 'Bank account: —','Select an employee','unknown'
    values=dict(row);state=account_state(row)
    if state=='yes':
        iban=''.join(str(values.get('iban') or '').split())
        bank=str(values.get('bank') or '').strip()
        if len(bank)>40:bank=bank[:39]+'…'
        detail=' · '.join(v for v in (bank,('IBAN ending '+iban[-4:]) if iban else 'IBAN not recorded') if v)
    elif state=='no':
        detail='No account declared'
        if any(values.get(key) for key in ('bank','iban','bic')):detail+=' · details on file are not used in new statements'
    else:detail='Account status has not been specified'
    return 'Bank account: '+ACCOUNT_LABELS[state],detail,state
