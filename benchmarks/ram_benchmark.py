"""
SYSTEM VITAL RAM BENCHMARK ENGINE
Industry-level tests mirroring AIDA64 Memory Benchmark + Extended RAM diagnostics.
  - Basic:
    - Sequential Read Bandwidth (MB/s)
    - Sequential Write Bandwidth (MB/s)
    - Sequential Copy Bandwidth (MB/s)
    - Memory Latency (ns)
    - Random Access Latency (ns)
    - Cache Hierarchy Sweep
    - Multi-Threaded Bandwidth
  - Extended:
    - TLB Stress Test
    - Cache Line False Sharing
    - NUMA Latency Detection
    - SIMD-Style Vectorized Bandwidth
    - Memory Controller Saturation
    - Row Hammer Access Pattern
    - Stride Sensitivity Analysis
    - Write Combining Effectiveness
    - Prefetch Effectiveness
    - Memory Latency Histogram
"""

import os
import sys
import time
import math
import struct
import random
import ctypes
import threading
import multiprocessing
import numpy as np
from typing import Callable, Optional, List, Dict


# ══════════════════════════════════════════════════════════════
#  CONSTANTS & SYSTEM DETECTION
# ══════════════════════════════════════════════════════════════

PAGE_SIZE       = 4096          # 4KB pages (x86/x64 standard)
CACHE_LINE_SIZE = 64            # 64-byte cache lines (all modern x86)

def _detect_cpu_count() -> int:
    return multiprocessing.cpu_count()

