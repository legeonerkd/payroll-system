# Audit remediation — 1.9.1

This change addresses the 30 October 2026 audit of the 1.9.0 code.

## Data

- Backed-up, transactional legacy schema migration; bank-name transfer and daily-hours migration. Unknown historical rates remain NULL instead of adopting a current rate.
- Atomic hour batches, explicit zero correction, enabled SQLite foreign keys and shared numeric validation.
- Archived employees retain history. Stable employee IDs distinguish namesakes.
- Immutable payroll and daily-line snapshots; duplicate identical saves reuse a fingerprint. Updating a card cannot rewrite a completed calculation.
- Startup/manual SQLite backups and data-preserving uninstall. Restore remains a deliberate manual procedure described in the guide.

## Calculation and files

- One decimal calculation service, daily ROUND_HALF_UP monetary policy, matching UI/PDF totals.
- Multipage Unicode statements, safe filenames, full periods, IDs and unique suffixes.
- Preview does not write data. Draft hour saving is explicit. Invalid PDF input is rejected before database writes.
- Timesheet drafts and legacy hours without applied rates are clearly labelled; CSV escapes formula-like employee names.

## Import and UI

- XLSX-only parser, finite values, duplicate-date/employee validation, optional Employee ID and preserved blank bank fields.
- A worker-owned SQLite connection; Tk is accessed only by the main thread via queued progress events.
- Batch preflight and rollback, including cleanup of newly generated files. Application/window close is blocked during an import.
- No decimal-hour truncation before PDF; refreshed employee lists and totals after import.
- Employee switches reload the appropriate saved hours and recalculate totals; changed periods must be regenerated.

## Delivery and limits

- Tracked PyInstaller spec, one version source, updated instructions and tests in a read-only Windows CI workflow.
- No production database has been migrated as part of development. Test data are synthetic.
- The application still represents hourly amounts and two deductions, not tax accounting or a bank payment system.
- Original historical payrolls cannot be reconstructed if earlier versions did not store them. PDF and SQLite writes are coordinated in normal error handling; an abrupt process/OS failure between file creation and database commit can still leave an unregistered PDF. Payroll snapshots themselves are transactional.
- Retain independent backups; startup backups alone do not protect against disk loss. No automatic backup-retention deletion is performed.
- Normal uninstall preserves data. The Windows installer must be verified before distribution; a successful PyInstaller build does not validate Inno Setup or actual printer delivery.
