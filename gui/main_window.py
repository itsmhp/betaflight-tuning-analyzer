"""
Main application window.

Uses QStackedWidget to switch between:
  - Upload page (file selection + quad profile form)
  - Loading page (while analysis runs in background)
  - Results page (analysis output with tabs and charts)
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QLabel, QProgressBar, QApplication,
)

from gui.pages.upload_page import UploadPage
from gui.pages.results_page import ResultsPage
from gui.worker import AnalysisWorker
from gui.i18n import t

# Page indices
PAGE_UPLOAD   = 0
PAGE_LOADING  = 1
PAGE_RESULTS  = 2


class LoadingPage(QWidget):
    """Simple animated loading indicator shown during analysis."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        self.title = QLabel(t("loading_title"))
        self.title.setObjectName("loading_label")
        self.title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.sub = QLabel(t("loading_sub"))
        self.sub.setStyleSheet("color:#6060a0;font-size:13px;")
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setFixedWidth(320)
        self.progress.setFixedHeight(12)

        self.hint = QLabel(t("loading_hint"))
        self.hint.setStyleSheet("color:#3a3a6a;font-size:11px;")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.sub)
        layout.addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.hint)
        layout.addStretch()


class MainWindow(QMainWindow):
    """Root window – hosts all pages in a QStackedWidget."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("window_title"))
        self.resize(1280, 860)
        self.setMinimumSize(900, 600)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        # Build pages
        self._upload_page  = UploadPage()
        self._loading_page = LoadingPage()

        self._stack.addWidget(self._upload_page)   # PAGE_UPLOAD  = 0
        self._stack.addWidget(self._loading_page)  # PAGE_LOADING = 1

        # Results page is created dynamically after analysis
        self._results_widget: Optional[QWidget] = None

        # Connect signals
        self._upload_page.analyze_requested.connect(self._on_analyze)
        self._upload_page.language_changed.connect(self._on_lang_changed)

        self._worker: Optional[AnalysisWorker] = None

        self._stack.setCurrentIndex(PAGE_UPLOAD)

    # ──────────────────────────────────────────────────────────────────────
    # Analysis flow
    # ──────────────────────────────────────────────────────────────────────

    def _on_analyze(self, cli_path: str, bbl_path, quad_profile) -> None:
        """Start background analysis and switch to loading page."""
        self._loading_page.sub.setText(
            f"Parsing {cli_path.split('/')[-1].split(chr(92))[-1]}…"
        )
        self._stack.setCurrentIndex(PAGE_LOADING)
        QApplication.processEvents()

        self._worker = AnalysisWorker(cli_path, bbl_path, quad_profile)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, result: dict) -> None:
        """Analysis complete – build and show results page."""
        self._worker = None

        # Remove previous results page if any
        if self._results_widget is not None:
            self._stack.removeWidget(self._results_widget)
            self._results_widget.deleteLater()
            self._results_widget = None

        results_page = ResultsPage(result)
        results_page.back_requested.connect(self._go_home)

        self._results_widget = results_page
        self._stack.insertWidget(PAGE_RESULTS, results_page)
        self._stack.setCurrentIndex(PAGE_RESULTS)

    def _on_error(self, message: str) -> None:
        """Analysis failed – go back to upload page and show error."""
        self._worker = None
        self._stack.setCurrentIndex(PAGE_UPLOAD)

        # Display error in the upload page (reuse the CLI hint label)
        err_lines = message.split("\n")[:2]
        from PySide6.QtWidgets import QMessageBox
        mb = QMessageBox(self)
        mb.setWindowTitle(t("error_title"))
        mb.setText(f"{t('error_text')}\n{err_lines[0]}")
        mb.setDetailedText(message)
        mb.setIcon(QMessageBox.Icon.Critical)
        mb.exec()

    def _on_lang_changed(self, code: str) -> None:
        """Refresh translatable strings in non-upload pages."""
        self.setWindowTitle(t("window_title"))
        self._loading_page.title.setText(t("loading_title"))
        self._loading_page.sub.setText(t("loading_sub"))
        self._loading_page.hint.setText(t("loading_hint"))

    def _go_home(self) -> None:
        """Return to the upload page."""
        self._stack.setCurrentIndex(PAGE_UPLOAD)
