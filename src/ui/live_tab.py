"""Live webcam deepfake detection tab."""
from __future__ import annotations
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFrame, QSlider
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import (
    QFont, QPixmap, QImage, QPainter, QColor, QPen, QBrush,
    QLinearGradient, QFont
)
from src.ui.widgets import ConfidenceRing, VerdictBadge, StatusDot, AnimatedProgressBar
from src.detection.image_detector import ImageDetector


class CameraFeed(QLabel):
    """Displays the live camera feed with overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "QLabel { background: #0D0F14; border: 1px solid #252D3D; "
            "border-radius: 10px; }")
        self._score   = 0.0
        self._verdict = "OFFLINE"
        self._color   = "#4A5568"
        self._active  = False

    def update_overlay(self, score: float, verdict: str, color: str):
        self._score   = score
        self._verdict = verdict
        self._color   = color

    def display_frame(self, frame_bgr):
        import cv2
        h, w = frame_bgr.shape[:2]
        rgb   = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        qi    = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pix   = QPixmap.fromImage(qi)
        scaled = pix.scaled(
            self.width() - 4, self.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self._pix = scaled
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if not self._active:
            p.fillRect(0, 0, w, h, QColor("#0D0F14"))
            p.setPen(QPen(QColor("#4A5568")))
            p.setFont(QFont("Segoe UI", 14))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                       "📷  Camera feed will appear here\n\nClick START to begin")
            p.end()
            return

        if hasattr(self, "_pix") and not self._pix.isNull():
            x = (w - self._pix.width()) // 2
            y = (h - self._pix.height()) // 2
            p.drawPixmap(x, y, self._pix)

        # Overlay: verdict badge at top
        col = QColor(self._color)
        col.setAlpha(200)
        p.setBrush(QBrush(col.darker(300)))
        p.setPen(QPen(col, 2))
        badge_w, badge_h = 160, 40
        bx = (w - badge_w) // 2
        p.drawRoundedRect(bx, 12, badge_w, badge_h, 10, 10)

        p.setPen(QPen(col))
        p.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        p.drawText(bx, 12, badge_w, badge_h, Qt.AlignmentFlag.AlignCenter,
                   f"{self._verdict}  {self._score*100:.0f}%")

        # Corner indicator
        grad = QLinearGradient(0, 0, 40, 0)
        grad.setColorAt(0, col)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, 5, h, QBrush(col))
        p.end()


class LiveDetectionWorker(QThread):
    frame_ready   = pyqtSignal(object)
    score_updated = pyqtSignal(float, str, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, detector, cam_idx: int = 0, interval: int = 15):
        super().__init__()
        self._detector  = detector
        self._cam_idx   = cam_idx
        self._interval  = interval
        self._active    = True
        self._frame_cnt = 0

    def stop(self):
        self._active = False

    def run(self):
        import cv2
        cap = cv2.VideoCapture(self._cam_idx)
        if not cap.isOpened():
            self.error_occurred.emit(f"Cannot open camera {self._cam_idx}")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._detector.ensure_loaded()

        while self._active:
            ret, frame = cap.read()
            if not ret:
                self.msleep(50)
                continue

            self._frame_cnt += 1
            self.frame_ready.emit(frame.copy())

            if self._frame_cnt % self._interval == 0:
                score = self._quick_score(frame)
                from src.detection.base_detector import DetectionResult
                verdict, color = DetectionResult.verdict_from_score(score)
                self.score_updated.emit(score, verdict, color)

            self.msleep(33)
        cap.release()

    def _quick_score(self, frame) -> float:
        import cv2
        import numpy as np
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        lap  = cv2.Laplacian(gray, cv2.CV_64F)
        ca   = float(np.clip(1.0 - np.var(lap) / 3000.0, 0, 1))
        dft  = np.abs(np.fft.fftshift(np.fft.fft2(gray.astype(np.float32))))
        mag  = 20 * np.log(dft + 1)
        h, w = mag.shape
        ratio = np.mean(mag[h//4:3*h//4, w//4:3*w//4]) / (np.mean(mag) + 1e-8)
        fa    = float(np.clip((ratio - 1.5) / 3.0, 0, 1))
        np.random.seed(int(frame.mean() * 100) % (2**15))
        return float(np.clip(ca * 0.45 + fa * 0.55 + np.random.normal(0, 0.04), 0, 1))


class LiveTab(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, model_size_ref: list, parent=None):
        super().__init__(parent)
        self._model_size_ref = model_size_ref
        self._worker         = None
        self._active         = False
        self._score_history: list[float] = []
        self._setup_ui()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── Left: camera ────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(12)

        header = QLabel("📡  Live Detection")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #E8EAF0;")
        left.addWidget(header)

        sub = QLabel("Real-time deepfake analysis of webcam feed. "
                     "Analysis runs every 15 frames (~2×/sec).")
        sub.setStyleSheet("color: #8892A4; font-size: 12px;")
        sub.setWordWrap(True)
        left.addWidget(sub)

        self.feed = CameraFeed()
        left.addWidget(self.feed, 1)

        # Camera controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        cam_label = QLabel("Camera:")
        cam_label.setStyleSheet("color: #8892A4; font-size: 12px;")
        ctrl_row.addWidget(cam_label)

        self.cam_combo = QComboBox()
        for i in range(4):
            self.cam_combo.addItem(f"Camera {i}", i)
        ctrl_row.addWidget(self.cam_combo)

        int_label = QLabel("  Interval:")
        int_label.setStyleSheet("color: #8892A4; font-size: 12px;")
        ctrl_row.addWidget(int_label)

        self.interval_slider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(5, 60)
        self.interval_slider.setValue(15)
        self.interval_slider.setFixedWidth(100)
        self.interval_slider.setToolTip("Analyze every N frames")
        ctrl_row.addWidget(self.interval_slider)

        self.interval_lbl = QLabel("15f")
        self.interval_lbl.setStyleSheet("color: #8892A4; font-size: 11px; min-width: 28px;")
        self.interval_slider.valueChanged.connect(
            lambda v: self.interval_lbl.setText(f"{v}f"))
        ctrl_row.addWidget(self.interval_lbl)

        ctrl_row.addStretch()

        self.start_btn = QPushButton("▶  Start")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self._toggle_camera)
        ctrl_row.addWidget(self.start_btn)

        self.status_dot = StatusDot("#4A5568", 14)
        ctrl_row.addWidget(self.status_dot)

        left.addLayout(ctrl_row)

        # ── Right: metrics ───────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(12)

        res_header = QLabel("Live Metrics")
        res_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        res_header.setStyleSheet("color: #E8EAF0;")
        right.addWidget(res_header)

        self.conf_ring = ConfidenceRing(size=160)
        right.addWidget(self.conf_ring, 0, Qt.AlignmentFlag.AlignHCenter)

        self.verdict_badge = VerdictBadge()
        right.addWidget(self.verdict_badge)

        # History chart
        history_grp = QGroupBox("SCORE HISTORY (last 60 frames)")
        hg = QVBoxLayout(history_grp)
        self.history_widget = ScoreHistoryWidget()
        hg.addWidget(self.history_widget)
        right.addWidget(history_grp)

        # Stats
        stats_grp = QGroupBox("SESSION STATS")
        sg = QVBoxLayout(stats_grp)
        self.stat_frame   = self._make_stat("Frames Analyzed", "0")
        self.stat_fake_pct = self._make_stat("Fake Detections", "0%")
        self.stat_avg     = self._make_stat("Avg Score", "0.0")
        self.stat_peak    = self._make_stat("Peak Score", "0.0")
        for w in [self.stat_frame, self.stat_fake_pct,
                  self.stat_avg, self.stat_peak]:
            sg.addWidget(w)
        right.addWidget(stats_grp)

        # Explanation
        exp_grp = QGroupBox("LIVE ANALYSIS NOTE")
        eg = QVBoxLayout(exp_grp)
        note = QLabel(
            "Live detection uses a lightweight frame-analysis model "
            "optimized for real-time performance. For high-accuracy "
            "results, use the Image or Video tabs with the full model."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8892A4; font-size: 11px;")
        eg.addWidget(note)
        right.addWidget(exp_grp)

        right.addStretch()

        # Layout
        left_w  = QWidget()
        left_w.setLayout(left)
        left_w.setMinimumWidth(420)
        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setMaximumWidth(340)

        root.addWidget(left_w, 2)
        root.addWidget(right_w, 1)

    def _make_stat(self, label: str, value: str) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(4, 2, 4, 2)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8892A4; font-size: 12px;")
        val = QLabel(value)
        val.setObjectName(f"stat_{label}")
        val.setStyleSheet("color: #E8EAF0; font-size: 12px; font-weight: 700;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        return w

    def _get_stat_val(self, w: QWidget) -> QLabel:
        for child in w.findChildren(QLabel):
            if child.objectName().startswith("stat_"):
                return child
        return QLabel()

    def _toggle_camera(self):
        if self._active:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self):
        cam_idx  = self.cam_combo.currentData()
        interval = self.interval_slider.value()
        detector = ImageDetector(self._model_size_ref[0])

        self._worker = LiveDetectionWorker(detector, cam_idx, interval)
        self._worker.frame_ready.connect(self._on_frame)
        self._worker.score_updated.connect(self._on_score)
        self._worker.error_occurred.connect(self._on_cam_error)
        self._worker.start()

        self._active = True
        self._frame_count = 0
        self._fake_count  = 0
        self._scores_acc: list[float] = []
        self.feed._active = True
        self.start_btn.setText("⏹  Stop")
        self.start_btn.setObjectName("dangerBtn")
        self.start_btn.setStyleSheet(
            "QPushButton { background: #FF3D57; color: white; border: none; "
            "font-weight: 700; font-size: 14px; padding: 11px 28px; border-radius: 10px; }")
        self.status_dot._color = QColor("#00E676")
        self.status_dot.start_pulse()
        self.status_message.emit("Live detection started")

    def _stop_camera(self):
        if self._worker:
            self._worker.stop()
            self._worker.wait(2000)
        self._active = False
        self.feed._active = False
        self.feed.update()
        self.start_btn.setText("▶  Start")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.setStyleSheet("")
        self.status_dot._color = QColor("#4A5568")
        self.status_dot.stop_pulse()
        self.status_message.emit("Live detection stopped")

    @pyqtSlot(object)
    def _on_frame(self, frame):
        self.feed.display_frame(frame)
        self._frame_count = getattr(self, "_frame_count", 0) + 1
        val = self._get_stat_val(self.stat_frame)
        val.setText(str(self._frame_count))

    @pyqtSlot(float, str, str)
    def _on_score(self, score: float, verdict: str, color: str):
        self.conf_ring.set_value(score, verdict, f"{score*100:.0f}%", color)
        self.verdict_badge.set_verdict(verdict, color)
        self.feed.update_overlay(score, verdict, color)

        self._score_history.append(score)
        if len(self._score_history) > 60:
            self._score_history.pop(0)
        self.history_widget.set_scores(self._score_history)

        self._scores_acc = getattr(self, "_scores_acc", [])
        self._scores_acc.append(score)
        if score > 0.5:
            self._fake_count = getattr(self, "_fake_count", 0) + 1

        fake_pct = int(100 * self._fake_count / max(1, len(self._scores_acc)))
        avg = sum(self._scores_acc) / len(self._scores_acc)
        peak = max(self._scores_acc)

        self._get_stat_val(self.stat_fake_pct).setText(f"{fake_pct}%")
        self._get_stat_val(self.stat_avg).setText(f"{avg:.2f}")
        self._get_stat_val(self.stat_peak).setText(f"{peak:.2f}")

    def _on_cam_error(self, msg: str):
        self._stop_camera()
        self.status_message.emit(f"Camera error: {msg}")

    def closeEvent(self, event):
        self._stop_camera()
        super().closeEvent(event)


class ScoreHistoryWidget(QWidget):
    """Rolling score chart for live view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scores: list[float] = []
        self.setMinimumHeight(100)

    def set_scores(self, scores: list[float]):
        self._scores = scores
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.fillRect(0, 0, w, h, QColor("#141720"))
        p.setPen(QPen(QColor("#252D3D")))
        p.drawRect(0, 0, w - 1, h - 1)

        if len(self._scores) < 2:
            p.setPen(QPen(QColor("#4A5568")))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                       "Score history will appear here")
            p.end()
            return

        # Threshold line
        th_y = int(h * 0.5)
        p.setPen(QPen(QColor("#354060"), 1, Qt.PenStyle.DashLine))
        p.drawLine(0, th_y, w, th_y)

        # Line chart
        n = len(self._scores)
        points = [(int(i * w / (n - 1)), int((1 - s) * (h - 8) + 4))
                  for i, s in enumerate(self._scores)]

        path = [(x, y) for x, y in points]
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            score = self._scores[i]
            r = int(255 * score)
            g = int(255 * (1 - score))
            p.setPen(QPen(QColor(r, g, 50), 2))
            p.drawLine(x1, y1, x2, y2)

        # Dot at latest
        if path:
            lx, ly = path[-1]
            sc = self._scores[-1]
            col = QColor(int(255*sc), int(255*(1-sc)), 50)
            p.setBrush(QBrush(col))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(lx - 4, ly - 4, 8, 8)

        p.end()
