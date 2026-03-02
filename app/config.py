"""Application configuration."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
TOOLS_DIR = BASE_DIR / "tools"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Ensure upload directory exists
UPLOAD_DIR.mkdir(exist_ok=True)

# blackbox_decode executable name (platform-dependent)
BLACKBOX_DECODE_BIN = "blackbox_decode.exe" if os.name == "nt" else "blackbox_decode"
BLACKBOX_DECODE_PATH = TOOLS_DIR / BLACKBOX_DECODE_BIN

# Analysis settings
MAX_UPLOAD_SIZE_MB = 200
ALLOWED_CLI_EXT = {".txt", ".log", ".cli"}
ALLOWED_BBL_EXT = {".bbl", ".bfl", ".csv"}
# Legacy aliases
SUPPORTED_CLI_EXTENSIONS = ALLOWED_CLI_EXT
SUPPORTED_BBL_EXTENSIONS = ALLOWED_BBL_EXT
FFT_SAMPLE_RATE = 8000  # Betaflight typical gyro rate for 8kHz
