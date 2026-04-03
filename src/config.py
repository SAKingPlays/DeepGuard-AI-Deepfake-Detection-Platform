"""Global configuration and constants."""
import os

# Lazy torch import to avoid DLL issues on startup
try:
    import torch
    _torch_available = True
except Exception:
    torch = None
    _torch_available = False

# ── Application Meta ──────────────────────────────────────────
APP_NAME    = "DeepGuard AI"
APP_VERSION = "2.0.0"
APP_AUTHOR  = "DeepGuard AI Labs"

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR  = os.path.join(BASE_DIR, "models")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CACHE_DIR   = os.path.join(BASE_DIR, ".cache")
LOGS_DIR    = os.path.join(BASE_DIR, "logs")
ASSETS_DIR  = os.path.join(BASE_DIR, "src", "assets")

for _dir in [MODELS_DIR, REPORTS_DIR, CACHE_DIR, LOGS_DIR]:
    os.makedirs(_dir, exist_ok=True)

# ── Device ────────────────────────────────────────────────────
if _torch_available and torch.cuda.is_available():
    DEVICE = "cuda"
    GPU_AVAILABLE = True
    GPU_NAME = torch.cuda.get_device_name(0)
else:
    DEVICE = "cpu"
    GPU_AVAILABLE = False
    GPU_NAME = "N/A"

# ── External API Keys ─────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ── Detection Thresholds ──────────────────────────────────────
DEFAULT_CONFIDENCE_THRESHOLD = 0.50
HIGH_CONFIDENCE_THRESHOLD    = 0.80
LOW_CONFIDENCE_THRESHOLD     = 0.30

# ── Model Sizes ───────────────────────────────────────────────
MODEL_SIZES = {
    "lightweight": {"description": "Fast, less accurate (CPU-friendly)", "params": "~5M"},
    "standard":    {"description": "Balanced speed/accuracy",            "params": "~25M"},
    "heavyweight": {"description": "Most accurate, GPU recommended",     "params": "~100M"},
}

# ── Video Processing ──────────────────────────────────────────
DEFAULT_FRAME_SAMPLE_RATE = 10   # every N frames
MAX_FRAMES_PER_VIDEO      = 500
VIDEO_BATCH_SIZE          = 16

# ── Audio Processing ──────────────────────────────────────────
AUDIO_SAMPLE_RATE    = 16000
AUDIO_SEGMENT_LENGTH = 3.0       # seconds

# ── UI Theme Colors (Dark Blue) ──────────────────────────────
THEME_DARK = {
    "bg_primary":   "#0A0F1A",  # Deep navy
    "bg_secondary": "#0F1629",  # Dark blue
    "bg_card":      "#141C33",  # Medium navy
    "bg_elevated":  "#1A2440",  # Elevated blue
    "accent":       "#4D9EFF",  # Bright blue
    "accent_dim":   "#3A7ACC",  # Medium blue
    "success":      "#4CAF50",  # Green
    "warning":      "#FFAB40",  # Orange
    "danger":       "#FF5252",  # Red
    "text_primary": "#E3F2FD",  # Light blue-white
    "text_secondary":"#90A4AE",  # Blue-gray
    "text_muted":   "#546E7A",  # Dark blue-gray
    "border":       "#1E3A5F",  # Navy border
    "border_bright":"#2E4A6F",  # Lighter navy
    "real_color":   "#4CAF50",  # Green
    "fake_color":   "#FF5252",  # Red
    "uncertain":    "#FFAB40",  # Orange
}

# ── UI Theme Colors (Light) ───────────────────────────────────
THEME_LIGHT = {
    "bg_primary":   "#F0F2F8",
    "bg_secondary": "#FFFFFF",
    "bg_card":      "#FFFFFF",
    "bg_elevated":  "#E8EBF2",
    "accent":       "#0066CC",
    "accent_dim":   "#0052A3",
    "success":      "#00A550",
    "warning":      "#E67700",
    "danger":       "#CC2233",
    "text_primary": "#1A1E2A",
    "text_secondary":"#4A5568",
    "text_muted":   "#8892A4",
    "border":       "#D0D5E0",
    "border_bright":"#A0AABB",
    "real_color":   "#00A550",
    "fake_color":   "#CC2233",
    "uncertain":    "#E67700",
}

# ── Supported File Formats ────────────────────────────────────
IMAGE_FORMATS = ["jpg", "jpeg", "png", "bmp", "tiff", "webp"]
VIDEO_FORMATS = ["mp4", "avi", "mov", "mkv", "wmv", "flv", "webm"]
AUDIO_FORMATS = ["wav", "mp3", "flac", "aac", "ogg", "m4a"]

IMAGE_FILTER = f"Images ({' '.join('*.' + f for f in IMAGE_FORMATS)})"
VIDEO_FILTER = f"Videos ({' '.join('*.' + f for f in VIDEO_FORMATS)})"
AUDIO_FILTER = f"Audio ({' '.join('*.' + f for f in AUDIO_FORMATS)})"
