# DeepGuard AI Pro - Deepfake Detection Platform

A professional-grade deepfake detection platform with multi-provider AI fallback, modern UI, and offline capabilities.

<img width="583" height="342" alt="image" src="https://github.com/user-attachments/assets/f5f78c71-77f0-4c02-86b6-1408d043211b" />

<img width="1366" height="768" alt="image" src="https://github.com/user-attachments/assets/c725ca9b-a1eb-4f1c-8c43-45b66d1f0351" />


## 🌟 Features

### Multi-Provider AI Detection
- **Google Gemini 2.0** - Multimodal AI analysis (primary)
- **OpenAI GPT-4o** - Vision-capable AI fallback
- **Local CV Detector** - Offline traditional computer vision (edge analysis, noise patterns, frequency domain)

### Smart Failover System
- Automatic provider fallback when APIs are rate-limited
- Intelligent caching (1-hour TTL)
- Rate limit tracking with exponential cooldown
- No single point of failure

### Professional UI
- **3-Panel Dashboard Layout**: Input | Results | Analysis
- Modern dark theme with glassmorphism
- Animated confidence gauge
- Real-time progress tracking
- Provider status indicator

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/SAKingPlays/deepguard-ai.git
cd deepguard-ai

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Set your API keys (optional - local detector works offline):

```bash
# Option 1: Environment variables
export GEMINI_API_KEY="your-gemini-key"
export OPENAI_API_KEY="your-openai-key"

# Option 2: Edit src/config.py directly
```

### Run the Application

```bash
python main.py
```

## 📋 System Requirements

- **Python**: 3.10+ (3.11+ recommended)
- **OS**: Windows 10/11, macOS, Linux
- **RAM**: 4GB minimum, 8GB recommended
- **Internet**: Required for AI providers (local mode works offline)

## 🏗️ Architecture

```
DeepGuard AI Pro
├── src/
│   ├── detection/
│   │   ├── base_detector.py      # Abstract detector interface
│   │   ├── gemini_detector.py    # Google Gemini 2.0 integration
│   │   ├── openai_detector.py    # OpenAI GPT-4o integration
│   │   ├── local_detector.py     # Offline CV-based detection
│   │   └── detector_factory.py   # Smart provider management
│   ├── ui/
│   │   ├── modern_main_window.py # Professional 3-panel UI
│   │   ├── modern_widgets.py     # Reusable UI components
│   │   └── splash_screen.py      # Loading screen
│   ├── config.py                 # Configuration & API keys
│   └── utils/                    # Utilities
├── main.py                       # Entry point
└── requirements.txt              # Dependencies
```

## 🔧 Detection Methods

### AI-Based (Gemini 2.0 / GPT-4o)
- Natural language analysis of visual artifacts
- Facial feature inconsistency detection
- Lighting and shadow analysis
- Metadata verification

### Local CV-Based (Offline)
- **Edge Analysis**: Unnatural sharpness detection
- **Noise Patterns**: Uniform noise identification
- **Frequency Domain**: FFT compression artifact detection
- **Chroma Analysis**: Color channel inconsistencies
- **Face Detection**: Proportion validation

## 📊 Usage

1. **Load Media**: Drag & drop or browse for image/video
2. **Start Analysis**: Click "Start Analysis" button
3. **View Results**: 
   - Center panel: Confidence gauge + verdict
   - Right panel: Detailed analysis + indicators

The system automatically tries providers in order:
1. Gemini 2.0 → 2. GPT-4o → 3. Local CV (offline)

## 🔐 API Key Management

### Free Tier Limits
- **Gemini**: 60 requests/minute, 1,500 requests/day
- **OpenAI**: Rate limits vary by tier

### When Limits Exceeded
The app automatically falls back to the next available provider. If all AI providers fail, it uses the local CV detector which works 100% offline.

## 🛠️ Development

### Adding New Providers

Create a new detector class in `src/detection/`:

```python
from src.detection.base_detector import BaseDetector, DetectionResult

class MyDetector(BaseDetector):
    def load_model(self):
        # Initialize your API client
        pass
    
    def detect(self, filepath, progress_cb=None, cancel_flag=None):
        # Implement detection logic
        return DetectionResult(...)
```

Register in `detector_factory.py`:

```python
self._providers.append(MyDetector())
```

## 🙏 Acknowledgments

- Google Gemini API
- OpenAI GPT-4 Vision
- PyQt6 Framework
- OpenCV Computer Vision Library

## 📧 Contact

For support or inquiries: sakingplays@gmail.com

---

**⚠️ Disclaimer**: This tool is for educational and research purposes. Results may vary and should not be used as sole evidence for legal proceedings.
