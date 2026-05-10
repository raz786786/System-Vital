import os
import math
import time
import numpy as np
import threading
import datetime
import config
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, 
    QLabel, QPushButton, QScrollArea, QSizePolicy, QProgressBar,
    QCheckBox, QMessageBox, QFileDialog, QTextEdit
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

ALL_COMPONENTS = [
    "CPU", "CPU_Extended",
    "GPU", "GPU_Extended",
    "RAM", "RAM_Extended",
    "SSD", "SSD_Extended",
    "HDD", "System",
]

GRADE_COLORS = {
    "S": "#FFD700", "A": "#00B894", "B": "#74B9FF",
    "C": "#FDCB6E", "D": "#E17055", "F": "#D63031",
    "?": "#888888",
}

SEVERITY_COLORS = {
    "critical":       "#D63031",
    "warning":        "#FDCB6E",
    "ok":             "#00B894",
    "improved":       "#74B9FF",
    "major_improved": "#FFD700",
    "no_baseline":    "#888888",
}

class BenchmarkWorkerThread(QThread):
    result_ready = Signal(dict)
    progress_update = Signal(str, int)
    
    def __init__(self, components=None):
        super().__init__()
        self.components = components or []
        from engine.benchmark_runner import BenchmarkRunner
        self.runner = BenchmarkRunner(progress_callback=self._cb)
        
    def _cb(self, msg, pct):
        self.progress_update.emit(msg, pct)
        
    def run(self):
        try:
            res = self.runner.run_all(self.components)
            self.result_ready.emit(res)
        except Exception as e:
            self.result_ready.emit({'error': str(e)})

    def cancel(self):
        if self.runner:
            self.runner.cancel()


class StressWorkerThread(QThread):
    telemetry_update = Signal(dict)
    
    def __init__(self, mode="cpu"):
        super().__init__()
        self.mode = mode
        from engine.stress_runner import StressRunner
        self.runner = StressRunner(telemetry_callback=self._telemetry_cb)
        
    def _telemetry_cb(self, data):
        self.telemetry_update.emit(data)
        
    def run(self):
        if self.mode == "cpu":
            self.runner.run_cpu_stress()
        elif self.mode == "ram":
            self.runner.run_ram_stress()
        elif self.mode == "gpu":
            self.runner.run_gpu_stress()
        elif self.mode == "system":
            self.runner.run_full_stress()
            
        # Keep thread alive while runner is working
        while not self.runner._stop_event.is_set():
            time.sleep(0.5)

    def stop(self):
        self.runner.stop()


class BenchmarkTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.active_subtab = "run"
        
        # Lazy-load heavy engine modules to speed up tab open time
        from engine.history import BenchmarkHistory
        from engine.scorer import SystemScoreAggregator
        from engine.report_exporter import ReportExporter
        
        self.history = BenchmarkHistory()
        self.aggregator = SystemScoreAggregator()
        self.exporter = ReportExporter()
        
        # Defer AI init — will be created on first use
        self._degradation = None
        
        self.stress_runner = None
        self.stress_thread = None
        self.stress_cards = {}

        self._last_results = {}
        self._last_comparisons = {}
        self._last_summary = {}
        self._last_ai_text = ""
        self._suggested_repairs = []
        self.runner_thread = None
        self.comp_checks = {}
        
        self.create_widgets()

    @property
    def degradation(self):
        if self._degradation is None:
            from engine.ai_factory import AIFactory
            from engine.degradation import DegradationAnalyzer
            provider = AIFactory.get_provider(config.AI_PROVIDER, config.GEMINI_API_KEY)
            self._degradation = DegradationAnalyzer(provider)
        return self._degradation

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
        title = QLabel("Hardware Benchmark")
        title.setProperty("class", "Title")
        sub = QLabel("Test CPU, GPU, RAM, Storage, and System Performance")
        sub.setProperty("class", "Muted")
        header_text.addWidget(title)
        header_text.addWidget(sub)
        header.addLayout(header_text)
        header.addStretch()
        self.container_layout.addLayout(header)
        
        # Sub-tab Bar
        tab_frame = QFrame()
        tab_frame.setProperty("class", "SegmentFrame")
        tab_layout = QHBoxLayout(tab_frame)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)
        
        self.subtab_btns = {}
        tabs = [
            ("run", "Run Benchmark"), 
            ("results", "Results"), 
            ("compare", "Compare"),
            ("history", "History"), 
            ("ai", "AI Analysis"),
            ("stress", "Stress Test")
        ]
        for key, label in tabs:
            btn = QPushButton(label)
            btn.setProperty("class", "SegmentBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            
            if key == "run":
                btn.setChecked(True)
                
            btn.clicked.connect(lambda checked, k=key: self._switch_subtab(k))
            tab_layout.addWidget(btn)
            self.subtab_btns[key] = btn
            
        tab_layout.addStretch()
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
        
        self._build_run()

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

    def _switch_subtab(self, key):
        for k, btn in self.subtab_btns.items():
            btn.setChecked(k == key)
            
        self._clear_content()
        self.active_subtab = key

        if key == "run":
            self._build_run()
        elif key == "results":
            self._build_results()
        elif key == "compare":
            self._build_compare()
        elif key == "history":
            self._build_history()
        elif key == "ai":
            self._build_ai()
        elif key == "stress":
            self._build_stress()

    # ── RUN TAB ────────────────────────────────────────────
    
    def _build_run(self):
        # Header
        run_header = QHBoxLayout()
        run_title = QLabel("Select Components to Benchmark")
        run_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #74b9ff;")
        
        self.check_all = QCheckBox("Check All")
        self.check_all.setChecked(True)
        self.check_all.stateChanged.connect(self._toggle_all_checkboxes)
        
        run_header.addWidget(run_title)
        run_header.addStretch()
        run_header.addWidget(self.check_all)
        self.content_layout.addLayout(run_header)
        
        comp_frame = QFrame()
        comp_frame.setProperty("class", "CardFrame")
        comp_grid_layout = QGridLayout(comp_frame)
        comp_grid_layout.setSpacing(10)

        self.comp_checks = {}
        for i, comp in enumerate(ALL_COMPONENTS):
            cb = QCheckBox(comp.replace("_Extended", "+"))
            cb.setChecked(True)
            self.comp_checks[comp] = cb
            comp_grid_layout.addWidget(cb, i // 2, i % 2)
        
        self.content_layout.addWidget(comp_frame)

        # Quick Component Scores (New User Request)
        if self._last_results:
            scores_frame = QFrame()
            scores_frame.setStyleSheet("background-color: #161925; border-radius: 8px; padding: 10px;")
            sl = QHBoxLayout(scores_frame)
            sl.setSpacing(15)
            
            for comp, res in self._last_results.items():
                if res.get("overall_score", 0) <= 0: continue
                item = QVBoxLayout()
                nl = QLabel(comp.replace("_Extended", "+"))
                nl.setStyleSheet("color: #8b90b8; font-size: 11px; font-weight: bold;")
                nl.setAlignment(Qt.AlignCenter)
                sl_score = QLabel(f"{res['overall_score']:,}")
                sl_score.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
                sl_score.setAlignment(Qt.AlignCenter)
                item.addWidget(nl)
                item.addWidget(sl_score)
                sl.addLayout(item)
            
            sl.addStretch()
            self.content_layout.addWidget(scores_frame)



        
        # Launch Card
        launch_card = QFrame()
        launch_card.setProperty("class", "CardFrame")
        lc_layout = QVBoxLayout(launch_card)
        lc_layout.setContentsMargins(24, 24, 24, 24)
        
        l_title = QLabel("System Performance Suite")
        l_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        l_desc = QLabel("Run a comprehensive test of your selected hardware.")
        l_desc.setProperty("class", "Muted")
        
        self.run_btn = QPushButton("🚀 START BENCHMARK")
        self.run_btn.setProperty("class", "PrimaryButton")
        self.run_btn.setFixedHeight(45)
        self.run_btn.setCursor(Qt.PointingHandCursor)
        self.run_btn.clicked.connect(self._start_benchmark)
        
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(12)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.hide()
        
        self.prog_lbl = QLabel("")
        self.prog_lbl.setProperty("class", "Muted")
        self.prog_lbl.hide()
        
        lc_layout.addWidget(l_title)
        lc_layout.addWidget(l_desc)
        lc_layout.addSpacing(20)
        lc_layout.addWidget(self.run_btn)
        lc_layout.addWidget(self.prog_bar)
        lc_layout.addWidget(self.prog_lbl)
        self.content_layout.addWidget(launch_card)
        
        # Overall Score Card
        if self._last_results:
            self._build_overall_score_card(self.content_layout)

    def _toggle_all_checkboxes(self, state):
        checked = (state == 2) # Qt.CheckState.Checked
        for cb in self.comp_checks.values():
            cb.setChecked(checked)

    def _build_overall_score_card(self, parent_layout):
        agg = self.aggregator.compute_overall(
            {k: v.get("overall_score", 0) for k, v in self._last_results.items()}
        )
        
        overall_card = QFrame()
        overall_card.setProperty("class", "CardFrame")
        overall_card.setStyleSheet("background-color: #1e2130; border: 1px solid #3b82f6;")
        ol = QVBoxLayout(overall_card)
        ol.setAlignment(Qt.AlignCenter)
        
        l1 = QLabel("OVERALL SCORE")
        l1.setStyleSheet("color: #3b82f6; font-weight: bold; letter-spacing: 2px;")
        l1.setAlignment(Qt.AlignCenter)
        
        l2 = QLabel(f"{agg['overall_score']:,}")
        l2.setStyleSheet("font-size: 48px; font-weight: bold; color: white;")
        l2.setAlignment(Qt.AlignCenter)
        
        grade_color = GRADE_COLORS.get(agg['overall_grade'], "#888")
        l3 = QLabel(f"Grade: {agg['overall_grade']}")
        l3.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {grade_color};")
        l3.setAlignment(Qt.AlignCenter)
        
        l4 = QLabel(f"Tier: {agg['overall_tier']}")
        l4.setProperty("class", "Muted")
        l4.setAlignment(Qt.AlignCenter)
        
        ol.addWidget(l1)
        ol.addWidget(l2)
        ol.addWidget(l3)
        ol.addWidget(l4)
        parent_layout.addWidget(overall_card)
        
    def _start_benchmark(self):
        comps = [comp for comp, cb in self.comp_checks.items() if cb.isChecked()]
        if not comps:
            QMessageBox.warning(self, "No Components", "Please select at least one component.")
            return

        self.run_btn.setText("Cancel Benchmark")
        self.run_btn.setStyleSheet("background-color: #ef4444; color: white; border: none;")
        self.run_btn.clicked.disconnect()
        self.run_btn.clicked.connect(self._cancel_benchmark)
        
        self.prog_bar.show()
        self.prog_bar.setValue(0)
        self.prog_lbl.show()
        self.prog_lbl.setText("Initializing...")
        
        self.runner_thread = BenchmarkWorkerThread(components=comps)
        self.runner_thread.progress_update.connect(self._update_progress)
        self.runner_thread.result_ready.connect(self._on_benchmark_done)
        self.runner_thread.start()
        
    def _cancel_benchmark(self):
        if self.runner_thread:
            self.runner_thread.cancel()
        self.prog_lbl.setText("Cancelling...")
        
    def _update_progress(self, msg, pct):
        self.prog_bar.setValue(pct)
        self.prog_lbl.setText(msg)
        
    def _on_benchmark_done(self, full_results):
        if "error" in full_results:
            QMessageBox.critical(self, "Error", full_results["error"])
            self._switch_subtab("run")
            return

        self._last_results = full_results.get("results", {})
        self._last_comparisons = full_results.get("comparisons", {})
        self._last_summary = full_results.get("summary", {})

        # Run AI analysis in background
        threading.Thread(target=self._background_ai_analysis, daemon=True).start()

        self._switch_subtab("results")

    # ── RESULTS TAB ────────────────────────────────────────

    def _build_results(self):
        if not self._last_results:
            l = QLabel("No benchmark results yet. Run a benchmark first.")
            l.setProperty("class", "Muted")
            self.content_layout.addWidget(l)
            return

        # Top Control Bar
        ctrl_frame = QFrame()
        ctrl_layout = QHBoxLayout(ctrl_frame)
        
        btn_base = QPushButton("🎯 Set as Baseline")
        btn_base.setProperty("class", "PrimaryButton")
        btn_base.clicked.connect(self._set_as_baseline)
        
        btn_exp = QPushButton("📤 Export Report")
        btn_exp.setProperty("class", "SecondaryButton")
        btn_exp.clicked.connect(self._export_report)
        
        ctrl_layout.addWidget(btn_base)
        ctrl_layout.addWidget(btn_exp)
        ctrl_layout.addStretch()
        self.content_layout.addWidget(ctrl_frame)

        self._build_overall_score_card(self.content_layout)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(16)
        
        col = 0
        row = 0
        for comp, result in self._last_results.items():
            if result.get("overall_score", 0) <= 0: continue

            score = result.get("overall_score", 0)
            grade = result.get("grade", "?")
            tier = result.get("tier", "Unknown")

            card = QFrame()
            card.setProperty("class", "CardFrame")
            cl = QVBoxLayout(card)
            
            nm = QLabel(comp.replace("_Extended", "+"))
            nm.setStyleSheet("color: #74b9ff; font-weight: bold; font-size: 16px;")
            nm.setAlignment(Qt.AlignCenter)
            
            sc = QLabel(f"{score:,}")
            sc.setStyleSheet("font-size: 28px; font-weight: bold;")
            sc.setAlignment(Qt.AlignCenter)

            gr = QLabel(grade)
            gr.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {GRADE_COLORS.get(grade, '#888')};")
            gr.setAlignment(Qt.AlignCenter)

            tr = QLabel(tier)
            tr.setProperty("class", "Muted")
            tr.setAlignment(Qt.AlignCenter)
            
            # Global Standing
            standing = result.get("standing", {})
            st_lbl = QLabel(f"🌐 World Top {100 - standing.get('percentile', 50)}%")
            st_lbl.setStyleSheet("color: #00B894; font-weight: bold; font-size: 11px; margin-top: 4px;")
            st_lbl.setAlignment(Qt.AlignCenter)
            
            cl.addWidget(nm)
            cl.addWidget(sc)
            cl.addWidget(gr)
            cl.addWidget(tr)
            cl.addWidget(st_lbl)
            grid.addWidget(card, row, col)
            
            col += 1
            if col > 3:
                col = 0
                row += 1
            
        self.content_layout.addWidget(grid_widget)

        # Detailed Test Results (New User Request)
        details_label = QLabel("Detailed Test Breakdown")
        details_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px; color: #74b9ff;")
        self.content_layout.addWidget(details_label)

        for comp, result in self._last_results.items():
            if result.get("overall_score", 0) <= 0: continue
            
            group_box = QFrame()
            group_box.setStyleSheet("background-color: #1a1c29; border-radius: 10px; margin-bottom: 15px;")
            gl = QVBoxLayout(group_box)
            
            head = QLabel(f"📊 {comp} Detailed Tests")
            head.setStyleSheet("font-weight: bold; color: white; font-size: 14px; padding-bottom: 5px; border-bottom: 1px solid #2d3150;")
            gl.addWidget(head)
            
            tests = result.get("tests", [])
            for t in tests:
                row = QHBoxLayout()
                tn = QLabel(t.get("name", "Unknown Test"))
                tn.setStyleSheet("color: #e8eaf6;")
                
                val = f"{t.get('value', 0)} {t.get('unit', '')}"
                if t.get("error"):
                    val = f"❌ {t['error']}"
                    
                tv = QLabel(val)
                tv.setStyleSheet("color: #00B894; font-weight: bold;")
                
                ts = QLabel(f"Score: {t.get('score', 0):,}")
                ts.setStyleSheet("color: #8b90b8; font-size: 11px;")
                
                row.addWidget(tn)
                row.addStretch()
                row.addWidget(tv)
                row.addSpacing(20)
                row.addWidget(ts)
                gl.addLayout(row)
                
            self.content_layout.addWidget(group_box)


    # ── COMPARE TAB ────────────────────────────────────────

    def _build_compare(self):
        if not self._last_comparisons:
            l = QLabel("No comparison data available. Run a benchmark first.")
            l.setProperty("class", "Muted")
            self.content_layout.addWidget(l)
            return

        for comp, cmp in self._last_comparisons.items():
            dp = cmp.get("delta_pct", 0)
            severity = cmp.get("severity", "ok")
            status = cmp.get("status", "")
            advice = cmp.get("advice", "")
            base_sc = cmp.get("baseline_score", 0)
            curr_sc = cmp.get("current_score", 0)

            sev_color = SEVERITY_COLORS.get(severity, "#888")

            card = QFrame()
            card.setProperty("class", "CardFrame")
            card.setStyleSheet(f"border-left: 4px solid {sev_color};")
            cl = QVBoxLayout(card)

            head_layout = QHBoxLayout()
            nm = QLabel(comp)
            nm.setStyleSheet("font-weight: bold; font-size: 16px;")
            st = QLabel(status)
            st.setStyleSheet(f"font-weight: bold; color: {sev_color};")
            
            head_layout.addWidget(nm)
            head_layout.addWidget(st)
            head_layout.addStretch()
            cl.addLayout(head_layout)

            metrics_layout = QHBoxLayout()
            ml1 = QLabel(f"Baseline: {base_sc:,}")
            ml2 = QLabel(f"Current: {curr_sc:,}")
            ml3 = QLabel(f"Change: {dp:+.1f}%")
            ml3.setStyleSheet(f"color: {sev_color}; font-weight: bold;")
            
            metrics_layout.addWidget(ml1)
            metrics_layout.addWidget(ml2)
            metrics_layout.addWidget(ml3)
            metrics_layout.addStretch()
            cl.addLayout(metrics_layout)

            if advice:
                adv = QLabel(f"💡 {advice}")
                adv.setWordWrap(True)
                adv.setStyleSheet("color: #fdcb6e; margin-top: 5px;")
                cl.addWidget(adv)

            self.content_layout.addWidget(card)

    # ── HISTORY TAB ────────────────────────────────────────

    def _build_history(self):
        import matplotlib
        matplotlib.use("qtagg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
        
        comps = self.history.get_all_components()
        if not comps:
            l = QLabel("No historical data found. Run a benchmark first.")
            l.setProperty("class", "Muted")
            self.content_layout.addWidget(l)
            return

        history_data = {}
        for comp in comps:
            trend = self.history.get_trend_data(comp, n_runs=20)
            if not trend.get("insufficient_data"):
                history_data[comp] = trend

        if not history_data:
            l = QLabel("Insufficient historical data for charting.")
            l.setProperty("class", "Muted")
            self.content_layout.addWidget(l)
            return

        n_plots = len(history_data)
        cols = min(n_plots, 2)
        rows = math.ceil(n_plots / cols) if n_plots > 0 else 1

        fig, axes = plt.subplots(
            rows, cols,
            figsize=(10, max(4, rows * 3)),
            facecolor="#0f0f0f",
            squeeze=False
        )
        fig.suptitle("Benchmark Score History", color="#eaeaea", fontsize=14, fontweight="bold")

        ax_flat = axes.flat
        for i, (comp, data) in enumerate(history_data.items()):
            ax = next(ax_flat)
            scores = data.get("scores", [])
            dates = data.get("dates", [])
            x = list(range(len(scores)))

            ax.set_facecolor("#1a1a2e")
            ax.tick_params(colors="#eaeaea", labelsize=8)
            for spine in ax.spines.values():
                spine.set_color("#2a2a4a")
            ax.grid(True, color="#2a2a4a", alpha=0.5)

            ax.plot(x, scores, color="#e94560", linewidth=2, marker="o")
            ax.fill_between(x, scores, alpha=0.15, color="#e94560")
            
            if len(x) > 2:
                z = np.polyfit(x, scores, 1)
                p = np.poly1d(z)
                ax.plot(x, p(x), "--", color="#fdcb6e", alpha=0.7)

            ax.set_title(comp, color="#74b9ff", fontsize=10)

        for ax in ax_flat:
            ax.set_visible(False)

        plt.tight_layout()
        
        canvas = FigureCanvas(fig)
        self.content_layout.addWidget(canvas)

    # ── AI TAB ─────────────────────────────────────────────

    def _build_ai(self):
        ctrl = QFrame()
        ctrl_layout = QHBoxLayout(ctrl)
        
        btn = QPushButton("🤖 Re-Analyze")
        btn.setProperty("class", "PrimaryButton")
        btn.clicked.connect(self._run_ai_analysis)
        ctrl_layout.addWidget(btn)
        
        self.ai_status = QLabel("")
        self.ai_status.setProperty("class", "Muted")
        ctrl_layout.addWidget(self.ai_status)
        ctrl_layout.addStretch()
        self.content_layout.addWidget(ctrl)

        self.ai_box = QTextEdit()
        self.ai_box.setReadOnly(True)
        self.ai_box.setStyleSheet("background-color: #1a1a2e; color: #eaeaea; font-family: Consolas; font-size: 14px; padding: 10px;")
        
        if self._last_ai_text:
            self.ai_box.setText(self._last_ai_text)
        else:
            self.ai_box.setText("Run a benchmark to get AI-powered insights.")
            
        self.content_layout.addWidget(self.ai_box)
        
        if self._suggested_repairs:
            r_lbl = QLabel("Actionable Repairs:")
            r_lbl.setStyleSheet("font-weight: bold; margin-top: 15px; color: #74b9ff;")
            self.content_layout.addWidget(r_lbl)
            
            from utilities.repair import REPAIR_UTILITIES
            repair_layout = QHBoxLayout()
            for r_id in self._suggested_repairs:
                tool = next((t for t in REPAIR_UTILITIES if t['id'] == r_id), None)
                if tool:
                    r_btn = QPushButton(f"{tool['icon']} {tool['name']}")
                    r_btn.setStyleSheet(f"background-color: {tool['color']}20; color: {tool['color']}; border: 1px solid {tool['color']}; padding: 8px;")
                    r_btn.clicked.connect(lambda checked, t=tool: self._run_specific_repair(t))
                    repair_layout.addWidget(r_btn)
            repair_layout.addStretch()
            self.content_layout.addLayout(repair_layout)

    def _run_specific_repair(self, tool):
        ans = QMessageBox.question(self, "Run Repair", f"Do you want to run {tool['name']}?\n\n{tool['desc']}")
        if ans == QMessageBox.StandardButton.Yes:
            res = tool['run']()
            if res.get('success'):
                QMessageBox.information(self, "Success", res.get('message'))
            else:
                QMessageBox.critical(self, "Error", res.get('message'))

    def _background_ai_analysis(self):
        try:
            trends = {comp: self.history.get_trend_data(comp) for comp in self._last_results}
            text, repairs = self.degradation.analyze(self._last_results, self._last_comparisons, trends)
            self._last_ai_text = text
            self._suggested_repairs = repairs
        except Exception as e:
            self._last_ai_text = f"AI analysis failed: {e}"
            self._suggested_repairs = []

    def _run_ai_analysis(self):
        if not self._last_results:
            QMessageBox.information(self, "No Data", "Run a benchmark first.")
            return
        self.ai_status.setText("Analyzing...")
        self._background_ai_analysis()
        self._build_ai()

    # ── STRESS TAB ─────────────────────────────────────────

    def _build_stress(self):
        self.stress_cards = {}
        
        # Header with Stop All button
        header_layout = QHBoxLayout()
        lbl = QLabel("System Stress Tests")
        lbl.setProperty("class", "Title")
        
        sub = QLabel("⚠ These tests load your hardware to 100%. Ensure cooling is adequate.")
        sub.setStyleSheet("color: #ef4444; font-weight: bold;")
        
        stop_all_btn = QPushButton("🛑 STOP ALL TESTS")
        stop_all_btn.setStyleSheet("background-color: #d6303120; color: #d63031; border: 1px solid #d63031; font-weight: bold; padding: 8px 16px;")
        stop_all_btn.clicked.connect(self._stop_stress)
        header_layout.addWidget(lbl)
        header_layout.addStretch()
        header_layout.addWidget(stop_all_btn)
        self.content_layout.addLayout(header_layout)
        self.content_layout.addWidget(sub)
        
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(16)
        
        tests = [
            ("cpu", "CPU Burner", "Multi-threaded integer load", "#ff7675"),
            ("ram", "Memory Torture", "Allocating & scanning VRAM/RAM", "#a29bfe"),
            ("gpu", "GPU Fire-Strike", "Heavy 3D rendering loop", "#81ecec"),
            ("system", "Full System Melt", "CPU + GPU + RAM simultaneous", "#fab1a0"),
        ]
        
        for i, (key, name, desc, color) in enumerate(tests):
            card = QFrame()
            card.setProperty("class", "CardFrame")
            cl = QVBoxLayout(card)
            
            # Icon + Title
            icon_lbl = QLabel("🔥" if key != "system" else "🌋")
            icon_lbl.setStyleSheet("font-size: 24px;")
            title_lbl = QLabel(name)
            title_lbl.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
            
            dl = QLabel(desc)
            dl.setProperty("class", "Muted")
            dl.setWordWrap(True)
            
            # Telemetry area
            tele_layout = QVBoxLayout()
            t_lbl = QLabel("Status: Ready")
            t_lbl.setObjectName("status_lbl")
            t_lbl.setStyleSheet("color: #8b90b8; font-size: 12px;")
            l_lbl = QLabel("Load: --%")
            l_lbl.setObjectName("load_lbl")
            l_lbl.setStyleSheet("color: #8b90b8; font-size: 12px;")
            temp_lbl = QLabel("Temp: --°C")
            temp_lbl.setObjectName("temp_lbl")
            temp_lbl.setStyleSheet("color: #8b90b8; font-size: 12px;")
            
            tele_layout.addWidget(t_lbl)
            tele_layout.addWidget(l_lbl)
            tele_layout.addWidget(temp_lbl)
            
            btn = QPushButton("Run Test")
            btn.setObjectName("run_btn")
            btn.setStyleSheet(f"background-color: {color}20; color: {color}; border: 1px solid {color}; font-weight: bold; padding: 6px;")
            btn.clicked.connect(lambda checked, k=key: self._toggle_stress(k))
            
            cl.addWidget(icon_lbl)
            cl.addWidget(title_lbl)
            cl.addWidget(dl)
            cl.addLayout(tele_layout)
            cl.addStretch()
            cl.addWidget(btn)
            
            grid.addWidget(card, i//2, i%2)
            self.stress_cards[key] = {
                "card": card,
                "btn": btn,
                "status": t_lbl,
                "load": l_lbl,
                "temp": temp_lbl
            }
            
        self.content_layout.addWidget(grid_widget)

    def _toggle_stress(self, key):
        if self.stress_thread and self.stress_thread.isRunning():
            self._stop_stress()
            # but usually we only run one at a time
            return
            
        # Start new stress test
        for k, widgets in self.stress_cards.items():
            if k == key:
                widgets["btn"].setText("STOP")
                widgets["btn"].setStyleSheet("background-color: #ef4444; color: white; border: none; font-weight: bold; padding: 6px;")
                widgets["status"].setText("Status: RUNNING")
                widgets["status"].setStyleSheet("color: #00B894; font-weight: bold;")
            else:
                widgets["btn"].setEnabled(False)
                
        self.stress_thread = StressWorkerThread(mode=key)
        self.stress_thread.telemetry_update.connect(lambda data, k=key: self._update_stress_telemetry(k, data))
        self.stress_thread.start()

    def _stop_stress(self):
        if self.stress_thread:
            self.stress_thread.stop()
            self.stress_thread.terminate() # Forceful on Windows if needed
            self.stress_thread.wait()
            self.stress_thread = None
            
        for k, widgets in self.stress_cards.items():
            widgets["btn"].setEnabled(True)
            widgets["btn"].setText("Run Test")
            color = "#ef4444" if k == "cpu" else "#a855f7" if k == "ram" else "#06b6d4" if k == "gpu" else "#f97316"
            widgets["btn"].setStyleSheet(f"background-color: {color}20; color: {color}; border: 1px solid {color}; font-weight: bold; padding: 6px;")
            widgets["status"].setText("Status: Stopped")
            widgets["status"].setStyleSheet("color: #8b90b8; font-size: 12px;")

    def _update_stress_telemetry(self, key, data):
        if key not in self.stress_cards: return
        w = self.stress_cards[key]
        
        if key == "cpu":
            w["load"].setText(f"Load: {data.get('cpu_load', 0):.1f}%")
            temp = data.get("cpu_temp")
            w["temp"].setText(f"Temp: {temp:.1f}°C" if temp else "Temp: N/A")
        elif key == "ram":
            ram = data.get("ram", {})
            w["load"].setText(f"Usage: {ram.get('percent', 0):.1f}%")
            w["temp"].setText(f"Used: {ram.get('used_gb', 0):.2f} GB")
        elif key == "gpu":
            gpu = data.get("gpu", {})
            w["load"].setText(f"Load: {gpu.get('load_pct', 0):.1f}%")
            temp = gpu.get("temp_c")
            w["temp"].setText(f"Temp: {temp:.1f}°C" if temp else "Temp: N/A")
        elif key == "system":
            w["load"].setText(f"CPU: {data.get('cpu_load', 0):.1f}%")
            temp = data.get("cpu_temp")
            w["temp"].setText(f"CPU Temp: {temp:.1f}°C" if temp else "CPU Temp: N/A")

    # ── EXPORT / BASELINE ──────────────────────────────────

    def _set_as_baseline(self):
        ans = QMessageBox.question(self, "Set Baseline", "Set current results as new baseline?")
        if ans == QMessageBox.StandardButton.Yes:
            for comp, result in self._last_results.items():
                if result.get("overall_score", 0) > 0:
                    run_id = self.history.save_run(result, notes="Manual baseline", auto_baseline=False)
                    self.history.set_baseline(comp, run_id)
            QMessageBox.information(self, "Success", "Baseline updated.")

    def _export_report(self):
        now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", f"SYSTEM VITAL_report_{now}.html", "HTML Files (*.html);;PDF Files (*.pdf)")
        if path:
            if path.endswith(".pdf"):
                out = self.exporter.export_pdf(self._last_results, self._last_comparisons, self._last_ai_text, path)
            else:
                out = self.exporter.export_html(self._last_results, self._last_comparisons, self._last_ai_text, path)
            
            if out:
                QMessageBox.information(self, "Export Complete", f"Saved to {out}")
