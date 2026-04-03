"""QSS Stylesheets for the application."""
from src.config import THEME_DARK, THEME_LIGHT


def get_stylesheet(theme: str = "dark") -> str:
    t = THEME_DARK if theme == "dark" else THEME_LIGHT
    return f"""
/* ─── Global ─────────────────────────────────────────────── */
* {{
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif;
    outline: none;
}}
QMainWindow, QDialog {{
    background-color: {t['bg_primary']};
    color: {t['text_primary']};
}}
QWidget {{
    background-color: transparent;
    color: {t['text_primary']};
    font-size: 13px;
}}

/* ─── Tabs ────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {t['border']};
    border-radius: 10px;
    background: {t['bg_secondary']};
    margin-top: -1px;
}}
QTabBar::tab {{
    background: {t['bg_card']};
    color: {t['text_secondary']};
    padding: 10px 22px;
    border: none;
    border-radius: 0px;
    font-size: 13px;
    font-weight: 500;
    min-width: 110px;
}}
QTabBar::tab:first {{
    border-top-left-radius: 10px;
}}
QTabBar::tab:last {{
    border-top-right-radius: 10px;
}}
QTabBar::tab:selected {{
    background: {t['bg_secondary']};
    color: {t['accent']};
    border-bottom: 2px solid {t['accent']};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    background: {t['bg_elevated']};
    color: {t['text_primary']};
}}

/* ─── Buttons ─────────────────────────────────────────────── */
QPushButton {{
    background-color: {t['bg_elevated']};
    color: {t['text_primary']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: {t['border_bright']};
    border-color: {t['accent']};
    color: {t['accent']};
}}
QPushButton:pressed {{
    background-color: {t['accent_dim']};
    color: white;
}}
QPushButton:disabled {{
    background-color: {t['bg_card']};
    color: {t['text_muted']};
    border-color: {t['border']};
}}
QPushButton#primaryBtn {{
    background-color: {t['accent']};
    color: #000;
    border: none;
    font-weight: 700;
    font-size: 14px;
    padding: 11px 28px;
    border-radius: 10px;
}}
QPushButton#primaryBtn:hover {{
    background-color: {t['accent_dim']};
    color: white;
}}
QPushButton#primaryBtn:pressed {{
    background-color: #007FA3;
}}
QPushButton#dangerBtn {{
    background-color: {t['danger']};
    color: white;
    border: none;
    font-weight: 600;
    border-radius: 8px;
}}
QPushButton#dangerBtn:hover {{
    background-color: #CC2233;
}}
QPushButton#successBtn {{
    background-color: {t['success']};
    color: #000;
    border: none;
    font-weight: 600;
    border-radius: 8px;
}}

/* ─── Input Fields ────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {t['bg_card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {t['text_primary']};
    font-size: 13px;
    selection-background-color: {t['accent']};
}}
QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid {t['accent']};
    background-color: {t['bg_elevated']};
}}

/* ─── ComboBox ────────────────────────────────────────────── */
QComboBox {{
    background-color: {t['bg_card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 8px 12px;
    color: {t['text_primary']};
    min-width: 140px;
}}
QComboBox:hover {{
    border-color: {t['accent']};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {t['text_secondary']};
    width: 0; height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {t['bg_elevated']};
    border: 1px solid {t['border_bright']};
    color: {t['text_primary']};
    selection-background-color: {t['accent']};
    border-radius: 6px;
    padding: 4px;
}}

/* ─── Progress Bars ───────────────────────────────────────── */
QProgressBar {{
    background-color: {t['bg_card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    height: 14px;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: {t['text_primary']};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t['accent']}, stop:1 {t['accent_dim']});
    border-radius: 7px;
}}

/* ─── Scroll Bars ─────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {t['bg_card']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t['border_bright']};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t['text_muted']};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {t['bg_card']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {t['border_bright']};
    border-radius: 4px;
    min-width: 24px;
}}

/* ─── List Widget ─────────────────────────────────────────── */
QListWidget {{
    background-color: {t['bg_card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 4px;
    color: {t['text_primary']};
}}
QListWidget::item {{
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px;
}}
QListWidget::item:hover {{
    background-color: {t['bg_elevated']};
}}
QListWidget::item:selected {{
    background-color: {t['accent']};
    color: #000;
}}

/* ─── Table Widget ────────────────────────────────────────── */
QTableWidget {{
    background-color: {t['bg_card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    gridline-color: {t['border']};
    color: {t['text_primary']};
}}
QTableWidget::item {{
    padding: 8px 12px;
}}
QTableWidget::item:selected {{
    background-color: {t['accent']};
    color: #000;
}}
QHeaderView::section {{
    background-color: {t['bg_elevated']};
    color: {t['text_secondary']};
    padding: 8px 12px;
    border: none;
    border-bottom: 1px solid {t['border']};
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ─── Sliders ─────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 6px;
    background: {t['bg_elevated']};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    width: 18px;
    height: 18px;
    background: {t['accent']};
    border-radius: 9px;
    margin: -6px 0;
}}
QSlider::handle:horizontal:hover {{
    background: {t['accent_dim']};
}}
QSlider::sub-page:horizontal {{
    background: {t['accent']};
    border-radius: 3px;
}}

/* ─── CheckBox & Radio ────────────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {t['text_primary']};
}}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    background: {t['bg_card']};
    border: 2px solid {t['border_bright']};
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background: {t['accent']};
    border-color: {t['accent']};
}}
QRadioButton {{
    spacing: 8px;
    color: {t['text_primary']};
}}
QRadioButton::indicator {{
    width: 18px; height: 18px;
    background: {t['bg_card']};
    border: 2px solid {t['border_bright']};
    border-radius: 9px;
}}
QRadioButton::indicator:checked {{
    background: {t['accent']};
    border-color: {t['accent']};
}}

/* ─── Spinbox ─────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {t['bg_card']};
    border: 1px solid {t['border']};
    border-radius: 8px;
    padding: 6px 10px;
    color: {t['text_primary']};
}}

/* ─── Group Box ───────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {t['border']};
    border-radius: 10px;
    margin-top: 12px;
    padding: 16px 14px 14px 14px;
    font-weight: 600;
    color: {t['text_secondary']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {t['accent']};
    font-size: 12px;
    letter-spacing: 0.5px;
}}

/* ─── Status Bar ──────────────────────────────────────────── */
QStatusBar {{
    background: {t['bg_secondary']};
    color: {t['text_secondary']};
    border-top: 1px solid {t['border']};
    padding: 4px 12px;
    font-size: 12px;
}}

/* ─── Tooltip ─────────────────────────────────────────────── */
QToolTip {{
    background-color: {t['bg_elevated']};
    color: {t['text_primary']};
    border: 1px solid {t['border_bright']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ─── Splitter ────────────────────────────────────────────── */
QSplitter::handle {{
    background: {t['border']};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}

/* ─── Menu Bar ────────────────────────────────────────────── */
QMenuBar {{
    background: {t['bg_secondary']};
    color: {t['text_primary']};
    border-bottom: 1px solid {t['border']};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background: {t['bg_elevated']};
    color: {t['accent']};
}}
QMenu {{
    background: {t['bg_elevated']};
    border: 1px solid {t['border_bright']};
    border-radius: 8px;
    padding: 6px 0;
}}
QMenu::item {{
    padding: 8px 24px 8px 16px;
    color: {t['text_primary']};
}}
QMenu::item:selected {{
    background: {t['accent']};
    color: #000;
}}
QMenu::separator {{
    height: 1px;
    background: {t['border']};
    margin: 4px 10px;
}}

/* ─── Label styles ────────────────────────────────────────── */
QLabel#sectionHeader {{
    font-size: 15px;
    font-weight: 700;
    color: {t['text_primary']};
    letter-spacing: 0.3px;
}}
QLabel#mutedLabel {{
    color: {t['text_muted']};
    font-size: 12px;
}}
QLabel#accentLabel {{
    color: {t['accent']};
    font-weight: 600;
}}
QLabel#realLabel {{
    color: {t['real_color']};
    font-weight: 700;
    font-size: 18px;
}}
QLabel#fakeLabel {{
    color: {t['fake_color']};
    font-weight: 700;
    font-size: 18px;
}}
QLabel#uncertainLabel {{
    color: {t['uncertain']};
    font-weight: 700;
    font-size: 18px;
}}
"""
