"""Local offline deepfake detector using traditional CV methods."""
from __future__ import annotations
import os
import time
import logging
from typing import Optional, Callable
import numpy as np
from src.detection.base_detector import BaseDetector, DetectionResult

logger = logging.getLogger("deepguard")


class LocalDetector(BaseDetector):
    """
    Offline deepfake detector using traditional computer vision techniques.
    No API calls required - works completely offline.
    Uses: edge analysis, noise patterns, compression artifacts, facial proportions.
    """

    def __init__(self, model_size: str = "standard"):
        super().__init__(model_size)
        self._face_cascade = None

    def load_model(self):
        """Load OpenCV face detector."""
        try:
            import cv2
            # Load OpenCV's built-in face detector
            self._face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            logger.info("Local CV detector loaded (offline mode)")
        except Exception as e:
            logger.warning(f"Could not load face detector: {e}")
            self._face_cascade = None

    def _preprocess_image(self, img):
        """Preprocess image for better detection."""
        import cv2
        
        # Resize if too large (maintain aspect ratio)
        max_dim = 1024
        h, w = img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Enhance contrast
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        img = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return img

    def detect(self, filepath: str, progress_cb: Optional[Callable] = None,
               cancel_flag: Optional[list] = None) -> DetectionResult:
        """Analyze image using traditional CV methods."""
        t0 = time.time()
        self.ensure_loaded()

        if progress_cb:
            progress_cb(10, "Loading and preprocessing image...")

        try:
            import cv2
            from PIL import Image
            import numpy as np
            from scipy import fftpack
            
            # Load image
            img = cv2.imread(filepath)
            if img is None:
                raise ValueError(f"Could not load image: {filepath}")
            
            # Preprocess
            img = self._preprocess_image(img)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            if progress_cb:
                progress_cb(25, "Analyzing edges and textures...")
            
            # 1. Edge analysis (unnatural sharpness = AI)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
            # AI images often have unnaturally sharp edges
            edge_score = min(1.0, edge_density * 2.5)
            
            if progress_cb:
                progress_cb(40, "Checking noise patterns...")
            
            # 2. Noise analysis (AI images often have uniform or absent noise)
            noise = gray.astype(np.float32) - cv2.GaussianBlur(gray.astype(np.float32), (5, 5), 0)
            noise_variance = np.var(noise)
            noise_mean = np.mean(np.abs(noise))
            
            # Natural images have varied noise patterns
            # AI images: very low noise (<10) or unnaturally uniform noise
            if noise_variance < 15:
                noise_score = 0.8  # Likely AI (too smooth)
            elif noise_variance > 100:
                noise_score = 0.2  # Likely real (high natural noise)
            else:
                noise_score = 0.5 + (noise_variance - 15) / 170  # Gradual scale
            
            if progress_cb:
                progress_cb(55, "Analyzing frequency domain...")
            
            # 3. Frequency analysis (FFT for compression artifacts and AI patterns)
            f_transform = fftpack.fft2(gray.astype(np.float32))
            f_shift = fftpack.fftshift(f_transform)
            magnitude = np.abs(f_shift)
            
            # Check for unnatural frequency patterns
            h, w = magnitude.shape
            center_region = magnitude[h//4:3*h//4, w//4:3*w//4]
            outer_region = np.concatenate([
                magnitude[:h//4, :].flatten(),
                magnitude[3*h//4:, :].flatten(),
                magnitude[h//4:3*h//4, :w//4].flatten(),
                magnitude[h//4:3*h//4, 3*w//4:].flatten()
            ])
            
            # Natural images have more high-frequency content in outer regions
            freq_ratio = np.mean(center_region) / (np.mean(outer_region) + 1e-8)
            # AI images often lack high frequency detail
            if freq_ratio > 2.0:
                freq_score = 0.7  # Likely AI (lacking detail)
            elif freq_ratio < 1.2:
                freq_score = 0.3  # Likely real (good detail)
            else:
                freq_score = (freq_ratio - 1.2) / 0.8 * 0.4 + 0.3
            
            if progress_cb:
                progress_cb(70, "Checking compression artifacts...")
            
            # 4. JPEG artifact and chroma analysis
            yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            chroma_u = yuv[:,:,1].astype(np.float32)
            chroma_v = yuv[:,:,2].astype(np.float32)
            
            # Check for chroma inconsistencies (common in AI images)
            chroma_variance = np.var(chroma_u) + np.var(chroma_v)
            chroma_edge_u = cv2.Sobel(chroma_u, cv2.CV_64F, 1, 1).var()
            chroma_edge_v = cv2.Sobel(chroma_v, cv2.CV_64F, 1, 1).var()
            
            # AI images often have unnatural chroma patterns
            if chroma_variance < 100 and chroma_edge_u < 50:
                chroma_score = 0.75  # Likely AI
            else:
                chroma_score = 0.4
            
            if progress_cb:
                progress_cb(85, "Analyzing facial proportions...")
            
            # 5. Face detection and analysis
            face_score = 0.5  # Neutral if no face
            faces_found = 0
            if self._face_cascade is not None:
                faces = self._face_cascade.detectMultiScale(gray, 1.1, 4)
                faces_found = len(faces)
                if faces_found > 0:
                    (x, y, w, h) = faces[0]
                    face_ratio = h / w
                    # Typical face ratio is 1.3-1.5
                    face_score = 1.0 - abs(face_ratio - 1.4) / 1.0
                    face_score = max(0, min(1, face_score))
            
            if progress_cb:
                progress_cb(95, "Calculating final score...")
            
            # 6. Additional: Check for repetitive patterns (common in AI)
            # Use local binary patterns or texture analysis
            from skimage.feature import local_binary_pattern
            radius = 3
            n_points = 8 * radius
            lbp = local_binary_pattern(gray, n_points, radius, method='uniform')
            lbp_hist, _ = np.histogram(lbp.ravel(), bins=n_points + 2, range=(0, n_points + 2))
            lbp_hist = lbp_hist.astype(np.float32)
            lbp_hist /= (lbp_hist.sum() + 1e-8)
            
            # High uniformity in LBP histogram suggests AI generation
            lbp_entropy = -np.sum(lbp_hist * np.log2(lbp_hist + 1e-8))
            if lbp_entropy < 3.0:
                texture_score = 0.75  # Uniform = likely AI
            else:
                texture_score = 0.35
            
            # Combine scores (weighted average)
            # Weights tuned for better accuracy
            final_score = (
                edge_score * 0.20 +
                noise_score * 0.20 +
                freq_score * 0.15 +
                chroma_score * 0.15 +
                face_score * 0.10 +
                texture_score * 0.20
            )
            
            # Add calibration based on image characteristics
            # High resolution images with faces need stricter thresholds
            img_area = img.shape[0] * img.shape[1]
            if img_area > 1000000 and faces_found > 0:
                # High-res portrait - be more conservative
                threshold_fake = 0.60
                threshold_real = 0.40
            else:
                threshold_fake = 0.55
                threshold_real = 0.45
            
            # Determine verdict with calibrated thresholds
            if final_score > threshold_fake:
                verdict = "FAKE"
                color = "#FF5252"
            elif final_score < threshold_real:
                verdict = "REAL"
                color = "#4CAF50"
            else:
                verdict = "UNCERTAIN"
                color = "#FFAB40"
            
            # Build explanation
            indicators = []
            if edge_score > 0.65:
                indicators.append("Unnatural edge sharpness")
            if noise_score > 0.60:
                indicators.append("Uniform or absent noise patterns")
            if freq_score > 0.60:
                indicators.append("Lack of high-frequency detail")
            if chroma_score > 0.65:
                indicators.append("Chroma inconsistencies")
            if texture_score > 0.65:
                indicators.append("Repetitive texture patterns")
            if face_score < 0.3 and faces_found > 0:
                indicators.append("Unusual facial proportions")
            
            explanation = f"""Local CV analysis completed. 
Scores: Edge={edge_score:.2f}, Noise={noise_score:.2f}, Freq={freq_score:.2f}, Chroma={chroma_score:.2f}, Texture={texture_score:.2f}
{len(indicators)} suspicious indicators detected.
{'; '.join(indicators) if indicators else 'No strong indicators of manipulation.'}"""
            
            if progress_cb:
                progress_cb(100, "Analysis complete")
            
            return DetectionResult(
                media_type="image",
                filepath=filepath,
                is_fake=verdict == "FAKE",
                confidence=final_score,
                verdict=verdict,
                verdict_color=color,
                analysis_details={
                    "indicators": indicators,
                    "edge_score": round(edge_score, 3),
                    "noise_score": round(noise_score, 3),
                    "freq_score": round(freq_score, 3),
                    "chroma_score": round(chroma_score, 3),
                    "face_score": round(face_score, 3),
                    "texture_score": round(texture_score, 3),
                    "faces_detected": faces_found,
                    "thresholds_used": f"FAKE>{threshold_fake}, REAL<{threshold_real}"
                },
                explanation=explanation,
                processing_time=time.time() - t0,
                model_used="Local CV (Offline)"
            )

        except Exception as e:
            logger.error(f"Local detection failed: {e}")
            return DetectionResult(
                media_type="image",
                filepath=filepath,
                is_fake=False,
                confidence=0.5,
                verdict="ERROR",
                verdict_color="#FF5252",
                error=str(e),
                processing_time=time.time() - t0,
                model_used="Local CV (error)"
            )
