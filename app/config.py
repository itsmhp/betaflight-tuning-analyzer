"""Application configuration."""
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path resolution – works both normally and inside a PyInstaller .exe bundle
# ---------------------------------------------------------------------------
def _get_bundle_dir() -> Path:
    """Return the base directory for bundled assets (sys._MEIPASS when frozen)."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _get_exe_dir() -> Path:
    """Return the directory that contains the running .exe (or project root)."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BUNDLE_DIR = _get_bundle_dir()
EXE_DIR = _get_exe_dir()

# Templates / static live inside the bundle (extracted by PyInstaller)
TEMPLATES_DIR = BUNDLE_DIR / "app" / "templates"
STATIC_DIR    = BUNDLE_DIR / "app" / "static"

# Uploads go next to the .exe (writable location)
UPLOAD_DIR = EXE_DIR / "uploads"

# Tools (blackbox_decode) next to the .exe, fallback to bundle
BLACKBOX_DECODE_BIN = "blackbox_decode.exe" if os.name == "nt" else "blackbox_decode"
_tools_exe   = EXE_DIR  / "tools" / BLACKBOX_DECODE_BIN
_tools_bundle = BUNDLE_DIR / "tools" / BLACKBOX_DECODE_BIN
TOOLS_DIR    = EXE_DIR / "tools" if _tools_exe.exists() else BUNDLE_DIR / "tools"
BLACKBOX_DECODE_PATH = _tools_exe if _tools_exe.exists() else _tools_bundle

# Legacy BASE_DIR alias
BASE_DIR = EXE_DIR

# Ensure upload directory exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Analysis settings
MAX_UPLOAD_SIZE_MB = 200
ALLOWED_CLI_EXT = {".txt", ".log", ".cli"}
ALLOWED_BBL_EXT = {".bbl", ".bfl", ".csv"}
# Legacy aliases
SUPPORTED_CLI_EXTENSIONS = ALLOWED_CLI_EXT
SUPPORTED_BBL_EXTENSIONS = ALLOWED_BBL_EXT
FFT_SAMPLE_RATE = 8000  # Betaflight typical gyro rate for 8kHz
