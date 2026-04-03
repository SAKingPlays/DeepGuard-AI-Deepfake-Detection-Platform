"""Base detector class with shared interface."""
from __future__ import annotations
import abc
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from src.config import DEVICE

logger = logging.getLogger("deepguard")


@dataclass
class DetectionResult:
    """Unified detection result container."""
    media_type:       str              # image | video | audio
    filepath:         str
    is_fake:          bool
    confidence:       float            # 0-1  (probability of being FAKE)
    verdict:          str              # REAL | FAKE | UNCERTAIN
    verdict_color:    str
    analysis_details: dict             = field(default_factory=dict)
    frame_scores:     list[float]      = field(default_factory=list)
    heatmap_path:     Optional[str]    = None
    processing_time:  float            = 0.0
    model_used:       str              = ""
    error:            Optional[str]    = None
    explanation:      str              = ""

    @staticmethod
    def verdict_from_score(score: float,
                           high: float = 0.70,
                           low:  float = 0.35) -> tuple[str, str]:
        """Return (verdict_label, color_hex)."""
        if score >= high:
            return "FAKE",      "#FF3D57"
        elif score < low:
            return "REAL",      "#00E676"
        else:
            return "UNCERTAIN", "#FFB300"


class BaseDetector(abc.ABC):
    """Abstract base for all detectors."""

    def __init__(self, model_size: str = "standard"):
        self.model_size = model_size
        self.device     = DEVICE
        self.model      = None
        self._loaded    = False
        logger.debug(f"{self.__class__.__name__} created (device={self.device})")

    def ensure_loaded(self):
        if not self._loaded:
            self.load_model()
            self._loaded = True

    @abc.abstractmethod
    def load_model(self):
        """Load the AI model into memory."""

    @abc.abstractmethod
    def detect(self, filepath: str,
               progress_cb=None,
               cancel_flag: list = None) -> DetectionResult:
        """Run detection and return a DetectionResult."""

    def _timer(self):
        return time.perf_counter()
