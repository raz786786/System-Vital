"""
Dashboard Tab — PySide6 Rewrite
Pixel-perfect React matching with Light/Dark mode support and dynamic network/hardware stats.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, 
    QLabel, QPushButton, QScrollArea, QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath

import psutil
import time
from typing import Dict
import config
from gui.themes import DARK_COLORS, LIGHT_COLORS
from utils.system_info import DeepSystemInfo
from PySide6.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QHeaderView

def format_mbps(bytes_val):
    return f"{(bytes_val * 8) / (1024 * 1024):.1f} Mbps"

class CircularHealthRing(QWidget):
    """Custom hardware-accelerated drawing for Health Score Ring"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self.score = 67
        self.color = QColor("#eab308")
        self.bg_color = QColor(DARK_COLORS["border_light"])
        self.text_color = QColor(DARK_COLORS["text_main"])

    def set_score(self, score, color_hex):
        self.score = score
        self.color = QColor(color_hex)
        self.update()

    def set_theme(self, is_dark):
        colors = DARK_COLORS if is_dark else LIGHT_COLORS
        self.bg_color = QColor(colors["border_light"])
        self.text_color = QColor(colors["text_main"])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background ring
        pen_bg = QPen(self.bg_color)
        pen_bg.setWidth(10)
        painter.setPen(pen_bg)
        rect = self.rect().adjusted(10, 10, -10, -10)
        painter.drawArc(rect, 0, 360 * 16)

        # Draw foreground ring
        pen_fg = QPen(self.color)
        pen_fg.setWidth(10)
        pen_fg.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_fg)
        
        span_angle = int(-360 * (self.score / 100) * 16)
        painter.drawArc(rect, 90 * 16, span_angle)
        
        # Draw text inside
        painter.setPen(self.color)
        font = painter.font()
        font.setPixelSize(32)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(0, -10, 0, -10), Qt.AlignCenter, str(self.score))
        
        font.setPixelSize(11)
        painter.setFont(font)
        tier = "POOR" if self.score < 40 else ("FAIR" if self.score < 70 else "GOOD")
        painter.drawText(self.rect().adjusted(0, 30, 0, 0), Qt.AlignCenter, tier)