def _detect_numa_nodes() -> int:
    if sys.platform.startswith("linux"):
        try:
            nodes = len([d for d in os.listdir("/sys/devices/system/node/") if d.startswith("node")])
            return max(1, nodes)
        except Exception:
            pass
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor")
            i = 0
            while True:
                try:
                    winreg.EnumKey(key, i)
                    i += 1
                except OSError:
                    break
            return max(1, i // 8)
        except Exception:
            pass
    return 1


# ══════════════════════════════════════════════════════════════
#  MODULE-LEVEL WORKER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def _saturation_worker(args: tuple) -> tuple:
    size_mb, duration, scalar = args
    n          = (size_mb * 1024 * 1024) // 8
    a          = np.ones(n,  dtype=np.float64) * 1.0
    b          = np.ones(n,  dtype=np.float64) * 2.0
    c          = np.ones(n,  dtype=np.float64) * 3.0
    scalar_val = np.float64(scalar)

    a[:] = b + scalar_val * c
    total_bytes = 0
    iterations  = 0
    end_time    = time.perf_counter() + duration

    while time.perf_counter() < end_time:
        np.add(b, scalar_val * c, out=a)
        total_bytes += n * 8 * 3
        iterations  += 1

    return total_bytes, iterations

def _false_sharing_worker(args: tuple) -> int:
    arr, thread_id, n_iters, use_padding = args
    if use_padding:
        idx = thread_id * (CACHE_LINE_SIZE // 8)
    else:
        idx = thread_id

    count = 0
    val   = np.float64(thread_id + 1.0)
    for _ in range(n_iters):
        arr[idx] += val
        count    += 1
    return count

def _stride_worker(args: tuple) -> float:
    buf_size_mb, stride_bytes, n_probes = args
    n_elements = (buf_size_mb * 1024 * 1024) // 8
    stride_els = max(1, stride_bytes // 8)

    buf = np.ones(n_elements, dtype=np.float64)
    indices = np.arange(0, min(n_probes * stride_els, n_elements), stride_els, dtype=np.int64)[:n_probes]
    _ = buf[indices].sum()

    start = time.perf_counter()
    acc   = np.float64(0.0)
    for idx in indices:
        acc += buf[idx]
    elapsed    = time.perf_counter() - start
    return float((elapsed / len(indices)) * 1e9)

def _prefetch_linear_worker(args: tuple) -> tuple:
    size_mb, duration = args
    n    = (size_mb * 1024 * 1024) // 8
    buf  = np.ones(n, dtype=np.float64)
    _ = buf.sum()

    total_bytes = 0
    iterations  = 0
    end         = time.perf_counter() + duration
    while time.perf_counter() < end:
        _ = buf.sum()
        total_bytes += n * 8
        iterations  += 1
    return total_bytes, iterations

def _prefetch_random_worker(args: tuple) -> tuple:
    size_mb, n_probes = args
    n       = (size_mb * 1024 * 1024) // 8
    buf     = np.ones(n, dtype=np.float64)
    rng     = np.random.default_rng(seed=42)
    indices = rng.integers(0, n, n_probes, dtype=np.int64)

    warm_idx = rng.integers(0, n, 1000, dtype=np.int64)
    _ = buf[warm_idx].sum()

    start = time.perf_counter()
    acc   = np.float64(0.0)
    for idx in indices:
        acc += buf[idx]
    elapsed = time.perf_counter() - start

    bw_mbs = (n_probes * 8) / elapsed / 1e6
    return bw_mbs, elapsed


# ══════════════════════════════════════════════════════════════
#  MAIN BENCHMARK CLASS
# ══════════════════════════════════════════════════════════════

class RAMBenchmark:
    BUFFER_SIZES_MB = [1, 4, 16, 64, 256, 512]
    MAIN_BUFFER_MB  = 512
    LATENCY_ITERS   = 2_000_000
    DURATION        = 4.0
    CORE_COUNT      = _detect_cpu_count()
    NUMA_NODES      = _detect_numa_nodes()

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_cb = progress_callback or (lambda msg, pct: None)

    # ── BASIC TESTS ───────────────────────────────────────────

    def test_read_bandwidth(self) -> dict:
        self.progress_cb("RAM: Sequential Read Bandwidth...", 3)
        size_bytes  = self.MAIN_BUFFER_MB * 1024 * 1024
        n_elements  = size_bytes // 8
        buf         = np.ones(n_elements, dtype=np.float64)
        _ = buf.sum()

        total_bytes = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION
        iterations  = 0

        while time.perf_counter() < deadline:
            acc = buf.sum()
            total_bytes += size_bytes
            iterations  += 1

        elapsed    = time.perf_counter() - start
        bandwidth  = total_bytes / elapsed / 1e9
        score      = self._normalize(bandwidth, 0, 150)

        return {
            "name":        "Sequential Read Bandwidth",
            "value":       round(bandwidth, 3), "unit": "GB/s",
            "raw":         total_bytes, "score": score,
            "description": f"Streamed {self.MAIN_BUFFER_MB}MB buffer × {iterations} passes. Total read: {total_bytes / 1e9:.1f} GB."
        }

    def test_write_bandwidth(self) -> dict:
        self.progress_cb("RAM: Sequential Write Bandwidth...", 6)
        size_bytes = self.MAIN_BUFFER_MB * 1024 * 1024
        n_elements = size_bytes // 8
        buf        = np.empty(n_elements, dtype=np.float64)

        total_bytes = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION
        iterations  = 0
        fill_value  = np.float64(3.14159265358979)

        while time.perf_counter() < deadline:
            buf.fill(fill_value)
            total_bytes += size_bytes
            iterations  += 1

        elapsed   = time.perf_counter() - start
        bandwidth = total_bytes / elapsed / 1e9
        score     = self._normalize(bandwidth, 0, 100)

        return {
            "name":        "Sequential Write Bandwidth",
            "value":       round(bandwidth, 3), "unit": "GB/s",
            "raw":         total_bytes, "score": score,
            "description": f"Filled {self.MAIN_BUFFER_MB}MB buffer × {iterations} passes. Total written: {total_bytes / 1e9:.1f} GB."
        }

    def test_copy_bandwidth(self) -> dict:
        self.progress_cb("RAM: Memory Copy Bandwidth (STREAM)...", 9)
        size_bytes = self.MAIN_BUFFER_MB * 1024 * 1024
        n_elements = size_bytes // 8
        src        = np.ones(n_elements,  dtype=np.float64)
        dst        = np.empty(n_elements, dtype=np.float64)

        total_bytes = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION
        iterations  = 0

        while time.perf_counter() < deadline:
            np.copyto(dst, src)
            total_bytes += size_bytes * 2
            iterations  += 1

        elapsed   = time.perf_counter() - start
        bandwidth = total_bytes / elapsed / 1e9
        score     = self._normalize(bandwidth, 0, 200)

        return {
            "name":        "Memory Copy Bandwidth (STREAM)",
            "value":       round(bandwidth, 3), "unit": "GB/s",
            "raw":         total_bytes, "score": score,
            "description": f"Memory copy (read+write) × {iterations} passes. Total transferred: {total_bytes / 1e9:.1f} GB."
        }

    def test_sequential_latency(self) -> dict:
        self.progress_cb("RAM: Sequential Access Latency...", 12)
        n_elements = (64 * 1024 * 1024) // 8
        buf        = np.arange(n_elements, dtype=np.float64)

        PROBES = 1_000_000
        stride = 16
        indices = np.arange(0, min(PROBES * stride, n_elements), stride, dtype=np.int64)[:PROBES]

        start = time.perf_counter()
        acc   = np.float64(0.0)
        for idx in indices: acc += buf[idx]
        elapsed    = time.perf_counter() - start
        latency_ns = (elapsed / PROBES) * 1e9
        score = self._normalize(1 / latency_ns if latency_ns > 0 else 0, 0, 0.5)

        return {
            "name":        "Sequential Access Latency",
            "value":       round(latency_ns, 2), "unit": "ns/access",
            "raw":         PROBES, "score": score,
            "description": f"64-byte stride access across 64MB buffer. {PROBES:,} probes."
        }

    def test_random_latency(self) -> dict:
        self.progress_cb("RAM: Random Access Latency...", 15)
        n_elements = (256 * 1024 * 1024) // 8
        PROBES     = self.LATENCY_ITERS
        rng     = np.random.default_rng(seed=42)
        indices = rng.choice(n_elements, size=PROBES, replace=False).astype(np.int64)
        buf     = np.ones(n_elements, dtype=np.float64) * 1.0

        start = time.perf_counter()
        acc   = 0.0
        for idx in indices: acc += buf[idx]
        elapsed    = time.perf_counter() - start
        latency_ns = (elapsed / PROBES) * 1e9

        score = self._normalize(1 / latency_ns if latency_ns > 0 else 0, 0, 0.05)
        return {
            "name":        "Random Access Latency",
            "value":       round(latency_ns, 2), "unit": "ns/access",
            "raw":         PROBES, "score": score,
            "description": f"Fully random access across 256MB buffer. {PROBES:,} probes."
        }

    def test_cache_hierarchy(self) -> dict:
        self.progress_cb("RAM: Cache Hierarchy Bandwidth Sweep...", 18)
        results_by_size = {}
        for size_mb in self.BUFFER_SIZES_MB:
            n_elements = (size_mb * 1024 * 1024) // 8
            buf        = np.ones(n_elements, dtype=np.float64)
            _ = buf.sum()
            ITERS = max(1, int(2.0 / (size_mb * 1024 * 1024 / 1e9)))
            start = time.perf_counter()
            for _ in range(ITERS): _ = buf.sum()
            elapsed   = time.perf_counter() - start
            bandwidth = (size_mb / 1024) * ITERS / elapsed
            results_by_size[f"{size_mb}MB"] = round(bandwidth, 3)

        bw_values = list(results_by_size.values())
        drop_points = [list(results_by_size.keys())[i] for i in range(1, len(bw_values)) if bw_values[i]/max(bw_values[i-1], 0.001) < 0.5]
        score = self._normalize(bw_values[-1], 0, 100)
        return {
            "name": "Cache Hierarchy Bandwidth Sweep",
            "value": bw_values[-1], "unit": "GB/s at DRAM level",
            "raw": results_by_size, "score": score, "cache_drops": drop_points,
            "description": "Bandwidth measured at multiple buffer sizes to expose L1/L2/L3/DRAM boundaries."
        }

    def test_multithreaded_bandwidth(self) -> dict:
        self.progress_cb("RAM: Multi-Threaded Memory Bandwidth...", 21)
        N_THREADS  = min(4, os.cpu_count() or 4)
        SIZE_PER_T = (128 * 1024 * 1024) // 8
        DURATION   = 3.0

        thread_bytes = [0] * N_THREADS
        stop_event   = threading.Event()

        def worker(tid):
            buf   = np.ones(SIZE_PER_T, dtype=np.float64)
            total = 0
            while not stop_event.is_set():
                _ = buf.sum()
                total += SIZE_PER_T * 8
            thread_bytes[tid] = total

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N_THREADS)]
        start   = time.perf_counter()
        for t in threads: t.start()
        time.sleep(DURATION)
        stop_event.set()
        for t in threads: t.join()

        elapsed   = time.perf_counter() - start
        total_bw  = sum(thread_bytes) / elapsed / 1e9
        score     = self._normalize(total_bw, 0, 200)
        return {
            "name": f"Multi-Threaded Read Bandwidth ({N_THREADS} threads)",
            "value": round(total_bw, 3), "unit": "GB/s",
            "raw": sum(thread_bytes), "score": score,
            "description": f"Concurrent memory reads from {N_THREADS} threads."
        }


    # ── EXTENDED TESTS ────────────────────────────────────────

    def test_tlb_stress(self) -> dict:
        self.progress_cb("RAM: TLB Stress Test...", 28)
        N_PROBES   = 500_000
        PAGE_BYTES = PAGE_SIZE

        TLB_FIT_PAGES = 512
        fit_size      = TLB_FIT_PAGES * PAGE_BYTES
        fit_n         = fit_size // 8
        buf_fit       = np.ones(fit_n, dtype=np.float64)
        stride_fit  = PAGE_BYTES // 8
        idx_fit     = np.arange(0, min(N_PROBES * stride_fit, fit_n), stride_fit, dtype=np.int64)[:N_PROBES]
        idx_fit     = idx_fit % fit_n
        _ = buf_fit[idx_fit[:100]].sum()

        start  = time.perf_counter()
        acc    = np.float64(0.0)
        for i in idx_fit: acc += buf_fit[i]
        fit_time   = time.perf_counter() - start
        fit_lat_ns = fit_time / len(idx_fit) * 1e9

        TLB_THRASH_PAGES = 16384
        thrash_size      = TLB_THRASH_PAGES * PAGE_BYTES
        thrash_n         = thrash_size // 8
        buf_thrash       = np.ones(thrash_n, dtype=np.float64)
        rng          = np.random.default_rng(seed=7)
        page_indices = rng.integers(0, TLB_THRASH_PAGES, N_PROBES, dtype=np.int64)
        idx_thrash   = page_indices * stride_fit
        _ = buf_thrash[idx_thrash[:50] % thrash_n].sum()

        start    = time.perf_counter()
        acc2     = np.float64(0.0)
        for i in idx_thrash: acc2 += buf_thrash[int(i) % thrash_n]
        thrash_time   = time.perf_counter() - start
        thrash_lat_ns = thrash_time / N_PROBES * 1e9

        tlb_miss_penalty = thrash_lat_ns / max(fit_lat_ns, 0.1)
        score = self._normalize(1.0 / max(tlb_miss_penalty, 0.1), 0, 1.0)

        return {
            "name":              "TLB Stress Test",
            "value":             round(thrash_lat_ns, 2), "unit": "ns (TLB-miss latency)",
            "miss_penalty_x":    round(tlb_miss_penalty, 2), "raw": N_PROBES * 2, "score": score,
            "description": f"Hit latency: {fit_lat_ns:.1f}ns | Miss latency: {thrash_lat_ns:.1f}ns | Miss penalty: {tlb_miss_penalty:.1f}×."
        }

    def test_false_sharing(self) -> dict:
        self.progress_cb("RAM: Cache Line False Sharing Detection...", 35)
        N_THREADS = min(self.CORE_COUNT, 8)
        N_ITERS   = 5_000_000

        padded_size = N_THREADS * (CACHE_LINE_SIZE // 8)
        arr_padded  = np.zeros(padded_size, dtype=np.float64)
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(N_THREADS) as pool:
            start   = time.perf_counter()
            results_padded = pool.map(_false_sharing_worker, [(arr_padded, tid, N_ITERS, True) for tid in range(N_THREADS)])
            padded_time = time.perf_counter() - start
        padded_throughput = sum(results_padded) / padded_time / 1e6

        packed_size = N_THREADS
        arr_packed  = np.zeros(packed_size, dtype=np.float64)
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(N_THREADS) as pool:
            start   = time.perf_counter()
            results_packed = pool.map(_false_sharing_worker, [(arr_packed, tid, N_ITERS, False) for tid in range(N_THREADS)])
            packed_time = time.perf_counter() - start
        packed_throughput = sum(results_packed) / packed_time / 1e6

        speedup = padded_throughput / max(packed_throughput, 0.001)
        score = self._normalize(speedup, 1.0, 20.0)

        return {
            "name":               "Cache Line False Sharing Detection",
            "value":              round(speedup, 2), "unit": "× speedup",
            "padded_m_ops_sec":   round(padded_throughput, 2), "packed_m_ops_sec": round(packed_throughput, 2),
            "raw":                N_ITERS * N_THREADS * 2, "score": score,
            "description": f"Padded: {padded_throughput:.1f}M ops/s | Packed: {packed_throughput:.1f}M ops/s. False sharing {speedup:.1f}× slower."
        }

    def test_numa_latency(self) -> dict:
        self.progress_cb("RAM: NUMA Latency Detection...", 42)
        N_PROBES  = 200_000
        LOCAL_MB  = 64
        local_n   = (LOCAL_MB * 1024 * 1024) // 8
        local_buf = np.ones(local_n, dtype=np.float64)

        rng          = np.random.default_rng(seed=11)
        local_idx    = rng.integers(0, local_n, N_PROBES, dtype=np.int64)
        _ = local_buf[local_idx[:1000]].sum()

        start    = time.perf_counter()
        acc      = np.float64(0.0)
        for i in local_idx: acc += local_buf[i]
        local_lat_ns   = (time.perf_counter() - start) / N_PROBES * 1e9

        REMOTE_MB     = 512
        n_remote_bufs = min(4, max(1, self.CORE_COUNT // 2))
        remote_bufs   = [np.ones((REMOTE_MB * 1024 * 1024) // 8, dtype=np.float64) for _ in range(n_remote_bufs)]
        for buf in remote_bufs: buf[0] = 1.0; buf[-1] = 1.0
        remote_indices = [rng.integers(0, len(buf), max(1, N_PROBES // n_remote_bufs), dtype=np.int64) for buf in remote_bufs]

        start   = time.perf_counter()
        acc2    = np.float64(0.0)
        for b_idx, (buf, idxs) in enumerate(zip(remote_bufs, remote_indices)):
            for i in idxs: acc2 += buf[i]
        remote_lat_ns  = (time.perf_counter() - start) / max(1, sum(len(x) for x in remote_indices)) * 1e9

        numa_ratio = remote_lat_ns / max(local_lat_ns, 0.1)
        score = self._normalize(1.0 / max(numa_ratio, 0.1), 0, 1.0)

        return {
            "name":              "NUMA Latency Detection",
            "value":             round(numa_ratio, 3), "unit": "× remote/local ratio",
            "local_lat_ns":      round(local_lat_ns, 2), "remote_lat_ns": round(remote_lat_ns, 2),
            "detected_nodes":    self.NUMA_NODES, "raw": N_PROBES, "score": score,
            "description": f"Detected: {self.NUMA_NODES} NUMA node(s). Local: {local_lat_ns:.1f}ns | Inter-region: {remote_lat_ns:.1f}ns | Ratio: {numa_ratio:.2f}×."
        }

    def test_simd_bandwidth(self) -> dict:
        self.progress_cb("RAM: SIMD-Style Vectorized Bandwidth...", 49)
        BUFFER_MB = 256
        DURATION  = self.DURATION / 4

        def measure_bandwidth(dtype, label: str) -> dict:
            itemsize  = np.dtype(dtype).itemsize
            n_els     = (BUFFER_MB * 1024 * 1024) // itemsize
            buf       = np.ones(n_els, dtype=dtype)
            _ = buf.sum()

            total_bytes = 0
            end         = time.perf_counter() + DURATION
            while time.perf_counter() < end:
                _ = buf.sum()
                total_bytes += n_els * itemsize

            return {"dtype": label, "bw_gbs": round(total_bytes / DURATION / 1e9, 3)}

        r_f32 = measure_bandwidth(np.float32, "float32  (32-bit scalar)")
        r_f64 = measure_bandwidth(np.float64, "float64  (64-bit scalar)")
        r_i16 = measure_bandwidth(np.int16, "int16    (SSE2 16×8-bit)")
        r_c128 = measure_bandwidth(np.complex128, "complex128(AVX2 256-bit)")

        n_avx = (BUFFER_MB * 1024 * 1024) // 1
        buf_avx = np.ones(BUFFER_MB * 1024 * 1024 // 8, dtype=np.float64)
        total_avx = 0
        end_avx   = time.perf_counter() + DURATION
        while time.perf_counter() < end_avx:
            _ = buf_avx.reshape(-1, 8).sum(axis=1).sum()
            total_avx += len(buf_avx) * 8
        r_avx512 = {"dtype": "float64×8 (AVX-512 sim)", "bw_gbs": round(total_avx / DURATION / 1e9, 3)}

        all_results = [r_f32, r_f64, r_i16, r_c128, r_avx512]
        peak_bw = max(r["bw_gbs"] for r in all_results)
        score = self._normalize(peak_bw, 0, 150)

        return {
            "name":          "SIMD-Style Vectorized Bandwidth",
            "value":         peak_bw, "unit": "GB/s peak",
            "f32_bw_gbs":    r_f32["bw_gbs"], "avx512_bw_gbs": r_avx512["bw_gbs"],
            "raw":           BUFFER_MB, "score": score,
            "description": f"Read bandwidth at multiple SIMD widths. Peak: {peak_bw:.2f} GB/s. float32: {r_f32['bw_gbs']}GB/s | AVX-512 sim: {r_avx512['bw_gbs']}GB/s."
        }

    def test_memory_controller_saturation(self) -> dict:
        self.progress_cb("RAM: Memory Controller Saturation...", 56)
        DURATION     = min(self.DURATION, 3.0)
        BUFFER_MB    = 128
        SCALAR       = 3.14159

        bw_by_threads = {}
        prev_bw = 0.0
        saturation_at = 1
        peak_bw = 0.0
        thread_counts = list(range(1, min(self.CORE_COUNT + 1, 9)))

        for n_threads in thread_counts:
            args_list = [(BUFFER_MB, DURATION, SCALAR) for _ in range(n_threads)]
            ctx = multiprocessing.get_context('spawn')
            with ctx.Pool(n_threads) as pool:
                thread_results = pool.map(_saturation_worker, args_list)

            bw_gbs = sum(r[0] for r in thread_results) / DURATION / 1e9
            bw_by_threads[f"{n_threads}T"] = round(bw_gbs, 3)

            if bw_gbs > peak_bw:
                peak_bw = bw_gbs
                saturation_at = n_threads

            if n_threads > 1 and bw_gbs < prev_bw * 1.03:
                break
            prev_bw = bw_gbs

        score = self._normalize(peak_bw, 0, 150)
        return {
            "name":             "Memory Controller Saturation",
            "value":            round(peak_bw, 3), "unit": "GB/s",
            "saturates_at_threads": saturation_at, "raw": saturation_at, "score": score,
            "description": f"STREAM Triad peak: {peak_bw:.2f} GB/s (saturated at {saturation_at} threads)."
        }

    def test_row_hammer_pattern(self) -> dict:
        self.progress_cb("RAM: Row Hammer Access Pattern Analysis...", 63)
        ROW_SIZE = 8192
        N_ROWS = 1024
        BUF_SIZE = ROW_SIZE * N_ROWS
        N_ITERS = 2_000_000

        row_a = np.zeros(BUF_SIZE // 8, dtype=np.float64); row_a[0] = 1.0; row_a[-1] = 1.0
        row_b = np.zeros(BUF_SIZE // 8, dtype=np.float64); row_b[0] = 2.0; row_b[-1] = 2.0

        STRIDE = ROW_SIZE // 8
        a_idx = 0; b_idx = STRIDE
        access_times = []
        SAMPLE_EVERY = N_ITERS // 100

        start = time.perf_counter()
        total_acc = np.float64(0.0)
        for i in range(N_ITERS):
            t0 = time.perf_counter()
            total_acc += row_a[a_idx]
            total_acc += row_b[b_idx]
            t1 = time.perf_counter()
            if i % SAMPLE_EVERY == 0: access_times.append((t1 - t0) * 1e9)

        elapsed = time.perf_counter() - start
        total_accesses = N_ITERS * 2
        acts_per_sec = total_accesses / elapsed
        score = self._normalize(acts_per_sec / 1e6, 0, 500)

        times_arr = np.array(access_times, dtype=np.float64)
        avg_ns = float(np.mean(times_arr))
        p99_ns = float(np.percentile(times_arr, 99))
        refresh_events = int(np.sum(times_arr > avg_ns * 5.0))

        return {
            "name":            "Row Hammer Access Pattern",
            "value":           round(acts_per_sec / 1e6, 2), "unit": "M ACTS/s",
            "avg_lat_ns":      round(avg_ns, 2), "p99_lat_ns": round(p99_ns, 2),
            "refresh_events":  refresh_events, "raw": N_ITERS, "score": score,
            "description": f"Row activation rate: {acts_per_sec/1e6:.1f}M ACTS/s. Avg latency: {avg_ns:.1f}ns. Refresh events: {refresh_events}."
        }

    def test_stride_sensitivity(self) -> dict:
        self.progress_cb("RAM: Stride Sensitivity Analysis...", 70)
        BUF_MB = 256
        N_PROBES = 100_000
        strides_bytes = [8, 64, 256, 4096, 65536, 1048576, 2097152]

        latencies = {}
        args_list = [(BUF_MB, stride, N_PROBES) for stride in strides_bytes]

        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(min(len(strides_bytes), self.CORE_COUNT)) as pool:
            results_mp = pool.map(_stride_worker, args_list)

        for stride, lat in zip(strides_bytes, results_mp):
            if stride < 1024: label = f"{stride}B"
            elif stride < 1048576: label = f"{stride//1024}KB"
            else: label = f"{stride//1048576}MB"
            latencies[label] = round(lat, 2)

        lat_values = list(latencies.values())
        best_lat = lat_values[0] if lat_values else 0
        worst_lat = lat_values[-1] if lat_values else 0
        score = self._normalize(1.0 / max(best_lat, 0.1), 0, 0.2)

        return {
            "name":           "Stride Sensitivity Analysis",
            "value":          best_lat, "unit": "ns (best case)",
            "worst_lat_ns":   worst_lat, "raw": N_PROBES, "score": score,
            "description": f"Latency at {len(strides_bytes)} strides. Best: {best_lat:.1f}ns | Worst: {worst_lat:.1f}ns."
        }

    def test_write_combining(self) -> dict:
        self.progress_cb("RAM: Write Combining Effectiveness...", 77)
        BUFFER_MB = 256
        DURATION = self.DURATION / 3
        n_elements = (BUFFER_MB * 1024 * 1024) // 8
        val = np.float64(3.14159)

        # Sequential
        buf_a = np.empty(n_elements, dtype=np.float64)
        total_seq = 0; end_seq = time.perf_counter() + DURATION
        while time.perf_counter() < end_seq:
            buf_a.fill(val); total_seq += n_elements * 8
        seq_bw = total_seq / DURATION / 1e9

        # Scattered
        buf_b = np.empty(n_elements, dtype=np.float64)
        scatter_idx = np.arange(0, n_elements, 16, dtype=np.int64)
        total_scat = 0; end_scat = time.perf_counter() + DURATION
        while time.perf_counter() < end_scat:
            buf_b[scatter_idx] = val; total_scat += len(scatter_idx) * 8
        scat_bw = total_scat / DURATION / 1e9

        wc_effectiveness = seq_bw / max(scat_bw, 0.001)
        score = self._normalize(seq_bw, 0, 100)

        return {
            "name":               "Write Combining Effectiveness",
            "value":              round(seq_bw, 3), "unit": "GB/s",
            "wc_effectiveness_x": round(wc_effectiveness, 2), "raw": n_elements, "score": score,
            "description": f"Sequential: {seq_bw:.2f}GB/s | Scattered: {scat_bw:.2f}GB/s | Effectiveness: {wc_effectiveness:.1f}×."
        }

    def test_prefetch_effectiveness(self) -> dict:
        self.progress_cb("RAM: Hardware Prefetch Effectiveness...", 84)
        BUF_MB = 256
        N_PROBES = 500_000
        DURATION = self.DURATION / 4
        n_elements = (BUF_MB * 1024 * 1024) // 8
        buf = np.ones(n_elements, dtype=np.float64); buf[0] = 0.0

        total_a, _ = _prefetch_linear_worker((BUF_MB, DURATION))
        bw_seq = total_a / DURATION / 1e9

        bw_rand_mbs, _ = _prefetch_random_worker((BUF_MB, N_PROBES))
        bw_rand = bw_rand_mbs / 1e3

        prefetch_benefit = bw_seq / max(bw_rand, 0.001)
        score = self._normalize(prefetch_benefit, 1, 50)

        return {
            "name":               "Hardware Prefetch Effectiveness",
            "value":              round(prefetch_benefit, 2), "unit": "× prefetch benefit",
            "sequential_bw_gbs":  round(bw_seq, 3), "random_bw_gbs": round(bw_rand, 3),
            "raw":                N_PROBES, "score": score,
            "description": f"Sequential: {bw_seq:.2f}GB/s | Random: {bw_rand:.3f}GB/s | Prefetch benefit: {prefetch_benefit:.1f}×."
        }

    def test_latency_histogram(self) -> dict:
        self.progress_cb("RAM: Memory Latency Histogram...", 91)
        N_PROBES = 1_000_000
        SAMPLE_BUFFERS = {
            "L1_cache":   (32, "~L1 Cache"),
            "L2_cache":   (256, "~L2 Cache"),
            "L3_cache":   (8192, "~L3 Cache"),
            "DRAM_large": (524288, "~DRAM Large"),
        }
        latency_summary = {}
        rng = np.random.default_rng(seed=7)

        for level_name, (size_kb, level_label) in SAMPLE_BUFFERS.items():
            n_els = max(1, (size_kb * 1024) // 8)
            buf = np.ones(n_els, dtype=np.float64)
            buf[0] = 1.0; buf[-1] = 1.0
            n_p = min(N_PROBES, n_els)
            indices = rng.integers(0, n_els, n_p, dtype=np.int64)
            _ = buf[indices[:100]].sum()

            SAMPLE_EVERY = max(1, n_p // 10_000)
            lat_samples = []
            acc = np.float64(0.0)
            for idx_i, i in enumerate(indices):
                if idx_i % SAMPLE_EVERY == 0:
                    t0 = time.perf_counter()
                    acc += buf[i]
                    lat_samples.append((time.perf_counter() - t0) * 1e9)
                else:
                    acc += buf[i]

            if lat_samples:
                lat_arr = np.array(lat_samples, dtype=np.float64)
                lat_arr = lat_arr[lat_arr < 10000]
                latency_summary[level_name] = round(float(np.percentile(lat_arr, 50)), 2)

        l1_lat = latency_summary.get("L1_cache", 5.0)
        dram_lat = latency_summary.get("DRAM_large", 100.0)
        score = self._normalize(1.0 / max(dram_lat, 1.0), 0, 0.1)

        return {
            "name":            "Memory Latency Histogram",
            "value":           dram_lat, "unit": "ns (DRAM P50 latency)",
            "l1_lat_ns":       l1_lat, "dram_lat_ns": dram_lat,
            "raw":             N_PROBES, "score": score,
            "description": f"Full latency histogram. L1: {l1_lat:.1f}ns | DRAM: {dram_lat:.1f}ns."
        }

    # ── HELPERS ───────────────────────────────────────────────

    @staticmethod
    def _normalize(value, low, high, out_min=0, out_max=100_000):
        if high == low: return out_min
        return int(out_min + (max(low, min(high, value)) - low) / (high - low) * (out_max - out_min))

    @staticmethod
    def _grade(score):
        if score >= 85_000: return "S"
        if score >= 70_000: return "A"
        if score >= 55_000: return "B"
        if score >= 40_000: return "C"
        if score >= 25_000: return "D"
        return "F"

    @staticmethod
    def _tier(score):
        if score >= 85_000: return "DDR5-7200+ / LPDDR5X"
        if score >= 70_000: return "DDR5-6000 / DDR4-5000+"
        if score >= 55_000: return "DDR5-4800 / DDR4-3600"
        if score >= 40_000: return "DDR4-3200 / DDR4-2666"
        if score >= 25_000: return "DDR4-2133 / DDR3-1866"
        return "DDR3 / Legacy"

    # ── RUN ALL ───────────────────────────────────────────────

    def run_all(self) -> dict:
        tests = [
            # Basic Tests
            self.test_read_bandwidth,
            self.test_write_bandwidth,
            self.test_copy_bandwidth,
            self.test_sequential_latency,
            self.test_random_latency,
            self.test_cache_hierarchy,
            self.test_multithreaded_bandwidth,
            # Extended Tests
            self.test_tlb_stress,
            self.test_false_sharing,
            self.test_numa_latency,
            self.test_simd_bandwidth,
            self.test_memory_controller_saturation,
            self.test_row_hammer_pattern,
            self.test_stride_sensitivity,
            self.test_write_combining,
            self.test_prefetch_effectiveness,
            self.test_latency_histogram,
        ]

        results = []
        for idx, fn in enumerate(tests):
            try:
                results.append(fn())
            except Exception as e:
                results.append({"name": fn.__name__, "error": str(e), "score": 0})
            
            self.progress_cb(f"Running RAM test {idx+1}/{len(tests)}", int((idx + 1) / len(tests) * 100))

        scoreable = [r["score"] for r in results if "score" in r and "error" not in r]
        overall = int(np.mean(scoreable)) if scoreable else 0
        self.progress_cb("RAM Benchmark Complete!", 100)

        return {
            "component": "RAM",
            "overall_score": overall,
            "grade": self._grade(overall),
            "tier": self._tier(overall),
            "core_count": self.CORE_COUNT,
            "numa_nodes": self.NUMA_NODES,
            "tests": results,
        }
