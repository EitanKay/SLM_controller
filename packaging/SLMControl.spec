# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


repo_root = Path.cwd()

datas = []
datas += [(str(path), "slm-files/LUT_files") for path in (repo_root / "slm-files" / "LUT_files").glob("*.lut")]

black_wfc = repo_root / "slm-files" / "WFC_files" / "black.bmp"
if black_wfc.exists():
    datas.append((str(black_wfc), "slm-files/WFC_files"))

hiddenimports = []
hiddenimports += [
    "slmsuite",
    "slmsuite.holography",
    "slmsuite.holography.algorithms",
    "slmsuite.holography.algorithms._hologram",
    "slmsuite.holography.algorithms._header",
    "slmsuite.holography.algorithms._stats",
    "slmsuite.holography.algorithms._feedback",
    "pylablib",
    "pylablib.devices",
    "pylablib.devices.Thorlabs",
]

datas += collect_data_files("slmsuite")
datas += collect_data_files("pylablib")


a = Analysis(
    [str(repo_root / "src" / "slm_gui" / "packaged_app.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PySide2",
        "PySide6",
        "tkinter",
        "pytest",
        "IPython",
        "jupyter",
        "notebook",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SLMControl",
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SLMControl",
)
