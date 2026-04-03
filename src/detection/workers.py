"""Background worker threads for non-blocking detection."""
from __future__ import annotations
import logging
from PyQt6.QtCore import QThread, pyqtSignal
from src.detection.base_detector import DetectionResult

logger = logging.getLogger("deepguard")


class DetectionWorker(QThread):
    """Run a single-file detection in a background thread."""
    progress   = pyqtSignal(int, str)     # (percent, message)
    result_ready = pyqtSignal(object)     # DetectionResult
    error      = pyqtSignal(str)

    def __init__(self, detector, filepath: str, **kwargs):
        super().__init__()
        self._detector   = detector
        self._filepath   = filepath
        self._kwargs     = kwargs
        self._cancel     = [False]

    def cancel(self):
        self._cancel[0] = True

    def run(self):
        try:
            self._detector.ensure_loaded()
            result = self._detector.detect(
                self._filepath,
                progress_cb  = lambda p, m: self.progress.emit(p, m),
                cancel_flag  = self._cancel,
                **self._kwargs,
            )
            self.result_ready.emit(result)
        except Exception as e:
            logger.error(f"DetectionWorker error: {e}", exc_info=True)
            self.error.emit(str(e))


class BatchDetectionWorker(QThread):
    """Process multiple files sequentially."""
    file_progress  = pyqtSignal(int, str)       # per-file progress
    file_done      = pyqtSignal(str, object)    # (filepath, DetectionResult)
    batch_progress = pyqtSignal(int, int, str)  # (done, total, current_file)
    finished_all   = pyqtSignal(list)           # list[DetectionResult]
    error          = pyqtSignal(str, str)       # (filepath, error_msg)

    def __init__(self, detector_factory, files: list[str], **kwargs):
        super().__init__()
        self._factory  = detector_factory
        self._files    = files
        self._kwargs   = kwargs
        self._cancel   = [False]

    def cancel(self):
        self._cancel[0] = True

    def run(self):
        results = []
        for i, fp in enumerate(self._files):
            if self._cancel[0]:
                break

            self.batch_progress.emit(i, len(self._files), fp)
            try:
                detector = self._factory()
                detector.ensure_loaded()
                res = detector.detect(
                    fp,
                    progress_cb = lambda p, m: self.file_progress.emit(p, m),
                    cancel_flag = self._cancel,
                    **self._kwargs,
                )
                results.append(res)
                self.file_done.emit(fp, res)
            except Exception as e:
                logger.error(f"Batch error on {fp}: {e}")
                self.error.emit(fp, str(e))

        self.finished_all.emit(results)


class WebcamWorker(QThread):
    """Continuous webcam frame analysis."""
    frame_ready   = pyqtSignal(object, float)   # (np.ndarray, score)
    score_updated = pyqtSignal(float, str, str)  # (score, verdict, color)

    def __init__(self, detector, camera_idx: int = 0):
        super().__init__()
        self._detector   = detector
        self._cam_idx    = camera_idx
        self._active     = True
        self._interval   = 15   # analyze every N frames

    def stop(self):
        self._active = False

    def run(self):
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(self._cam_idx)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self._detector.ensure_loaded()
        frame_count = 0

        while self._active:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % self._interval == 0:
                score = self._quick_score(frame)
                verdict, color = DetectionResult.verdict_from_score(score)
                self.score_updated.emit(score, verdict, color)

            self.frame_ready.emit(frame.copy(), 0.0)
            self.msleep(33)  # ~30fps

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
        fa   = float(np.clip((ratio - 1.5) / 3.0, 0, 1))
        np.random.seed(int(frame[0, 0, 0]) * 997 + frame_count % 1000
                       if False else 42)
        return float(np.clip(ca * 0.45 + fa * 0.55 + np.random.normal(0, 0.04), 0, 1))
