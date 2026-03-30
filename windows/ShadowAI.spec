# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).parent
main_script = project_root / "main.py"

datas = [
    (str(project_root / "data"), "data"),
    (str(project_root / "config"), "config"),
    (str(project_root / "docs"), "docs"),
    (str(project_root / "README.md"), "."),
    (str(project_root / "LICENSE"), "."),
    (str(project_root / "ShadowAI.ico"), "."),
    (str(project_root / "run_windows.bat"), "."),
    (str(project_root / "run_windows.vbs"), "."),
    (str(project_root / "install_windows.ps1"), "."),
]

hiddenimports = (
    collect_submodules("PIL")
    + [
        "tkinter",
        "tkinter.ttk",
        "tkinter.scrolledtext",
        "tkinter.filedialog",
        "PIL._tkinter_finder",
        "pynvml",
    ]
)

block_cipher = None


a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests",
        "unittest",
        "pytest",
        "pip",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShadowAI",
    icon=str(project_root / "ShadowAI.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ShadowAI",
)
