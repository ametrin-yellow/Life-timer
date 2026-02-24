# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec для Life Timer.
Сборка: pyinstaller life_timer.spec
  или просто запусти build.bat
"""

import os
from PyInstaller.utils.hooks import collect_data_files

ctk_datas = collect_data_files("customtkinter", include_py_files=False)

try:
    pil_datas = collect_data_files("PIL")
except Exception:
    pil_datas = []

# Иконка опциональна
icon_path = os.path.join("assets", "icon.ico")
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
        "plyer.platforms.win.notification",
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest",
        "unittest",
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
    upx=True,
    console=False,       # без чёрного окна консоли
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Life Timer",
)
