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
    QApplication, QFileDialog, QMessageBox,
    QDoubleSpinBox, QSlider,
)

from app.knowledge.best_practices import Severity, Category
from gui.i18n import t
from gui.html_export import generate_html_report


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
# Quick Tuning Tool definitions
# ───────────────────────────────────────────────────────────────────────────────

_TOOL_DEFS: list = [
    {
        "id": "step_response",
        "label": "Step Response",
        "desc": "Per-axis PID response quality: rise time, overshoot, damping & oscillation count.",
        "dtype": "step_response",
        "needs_bbl": True,
    },
    {
        "id": "motor_health",
        "label": "Motor Health",
        "desc": "Motor imbalance, vibration noise & desync risk detection per motor.",
        "dtype": "motor_health",
        "needs_bbl": True,
    },
    {
        "id": "tpa",
        "label": "TPA Analysis",
        "desc": "Throttle PID Attenuation — measures whether TPA settings reduce oscillations at high throttle.",
        "dtype": "tpa_analysis",
        "needs_bbl": True,
    },
    {
        "id": "prop_wash",
        "label": "Prop Wash Detection",
        "desc": "Detects & scores prop-wash recovery during rapid direction changes.",
        "dtype": "prop_wash_analysis",
        "needs_bbl": True,
    },
    {
        "id": "dynamic_idle",
        "label": "Dynamic Idle",
        "desc": "Finds stable ground-idle windows to suggest an optimal dynamic_idle_min_rpm value.",
        "dtype": "dynamic_idle_analysis",
        "needs_bbl": True,
    },
    {
        "id": "anti_gravity",
        "label": "Anti-Gravity",
        "desc": "Measures gyro drift during throttle punches — tunes anti_gravity_gain.",
        "dtype": "anti_gravity",
        "needs_bbl": True,
    },
    {
        "id": "iterm_buildup",
        "label": "I-Term Build-Up",
        "desc": "Detects I-term wind-up events that cause wobble on hard manoeuvres.",
        "dtype": "iterm_buildup",
        "needs_bbl": True,
    },
    {
        "id": "feedforward",
        "label": "FeedForward Tuning",
        "desc": "Setpoint tracking quality & stick-to-FF lag per roll/pitch/yaw axis.",
        "dtype": "feedforward_analysis",
        "needs_bbl": True,
    },
    {
        "id": "thrust_linearization",
        "label": "Thrust Linearization",
        "desc": "Motor thrust curve non-linearity — onset percentage, hover point & PID impact.",
        "dtype": "thrust_linearization",
        "needs_bbl": True,
    },
    {
        "id": "stick_movement",
        "label": "Stick Movement",
        "desc": "Pilot input analysis: smoothness, symmetry, jitter & expo suggestions.",
        "dtype": "stick_movement",
        "needs_bbl": True,
    },
    {
        "id": "throttle_axis",
        "label": "Throttle & Axis Manager",
        "desc": "Throttle distribution, hover point detection & per-axis control percentages.",
        "dtype": "throttle_axis",
        "needs_bbl": True,
    },
    {
        "id": "pid_contribution",
        "label": "PID Contribution",
        "desc": "P/I/D/F ratio per axis — diagnoses D-term dominance, I-term dominance, or FF under-use.",
        "dtype": "pid_contribution",
        "needs_bbl": True,
    },
    {
        "id": "master_multiplier",
        "label": "PID Master Multiplier",
        "desc": "Interactively scale all PID gains by a multiplier and generate CLI commands.",
        "dtype": None,
        "needs_bbl": False,
    },
    {
        "id": "noise",
        "label": "Noise Profile",
        "desc": "FFT gyro noise analysis: identifies resonance peaks & filter coverage evaluation.",
        "dtype": None,
        "cat": "Noise Analysis",
        "needs_bbl": True,
    },
    {
        "id": "filter",
        "label": "Filter Analysis",
        "desc": "Filter configuration audit: LPF, notch & dynamic filter settings vs measured noise.",
        "dtype": None,
        "cat": "Filter Settings",
        "needs_bbl": False,
    },
]


def _qt_tool_findings(all_findings: list, tool: dict) -> list:
    """Collect findings belonging to a specific Quick Tuning Tool."""
    dtype = tool.get("dtype")
    cat   = tool.get("cat")
    if dtype:
        return [f for f in all_findings
                if f.data and f.data.get("type") == dtype]
    elif cat:
        return [f for f in all_findings
                if f.category.value == cat]
    return []


