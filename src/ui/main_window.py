"""Main application window with tabbed interface."""
from __future__ import annotations
import os
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QStatusBar, QToolBar, QPushButton, QMenu,
    QMenuBar, QFileDialog, QMessageBox, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QAction, QKeySequence

from src.ui.video_tab import VideoTab
from src.ui.audio_tab import AudioTab
from src.ui.image_tab import ImageTab
from src.ui.batch_tab import BatchTab
from src.ui.live_tab import LiveTab
from src.utils.config import APP_NAME, APP_VERSION, THEME_DARK, MODEL_SIZES

logger = logging.getLogger("deepguard")


class MainWindow(QMainWindow):
    """Main application window with tabbed interface."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self):
        """Setup the main UI components."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        
        # Shared model size reference (default: standard)
        self._model_size_ref = ["standard"]
        
        # Add tabs with model_size_ref
        self.video_tab = VideoTab(self._model_size_ref)
        self.audio_tab = AudioTab(self._model_size_ref)
        self.image_tab = ImageTab(self._model_size_ref)
        self.batch_tab = BatchTab(self._model_size_ref)
        self.live_tab = LiveTab(self._model_size_ref)
        
        self.tabs.addTab(self.video_tab, "📹 Video")
        self.tabs.addTab(self.audio_tab, "🎵 Audio")
        self.tabs.addTab(self.image_tab, "🖼️ Image")
        self.tabs.addTab(self.batch_tab, "📁 Batch")
        self.tabs.addTab(self.live_tab, "🔴 Live")
        
        layout.addWidget(self.tabs)
        
        # Apply theme styling
        self._apply_theme()
    
    def _apply_theme(self):
        """Apply dark theme styling."""
        theme = THEME_DARK
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['bg_primary']};
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {theme['bg_primary']};
            }}
            QTabBar::tab {{
                background-color: {theme['bg_secondary']};
                color: {theme['text_secondary']};
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme['bg_card']};
                color: {theme['accent']};
                border-bottom: 2px solid {theme['accent']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {theme['bg_elevated']};
                color: {theme['text_primary']};
            }}
        """)
    
    def _setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._on_open)
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
    
    def _setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        toolbar.setMovable(False)
        toolbar.setVisible(False)  # Hidden by default for cleaner look
    
    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")
        
        # GPU status label
        from src.utils.config import GPU_AVAILABLE, GPU_NAME
        gpu_text = f"GPU: {GPU_NAME}" if GPU_AVAILABLE else "CPU Mode"
        gpu_label = QLabel(gpu_text)
        self.statusbar.addPermanentWidget(gpu_label)
    
    def _on_open(self):
        """Handle open file action."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "",
            "All Media (*.mp4 *.avi *.mov *.wav *.mp3 *.jpg *.png);;All Files (*)"
        )
        if file_path:
            # Switch to appropriate tab based on file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.mp4', '.avi', '.mov', '.mkv']:
                self.tabs.setCurrentWidget(self.video_tab)
                self.video_tab.load_file(file_path)
            elif ext in ['.wav', '.mp3', '.flac']:
                self.tabs.setCurrentWidget(self.audio_tab)
                self.audio_tab.load_file(file_path)
            elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                self.tabs.setCurrentWidget(self.image_tab)
                self.image_tab.load_file(file_path)
    
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            f"<p>Advanced AI-powered deepfake detection platform.</p>"
            f"<p>Detect synthetic media across video, audio, and images.</p>"
        )
