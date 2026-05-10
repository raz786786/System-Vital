"""
Diagnostics Tab — PySide6 Rewrite
Instant rendering of tabs and fast execution using Qt Thread Pools.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, 
    QLabel, QPushButton, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

import config
import threading

def _blend(hex_color, alpha, bg="#1e2130"):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    br, bg_, bb = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
    return f"#{int(r*alpha+br*(1-alpha)):02x}{int(g*alpha+bg_*(1-alpha)):02x}{int(b*alpha+bb*(1-alpha)):02x}"


class ToolWorkerThread(QThread):
    result_ready = Signal(dict)
    def __init__(self, run_func):
        super().__init__()
        self.run_func = run_func
        
    def run(self):
        try:
            res = self.run_func()
            self.result_ready.emit(res)
        except Exception as e:
            self.result_ready.emit({'success': False, 'message': str(e)})


class DiagnosticsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.issues_data = {}
        self.threads = []
        self.create_widgets()

    def create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(24, 24, 24, 24)
        self.container_layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("System Diagnostics")
        title.setProperty("class", "Title")
        sub = QLabel("Scan, diagnose, and repair system issues")
        sub.setProperty("class", "Muted")
        header_text.addWidget(title)
        header_text.addWidget(sub)
        
        header.addLayout(header_text)
        header.addStretch()
        
        self.btn_scan = QPushButton("🔍 Run Full Analysis")
        self.btn_scan.setProperty("class", "PrimaryButton")
        self.btn_scan.setFixedSize(180, 40)
        self.btn_scan.clicked.connect(self.run_diagnostics)
        header.addWidget(self.btn_scan)
        
        self.container_layout.addLayout(header)
        
        # Sub-tab Bar
        tab_frame = QFrame()
        tab_frame.setProperty("class", "SegmentFrame")
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)
        
        self.subtab_btns = {}
        for key, label in [("scan", "Scan Results"), ("quick", "Quick Tools"), ("advanced", "Advanced Tools")]:
            btn = QPushButton(label)
            btn.setProperty("class", "SegmentBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            
            if key == "scan":
                btn.setChecked(True)
            else:
                btn.setChecked(False)
                
            btn.clicked.connect(lambda checked, k=key: self._switch_subtab(k))
            tab_layout.addWidget(btn)
            self.subtab_btns[key] = btn
            
        top_align_layout = QHBoxLayout()
        top_align_layout.addWidget(tab_frame)
        top_align_layout.addStretch()
        self.container_layout.addLayout(top_align_layout)
        
        # Content Area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.addWidget(self.content_area)
        self.container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        self._build_scan()

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _switch_subtab(self, key):
        for k, btn in self.subtab_btns.items():
            btn.setChecked(k == key)
            # Force style re-eval since property changed
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._clear_content()

        if key == "scan":
            self._build_scan()
        elif key == "quick":
            self._build_quick_tools()
        elif key == "advanced":
            self._build_advanced()

    # ── SCAN RESULTS ──
    def _build_scan(self):
        # Summary Card
        card = QFrame()
        card.setProperty("class", "CardFrame")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        
        icon = QLabel("🩺")
        icon.setStyleSheet("font-size: 28px;")
        cl.addWidget(icon)
        
        tl = QVBoxLayout()
        self.summary_title = QLabel("System Status")
        self.summary_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.summary_label = QLabel("No diagnostics run yet. Click 'Run Full Analysis' to start.")
        self.summary_label.setProperty("class", "Muted")
        tl.addWidget(self.summary_title)
        tl.addWidget(self.summary_label)
        cl.addLayout(tl)
        cl.addStretch()
        
        self.critical_badge = QLabel("0 Critical")
        self.critical_badge.setStyleSheet("color: #ef4444; background-color: #3d1a1f; padding: 4px 10px; border-radius: 12px; font-weight: bold;")
        self.warning_badge = QLabel("0 Warnings")
        self.warning_badge.setStyleSheet("color: #eab308; background-color: #332d19; padding: 4px 10px; border-radius: 12px; font-weight: bold;")
        
        cl.addWidget(self.critical_badge)
        cl.addWidget(self.warning_badge)
        
        self.content_layout.addWidget(card)
        
        # Issues label
        lbl = QLabel("DETECTED ISSUES")
        lbl.setProperty("class", "Muted")
        lbl.setStyleSheet("font-weight: bold; margin-top: 8px;")
        self.content_layout.addWidget(lbl)
        
        self.issues_container = QVBoxLayout()
        self.content_layout.addLayout(self.issues_container)
        
        if self.issues_data:
            self._render_issues(self.issues_data)

    def _render_issues(self, data):
        # Implementation for rendering issues in PySide6
        pass

    # ── QUICK TOOLS ──
    def _build_quick_tools(self):
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(16)
        
        tools = [
            ("🔄", "Restart Explorer", "Kill & restart explorer.exe", "explorer_fix", "#3b82f6"),
            ("🌐", "Flush DNS", "ipconfig /flushdns", "dns_flush", "#06b6d4"),
            ("💾", "Optimize Drives", "Defrag HDD / TRIM SSD", "optimize_drives", "#f97316"),
            ("🧹", "Clean Temp Files", "Wipe %TEMP% & Windows\\Temp", "temp", "#ef4444"),
            ("🛡️", "Run SFC Scan", "System file integrity check", "sfc", "#22c55e"),
            ("🔧", "Run DISM Repair", "Repair Windows image", "dism", "#a855f7"),
            ("📡", "IP Release/Renew", "Reset IP configuration", "ip_reset", "#3b82f6"),
            ("📋", "Scan Event Logs", "AI-powered log analysis", "event_logs", "#eab308"),
            ("♻️", "Empty Recycle Bin", "Force clear recycle bin", "recycle", "#eab308"),
            ("🔑", "Wi-Fi Passwords", "Show saved network keys", "wifi_pass", "#06b6d4"),
            ("🚀", "Startup Manager", "List startup items", "startup", "#3b82f6"),
            ("⚡", "Toggle Power Plan", "Switch to High Performance", "power", "#eab308"),
        ]

        for i, (icon, name, desc, uid, color) in enumerate(tools):
            r, c = divmod(i, 4)
            card = QFrame()
            card.setProperty("class", "CardFrame")
            cl = QVBoxLayout(card)
            cl.setAlignment(Qt.AlignCenter)
            
            i_lbl = QLabel(icon)
            i_lbl.setStyleSheet(f"font-size: 24px; color: {color};")
            i_lbl.setAlignment(Qt.AlignCenter)
            
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
            n_lbl.setAlignment(Qt.AlignCenter)
            
            d_lbl = QLabel(desc)
            d_lbl.setProperty("class", "Muted")
            d_lbl.setAlignment(Qt.AlignCenter)
            
            btn = QPushButton("▷ Run")
            btn.setProperty("class", "PrimaryButton")
            btn.clicked.connect(lambda checked=False, u=uid: self._run_quick_tool(u))
            
            cl.addWidget(i_lbl)
            cl.addWidget(n_lbl)
            cl.addWidget(d_lbl)
            cl.addWidget(btn)
            
            grid.addWidget(card, r, c)
            
        self.content_layout.addWidget(grid_widget)

    def _run_quick_tool(self, uid):
        from utilities import get_utility_by_id
        util = get_utility_by_id(uid)
        if util:
            thread = ToolWorkerThread(util['run'])
            thread.result_ready.connect(self._handle_tool_result)
            self.threads.append(thread)
            thread.start()

    def _handle_tool_result(self, result):
        msg = result.get('message', 'Done')[:80]
        self.main_window.update_status(f"{'✅' if result.get('success') else '⚠️'} {msg}")

    # ── ADVANCED TOOLS ──
    def _build_advanced(self):
        tools = [
            ("HWiNFO Utility", "Hardware monitoring & sensor data", "Launch Application", "#3b82f6", "solid", None),
            ("Sensor Log Analysis (HWiNFO)", "Analyze exported CSV sensor logs", "Analyze .CSV", "#22c55e", "tint", None),
            ("AI System Log Analysis", "AI-powered Windows event log scanner", "Scan Windows Logs", "#a855f7", "tint", None),
            ("BSOD Minidump Parser", "Decode crash dump files (.dmp)", "Parse Dumps", "#ef4444", "tint", None),
            ("DLL Error Scanner", "Find SideBySide and dependency errors", "Scan DLLs", "#eab308", "tint", None),
            ("Registry Scanner", "Find invalid install locations", "Scan Registry", "#06b6d4", "tint", None),
        ]
        
        container_card = QFrame()
        container_card.setProperty("class", "CardFrame")
        cc_layout = QVBoxLayout(container_card)
        cc_layout.setContentsMargins(0, 0, 0, 0)
        cc_layout.setSpacing(0)
        
        for i, (title, subtitle, btn_text, color, btn_type, command) in enumerate(tools):
            row = QWidget()
            cl = QHBoxLayout(row)
            cl.setContentsMargins(20, 16, 20, 16)
            
            tl = QVBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
            s_lbl = QLabel(subtitle)
            s_lbl.setProperty("class", "Muted")
            tl.addWidget(t_lbl)
            tl.addWidget(s_lbl)
            cl.addLayout(tl)
            cl.addStretch()
            
            btn = QPushButton(btn_text)
            if btn_type == "solid":
                btn.setStyleSheet(f"background-color: {color}; color: white; border: none; border-radius: 6px; font-weight: bold;")
            else:
                bg_col = "#1e2130" if getattr(self.main_window, "is_dark_mode", True) else "#ffffff"
                bg = _blend(color, 0.15, bg=bg_col)
                btn.setStyleSheet(f"background-color: {bg}; color: {color}; border: 1px solid {color}; border-radius: 6px; font-weight: bold;")
            
            btn.setFixedSize(130, 34)
            cl.addWidget(btn)
            
            cc_layout.addWidget(row)
            
            if i < len(tools) - 1:
                line = QFrame()
                line.setFixedHeight(1)
                is_dark = getattr(self.main_window, "is_dark_mode", True)
                line_color = "#2d3150" if is_dark else "#e2e8f0"
                line.setStyleSheet(f"background-color: {line_color};")
                cc_layout.addWidget(line)
            
        self.content_layout.addWidget(container_card)
            
        # Fix History
        lbl = QLabel("🕒 FIX HISTORY")
        lbl.setProperty("class", "Muted")
        lbl.setStyleSheet("font-weight: bold; margin-top: 16px;")
        self.content_layout.addWidget(lbl)
        
        history = [
            ("2h ago", "DNS Flush — ipconfig /flushdns", "Success", "#22c55e"),
            ("1d ago", "Temp File Cleaner — Removed 2.1 GB", "Success", "#22c55e"),
            ("3d ago", "SFC Scan — 3 files repaired", "Success", "#22c55e"),
            ("1w ago", "Disk Optimization — HDD defragmented", "Success", "#22c55e")
        ]
        
        for time_str, desc, status, color in history:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)
            
            tlbl = QLabel(time_str)
            tlbl.setProperty("class", "Muted")
            tlbl.setFixedWidth(50)
            rl.addWidget(tlbl)
            
            dlbl = QLabel(desc)
            dlbl.setProperty("class", "Muted")
            rl.addWidget(dlbl)
            
            rl.addStretch()
            slbl = QLabel(status)
            slbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px;")
            rl.addWidget(slbl)
            
            self.content_layout.addWidget(row)

    def on_theme_changed(self, is_dark):
        current_tab = None
        for key, btn in self.subtab_btns.items():
            if btn.isChecked():
                current_tab = key
                break
        if current_tab:
            self._switch_subtab(current_tab)

    def run_diagnostics(self):
        pass
