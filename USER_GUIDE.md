# PayrollSystem 1.11.0 — usage

## Payroll screen

Payroll opens first. Select an employee and dates, then Load period to load saved hours
or the existing default schedule. Distribute Mon-Sat can create a period directly.
Hours stay on the left; rate, deductions, Net pay and saving actions are on the right.

Double-click an Hours cell to edit. Enter or leaving the cell confirms a valid value;
Esc cancels the current input. Changed rows display Manual edit until you reload or
redistribute the period. These markers are temporary UI hints, not a persistent audit log.
Sundays are highlighted; hours can still be manually entered on any date.

Save hours writes draft daily hours. It does not store deductions or issue a payroll;
changed payroll settings remain pending. Save payroll + PDF records the payroll and its PDF.
Preview PDF and Print do not save hours or create payroll history entries.
Watch the status beside Working hours for unsaved changes, saved drafts or saved payrolls.
Changing dates requires Load period or Distribute Mon-Sat before saving.

At larger text scales or smaller window heights, scroll the right panel to reach all actions.
Keyboard focus automatically brings its controls into view.

## Distribute total hours

Select an employee and the From/To dates, enter Total hours (incl. locked), then click
Distribute Mon-Sat. Load period is not required first. The total covers the entire period.

Select one or more table rows (Ctrl/Shift for multiple dates), then Lock / unlock to preserve
their current hours during distribution. Locked hours can still be edited manually.
Exclude / include marks a date as non-working and sets its hours to zero. Unlock a date before
excluding it; include it before locking it or entering non-zero hours. Including a date does
not restore its previous hours; edit it or distribute again.

Set Daily range Min and Max (whole numbers from 0 to 24), for example 8 and 12.
The range applies only to unlocked, non-excluded Monday-Saturday dates. Locked values may
fall outside that range, including manually entered hours on Sunday.
The app subtracts locked hours and distributes the remaining whole hours within Min–Max,
with modest variation where feasible. Some days may have equal hours. Unlocked Sundays and
excluded dates stay at zero. No day may exceed 24 hours. Repeating can give a different schedule.

If locked hours are fractional, the total may also be fractional, but the remainder must
be a whole number. For example, lock 8.5 hours and enter a total of 48.5 to distribute 40.
Impossible constraints show an error without modifying the table or database.

Double-click Hours to edit, then press Enter. Manual edits may include fractional hours and
do not redistribute other days. Save hours or Save payroll + PDF stores day rules and the
daily range together with hours. Locks/exclusions belong to the employee and dates; the range
belongs to the employee. Distributing alone does not write anything to the database.

Unsaved rules are discarded when loading a period or switching employees after confirmation.
The daily range and payroll settings are kept when loading a period for the same employee.
Repeating distribution replaces unlocked daily edits after confirmation.
Imports cannot silently enter non-zero hours on excluded dates: include and save them first.
Locks protect redistribution; they do not prevent explicit manual edits or imports.

## Employees

Add a name and positive hourly rate. Banking fields are optional. Each employee has a stable ID, displayed as `Name [#ID]` in Payroll. Two employees may share a name. Archive hides the employee from active lists while retaining hours and completed statements.

## Working hours and statements

1. Select an employee and the From/To dates; click Generate Period.
2. Existing hours are loaded. If no saved hours exist in the period, weekdays start at 10 and weekends at zero. Review all values; these defaults are not attendance records.
3. Double-click hours to edit (0–24, decimal hours allowed). Save hours (draft) stores the timesheet without issuing a statement. Enter explicitly zero hours to correct a day to zero.
4. Choose Fixed 8 EUR/hour or Employee Custom Rate. Enter rental and utility deductions, using a decimal point.
5. Preview creates a temporary PDF without changing the database. Save creates a unique PDF and records a payroll snapshot. Print also records the calculation after submitting the document to the system print handler; printer delivery is controlled by Windows.

Switching employee loads that employee's period and resets deductions. Unsaved hours require confirmation before discarding. If you change the dates, Generate Period again before saving or creating a PDF.

History > Payroll history shows completed saved calculations. Opening a historical calculation uses its saved name, banking details, daily rates and totals, even after the employee card changes. A revised calculation creates another history entry; identical repeated saves reuse the same snapshot.

Export > Export work hours exports the timesheet, not a record of payments. Applied rates for legacy hours and unissued drafts may be unknown. Completed statement totals and deductions are kept in Payroll history.

## XLSX import

Use Import > Import from Excel > Template. Only `.xlsx` is supported. Keep the first five columns in this order: Employee Name, Hourly Rate, Bank, IBAN, BIC. Add date columns such as `01-05-2026` or real Excel dates. An optional `Employee ID` column may be added after the first five columns.

- Use Employee ID for existing namesakes. Without an ID, the name must resolve to exactly one active employee or identify a new employee.
- Enter a finite positive rate and hours from 0 to 24. Duplicate dates or employee rows are errors.
- Zero explicitly corrects hours. Empty hour cells are omitted and leave existing dates unchanged.
- Empty bank, IBAN and BIC cells preserve existing details when updating. Clear details deliberately in the employee editor instead.
- Select the rate mode and deductions; preview gross values respond to the rate mode. Deductions apply individually to every imported employee.
- Save hours to database controls database writes. With it disabled, PDFs can be created without creating/updating employees. With PDFs disabled, only draft hours are saved.
- The entire batch is validated and processed as one transaction. If any row or PDF fails, database changes are rolled back and PDFs created by that attempt are removed. Do not close the program while a batch is running.

Full precision hours are used in the calculation and PDF. Files use unique names and do not overwrite earlier periods.

## Backups and restore

A verified database backup is made on startup before opening an existing database. Data > Create database backup makes a manual copy. Backups are inside the application data directory: also copy them and your PDF folder to independent storage.

To restore: close the application; preserve a copy of the current database; replace `payroll.db` with the selected backup; reopen with the appropriate application version. The next launch verifies/migrates supported schemas. Restoring replaces newer records, so first confirm that the chosen backup has the required data.

Normal uninstall preserves the database and backups. Do not delete `%LOCALAPPDATA%\PayrollSystem` unless you intentionally want to erase user data.
