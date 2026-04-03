"""Audio / voice-clone detection tab."""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QSplitter, QGroupBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient

from src.ui.widgets import (
    DropZone, ConfidenceRing, VerdictBadge, StatCard,
    AnimatedProgressBar, HSeparator
)
from src.detection.audio_detector import AudioDetector
from src.detection.workers import DetectionWorker
from src.config import AUDIO_FORMATS, AUDIO_FILTER


class SpectrogramWidget(QWidget):
    """Displays a spectrogram image or placeholder."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setMinimumHeight(160)

    def set_image(self, path: str):
        from PyQt6.QtGui import QPixmap
        if path and os.path.exists(path):
            self._pixmap = QPixmap(path)
            self.update()

    def clear(self):
        self._pixmap = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#141720"))
        p.setPen(QPen(QColor("#252D3D")))
        p.drawRect(0, 0, w - 1, h - 1)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
        else:
            p.setPen(QPen(QColor("#4A5568")))
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter,
                       "Mel Spectrogram will appear after analysis")
        p.end()


class AudioFeatureBar(QWidget):
    """Horizontal bar showing feature scores."""

    def __init__(self, label: str, color: str = "#00D4FF", parent=None):
        super().__init__(parent)
        self._label = label
        self._color = QColor(color)
        self._value = 0.0
        self.setFixedHeight(32)

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # Label
        p.setPen(QPen(QColor("#8892A4")))
        p.setFont(QFont("Segoe UI", 10))
        lbl_w = 160
        p.drawText(0, 0, lbl_w, h, Qt.AlignmentFlag.AlignVCenter, self._label)

        # Track
        bar_x, bar_w_max = lbl_w + 8, w - lbl_w - 60
        bar_h, bar_y = 8, (h - 8) // 2
        p.setBrush(QBrush(QColor("#1F2535")))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w_max, bar_h, 4, 4)

        # Fill
        fill_w = int(bar_w_max * self._value)
        if fill_w > 0:
            grad = QLinearGradient(bar_x, 0, bar_x + bar_w_max, 0)
            grad.setColorAt(0, self._color.lighter(130))
            grad.setColorAt(1, self._color)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 4, 4)

        # Value text
        p.setPen(QPen(self._color))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(bar_x + bar_w_max + 6, 0, 50, h,
                   Qt.AlignmentFlag.AlignVCenter,
                   f"{self._value*100:.0f}%")
        p.end()


class AudioTab(QWidget):
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

        # ── Left panel ───────────────────────────────────────────────
        left = QWidget()
        lv   = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        header = QLabel("🎵  Audio Analysis")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #E8EAF0;")
        lv.addWidget(header)

        sub = QLabel("Detects voice cloning, TTS synthesis, and audio deepfakes "
                     "using spectral & prosodic analysis.")
        sub.setStyleSheet("color: #8892A4; font-size: 12px;")
        sub.setWordWrap(True)
        lv.addWidget(sub)

        self.drop_zone = DropZone(AUDIO_FORMATS,
                                   "Drop audio file here or click to browse")
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        lv.addWidget(self.drop_zone)

        # File info
        info_frame = QFrame()
        info_frame.setStyleSheet(
            "QFrame { background: #1A1E2A; border: 1px solid #252D3D; "
            "border-radius: 8px; }")
        ifv = QVBoxLayout(info_frame)
        ifv.setContentsMargins(12, 10, 12, 10)
        self.file_info = QLabel("No file loaded")
        self.file_info.setStyleSheet("color: #8892A4; font-size: 12px;")
        ifv.addWidget(self.file_info)
        lv.addWidget(info_frame)

        # Detection capabilities info
        caps_grp = QGroupBox("DETECTION CAPABILITIES")
        cg = QVBoxLayout(caps_grp)
        caps = [
            ("🎤", "Voice Cloning",    "Detects AI voice synthesis"),
            ("🤖", "TTS Detection",    "Text-to-speech identification"),
            ("📊", "Spectral Analysis","Frequency domain anomalies"),
            ("🎵", "Prosody Analysis", "Unnatural pitch patterns"),
            ("🔊", "Vocoder Artifacts","GAN/neural vocoder traces"),
        ]
        for icon, title, desc in caps:
            row = QHBoxLayout()
            row.addWidget(QLabel(icon))
            col = QVBoxLayout()
            col.setSpacing(0)
            t = QLabel(title)
            t.setStyleSheet("color: #E8EAF0; font-size: 12px; font-weight: 600;")
            d = QLabel(desc)
            d.setStyleSheet("color: #4A5568; font-size: 11px;")
            col.addWidget(t)
            col.addWidget(d)
            row.addLayout(col)
            row.addStretch()
            cg.addLayout(row)
        lv.addWidget(caps_grp)

        lv.addStretch()

        btn_row = QHBoxLayout()
        self.analyze_btn = QPushButton("▶  Analyze Audio")
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
        left.setMaximumWidth(420)

        # ── Right panel ───────────────────────────────────────────────
        right = QWidget()
        rv    = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)

        res_header = QLabel("Detection Results")
        res_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        res_header.setStyleSheet("color: #E8EAF0;")
        rv.addWidget(res_header)

        top_row = QHBoxLayout()
        self.conf_ring = ConfidenceRing(size=150)
        top_row.addWidget(self.conf_ring)

        vbox = QVBoxLayout()
        self.verdict_badge = VerdictBadge()
        vbox.addWidget(self.verdict_badge)

        from PyQt6.QtWidgets import QGridLayout
        g = QGridLayout()
        g.setSpacing(8)
        self.stat_dur    = StatCard("Duration",   "–", "⏱", "#00D4FF")
        self.stat_sr     = StatCard("Sample Rate","–", "📡", "#8892A4")
        self.stat_time   = StatCard("Proc. Time", "–", "⚡", "#FFB300")
        self.stat_model  = StatCard("Model",      "–", "🤖", "#00D4FF")
        g.addWidget(self.stat_dur,   0, 0)
        g.addWidget(self.stat_sr,    0, 1)
        g.addWidget(self.stat_time,  1, 0)
        g.addWidget(self.stat_model, 1, 1)
        vbox.addLayout(g)
        vbox.addStretch()
        top_row.addLayout(vbox)
        rv.addLayout(top_row)

        rv.addWidget(HSeparator())

        # Feature scores
        feat_grp = QGroupBox("FEATURE ANALYSIS SCORES")
        fg = QVBoxLayout(feat_grp)
        self._feat_bars: dict[str, AudioFeatureBar] = {}
        feats = [
            ("mfcc_anomaly",      "MFCC Anomaly",          "#FF3D57"),
            ("spectral_anomaly",  "Spectral Anomaly",       "#FF7B45"),
            ("prosody_score",     "Prosody Score",          "#FFB300"),
            ("phase_coherence",   "Phase Coherence",        "#00D4FF"),
            ("vocoder_artifacts", "Vocoder Artifacts",      "#C084FC"),
        ]
        for key, label, color in feats:
            bar = AudioFeatureBar(label, color)
            fg.addWidget(bar)
            self._feat_bars[key] = bar
        rv.addWidget(feat_grp)

        # Spectrogram
        spec_grp = QGroupBox("MEL SPECTROGRAM")
        sg_l = QVBoxLayout(spec_grp)
        self.spectrogram = SpectrogramWidget()
        sg_l.addWidget(self.spectrogram)
        rv.addWidget(spec_grp)

        # Explanation
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
        splitter.setSizes([340, 640])
        root.addWidget(splitter)

    # ── Slots ────────────────────────────────────────────────────────

    def _on_files_dropped(self, files: list):
        if not files:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Audio File", "",
                AUDIO_FILTER + ";;All Files (*)"
            )
        if files:
            self._load_file(files[0])

    def _load_file(self, filepath: str):
        self._current_file = filepath
        self.drop_zone.set_file(filepath)
        self.analyze_btn.setEnabled(True)
        size_kb = os.path.getsize(filepath) / 1024
        self.file_info.setText(
            f"🎵  {os.path.basename(filepath)}\n"
            f"    Size: {size_kb:.1f} KB"
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

        detector = AudioDetector(model_size=self._model_size_ref[0])
        self._worker = DetectionWorker(detector, self._current_file)
        self._worker.progress.connect(self._on_progress)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self.status_message.emit("Analyzing audio…")

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._reset_state()

    def _clear(self):
        self._cancel()
        self._current_file = None
        self.drop_zone.clear()
        self.file_info.setText("No file loaded")
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
        self.stat_dur.set_value(f"{ad.get('duration_s', '–')}s")
        self.stat_sr.set_value(ad.get("sample_rate", "–"))
        self.stat_time.set_value(f"{result.processing_time:.2f}s")
        self.stat_model.set_value(result.model_used or "–")

        for key, bar in self._feat_bars.items():
            try:
                bar.set_value(float(ad.get(key, 0)))
            except:
                pass

        if result.heatmap_path:
            self.spectrogram.set_image(result.heatmap_path)

        self.explain_text.setPlainText(result.explanation or "–")
        self.status_message.emit(
            f"Done — {result.verdict} ({result.confidence*100:.1f}%) "
            f"in {result.processing_time:.2f}s"
        )

    def _on_error(self, msg: str):
        self._reset_state()
        self.explain_text.setPlainText(f"Error: {msg}")
        self.status_message.emit(f"Error: {msg}")

    def _reset_results(self):
        self.conf_ring.set_value(0, "–", "", "#4A5568")
        self.verdict_badge.set_verdict("–", "#4A5568")
        for c in [self.stat_dur, self.stat_sr, self.stat_time, self.stat_model]:
            c.set_value("–")
        for bar in self._feat_bars.values():
            bar.set_value(0)
        self.spectrogram.clear()
        self.explain_text.clear()

    def _reset_state(self):
        self.analyze_btn.setEnabled(bool(self._current_file))
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.progress_bar.setValue(0)

    def get_last_result(self):
        return self._last_result
