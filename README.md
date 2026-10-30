# PayrollSystem 1.9.1

Local Windows application for employees, working hours and PDF payroll statements.

## Features

- Employees with stable IDs, custom hourly rates and optional banking details. Namesakes are supported. Archive preserves hours and payroll history.
- Fixed rate of 8 EUR/hour or the employee's custom rate. Rental and utilities deductions apply in both modes.
- Load an existing timesheet or generate a period (up to 366 days). New periods start with 10 weekday hours and zero weekend hours; verify them before saving.
- Save draft hours independently. Preview does not change the database. Save/Print creates an immutable payroll snapshot with applied rates, deductions and bank details.
- XLSX import with validation, optional Employee ID, an all-or-nothing database transaction and unique PDF documents. Explicit zero hours correct existing hours. Blank bank fields preserve existing values.
- Unicode, multipage PDF statements; history reopens the saved calculation without using the employee's current card.
- CSV export of working hours. Historical applied rates are shown only when recorded; draft/legacy rates remain unknown.

## Run from source

Windows 10/11, Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

Tests and build instructions: [BUILD.md](BUILD.md). Usage: [USER_GUIDE.md](USER_GUIDE.md).

## Data and updates

The database is stored in `%LOCALAPPDATA%\PayrollSystem\payroll.db`. A verified SQLite backup is created on startup before updating an existing database. `Data > Create database backup` creates another copy; copy backups to a separate drive as well.

Version 1.9.1 migrates the legacy `bank_name` and `daily_hours` schema automatically. Migration failure leaves the original data unchanged. Rates and completed payrolls that older versions never saved cannot be reconstructed: legacy hours remain available with an unknown applied rate. Do not open an upgraded database with an older application version; use the pre-upgrade backup for rollback.

Uninstall preserves the database and backups. The application never uploads payroll data. Do not commit databases, payroll documents, exports or personal examples to Git.

PDFs are saved under `Documents\PayrollSystem\Payroll\YYYY-MM\` with employee ID, full period and a unique suffix. They are separate from the database; back them up as well.

## Calculation policy

Money is calculated with decimal arithmetic. Each daily amount is rounded to cents with ROUND_HALF_UP, then summed; each deduction is rounded to cents before subtraction. Hours remain exact to the supplied decimal input (0–24 per day). Employee rates must be finite and positive; deductions must be finite and non-negative. Negative net results are allowed when deductions exceed gross pay and must be reviewed by the operator.

This application implements hourly amounts and two deductions; it has no tax, social contribution, overtime or payment-approval engine.

## Repository safety

Real database backups were removed from the branch and tag history on 30 October 2026. Existing clones must be replaced with fresh clones; do not merge old history back. GitHub may retain old cached objects pending a support cleanup.
