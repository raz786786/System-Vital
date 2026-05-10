import subprocess
import threading
import time
from typing import Callable, Optional

from benchmarks.cpu_benchmark import CPUBenchmark
from benchmarks.ram_benchmark import RAMBenchmark
from benchmarks.ssd_benchmark import SSDDiskBenchmark
from benchmarks.gpu_benchmark import GPUBenchmark
from benchmarks.cpu_extended import CPUExtendedBenchmark
from benchmarks.hdd_benchmark import HDDBenchmark
from benchmarks.system_benchmark import SystemBenchmark
from engine.history import BenchmarkHistory
from modules.online_comparator import OnlineComparator


class BenchmarkRunner:

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_cb = progress_callback or (lambda msg, pct: None)
        self.history = BenchmarkHistory()
        self.comparator = OnlineComparator()
        self._cancelled = False
        self.results = {}

    def cancel(self):
        self._cancelled = True

    def _set_high_performance(self):
        """Force High Performance power plan for accurate results."""
        try:
            subprocess.run(
                ['powercfg', '/setactive', '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def _restore_power_plan(self):
        try:
            subprocess.run(
                ['powercfg', '/setactive', 'balanced'],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    def _pause_indexing(self):
        try:
            subprocess.run(['sc', 'stop', 'WSearch'], capture_output=True, timeout=5)
        except Exception:
            pass

    def _resume_indexing(self):
        try:
            subprocess.run(['sc', 'start', 'WSearch'], capture_output=True, timeout=5)
        except Exception:
            pass

    def run_all(self, components: list = None) -> dict:
        """
        Run selected components (default: all 4).
        Returns full results with baseline comparison.
        """
        if components is None:
            components = ['CPU', 'RAM', 'SSD', 'GPU', 'HDD', 'System']

        self.progress_cb("Preparing system for benchmarks...", 0)
        self._set_high_performance()
        self._pause_indexing()
        time.sleep(2)  # Let system settle

        all_results = {}
        comparisons = {}
        component_map = {
            'CPU': CPUBenchmark,
            'RAM': RAMBenchmark,
            'SSD': SSDDiskBenchmark,
            'GPU': GPUBenchmark,
            'CPU_Extended': CPUExtendedBenchmark,
            'RAM_Extended': RAMBenchmark,
            'GPU_Extended': GPUBenchmark,
            'SSD_Extended': SSDDiskBenchmark,
            'HDD': HDDBenchmark,
            'System': SystemBenchmark
        }

        # Assign progress ranges per component
        progress_ranges = {
            'CPU': (5, 15),
            'CPU_Extended': (15, 25),
            'RAM': (25, 35),
            'RAM_Extended': (35, 45),
            'SSD': (45, 55),
            'SSD_Extended': (55, 65),
            'GPU': (65, 75),
            'GPU_Extended': (75, 85),
            'HDD': (85, 92),
            'System': (92, 98)
        }

        for comp_name in components:
            if self._cancelled:
                break

            p_start, p_end = progress_ranges.get(comp_name, (0, 100))

            def make_cb(name, start, end):
                def cb(msg, pct):
                    scaled = start + (pct / 100) * (end - start)
                    self.progress_cb(f"[{name}] {msg}", int(scaled))
                return cb

            cb_fn = make_cb(comp_name, p_start, p_end)
            BenchCls = component_map[comp_name]

            try:
                bench = BenchCls(progress_callback=cb_fn)
                result = bench.run_all()

                # Save to history
                run_id = self.history.save_run(result)

                # Compare to baseline
                comparison = self.history.compare_to_baseline(
                    comp_name, result.get("overall_score", 0)
                )

                # Global standing
                standing = self.comparator.get_global_standing(
                    comp_name, result.get("overall_score", 0)
                )

                all_results[comp_name] = result
                all_results[comp_name]["standing"] = standing
                comparisons[comp_name] = comparison

            except Exception as e:
                all_results[comp_name] = {
                    "component": comp_name,
                    "overall_score": 0,
                    "error": str(e),
                    "tests": []
                }

        self._restore_power_plan()
        self._resume_indexing()
        self.progress_cb("All benchmarks complete!", 100)

        return {
            "results": all_results,
            "comparisons": comparisons,
            "summary": self._build_summary(all_results, comparisons)
        }

    @staticmethod
    def _build_summary(results: dict, comparisons: dict) -> dict:
        scores = {k: v.get("overall_score", 0) for k, v in results.items()}
        valid = [s for s in scores.values() if s > 0]
        avg = int(sum(valid) / len(valid)) if valid else 0

        def grade(s):
            if s >= 85_000: return "S"
            if s >= 70_000: return "A"
            if s >= 55_000: return "B"
            if s >= 40_000: return "C"
            if s >= 25_000: return "D"
            return "F"

        def tier(s):
            if s >= 85_000: return "Flagship"
            if s >= 70_000: return "High-End"
            if s >= 55_000: return "Mid-Range"
            if s >= 40_000: return "Entry-Level"
            return "Legacy"

        return {
            "scores": scores,
            "overall_avg": avg,
            "overall_grade": grade(avg),
            "overall_tier": tier(avg),
            "degraded": [
                k for k, v in comparisons.items()
                if v.get("delta_pct", 0) < -5
            ]
        }
