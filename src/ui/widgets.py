"""Custom reusable UI widgets."""
import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QProgressBar, QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QMimeData, QThread, pyqtProperty, QSize
)
from PyQt6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPixmap,
    QDragEnterEvent, QDropEvent, QPainterPath, QLinearGradient
)
from src.config import THEME_DARK, IMAGE_FORMATS, VIDEO_FORMATS, AUDIO_FORMATS


# ── Animated Confidence Ring ──────────────────────────────────
class ConfidenceRing(QWidget):
    """Animated circular confidence gauge."""

    def __init__(self, parent=None, size: int = 160):
        super().__init__(parent)
        self._value    = 0.0
        self._target   = 0.0
        self._color    = QColor("#00D4FF")
        self._label    = "–"
        self._sublabel = ""
        self._sz       = size
        self.setFixedSize(size, size)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._step)

    def set_value(self, value: float, label: str = "", sublabel: str = "",
                  color: str = "#00D4FF"):
        self._target   = max(0.0, min(1.0, value))
        self._label    = label
        self._sublabel = sublabel
        self._color    = QColor(color)
        self._anim_timer.start(16)

    def _step(self):
        diff = self._target - self._value
        if abs(diff) < 0.005:
            self._value = self._target
            self._anim_timer.stop()
        else:
            self._value += diff * 0.12
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        sz, val = self._sz, self._value

        # Track
        margin = 14
        rect_f = self.rect().adjusted(margin, margin, -margin, -margin)
        pen = QPen(QColor("#1F2535"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(rect_f, 225 * 16, -270 * 16)

        # Value arc
        if val > 0:
            grad = QLinearGradient(0, 0, sz, 0)
            grad.setColorAt(0.0, self._color.lighter(130))
            grad.setColorAt(1.0, self._color)
            pen2 = QPen(QBrush(grad), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            p.setPen(pen2)
            p.drawArc(rect_f, 225 * 16, int(-270 * val * 16))

        # Centre text
        p.setPen(QPen(QColor("#E8EAF0")))
        pct = f"{int(val * 100)}%"
        font = QFont("Segoe UI", int(sz * 0.13), QFont.Weight.Bold)
        p.setFont(font)
        p.drawText(self.rect().adjusted(0, -14, 0, -14), Qt.AlignmentFlag.AlignCenter, pct)

        if self._label:
            font2 = QFont("Segoe UI", int(sz * 0.075), QFont.Weight.Bold)
            p.setFont(font2)
            p.setPen(QPen(self._color))
            p.drawText(self.rect().adjusted(0, int(sz * 0.12), 0, 0),
                       Qt.AlignmentFlag.AlignCenter, self._label)

        if self._sublabel:
            font3 = QFont("Segoe UI", int(sz * 0.06))
            p.setFont(font3)
            p.setPen(QPen(QColor("#8892A4")))
            p.drawText(self.rect().adjusted(0, int(sz * 0.26), 0, 0),
                       Qt.AlignmentFlag.AlignCenter, self._sublabel)
        p.end()


# ── Drag-and-Drop Zone ────────────────────────────────────────
class DropZone(QWidget):
    """Drag-and-drop file input zone."""
    files_dropped = pyqtSignal(list)

    def __init__(self, accept_types: list[str], hint_text: str = "Drop files here",
                 parent=None):
        super().__init__(parent)
        self._accept = accept_types
        self._hint   = hint_text
        self._hover  = False
        self._has_file = False
        self._filename = ""
        self.setAcceptDrops(True)
        self.setMinimumHeight(160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_file(self, filename: str):
        self._has_file = True
        self._filename = os.path.basename(filename)
        self.update()

    def clear(self):
        self._has_file = False
        self._filename = ""
        self.update()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            self._hover = True
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._hover = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self._hover = False
        urls = [u.toLocalFile() for u in event.mimeData().urls()
                if u.isLocalFile()]
        valid = [u for u in urls
                 if any(u.lower().endswith(f".{ext}") for ext in self._accept)]
        if valid:
            self.files_dropped.emit(valid)
        self.update()

    def mousePressEvent(self, event):
        self.files_dropped.emit([])  # Signal for browse dialog

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        bg = QColor("#1A1E2A") if not self._hover else QColor("#1F2535")
        p.setBrush(QBrush(bg))
        accent = QColor("#00D4FF")
        pen = QPen(accent if self._hover else QColor("#252D3D"),
                   2, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRoundedRect(4, 4, w - 8, h - 8, 12, 12)

        if self._has_file:
            p.setPen(QPen(QColor("#00D4FF")))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       f"📄  {self._filename}")
        else:
            # Icon placeholder area
            cx, cy = w // 2, h // 2 - 18
            icon_col = QColor("#00D4FF") if self._hover else QColor("#4A5568")
            p.setPen(QPen(icon_col, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Arrow down icon
            p.drawLine(cx, cy - 14, cx, cy + 10)
            p.drawLine(cx - 10, cy, cx, cy + 10)
            p.drawLine(cx + 10, cy, cx, cy + 10)
            p.drawLine(cx - 16, cy + 14, cx + 16, cy + 14)

            p.setPen(QPen(QColor("#8892A4")))
            p.setFont(QFont("Segoe UI", 11))
            p.drawText(0, cy + 22, w, 28, Qt.AlignmentFlag.AlignCenter, self._hint)
            p.setFont(QFont("Segoe UI", 10))
            p.setPen(QPen(QColor("#4A5568")))
            exts = ", ".join(f".{e}" for e in self._accept[:6])
            p.drawText(0, cy + 44, w, 24, Qt.AlignmentFlag.AlignCenter,
                       f"Supports: {exts}")
        p.end()


# ── Verdict Badge ─────────────────────────────────────────────
class VerdictBadge(QWidget):
    """Large verdict display widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self._verdict = "–"
        self._color   = "#8892A4"

    def set_verdict(self, verdict: str, color: str):
        self._verdict = verdict.upper()
        self._color   = color
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        col = QColor(self._color)
        p.setBrush(QBrush(col.darker(300)))
        p.setPen(QPen(col, 2))
        p.drawRoundedRect(0, 0, w, h, 10, 10)
        p.setPen(QPen(col))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._verdict)
        p.end()


# ── Stat Card ─────────────────────────────────────────────────
class StatCard(QFrame):
    """A small card showing a key metric."""

    def __init__(self, title: str, value: str = "–",
                 icon: str = "", color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet(f"""
            QFrame#statCard {{
                background: #1A1E2A;
                border: 1px solid #252D3D;
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(14, 12, 14, 12)

        top = QHBoxLayout()
        if icon:
            ico = QLabel(icon)
            ico.setStyleSheet(f"font-size: 20px; color: {color};")
            top.addWidget(ico)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: #8892A4; font-size: 11px; font-weight: 600; "
                                "letter-spacing: 0.5px; text-transform: uppercase;")
        top.addWidget(title_lbl)
        top.addStretch()
        layout.addLayout(top)

        self.value_lbl = QLabel(value)
        self.value_lbl.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 700; "
            f"letter-spacing: -0.5px;")
        layout.addWidget(self.value_lbl)

    def set_value(self, val: str):
        self.value_lbl.setText(val)


# ── Animated Progress Bar ─────────────────────────────────────
class AnimatedProgressBar(QProgressBar):
    def __init__(self, color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._color = color
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1A1E2A;
                border: 1px solid #252D3D;
                border-radius: 8px;
                height: 12px;
                text-align: center;
                font-size: 10px;
                font-weight: 700;
                color: #E8EAF0;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 {QColor(color).darker(120).name()});
                border-radius: 7px;
            }}
        """)

    def set_color(self, color: str):
        self._color = color
        darker = QColor(color).darker(120).name()
        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: #1A1E2A;
                border: 1px solid #252D3D;
                border-radius: 8px;
                height: 12px;
                text-align: center;
                font-size: 10px;
                font-weight: 700;
                color: #E8EAF0;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 {darker});
                border-radius: 7px;
            }}
        """)


# ── File List Item ────────────────────────────────────────────
class FileListItem(QWidget):
    """Rich file item for batch list."""
    remove_requested = pyqtSignal(str)

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.status   = "pending"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        ext = os.path.splitext(filepath)[1][1:].lower()
        icon_map = {
            **{e: "🖼️" for e in IMAGE_FORMATS},
            **{e: "🎬" for e in VIDEO_FORMATS},
            **{e: "🎵" for e in AUDIO_FORMATS},
        }
        ico = QLabel(icon_map.get(ext, "📄"))
        ico.setFixedWidth(24)
        layout.addWidget(ico)

        name = QLabel(os.path.basename(filepath))
        name.setStyleSheet("color: #E8EAF0; font-size: 12px;")
        name.setToolTip(filepath)
        layout.addWidget(name, 1)

        size_bytes = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        size_str = (f"{size_bytes/1024:.1f} KB" if size_bytes < 1024*1024
                    else f"{size_bytes/1024/1024:.1f} MB")
        size_lbl = QLabel(size_str)
        size_lbl.setStyleSheet("color: #8892A4; font-size: 11px; min-width: 70px;")
        layout.addWidget(size_lbl)

        self.status_lbl = QLabel("⏳ Pending")
        self.status_lbl.setStyleSheet("color: #8892A4; font-size: 11px; min-width: 100px;")
        layout.addWidget(self.status_lbl)

        rm = QPushButton("✕")
        rm.setFixedSize(26, 26)
        rm.setStyleSheet("""QPushButton { background: #252D3D; color: #8892A4;
            border: none; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background: #FF3D57; color: white; }""")
        rm.clicked.connect(lambda: self.remove_requested.emit(filepath))
        layout.addWidget(rm)

    def set_status(self, status: str, verdict: str = ""):
        icons = {"pending": ("⏳", "#8892A4"), "processing": ("⚡", "#00D4FF"),
                 "done": ("✅", "#00E676"), "fake": ("🚫", "#FF3D57"),
                 "error": ("❌", "#FF3D57")}
        ico, col = icons.get(status, ("⏳", "#8892A4"))
        text = f"{ico} {verdict or status.capitalize()}"
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"color: {col}; font-size: 11px; min-width: 100px; "
                                      f"font-weight: 600;")


# ── Separator ─────────────────────────────────────────────────
class HSeparator(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setStyleSheet("color: #252D3D; max-height: 1px;")


# ── Pulsing Status Dot ────────────────────────────────────────
class StatusDot(QWidget):
    def __init__(self, color: str = "#00E676", size: int = 12, parent=None):
        super().__init__(parent)
        self._color  = QColor(color)
        self._alpha  = 255
        self._up     = False
        self.setFixedSize(size, size)
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._pulse)

    def start_pulse(self):
        self._timer.start(30)

    def stop_pulse(self):
        self._timer.stop()
        self._alpha = 255
        self.update()

    def _pulse(self):
        self._alpha += -6 if self._up else 6
        if self._alpha <= 80:
            self._up = False
        elif self._alpha >= 255:
            self._up = True
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        col = QColor(self._color)
        col.setAlpha(self._alpha)
        p.setBrush(QBrush(col))
        p.setPen(Qt.PenStyle.NoPen)
        r = self.width() // 2 - 1
        cx, cy = self.width() // 2, self.height() // 2
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        p.end()