def _qt_tool_status(findings: list) -> tuple:
    """Return (status_label, hex_color) from the worst finding severity."""
    _order = {"critical": 4, "error": 3, "warning": 2, "info": 1}
    worst = max(findings, key=lambda f: _order.get(f.severity.value.lower(), 0))
    sev = worst.severity.value.lower()
    return {
        "critical": ("CRITICAL",     "#e74c3c"),
        "error":    ("NEEDS TUNING", "#e67e22"),
        "warning":  ("WARNING",      "#f1c40f"),
        "info":     ("GOOD",         "#2ecc71"),
    }.get(sev, ("OK", "#2ecc71"))


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

        # Quick Tuning Tools tab
        tabs.addTab(self._make_tools_tab(r, chart_data), "Quick Tuning Tools")

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

        # ── Back button + Export ─────────────────────────────────────────
        back_row = QHBoxLayout()
        back_btn = QPushButton(t("back_btn"))
        back_btn.setObjectName("secondary")
        back_btn.setMaximumWidth(220)
        back_btn.clicked.connect(self.back_requested.emit)
        back_row.addWidget(back_btn)
        back_row.addStretch()

        export_btn = QPushButton(t("export_html_btn"))
        export_btn.setMaximumWidth(200)
        export_btn.clicked.connect(lambda: self._export_html(r, chart_data))
        back_row.addWidget(export_btn)

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

    def _make_tools_tab(self, result: dict, chart_data: dict) -> QWidget:
        """Quick Tuning Tools tab — one card panel per tool."""
        has_bbl    = result.get("has_bbl", False)
        report     = result["report"]
        cli_data   = result.get("cli_data")
        all_findings = report.findings

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(16, 12, 16, 12)
        vbox.setSpacing(12)
        scroll.setWidget(container)

        if not has_bbl:
            warn = QLabel(
                "\u26a0  No .bbl / .bfl flight log uploaded.\n"
                "Most tools require blackbox data — upload a flight log to unlock them.\n"
                "Only the PID Master Multiplier and Filter Analysis work without a log."
            )
            warn.setWordWrap(True)
            warn.setStyleSheet(
                "background:#2d2000;color:#ffc107;border:1px solid #7d5a00;"
                "border-radius:4px;padding:10px 14px;font-size:12px;"
            )
            vbox.addWidget(warn)

        for tool in _TOOL_DEFS:
            findings = _qt_tool_findings(all_findings, tool)
            if tool["id"] == "master_multiplier":
                panel = self._build_multiplier_panel(cli_data)
            else:
                panel = self._build_tool_panel(tool, findings, has_bbl)
            vbox.addWidget(panel)

        vbox.addStretch()
        return outer

    def _build_tool_panel(self, tool: dict, findings: list, has_bbl: bool) -> QFrame:
        """Build a single Quick Tuning Tool result card."""
        frame = QFrame()
        frame.setObjectName("card")
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(16, 14, 16, 14)
        vbox.setSpacing(8)

        # Header row
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        name_lbl = QLabel(tool["label"])
        name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color:#e0e0f0;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()

        needs_bbl = tool.get("needs_bbl", True)
        if needs_bbl and not has_bbl:
            badge = QLabel("BBL REQUIRED")
            badge.setStyleSheet(
                "color:#6060a0;border:1px solid #2a2a5a;"
                "border-radius:3px;padding:2px 8px;font-weight:bold;font-size:11px;"
            )
        elif findings:
            status_text, status_color = _qt_tool_status(findings)
            badge = QLabel(status_text)
            badge.setStyleSheet(
                f"color:{status_color};border:1px solid {status_color};"
                "border-radius:3px;padding:2px 8px;font-weight:bold;font-size:11px;"
            )
        else:
            badge = QLabel("ALL CLEAR" if (has_bbl or not needs_bbl) else "NO DATA")
            badge.setStyleSheet(
                "color:#4db6ac;border:1px solid #4db6ac;"
                "border-radius:3px;padding:2px 8px;font-weight:bold;font-size:11px;"
            )
        hdr.addWidget(badge)
        vbox.addLayout(hdr)

        # Description
        desc = QLabel(tool["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#8080b0;font-size:11px;margin-bottom:2px;")
        vbox.addWidget(desc)

        # Findings
        if findings:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("background:#1e1e38;")
            sep.setFixedHeight(1)
            vbox.addWidget(sep)
            for f in findings:
                vbox.addWidget(_finding_card(f))
        elif (has_bbl or not needs_bbl) and not (needs_bbl and not has_bbl):
            ok_lbl = QLabel("\u2714  No issues detected \u2014 all checks passed.")
            ok_lbl.setStyleSheet("color:#4db6ac;font-size:12px;padding:2px 0;")
            vbox.addWidget(ok_lbl)

        return frame

    def _build_multiplier_panel(self, cli_data) -> QFrame:
        """Interactive PID Master Multiplier panel."""
        from app.analyzers.master_multiplier import generate_scaled_pids

        frame = QFrame()
        frame.setObjectName("card")
        frame.setFrameShape(QFrame.Shape.StyledPanel)

        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(16, 14, 16, 14)
        vbox.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        name_lbl = QLabel("PID Master Multiplier")
        name_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color:#e0e0f0;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        badge = QLabel("INTERACTIVE")
        badge.setStyleSheet(
            "color:#4361ee;border:1px solid #4361ee;"
            "border-radius:3px;padding:2px 8px;font-weight:bold;font-size:11px;"
        )
        hdr.addWidget(badge)
        vbox.addLayout(hdr)

        desc = QLabel(
            "Scale all PID gains by a chosen multiplier (0.10\u20132.00). "
            "Try 0.80\u00d7 to soften or 1.20\u00d7 to stiffen the tune."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#8080b0;font-size:11px;")
        vbox.addWidget(desc)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background:#1e1e38;")
        sep.setFixedHeight(1)
        vbox.addWidget(sep)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.setSpacing(10)
        ctrl.addWidget(QLabel("Multiplier:"))

        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.10, 2.00)
        spinbox.setSingleStep(0.05)
        spinbox.setValue(1.00)
        spinbox.setDecimals(2)
        spinbox.setFixedWidth(90)
        spinbox.setStyleSheet(
            "color:#e0e0f0;background:#1a1a38;border:1px solid #3a3a6a;"
            "border-radius:3px;padding:2px 4px;"
        )
        ctrl.addWidget(spinbox)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(10, 200)
        slider.setValue(100)
        slider.setMinimumWidth(180)
        ctrl.addWidget(slider)

        preview_btn = QPushButton("Preview")
        preview_btn.setFixedWidth(90)
        ctrl.addWidget(preview_btn)

        copy_btn = QPushButton("Copy CLI")
        copy_btn.setObjectName("copy_btn")
        copy_btn.setFixedWidth(90)
        copy_btn.setEnabled(False)
        ctrl.addWidget(copy_btn)
        ctrl.addStretch()
        vbox.addLayout(ctrl)

        # Result area
        result_area = QTextEdit()
        result_area.setReadOnly(True)
        result_area.setMinimumHeight(160)
        result_area.setMaximumHeight(260)
        result_area.setFont(QFont("Consolas", 11))
        result_area.setPlaceholderText(
            "Click \u2018Preview\u2019 to see scaled PID values and CLI commands\u2026"
        )
        vbox.addWidget(result_area)

        # Wiring
        _latest = [""]  # mutable closure ref

        def _sync_slider(val: int) -> None:
            spinbox.blockSignals(True)
            spinbox.setValue(val / 100.0)
            spinbox.blockSignals(False)

        def _sync_spin(val: float) -> None:
            slider.blockSignals(True)
            slider.setValue(int(round(val * 100)))
            slider.blockSignals(False)

        def _do_preview() -> None:
            mult = spinbox.value()
            if cli_data is None:
                result_area.setPlainText(
                    "No CLI data available \u2014 upload a CLI dump first."
                )
                return
            res = generate_scaled_pids(cli_data, mult)
            if res is None:
                result_area.setPlainText(
                    "Could not parse PID values from the CLI dump.\n"
                    "Ensure the file contains a full 'diff all' or 'dump all' output."
                )
                return
            lines = [res.summary, "", "\u2500\u2500 CLI Commands " + "\u2500" * 30]
            lines.extend(res.all_cli_commands)
            result_area.setPlainText("\n".join(lines))
            _latest[0] = "\n".join(res.all_cli_commands)
            copy_btn.setEnabled(True)

        slider.valueChanged.connect(_sync_slider)
        spinbox.valueChanged.connect(_sync_spin)
        preview_btn.clicked.connect(_do_preview)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(_latest[0]))

        return frame

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
    # Export
    # ──────────────────────────────────────────────────────────────────────

    def _export_html(self, result: dict, chart_data: dict) -> None:
        """Export analysis results to a standalone HTML file."""
        cli_data = result.get("cli_data")
        craft = getattr(cli_data, "craft_name", "report") or "report"
        default_name = f"tuning_report_{craft}.html".replace(" ", "_")

        path, _ = QFileDialog.getSaveFileName(
            self,
            t("export_html_title"),
            default_name,
            "HTML Files (*.html);;All Files (*)",
        )
        if not path:
            return

        try:
            html = generate_html_report(result, chart_data)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            QMessageBox.information(
                self,
                t("export_html_title"),
                t("export_html_success").replace("{path}", path),
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                t("export_html_title"),
                f"{t('export_html_fail')}\n{exc}",
            )

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
