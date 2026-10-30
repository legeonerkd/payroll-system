# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root / 'app.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'icon.ico'), '.'),(str(root / 'fonts' / 'DejaVuSans.ttf'),'fonts')],
    hiddenimports=['babel.numbers'], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='PayrollSystem',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False, icon=str(root/'icon.ico'))
