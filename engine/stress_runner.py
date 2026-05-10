"""
SYSTEM VITAL STRESS TESTING ENGINE
Handles long-duration endurance loops for CPU, GPU, RAM, and System.
Uses threading instead of multiprocessing to avoid Windows handle errors.
Provides real-time telemetry and safety monitoring.
"""

import time
import threading
import os
import numpy as np
from typing import Callable, Optional

from utils.telemetry import TelemetrySampler


def _cpu_burn_thread(stop_event: threading.Event):
    """Pure CPU burn — tight integer arithmetic loop."""
    a, b = 123456789, 987654321
    while not stop_event.is_set():
        for _ in range(100_000):
            a = (a ^ b) & 0xFFFFFFFF
            b = (b + a) & 0xFFFFFFFF
            a = (a * 6364136223846793005 + 1) & 0xFFFFFFFF
            b = (b >> 3) | ((b & 0x7) << 29)


def _ram_burn_thread(stop_event: threading.Event, size_mb: int = 256):
    """RAM stress — allocate and thrash large numpy arrays."""
    n = (size_mb * 1024 * 1024) // 8
    while not stop_event.is_set():
        a = np.ones(n, dtype=np.float64)
        b = np.ones(n, dtype=np.float64) * 2.0
        c = np.empty(n, dtype=np.float64)
        np.add(a, b, out=c)
        np.multiply(c, 3.14159, out=a)
        _ = a.sum()
        del a, b, c


class StressRunner:
    def __init__(self, telemetry_callback: Optional[Callable] = None):
        self.telemetry_cb = telemetry_callback or (lambda data: None)
        self.sampler = TelemetrySampler()
        self._stop_event = threading.Event()
        self._is_running = False
        self._threads = []

    def stop(self):
        self._stop_event.set()
        self._is_running = False
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads = []

    def _telemetry_loop(self, temp_key="cpu_temp", temp_limit=95):
        """Periodically sample telemetry and emit updates."""
        while not self._stop_event.is_set():
            time.sleep(1.0)
            data = self.sampler.get_all()
            self.telemetry_cb(data)
            
            # Safety check
            temp = data.get(temp_key)
            if temp and temp > temp_limit:
                self.stop()
                break

    def run_cpu_stress(self):
        """CPU torture test using all logical cores."""
        self._is_running = True
        self._stop_event.clear()

        n_threads = os.cpu_count() or 4
        for _ in range(n_threads):
            t = threading.Thread(target=_cpu_burn_thread, args=(self._stop_event,), daemon=True)
            t.start()
            self._threads.append(t)

        # Telemetry monitor
        tm = threading.Thread(target=self._telemetry_loop, args=("cpu_temp", 95), daemon=True)
        tm.start()
        self._threads.append(tm)

    def run_ram_stress(self):
        """RAM torture test — thrashes memory with numpy."""
        self._is_running = True
        self._stop_event.clear()

        n_threads = min(os.cpu_count() or 4, 4)
        size_per = 256  # MB per thread
        for _ in range(n_threads):
            t = threading.Thread(target=_ram_burn_thread, args=(self._stop_event, size_per), daemon=True)
            t.start()
            self._threads.append(t)

        tm = threading.Thread(target=self._telemetry_loop, args=("cpu_temp", 95), daemon=True)
        tm.start()
        self._threads.append(tm)

    def run_gpu_stress(self):
        """GPU torture test — heavy shader loops."""
        self._is_running = True
        self._stop_event.clear()

        def gpu_loop():
            try:
                from benchmarks.gpu_benchmark import GPUBenchmark
                bench = GPUBenchmark()
                bench._init_context()
                while not self._stop_event.is_set():
                    try:
                        bench.test_mandelbrot()
                    except Exception:
                        pass
                    data = self.sampler.get_all()
                    self.telemetry_cb(data)
                    
                    if data.get("gpu", {}).get("temp_c", 0) > 85:
                        self.stop()
                        break
                if bench.ctx:
                    try: bench.ctx.release()
                    except Exception: pass
            except Exception:
                pass

        t = threading.Thread(target=gpu_loop, daemon=True)
        t.start()
        self._threads.append(t)

    def run_full_stress(self):
        """Simultaneous load on CPU, RAM, and GPU."""
        self._is_running = True
        self._stop_event.clear()
        self.run_cpu_stress()
        self.run_ram_stress()
        self.run_gpu_stress()
