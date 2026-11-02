# PayrollSystem 1.17.0 — usage

## Payroll screen

Bank account is visible below the employee picker: Yes, No or Not specified. A saved bank
name and only the last four IBAN characters are shown. Edit employee opens that person's card.
Set Bank account in Employees and save the card to update Payroll immediately.
Missing bank fields do not automatically mean No. During upgrade, an existing non-empty IBAN
is marked Yes; other records remain Not specified until reviewed.

Declaring No does not erase retained bank fields from the employee card. Those details are
omitted from newly generated statements and PDFs while No is selected. Already issued
statements retain their original details. A Yes status records the operator's information;
the application does not verify bank accounts with a bank.

The interface uses a light, flat theme with a separate Net pay card and scrollable forms.

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

Set Preferred min and Preferred max (whole numbers from 0 to 14), for example 8 and 12.
The range applies only to unlocked, non-excluded Monday-Saturday dates. Locked values may
fall outside that range, including manually entered hours on Sunday.
The app subtracts locked hours and distributes the remaining whole hours within the preferred
range when possible. If the total is lower or higher, it automatically relaxes the relevant
bound to match the total exactly. For example, 158 hours over October 2026 distributes
successfully even with a preferred range of 8–12. Preferences do not block a feasible total.
The allocation has modest variation where feasible. Some days may have equal hours. Unlocked Sundays and
excluded dates stay at zero. Automatic distribution never exceeds 14 hours per day,
even when an older saved preference was higher. If a locked date already exceeds 14,
correct it manually before distributing; it will not be reduced silently.
If the total exceeds the available capacity, extend the period or unlock more dates.
Existing saved hours and historical statements are not changed by this limit.
Repeating can give a different schedule.

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

New / clear starts a blank employee card. Search and list refresh keep the active filter;
searching does not leave another employee's details in Add mode. Unsaved card edits require
confirmation before clearing, searching, switching or closing. If another window/import has
changed or archived the loaded employee, Update is rejected until the card is reloaded.
Copy any unsaved values you need, then clear and select the employee again.

Changing the current employee's relevant name, rate or bank details marks the displayed
Payroll calculation unsaved. Previously issued statements remain unchanged. A custom-rate
change does not affect a calculation using Fixed rate. Archiving warns about unsaved Payroll edits.

Add a name and positive hourly rate. Banking fields are optional. Each employee has a stable ID, displayed as `Name [#ID]` in Payroll. Two employees may share a name. Archive hides the employee from active lists while retaining hours and completed statements.

## Working hours and statements

1. Select an employee and the From/To dates; click Generate Period.
2. Existing hours are loaded. If no saved hours exist in the period, weekdays start at 10 and weekends at zero. Review all values; these defaults are not attendance records.
3. Double-click hours to edit (0–24, decimal hours allowed). Save hours (draft) stores the timesheet without issuing a statement. Enter explicitly zero hours to correct a day to zero.
4. Choose Fixed 8 EUR/hour or Employee Custom Rate. Rental uses the saved Employee Details setting and bank-account rule; enter utilities manually using a decimal point (zero is valid).
5. Preview creates a temporary PDF without changing the database. Save payroll + PDF creates a unique PDF and records a payroll snapshot. Print submits a PDF to Windows without saving hours or creating a statement; printer delivery is controlled by Windows.

Switching employee loads that employee's period and resets deductions. Unsaved hours require confirmation before discarding. If you change the dates, Generate Period again before saving or creating a PDF.

History > Payroll history shows completed saved calculations. Opening one uses its saved name, banking details, daily rates and totals, even after the employee card changes.

When saving for an already issued exact period, choose Open selected, Create corrected version or Cancel.
A correction links to all current statements for that exact employee/period, preserves the originals and marks
them Superseded. History can show originals or Current only. Explicitly confirmed overlapping periods remain
separate statements and are flagged in the monthly summary. Imports cannot silently issue a changed statement
for an existing exact period: create the correction from Payroll.

## Monthly summary

