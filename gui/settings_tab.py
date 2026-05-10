"""
Settings Tab — System Vital
Redesigned to support multiple AI providers and deep configuration.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QLineEdit, QComboBox, QPushButton, QScrollArea, QMessageBox,
    QSpacerItem, QSizePolicy, QSlider
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
import config
import json
import os
from engine.ai_providers import AI_PROVIDERS

class SwitchButton(QPushButton):
    """Custom iOS-style toggle switch"""
    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.PointingHandCursor)
        self.toggled.connect(self._update_style)
        self._update_style(checked)
        
    def _update_style(self, checked):
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {config.ACCENT_COLOR}; border-radius: 11px;
                    border: 2px solid {config.ACCENT_COLOR}; color: white; text-align: right;
                    padding-right: 2px; font-size: 14px;
                }}
            """)
            self.setText("●")
        else:
            off_bg = "#334155" if config.THEME == "dark" else "#cbd5e1"
            off_dot = "#94a3b8" if config.THEME == "dark" else "#64748b"
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {off_bg}; border-radius: 11px;
                    border: 2px solid {off_bg}; color: {off_dot}; text-align: left;
                    padding-left: 2px; font-size: 14px;
                }}
            """)
            self.setText("●")

class ColorCircle(QPushButton):
    """Circular color picker button"""
    def __init__(self, color_hex, selected=False, parent=None):
        super().__init__(parent)
        self.color = color_hex
        self.setFixedSize(32, 32)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setChecked(selected)
        self.update_style()
        
    def update_style(self):
        if self.isChecked():
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color};
                    border-radius: 16px;
                    border: 3px solid #ffffff;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.color};
                    border-radius: 16px;
                    border: none;
                }}
            """)

class SettingsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.color_buttons = []
        self.provider_controls = {} # stores {id: {"key": QLineEdit, "switch": SwitchButton}}
        self.create_widgets()

    def create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setObjectName("SettingsContainer")
        self.cl = QVBoxLayout(container)
        self.cl.setContentsMargins(28, 28, 28, 28)
        self.cl.setSpacing(24)

        # Header
        hdr = QVBoxLayout()
        hdr.setSpacing(4)
        t = QLabel("Settings")
        t.setProperty("class", "Title")
        s = QLabel("Configure System Vital to your preferences")
        s.setProperty("class", "Muted")
        hdr.addWidget(t)
        hdr.addWidget(s)
        self.cl.addLayout(hdr)

        # --- AI PROVIDER CONFIGURATION ---
        self.cl.addWidget(self._group_header("AI PROVIDER CONFIGURATION"))
        ai_box = self._group_box()
        al = QVBoxLayout(ai_box)
        al.setSpacing(20)
        
        # Loop through all providers from registry
        for p_id, p_meta in AI_PROVIDERS.items():
            al.addLayout(self._create_provider_section(p_id, p_meta))
            if p_id != list(AI_PROVIDERS.keys())[-1]:
                al.addWidget(self._divider())
        
        # Offline Mode & Provider Selection
        al.addWidget(self._divider())
        
        row_extras = QHBoxLayout()
        
        # Offline toggle
        off_col = QVBoxLayout()
        off_col.addWidget(self._lbl("Offline Mode", bold=True))
        off_col.addWidget(self._lbl("Use rule-based engine without AI (no internet required)", muted=True))
        row_extras.addLayout(off_col)
        row_extras.addStretch()
        self.offline_switch = SwitchButton(config.AI_PROVIDER == "rule-based")
        row_extras.addWidget(self.offline_switch)
        al.addLayout(row_extras)
        
        al.addWidget(self._divider())
        
        # Default Provider selector
        al.addWidget(self._lbl("Default AI Provider", bold=True))
        self.provider_combo = QComboBox()
        self.provider_combo.setFixedHeight(36)
        # Will be populated dynamically in _populate_providers
        self._populate_providers()
        al.addWidget(self.provider_combo)
        
        self.cl.addWidget(ai_box)

        # --- APPEARANCE & THEME ---
        self.cl.addWidget(self._group_header("APPEARANCE & THEME"))
        app_box = self._group_box()
        apl = QVBoxLayout(app_box)
        apl.setSpacing(20)

        # Theme
        row_th = self._row_layout("Color Scheme", "Switch between dark and light interface")
        self.theme_cb = QComboBox()
        self.theme_cb.setFixedSize(120, 32)
        self.theme_cb.addItems(["Light", "Dark"])
        self.theme_cb.setCurrentIndex(1 if config.THEME == "dark" else 0)
        row_th.addWidget(self.theme_cb)
        apl.addLayout(row_th)
        apl.addWidget(self._divider())

        # Accent Color
        apl.addWidget(self._lbl("Accent Color", bold=True))
        color_row = QHBoxLayout()
        colors = ["#3b82f6", "#8b5cf6", "#06b6d4", "#22c55e", "#f97316", "#ec4899"]
        for c in colors:
            btn = ColorCircle(c, c == config.ACCENT_COLOR)
            btn.clicked.connect(lambda _, col=c: self._select_color(col))
            self.color_buttons.append(btn)
            color_row.addWidget(btn)
        color_row.addStretch()
        apl.addLayout(color_row)
        apl.addWidget(self._divider())

        # User Profile
        row_up = self._row_layout("User Profile", "Adjust interface complexity to your experience level")
        self.profile_cb = QComboBox()
        self.profile_cb.setFixedSize(220, 32)
        self.profile_cb.addItems(["Beginner — Simple mode", "Power User — All features", "IT Professional — CLI & advanced"])
        curr_p = config.USER_PROFILE
        if curr_p == "Beginner": self.profile_cb.setCurrentIndex(0)
        elif curr_p == "IT Professional": self.profile_cb.setCurrentIndex(2)
        else: self.profile_cb.setCurrentIndex(1)
        row_up.addWidget(self.profile_cb)
        apl.addLayout(row_up)
        apl.addWidget(self._divider())

        # Language
        row_lg = self._row_layout("Language", "Interface language (requires restart)")
        self.lang_cb = QComboBox()
        self.lang_cb.setFixedSize(120, 32)
        self.lang_cb.addItems(["English", "Spanish", "French", "German"])
        row_lg.addWidget(self.lang_cb)
        apl.addLayout(row_lg)

        self.cl.addWidget(app_box)

        # --- MONITORING & ALERTS ---
        self.cl.addWidget(self._group_header("MONITORING & ALERTS"))
        mon_box = self._group_box()
        ml = QVBoxLayout(mon_box)
        ml.setSpacing(20)

        # Threshold Slider
        tr = QHBoxLayout()
        tt = QVBoxLayout()
        tt.addWidget(self._lbl("Threshold Alerts", bold=True))
        tt.addWidget(self._lbl("Send notification when CPU/RAM usage exceeds limit", muted=True))
        tr.addLayout(tt)
        tr.addStretch()
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(50, 100)
        self.threshold_slider.setValue(90)
        self.threshold_slider.setFixedWidth(150)
        tr.addWidget(self.threshold_slider)
        self.thresh_val_lbl = QLabel("90%")
        self.thresh_val_lbl.setStyleSheet("font-weight: bold; color: #3b82f6; min-width: 40px;")
        self.threshold_slider.valueChanged.connect(lambda v: self.thresh_val_lbl.setText(f"{v}%"))
        tr.addWidget(self.thresh_val_lbl)
        ml.addLayout(tr)
        ml.addWidget(self._divider())

        # Scheduled Scan
        row_ss = self._row_layout("Scheduled Health Scan", "Automatically run diagnostics in the background")
        self.scan_switch = SwitchButton(True)
        row_ss.addWidget(self.scan_switch)
        ml.addLayout(row_ss)
        ml.addWidget(self._divider())

        # Scan Frequency
        row_sf = self._row_layout("Scan Frequency", "How often to run automatic diagnostics")
        self.freq_cb = QComboBox()
        self.freq_cb.setFixedSize(120, 32)
        self.freq_cb.addItems(["Daily", "Weekly", "Monthly"])
        self.freq_cb.setCurrentIndex(1)
        row_sf.addWidget(self.freq_cb)
        ml.addLayout(row_sf)
        ml.addWidget(self._divider())

        # Auto Restore
        row_ar = self._row_layout("Auto Restore Point", "Create a restore point before any fix is applied")
        self.restore_switch = SwitchButton(True)
        row_ar.addWidget(self.restore_switch)
        ml.addLayout(row_ar)

        self.cl.addWidget(mon_box)

        # --- APPLICATION INFO ---
        self.cl.addWidget(self._group_header("APPLICATION INFO"))
        info_box = self._group_box()
        il = QGridLayout(info_box)
        il.setSpacing(16)
        
        il.addWidget(self._info_tile("VERSION", config.APP_VERSION), 0, 0)
        il.addWidget(self._info_tile("BUILD DATE", "June 2025"), 0, 1)
        il.addWidget(self._info_tile("MADE BY", "AHMED ZUBAIR RAO • SHAYAN HUMAYUN • MUHAMMAD AHMAD"), 1, 0)
        il.addWidget(self._info_tile("LICENSE", "MIT Open Source"), 1, 1)
        
        btn_row = QHBoxLayout()
        btn_row.addWidget(self._btn("📄 Changelog"))
        btn_row.addWidget(self._btn("Export Settings"))
        btn_row.addWidget(self._btn("Import Settings"))
        btn_row.addStretch()
        il.addLayout(btn_row, 2, 0, 1, 2)
        
        self.cl.addWidget(info_box)

        # Save Button
        self.save_btn = QPushButton("💾 Apply & Save Changes")
        self.save_btn.setFixedHeight(48)
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.ACCENT_COLOR};
                color: white;
                border-radius: 10px;
                font-weight: bold;
                font-size: 15px;
                margin-top: 20px;
            }}
            QPushButton:hover {{ background-color: #2563eb; }}
        """)
        self.save_btn.clicked.connect(self._save_all)
        self.cl.addWidget(self.save_btn)

        self.cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    # --- Helper Builders ---
    
    def _create_provider_section(self, p_id, p_meta):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title + Switch row
        title_row = QHBoxLayout()
        title_lbl = QLabel(p_meta["name"])
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {config.get_text_color()};")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        
        is_enabled = p_id in config.ENABLED_PROVIDERS
        switch = SwitchButton(is_enabled)
        title_row.addWidget(switch)
        layout.addLayout(title_row)
        
        # Key field
        key_edit = QLineEdit()
        key_edit.setEchoMode(QLineEdit.Password)
        key_edit.setPlaceholderText(f"Enter {p_meta['name']} API Key...")
        # Load current key
        key_val = getattr(config, f"{p_id.upper()}_API_KEY", "")
        key_edit.setText(key_val)
        layout.addWidget(key_edit)
        
        # Footer row: Link + Validate button
        footer = QHBoxLayout()
        link = QLabel(f"<a href='{p_meta['get_key_url']}' style='color: #3b82f6;'>Get a free key ↗</a>")
        link.setOpenExternalLinks(True)
        link.setStyleSheet("font-size: 11px;")
        footer.addWidget(link)
        footer.addStretch()
        
        val_btn = QPushButton("✅ Validate Key")
        val_btn.setFixedSize(120, 28)
        val_btn.setCursor(Qt.PointingHandCursor)
        val_btn_bg = "#1e293b" if config.THEME == "dark" else "#ecfdf5"
        val_btn_hover = "#064e3b" if config.THEME == "dark" else "#d1fae5"
        val_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {val_btn_bg}; color: #10b981; border: 1px solid #10b981;
                border-radius: 6px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {val_btn_hover}; }}
        """)
        val_btn.clicked.connect(lambda _, pid=p_id, edit=key_edit: self._validate_key(pid, edit.text()))
        footer.addWidget(val_btn)
        layout.addLayout(footer)
        
        self.provider_controls[p_id] = {"key": key_edit, "switch": switch}
        return layout

    def _group_header(self, title):
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {config.get_text_muted()}; letter-spacing: 1.5px;")
        return lbl

    def _group_box(self):
        box = QFrame()
        box.setObjectName("SettingsGroupBox")
        box.setStyleSheet(f"""
            #SettingsGroupBox {{
                background-color: {config.get_card_bg()};
                border: 1px solid {config.get_border_color()};
                border-radius: 16px;
            }}
        """)
        return box

    def _lbl(self, text, bold=False, muted=False):
        l = QLabel(text)
        l.setStyleSheet("border: none; background: transparent;")
        if bold: l.setStyleSheet(l.styleSheet() + f" font-weight: bold; color: {config.get_text_color()};")
        if muted: l.setStyleSheet(l.styleSheet() + f" color: {config.get_text_muted()}; font-size: 12px;")
        return l

    def _row_layout(self, title, sub):
        row = QHBoxLayout()
        col = QVBoxLayout()
        col.addWidget(self._lbl(title, bold=True))
        col.addWidget(self._lbl(sub, muted=True))
        row.addLayout(col)
        row.addStretch()
        return row

    def _divider(self):
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet(f"background-color: {config.get_border_color()}; border: none;")
        return d

    def _info_tile(self, title, val):
        f = QFrame()
        f.setStyleSheet(f"background-color: {config.get_card_bg()}; border: 1px solid {config.get_border_color()}; border-radius: 10px;")
        l = QVBoxLayout(f)
        l.setContentsMargins(12, 10, 12, 10)
        t = QLabel(title)
        t.setStyleSheet(f"font-size: 10px; color: {config.get_text_muted()}; font-weight: bold; letter-spacing: 1px;")
        l.addWidget(t)
        v = QLabel(val)
        v.setStyleSheet(f"font-size: 13px; color: {config.get_text_color()}; font-weight: bold;")
        v.setWordWrap(True)
        l.addWidget(v)
        return f

    def _btn(self, text):
        b = QPushButton(text)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.get_card_bg()}; color: {config.get_text_color()}; border: 1px solid {config.get_border_color()};
                border-radius: 8px; padding: 8px 16px; font-weight: bold; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {config.get_border_color()}; }}
        """)
        return b

    # --- Actions ---

    def _populate_providers(self):
        self.provider_combo.clear()
        enabled = [p_id for p_id, ctrl in self.provider_controls.items() if ctrl["switch"].isChecked()]
        if not enabled:
            self.provider_combo.addItem("Offline (Rule-based)")
            return
            
        for p_id in enabled:
            self.provider_combo.addItem(AI_PROVIDERS[p_id]["name"], p_id)
        
        # Set current
        idx = self.provider_combo.findData(config.CHAT_PROVIDER)
        if idx >= 0: self.provider_combo.setCurrentIndex(idx)

    def _validate_key(self, p_id, key):
        if not key.strip():
            QMessageBox.warning(self, "Validation", "Please enter a key first.")
            return
        from engine.ai_chat_engine import validate_provider_key
        ok, msg = validate_provider_key(p_id, key)
        if ok: QMessageBox.information(self, "Validation", msg)
        else: QMessageBox.warning(self, "Validation Failed", msg)

    def _select_color(self, hex_color):
        for btn in self.color_buttons:
            btn.setChecked(btn.color == hex_color)
            btn.update_style()
        config.ACCENT_COLOR = hex_color

    def _save_all(self):
        # 1. Update API Keys in config
        enabled_list = []
        for p_id, ctrls in self.provider_controls.items():
            key = ctrls["key"].text().strip()
            setattr(config, f"{p_id.upper()}_API_KEY", key)
            if ctrls["switch"].isChecked():
                enabled_list.append(p_id)
        
        config.ENABLED_PROVIDERS = enabled_list
        
        # 2. Update Default Provider
        if self.offline_switch.isChecked() or not enabled_list:
            config.CHAT_PROVIDER = "rule-based"
        else:
            p_data = self.provider_combo.currentData()
            if p_data: config.CHAT_PROVIDER = p_data

        # 3. GUI settings
        config.THEME = "dark" if self.theme_cb.currentIndex() == 1 else "light"
        p_idx = self.profile_cb.currentIndex()
        if p_idx == 0: config.USER_PROFILE = "Beginner"
        elif p_idx == 2: config.USER_PROFILE = "IT Professional"
        else: config.USER_PROFILE = "Power User"

        # 4. Save to JSON
        settings_path = os.path.join(config.DATA_DIR, "user_settings.json")
        data = {
            "CHAT_PROVIDER": config.CHAT_PROVIDER,
            "CHAT_MODEL": config.CHAT_MODEL,
            "ENABLED_PROVIDERS": config.ENABLED_PROVIDERS,
            "GEMINI_API_KEY": config.GEMINI_API_KEY,
            "GROQ_API_KEY": config.GROQ_API_KEY,
            "OPENROUTER_API_KEY": config.OPENROUTER_API_KEY,
            "NVIDIA_API_KEY": config.NVIDIA_API_KEY,
            "NOVA_API_KEY": config.NOVA_API_KEY,
            "ACCENT_COLOR": config.ACCENT_COLOR,
            "THEME": config.THEME,
            "USER_PROFILE": config.USER_PROFILE
        }
        
        try:
            with open(settings_path, 'w') as f:
                json.dump(data, f, indent=4)
            QMessageBox.information(self, "System Vital", "Settings saved successfully!")
            # Trigger live updates if needed
            self._populate_providers()
            if self.main_window:
                self.main_window.on_theme_changed() # Trigger theme refresh
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
