"""
Betaflight Tuning Analyzer – Qt GUI Entry point.

Launches a native PySide6 desktop application.
No browser or web server required.

Usage
-----
    python run_gui.py
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Make sure the project root is on sys.path so `app` and `gui` can be found
# when running as `python run_gui.py` from the project root.
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Set matplotlib backend before any GUI imports so it doesn't conflict
os.environ.setdefault("MPLBACKEND", "QtAgg")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.style import DARK_STYLE
from gui.main_window import MainWindow


def main() -> None:
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Betaflight Tuning Analyzer")
    app.setOrganizationName("BetaflightAnalyzer")

    # Apply dark stylesheet
    app.setStyleSheet(DARK_STYLE)

    # Default font
    app.setFont(QFont("Segoe UI", 13))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
