# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\..\\turni_app\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\antim\\cedolini_web\\portal\\static\\portal', 'portal\\static\\portal')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Turni Planner San Vincenzo',
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
    icon=['C:\\Users\\antim\\cedolini_web\\tmp\\turni_planner_package\\turni_planner.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Turni Planner San Vincenzo',
)