class RollingChart(QWidget):
    """Custom hardware-accelerated rolling line chart"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.history = [0]*60
        self.color = QColor("#3b82f6")
        self.grid_color = QColor(DARK_COLORS["border_light"])
        self.text_color = QColor(DARK_COLORS["text_muted"])

    def update_data(self, history, color_hex):
        self.history = history
        self.color = QColor(color_hex)
        self.update()

    def set_theme(self, is_dark):
        colors = DARK_COLORS if is_dark else LIGHT_COLORS
        self.grid_color = QColor(colors["border_light"])
        self.text_color = QColor(colors["text_muted"])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Grid
        pen_grid = QPen(self.grid_color)
        pen_grid.setStyle(Qt.DashLine)
        painter.setPen(pen_grid)
        
        for y_pct in [25, 50, 75, 100]:
            y = int(h - (y_pct / 100 * h))
            if y_pct != 100:
                painter.drawLine(0, y, w, y)
            
            painter.setPen(self.text_color)
            painter.drawText(10, y + (12 if y_pct==100 else -5), str(y_pct))
            painter.setPen(pen_grid)
            
        # Draw Line
        if len(self.history) < 2: return
        
        path = QPainterPath()
        step = w / max(len(self.history) - 1, 1)
        
        for i, val in enumerate(self.history):
            x = i * step
            y = h - (val / 100 * h)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
                
        pen_line = QPen(self.color)
        pen_line.setWidth(2)
        painter.setPen(pen_line)
        painter.drawPath(path)


class HardwareMonitorThread(QThread):
    metrics_updated = Signal(float, object, object, object, float, float)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        while self.running:
            try:
                cpu_pct = psutil.cpu_percent(interval=1)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('C:\\')
                net = psutil.net_io_counters()
                gpu_pct = min(100, max(0, cpu_pct * 0.8 + 15)) # Mock
                temp_c = min(100, max(30, 45 + (cpu_pct * 0.4))) # Mock
                self.metrics_updated.emit(cpu_pct, mem, disk, net, gpu_pct, temp_c)
            except Exception:
                pass

    def stop(self):
        self.running = False
        self.wait()


class DashboardTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        
        self.cpu_history = [0]*60
        self.ram_history = [0]*60
        self.gpu_history = [0]*60
        self.temp_history = [0]*60
        self.current_graph = "CPU"
        self.last_net = None
        self.last_net_time = 0
        
        self.deep_info_fetcher = DeepSystemInfo()
        self.create_widgets()
        
        self.monitor_thread = HardwareMonitorThread()
        self.monitor_thread.metrics_updated.connect(self._update_live_metrics)
        self.monitor_thread.start()

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
        title = QLabel("System Overview")
        title.setProperty("class", "Title")
        sub = QLabel("Real-time hardware monitoring & health analysis")
        sub.setProperty("class", "Muted")
        header_text.addWidget(title)
        header_text.addWidget(sub)
        
        header.addLayout(header_text)
        header.addStretch()
        
        btn_export = QPushButton("📥 Export Report")
        btn_export.setFixedHeight(36)
        
        btn_specs = QPushButton("🔍 Detailed Specs")
        btn_specs.setFixedHeight(36)
        btn_specs.clicked.connect(self._show_detailed_specs)
        
        btn_scan = QPushButton("📈 Scan Hardware")
        btn_scan.setProperty("class", "PrimaryButton")
        btn_scan.setFixedHeight(36)
        
        header.addWidget(btn_export)
        header.addWidget(btn_specs)
        header.addWidget(btn_scan)
        
        self.container_layout.addLayout(header)
        
        # Top Row (Health, Uptime & Network, Battery)
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        
        # 1. Health Card
        health_card = QFrame()
        health_card.setProperty("class", "CardFrame")
        hl = QHBoxLayout(health_card)
        
        self.ring = CircularHealthRing()
        hl.addWidget(self.ring)
        
        self.bullets = QVBoxLayout()
        b_title = QLabel("HEALTH SCORE")
        b_title.setProperty("class", "Muted")
        b_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.bullets.addWidget(b_title)
        self.b_disk = QLabel("Disk: Critical (91%)")
        self.b_disk = QLabel("Disk: Critical (91%)")
        self.b_disk.setStyleSheet("color: #ef4444; font-size: 11px;")
        self.bullets.addWidget(self.b_disk)
        self.b_ram = QLabel("RAM: Warning (72%)")
        self.b_ram.setStyleSheet("color: #eab308; font-size: 11px;")
        self.bullets.addWidget(self.b_ram)
        self.b_cpu = QLabel("CPU: Good (38%)")
        self.b_cpu.setStyleSheet("color: #22c55e; font-size: 11px;")
        self.bullets.addWidget(self.b_cpu)
        self.b_temp = QLabel("Thermal: Normal (62°C)")
        self.b_temp.setStyleSheet("color: #22c55e; font-size: 11px;")
        self.bullets.addWidget(self.b_temp)
        
        hl.addLayout(self.bullets)
        top_row.addWidget(health_card, 4)
        
        # 2. Mid Column
        mid_col = QVBoxLayout()
        mid_col.setSpacing(12)
        
        uptime_card = QFrame()
        uptime_card.setProperty("class", "CardFrame")
        ul = QVBoxLayout(uptime_card)
        lbl = QLabel("🕒 UPTIME")
        lbl.setProperty("class", "Muted")
        ul.addWidget(lbl)
        self.uptime_val = QLabel("0d 0h 0m")
        self.uptime_val.setProperty("class", "ValueBig")
        self.uptime_val.setStyleSheet("color: #06b6d4;")
        ul.addWidget(self.uptime_val)
        mid_col.addWidget(uptime_card, 1)
        
        net_card = QFrame()
        net_card.setProperty("class", "CardFrame")
        nl = QVBoxLayout(net_card)
        nh = QHBoxLayout()
        nlbl = QLabel("📶 NETWORK")
        nlbl.setProperty("class", "Muted")
        nstat = QLabel(" Connected ")
        nstat.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 10px;")
        nh.addWidget(nlbl)
        nh.addStretch()
        nh.addWidget(nstat)
        nl.addLayout(nh)
        
        stats = QHBoxLayout()
        d_lbl = QVBoxLayout()
        d_title = QLabel("↓ DOWN")
        d_title.setProperty("class", "Muted")
        self.net_down = QLabel("0.0 Mbps")
        self.net_down.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 16px;")
        d_lbl.addWidget(d_title)
        d_lbl.addWidget(self.net_down)
        
        u_lbl = QVBoxLayout()
        u_title = QLabel("↑ UP")
        u_title.setProperty("class", "Muted")
        self.net_up = QLabel("0.0 Mbps")
        self.net_up.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 16px;")
        u_lbl.addWidget(u_title)
        u_lbl.addWidget(self.net_up)
        
        p_lbl = QVBoxLayout()
        p_title = QLabel("PING")
        p_title.setProperty("class", "Muted")
        self.net_ping = QLabel("18ms")
        self.net_ping.setStyleSheet("color: #eab308; font-weight: bold; font-size: 16px;")
        p_lbl.addWidget(p_title)
        p_lbl.addWidget(self.net_ping)
        
        stats.addLayout(d_lbl)
        stats.addLayout(u_lbl)
        stats.addLayout(p_lbl)
        nl.addLayout(stats)
        
        mid_col.addWidget(net_card, 1)
        top_row.addLayout(mid_col, 3)
        
        # 3. Battery Card
        bat_card = QFrame()
        bat_card.setProperty("class", "CardFrame")
        bl = QVBoxLayout(bat_card)
        bh = QHBoxLayout()
        blbl = QLabel("🔋 BATTERY HEALTH")
        blbl.setProperty("class", "Muted")
        self.bat_status = QLabel(" Discharging ")
        self.bat_status.setStyleSheet("color: #eab308; font-weight: bold; font-size: 10px;")
        bh.addWidget(blbl)
        bh.addStretch()
        bh.addWidget(self.bat_status)
        bl.addLayout(bh)
        
        self.bat_val = QLabel("74%")
        self.bat_val.setProperty("class", "ValueBig")
        self.bat_val.setStyleSheet("color: #eab308;")
        bl.addWidget(self.bat_val)
        
        self.bat_prog = QProgressBar()
        self.bat_prog.setFixedHeight(8)
        self.bat_prog.setValue(74)
        bl.addWidget(self.bat_prog)
        
        self.bat_sub = QLabel("Health: 82%   Cycles: 312")
        self.bat_sub.setProperty("class", "Muted")
        bl.addWidget(self.bat_sub)
        
        top_row.addWidget(bat_card, 3)
        self.container_layout.addLayout(top_row)
        
        # Chart
        chart_card = QFrame()
        chart_card.setProperty("class", "CardFrame")
        cl = QVBoxLayout(chart_card)
        
        ch = QHBoxLayout()
        ch_title = QLabel("📈 60-Second Rolling Graph")
        ch_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        ch.addWidget(ch_title)
        ch.addStretch()
        
        self.btn_cpu = QPushButton("CPU %")
        self.btn_ram = QPushButton("RAM %")
        self.btn_gpu = QPushButton("GPU %")
        self.btn_temp = QPushButton("Temp °C")
        
        self.chart = RollingChart()
        
        for btn, key in [(self.btn_cpu, "CPU"), (self.btn_ram, "RAM"), (self.btn_gpu, "GPU"), (self.btn_temp, "Temp")]:
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, k=key: self._set_graph(k))
            ch.addWidget(btn)
            
        self._set_graph("CPU")
        
        cl.addLayout(ch)
        cl.addWidget(self.chart)
        self.container_layout.addWidget(chart_card)
        
        # Grid
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)
        
        self.cpu_val = QLabel("0%")
        self.cpu_sub = QLabel("Scanning CPU...")
        self.cpu_prog = QProgressBar()
        
        self.gpu_val = QLabel("0%")
        self.gpu_sub = QLabel("Scanning GPU...")
        self.gpu_prog = QProgressBar()
        
        self.ram_val = QLabel("0%")
        self.ram_sub = QLabel("Scanning RAM...")
        self.ram_prog = QProgressBar()
        
        self.storage_val = QLabel("0%")
        self.storage_sub = QLabel("Scanning Storage...")
        self.storage_prog = QProgressBar()
        
        items = [
            ("CPU", "💻", "#3b82f6", self.cpu_val, self.cpu_sub, self.cpu_prog, "2 Cores / 4 Threads"),
            ("GPU", "🎮", "#06b6d4", self.gpu_val, self.gpu_sub, self.gpu_prog, "VRAM: 2.00 GB"),
            ("RAM", "🧠", "#a855f7", self.ram_val, self.ram_sub, self.ram_prog, "2 Modules installed"),
            ("Storage", "💾", "#ef4444", self.storage_val, self.storage_sub, self.storage_prog, "C:\\ - HDD")
        ]
        
        for i, (title, icon, color, val_lbl, sub_lbl, prog, bot_text) in enumerate(items):
            r, c = divmod(i, 2)
            gc = QFrame()
            gc.setProperty("class", "CardFrame")
            gcl = QVBoxLayout(gc)
            
            th = QHBoxLayout()
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"font-size: 16px;")
            tl = QVBoxLayout()
            tl_lbl = QLabel(title)
            tl_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
            sub_lbl.setProperty("class", "Muted")
            tl.addWidget(tl_lbl)
            tl.addWidget(sub_lbl)
            
            vl = QVBoxLayout()
            val_lbl.setProperty("class", "ValueBig")
            val_lbl.setStyleSheet(f"color: {color};")
            temp_lbl = QLabel("--°C" if title != "Storage" else "Health: Good")
            temp_lbl.setProperty("class", "Muted")
            temp_lbl.setAlignment(Qt.AlignRight)
            vl.addWidget(val_lbl)
            vl.addWidget(temp_lbl)
            
            th.addWidget(icon_lbl)
            th.addLayout(tl)
            th.addStretch()
            th.addLayout(vl)
            
            gcl.addLayout(th)
            prog.setFixedHeight(6)
            prog.setValue(50)
            prog.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}")
            gcl.addWidget(prog)
            
            b_lbl = QLabel(bot_text)
            b_lbl.setProperty("class", "Muted")
            gcl.addWidget(b_lbl)
            
            grid_layout.addWidget(gc, r, c)
            
        self.container_layout.addLayout(grid_layout)
        
        # Detected Issues
        self.issues_card = QFrame()
        self.issues_card.setProperty("class", "CardFrame")
        self.il = QVBoxLayout(self.issues_card)
        
        ih = QHBoxLayout()
        ih_lbl = QLabel("⚠️ Detected Issues")
        ih_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        ih.addWidget(ih_lbl)
        self.issue_count = QLabel("4 issues")
        self.issue_count.setStyleSheet("color: #eab308; font-weight: bold; font-size: 11px;")
        ih.addWidget(self.issue_count)
        ih.addStretch()
        self.il.addLayout(ih)
        
        self.issues_container = QVBoxLayout()
        self.il.addLayout(self.issues_container)
        
        # Mock issues initially
        self._add_issue("Disk at 91% — Low free space on C:\\", "#eab308", "Run Disk Cleanup")
        self._add_issue("RAM usage is 72% at idle — check background apps", "#eab308", "Kill Zombies")
        self._add_issue("HDD detected — Consider disk optimization", "#ef4444", "Defrag Now")
        self._add_issue("CPU temperature is normal (62°C)", "#22c55e", None)
        self._add_issue("Battery health at 82% — moderate degradation", "#eab308", "View Report")
        
        self.container_layout.addWidget(self.issues_card)
        self.container_layout.addStretch()
        
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _set_graph(self, gtype):
        self.current_graph = gtype
        
        # Determine unselected styling based on theme
        is_dark = getattr(self.main_window, "is_dark_mode", True)
        border_color = DARK_COLORS["border_light"] if is_dark else LIGHT_COLORS["border_light"]
        text_color = DARK_COLORS["text_muted"] if is_dark else LIGHT_COLORS["text_muted"]

        for btn, name in [(self.btn_cpu, "CPU"), (self.btn_ram, "RAM"), (self.btn_gpu, "GPU"), (self.btn_temp, "Temp")]:
            if name == gtype:
                btn.setStyleSheet(f"background-color: {config.ACCENT_COLOR}; color: white; border: none;")
            else:
                btn.setStyleSheet(f"background-color: transparent; color: {text_color}; border: 1px solid {border_color};")
        
        hist_map = {"CPU": (self.cpu_history, "#3b82f6"), "RAM": (self.ram_history, "#a855f7"), 
                    "GPU": (self.gpu_history, "#06b6d4"), "Temp": (self.temp_history, "#ef4444")}
        hist, color = hist_map.get(self.current_graph, (self.cpu_history, "#3b82f6"))
        self.chart.update_data(hist, color)

    def _add_issue(self, text, color, btn_text):
        row = QFrame()
        row.setProperty("class", "IssueRow")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(16, 8, 16, 8)
        
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color}; border: none;")
        rl.addWidget(dot)
        
        lbl = QLabel(text)
        lbl.setStyleSheet("border: none;")
        rl.addWidget(lbl)
        rl.addStretch()
        
        if btn_text:
            btn = QPushButton(btn_text)
            btn.setProperty("class", "IssueBtn")
            btn.setFixedHeight(28)
            rl.addWidget(btn)
        
        self.issues_container.addWidget(row)

    def on_theme_changed(self, is_dark):
        self.ring.set_theme(is_dark)
        self.chart.set_theme(is_dark)
        # Update dynamically set button borders
        self._set_graph(self.current_graph)

    def update_hardware_display(self, data: Dict):
        try:
            # CPU
            cpu = data.get('cpu', {})
            self.cpu_sub.setText(cpu.get('name', 'Unknown CPU'))
            # GPU
            gpus = data.get('gpu', [])
            if gpus and gpus[0].get('name') != 'No GPU detected':
                self.gpu_sub.setText(gpus[0].get('name'))
            # RAM
            ram = data.get('ram', {})
            self.ram_sub.setText(f"Total: {ram.get('total_formatted', '0 GB')}")
            # Storage
            storage_list = data.get('storage', [])
            primary = storage_list[0].get('device', 'Drive 0') if storage_list else 'No Storage'
            self.storage_sub.setText(f"{primary} - HDD/SSD")
        except:
            pass
        
    def update_scores(self, data: Dict):
        score = data.get('overall_score', data.get('health_score', 0))
        color = data.get('color', config.ACCENT_COLOR)
        self.ring.set_score(score, color)

    def _update_live_metrics(self, cpu_pct, mem, disk, net, gpu_pct, temp_c):
        self.cpu_history.append(cpu_pct)
        self.ram_history.append(mem.percent)
        self.gpu_history.append(gpu_pct)
        self.temp_history.append(temp_c)
        
        if len(self.cpu_history) > 60:
            self.cpu_history.pop(0)
            self.ram_history.pop(0)
            self.gpu_history.pop(0)
            self.temp_history.pop(0)
            
        # Update text & progress
        self.cpu_val.setText(f"{cpu_pct:.0f}%")
        self.cpu_prog.setValue(int(cpu_pct))
        
        self.gpu_val.setText(f"{gpu_pct:.0f}%")
        self.gpu_prog.setValue(int(gpu_pct))
        
        self.ram_val.setText(f"{mem.percent:.0f}%")
        self.ram_prog.setValue(int(mem.percent))
        
        self.storage_val.setText(f"{disk.percent:.0f}%")
        self.storage_prog.setValue(int(disk.percent))
        
        # Network Speed Calculation
        current_time = time.time()
        if self.last_net is not None:
            dt = current_time - self.last_net_time
            if dt > 0:
                up_rate = (net.bytes_sent - self.last_net.bytes_sent) / dt
                down_rate = (net.bytes_recv - self.last_net.bytes_recv) / dt
                self.net_up.setText(format_mbps(up_rate))
                self.net_down.setText(format_mbps(down_rate))
        self.last_net = net
        self.last_net_time = current_time

        # Update Uptime & Battery
        uptime_s = time.time() - psutil.boot_time()
        days = int(uptime_s // 86400)
        hours = int((uptime_s % 86400) // 3600)
        mins = int((uptime_s % 3600) // 60)
        self.uptime_val.setText(f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m")
        
        battery = psutil.sensors_battery()
        if battery:
            self.bat_val.setText(f"{int(battery.percent)}%")
            self.bat_prog.setValue(int(battery.percent))
            self.bat_status.setText(" Charging " if battery.power_plugged else " Discharging ")
            self.bat_status.setStyleSheet("color: #22c55e;" if battery.power_plugged else "color: #eab308;")
        
        # Update chart
        hist_map = {"CPU": (self.cpu_history, "#3b82f6"), "RAM": (self.ram_history, "#a855f7"), 
                    "GPU": (self.gpu_history, "#06b6d4"), "Temp": (self.temp_history, "#ef4444")}
        hist, color = hist_map.get(self.current_graph, (self.cpu_history, "#3b82f6"))
        self.chart.update_data(hist, color)

    def _show_detailed_specs(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Detailed System Specifications")
        dialog.setMinimumSize(800, 600)
        dialog.setStyleSheet("background-color: #0f111a; color: #e8eaf6;")
        
        layout = QVBoxLayout(dialog)
        
        title = QLabel("Deep Hardware Diagnostics")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #00B894;")
        layout.addWidget(title)
        
        # Scroll Area for info
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        cl = QVBoxLayout(content)
        
        data = self.deep_info_fetcher.get_all()
        
        # CPU Section
        cpu = data.get("cpu", {})
        self._add_spec_group(cl, "CPU Information", [
            ("Model", cpu.get("name")),
            ("Architecture", cpu.get("architecture")),
            ("Cores (P/L)", f"{cpu.get('cores_physical')} / {cpu.get('cores_logical')}"),
            ("L2 Cache", cpu.get("l2_cache")),
            ("L3 Cache", cpu.get("l3_cache")),
            ("Max Clock", cpu.get("max_clock")),
            ("Voltage", cpu.get("voltage")),
        ])
        
        # RAM Section
        ram = data.get("ram", {})
        sticks = ram.get("sticks", [])
        ram_list = [("Total Capacity", f"{ram.get('total_gb')} GB"), ("Sticks Found", str(ram.get("count")))]
        for i, s in enumerate(sticks):
            ram_list.append((f"Stick {i+1}", f"{s['capacity']} @ {s['speed']} ({s['manufacturer']})"))
        self._add_spec_group(cl, "Memory Subsystem", ram_list)
        
        # GPU Section
        gpus = data.get("gpu", [])
        for i, g in enumerate(gpus):
            self._add_spec_group(cl, f"GPU {i+1}: {g['name']}", [
                ("Driver Version", g.get("driver_version")),
                ("VRAM Total", g.get("vram_total")),
                ("Resolution", g.get("res")),
                ("Refresh Rate", g.get("refresh_rate")),
                ("Current Load", g.get("load", "N/A")),
                ("Temperature", g.get("temp", "N/A")),
            ])
            
        # Motherboard
        mobo = data.get("motherboard", {})
        self._add_spec_group(cl, "Motherboard & BIOS", [
            ("Manufacturer", mobo.get("manufacturer")),
            ("Product", mobo.get("product")),
            ("BIOS Version", mobo.get("bios_version")),
            ("Release Date", mobo.get("bios_date")),
        ])
        
        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        btn_close = QPushButton("Close")
        btn_close.setFixedHeight(40)
        btn_close.setStyleSheet("background-color: #1e2130; border: 1px solid #2d3150; border-radius: 8px;")
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        dialog.exec()

    def _add_spec_group(self, layout, title, items):
        group = QFrame()
        group.setStyleSheet("background-color: #1a1c29; border-radius: 8px; margin-bottom: 10px;")
        gl = QVBoxLayout(group)
        
        t = QLabel(title)
        t.setStyleSheet("font-weight: bold; color: #74b9ff; font-size: 14px; border: none;")
        gl.addWidget(t)
        
        for key, val in items:
            row = QHBoxLayout()
            kl = QLabel(f"{key}:")
            kl.setStyleSheet("color: #8b90b8; border: none;")
            vl = QLabel(str(val))
            vl.setStyleSheet("color: white; border: none; font-weight: bold;")
            row.addWidget(kl)
            row.addStretch()
            row.addWidget(vl)
            gl.addLayout(row)
            
        layout.addWidget(group)

    def closeEvent(self, event):
        self.monitor_thread.stop()
        super().closeEvent(event)

