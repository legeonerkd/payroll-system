import sys
from pathlib import Path


def get_app_dir(app_name="PayrollSystem") -> Path:
    """
    Returns writable application directory.
    Works both for Python and PyInstaller exe.
    """
    if sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Local"
    else:
        base = Path.home() / ".local" / "share"

    app_dir = base / app_name
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir
