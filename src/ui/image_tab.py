"""Image detection tab."""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QSplitter, QFrame, QScrollArea,
    QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QFont

from src.ui.widgets import (
    DropZone, ConfidenceRing, VerdictBadge, StatCard,
    AnimatedProgressBar, HSeparator
)
from src.detection.image_detector import ImageDetector
from src.detection.workers import DetectionWorker
from src.config import IMAGE_FORMATS, IMAGE_FILTER, THEME_DARK


class ImageTab(QWidget):
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
        splitter.setHandleWidth(2)

        # ── Left panel: input ────────────────────────────────────────
        left = QWidget()
        lv   = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(12)

        header = QLabel("🖼  Image Analysis")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #E8EAF0;")
        lv.addWidget(header)

        sub = QLabel("Drop an image or click to browse. "
                     "Supports JPEG, PNG, BMP, TIFF, WebP.")
        sub.setStyleSheet("color: #8892A4; font-size: 12px;")
        sub.setWordWrap(True)
        lv.addWidget(sub)

        # Drop zone
        self.drop_zone = DropZone(IMAGE_FORMATS,
                                   "Drop image here or click to browse")
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        lv.addWidget(self.drop_zone)

        # Preview
        preview_frame = QFrame()
        preview_frame.setStyleSheet(
            "QFrame { background: #1A1E2A; border: 1px solid #252D3D; "
            "border-radius: 10px; }")
        pv = QVBoxLayout(preview_frame)
        pv.setContentsMargins(8, 8, 8, 8)

        self.preview_label = QLabel("Preview will appear here")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet("color: #4A5568; font-size: 12px;")
        pv.addWidget(self.preview_label)
        lv.addWidget(preview_frame)

        # Heatmap toggle
        hmap_row = QHBoxLayout()
        self.heatmap_label = QLabel("Attention Heatmap:")
        self.heatmap_label.setStyleSheet("color: #8892A4; font-size: 12px;")
        hmap_row.addWidget(self.heatmap_label)
        self.show_heatmap_btn = QPushButton("Show Heatmap")
        self.show_heatmap_btn.setEnabled(False)
        self.show_heatmap_btn.clicked.connect(self._toggle_heatmap)
        hmap_row.addWidget(self.show_heatmap_btn)
        hmap_row.addStretch()
        lv.addLayout(hmap_row)

        lv.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        self.analyze_btn = QPushButton("▶  Analyze Image")
        self.analyze_btn.setObjectName("primaryBtn")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analysis)
        self.analyze_btn.setToolTip("Run deepfake detection on the selected image")
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

        # Progress
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        lv.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #8892A4; font-size: 11px;")
        lv.addWidget(self.progress_label)

        left.setMinimumWidth(320)
        left.setMaximumWidth(480)

        # ── Right panel: results ─────────────────────────────────────
        right     = QWidget()
        rv        = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(12)

        res_header = QLabel("Detection Results")
        res_header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        res_header.setStyleSheet("color: #E8EAF0;")
        rv.addWidget(res_header)

        # Top row: ring + verdict + stats
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        self.conf_ring = ConfidenceRing(size=160)
        top_row.addWidget(self.conf_ring)

        right_stats = QVBoxLayout()
        right_stats.setSpacing(8)

        self.verdict_badge = VerdictBadge()
        right_stats.addWidget(self.verdict_badge)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(8)
        self.stat_faces   = StatCard("Faces",     "–", "👤", "#00D4FF")
        self.stat_size    = StatCard("Resolution","–", "📐", "#8892A4")
        self.stat_time    = StatCard("Time",      "–", "⏱", "#FFB300")
        self.stat_model   = StatCard("Model",     "–", "🤖", "#00D4FF")
        stats_grid.addWidget(self.stat_faces,  0, 0)
        stats_grid.addWidget(self.stat_size,   0, 1)
        stats_grid.addWidget(self.stat_time,   1, 0)
        stats_grid.addWidget(self.stat_model,  1, 1)
        right_stats.addLayout(stats_grid)
        right_stats.addStretch()

        top_row.addLayout(right_stats)
        rv.addLayout(top_row)

        rv.addWidget(HSeparator())

        # Analysis details
        details_grp = QGroupBox("ANALYSIS DETAILS")
        dg_layout   = QVBoxLayout(details_grp)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(130)
        self.details_text.setStyleSheet(
            "QTextEdit { background: #141720; border: none; "
            "color: #8892A4; font-size: 12px; font-family: 'Consolas', monospace; }")
        dg_layout.addWidget(self.details_text)
        rv.addWidget(details_grp)

        # AI Explanation
        explain_grp = QGroupBox("AI EXPLANATION")
        eg_layout   = QVBoxLayout(explain_grp)
        self.explain_text = QTextEdit()
        self.explain_text.setReadOnly(True)
        self.explain_text.setMaximumHeight(100)
        self.explain_text.setStyleSheet(
            "QTextEdit { background: #141720; border: none; "
            "color: #E8EAF0; font-size: 12px; line-height: 1.5; }")
        eg_layout.addWidget(self.explain_text)
        rv.addWidget(explain_grp)

        # Heatmap preview
        hmap_grp  = QGroupBox("ATTENTION HEATMAP")
        hg_layout = QVBoxLayout(hmap_grp)
        self.heatmap_preview = QLabel("Heatmap appears after analysis")
        self.heatmap_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_preview.setMinimumHeight(140)
        self.heatmap_preview.setStyleSheet(
            "color: #4A5568; background: #141720; border-radius: 6px;")
        hg_layout.addWidget(self.heatmap_preview)
        rv.addWidget(hmap_grp)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([380, 600])

        root.addWidget(splitter)

    # ── Slots ────────────────────────────────────────────────────────

    def _on_files_dropped(self, files: list):
        if not files:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Select Image", "",
                IMAGE_FILTER + ";;All Files (*)"
            )
        if files:
            self._load_file(files[0])

    def _load_file(self, filepath: str):
        self._current_file = filepath
        self.drop_zone.set_file(filepath)
        self.analyze_btn.setEnabled(True)

        # Show preview
        pix = QPixmap(filepath)
        if not pix.isNull():
            scaled = pix.scaled(
                self.preview_label.width() or 300,
                240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
        self.status_message.emit(f"Loaded: {os.path.basename(filepath)}")

    def _start_analysis(self):
        if not self._current_file:
            return

        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._reset_results()

        detector = ImageDetector(model_size=self._model_size_ref[0])
        self._worker = DetectionWorker(detector, self._current_file)
        self._worker.progress.connect(self._on_progress)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        self.status_message.emit("Analyzing image…")

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._reset_state()
        self.status_message.emit("Analysis cancelled")

    def _clear(self):
        self._cancel()
        self._current_file = None
        self.drop_zone.clear()
        self.preview_label.clear()
        self.preview_label.setText("Preview will appear here")
        self.heatmap_preview.clear()
        self.heatmap_preview.setText("Heatmap appears after analysis")
        self._reset_results()
        self.analyze_btn.setEnabled(False)
        self.show_heatmap_btn.setEnabled(False)

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(msg)

    def _on_result(self, result):
        self._last_result = result
        self._reset_state()

        # Ring
        self.conf_ring.set_value(
            result.confidence,
            result.verdict,
            f"{result.confidence*100:.0f}%",
            result.verdict_color
        )
        # Verdict badge
        self.verdict_badge.set_verdict(result.verdict, result.verdict_color)

        # Stats
        ad = result.analysis_details
        self.stat_faces.set_value(str(ad.get("faces_detected", "–")))
        self.stat_size.set_value(ad.get("image_size", "–"))
        self.stat_time.set_value(f"{result.processing_time:.2f}s")
        self.stat_model.set_value(result.model_used or "–")

        # Details text
        lines = [f"  {k:<28} {v}" for k, v in ad.items()]
        self.details_text.setPlainText("\n".join(lines))

        # Explanation
        self.explain_text.setPlainText(
            result.explanation or "No explanation available.")

        # Heatmap
        if result.heatmap_path and os.path.exists(result.heatmap_path):
            pix = QPixmap(result.heatmap_path)
            if not pix.isNull():
                scaled = pix.scaled(
                    self.heatmap_preview.width() or 400,
                    200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.heatmap_preview.setPixmap(scaled)
            self.show_heatmap_btn.setEnabled(True)

        v = result.verdict
        self.status_message.emit(
            f"Done — {v} ({result.confidence*100:.1f}% confidence) "
            f"in {result.processing_time:.2f}s")

    def _on_error(self, msg: str):
        self._reset_state()
        self.details_text.setPlainText(f"Error: {msg}")
        self.status_message.emit(f"Error: {msg}")

    def _toggle_heatmap(self):
        """Switch preview between original and heatmap."""
        if not self._last_result:
            return
        if self._showing_heatmap if hasattr(self, '_showing_heatmap') else False:
            pix = QPixmap(self._current_file)
            self.show_heatmap_btn.setText("Show Heatmap")
        else:
            pix = QPixmap(self._last_result.heatmap_path)
            self.show_heatmap_btn.setText("Show Original")
        self._showing_heatmap = not getattr(self, '_showing_heatmap', False)
        if not pix.isNull():
            self.preview_label.setPixmap(
                pix.scaled(300, 240, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation))

    def _reset_results(self):
        self.conf_ring.set_value(0, "–", "", "#4A5568")
        self.verdict_badge.set_verdict("–", "#4A5568")
        for c in [self.stat_faces, self.stat_size, self.stat_time, self.stat_model]:
            c.set_value("–")
        self.details_text.clear()
        self.explain_text.clear()

    def _reset_state(self):
        self.analyze_btn.setEnabled(bool(self._current_file))
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.progress_bar.setValue(0)

    def get_last_result(self):
        return self._last_result
