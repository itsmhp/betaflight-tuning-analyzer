# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Qt GUI (native desktop window) build.
# No browser or web server required.
#
# Build command:
#   pyinstaller betaflight_analyzer_gui.spec

import os
from pathlib import Path

block_cipher = None

BASE_DIR = Path(SPECPATH)

a = Analysis(
    ['run_gui.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[
        (str(BASE_DIR / 'app' / 'knowledge'), 'app/knowledge'),
        (str(BASE_DIR / 'tools'),             'tools'),
    ],
    hiddenimports=[
        # scientific
        'numpy', 'numpy.core', 'numpy.lib',
        'scipy', 'scipy.fft', 'scipy.signal',
        'pandas',
        # matplotlib / Qt backend
        'matplotlib', 'matplotlib.backends.backend_qtagg',
        'matplotlib.backends.backend_agg',
        # app modules
        'app', 'app.core', 'app.config',
        'app.parsers', 'app.parsers.cli_parser',
        'app.parsers.bbl_header_parser', 'app.parsers.bbl_data_parser',
        'app.analyzers', 'app.analyzers.pid_analyzer',
        'app.analyzers.filter_analyzer', 'app.analyzers.rate_analyzer',
        'app.analyzers.general_analyzer', 'app.analyzers.noise_analyzer',
        'app.analyzers.motor_analyzer', 'app.analyzers.tracking_analyzer',
        'app.generators', 'app.generators.cli_generator',
        'app.knowledge', 'app.knowledge.best_practices', 'app.knowledge.presets',
        # gui modules
        'gui', 'gui.style', 'gui.worker', 'gui.charts', 'gui.i18n',
        'gui.pages', 'gui.pages.upload_page', 'gui.pages.results_page',
        'gui.main_window',
        # PySide6 essentials
        'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui',
        'shiboken6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=['uvicorn', 'fastapi', 'starlette', 'aiofiles',
              'tkinter', 'PyQt5', 'wx',
              'PySide6.QtWebEngineWidgets', 'PySide6.QtMultimedia'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BetaflightTuningAnalyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
