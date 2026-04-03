"""Google Gemini 2.0 powered deepfake detector."""
from __future__ import annotations
import os
import time
import logging
import base64
from typing import Optional, Callable
from src.detection.base_detector import BaseDetector, DetectionResult

logger = logging.getLogger("deepguard")


class GeminiDetector(BaseDetector):
    """
    Deepfake detector using Google Gemini 2.0 multimodal AI.
    Analyzes images and video frames for synthetic media artifacts.
    """

    def __init__(self, model_size: str = "standard", api_key: Optional[str] = None):
        super().__init__(model_size)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
        self._model_name = "gemini-2.0-flash"

    def load_model(self):
        """Initialize Gemini API client."""
        try:
            import google.generativeai as genai
            
            if not self.api_key:
                raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY env var.")
            
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self._model_name)
            logger.info(f"Gemini model {self._model_name} initialized")
            
        except ImportError:
            logger.error("google-generativeai not installed. Run: pip install google-generativeai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    def detect(self, filepath: str, progress_cb: Optional[Callable] = None,
               cancel_flag: Optional[list] = None) -> DetectionResult:
        """Analyze media using Gemini 2.0 multimodal capabilities."""
        t0 = time.time()
        self.ensure_loaded()

        if progress_cb:
            progress_cb(10, "Loading media for Gemini analysis...")

        try:
            with open(filepath, "rb") as f:
                file_data = f.read()
            
            file_ext = os.path.splitext(filepath)[1].lower()
            is_video = file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            
            if progress_cb:
                progress_cb(30, "Preparing multimodal prompt...")

            prompt = self._create_analysis_prompt(is_video)
            
            if progress_cb:
                progress_cb(50, "Sending to Gemini 2.0...")

            if is_video:
                content = self._prepare_video_content(file_data, filepath)
            else:
                mime_type = f"image/{file_ext.replace('.', '').replace('jpg', 'jpeg')}"
                content = [prompt, {"mime_type": mime_type, "data": file_data}]

            response = self._client.generate_content(
                content,
                generation_config={"temperature": 0.1, "max_output_tokens": 1024}
            )

            if progress_cb:
                progress_cb(80, "Processing Gemini response...")

            result = self._parse_gemini_response(response.text, filepath)
            result.processing_time = time.time() - t0
            result.model_used = f"Gemini 2.0 ({self._model_name})"

            if progress_cb:
                progress_cb(100, "Analysis complete")

            return result

        except Exception as e:
            logger.error(f"Gemini detection failed: {e}")
            return DetectionResult(
                media_type="image",
                filepath=filepath,
                is_fake=False,
                confidence=0.0,
                verdict="ERROR",
                verdict_color="#FF5252",
                error=str(e),
                processing_time=time.time() - t0,
                model_used="Gemini 2.0 (error)"
            )

    def _create_analysis_prompt(self, is_video: bool) -> str:
        media_type = "video" if is_video else "image"
        return f"""Analyze this {media_type} for deepfake/synthetic media detection.

Look for: facial inconsistencies, lighting mismatches, artifacts, unnatural expressions, metadata issues.

Respond in format:
VERDICT: [REAL/FAKE/UNCERTAIN]
CONFIDENCE: [0-100]
ANALYSIS: [2-3 sentences]
INDICATORS: [features found]"""

    def _prepare_video_content(self, file_data: bytes, filepath: str) -> list:
        try:
            import cv2
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp.write(file_data)
                tmp_path = tmp.name
            
            cap = cv2.VideoCapture(tmp_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            mid_frame = total_frames // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
            ret, frame = cap.read()
            cap.release()
            os.unlink(tmp_path)
            
            if ret:
                _, encoded = cv2.imencode('.jpg', frame)
                return [
                    self._create_analysis_prompt(True) + f"\n(Frame {mid_frame}/{total_frames})",
                    {"mime_type": "image/jpeg", "data": encoded.tobytes()}
                ]
        except Exception as e:
            logger.warning(f"Video extraction failed: {e}")
        
        return [self._create_analysis_prompt(True)]

    def _parse_gemini_response(self, text: str, filepath: str) -> DetectionResult:
        import re
        text = text.strip()
        
        verdict = "UNCERTAIN"
        if "VERDICT: FAKE" in text.upper():
            verdict = "FAKE"
        elif "VERDICT: REAL" in text.upper():
            verdict = "REAL"
        
        confidence = 0.5
        if match := re.search(r'CONFIDENCE:\s*(\d+)', text):
            confidence = int(match.group(1)) / 100.0
        
        colors = {"FAKE": "#FF5252", "REAL": "#4CAF50", "UNCERTAIN": "#FFAB40", "ERROR": "#FF5252"}
        
        analysis = ""
        if match := re.search(r'ANALYSIS:\s*(.+?)(?=INDICATORS:|$)', text, re.DOTALL):
            analysis = match.group(1).strip()
        
        indicators = []
        if match := re.search(r'INDICATORS:\s*(.+?)$', text, re.MULTILINE):
            indicators = [i.strip() for i in match.group(1).split(',')]
        
        return DetectionResult(
            media_type="image",
            filepath=filepath,
            is_fake=verdict == "FAKE",
            confidence=confidence,
            verdict=verdict,
            verdict_color=colors.get(verdict, "#FFAB40"),
            analysis_details={"indicators": indicators, "raw_response": text[:500]},
            explanation=analysis,
            processing_time=0
        )
