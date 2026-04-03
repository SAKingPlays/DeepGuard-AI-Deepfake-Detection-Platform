"""Video detection tab with frame timeline."""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QSplitter, QGroupBox, QSlider,
    QSpinBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from src.ui.widgets import (
    DropZone, ConfidenceRing, VerdictBadge, StatCard,
    AnimatedProgressBar, HSeparator
)
from src.detection.video_detector import VideoDetector
from src.detection.workers import DetectionWorker
from src.config import VIDEO_FORMATS, VIDEO_FILTER


class FrameTimeline(QWidget):
    """Mini chart of per-frame detection scores."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scores: list[float] = []
        self.setMinimumHeight(80)
        self.setToolTip("Per-frame deepfake probability (red = suspicious, green = clean)")

    def set_scores(self, scores: list[float]):
        self._scores = scores
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Background
        p.fillRect(0, 0, w, h, QColor("#141720"))
        p.setPen(QPen(QColor("#252D3D"), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        if not self._scores:
            p.setPen(QPen(QColor("#4A5568")))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                       "Frame timeline — run analysis to populate")
            p.end()
            return

        # Threshold line at 0.5
        th_y = int(h * (1 - 0.5))
        p.setPen(QPen(QColor("#354060"), 1, Qt.PenStyle.DashLine))
        p.drawLine(0, th_y, w, th_y)

        # Bars
        n     = len(self._scores)
        bar_w = max(2, w // n)

        for i, score in enumerate(self._scores):
            bx  = int(i * w / n)
            bh  = int(score * (h - 4))
            by  = h - bh - 2
            bw  = max(2, int(w / n) - 1)

            r = int(255 * score)
            g = int(255 * (1 - score))
            col = QColor(r, g, 0, 200)
            p.fillRect(bx, by, bw, bh, col)

        # Labels
        p.setPen(QPen(QColor("#4A5568")))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(4, 12, "100%")
        p.drawText(4, h - 4, "0%")
        p.end()


class VideoTab(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, model_size_ref: list, parent=None):
        super().__init__(parent)
        self._model_size_ref = model_size_ref
        self._worker         = None
        self._last_result    = None
        self._current_file   = None
        self._setup_ui()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ── Left: input ──────────────────────────────────────────────
        left = QWidget()
        lv   = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        header = QLabel("🎬  Video Analysis")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #E8EAF0;")
        lv.addWidget(header)

        sub = QLabel("Analyzes video frames for temporal deepfake artifacts. "
                     "Supports MP4, AVI, MOV, MKV, WebM.")
        sub.setStyleSheet("color: #8892A4; font-size: 12px;")
        sub.setWordWrap(True)
        lv.addWidget(sub)

        self.drop_zone = DropZone(VIDEO_FORMATS,
                                   "Drop video here or click to browse")
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        lv.addWidget(self.drop_zone)

        # Settings
        settings_grp = QGroupBox("DETECTION SETTINGS")
        sg = QVBoxLayout(settings_grp)

        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("Sample every:"))
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(1, 100)
        self.sample_spin.setValue(10)
        self.sample_spin.setSuffix(" frames")
        self.sample_spin.setToolTip(
            "Analyze 1 frame out of every N. Lower = more thorough but slower.")
        sample_row.addWidget(self.sample_spin)
        sample_row.addStretch()
        sg.addLayout(sample_row)

        lv.addWidget(settings_grp)

        # File info panel
        info_frame = QFrame()
        info_frame.setStyleSheet(
            "QFrame { background: #1A1E2A; border: 1px solid #252D3D; "
            "border-radius: 8px; }")
        ifv = QVBoxLayout(info_frame)
        ifv.setContentsMargins(12, 10, 12, 10)
        self.file_info_label = QLabel("No file loaded")
        self.file_info_label.setStyleSheet("color: #8892A4; font-size: 12px;")
        self.file_info_label.setWordWrap(True)
        ifv.addWidget(self.file_info_label)
        lv.addWidget(info_frame)

        lv.addStretch()

        btn_row = QHBoxLayout()
        self.analyze_btn = QPushButton("▶  Analyze Video")
        self.analyze_btn.setObjectName("primaryBtn")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analysis)
        btn_row.addWidget(self.analyze_btn)

        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self.cancel_btn)

        clear_btn = QPushButton("🗑  Clear")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        lv.addLayout(btn_row)

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        lv.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #8892A4; font-size: 11px;")
        lv.addWidget(self.progress_label)

        left.setMinimumWidth(300)
        left.setMaximumWidth(440)

        # ── Right: results ───────────────────────────────────────────
        right = QWidget()
        rv    = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)

        res_header = QLabel("Detection Results")
        res_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        res_header.setStyleSheet("color: #E8EAF0;")
        rv.addWidget(res_header)

        # Top row
        top_row = QHBoxLayout()
        self.conf_ring = ConfidenceRing(size=150)
        top_row.addWidget(self.conf_ring)

        vbox = QVBoxLayout()
        self.verdict_badge = VerdictBadge()
        vbox.addWidget(self.verdict_badge)

        from PyQt6.QtWidgets import QGridLayout
        g = QGridLayout()
        g.setSpacing(8)
        self.stat_frames   = StatCard("Frames",     "–", "🎞", "#00D4FF")
        self.stat_duration = StatCard("Duration",   "–", "⏱", "#8892A4")
        self.stat_fps      = StatCard("FPS",        "–", "🎬", "#FFB300")
        self.stat_susp     = StatCard("Suspicious", "–", "⚠",  "#FF3D57")
        g.addWidget(self.stat_frames,   0, 0)
        g.addWidget(self.stat_duration, 0, 1)
        g.addWidget(self.stat_fps,      1, 0)
        g.addWidget(self.stat_susp,     1, 1)
        vbox.addLayout(g)
        vbox.addStretch()
        top_row.addLayout(vbox)
        rv.addLayout(top_row)

        rv.addWidget(HSeparator())

        # Frame timeline
        timeline_grp = QGroupBox("FRAME-LEVEL DETECTION TIMELINE")
        tg = QVBoxLayout(timeline_grp)
        self.timeline = FrameTimeline()
        tg.addWidget(self.timeline)
        rv.addWidget(timeline_grp)

        # Details + explanation
        details_grp = QGroupBox("ANALYSIS DETAILS")
        dg = QVBoxLayout(details_grp)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(100)
        self.details_text.setStyleSheet(
            "QTextEdit { background: #141720; border: none; "
            "color: #8892A4; font-size: 11px; font-family: 'Consolas', monospace; }")
        dg.addWidget(self.details_text)
        rv.addWidget(details_grp)

        explain_grp = QGroupBox("AI EXPLANATION")
        eg = QVBoxLayout(explain_grp)
        self.explain_text = QTextEdit()
        self.explain_text.setReadOnly(True)
        self.explain_text.setMaximumHeight(80)
        self.explain_text.setStyleSheet(
            "QTextEdit { background: #141720; border: none; "
            "color: #E8EAF0; font-size: 12px; }")
        eg.addWidget(self.explain_text)
        rv.addWidget(explain_grp)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([360, 620])
        root.addWidget(splitter)

    # ── Slots ──────────────────────────────────────────────────────

    def _on_files_dropped(self, files: list):
        if not files:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Video", "",
                VIDEO_FILTER + ";;All Files (*)"
            )
        if files:
            self._load_file(files[0])

    def _load_file(self, filepath: str):
        self._current_file = filepath
        self.drop_zone.set_file(filepath)
        self.analyze_btn.setEnabled(True)

        size_mb = os.path.getsize(filepath) / 1024 / 1024
        self.file_info_label.setText(
            f"📹  {os.path.basename(filepath)}\n"
            f"    Size: {size_mb:.1f} MB  •  "
            f"Path: {filepath}"
        )
        self.status_message.emit(f"Loaded: {os.path.basename(filepath)}")

    def _start_analysis(self):
        if not self._current_file:
            return
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._reset_results()

        detector = VideoDetector(model_size=self._model_size_ref[0])
        self._worker = DetectionWorker(
            detector, self._current_file,
            frame_rate=self.sample_spin.value()
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self.status_message.emit("Analyzing video…")

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._reset_state()
        self.status_message.emit("Analysis cancelled")

    def _clear(self):
        self._cancel()
        self._current_file = None
        self.drop_zone.clear()
        self.file_info_label.setText("No file loaded")
        self._reset_results()
        self.analyze_btn.setEnabled(False)

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def _on_result(self, result):
        self._last_result = result
        self._reset_state()

        self.conf_ring.set_value(
            result.confidence, result.verdict,
            f"{result.confidence*100:.0f}%", result.verdict_color
        )
        self.verdict_badge.set_verdict(result.verdict, result.verdict_color)

        ad = result.analysis_details
        self.stat_frames.set_value(str(ad.get("frames_analyzed", "–")))
        self.stat_duration.set_value(ad.get("duration", "–"))
        self.stat_fps.set_value(ad.get("fps", "–"))
        self.stat_susp.set_value(str(ad.get("suspicious_frames", "–")))

        if result.frame_scores:
            self.timeline.set_scores(result.frame_scores)

        lines = [f"  {k:<30} {v}" for k, v in ad.items()]
        self.details_text.setPlainText("\n".join(lines))
        self.explain_text.setPlainText(result.explanation or "–")

        self.status_message.emit(
            f"Done — {result.verdict} ({result.confidence*100:.1f}%) "
            f"in {result.processing_time:.1f}s"
        )

    def _on_error(self, msg: str):
        self._reset_state()
        self.details_text.setPlainText(f"Error: {msg}")
        self.status_message.emit(f"Error: {msg}")

    def _reset_results(self):
        self.conf_ring.set_value(0, "–", "", "#4A5568")
        self.verdict_badge.set_verdict("–", "#4A5568")
        for c in [self.stat_frames, self.stat_duration, self.stat_fps, self.stat_susp]:
            c.set_value("–")
        self.details_text.clear()
        self.explain_text.clear()
        self.timeline.set_scores([])

    def _reset_state(self):
        self.analyze_btn.setEnabled(bool(self._current_file))
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.progress_bar.setValue(0)

    def get_last_result(self):
        return self._last_result
