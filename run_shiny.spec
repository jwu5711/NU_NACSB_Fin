# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

faicons_datas = collect_data_files("faicons", include_py_files=False)
shiny_datas = collect_data_files("shiny", include_py_files=False)
a = Analysis(
    ["run_shiny.py"],
    pathex=[],
    binaries=[],
    datas=[
        ('shiny_implementation.py', '.'),
        ('GS_Classes.py', '.'),
        ('GS_Functions.py', '.'),
        ('outline.py', '.'),
        ('deferred_acceptance.py', '.')
    ] + faicons_datas + shiny_datas,
    hiddenimports=['faicons', 'faicons._svg', 'faicons._cache'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='run_shiny',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