History > Monthly summary groups saved current statements by the month of their period end.
A period from October 20 to November 5 belongs entirely to November, including deductions.
Past sums come from saved snapshots; changing employee rates does not recalculate them.
Superseded originals are excluded. Unlinked legacy statements for an identical employee/period are marked
Needs review and excluded until an explicit correction resolves them. Confirmed overlapping periods are
included with an overlap warning. Draft hours, including hours changed since issuing a statement, are shown
separately and never estimated as pay. Refresh after saving changes. Open employee history inspects issued
statements; Open timesheet loads the employee and month in Payroll (archived employees remain viewable in history).

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

Data > Backups and restore shows the latest available verified copy and its location. Create backup makes
a local copy; Save to another location writes a new verified file without overwriting an existing file.
Open backup folder opens the latest available backup's location. PDF files are stored separately and are
not included in a database backup; copy the PDF folder independently if required.

Choose backup to restore validates and, if required, migrates an isolated copy before confirmation.
Review the employee/hour/statement counts and confirm replacing the current database. Cancel leaves the
working data and unsaved edits untouched. Confirming discards unsaved edits and closes other data windows.
The app keeps a verified pre-restore backup, restores through a SQLite transaction and rebuilds its views.
Restore is blocked during import. Close other PayrollSystem instances first. Corrupt, unrelated or newer
unsupported backups are rejected. The selected backup file remains unchanged.

Normal uninstall preserves the database and backups. Do not delete `%LOCALAPPDATA%\PayrollSystem` unless you intentionally want to erase user data.

## Saved rental and utilities reminder (1.17.0)

In Employees, set Rental / statement (€) once; 0 disables the saved rental deduction.
The saved amount is also shown in the Employees table under Rental (€).
The amount applies to every new statement of the appropriate type, without monthly proration:
Bank account Yes → Fixed rate; Bank account No → Employee rate. Not specified does not
apply rental and shows a reminder to declare the status. Payroll has no separate rental input;
the saved amount is included automatically in Deductions and Net pay for the matching mode. Changing the mode
does not copy the deduction into both parts. Utilities stay manual and may be zero; they follow
the same bank-status rule as rental. Enter the amount once and it applies only to the matching rate.

Before Print with a positive rental deduction, an inline Utilities reminder appears.
It requires no answer and printing continues with the utilities amount applicable to this rate,
including zero. Review or edit utilities before pressing Print if a different amount is needed.
The reminder is informational; it does not enter a charge automatically. Preview/save do not
trigger this print reminder. Existing saved statements retain their original deductions.

Excel import routes both rental and entered utilities by the same declared bank status; it no longer
uses a single manual rental value for everyone. New employees default to a saved rental of zero.
For an existing employee, imported name/rate/bank updates preserve the saved rental amount.

Schema 7 adds the saved rental field with a default of zero. A verified pre-migration backup
is created first. Old statement deductions are not guessed as future recurring settings.

## Save both PDFs (1.17.0)

Load the selected employee's period, enter utilities once (0 is valid) and click Save both PDFs.
The app creates two separately named files, fixed and custom, with the same daily hours.
It saves both statements together; a failure rolls back both new statements and removes new files.
This action is for the selected employee, not a batch across employees. The selected rate and
entered utilities remain unchanged. Save payroll + PDF, Preview PDF and Print still act on the selected rate.

Both rental and utilities follow Bank account: Yes → Fixed rate; No → Employee rate;
Not specified → neither deduction, with a status reminder. When a bank account appears, change
Bank account to Yes in Employee Details and save the card. The app refreshes the card before output,
so a saved No→Yes change routes both deductions into the new fixed statement and zero into custom.
Entering banking details while explicitly leaving the declaration No does not override that declaration.

If statements already exist, saving both asks to create corrected versions for the same rate and
exact period. Originals remain in history. Review any other overlapping periods before confirming.
After a bank-status change, use Save both PDFs to correct both current parts together; saving only
one part cannot leave misplaced deductions in the other. A concurrent card/history change cancels
new output rather than overwriting it.

Monthly summary adds the money from both current parts and counts their matching period hours once.
Old unlinked statements of opposite rates remain excluded pending explicit paired correction.
Duplicate statements of the same rate, differing daily hours in a pair, or positive deductions
in both parts are excluded pending review. Original statements remain available.

