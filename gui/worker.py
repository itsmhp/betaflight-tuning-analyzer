"""
Background worker thread for running the analysis pipeline.

Keeps the Qt UI responsive while analysis runs in a separate thread.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from app.core import run_analysis
from app.knowledge.presets import QuadProfile


class AnalysisWorker(QThread):
    """Runs analysis in a background thread and emits result or error."""

    finished = Signal(dict)   # emits the result dict from run_analysis()
    error = Signal(str)       # emits traceback string on exception

    def __init__(
        self,
        cli_path: str,
        bbl_path: Optional[str],
        quad_profile: QuadProfile,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cli_path = cli_path
        self.bbl_path = bbl_path
        self.quad_profile = quad_profile

    def run(self) -> None:  # noqa: D102
        try:
            cli_text = Path(self.cli_path).read_text(encoding="utf-8", errors="replace")
            bbl = Path(self.bbl_path) if self.bbl_path else None
            result = run_analysis(cli_text, bbl, self.quad_profile)
            self.finished.emit(result)
        except Exception as exc:  # pylint: disable=broad-except
            import traceback as tb
            self.error.emit(f"{type(exc).__name__}: {exc}\n\n{tb.format_exc()}")
