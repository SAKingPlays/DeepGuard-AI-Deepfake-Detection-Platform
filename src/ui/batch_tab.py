"""Batch processing tab for multiple files."""
from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QListWidget, QListWidgetItem, QProgressBar,
    QGroupBox, QComboBox, QTextEdit, QSplitter, QFrame,
    QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QColor

from src.ui.widgets import (
    FileListItem, AnimatedProgressBar, StatCard, HSeparator
)
from src.detection.image_detector import ImageDetector
from src.detection.video_detector import VideoDetector
from src.detection.audio_detector import AudioDetector
from src.detection.workers import BatchDetectionWorker
from src.config import (
    IMAGE_FORMATS, VIDEO_FORMATS, AUDIO_FORMATS,
    IMAGE_FILTER, VIDEO_FILTER, AUDIO_FILTER
)


def _get_detector(filepath: str, model_size: str):
    ext = os.path.splitext(filepath)[1][1:].lower()
    if ext in IMAGE_FORMATS:
        return ImageDetector(model_size)
    elif ext in VIDEO_FORMATS:
        return VideoDetector(model_size)
    elif ext in AUDIO_FORMATS:
        return AudioDetector(model_size)
    return ImageDetector(model_size)


class BatchTab(QWidget):
    status_message = pyqtSignal(str)

    def __init__(self, model_size_ref: list, parent=None):
        super().__init__(parent)
        self._model_size_ref = model_size_ref
        self._worker         = None
        self._files: list[str] = []
        self._results        = []
        self._widgets: dict[str, FileListItem] = {}
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header
        header_row = QHBoxLayout()
        header = QLabel("📦  Batch Processing")
        header.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #E8EAF0;")
        header_row.addWidget(header)
        header_row.addStretch()

        add_btn = QPushButton("＋  Add Files")
        add_btn.clicked.connect(self._add_files)
        header_row.addWidget(add_btn)

        add_folder_btn = QPushButton("📁  Add Folder")
        add_folder_btn.clicked.connect(self._add_folder)
        header_row.addWidget(add_folder_btn)

        clear_btn = QPushButton("🗑  Clear All")
        clear_btn.clicked.connect(self._clear_all)
        header_row.addWidget(clear_btn)

        root.addLayout(header_row)

        sub = QLabel(
            "Process multiple images, videos, and audio files in one batch. "
            "Results are shown per-file and can be exported as a report."
        )
        sub.setStyleSheet("color: #8892A4; font-size: 12px;")
        sub.setWordWrap(True)
        root.addWidget(sub)

        # Summary stats row
        stats_row = QHBoxLayout()
        self.stat_total  = StatCard("Total Files", "0", "📄", "#00D4FF")
        self.stat_done   = StatCard("Completed",   "0", "✅", "#00E676")
        self.stat_fake   = StatCard("Fake Found",  "0", "🚫", "#FF3D57")
        self.stat_real   = StatCard("Authentic",   "0", "✔",  "#00E676")
        self.stat_errors = StatCard("Errors",       "0", "⚠",  "#FFB300")
        for c in [self.stat_total, self.stat_done, self.stat_fake,
                  self.stat_real, self.stat_errors]:
            stats_row.addWidget(c)
        root.addLayout(stats_row)

        # Splitter: file list left, log right
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list
        left_w = QWidget()
        lv = QVBoxLayout(left_w)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(6)

        lv.addWidget(QLabel("Files to Process:").setStyleSheet("color:#E8EAF0; font-weight:600;")
                     or QLabel("Files to Process:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: #1A1E2A; border: 1px solid #252D3D; "
            "border-radius: 8px; }")
        self.file_list_container = QWidget()
        self.file_list_layout    = QVBoxLayout(self.file_list_container)
        self.file_list_layout.setContentsMargins(4, 4, 4, 4)
        self.file_list_layout.setSpacing(2)
        self.file_list_layout.addStretch()
        scroll.setWidget(self.file_list_container)
        lv.addWidget(scroll, 1)

        self.empty_label = QLabel("No files added yet.\nClick 'Add Files' to get started.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            "color: #4A5568; font-size: 12px; padding: 40px;")

        # Right: log / results
        right_w = QWidget()
        rv = QVBoxLayout(right_w)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(6)

        log_lbl = QLabel("Processing Log:")
        log_lbl.setStyleSheet("color: #E8EAF0; font-weight: 600; font-size: 13px;")
        rv.addWidget(log_lbl)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "QTextEdit { background: #141720; border: 1px solid #252D3D; "
            "border-radius: 8px; color: #8892A4; font-size: 11px; "
            "font-family: 'Consolas', monospace; }")
        rv.addWidget(self.log_text, 1)

        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.setSizes([500, 380])
        root.addWidget(splitter, 1)

        # Bottom controls
        root.addWidget(HSeparator())
        bottom = QHBoxLayout()

        self.run_btn = QPushButton("▶  Run Batch Analysis")
        self.run_btn.setObjectName("primaryBtn")
        self.run_btn.setEnabled(False)
        self.run_btn.clicked.connect(self._start_batch)
        bottom.addWidget(self.run_btn)

        self.cancel_btn = QPushButton("✕  Cancel")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel)
        bottom.addWidget(self.cancel_btn)

        bottom.addStretch()

        # Export
        export_lbl = QLabel("Export:")
        export_lbl.setStyleSheet("color: #8892A4;")
        bottom.addWidget(export_lbl)

        self.export_pdf_btn = QPushButton("📄 PDF")
        self.export_pdf_btn.setEnabled(False)
        self.export_pdf_btn.clicked.connect(lambda: self._export("pdf"))
        bottom.addWidget(self.export_pdf_btn)

        self.export_csv_btn = QPushButton("📊 CSV")
        self.export_csv_btn.setEnabled(False)
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))
        bottom.addWidget(self.export_csv_btn)

        self.export_json_btn = QPushButton("{ } JSON")
        self.export_json_btn.setEnabled(False)
        self.export_json_btn.clicked.connect(lambda: self._export("json"))
        bottom.addWidget(self.export_json_btn)

        root.addLayout(bottom)

        # Progress
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #8892A4; font-size: 11px;")
        root.addWidget(self.progress_label)

    # ── File management ──────────────────────────────────────────────

    def _add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files", "",
            f"{IMAGE_FILTER};;{VIDEO_FILTER};;{AUDIO_FILTER};;All Files (*)"
        )
        for f in files:
            self._add_file(f)

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        all_exts = set(IMAGE_FORMATS + VIDEO_FORMATS + AUDIO_FORMATS)
        for root_d, _, fnames in os.walk(folder):
            for fname in fnames:
                ext = os.path.splitext(fname)[1][1:].lower()
                if ext in all_exts:
                    self._add_file(os.path.join(root_d, fname))

    def _add_file(self, filepath: str):
        if filepath in self._files:
            return
        self._files.append(filepath)

        item = FileListItem(filepath)
        item.remove_requested.connect(self._remove_file)
        self._widgets[filepath] = item

        # Remove stretch, add item, re-add stretch
        stretch = self.file_list_layout.takeAt(
            self.file_list_layout.count() - 1)
        self.file_list_layout.addWidget(item)
        self.file_list_layout.addStretch()

        self._update_counts()

    def _remove_file(self, filepath: str):
        if filepath in self._files:
            self._files.remove(filepath)
        if filepath in self._widgets:
            w = self._widgets.pop(filepath)
            self.file_list_layout.removeWidget(w)
            w.deleteLater()
        self._update_counts()

    def _clear_all(self):
        for fp in list(self._files):
            self._remove_file(fp)
        self._results.clear()
        self.log_text.clear()
        self._update_counts()

    def _update_counts(self):
        n = len(self._files)
        self.stat_total.set_value(str(n))
        self.run_btn.setEnabled(n > 0)

    # ── Batch processing ─────────────────────────────────────────────

    def _start_batch(self):
        if not self._files:
            return

        self.run_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._results.clear()

        self._done = 0
        self._fake = 0
        self._real = 0
        self._errs = 0
        self.stat_done.set_value("0")
        self.stat_fake.set_value("0")
        self.stat_real.set_value("0")
        self.stat_errors.set_value("0")

        ms = self._model_size_ref[0]
        def factory():
            # Will be called per-file, but model caches
            return None  # placeholder; worker handles this

        self._worker = _BatchWorkerWrapper(
            self._files, ms,
            lambda fp, r: self._on_file_done(fp, r),
            lambda i, n, fp: self._on_batch_progress(i, n, fp),
            lambda rs: self._on_batch_done(rs),
            lambda fp, e: self._on_file_error(fp, e),
        )
        self._worker.start()
        self._log("Batch started – processing %d files…" % len(self._files))

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._reset_state()
        self._log("Batch cancelled by user.")
        self.status_message.emit("Batch cancelled")

    def _on_batch_progress(self, done: int, total: int, filepath: str):
        pct = int(100 * done / total) if total else 0
        self.progress_bar.setValue(pct)
        self.progress_label.setText(
            f"Processing {done + 1}/{total}: {os.path.basename(filepath)}…")
        if filepath in self._widgets:
            self._widgets[filepath].set_status("processing")

    def _on_file_done(self, filepath: str, result):
        self._results.append(result)
        self._done += 1

        if result.error:
            self._errs += 1
            status, verdict = "error", f"Error"
        elif result.is_fake:
            self._fake += 1
            status, verdict = "fake", "FAKE"
        else:
            self._real += 1
            status, verdict = "done", "REAL"

        if filepath in self._widgets:
            self._widgets[filepath].set_status(status, verdict)

        self.stat_done.set_value(str(self._done))
        self.stat_fake.set_value(str(self._fake))
        self.stat_real.set_value(str(self._real))
        self.stat_errors.set_value(str(self._errs))

        self._log(
            f"  [{self._done}/{len(self._files)}]  "
            f"{os.path.basename(filepath)}  →  "
            f"{result.verdict}  ({result.confidence*100:.1f}%)"
        )

    def _on_file_error(self, filepath: str, error: str):
        self._errs += 1
        if filepath in self._widgets:
            self._widgets[filepath].set_status("error")
        self._log(f"  ERROR  {os.path.basename(filepath)}: {error}")

    def _on_batch_done(self, results):
        self._reset_state()
        self._enable_exports(True)
        self._log(
            f"\nBatch complete: {self._done} processed, "
            f"{self._fake} fake, {self._real} real, "
            f"{self._errs} errors."
        )
        self.status_message.emit(
            f"Batch done — {self._fake} fake / {self._real} real")

    def _export(self, fmt: str):
        from src.utils.report_generator import ReportGenerator
        if not self._results:
            return
        gen = ReportGenerator()
        try:
            if fmt == "pdf":
                path = gen.export_pdf(self._results)
            elif fmt == "csv":
                path = gen.export_csv(self._results)
            else:
                path = gen.export_json(self._results)
            self._log(f"Report exported: {path}")
            self.status_message.emit(f"Exported: {os.path.basename(path)}")
            # Open folder
            import subprocess
            subprocess.Popen(f'explorer /select,"{path}"')
        except Exception as e:
            self._log(f"Export error: {e}")

    def _log(self, msg: str):
        from datetime import datetime
        self.log_text.append(
            f"[{datetime.now().strftime('%H:%M:%S')}]  {msg}")

    def _reset_state(self):
        self.run_btn.setEnabled(len(self._files) > 0)
        self.cancel_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.progress_bar.setValue(0)

    def _enable_exports(self, enabled: bool):
        self.export_pdf_btn.setEnabled(enabled)
        self.export_csv_btn.setEnabled(enabled)
        self.export_json_btn.setEnabled(enabled)

    def get_results(self):
        return self._results