Database format 8 protects independently corrected rate pairs from older applications that treat
all statements of one period as a single correction group. The new payroll_pairs table records
the explicit relationship; old records are not automatically guessed as pairs. A verified format-7 backup is made
before upgrading; existing rows, bank details and historical amounts are unchanged. Use the
pre-upgrade backup if a return to an older app version is necessary.

## Save and print both PDFs (1.17.0)

Click Save & print both PDFs to save the fixed/custom pair and send both saved files to the
configured print application, in that order. Both files and statements are saved before either
print request. The utilities reminder remains informational; zero is valid. Cancellation or a
PDF/database failure sends nothing. Save both PDFs remains available without printing.

If print submission fails, the saved statements and files remain. The message lists which
parts were submitted and which were not. Retry only the remaining report; do not automatically
resend a complete pair after partial submission. A successful submission means the print request
was handed to the configured application, not confirmation that paper has physically printed.

## Checks, employee journal and completed periods (1.17.0)

Payroll displays informational checks in the scrollable right panel: bank status not specified,
zero total hours, or negative net pay for the rate being generated. Before paired output both
rates are checked. These notices do not require an answer or a nonzero utilities value. Invalid
numeric inputs are still rejected. The separate utilities reminder for rental remains non-modal.

History > Employee changes lists actual rate, Rental / statement and Bank account changes with
old/new values and a timestamp. Change history in Employee Details opens the selected employee.
New employee creation records initial values. Existing employees receive no invented past events
on migration. Bank names, IBAN and BIC are not copied to this journal. Failed transactions do not
leave journal entries. Backups and restores include the journal.

History > Payroll history > Print selected PDF sends only the selected statement. A saved file is
used when available; otherwise the original snapshot reconstructs it, preserving original amounts,
name, rates and bank details. Current card changes never recalculate a reprint. The rental/utilities
reminder is informational and uses the saved utilities value. Open PDF folder opens the selected
file's folder; with no selection it opens the reports root. Export > Open PDF folder also opens the root.

After saving and reviewing the exact employee period, choose Close period on Payroll and confirm.
Only saved statements matching current daily hours can be closed. Resolve overlaps, duplicate rates
and unlinked/inconsistent pairs first. A closed period protects hours, day rules, imports and new
or corrected statements. The card can still be updated for future periods, and closed statement
amounts remain unchanged. Payroll shows Closed / read-only and See History instead of recalculating
completed financial figures from the current card. Use History to view or reprint saved statements.

Reopen period on Payroll or History > Closed periods > Reopen selected period explicitly enables
editing again. Cancel leaves the period closed. Closed/reopened timestamps remain in the archive;
reopening does not delete original statements or bypass normal explicit correction rules. Closing
is per employee and exact date range, not a global month lock. Other employees and dates remain editable.

Database format 9 adds the journal and closed-period records after a verified backup. Existing
employee/hour/payroll rows are unchanged. Older apps reject format 9, so they cannot bypass the
closed-date protection. Full-database restore includes the saved close/reopen and journal state.


## Cyprus holidays

Data > Cyprus holidays shows an offline calendar by year. Automatic Monday–Saturday distribution skips these dates; manual hours remain allowed (up to 14/day). Lock manual holiday hours to retain them when redistributing. Existing saved hours and historical statements are unchanged.

The calendar follows [Visit Cyprus](https://www.visitcyprus.com/useful-info/time-working-hours-holidays/), checked 2026-11-02, including Christmas Eve; bank-only Easter Tuesday is excluded. Movable dates follow Orthodox Easter. Green Monday is Easter minus 48 days, as in the published table. Pentecost Monday 2029 is May 28 (Easter + 50 days), correcting a June typo in the tourism table; [OCA lists Pentecost Sunday on May 27](https://www.oca.org/readings/daily/2029/05/27). Company-specific days can use Exclude. This calendar plans hours and does not alter pay rates.

New timesheets start with zero hours on holidays. Existing saved timesheets retain their hours. To work on a holiday, double-click its hours and enter a value manually. Lock the date before redistributing to preserve those hours. Holiday names appear in Changes.
