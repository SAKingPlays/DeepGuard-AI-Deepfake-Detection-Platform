"""
╔══════════════════════════════════════════════════════════════╗
║        DeepGuard AI Pro - Deepfake Detection Platform        ║
║        Powered by Google Gemini 2.0 Multimodal AI            ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import os
import logging

# Ensure src directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
from src.ui.modern_main_window import ModernMainWindow
from src.ui.splash_screen import SplashScreen
from src.utils.logger import setup_logger
from src.config import APP_NAME, APP_VERSION


def main():
    # High-DPI support
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("DeepGuard AI")
    # High DPI handled automatically in PyQt6

    # Setup logging
    logger = setup_logger()
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # Show splash screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Create main window
    window = ModernMainWindow()

    def finish_splash():
        splash.finish(window)
        window.show()
        window.raise_()
        window.activateWindow()

    QTimer.singleShot(2000, finish_splash)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
