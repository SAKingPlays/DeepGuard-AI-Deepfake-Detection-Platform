"""OpenAI GPT-4 Vision powered deepfake detector."""
from __future__ import annotations
import os
import time
import logging
import base64
from typing import Optional, Callable
from src.detection.base_detector import BaseDetector, DetectionResult

logger = logging.getLogger("deepguard")


class OpenAIDetector(BaseDetector):
    """
    Deepfake detector using OpenAI GPT-4 Vision.
    Analyzes images for synthetic media artifacts.
    """

    def __init__(self, model_size: str = "standard", api_key: Optional[str] = None):
        super().__init__(model_size)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        self._model = "gpt-4o"  # GPT-4o has vision capabilities

    def load_model(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            
            if not self.api_key:
                raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY env var.")
            
            self._client = OpenAI(api_key=self.api_key)
            logger.info(f"OpenAI client initialized with model {self._model}")
            
        except ImportError:
            logger.error("openai not installed. Run: pip install openai")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    def detect(self, filepath: str, progress_cb: Optional[Callable] = None,
               cancel_flag: Optional[list] = None) -> DetectionResult:
        """Analyze media using GPT-4 Vision."""
        t0 = time.time()
        self.ensure_loaded()

        if progress_cb:
            progress_cb(10, "Loading image for OpenAI analysis...")

        try:
            # Read and encode image
            with open(filepath, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            file_ext = os.path.splitext(filepath)[1].lower().replace('.', '')
            if file_ext == 'jpg':
                file_ext = 'jpeg'
            
            if progress_cb:
                progress_cb(30, "Sending to GPT-4 Vision...")

            # Create the vision request
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert deepfake detection analyst. Analyze images for signs of AI generation or manipulation."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze this image for deepfake/synthetic media detection.

Look for these indicators:
1. Unnatural facial features (eyes, teeth, hair, skin texture)
2. Inconsistent lighting and shadows
3. Background artifacts or distortions
4. Unnatural expressions or proportions
5. AI-generated artifacts (repeated patterns, smoothing)

Respond in this exact format:

VERDICT: [REAL/FAKE/UNCERTAIN]
CONFIDENCE: [0-100]
ANALYSIS: [2-3 sentences explaining your reasoning]
INDICATORS: [comma-separated list of suspicious features, or "None detected"]"""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{file_ext};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )

            if progress_cb:
                progress_cb(80, "Processing GPT-4 response...")

            # Parse response
            result_text = response.choices[0].message.content
            result = self._parse_response(result_text, filepath)
            result.processing_time = time.time() - t0
            result.model_used = f"OpenAI GPT-4o"

            if progress_cb:
                progress_cb(100, "Analysis complete")

            return result

        except Exception as e:
            logger.error(f"OpenAI detection failed: {e}")
            return DetectionResult(
                media_type="image",
                filepath=filepath,
                is_fake=False,
                confidence=0.0,
                verdict="ERROR",
                verdict_color="#FF5252",
                error=str(e),
                processing_time=time.time() - t0,
                model_used="OpenAI GPT-4o (error)"
            )

    def _parse_response(self, text: str, filepath: str) -> DetectionResult:
        """Parse GPT-4 response into DetectionResult."""
        import re
        text = text.strip()
        
        # Extract verdict
        verdict = "UNCERTAIN"
        if "VERDICT: FAKE" in text.upper():
            verdict = "FAKE"
        elif "VERDICT: REAL" in text.upper():
            verdict = "REAL"
        
        # Extract confidence
        confidence = 0.5
        if match := re.search(r'CONFIDENCE:\s*(\d+)', text):
            confidence = int(match.group(1)) / 100.0
        
        # Colors
        colors = {"FAKE": "#FF5252", "REAL": "#4CAF50", "UNCERTAIN": "#FFAB40"}
        
        # Extract analysis
        analysis = ""
        if match := re.search(r'ANALYSIS:\s*(.+?)(?=INDICATORS:|$)', text, re.DOTALL):
            analysis = match.group(1).strip()
        
        # Extract indicators
        indicators = []
        if match := re.search(r'INDICATORS:\s*(.+?)$', text, re.MULTILINE):
            indicators = [i.strip() for i in match.group(1).split(',') if i.strip()]
        
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
