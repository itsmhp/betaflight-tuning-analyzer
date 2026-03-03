"""
Results page widget.

Shows the analysis results with tabs for overview, per-category findings,
CLI commands, and charts (matplotlib embedded).
"""
from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import Qt, Signal, QRectF
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QConicalGradient, QPalette
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea,
    QTabWidget, QTextEdit, QSplitter, QSizePolicy,
    QApplication,
)

from app.knowledge.best_practices import Severity
from gui.i18n import t


# ───────────────────────────────────────────────────────────────────────────────
# Helper widgets
# ───────────────────────────────────────────────────────────────────────────────

class ScoreRing(QWidget):
    """Circular score indicator painted with QPainter."""

    def __init__(self, score: int = 0, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._score = max(0, min(100, score))
        self.setFixedSize(120, 120)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(10, 10, 100, 100)
        pen_w = 10

        # Background arc
        bg = QPen(QColor("#1e1e38"), pen_w)
        p.setPen(bg)
        p.drawEllipse(rect)

        # Score arc
        score = self._score
        if score >= 80:
            color = QColor("#2ecc71")
        elif score >= 60:
            color = QColor("#f1c40f")
        elif score >= 40:
            color = QColor("#e67e22")
        else:
            color = QColor("#e74c3c")

        arc_pen = QPen(color, pen_w)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(arc_pen)
        span_angle = int(-(score / 100) * 360 * 16)
        p.drawArc(rect, 90 * 16, span_angle)

        # Score text
        p.setPen(QPen(QColor("#ffffff")))
        p.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        p.drawText(QRectF(0, 10, 120, 90), Qt.AlignmentFlag.AlignCenter, str(score))

        p.setPen(QPen(QColor("#7070a0")))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(QRectF(0, 56, 120, 50), Qt.AlignmentFlag.AlignCenter, "/100")
        p.end()


def _severity_badge(text: str, severity: str) -> QLabel:
    """Return a styled badge label for severity."""
    lbl = QLabel(text)
    colors = {
        "critical": ("background:#5a0a25;color:#ff4081;border:1px solid #8a1040;",),
        "error":    ("background:#3d0a0a;color:#ff6b6b;border:1px solid #7d2020;",),
        "warning":  ("background:#3d2d00;color:#ffc107;border:1px solid #7d5a00;",),
        "info":     ("background:#00243d;color:#64b5f6;border:1px solid #0a4f7d;",),
    }
    style = colors.get(severity.lower(), colors["info"])[0]
    lbl.setStyleSheet(
        f"QLabel {{ {style} border-radius:3px; padding:2px 8px; "
        "font-weight:bold; font-size:11px; }}"
    )
    lbl.setFixedHeight(22)
    return lbl


def _finding_card(finding) -> QFrame:
    """Build a finding card QFrame."""
    sev = finding.severity.value.lower()
    frame = QFrame()
    frame.setObjectName(f"severity_{sev}")
    frame.setFrameShape(QFrame.Shape.StyledPanel)

    card_layout = QVBoxLayout(frame)
    card_layout.setContentsMargins(12, 10, 12, 10)
    card_layout.setSpacing(5)

    # Header row: badge + category + title
    header_row = QHBoxLayout()
    header_row.setSpacing(8)
    header_row.addWidget(_severity_badge(sev.upper(), sev))

    cat_lbl = QLabel(finding.category.value)
    cat_lbl.setStyleSheet("color:#6060a0;font-size:11px;")
    header_row.addWidget(cat_lbl)

    title_lbl = QLabel(finding.title)
    title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    title_lbl.setStyleSheet("color:#e0e0f0;")
    header_row.addWidget(title_lbl)
    header_row.addStretch()

    if finding.current_value:
        cur = QLabel(f"Current: {finding.current_value}")
        cur.setStyleSheet("color:#a0a0c0;font-size:11px;")
        header_row.addWidget(cur)
    if finding.recommended_value:
        rec = QLabel(f"→ {finding.recommended_value}")
        rec.setStyleSheet("color:#4db6ac;font-size:11px;font-weight:bold;")
        header_row.addWidget(rec)

    card_layout.addLayout(header_row)

    # Description
    if finding.description:
        desc = QLabel(finding.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#c0c0e0;font-size:12px;")
        card_layout.addWidget(desc)

    # Explanation
    if finding.explanation:
        exp = QLabel(finding.explanation)
        exp.setWordWrap(True)
        exp.setStyleSheet("color:#8080b0;font-size:11px;font-style:italic;")
        card_layout.addWidget(exp)

    # CLI commands
    if finding.cli_commands:
        cmd_box = QFrame()
        cmd_box.setStyleSheet(
            "background:#060c14;border:1px solid #1a1a3a;border-radius:4px;"
        )
        cmd_layout = QHBoxLayout(cmd_box)
        cmd_layout.setContentsMargins(8, 4, 8, 4)
        cmd_text = QLabel("\n".join(finding.cli_commands))
        cmd_text.setFont(QFont("Consolas", 11))
        cmd_text.setStyleSheet("color:#a8ff78;background:transparent;border:none;")
        cmd_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        cmd_layout.addWidget(cmd_text)
        cmd_layout.addStretch()

        copy_btn = QPushButton(t("copy_btn"))
        copy_btn.setObjectName("copy_btn")
        copy_btn.setFixedWidth(60)
        cmds = "\n".join(finding.cli_commands)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(cmds))
        cmd_layout.addWidget(copy_btn)

        card_layout.addWidget(cmd_box)

    return frame


def _scrollable_findings(findings: list) -> QWidget:
    """Wrap a list of finding cards in a scrollable widget."""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(16, 12, 16, 12)
    layout.setSpacing(10)

    if not findings:
        empty = QLabel(t("no_findings"))
        empty.setStyleSheet("color:#606080;font-style:italic;")
        layout.addWidget(empty)
    else:
        for f in findings:
            layout.addWidget(_finding_card(f))
    layout.addStretch()
    return container


# ───────────────────────────────────────────────────────────────────────────────
# Main results page
# ───────────────────────────────────────────────────────────────────────────────

class ResultsPage(QWidget):
    """Full results page populated from the analysis result dict."""

    back_requested = Signal()

    def __init__(self, result: dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._result = result
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        inner = QWidget()
        vbox = QVBoxLayout(inner)
        vbox.setContentsMargins(40, 24, 40, 32)
        vbox.setSpacing(16)
        scroll.setWidget(inner)

        r       = self._result
        report  = r["report"]
        cli_data = r.get("cli_data")
        chart_data = r.get("chart_data", {})

        # ── Header ────────────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("card")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 16, 20, 16)
        h_layout.setSpacing(20)

        score_widget = ScoreRing(report.overall_score)
        h_layout.addWidget(score_widget)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        title_lbl = QLabel(t("results_title"))
        title_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color:#ffffff;")
        info_col.addWidget(title_lbl)

        if cli_data:
            craft = cli_data.craft_name or t("results_unknown_craft")
            board = cli_data.board_name or "?"
            fw    = cli_data.firmware_version or "?"
            craft_lbl = QLabel(f"{craft}  •  {board}  •  Betaflight {fw}")
            craft_lbl.setStyleSheet("color:#a0a0d0;font-size:13px;")
            info_col.addWidget(craft_lbl)

        # Stat pills row
        pills = QHBoxLayout()
        pills.setSpacing(8)
        pills.setContentsMargins(0, 4, 0, 0)
        for text, style in [
            (t("results_errors").replace("{n}", str(report.error_count + report.critical_count)),
             "background:#3d0a0a;color:#ff6b6b;border:1px solid #7d2020;"),
            (t("results_warnings").replace("{n}", str(report.warning_count)),
             "background:#3d2d00;color:#ffc107;border:1px solid #7d5a00;"),
            (t("results_info").replace("{n}", str(report.info_count)),
             "background:#00243d;color:#64b5f6;border:1px solid #0a4f7d;"),
            (t("results_total").replace("{n}", str(len(report.findings))),
             "background:#1a1a38;color:#c0c0e0;border:1px solid #2a2a5a;"),
        ]:
            pl = QLabel(text)
            pl.setStyleSheet(
                f"QLabel {{ {style} border-radius:4px; padding:3px 10px; "
                "font-weight:bold; font-size:12px; }}"
            )
            pills.addWidget(pl)
        pills.addStretch()
        info_col.addLayout(pills)
        info_col.addStretch()
        h_layout.addLayout(info_col)
        h_layout.addStretch()
        vbox.addWidget(header)

        # ── Tab widget ────────────────────────────────────────────────────
        tabs = QTabWidget()
        tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tabs.setMinimumHeight(480)

        # Overview tab
        tabs.addTab(self._make_overview_tab(report, cli_data), t("tab_overview"))

        # Per-category tabs
        for cat_name, findings in r.get("findings_by_category", {}).items():
            tabs.addTab(
                self._scrollable_wrap(_scrollable_findings(findings)),
                cat_name,
            )

        # CLI Commands tab
        tabs.addTab(self._make_cli_tab(r), t("tab_cli"))

        # Charts tab
        if chart_data:
            tabs.addTab(self._make_charts_tab(chart_data), t("tab_charts"))

        vbox.addWidget(tabs, 1)

        # ── Back button ───────────────────────────────────────────────────
        back_row = QHBoxLayout()
        back_btn = QPushButton(t("back_btn"))
        back_btn.setObjectName("secondary")
        back_btn.setMaximumWidth(220)
        back_btn.clicked.connect(self.back_requested.emit)
        back_row.addWidget(back_btn)
        back_row.addStretch()
        vbox.addLayout(back_row)

    # ──────────────────────────────────────────────────────────────────────
    # Tab builders
    # ──────────────────────────────────────────────────────────────────────

    def _scrollable_wrap(self, widget: QWidget) -> QScrollArea:
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(widget)
        return sa

    def _make_overview_tab(self, report, cli_data) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Critical / Error findings
        critical = [f for f in report.findings
                    if f.severity in (Severity.CRITICAL, Severity.ERROR)]
        if critical:
            sec = self._section(t("overview_issues"), "#ef5350")
            layout.addWidget(sec)
            for f in critical:
                layout.addWidget(_finding_card(f))

        # Warnings
        warnings = [f for f in report.findings if f.severity == Severity.WARNING]
        if warnings:
            sec = self._section(t("overview_warnings").replace("{n}", str(len(warnings))), "#ffc107")
            layout.addWidget(sec)
            for f in warnings:
                layout.addWidget(_finding_card(f))

        # Config summary
        if cli_data:
            layout.addWidget(self._config_summary(cli_data))

        layout.addStretch()
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(container)
        return sa

    def _make_cli_tab(self, result: dict) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        cli_script = result.get("cli_script", "")
        cli_diff   = result.get("cli_diff", [])

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel(t("cli_tab_title"))
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet("color:#c0c0e0;")
        toolbar.addWidget(title)
        toolbar.addStretch()

        copy_all = QPushButton(t("cli_copy_all"))
        copy_all.setObjectName("copy_btn")
        copy_all.setFixedWidth(90)
        copy_all.clicked.connect(lambda: QApplication.clipboard().setText(cli_script))
        toolbar.addWidget(copy_all)

        diff_count = QLabel(t("cli_changes").replace("{n}", str(len(cli_diff))))
        diff_count.setStyleSheet("color:#6060a0;font-size:11px;")
        toolbar.addWidget(diff_count)
        layout.addLayout(toolbar)

        # Text area
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText(cli_script if cli_script else t("cli_empty"))
        te.setMinimumHeight(320)
        layout.addWidget(te, 1)

        hint = QLabel(t("cli_paste_hint"))
        hint.setObjectName("hint_label")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        return w

    def _make_charts_tab(self, chart_data: dict) -> QWidget:
        """Build charts tab lazily (imports matplotlib here to keep startup fast)."""
        from gui.charts import build_all_charts

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        scroll.setWidget(container)

        charts = build_all_charts(chart_data)

        if not charts:
            lbl = QLabel(t("charts_empty"))
            lbl.setStyleSheet("color:#606080;font-style:italic;")
            layout.addWidget(lbl)
        else:
            for title, canvas in charts:
                # Section title
                title_lbl = QLabel(title)
                title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
                title_lbl.setStyleSheet("color:#9090d0;padding-top:4px;")
                layout.addWidget(title_lbl)

                # Separator
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("background:#1e1e38;")
                sep.setFixedHeight(1)
                layout.addWidget(sep)

                # Canvas
                canvas.setMinimumHeight(260)
                canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                layout.addWidget(canvas)

        layout.addStretch()
        return outer

    # ──────────────────────────────────────────────────────────────────────
    # Small helper widgets
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _section(text: str, color: str = "#9090d0") -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(
            f"color:{color};padding:4px 0 2px 0;"
            "border-bottom:1px solid #2a2a4a;margin-top:4px;"
        )
        return lbl

    @staticmethod
    def _config_summary(cli_data) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        title = QLabel(t("config_summary"))
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet("color:#c0c0e0;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(6)

        fields = [
            (t("config_board"),        getattr(cli_data, "board_name", "?")),
            (t("config_firmware"),     getattr(cli_data, "firmware_version", "?")),
            (t("config_craft"),        getattr(cli_data, "craft_name", "?")),
            (t("config_pid_profile"),  str(getattr(cli_data, "active_pid_profile", "?") or "?")),
            (t("config_rate_profile"), str(getattr(cli_data, "active_rate_profile", "?") or "?")),
        ]
        for i, (lbl_text, val_text) in enumerate(fields):
            row, col = divmod(i, 2)
            lbl = QLabel(lbl_text + ":")
            lbl.setStyleSheet("color:#6060a0;font-size:12px;")
            val = QLabel(str(val_text) if val_text else "—")
            val.setStyleSheet("color:#e0e0f0;font-size:12px;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(lbl, row, col * 2)
            grid.addWidget(val, row, col * 2 + 1)

        layout.addLayout(grid)
        return frame
