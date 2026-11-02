# PayrollSystem 1.15.2

Local Windows application for employees, working hours and PDF payroll statements.

## Features

- Employees with stable IDs, custom hourly rates and optional banking details. Namesakes are supported. Archive preserves hours and payroll history.
- Fixed rate of 8 EUR/hour or the employee's custom rate. Rental and manually entered utilities apply to Fixed rate for Bank account Yes, or Employee rate for No; Not specified applies neither and requires clarification. Zero utilities are valid. Printing with a rental deduction shows a non-blocking utilities reminder.
- Load an existing timesheet or generate a period (up to 366 days). New periods start with 10 weekday hours and zero weekend hours; verify them before saving.
- Save draft hours independently. Preview and Print do not change the database. Save payroll + PDF records an immutable snapshot with applied rates, deductions and bank details.
- Save both PDFs creates separate fixed/custom files and saves both statements atomically. Corrections remain separate by rate; monthly totals count matching paired hours once.
- Save & print both PDFs saves the pair, then submits both saved files to the configured print application. Partial print failures preserve saved files and identify which report remains to send.
- XLSX import with validation, optional Employee ID, an all-or-nothing database transaction and unique PDF documents. Explicit zero hours correct existing hours. Blank bank fields preserve existing values.
- Unicode PDF statements fit on one A4 page; longer content shrinks. History reopens the saved calculation without using the employee's current card.
- Whole-hour distribution with daily limits, locked dates and excluded non-working dates; manual editing remains available.
- Explicit corrected statement versions preserve originals. Monthly totals use current statements by period end; drafts and unresolved duplicate periods stay separate.
- Verified database backups, export to another location and restore through Data > Backups and restore.
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

Version 1.15.2 migrates the legacy `bank_name` and `daily_hours` schema automatically. Migration failure leaves the original data unchanged. Rates and completed payrolls that older versions never saved cannot be reconstructed: legacy hours remain available with an unknown applied rate. Do not open an upgraded database with an older application version; use the pre-upgrade backup for rollback.

Uninstall preserves the database and backups. The application never uploads payroll data. Do not commit databases, payroll documents, exports or personal examples to Git.

PDFs are saved under `Documents\PayrollSystem\Payroll\YYYY-MM\` with employee ID, full period and a unique suffix. They are separate from the database; back them up as well.

## Calculation policy

Money is calculated with decimal arithmetic. Each daily amount is rounded to cents with ROUND_HALF_UP, then summed; each deduction is rounded to cents before subtraction. Hours remain exact to the supplied decimal input (0–24 per day). Employee rates must be finite and positive; deductions must be finite and non-negative. Negative net results are allowed when deductions exceed gross pay and must be reviewed by the operator.

This application implements hourly amounts and two deductions; it has no tax, social contribution, overtime or payment-approval engine.

## Repository safety

Real database backups were removed from the branch and tag history on 30 October 2026. Existing clones must be replaced with fresh clones; do not merge old history back. GitHub may retain old cached objects pending a support cleanup.
