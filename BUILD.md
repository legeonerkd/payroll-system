# Build and verify PayrollSystem 1.9.1

Windows 10/11 x64, Python 3.12 and Inno Setup 6 are required for the Windows installer.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m PyInstaller PayrollSystem.spec --clean --noconfirm
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' PayrollSystem.iss
```

The tracked spec includes the application icon, Unicode font and Babel calendar support. The EXE is written to `dist\PayrollSystem.exe`; the installer to `output\PayrollSystem_v1.9.1_Setup.exe`. Build artifacts are not stored in Git. Downloadable releases exist only when explicitly published under GitHub Releases.

Before distributing, test a clean install, an upgrade from a copy of each supported database schema, PDF preview/save, XLSX import and uninstall. The installer must preserve user data under `%LOCALAPPDATA%\PayrollSystem`.

For isolated verification, set `PAYROLL_DATA_DIR` and `PAYROLL_OUTPUT_DIR` to disposable directories before launch. Tests set these paths themselves and never use the live database.

Schema migrations make a verified backup before changing an existing database. For rollback, close the program and restore a backup into a separate data directory; never use an older app against the upgraded database.

The version is defined in `core/version.py`; keep the installer AppVersion and output name in sync. `python get_version.py` prints the application version.
