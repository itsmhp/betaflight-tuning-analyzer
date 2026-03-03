"""
Dark QSS stylesheet for the Betaflight Tuning Analyzer Qt GUI.
"""

DARK_STYLE = """
/* ─────────────────────────────── Global ─────────────────────────────── */
QMainWindow, QWidget {
    background-color: #0d0d1a;
    color: #e0e0f0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QDialog {
    background-color: #0d0d1a;
    color: #e0e0f0;
}

/* ─────────────────────────────── Buttons ─────────────────────────────── */
QPushButton {
    background-color: #4361ee;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: bold;
    font-size: 13px;
    min-height: 32px;
}
QPushButton:hover {
    background-color: #5575ff;
}
QPushButton:pressed {
    background-color: #2b47d6;
}
QPushButton:disabled {
    background-color: #2a2a4a;
    color: #606080;
}

QPushButton#secondary {
    background-color: #1e1e38;
    color: #c0c0e0;
    border: 1px solid #2a2a4a;
}
QPushButton#secondary:hover {
    background-color: #2a2a4e;
}

QPushButton#danger {
    background-color: #c0392b;
    color: white;
}
QPushButton#danger:hover {
    background-color: #e74c3c;
}

QPushButton#file_btn {
    background-color: #1e1e38;
    color: #a0a0d0;
    border: 2px dashed #2a2a5a;
    border-radius: 8px;
    padding: 14px 24px;
    font-size: 13px;
    text-align: left;
}
QPushButton#file_btn:hover {
    border-color: #4361ee;
    background-color: #1a1a38;
    color: #d0d0ff;
}
QPushButton#file_btn[hasFile="true"] {
    border-style: solid;
    border-color: #4361ee;
    background-color: #131330;
    color: #6ee7b7;
}

QPushButton#copy_btn {
    background-color: #1e1e38;
    color: #a0a0d0;
    border: 1px solid #2a2a5a;
    border-radius: 4px;
    padding: 5px 14px;
    font-size: 12px;
    min-height: 26px;
}
QPushButton#copy_btn:hover {
    background-color: #2a2a4e;
}

/* ─────────────────── Input Fields ─────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #141428;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 7px 10px;
    color: #e0e0f0;
    font-size: 13px;
    min-height: 30px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #4361ee;
    background-color: #16163a;
}
QLineEdit::placeholder {
    color: #505065;
}

QComboBox {
    background-color: #141428;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 6px 10px;
    color: #e0e0f0;
    font-size: 13px;
    min-height: 32px;
}
QComboBox:focus {
    border: 1px solid #4361ee;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #6060a0;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    color: #e0e0f0;
    selection-background-color: #4361ee;
    selection-color: white;
    padding: 2px;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #2a2a4a;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3a3a6a;
}

/* ─────────────────── Tabs ─────────────────── */
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    border-radius: 0 4px 4px 4px;
    background-color: #0d0d1a;
}
QTabBar {
    background-color: transparent;
}
QTabBar::tab {
    background-color: #141428;
    color: #7070a0;
    padding: 8px 18px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 4px 4px 0 0;
    margin-right: 2px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background-color: #1e1e38;
    color: #4361ee;
    border-color: #2a2a4a;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background-color: #1a1a30;
    color: #c0c0e0;
}

/* ─────────────────── Scroll Bars ─────────────────── */
QScrollBar:vertical {
    background-color: #0d0d1a;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #2a2a5a;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background-color: #4361ee;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background-color: #0d0d1a;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #2a2a5a;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ─────────────────── Text / Labels ─────────────────── */
QLabel#title_label {
    font-size: 24px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#subtitle_label {
    font-size: 13px;
    color: #7070a0;
}
QLabel#section_label {
    font-size: 14px;
    font-weight: bold;
    color: #c0c0ff;
    padding-top: 6px;
}
QLabel#hint_label {
    font-size: 11px;
    color: #606080;
}
QLabel#error_badge {
    background-color: #3d0a0a;
    color: #ff6b6b;
    border: 1px solid #7d2020;
    border-radius: 3px;
    padding: 2px 8px;
    font-weight: bold;
}
QLabel#warning_badge {
    background-color: #3d2d00;
    color: #ffc107;
    border: 1px solid #7d5a00;
    border-radius: 3px;
    padding: 2px 8px;
    font-weight: bold;
}
QLabel#info_badge {
    background-color: #00243d;
    color: #64b5f6;
    border: 1px solid #0a4f7d;
    border-radius: 3px;
    padding: 2px 8px;
    font-weight: bold;
}
QLabel#critical_badge {
    background-color: #3d0520;
    color: #ff4081;
    border: 1px solid #7d1040;
    border-radius: 3px;
    padding: 2px 8px;
    font-weight: bold;
}

/* ─────────────────── Text Edit (CLI output) ─────────────────── */
QTextEdit {
    background-color: #080c14;
    border: 1px solid #1a1a3a;
    border-radius: 4px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #a8ff78;
    padding: 8px;
}

/* ─────────────────── Group Box ─────────────────── */
QGroupBox {
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px 12px 12px 12px;
    background-color: #0e0e1e;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #7070d0;
    font-weight: bold;
    font-size: 12px;
}

/* ─────────────────── Frame / Cards ─────────────────── */
QFrame#card {
    background-color: #111128;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
}
QFrame#severity_error {
    background-color: #1a0808;
    border: 1px solid #5a1010;
    border-radius: 6px;
}
QFrame#severity_critical {
    background-color: #1a0512;
    border: 1px solid #6a0828;
    border-radius: 6px;
}
QFrame#severity_warning {
    background-color: #1a1400;
    border: 1px solid #5a4200;
    border-radius: 6px;
}
QFrame#severity_info {
    background-color: #001824;
    border: 1px solid #003a5a;
    border-radius: 6px;
}

/* ─────────────────── Loading label ─────────────────── */
QLabel#loading_label {
    font-size: 16px;
    font-weight: bold;
    color: #7070e0;
}

/* ─────────────────── Progress Bar ─────────────────── */
QProgressBar {
    background-color: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    text-align: center;
    color: #e0e0f0;
    height: 14px;
}
QProgressBar::chunk {
    background-color: #4361ee;
    border-radius: 3px;
}

/* ─────────────────── Splitter ─────────────────── */
QSplitter::handle {
    background-color: #2a2a4a;
    width: 2px;
    height: 2px;
}

/* ─────────────────── Preset radio frame ─────────────────── */
QFrame#preset_btn {
    background-color: #111128;
    border: 2px solid #2a2a4a;
    border-radius: 8px;
    padding: 8px;
}
QFrame#preset_btn:hover {
    border-color: #4361ee;
    background-color: #16163a;
}
QFrame#preset_btn[selected="true"] {
    border-color: #4361ee;
    background-color: #131340;
}
"""
