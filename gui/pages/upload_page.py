"""
Upload / home page widget.

Provides file pickers for CLI dump and optional BBL file,
a quad-profile form, preset selection, and the Analyze button.
Includes a language selector that updates all UI strings live.
"""
from __future__ import annotations

from typing import Optional
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QComboBox,
    QGroupBox, QFileDialog, QScrollArea,
    QSizePolicy,
)

from app.knowledge.presets import QuadProfile
from gui.i18n import t, set_lang, current_lang, LANGUAGE_OPTIONS



class UploadPage(QWidget):
    """Form page for selecting files and entering quad profile data."""

    analyze_requested = Signal(str, object, object)  # cli_path, bbl_path|None, QuadProfile
    # Emitted when the user changes language so MainWindow can refresh other pages
    language_changed = Signal(str)

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

        # ── Hero header (title + language selector) ──────────────────────
        hero = QWidget()
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(0, 0, 0, 8)
        hero_layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel(t("app_title"))
        self.title_lbl.setObjectName("title_label")
        self.title_lbl.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        lang_row = QHBoxLayout()
        lang_row.setSpacing(6)
        self.lang_label = QLabel(t("language_label") + ":")
        self.lang_label.setStyleSheet("color:#7070a0;font-size:12px;")
        self.lang_combo = QComboBox()
        self.lang_combo.setFixedWidth(160)
        self.lang_combo.setToolTip("Select language / Pilih Bahasa / Idioma / Sprache")
        for code, name in LANGUAGE_OPTIONS:
            self.lang_combo.addItem(name, code)
        current = current_lang()
        for i, (code, _) in enumerate(LANGUAGE_OPTIONS):
            if code == current:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.currentIndexChanged.connect(self._on_lang_change)
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo)
        top_row.addLayout(lang_row)
        hero_layout.addLayout(top_row)

        self.subtitle_lbl = QLabel(t("app_subtitle"))
        self.subtitle_lbl.setObjectName("subtitle_label")
        self.subtitle_lbl.setWordWrap(True)
        hero_layout.addWidget(self.subtitle_lbl)
        layout.addWidget(hero)

        # ── File selection ────────────────────────────────────────────────
        self.files_box = QGroupBox(t("files_group"))
        files_grid = QGridLayout(self.files_box)
        files_grid.setSpacing(12)

        cli_top = QHBoxLayout()
        self.cli_title_lbl = QLabel(t("cli_section"))
        self.cli_title_lbl.setObjectName("section_label")
        self.cli_req_lbl = QLabel(t("cli_required"))
        self.cli_req_lbl.setStyleSheet("color: #ef5350; font-size: 11px;")
        cli_top.addWidget(self.cli_title_lbl)
        cli_top.addWidget(self.cli_req_lbl)
        cli_top.addStretch()

        self.cli_hint = QLabel(t("cli_hint"))
        self.cli_hint.setObjectName("hint_label")

        self.cli_btn = QPushButton(t("cli_btn"))
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

        bbl_top = QHBoxLayout()
        self.bbl_title_lbl = QLabel(t("bbl_section"))
        self.bbl_title_lbl.setObjectName("section_label")
        self.bbl_opt_lbl = QLabel(t("bbl_optional"))
        self.bbl_opt_lbl.setStyleSheet("color: #606080; font-size: 11px;")
        bbl_top.addWidget(self.bbl_title_lbl)
        bbl_top.addWidget(self.bbl_opt_lbl)
        bbl_top.addStretch()

        self.bbl_hint = QLabel(t("bbl_hint"))
        self.bbl_hint.setObjectName("hint_label")

        self.bbl_btn = QPushButton(t("bbl_btn"))
        self.bbl_btn.setObjectName("file_btn")
        self.bbl_btn.setMinimumHeight(56)
        self.bbl_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.bbl_btn.clicked.connect(self._pick_bbl)

        self.bbl_name_label = QLabel("")
        self.bbl_name_label.setObjectName("hint_label")

        bbl_clear_layout = QHBoxLayout()
        self.bbl_clear_btn = QPushButton(t("bbl_clear"))
        self.bbl_clear_btn.setObjectName("secondary")
        self.bbl_clear_btn.setMaximumWidth(140)
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
        layout.addWidget(self.files_box)

        # ── Quad profile ─────────────────────────────────────────────────
        self.profile_box = QGroupBox(t("profile_group"))
        profile_grid = QGridLayout(self.profile_box)
        profile_grid.setSpacing(10)
        profile_grid.setContentsMargins(14, 16, 14, 14)

        def _lbl(text: str) -> QLabel:
            lb = QLabel(text)
            lb.setStyleSheet("color: #a0a0d0; font-size: 12px;")
            return lb

        self._lbl_frame = _lbl(t("frame_size_lbl"))
        profile_grid.addWidget(self._lbl_frame, 0, 0)
        self.frame_size = QComboBox()
        self._update_frame_options()
        profile_grid.addWidget(self.frame_size, 0, 1)

        self._lbl_prop = _lbl(t("prop_size_lbl"))
        profile_grid.addWidget(self._lbl_prop, 0, 2)
        self.prop_size = QLineEdit()
        self.prop_size.setPlaceholderText(t("prop_size_placeholder"))
        profile_grid.addWidget(self.prop_size, 0, 3)

        self._lbl_battery = _lbl(t("battery_lbl"))
        profile_grid.addWidget(self._lbl_battery, 1, 0)
        self.battery_cells = QComboBox()
        self._update_battery_options()
        profile_grid.addWidget(self.battery_cells, 1, 1)

        self._lbl_kv = _lbl(t("motor_kv_lbl"))
        profile_grid.addWidget(self._lbl_kv, 1, 2)
        self.motor_kv = QSpinBox()
        self.motor_kv.setRange(0, 30_000)
        self.motor_kv.setValue(0)
        self.motor_kv.setSpecialValueText("—")
        self.motor_kv.setSingleStep(100)
        profile_grid.addWidget(self.motor_kv, 1, 3)

        self._lbl_weight = _lbl(t("weight_lbl"))
        profile_grid.addWidget(self._lbl_weight, 2, 0)
        self.weight = QSpinBox()
        self.weight.setRange(0, 10_000)
        self.weight.setValue(0)
        self.weight.setSpecialValueText("—")
        self.weight.setSingleStep(10)
        profile_grid.addWidget(self.weight, 2, 1)

        self._lbl_fc = _lbl(t("fc_lbl"))
        profile_grid.addWidget(self._lbl_fc, 2, 2)
        self.fc_name = QLineEdit()
        self.fc_name.setPlaceholderText(t("fc_placeholder"))
        profile_grid.addWidget(self.fc_name, 2, 3)

        self._lbl_esc = _lbl(t("esc_lbl"))
        profile_grid.addWidget(self._lbl_esc, 3, 0)
        self.esc_name = QLineEdit()
        self.esc_name.setPlaceholderText(t("esc_placeholder"))
        profile_grid.addWidget(self.esc_name, 3, 1)

        self._lbl_style = _lbl(t("style_lbl"))
        profile_grid.addWidget(self._lbl_style, 3, 2)
        self.flying_style = QComboBox()
        self._update_style_options()
        profile_grid.addWidget(self.flying_style, 3, 3)

        for col in (1, 3):
            profile_grid.setColumnStretch(col, 1)
        layout.addWidget(self.profile_box)

        # Internal value lists — order mirrors the combo options
        self._frame_values = [
            "", "65mm", "75mm", "3inch", "3inch_cinewhoop",
            "4inch", "5inch", "5inch_race", "6inch", "7inch", "8inch_plus",
        ]
        self._battery_values = [0, 1, 2, 3, 4, 5, 6]
        self._style_values = ["freestyle", "cinematic", "racing", "long_range"]

        # ── Preset selection ─────────────────────────────────────────────
        self.preset_box = QGroupBox(t("preset_group"))
        preset_layout = QVBoxLayout(self.preset_box)
        preset_layout.setSpacing(8)

        self.preset_desc_lbl = QLabel(t("preset_desc"))
        self.preset_desc_lbl.setObjectName("hint_label")
        self.preset_desc_lbl.setWordWrap(True)
        preset_layout.addWidget(self.preset_desc_lbl)

        presets_row = QHBoxLayout()
        presets_row.setSpacing(10)
        self._preset_buttons: dict[str, QPushButton] = {}
        self._preset_keys = ["none", "low", "medium", "high", "ultra"]
        for key in self._preset_keys:
            btn = self._make_preset_btn(key)
            self._preset_buttons[key] = btn
            btn.clicked.connect(lambda checked, k=key: self._select_preset(k))
            presets_row.addWidget(btn)
        preset_layout.addLayout(presets_row)
        layout.addWidget(self.preset_box)

        self._select_preset("none")

        # ── Analyze button ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.analyze_btn = QPushButton(t("analyze_btn"))
        self.analyze_btn.setMinimumWidth(200)
        self.analyze_btn.setMinimumHeight(44)
        self.analyze_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.analyze_btn.clicked.connect(self._on_analyze)
        btn_row.addWidget(self.analyze_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

    # ──────────────────────────────────────────────────────────────────────
    # Language switching
    # ──────────────────────────────────────────────────────────────────────

    def _on_lang_change(self, index: int) -> None:
        code = self.lang_combo.itemData(index)
        if code and code != current_lang():
            set_lang(code)
            self._apply_lang()
            self.language_changed.emit(code)

    def _apply_lang(self) -> None:
        """Update all translatable UI strings to the current language."""
        self.title_lbl.setText(t("app_title"))
        self.subtitle_lbl.setText(t("app_subtitle"))
        self.lang_label.setText(t("language_label") + ":")

        self.files_box.setTitle(t("files_group"))
        self.cli_title_lbl.setText(t("cli_section"))
        self.cli_req_lbl.setText(t("cli_required"))
        self.cli_hint.setText(t("cli_hint"))
        self.bbl_title_lbl.setText(t("bbl_section"))
        self.bbl_opt_lbl.setText(t("bbl_optional"))
        self.bbl_hint.setText(t("bbl_hint"))
        self.bbl_clear_btn.setText(t("bbl_clear"))

        if not self._cli_path:
            self.cli_btn.setText(t("cli_btn"))
        if not self._bbl_path:
            self.bbl_btn.setText(t("bbl_btn"))

        self.profile_box.setTitle(t("profile_group"))
        self._lbl_frame.setText(t("frame_size_lbl"))
        self._lbl_prop.setText(t("prop_size_lbl"))
        self.prop_size.setPlaceholderText(t("prop_size_placeholder"))
        self._lbl_battery.setText(t("battery_lbl"))
        self._lbl_kv.setText(t("motor_kv_lbl"))
        self._lbl_weight.setText(t("weight_lbl"))
        self._lbl_fc.setText(t("fc_lbl"))
        self.fc_name.setPlaceholderText(t("fc_placeholder"))
        self._lbl_esc.setText(t("esc_lbl"))
        self.esc_name.setPlaceholderText(t("esc_placeholder"))
        self._lbl_style.setText(t("style_lbl"))

        fi = self.frame_size.currentIndex()
        self._update_frame_options()
        self.frame_size.setCurrentIndex(fi)

        bi = self.battery_cells.currentIndex()
        self._update_battery_options()
        self.battery_cells.setCurrentIndex(bi)

        si = self.flying_style.currentIndex()
        self._update_style_options()
        self.flying_style.setCurrentIndex(si)

        self.preset_box.setTitle(t("preset_group"))
        self.preset_desc_lbl.setText(t("preset_desc"))
        for key in self._preset_keys:
            self._preset_buttons[key].setText(f"{t(f'preset_{key}')}\n{t(f'preset_{key}_tip')}")

        self.analyze_btn.setText(t("analyze_btn"))

    def _update_frame_options(self) -> None:
        self.frame_size.clear()
        self.frame_size.addItems([
            "",
            t("frame_65mm"), t("frame_75mm"), t("frame_3inch"), t("frame_3inch_cw"),
            t("frame_4inch"), t("frame_5inch"), t("frame_5inch_race"),
            t("frame_6inch"), t("frame_7inch"), t("frame_8inch"),
        ])

    def _update_battery_options(self) -> None:
        self.battery_cells.clear()
        self.battery_cells.addItems([t("battery_unknown"), "1S", "2S", "3S", "4S", "5S", "6S"])

    def _update_style_options(self) -> None:
        self.flying_style.clear()
        self.flying_style.addItems([
            t("style_freestyle"), t("style_cinematic"),
            t("style_racing"),    t("style_longrange"),
        ])

    # ──────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────

    def _make_preset_btn(self, key: str) -> QPushButton:
        btn = QPushButton(f"{t(f'preset_{key}')}\n{t(f'preset_{key}_tip')}")
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
            self, t("cli_section"), "",
            "CLI Dump (*.txt *.log *.cli);;All Files (*)"
        )
        if path:
            self._cli_path = path
            name = Path(path).name
            self.cli_btn.setText(f"  {name}")
            self.cli_btn.setProperty("hasFile", "true")
            self.cli_btn.setStyle(self.cli_btn.style())
            self.cli_name_label.setText(path)
            self.cli_name_label.setStyleSheet("color: #6ee7b7; font-size: 11px;")

    def _pick_bbl(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, t("bbl_section"), "",
            "Blackbox Log (*.bbl *.bfl *.csv);;All Files (*)"
        )
        if path:
            self._bbl_path = path
            name = Path(path).name
            self.bbl_btn.setText(f"  {name}")
            self.bbl_btn.setProperty("hasFile", "true")
            self.bbl_btn.setStyle(self.bbl_btn.style())
            self.bbl_name_label.setText(path)
            self.bbl_name_label.setStyleSheet("color: #6ee7b7; font-size: 11px;")
            self.bbl_clear_btn.setVisible(True)

    def _clear_bbl(self) -> None:
        self._bbl_path = None
        self.bbl_btn.setText(t("bbl_btn"))
        self.bbl_btn.setProperty("hasFile", "false")
        self.bbl_btn.setStyle(self.bbl_btn.style())
        self.bbl_name_label.setText("")
        self.bbl_clear_btn.setVisible(False)

    def _on_analyze(self) -> None:
        if not self._cli_path:
            self.cli_btn.setStyleSheet(
                "QPushButton#file_btn { border-color: #ef5350; background-color: #1a080a; }"
            )
            self.cli_name_label.setText(t("cli_missing_error"))
            self.cli_name_label.setStyleSheet("color: #ef5350; font-size: 11px;")
            return

        idx_frame   = self.frame_size.currentIndex()
        idx_battery = self.battery_cells.currentIndex()
        idx_style   = self.flying_style.currentIndex()

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

