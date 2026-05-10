"""
AI Chat Tab — System Vital
Upgraded to support multi-provider model selection.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QScrollArea, QLineEdit,
    QFileDialog, QSizePolicy, QSpacerItem, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QFont

import config
from engine.ai_chat_engine import AIChatEngine
from engine.ai_providers import AI_PROVIDERS
from gui.utilities_tab import ToolWorkerThread

class AIChatWorker(QThread):
    result_ready = Signal(dict)
    
    def __init__(self, engine, text, file_path, provider_id, model_id):
        super().__init__()
        self.engine = engine
        self.text = text
        self.file_path = file_path
        self.provider_id = provider_id
        self.model_id = model_id
        
    def run(self):
        result = self.engine.send_message(self.text, self.file_path, self.provider_id, self.model_id)
        self.result_ready.emit(result)


class MessageBubble(QFrame):
    def __init__(self, text, is_user=False, tools=None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.tools = tools or []
        self.tool_buttons = []
        self._build_ui(text)
        
    def _build_ui(self, text):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        if self.is_user:
            self.setStyleSheet(f"""
                MessageBubble {{
                    background-color: {config.ACCENT_COLOR};
                    border-radius: 12px;
                    border-top-right-radius: 2px;
                }}
                QLabel {{ color: white; background: transparent; }}
            """)
        else:
            self.setStyleSheet(f"""
                MessageBubble {{
                    background-color: {config.get_card_bg()};
                    border: 1px solid {config.get_border_color()};
                    border-radius: 12px;
                    border-top-left-radius: 2px;
                }}
                QLabel {{ color: {config.get_text_color()}; background: transparent; }}
            """)
            
        msg_lbl = QLabel(text.strip())
        msg_lbl.setWordWrap(True)
        font = msg_lbl.font()
        font.setPointSize(11)
        msg_lbl.setFont(font)
        msg_lbl.setTextFormat(Qt.MarkdownText)
        layout.addWidget(msg_lbl)
        
        if self.tools:
            tools_frame = QFrame()
            tools_frame.setStyleSheet("background: transparent; border: none;")
            tl = QVBoxLayout(tools_frame)
            tl.setContentsMargins(0, 8, 0, 0)
            tl.setSpacing(6)
            for tool in self.tools:
                btn = QPushButton(f"⚡ Run: {tool['name']}")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #00B894; color: white; font-weight: bold;
                        border-radius: 6px; padding: 8px 12px; text-align: left;
                    }
                    QPushButton:hover { background-color: #00d2a8; }
                """)
                btn.setProperty("tool_id", tool["id"])
                tl.addWidget(btn)
                self.tool_buttons.append(btn)
            layout.addWidget(tools_frame)


class AIChatTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.engine = AIChatEngine(hardware_data=main_window.hardware_data if hasattr(main_window, 'hardware_data') else {})
        self.attached_file = None
        self.create_widgets()
        self._populate_selectors()

    def create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        
        main_container = QFrame()
        main_container.setObjectName("ChatMainContainer")
        mc_layout = QVBoxLayout(main_container)
        mc_layout.setContentsMargins(0, 0, 0, 0)
        mc_layout.setSpacing(16)
        
        # Header Row
        hdr = QHBoxLayout()
        hv = QVBoxLayout()
        hv.setSpacing(4)
        t = QLabel("System Vital AI Assistant")
        t.setProperty("class", "Title")
        s = QLabel("Ask anything about your hardware, optimization, or Windows issues")
        s.setProperty("class", "Muted")
        hv.addWidget(t)
        hv.addWidget(s)
        hdr.addLayout(hv)
        hdr.addStretch()
        
        clear_btn = QPushButton("🗑️ Clear Chat")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.get_card_bg()}; color: {config.get_text_muted()}; border: 1px solid {config.get_border_color()};
                border-radius: 6px; padding: 8px 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {config.get_border_color()}; color: {config.get_text_color()}; }}
        """)
        clear_btn.clicked.connect(self._clear_chat)
        hdr.addWidget(clear_btn)
        mc_layout.addLayout(hdr)

        # Model Selector Bar
        sel_bar = QFrame()
        sel_bar.setStyleSheet(f"background: {config.get_card_bg()}; border: 1px solid {config.get_border_color()}; border-radius: 10px;")
        sel_layout = QHBoxLayout(sel_bar)
        sel_layout.setContentsMargins(12, 8, 12, 8)
        
        sel_layout.addWidget(QLabel("Provider:"))
        self.provider_sel = QComboBox()
        self.provider_sel.setFixedWidth(160)
        self.provider_sel.currentIndexChanged.connect(self._on_provider_changed)
        sel_layout.addWidget(self.provider_sel)
        
        sel_layout.addSpacing(16)
        sel_layout.addWidget(QLabel("Model:"))
        self.model_sel = QComboBox()
        self.model_sel.setFixedWidth(200)
        sel_layout.addWidget(self.model_sel)
        
        sel_layout.addStretch()
        mc_layout.addWidget(sel_bar)
        
        # Chat History Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        bg_main = config.BG_COLOR_DARK if config.THEME == 'dark' else config.BG_COLOR_LIGHT
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: 1px solid {config.get_border_color()}; border-radius: 8px; background: {bg_main}; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
        """)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()
        
        self.scroll_area.setWidget(self.chat_container)
        mc_layout.addWidget(self.scroll_area, 1)
        
        # Loading Indicator
        self.loading_lbl = QLabel("AI is thinking...")
        self.loading_lbl.setStyleSheet(f"color: {config.get_text_muted()}; font-style: italic;")
        self.loading_lbl.hide()
        mc_layout.addWidget(self.loading_lbl)
        
        # File Attachment Chip
        self.file_chip = QFrame()
        self.file_chip.setStyleSheet(f"background: {config.get_card_bg()}; border: 1px solid {config.ACCENT_COLOR}; border-radius: 12px;")
        fcl = QHBoxLayout(self.file_chip)
        fcl.setContentsMargins(12, 6, 12, 6)
        fcl.setSpacing(8)
        self.file_name_lbl = QLabel("filename.jpg")
        self.file_name_lbl.setStyleSheet(f"color: {config.get_text_color()}; font-size: 11px;")
        remove_btn = QPushButton("✖")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.setStyleSheet("background: transparent; color: #ef4444; border: none; font-weight: bold;")
        remove_btn.clicked.connect(self._remove_file)
        fcl.addWidget(QLabel("📎"))
        fcl.addWidget(self.file_name_lbl)
        fcl.addWidget(remove_btn)
        self.file_chip.hide()
        
        file_row = QHBoxLayout()
        file_row.addWidget(self.file_chip)
        file_row.addStretch()
        mc_layout.addLayout(file_row)
        
        # Input Area
        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(45, 45)
        self.attach_btn.setCursor(Qt.PointingHandCursor)
        self.attach_btn.setToolTip("Attach file (Only on Gemini)")
        self.attach_btn.setStyleSheet(f"background: {config.get_card_bg()}; border: 1px solid {config.get_border_color()}; border-radius: 8px; font-size: 18px;")
        self.attach_btn.clicked.connect(self._attach_file)
        input_row.addWidget(self.attach_btn)
        
        self.input_field = QLineEdit()
        self.input_field.setFixedHeight(45)
        self.input_field.setPlaceholderText("Type a message or describe an issue...")
        self.input_field.setStyleSheet(f"background: {config.get_card_bg()}; border: 1px solid {config.get_border_color()}; border-radius: 8px; padding: 0 16px; font-size: 13px; color: {config.get_text_color()};")
        self.input_field.returnPressed.connect(self._send_message)
        input_row.addWidget(self.input_field)
        
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(45, 45)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(f"background: {config.ACCENT_COLOR}; color: white; border: none; border-radius: 8px; font-size: 18px;")
        self.send_btn.clicked.connect(self._send_message)
        input_row.addWidget(self.send_btn)
        
        mc_layout.addLayout(input_row)
        layout.addWidget(main_container)

        # Initial greeting
        self._add_message("Hello! I'm **System Vital AI**. I can help you diagnose PC issues, optimize performance, or answer any Windows questions. How can I help today?", is_user=False)

    def _populate_selectors(self):
        self.provider_sel.blockSignals(True)
        self.provider_sel.clear()
        
        # Only show enabled providers
        enabled = config.ENABLED_PROVIDERS
        if not enabled:
            self.provider_sel.addItem("No AI Providers Enabled", None)
            self.provider_sel.setEnabled(False)
            return

        for p_id in enabled:
            if p_id in AI_PROVIDERS:
                self.provider_sel.addItem(AI_PROVIDERS[p_id]["name"], p_id)
        
        # Set current
        idx = self.provider_sel.findData(config.CHAT_PROVIDER)
        if idx >= 0: self.provider_sel.setCurrentIndex(idx)
        else: self.provider_sel.setCurrentIndex(0)
        
        self.provider_sel.blockSignals(False)
        self._on_provider_changed()

    def _on_provider_changed(self):
        p_id = self.provider_sel.currentData()
        if not p_id or p_id not in AI_PROVIDERS:
            self.model_sel.clear()
            return
            
        self.model_sel.clear()
        for m in AI_PROVIDERS[p_id]["models"]:
            self.model_sel.addItem(m["label"], m["id"])
            
        # Set default model
        if p_id == config.CHAT_PROVIDER:
            idx = self.model_sel.findData(config.CHAT_MODEL)
            if idx >= 0: self.model_sel.setCurrentIndex(idx)

        # File attach only for gemini
        self.attach_btn.setVisible(p_id == "gemini")
        if p_id != "gemini":
            self._remove_file()

    def _send_message(self):
        text = self.input_field.text().strip()
        if not text and not self.attached_file:
            return
            
        p_id = self.provider_sel.currentData()
        m_id = self.model_sel.currentData()
        
        # Add to UI
        self._add_message(text, is_user=True)
        self.input_field.clear()
        self.loading_lbl.show()
        
        # Worker
        self.worker = AIChatWorker(self.engine, text, self.attached_file, p_id, m_id)
        self.worker.result_ready.connect(self._on_ai_result)
        self.worker.start()
        
        self._remove_file()

    def _on_ai_result(self, result):
        self.loading_lbl.hide()
        self._add_message(result["response"], is_user=False, tools=result["tools"])

    def _add_message(self, text, is_user, tools=None):
        bubble = MessageBubble(text, is_user, tools)
        for btn in bubble.tool_buttons:
            btn.clicked.connect(lambda checked=False, b=btn: self._execute_tool(b))
            
        row = QHBoxLayout()
        if is_user:
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
            
        count = self.chat_layout.count()
        self.chat_layout.insertLayout(count - 1, row)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _execute_tool(self, btn):
        tool_id = btn.property("tool_id")
        btn.setEnabled(False)
        btn.setText(f"⌛ Running {tool_id}...")
        self.tool_worker = ToolWorkerThread(tool_id)
        self.tool_worker.finished.connect(lambda: btn.setText(f"✅ {tool_id} Complete"))
        self.tool_worker.start()

    def _attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*.*)")
        if path:
            self.attached_file = path
            self.file_name_lbl.setText(os.path.basename(path))
            self.file_chip.show()

    def _remove_file(self):
        self.attached_file = None
        self.file_chip.hide()

    def _clear_chat(self):
        self.engine.clear_history()
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    si = item.layout().takeAt(0)
                    if si.widget(): si.widget().deleteLater()
        self.chat_layout.addStretch()
        self._add_message("Chat history cleared. How can I help today?", is_user=False)

    def _scroll_to_bottom(self):
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())
