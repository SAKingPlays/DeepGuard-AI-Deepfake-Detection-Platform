"""Animated splash screen."""
from PyQt6.QtWidgets import QSplashScreen, QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont, QLinearGradient, QBrush, QPen


class SplashScreen(QSplashScreen):
    """Animated splash screen shown at startup."""

    def __init__(self):
        from PyQt6.QtGui import QPixmap
        pm = QPixmap(580, 340)
        pm.fill(QColor("#0D0F14"))
        super().__init__(pm, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self._progress = 0
        self._msg = "Initializing…"
        self._dot_count = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

        self._steps = [
            (10, "Loading core modules…"),
            (25, "Initializing AI engine…"),
            (45, "Checking GPU availability…"),
            (60, "Loading detection models…"),
            (75, "Preparing media processors…"),
            (88, "Building UI components…"),
            (96, "Finalizing…"),
            (100, "Ready!"),
        ]
        self._step_idx = 0
        self._step_timer = QTimer(self)
        self._step_timer.timeout.connect(self._advance_step)
        self._step_timer.start(300)

    def _tick(self):
        self._dot_count = (self._dot_count + 1) % 4
        self.repaint()

    def _advance_step(self):
        if self._step_idx < len(self._steps):
            self._progress, self._msg = self._steps[self._step_idx]
            self._step_idx += 1
            self.repaint()
        else:
            self._step_timer.stop()

    def drawContents(self, painter: QPainter):
        w, h = self.width(), self.height()

        # Background gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor("#0D0F14"))
        grad.setColorAt(1.0, QColor("#141720"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # Decorative lines
        painter.setPen(QPen(QColor("#252D3D"), 1))
        for i in range(0, w, 40):
            painter.setOpacity(0.3)
            painter.drawLine(i, 0, i, h)
        for i in range(0, h, 40):
            painter.drawLine(0, i, w, i)
        painter.setOpacity(1.0)

        # Accent bar at top
        grad2 = QLinearGradient(0, 0, w, 0)
        grad2.setColorAt(0, QColor("#00D4FF"))
        grad2.setColorAt(0.5, QColor("#0099BB"))
        grad2.setColorAt(1, QColor("#00D4FF"))
        painter.fillRect(0, 0, w, 3, QBrush(grad2))

        # Logo area
        painter.setPen(QPen(QColor("#00D4FF")))
        painter.setFont(QFont("Segoe UI", 36, QFont.Weight.Black))
        painter.drawText(0, 60, w, 70, Qt.AlignmentFlag.AlignCenter, "DeepGuard AI")

        painter.setPen(QPen(QColor("#8892A4")))
        painter.setFont(QFont("Segoe UI", 12))
        painter.drawText(0, 118, w, 28, Qt.AlignmentFlag.AlignCenter,
                         "Universal Deepfake Detection Platform  •  v2.0")

        # Divider
        painter.setPen(QPen(QColor("#252D3D"), 1))
        painter.drawLine(60, 160, w - 60, 160)

        # Status message
        dots = "." * (self._dot_count + 1)
        msg = self._msg.rstrip("…") + (dots if self._msg.endswith("…") else "")
        painter.setPen(QPen(QColor("#8892A4")))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(40, 178, w - 80, 26, Qt.AlignmentFlag.AlignLeft, msg)

        # Progress bar track
        bar_y = 218
        bar_h = 6
        bar_x, bar_w = 40, w - 80
        painter.setBrush(QBrush(QColor("#1F2535")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

        # Progress bar fill
        fill_w = int(bar_w * self._progress / 100)
        if fill_w > 0:
            grad3 = QLinearGradient(bar_x, 0, bar_x + bar_w, 0)
            grad3.setColorAt(0.0, QColor("#00D4FF"))
            grad3.setColorAt(1.0, QColor("#0066AA"))
            painter.setBrush(QBrush(grad3))
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

        # Progress percent
        painter.setPen(QPen(QColor("#4A5568")))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(bar_x + bar_w + 8, bar_y - 2, 40, bar_h + 4,
                         Qt.AlignmentFlag.AlignLeft, f"{self._progress}%")

        # Footer
        painter.setPen(QPen(QColor("#2A3040")))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(0, h - 28, w, 22, Qt.AlignmentFlag.AlignCenter,
                         "© 2024 DeepGuard AI Labs  •  GPU-Accelerated  •  Multi-Modal Detection")
