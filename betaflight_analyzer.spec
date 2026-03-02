# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None

# Base directory of the project
BASE_DIR = Path(SPECPATH)

a = Analysis(
    ['run.py'],
    pathex=[str(BASE_DIR)],
    binaries=[],
    datas=[
        # Include templates folder
        (str(BASE_DIR / 'app' / 'templates'), 'app/templates'),
        # Include static files (CSS, JS)
        (str(BASE_DIR / 'app' / 'static'), 'app/static'),
        # Include knowledge base
        (str(BASE_DIR / 'app' / 'knowledge'), 'app/knowledge'),
        # Include tools directory (for blackbox_decode placeholder)
        (str(BASE_DIR / 'tools'), 'tools'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'starlette.routing',
        'starlette.middleware',
        'starlette.middleware.base',
        'anyio',
        'anyio._backends._asyncio',
        'jinja2',
        'jinja2.ext',
        'multipart',
        'multipart.multipart',
        'aiofiles',
        'aiofiles.os',
        'aiofiles.threadpool',
        'numpy',
        'numpy.core',
        'numpy.lib',
        'app',
        'app.main',
        'app.config',
        'app.parsers',
        'app.parsers.cli_parser',
        'app.parsers.bbl_header_parser',
        'app.parsers.bbl_data_parser',
        'app.analyzers',
        'app.analyzers.pid_analyzer',
        'app.analyzers.filter_analyzer',
        'app.analyzers.rate_analyzer',
        'app.analyzers.general_analyzer',
        'app.analyzers.noise_analyzer',
        'app.analyzers.motor_analyzer',
        'app.analyzers.tracking_analyzer',
        'app.generators',
        'app.generators.cli_generator',
        'app.knowledge',
        'app.knowledge.best_practices',
        'app.knowledge.presets',
        'scipy',
        'scipy.fft',
        'scipy.signal',
        'pandas',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=['matplotlib', 'tkinter', 'PyQt5', 'wx'],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