# ── Simple thread wrapper ─────────────────────────────────────────────
from PyQt6.QtCore import QThread, pyqtSignal as Signal

class _BatchWorkerWrapper(QThread):
    def __init__(self, files, model_size, on_done, on_progress, on_finished, on_error):
        super().__init__()
        self._files      = files
        self._ms         = model_size
        self._on_done    = on_done
        self._on_progress = on_progress
        self._on_finished = on_finished
        self._on_error   = on_error
        self._cancel     = [False]

    def cancel(self):
        self._cancel[0] = True

    def run(self):
        results = []
        for i, fp in enumerate(self._files):
            if self._cancel[0]:
                break
            self._on_progress(i, len(self._files), fp)
            try:
                from src.detection.image_detector import ImageDetector
                from src.detection.video_detector import VideoDetector
                from src.detection.audio_detector import AudioDetector
                from src.config import IMAGE_FORMATS, VIDEO_FORMATS, AUDIO_FORMATS

                ext = os.path.splitext(fp)[1][1:].lower()
                if ext in VIDEO_FORMATS:
                    det = VideoDetector(self._ms)
                elif ext in AUDIO_FORMATS:
                    det = AudioDetector(self._ms)
                else:
                    det = ImageDetector(self._ms)

                det.ensure_loaded()
                r = det.detect(fp, cancel_flag=self._cancel)
                results.append(r)
                self._on_done(fp, r)
            except Exception as e:
                self._on_error(fp, str(e))

        self._on_finished(results)
