"""
Network Suite Tab — Live ping, speed stats, ping graph, quick fixes.
"""
import time, threading, subprocess, re, os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QLabel, QPushButton, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath
import config


class PingWorker(QThread):
    ping_result = Signal(float)

    def __init__(self):
        super().__init__()
        self._running = True

    def run(self):
        while self._running:
            try:
                out = subprocess.run(
                    ["ping", "-n", "1", "-w", "2000", "8.8.8.8"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                m = re.search(r"time[=<](\d+)", out.stdout)
                self.ping_result.emit(float(m.group(1)) if m else -1)
            except Exception:
                self.ping_result.emit(-1)
            time.sleep(1.5)

    def stop(self):
        self._running = False


class SpeedWorker(QThread):
    speed_result = Signal(dict)

    def run(self):
        info = {"download": "—", "upload": "—", "adapter": "—", "status": "Unknown", "dhcp": "—"}
        try:
            out = subprocess.run(
                ["powershell", "-Command",
                 "Get-NetAdapter | Where-Object Status -eq Up | Select-Object -First 1 Name,LinkSpeed,Status | Format-List"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in out.stdout.splitlines():
                if "Name" in line and ":" in line:
                    info["adapter"] = line.split(":", 1)[1].strip()
                if "LinkSpeed" in line and ":" in line:
                    info["download"] = line.split(":", 1)[1].strip()
                if "Status" in line and ":" in line:
                    info["status"] = line.split(":", 1)[1].strip()
            out2 = subprocess.run(
                ["powershell", "-Command",
                 "(Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway -ne $null} | Select-Object -First 1).NetIPv4Interface.Dhcp"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            dhcp = out2.stdout.strip()
            info["dhcp"] = "DHCP assigned" if "Enabled" in dhcp else "Static IP"
        except Exception:
            pass
        self.speed_result.emit(info)


class PingGraphWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        self.data = []
        self.max_points = 40

    def add_point(self, ms):
        self.data.append(max(0, ms))
        if len(self.data) > self.max_points:
            self.data = self.data[-self.max_points:]
        self.update()

    def paintEvent(self, event):
        if len(self.data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 50, 20, 20, 30
        draw_w = w - pad_l - pad_r
        draw_h = h - pad_t - pad_b
        ceil_val = max(((int(max(self.data)) // 50) + 1) * 50, 50)

        p.setPen(QPen(QColor("#e2e8f0"), 1))
        for frac in [0, 0.25, 0.5, 0.75, 1.0]:
            y = pad_t + draw_h * (1 - frac)
            p.drawLine(pad_l, int(y), w - pad_r, int(y))
            p.setPen(QPen(QColor("#94a3b8"), 1))
            p.drawText(5, int(y + 4), f"{int(ceil_val * frac)}")
            p.setPen(QPen(QColor("#e2e8f0"), 1))

        path = QPainterPath()
        n = len(self.data)
        for i, val in enumerate(self.data):
            x = pad_l + (i / (n - 1)) * draw_w
            y = pad_t + draw_h * (1 - val / ceil_val)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        p.setPen(QPen(QColor("#ef4444"), 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        p.end()


class NetworkSuiteTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.ping_worker = None
        self.create_widgets()
        self._start_monitoring()

    def create_widgets(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self.cl = QVBoxLayout(container)
        self.cl.setContentsMargins(28, 28, 28, 28)
        self.cl.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        t = QLabel("Network Suite")
        t.setStyleSheet("font-size: 24px; font-weight: bold;")
        s = QLabel("Monitor, diagnose, and repair network issues")
        s.setProperty("class", "Muted")
        hv = QVBoxLayout()
        hv.setSpacing(4)
        hv.addWidget(t)
        hv.addWidget(s)
        hdr.addLayout(hv)
        hdr.addStretch()
        for key, label in [("monitor", "📡 Live Monitor"), ("tools", "🔧 Tools"), ("adapter", "📋 Adapter Info")]:
            b = QPushButton(label)
            b.setCheckable(True)
            b.setChecked(key == "monitor")
            b.setProperty("class", "SegmentBtn")
            b.setCursor(Qt.PointingHandCursor)
            hdr.addWidget(b)
        self.cl.addLayout(hdr)

        # Stats row
        sf = QWidget()
        sl = QHBoxLayout(sf)
        sl.setSpacing(14)
        sl.setContentsMargins(0, 0, 0, 0)
        self.ping_val = self._stat(sl, "LIVE PING", "—", "to 8.8.8.8", "#3b82f6")
        self.dl_val = self._stat(sl, "DOWNLOAD", "—", "", "#22c55e")
        self.ul_val = self._stat(sl, "UPLOAD", "—", "", "#a855f7")
        self.status_val = self._stat(sl, "STATUS", "Checking…", "", "#22c55e")
        self.cl.addWidget(sf)

        # Ping graph card
        gc = QFrame()
        gc.setProperty("class", "CardFrame")
        gl = QVBoxLayout(gc)
        gl.setContentsMargins(16, 12, 16, 12)
        gh = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color: #22c55e; font-size: 10px;")
        gt = QLabel("Live Ping Graph — real-time latency to 8.8.8.8")
        gt.setStyleSheet("font-weight: bold; font-size: 13px;")
        gh.addWidget(dot)
        gh.addWidget(gt)
        gh.addStretch()
        self.pgv = QLabel("—")
        self.pgv.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: bold;")
        gh.addWidget(self.pgv)
        gl.addLayout(gh)
        self.ping_graph = PingGraphWidget()
        gl.addWidget(self.ping_graph)
        self.cl.addWidget(gc)

        # Quick fixes card
        fc = QFrame()
        fc.setProperty("class", "CardFrame")
        fl = QVBoxLayout(fc)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.setSpacing(12)
        ft = QLabel("Quick Network Fixes")
        ft.setStyleSheet("font-size: 16px; font-weight: bold;")
        fl.addWidget(ft)
        fg = QGridLayout()
        fg.setSpacing(12)
        fixes = [
            ("🌐", "Flush DNS", "ipconfig /flushdns"),
            ("🔄", "IP Release/Renew", "ipconfig /release & ipconfig /renew"),
            ("📡", "Reset WinSock", "netsh winsock reset"),
            ("🚫", "Clear Proxy", "netsh winhttp reset proxy"),
            ("🛡️", "Check Firewall", "netsh advfirewall show allprofiles state"),
            ("📶", "Reset Adapter", "netsh int ip reset"),
        ]
        for i, (icon, name, cmd) in enumerate(fixes):
            w = QFrame()
            w.setProperty("class", "CardFrame")
            wl = QVBoxLayout(w)
            wl.setContentsMargins(14, 10, 14, 10)
            r = QHBoxLayout()
            r.addWidget(QLabel(icon))
            nl = QLabel(name)
            nl.setStyleSheet("font-weight: bold; font-size: 13px;")
            r.addWidget(nl)
            r.addStretch()
            wl.addLayout(r)
            btn = QPushButton("▷ Run")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("background-color: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: bold; padding: 8px;")
            btn.clicked.connect(lambda _, c=cmd, b=btn: self._run_fix(c, b))
            wl.addWidget(btn)
            fg.addWidget(w, i // 3, i % 3)
        fl.addLayout(fg)
        self.cl.addWidget(fc)
        self.cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _stat(self, parent, title, value, sub, color):
        c = QFrame()
        c.setProperty("class", "CardFrame")
        c.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        l = QVBoxLayout(c)
        l.setContentsMargins(16, 12, 16, 12)
        l.setAlignment(Qt.AlignCenter)
        tl = QLabel(title)
        tl.setAlignment(Qt.AlignCenter)
        tl.setStyleSheet("font-size: 10px; font-weight: bold; color: #94a3b8; letter-spacing: 1px;")
        l.addWidget(tl)
        vl = QLabel(value)
        vl.setAlignment(Qt.AlignCenter)
        vl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        l.addWidget(vl)
        sl = QLabel(sub)
        sl.setAlignment(Qt.AlignCenter)
        sl.setProperty("class", "Muted")
        l.addWidget(sl)
        parent.addWidget(c)
        return vl

    def _start_monitoring(self):
        self.ping_worker = PingWorker()
        self.ping_worker.ping_result.connect(self._on_ping)
        self.ping_worker.start()
        sw = SpeedWorker()
        sw.speed_result.connect(self._on_speed)
        sw.start()
        self._sw = sw

    def _on_ping(self, ms):
        if ms < 0:
            self.ping_val.setText("Timeout")
            self.pgv.setText("Timeout")
        else:
            self.ping_val.setText(f"{ms:.0f}ms")
            self.pgv.setText(f"{ms:.0f}ms")
            self.ping_graph.add_point(ms)

    def _on_speed(self, info):
        self.dl_val.setText(info.get("download", "—"))
        self.ul_val.setText(info.get("upload", "—"))
        st = info.get("status", "Unknown")
        self.status_val.setText("Connected" if st == "Up" else st)
        c = "#22c55e" if st == "Up" else "#ef4444"
        self.status_val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {c};")

    def _run_fix(self, cmd, btn):
        btn.setText("⟳ Running…")
        btn.setEnabled(False)
        import concurrent.futures
        def do():
            try:
                subprocess.run(cmd, shell=True, capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
                return True
            except Exception:
                return False
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(do)
        future.add_done_callback(lambda f: QTimer.singleShot(0, lambda: self._fix_done(btn, f.result())))

    def _fix_done(self, btn, success):
        btn.setText("✅ Done" if success else "⚠ Failed")
        btn.setEnabled(True)
        QTimer.singleShot(3000, lambda: (btn.setText("▷ Run"), btn.setStyleSheet(
            "background-color: #3b82f6; color: white; border: none; border-radius: 6px; font-weight: bold; padding: 8px;")))

    def closeEvent(self, event):
        if self.ping_worker:
            self.ping_worker.stop()
            self.ping_worker.wait(2000)
        super().closeEvent(event)
