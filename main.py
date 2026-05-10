"""
Hardware Diagnostic Tool - Main Entry Point (PySide6 Edition)
"""

import sys
import os
import multiprocessing

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Main application entry point"""
    try:
        logger.info("Starting Hardware Diagnostic Tool (PySide6)...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        
        # High DPI scaling
        if hasattr(QApplication, 'setHighDpiScaleFactorRoundingPolicy'):
            from PySide6.QtCore import Qt
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

        app = QApplication(sys.argv)
        
        # Load initial stylesheet
        from gui.themes import DARK_THEME_QSS
        app.setStyleSheet(DARK_THEME_QSS)
        
        window = MainWindow()
        window.showMaximized()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass
    main()
