# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для macOS.
Сборка: pyinstaller life_timer_mac.spec
  или запусти build.sh
"""

import os
from PyInstaller.utils.hooks import collect_data_files

ctk_datas = collect_data_files("customtkinter", include_py_files=False)

try:
    pil_datas = collect_data_files("PIL")
except Exception:
    pil_datas = []

icon_path = os.path.join("assets", "icon.icns")
icon = icon_path if os.path.exists(icon_path) else None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        *ctk_datas,
        *pil_datas,
    ],
    hiddenimports=[
        "customtkinter",
        "PIL",
        "PIL._imagingtk",
        "PIL._imaging",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "sqlalchemy.dialects.sqlite.pysqlite",
        "sqlalchemy.orm",
        "plyer",
        "plyer.platforms.macosx.notification",
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest",
        "unittest",
        "email",
        "http",
        "xml",
        "pydoc",
        "doctest",
        "difflib",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Life Timer",
    debug=False,
    strip=False,
    upx=False,           # UPX на macOS не нужен
    console=False,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Life Timer",
)

# .app bundle для macOS
app = BUNDLE(
    coll,
    name="Life Timer.app",
    icon=icon,
    bundle_identifier="com.yourname.lifetimer",
    info_plist={
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # поддержка dark mode
        "CFBundleShortVersionString": "1.0",
    },
)
