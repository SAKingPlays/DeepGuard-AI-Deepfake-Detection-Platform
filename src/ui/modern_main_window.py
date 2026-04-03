"""Professional 3-panel MainWindow for DeepGuard AI - Modern Dashboard Layout."""
from __future__ import annotations
import os
import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSplitter, QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox,
    QProgressBar, QFrame, QSizePolicy, QScrollArea, QStackedWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QAction, QKeySequence, QColor

from src.ui.modern_widgets import (
    CardWidget, MetricCard, MediaDropZone, ConfidenceGauge,
    ModernButton, LoadingSkeleton, AnalysisPanel
)
from src.config import APP_NAME, APP_VERSION, THEME_DARK, GEMINI_API_KEY, OPENAI_API_KEY
from src.detection.detector_factory import get_detector_factory, SmartDetectorFactory
from src.detection.workers import DetectionWorker

logger = logging.getLogger("deepguard")


class ModernMainWindow(QMainWindow):
    """Professional 3-panel layout: Left (Input), Center (Results), Right (Details)."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} Pro v{APP_VERSION}")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        self._current_file = None
        self._worker = None
        self._factory = get_detector_factory()
        
        self._setup_ui()
        self._setup_menu()
        self._setup_statusbar()
        self._apply_global_styles()
        
        # Show available providers
        self._show_provider_status()
    
    def _setup_ui(self):
        """Build the 3-panel professional layout."""
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main horizontal layout with 3 panels
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # === LEFT PANEL: Media Input (25% width) ===
        self.left_panel = self._create_left_panel()
        main_layout.addWidget(self.left_panel, 25)
        
        # === CENTER PANEL: Primary Results (35% width) ===
        self.center_panel = self._create_center_panel()
        main_layout.addWidget(self.center_panel, 35)
        
        # === RIGHT PANEL: Detailed Analysis (40% width) ===
        self.right_panel = self._create_right_panel()
        main_layout.addWidget(self.right_panel, 40)
    
    def _create_left_panel(self) -> QWidget:
        """Create left media input panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("📁 Media Input")
        header.setStyleSheet(f"""
            color: {THEME_DARK['text_primary']};
            font-size: 20px;
            font-weight: 700;
        """)
        layout.addWidget(header)
        
        # Media drop zone card
        self.media_card = CardWidget(title="Upload Media")
        self.drop_zone = MediaDropZone(
            accepted_formats=['jpg', 'jpeg', 'png', 'mp4', 'avi', 'mov'],
            placeholder="Drop image or video here"
        )
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.media_card.add_widget(self.drop_zone)
        layout.addWidget(self.media_card)
        
        # File info card
        self.file_info_card = CardWidget(title="File Information")
        self.file_info_card.setMaximumHeight(150)
        self.file_info_text = QLabel("No file loaded")
        self.file_info_text.setWordWrap(True)
        self.file_info_text.setStyleSheet(f"color: {THEME_DARK['text_secondary']};")
        self.file_info_card.add_widget(self.file_info_text)
        layout.addWidget(self.file_info_card)
        
        # Action buttons
        self.action_card = CardWidget()
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(12)
        
        self.analyze_btn = ModernButton("▶  Start Analysis", variant="primary")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._start_analysis)
        btn_layout.addWidget(self.analyze_btn)
        
        self.clear_btn = ModernButton("🗑  Clear", variant="secondary")
        self.clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self.clear_btn)
        
        self.action_card.add_layout(btn_layout)
        layout.addWidget(self.action_card)
        
        # Progress bar
        self.progress_card = CardWidget()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {THEME_DARK['bg_primary']};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {THEME_DARK['accent']}, stop:1 {THEME_DARK['accent_dim']});
                border-radius: 3px;
            }}
        """)
        self.progress_card.add_widget(self.progress_bar)
        self.progress_card.hide()
        layout.addWidget(self.progress_card)
        
        layout.addStretch()
        return panel
    
    def _create_center_panel(self) -> QWidget:
        """Create center primary results panel."""
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        
        # Header
        header = QLabel("🎯 Detection Result")
        header.setStyleSheet(f"""
            color: {THEME_DARK['text_primary']};
            font-size: 20px;
            font-weight: 700;
        """)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Main result card - fills available space
        self.result_card = CardWidget()
        self.result_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        result_layout = QVBoxLayout()
        result_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.setSpacing(20)
        
        # Large confidence gauge - centered
        self.confidence_gauge = ConfidenceGauge(size=220)
        result_layout.addWidget(self.confidence_gauge, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Verdict badge - fixed width centered
        self.verdict_container = QFrame()
        self.verdict_container.setFixedSize(200, 48)
        self.verdict_container.setStyleSheet(f"""
            background-color: {THEME_DARK['bg_primary']};
            border-radius: 24px;
            border: 2px solid {THEME_DARK['border']};
        """)
        verdict_layout = QHBoxLayout(self.verdict_container)
        verdict_layout.setContentsMargins(0, 0, 0, 0)
        verdict_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.verdict_label = QLabel("AWAITING ANALYSIS")
        self.verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verdict_label.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        verdict_layout.addWidget(self.verdict_label)
        
        result_layout.addWidget(self.verdict_container, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Model info
        self.model_info = QLabel("Ready to analyze")
        self.model_info.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 11px;
            margin-top: 8px;
        """)
        self.model_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_layout.addWidget(self.model_info)
        
        # Add stretch to push content to top of card
        result_layout.addStretch()
        
        self.result_card.add_layout(result_layout)
        layout.addWidget(self.result_card, stretch=1)
        
        # Quick stats - fixed height at bottom
        self.quick_stats = CardWidget(title="Quick Statistics")
        self.quick_stats.setMaximumHeight(140)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.stat_real = MetricCard("Real", "–", "✓", THEME_DARK['success'])
        self.stat_fake = MetricCard("Fake", "–", "⚠", THEME_DARK['danger'])
        self.stat_uncertain = MetricCard("Uncertain", "–", "?", THEME_DARK['warning'])
        
        stats_layout.addWidget(self.stat_real)
        stats_layout.addWidget(self.stat_fake)
        stats_layout.addWidget(self.stat_uncertain)
        
        self.quick_stats.add_layout(stats_layout)
        layout.addWidget(self.quick_stats)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Create right detailed analysis panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("📊 Detailed Analysis")
        header.setStyleSheet(f"""
            color: {THEME_DARK['text_primary']};
            font-size: 20px;
            font-weight: 700;
        """)
        layout.addWidget(header)
        
        # Analysis panel
        self.analysis_panel = AnalysisPanel()
        layout.addWidget(self.analysis_panel)
        
        # Heatmap placeholder
        self.heatmap_card = CardWidget(title="Attention Heatmap")
        self.heatmap_card.setMinimumHeight(200)
        
        self.heatmap_placeholder = QLabel("Heatmap will appear after analysis")
        self.heatmap_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.heatmap_placeholder.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 13px;
            background-color: {THEME_DARK['bg_primary']};
            border-radius: 8px;
            padding: 40px;
        """)
        self.heatmap_card.add_widget(self.heatmap_placeholder)
        layout.addWidget(self.heatmap_card)
        
        # Technical details
        self.tech_card = CardWidget(title="Technical Details")
        self.tech_card.setMaximumHeight(150)
        
        self.tech_text = QLabel("No technical data available")
        self.tech_text.setWordWrap(True)
        self.tech_text.setStyleSheet(f"color: {THEME_DARK['text_secondary']};")
        self.tech_card.add_widget(self.tech_text)
        layout.addWidget(self.tech_card)
        
        layout.addStretch()
        return panel
    
    def _setup_menu(self):
        """Setup application menu bar."""
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {THEME_DARK['bg_primary']};
                color: {THEME_DARK['text_primary']};
                border-bottom: 1px solid {THEME_DARK['border']};
                padding: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {THEME_DARK['bg_elevated']};
                border-radius: 4px;
            }}
        """)
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open Media...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _setup_statusbar(self):
        """Setup status bar with modern styling."""
        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {THEME_DARK['bg_primary']};
                color: {THEME_DARK['text_secondary']};
                border-top: 1px solid {THEME_DARK['border']};
                padding: 8px 16px;
            }}
        """)
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready - Load media to begin analysis")
        
        # GPU / Provider status
        status_layout = QHBoxLayout()
        
        self.provider_label = QLabel("🔍 Checking providers...")
        self.provider_label.setStyleSheet(f"color: {THEME_DARK['text_muted']}; font-size: 11px;")
        status_layout.addWidget(self.provider_label)
        
        gpu_label = QLabel("🔴 CPU Mode")
        gpu_label.setStyleSheet(f"color: {THEME_DARK['text_muted']}; font-size: 11px;")
        status_layout.addWidget(gpu_label)
        
        self.statusbar.addPermanentWidget(QWidget())  # Spacer
        for i in range(status_layout.count()):
            self.statusbar.addPermanentWidget(status_layout.itemAt(i).widget())
    
    def _apply_global_styles(self):
        """Apply global application styles."""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {THEME_DARK['bg_primary']};
            }}
            QWidget {{
                font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
    
    def _on_files_dropped(self, files: list):
        """Handle dropped files."""
        if files:
            self._load_file(files[0])
    
    def _on_open_file(self):
        """Handle open file dialog."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Media", "",
            "Images (*.jpg *.jpeg *.png);;Videos (*.mp4 *.avi *.mov);;All Files (*)"
        )
        if files:
            self._load_file(files[0])
    
    def _load_file(self, filepath: str):
        """Load and display file info."""
        self._current_file = filepath
        
        # Update drop zone
        self.drop_zone.set_file(filepath)
        
        # Update file info
        file_size = os.path.getsize(filepath) / (1024 * 1024)
        file_name = os.path.basename(filepath)
        
        info_text = f"""
        <b>📄 {file_name}</b><br>
        <span style='color: {THEME_DARK['text_muted']}'>
        Size: {file_size:.2f} MB<br>
        Path: {filepath[:50]}...
        </span>
        """
        self.file_info_text.setText(info_text)
        
        # Enable analyze button
        self.analyze_btn.setEnabled(True)
        self.statusbar.showMessage(f"Loaded: {file_name} - Ready for analysis")
    
    def _show_provider_status(self):
        """Display available detection providers in status bar."""
        try:
            providers = self._factory.get_provider_names()
            status_text = " → ".join([f"✓ {p.title()}" for p in providers])
            self.provider_label.setText(f"Providers: {status_text}")
            logger.info(f"Available providers: {providers}")
        except Exception as e:
            self.provider_label.setText("⚠ No providers available")
            logger.error(f"Provider check failed: {e}")
    
    def _start_analysis(self):
        """Start the analysis process with automatic provider fallback."""
        if not self._current_file:
            return
        
        # Update UI state
        self.analyze_btn.setEnabled(False)
        self.progress_card.show()
        self.progress_bar.setValue(0)
        self.statusbar.showMessage("Initializing analysis with automatic fallback...")
        
        # Reset results
        self.confidence_gauge.set_result(0, "ANALYZING", THEME_DARK['accent'])
        self.verdict_label.setText("ANALYZING...")
        self.verdict_label.setStyleSheet(f"""
            color: {THEME_DARK['accent']};
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        
        # Create worker with factory
        try:
            self._worker = DetectionWorker(
                self._factory, self._current_file
            )
            self._worker.progress.connect(self._on_progress)
            self._worker.result_ready.connect(self._on_result)
            self._worker.error.connect(self._on_error)
            self._worker.start()
            
            self.model_info.setText("🤖 Analyzing with AI (auto-fallback enabled)")
            
        except Exception as e:
            self._on_error(str(e))
    
    def _on_progress(self, pct: int, msg: str):
        """Handle analysis progress."""
        self.progress_bar.setValue(pct)
        self.statusbar.showMessage(msg)
    
    def _on_result(self, result):
        """Handle analysis result."""
        self.progress_card.hide()
        self.analyze_btn.setEnabled(True)
        
        # Update confidence gauge
        self.confidence_gauge.set_result(
            result.confidence, 
            result.verdict,
            result.verdict_color
        )
        
        # Update verdict
        self.verdict_label.setText(result.verdict)
        self.verdict_label.setStyleSheet(f"""
            color: {result.verdict_color};
            font-size: 16px;
            font-weight: 700;
            letter-spacing: 3px;
        """)
        self.verdict_container.setStyleSheet(f"""
            background-color: {result.verdict_color}22;
            border-radius: 25px;
            border: 2px solid {result.verdict_color};
        """)
        
        # Update quick stats
        real_score = 1 - result.confidence if result.verdict == "REAL" else 0
        fake_score = result.confidence if result.verdict == "FAKE" else 0
        uncertain_score = result.confidence if result.verdict == "UNCERTAIN" else 0
        
        self.stat_real.set_value(f"{real_score:.1%}")
        self.stat_fake.set_value(f"{fake_score:.1%}")
        self.stat_uncertain.set_value(f"{uncertain_score:.1%}")
        
        self.stat_real.set_color(THEME_DARK['success'] if real_score > 0.5 else THEME_DARK['text_muted'])
        self.stat_fake.set_color(THEME_DARK['danger'] if fake_score > 0.5 else THEME_DARK['text_muted'])
        self.stat_uncertain.set_color(THEME_DARK['warning'] if uncertain_score > 0.5 else THEME_DARK['text_muted'])
        
        # Update analysis panel
        indicators = result.analysis_details.get('indicators', [])
        self.analysis_panel.update_results(
            confidence=result.confidence,
            frames=result.analysis_details.get('frames_analyzed', 1),
            time_sec=result.processing_time,
            explanation=result.explanation,
            indicators=indicators
        )
        
        # Update technical info
        tech_info = f"""
        <b>Model:</b> {result.model_used}<br>
        <b>Processing Time:</b> {result.processing_time:.2f}s<br>
        <b>Confidence Score:</b> {result.confidence:.3f}
        """
        self.tech_text.setText(tech_info)
        
        # Update status
        self.statusbar.showMessage(
            f"✓ Analysis complete: {result.verdict} ({result.confidence:.1%} confidence)"
        )
        
        self.model_info.setText(f"✓ Analysis complete in {result.processing_time:.1f}s")
    
    def _on_error(self, msg: str):
        """Handle analysis error."""
        self.progress_card.hide()
        self.analyze_btn.setEnabled(True)
        
        self.confidence_gauge.set_result(0, "ERROR", THEME_DARK['danger'])
        self.verdict_label.setText("ERROR")
        self.verdict_label.setStyleSheet(f"""
            color: {THEME_DARK['danger']};
            font-size: 14px;
            font-weight: 700;
        """)
        
        self.statusbar.showMessage(f"❌ Error: {msg}")
        QMessageBox.critical(self, "Analysis Error", f"Failed to analyze media:\n{msg}")
    
    def _clear_all(self):
        """Clear all data and reset UI."""
        self._current_file = None
        self._worker = None
        
        self.drop_zone.clear()
        self.file_info_text.setText("No file loaded")
        self.analyze_btn.setEnabled(False)
        
        self.confidence_gauge.set_result(0, "–", THEME_DARK['text_muted'])
        self.verdict_label.setText("AWAITING ANALYSIS")
        self.verdict_label.setStyleSheet(f"""
            color: {THEME_DARK['text_muted']};
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        self.verdict_container.setStyleSheet(f"""
            background-color: {THEME_DARK['bg_primary']};
            border-radius: 25px;
            border: 2px solid {THEME_DARK['border']};
        """)
        
        self.stat_real.set_value("–")
        self.stat_fake.set_value("–")
        self.stat_uncertain.set_value("–")
        
        self.analysis_panel.explanation_text.setText("Analysis results will appear here...")
        self.analysis_panel.indicators_text.setText("No indicators detected yet.")
        self.tech_text.setText("No technical data available")
        
        self.statusbar.showMessage("Ready - Load media to begin analysis")
    
    def _on_about(self):
        """Show about dialog."""
        providers = self._factory.get_provider_names()
        providers_text = ", ".join([p.title() for p in providers])
        
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"""<h2>{APP_NAME} Pro v{APP_VERSION}</h2>
            <p>Advanced AI-powered deepfake detection platform with automatic provider fallback.</p>
            <p><b>Available Providers:</b> {providers_text}</p>
            <p>Features smart caching, rate limiting, and seamless failover between AI services.</p>
            <p>© 2024 DeepGuard AI Labs</p>"""
        )
