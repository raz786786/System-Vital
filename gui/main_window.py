"""
Main GUI Window — PySide6 Architecture
Matches the exact React 'Gui new' design language with instant layout rendering.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QPushButton, QStackedWidget, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QColor

import config
from typing import Dict
from utils.logger import setup_logger

logger = setup_logger(__name__)


class HardwarePreFetchThread(QThread):
    """Background thread to pre-fetch hardware info without blocking UI"""
    hardware_ready = Signal(dict)
    scores_ready = Signal(dict)
    error_occurred = Signal(str)

    def run(self):
        try:
            from modules.hardware_detector import HardwareDetector
            detector = HardwareDetector()
            data = detector.get_all_hardware()
            self.hardware_ready.emit(data)

            from modules.scoring_system import ScoringSystem
            scorer = ScoringSystem()
            scores = {
                'cpu': scorer.score_cpu(data.get('cpu', {}), None),
                'gpu': scorer.score_gpu(data.get('gpu', [{}])[0] if data.get('gpu') else {}, None),
                'ram': scorer.score_ram(data.get('ram', {})),
                'storage': scorer.score_storage(data.get('storage', [])),
            }
            score_data = scorer.calculate_overall_score(scores)
            self.scores_ready.emit(score_data)
        except Exception as e:
            logger.error(f"Error in hardware pre-fetch: {e}")
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window with modern sidebar navigation"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        self.setMinimumSize(1200, 800)

        # Data storage
        self.hardware_data = {}
        self.benchmark_data = {}
        self.diagnostic_data = {}
        self.score_data = {}
        
        self.is_dark_mode = True

        # Core Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create UI
        self.create_sidebar()
        self.create_content_area()

        # Start pre-fetch thread
        self.fetch_thread = HardwarePreFetchThread()
        self.fetch_thread.hardware_ready.connect(self.set_hardware_data)
        self.fetch_thread.scores_ready.connect(self.set_score_data)
        self.fetch_thread.start()

        logger.info("PySide6 Main window initialized")

    def create_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(8)

        # Logo
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(0, 0, 0, 16)
        
        logo_icon = QLabel("🔬")
        logo_icon.setFixedSize(36, 36)
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet(f"background-color: {config.ACCENT_COLOR}; border-radius: 10px; font-size: 20px;")
        
        logo_text_layout = QVBoxLayout()
        logo_text_layout.setSpacing(0)
        title = QLabel("SYSTEM VITAL")
        title.setProperty("class", "Title")
        title.setStyleSheet("font-size: 16px;")
        subtitle = QLabel("DIAGNOSTIC TOOL")
        subtitle.setProperty("class", "Muted")
        subtitle.setStyleSheet("font-size: 10px; font-weight: bold;")
        
        logo_text_layout.addWidget(title)
        logo_text_layout.addWidget(subtitle)
        
        logo_layout.addWidget(logo_icon)
        logo_layout.addLayout(logo_text_layout)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # Main Nav
        self._add_section_header(layout, "MAIN")
        self.nav_buttons = {}
        
        nav_items = [
            ("Dashboard", "📊", "dashboard"),
            ("Diagnostics", "🩺", "diagnostics"),
            ("Benchmark", "⚡", "benchmark"),
            ("Utilities", "🔧", "utilities"),
            ("Network Suite", "📡", "network"),
            ("AI Chat", "🤖", "ai_chat"),
        ]
        for label, icon, key in nav_items:
            self._create_nav_btn(layout, icon, label, key)

        # System section
        self._add_section_header(layout, "SYSTEM")
        system_items = [
            ("Health Score", "❤️", "health"),
            ("Settings", "⚙️", "settings"),
        ]
        for label, icon, key in system_items:
            self._create_nav_btn(layout, icon, label, key)

        layout.addStretch()

        # Footer Status
        footer = QFrame()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        
        # Theme Toggle
        self.theme_btn = QPushButton("🌙 Dark Mode")
        self.theme_btn.setProperty("class", "NavButton")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        footer_layout.addWidget(self.theme_btn)
        
        footer_layout.addSpacing(8)
        
        status_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #22c55e; font-size: 12px;")
        self.status_label = QLabel("System Ready")
        self.status_label.setProperty("class", "Muted")
        
        status_row.addWidget(dot)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        footer_layout.addLayout(status_row)
        
        layout.addWidget(footer)
        
        version = QLabel(f"v{config.APP_VERSION}")
        version.setProperty("class", "Muted")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        self.main_layout.addWidget(self.sidebar)

    def toggle_theme(self):
        from PySide6.QtWidgets import QApplication
        from gui.themes import DARK_THEME_QSS, LIGHT_THEME_QSS
        
        self.is_dark_mode = not self.is_dark_mode
        config.THEME = "dark" if self.is_dark_mode else "light"
        
        app = QApplication.instance()
        if self.is_dark_mode:
            self.theme_btn.setText("🌙 Dark Mode")
            app.setStyleSheet(DARK_THEME_QSS)
        else:
            self.theme_btn.setText("☀️ Light Mode")
            app.setStyleSheet(LIGHT_THEME_QSS)
        
        self._rebuild_tabs()

    def on_theme_changed(self):
        """Called by Settings tab after 'Apply & Save'."""
        from PySide6.QtWidgets import QApplication
        from gui.themes import DARK_THEME_QSS, LIGHT_THEME_QSS
        
        self.is_dark_mode = config.THEME == "dark"
        app = QApplication.instance()
        if self.is_dark_mode:
            self.theme_btn.setText("🌙 Dark Mode")
            app.setStyleSheet(DARK_THEME_QSS)
        else:
            self.theme_btn.setText("☀️ Light Mode")
            app.setStyleSheet(LIGHT_THEME_QSS)
        
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        """Destroy and recreate all cached tab pages so they pick up fresh theme colors."""
        current_name = None
        current_widget = self.stacked_widget.currentWidget()
        for name, page in self.pages.items():
            if page is current_widget:
                current_name = name
                break
        
        # Remove all pages from stacked widget and delete them
        for name in list(self.pages.keys()):
            widget = self.pages[name]
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()
        self.pages.clear()
        
        # Re-navigate to rebuild the current tab
        if current_name:
            self.select_frame_by_name(current_name)

    def _add_section_header(self, layout, text):
        lbl = QLabel(text)
        lbl.setProperty("class", "Muted")
        lbl.setStyleSheet("font-weight: bold; margin-top: 8px; margin-bottom: 4px;")
        layout.addWidget(lbl)

    def _create_nav_btn(self, layout, icon, label, key):
        btn = QPushButton(f"  {icon}  {label}")
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.select_frame_by_name(key))
        layout.addWidget(btn)
        self.nav_buttons[key] = btn

    def create_content_area(self):
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Topbar
        self.topbar = QFrame()
        self.topbar.setObjectName("Topbar")
        self.topbar.setFixedHeight(60)
        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(24, 0, 24, 0)
        
        self.topbar_title = QLabel("Dashboard")
        self.topbar_title.setProperty("class", "Title")
        self.topbar_title.setStyleSheet("font-size: 16px;")
        
        sep = QLabel("|")
        sep.setProperty("class", "Muted")
        
        desc = QLabel("System Vital")
        desc.setProperty("class", "Muted")
        
        topbar_layout.addWidget(self.topbar_title)
        topbar_layout.addWidget(sep)
        topbar_layout.addWidget(desc)
        topbar_layout.addStretch()
        
        # Badges
        sys_badge = QLabel("● All Systems Normal")
        sys_badge.setProperty("class", "SysBadge")
        
        self.health_badge = QLabel("Health: --/100")
        self.health_badge.setProperty("class", "HealthBadge")
        
        topbar_layout.addWidget(sys_badge)
        topbar_layout.addWidget(self.health_badge)
        
        content_layout.addWidget(self.topbar)

        # Stacked Widget (Router)
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        self.main_layout.addWidget(content_container)

        # Pages registry
        self.pages = {}
        
        # Load Dashboard initially
        self.select_frame_by_name("dashboard")

    def select_frame_by_name(self, name):
        # Update Nav Buttons
        for key, btn in self.nav_buttons.items():
            btn.setChecked(key == name)

        # Update title
        self.topbar_title.setText(name.title().replace("_", " "))

        # Lazy load logic
        if name not in self.pages:
            self._instantiate_tab(name)
            
        if name in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[name])

    def _instantiate_tab(self, name):
        # We will build out tabs module by module
        page = QWidget()
        layout = QVBoxLayout(page)
        lbl = QLabel(f"Placeholder for {name}")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setProperty("class", "Title")
        layout.addWidget(lbl)
        
        # Mock registration until tabs are fully ported
        if name == "dashboard":
            from gui.dashboard_tab import DashboardTab
            page = DashboardTab(self)
        elif name == "utilities":
            from gui.utilities_tab import UtilitiesTab
            page = UtilitiesTab(self)
        elif name == "diagnostics":
            from gui.diagnostics_tab import DiagnosticsTab
            page = DiagnosticsTab(self)
        elif name == "benchmark":
            from gui.benchmark_tab import BenchmarkTab
            page = BenchmarkTab(self)
        elif name == "network":
            from gui.network_tab import NetworkSuiteTab
            page = NetworkSuiteTab(self)
        elif name == "health":
            from gui.health_tab import HealthScoreTab
            page = HealthScoreTab(self)
        elif name == "settings":
            from gui.settings_tab import SettingsTab
            page = SettingsTab(self)
        elif name == "ai_chat":
            from gui.ai_chat_tab import AIChatTab
            page = AIChatTab(self)

        self.pages[name] = page
        self.stacked_widget.addWidget(page)

        # Apply pre-fetched data if available
        if name == "dashboard" and self.hardware_data:
            page.update_hardware_display(self.hardware_data)
        if name == "dashboard" and self.score_data:
            page.update_scores(self.score_data)

    def update_status(self, message: str):
        self.status_label.setText(message)

    def set_hardware_data(self, data: Dict):
        self.hardware_data = data
        if "dashboard" in self.pages:
            self.pages["dashboard"].update_hardware_display(data)

    def set_score_data(self, data: Dict):
        self.score_data = data
        if "dashboard" in self.pages:
            self.pages["dashboard"].update_scores(data)
        score = data.get('overall_score', data.get('health_score', 0))
        self.health_badge.setText(f"Health: {score}/100")
