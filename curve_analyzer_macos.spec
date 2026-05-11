# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


block_cipher = None

hiddenimports = []
hiddenimports += collect_submodules("openpyxl")
hiddenimports += collect_submodules("scipy.interpolate")
hiddenimports += collect_submodules("scipy.optimize")
hiddenimports += [
    "matplotlib.backends.backend_tkagg",
    "PIL._tkinter_finder",
]

datas = [
    ("sample_sinusoidal_data.xlsx", "."),
    ("INSTRUCTIONS.txt", "."),
]

a = Analysis(
    ["curve_analyzer_gui.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Curve Analyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Curve Analyzer",
)

app = BUNDLE(
    coll,
    name="Curve Analyzer.app",
    icon=None,
    bundle_identifier="com.curveanalyzer.app",
)
