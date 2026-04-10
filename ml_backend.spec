# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the DaVinci Auto-Editor AI ML backend.
# Run from repo root: pyinstaller ml_backend.spec

a = Analysis(
    ['python/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('python/assets', 'assets'),
    ],
    hiddenimports=[
        'faster_whisper',
        'ctranslate2',
        'librosa',
        'cv2',
        'numpy',
        'scipy',
        'soundfile',
        'audioread',
    ],
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
    a.binaries,
    a.datas,
    [],
    name='ml_backend',
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
