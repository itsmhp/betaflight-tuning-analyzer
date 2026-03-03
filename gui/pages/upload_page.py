"""
Upload / home page widget.

Provides file pickers for CLI dump and optional BBL file,
a quad-profile form, preset selection, and the Analyze button.
"""
from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QComboBox,
    QGroupBox, QFileDialog, QFrame, QScrollArea,
    QSizePolicy, QButtonGroup,
)

from app.knowledge.presets import QuadProfile


class UploadPage(QWidget):
    """Form page for selecting files and entering quad profile data."""

    analyze_requested = Signal(str, object, object)  # cli_path, bbl_path|None, QuadProfile

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cli_path: Optional[str] = None
        self._bbl_path: Optional[str] = None
        self._preset_level: str = "none"
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root.addWidget(scroll)

        inner = QWidget()
        inner.setObjectName("inner")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(40, 32, 40, 40)
        layout.setSpacing(20)
        scroll.setWidget(inner)

        # ── Hero header ──────────────────────────────────────────────────
        hero = QWidget()
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 8)
        hero_layout.setSpacing(4)

        title = QLabel("Betaflight Tuning Analyzer")
        title.setObjectName("title_label")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))

        subtitle = QLabel("Upload your CLI dump and optional blackbox log for comprehensive tuning analysis.")
        subtitle.setObjectName("subtitle_label")
        subtitle.setWordWrap(True)

        hero_layout.addWidget(title)
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        # ── File selection ────────────────────────────────────────────────
        files_box = QGroupBox("Flight Data Files")
        files_grid = QGridLayout(files_box)
        files_grid.setSpacing(12)

        # CLI file
        cli_top = QHBoxLayout()
        cli_title = QLabel("CLI Dump File")
        cli_title.setObjectName("section_label")
        cli_req = QLabel("(required)")
        cli_req.setStyleSheet("color: #ef5350; font-size: 11px;")
        cli_top.addWidget(cli_title)
        cli_top.addWidget(cli_req)
        cli_top.addStretch()

        self.cli_hint = QLabel("Betaflight CLI 'dump all' output (.txt / .log / .cli)")
        self.cli_hint.setObjectName("hint_label")

        self.cli_btn = QPushButton("  Click to select CLI dump file…")
        self.cli_btn.setObjectName("file_btn")
        self.cli_btn.setMinimumHeight(56)
        self.cli_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cli_btn.clicked.connect(self._pick_cli)

        self.cli_name_label = QLabel("")
        self.cli_name_label.setObjectName("hint_label")

        files_grid.addLayout(cli_top, 0, 0)
        files_grid.addWidget(self.cli_hint, 1, 0)
        files_grid.addWidget(self.cli_btn, 2, 0)
        files_grid.addWidget(self.cli_name_label, 3, 0)

        # BBL file
        bbl_top = QHBoxLayout()
        bbl_title = QLabel("Blackbox Log File")
        bbl_title.setObjectName("section_label")
        bbl_opt = QLabel("(optional)")
        bbl_opt.setStyleSheet("color: #606080; font-size: 11px;")
        bbl_top.addWidget(bbl_title)
        bbl_top.addWidget(bbl_opt)
        bbl_top.addStretch()

        self.bbl_hint = QLabel("Blackbox flight log (.bbl / .bfl / .csv)")
        self.bbl_hint.setObjectName("hint_label")

        self.bbl_btn = QPushButton("  Click to select BBL file (optional)…")
        self.bbl_btn.setObjectName("file_btn")
        self.bbl_btn.setMinimumHeight(56)
        self.bbl_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.bbl_btn.clicked.connect(self._pick_bbl)

        self.bbl_name_label = QLabel("")
        self.bbl_name_label.setObjectName("hint_label")

        bbl_clear_layout = QHBoxLayout()
        self.bbl_clear_btn = QPushButton("✕ Clear BBL")
        self.bbl_clear_btn.setObjectName("secondary")
        self.bbl_clear_btn.setMaximumWidth(130)
        self.bbl_clear_btn.setVisible(False)
        self.bbl_clear_btn.clicked.connect(self._clear_bbl)
        bbl_clear_layout.addWidget(self.bbl_name_label)
        bbl_clear_layout.addStretch()
        bbl_clear_layout.addWidget(self.bbl_clear_btn)

        files_grid.addLayout(bbl_top, 0, 1)
        files_grid.addWidget(self.bbl_hint, 1, 1)
        files_grid.addWidget(self.bbl_btn, 2, 1)
        files_grid.addLayout(bbl_clear_layout, 3, 1)

        files_grid.setColumnStretch(0, 1)
        files_grid.setColumnStretch(1, 1)

        layout.addWidget(files_box)

        # ── Quad profile ─────────────────────────────────────────────────
        profile_box = QGroupBox("Quad Profile  (optional – improves recommendations)")
        profile_grid = QGridLayout(profile_box)
        profile_grid.setSpacing(10)
        profile_grid.setContentsMargins(14, 16, 14, 14)

        def _lbl(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setStyleSheet("color: #a0a0d0; font-size: 12px;")
            return lb

        # Row 0: Frame size, Prop size
        profile_grid.addWidget(_lbl("Frame Size"), 0, 0)
        self.frame_size = QComboBox()
        self.frame_size.addItems([
            "", "65mm (Tiny Whoop)", "75mm (Whoop)", "3\" Micro / Toothpick",
            "3\" CineWhoop", "4\" Micro", "5\" Freestyle",
            "5\" Race", "6\" Long Range", "7\" Long Range", "8\"+ X-Class",
        ])
        self._frame_values = [
            "", "65mm", "75mm", "3inch", "3inch_cinewhoop",
            "4inch", "5inch", "5inch_race", "6inch", "7inch", "8inch_plus",
        ]
        profile_grid.addWidget(self.frame_size, 0, 1)

        profile_grid.addWidget(_lbl("Prop Size"), 0, 2)
        self.prop_size = QLineEdit()
        self.prop_size.setPlaceholderText("e.g. 5045, 3018, 51303")
        profile_grid.addWidget(self.prop_size, 0, 3)

        # Row 1: Battery, Motor KV
        profile_grid.addWidget(_lbl("Battery (S count)"), 1, 0)
        self.battery_cells = QComboBox()
        self.battery_cells.addItems(["0 – Unknown", "1S", "2S", "3S", "4S", "5S", "6S"])
        self._battery_values = [0, 1, 2, 3, 4, 5, 6]
        profile_grid.addWidget(self.battery_cells, 1, 1)

        profile_grid.addWidget(_lbl("Motor KV"), 1, 2)
        self.motor_kv = QSpinBox()
        self.motor_kv.setRange(0, 30_000)
        self.motor_kv.setValue(0)
        self.motor_kv.setSpecialValueText("Unknown")
        self.motor_kv.setSingleStep(100)
        profile_grid.addWidget(self.motor_kv, 1, 3)

        # Row 2: Weight, FC name
        profile_grid.addWidget(_lbl("AUW Weight (g)"), 2, 0)
        self.weight = QSpinBox()
        self.weight.setRange(0, 10_000)
        self.weight.setValue(0)
        self.weight.setSpecialValueText("Unknown")
        self.weight.setSingleStep(10)
        profile_grid.addWidget(self.weight, 2, 1)

        profile_grid.addWidget(_lbl("FC Board"), 2, 2)
        self.fc_name = QLineEdit()
        self.fc_name.setPlaceholderText("e.g. SpeedyBee F405 V4")
        profile_grid.addWidget(self.fc_name, 2, 3)

        # Row 3: ESC, Flying style
        profile_grid.addWidget(_lbl("ESC"), 3, 0)
        self.esc_name = QLineEdit()
        self.esc_name.setPlaceholderText("e.g. BLHeli_32 55A 4in1")
        profile_grid.addWidget(self.esc_name, 3, 1)

        profile_grid.addWidget(_lbl("Flying Style"), 3, 2)
        self.flying_style = QComboBox()
        self.flying_style.addItems(["Freestyle", "Cinematic / Smooth", "Racing", "Long Range / Cruise"])
        self._style_values = ["freestyle", "cinematic", "racing", "long_range"]
        profile_grid.addWidget(self.flying_style, 3, 3)

        for col in (1, 3):
            profile_grid.setColumnStretch(col, 1)
        layout.addWidget(profile_box)

        # ── Preset selection ─────────────────────────────────────────────
        preset_box = QGroupBox("Tuning Preset  (optional)")
        preset_layout = QVBoxLayout(preset_box)
        preset_layout.setSpacing(8)

        preset_desc = QLabel(
            "Choose a tuning aggression level. The analyzer will compare your tune against the preset."
        )
        preset_desc.setObjectName("hint_label")
        preset_desc.setWordWrap(True)
        preset_layout.addWidget(preset_desc)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(10)
        self._preset_buttons: dict[str, QPushButton] = {}
        presets_info = [
            ("None",   "none",   "Analyze only – no preset comparison"),
            ("Low",    "low",    "Smooth & gentle. Great for cinematic."),
            ("Medium", "medium", "Balanced for everyday freestyle."),
            ("High",   "high",   "Aggressive, snappy. Motors run warmer."),
            ("Ultra",  "ultra",  "Maximum authority. Racing builds only."),
        ]
        for name, key, tip in presets_info:
            btn = self._make_preset_btn(name, tip)
            self._preset_buttons[key] = btn
            btn.clicked.connect(lambda checked, k=key: self._select_preset(k))
            presets_row.addWidget(btn)
        preset_layout.addLayout(presets_row)
        layout.addWidget(preset_box)

        # Select 'none' by default
        self._select_preset("none")

        # ── Analyze button ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.analyze_btn = QPushButton("  Analyze Tuning")
        self.analyze_btn.setMinimumWidth(200)
        self.analyze_btn.setMinimumHeight(44)
        self.analyze_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.analyze_btn.clicked.connect(self._on_analyze)
        btn_row.addWidget(self.analyze_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _make_preset_btn(self, name: str, desc: str) -> QPushButton:
        btn = QPushButton(f"{name}\n{desc}")
        btn.setObjectName("file_btn")
        btn.setMinimumHeight(68)
        btn.setFont(QFont("Segoe UI", 11))
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return btn

    def _select_preset(self, level: str) -> None:
        self._preset_level = level
        for key, btn in self._preset_buttons.items():
            if key == level:
                btn.setStyleSheet(
                    "QPushButton { border: 2px solid #4361ee; background-color: #131340;"
                    "color: #a0c4ff; border-radius: 8px; padding: 8px; text-align:center; "
                    "font-size:11px; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { border: 2px solid #2a2a4a; background-color: #111128;"
                    "color: #8080a0; border-radius: 8px; padding: 8px; text-align:center; "
                    "font-size:11px; }"
                    "QPushButton:hover { border-color: #4361ee; color: #d0d0ff; "
                    "background-color: #16163a; }"
                )

    def _pick_cli(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select CLI Dump File", "",
            "CLI Dump (*.txt *.log *.cli);;All Files (*)"
        )
        if path:
            self._cli_path = path
            name = Path(path).name
            self.cli_btn.setText(f"  {name}")
            self.cli_btn.setProperty("hasFile", "true")
            self.cli_btn.setStyle(self.cli_btn.style())
            self.cli_name_label.setText(f"{path}")
            self.cli_name_label.setStyleSheet("color: #6ee7b7; font-size: 11px;")

    def _pick_bbl(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Blackbox Log File", "",
            "Blackbox Log (*.bbl *.bfl *.csv);;All Files (*)"
        )
        if path:
            self._bbl_path = path
            name = Path(path).name
            self.bbl_btn.setText(f"  {name}")
            self.bbl_btn.setProperty("hasFile", "true")
            self.bbl_btn.setStyle(self.bbl_btn.style())
            self.bbl_name_label.setText(f"{path}")
            self.bbl_name_label.setStyleSheet("color: #6ee7b7; font-size: 11px;")
            self.bbl_clear_btn.setVisible(True)

    def _clear_bbl(self) -> None:
        self._bbl_path = None
        self.bbl_btn.setText("  Click to select BBL file (optional)…")
        self.bbl_btn.setProperty("hasFile", "false")
        self.bbl_btn.setStyle(self.bbl_btn.style())
        self.bbl_name_label.setText("")
        self.bbl_clear_btn.setVisible(False)

    def _on_analyze(self) -> None:
        if not self._cli_path:
            self.cli_btn.setStyleSheet(
                "QPushButton#file_btn { border-color: #ef5350; background-color: #1a080a; }"
            )
            self.cli_name_label.setText("  Please select a CLI dump file first.")
            self.cli_name_label.setStyleSheet("color: #ef5350; font-size: 11px;")
            return

        idx_frame    = self.frame_size.currentIndex()
        idx_battery  = self.battery_cells.currentIndex()
        idx_style    = self.flying_style.currentIndex()

        profile = QuadProfile(
            frame_size    = self._frame_values[idx_frame] if idx_frame < len(self._frame_values) else "",
            prop_size     = self.prop_size.text().strip(),
            battery_cells = self._battery_values[idx_battery] if idx_battery < len(self._battery_values) else 0,
            motor_kv      = self.motor_kv.value(),
            weight_grams  = self.weight.value(),
            fc_name       = self.fc_name.text().strip(),
            esc_name      = self.esc_name.text().strip(),
            flying_style  = self._style_values[idx_style] if idx_style < len(self._style_values) else "freestyle",
            preset_level  = self._preset_level if self._preset_level != "none" else "",
        )

        self.analyze_requested.emit(self._cli_path, self._bbl_path, profile)
