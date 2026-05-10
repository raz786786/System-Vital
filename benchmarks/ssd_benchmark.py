"""
SYSTEM VITAL SSD BENCHMARK ENGINE
Industry-level tests mirroring CrystalDiskMark + Extended SSD diagnostics.
"""

import os
import sys
import time
import math
import struct
import random
import tempfile
import threading
import statistics
import numpy as np
from typing import Callable, Optional, List, Tuple


def _make_random_data(size_bytes: int, seed: int = 42) -> bytes:
    rng    = np.random.default_rng(seed=seed)
    n      = size_bytes
    arr    = rng.integers(0, 256, n, dtype=np.uint8)
    return arr.tobytes()

def _make_compressible_data(size_bytes: int) -> bytes:
    pattern = b"SYSTEM VITAL_BENCH_COMPRESSIBLE_DATA_" * 32
    repeats = math.ceil(size_bytes / len(pattern))
    return (pattern * repeats)[:size_bytes]

def _safe_remove(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def _detect_drive_root(ref_path: str = None) -> str:
    path = ref_path or os.path.abspath(__file__)
    drive = os.path.splitdrive(path)[0]
    return (drive + os.sep) if drive else os.sep

def _get_free_space_gb(path: str) -> float:
    try:
        stat = os.statvfs(path) if hasattr(os, 'statvfs') else None
        if stat:
            return stat.f_bavail * stat.f_frsize / 1e9
        else:
            import shutil
            return shutil.disk_usage(path).free / 1e9
    except Exception:
        return 0.0


class SSDDiskBenchmark:
    SEQ_FILE_SIZE_MB    = 1024
    RAND_FILE_SIZE_MB   = 512
    BLOCK_SIZE_SEQ_MB   = 1
    BLOCK_SIZE_4K       = 4096
    BLOCK_64K           = 65536
    BLOCK_1M            = 1024 * 1024
    BLOCK_128K          = 131072
    DURATION_SEC        = 5.0
    DURATION_SHORT      = 5.0
    DURATION_LONG       = 10.0

    def __init__(self,
                 test_drive: str = None,
                 progress_callback: Optional[Callable] = None):
        self.progress_cb  = progress_callback or (lambda msg, pct: None)
        self.drive_root   = _detect_drive_root(test_drive)
        self.test_drive   = self.drive_root
        self.test_file    = os.path.join(self.test_drive, "_SYSTEM VITAL_benchmark_tmp.dat")
        self._tmp_prefix  = os.path.join(self.test_drive, "_dkbench_ssd_")
        self._write_flag  = os.O_RDWR | os.O_CREAT | (os.O_SYNC if hasattr(os, 'O_SYNC') else 0)

    # ── FILE PREPARATION ─────────────────────

    def _create_test_file(self, size_mb: int, show_progress: bool = False):
        rng          = np.random.default_rng(seed=777)
        chunk_mb     = 8
        n_chunks     = size_mb // chunk_mb
        chunk_bytes  = chunk_mb * 1024 * 1024
        if show_progress:
            self.progress_cb(f"SSD: Creating {size_mb}MB test file...", 2)

        with open(self.test_file, 'wb', buffering=0) as f:
            for i in range(n_chunks):
                chunk = rng.integers(0, 256, chunk_bytes, dtype=np.uint8).tobytes()
                f.write(chunk)
                if show_progress:
                    self.progress_cb(
                        f"SSD: Preparing test file... {int((i+1)/n_chunks*100)}%",
                        int(2 + (i+1)/n_chunks * 5)
                    )
            f.flush()
            os.fsync(f.fileno())

    def _cleanup(self):
        _safe_remove(self.test_file)

    # ── BASIC TESTS ────────────────────────────────────────────────

    def test_sequential_read(self) -> dict:
        self.progress_cb("SSD: Sequential Read (SEQ1M)...", 10)
        block_size   = self.BLOCK_SIZE_SEQ_MB * 1024 * 1024
        file_size    = os.path.getsize(self.test_file)
        total_bytes  = 0
        start        = time.perf_counter()
        deadline     = start + self.DURATION_SEC

        with open(self.test_file, 'rb', buffering=0) as f:
            offset = 0
            while time.perf_counter() < deadline:
                if offset + block_size > file_size:
                    offset = 0
                    f.seek(0)
                data         = f.read(block_size)
                if not data: break
                total_bytes += len(data)
                offset      += block_size

        elapsed   = time.perf_counter() - start
        speed_mbs = total_bytes / elapsed / 1e6
        score     = self._normalize(speed_mbs, 0, 7000)

        return {
            "name":        "Sequential Read (SEQ1M)",
            "value":       round(speed_mbs, 2), "unit": "MB/s",
            "raw":         total_bytes, "score": score,
            "description": f"1MB block sequential reads. {total_bytes/1e9:.2f}GB read in {elapsed:.2f}s."
        }

    def test_sequential_write(self) -> dict:
        self.progress_cb("SSD: Sequential Write (SEQ1M)...", 15)
        block_size  = self.BLOCK_SIZE_SEQ_MB * 1024 * 1024
        rng         = np.random.default_rng(seed=888)
        write_block = rng.integers(0, 256, block_size, dtype=np.uint8).tobytes()
        total_bytes = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION_SEC
        write_path  = f"{self._tmp_prefix}write_tmp.dat"

        try:
            with open(write_path, 'wb', buffering=0) as f:
                while time.perf_counter() < deadline:
                    f.write(write_block)
                    total_bytes += block_size
                f.flush()
                os.fsync(f.fileno())
        finally:
            _safe_remove(write_path)

        elapsed   = time.perf_counter() - start
        speed_mbs = total_bytes / elapsed / 1e6
        score     = self._normalize(speed_mbs, 0, 7000)

        return {
            "name":        "Sequential Write (SEQ1M)",
            "value":       round(speed_mbs, 2), "unit": "MB/s",
            "raw":         total_bytes, "score": score,
            "description": f"1MB block sequential writes. {total_bytes/1e9:.2f}GB written in {elapsed:.2f}s."
        }

    def test_random_4k_read_q1t1(self) -> dict:
        self.progress_cb("SSD: Random 4K Read (Q1T1)...", 20)
        file_size   = os.path.getsize(self.test_file)
        max_offset  = (file_size - self.BLOCK_SIZE_4K) // self.BLOCK_SIZE_4K
        rng         = np.random.default_rng(seed=111)
        offsets     = (rng.integers(0, max_offset, 50_000) * self.BLOCK_SIZE_4K).tolist()
        total_bytes = 0
        iops        = 0
        offset_idx  = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION_SEC

        with open(self.test_file, 'rb', buffering=0) as f:
            while time.perf_counter() < deadline:
                if offset_idx >= len(offsets): offset_idx = 0
                f.seek(offsets[offset_idx])
                data         = f.read(self.BLOCK_SIZE_4K)
                total_bytes += len(data)
                iops        += 1
                offset_idx  += 1

        elapsed   = time.perf_counter() - start
        speed_mbs = total_bytes / elapsed / 1e6
        real_iops = iops / elapsed
        score     = self._normalize(real_iops, 0, 1_000_000)

        return {
            "name":        "Random 4K Read (Q1T1)",
            "value":       round(real_iops, 0), "unit": "IOPS",
            "speed_mbs":   round(speed_mbs, 2), "raw": iops, "score": score,
            "description": f"{iops:,} random 4K reads in {elapsed:.2f}s."
        }

    def test_random_4k_read_q32(self) -> dict:
        self.progress_cb("SSD: Random 4K Read (Q32T1)...", 25)
        N_THREADS   = 32
        file_size   = os.path.getsize(self.test_file)
        max_offset  = (file_size - self.BLOCK_SIZE_4K) // self.BLOCK_SIZE_4K
        DURATION    = self.DURATION_SEC
        thread_iops  = [0] * N_THREADS
        thread_bytes = [0] * N_THREADS
        stop_event   = threading.Event()

        def reader_thread(tid):
            rng_t   = np.random.default_rng(seed=tid * 7 + 999)
            offsets = (rng_t.integers(0, max_offset, 100_000) * self.BLOCK_SIZE_4K).tolist()
            iops = 0; tb = 0; oidx = 0
            with open(self.test_file, 'rb', buffering=0) as f:
                while not stop_event.is_set():
                    if oidx >= len(offsets): oidx = 0
                    f.seek(offsets[oidx])
                    data  = f.read(self.BLOCK_SIZE_4K)
                    iops += 1; tb += len(data); oidx += 1
            thread_iops[tid]  = iops
            thread_bytes[tid] = tb

        threads = [threading.Thread(target=reader_thread, args=(i,), daemon=True) for i in range(N_THREADS)]
        start = time.perf_counter()
        for t in threads: t.start()
        time.sleep(DURATION)
        stop_event.set()
        for t in threads: t.join()

        elapsed    = time.perf_counter() - start
        total_iops = sum(thread_iops) / elapsed
        total_mbs  = sum(thread_bytes) / elapsed / 1e6
        score      = self._normalize(total_iops, 0, 2_000_000)

        return {
            "name":        "Random 4K Read (Q32T1)",
            "value":       round(total_iops, 0), "unit": "IOPS",
            "speed_mbs":   round(total_mbs, 2), "raw": sum(thread_iops), "score": score,
            "description": f"{N_THREADS} concurrent threads. {sum(thread_iops):,} total 4K reads."
        }

    def test_random_4k_write_q1t1(self) -> dict:
        self.progress_cb("SSD: Random 4K Write (Q1T1)...", 30)
        rng         = np.random.default_rng(seed=222)
        write_block = rng.integers(0, 256, self.BLOCK_SIZE_4K, dtype=np.uint8).tobytes()
        file_size   = os.path.getsize(self.test_file)
        max_offset  = (file_size - self.BLOCK_SIZE_4K) // self.BLOCK_SIZE_4K
        offsets  = (rng.integers(0, max_offset, 50_000) * self.BLOCK_SIZE_4K).tolist()
        total_bytes = 0; iops = 0; oidx = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION_SEC

        with open(self.test_file, 'r+b', buffering=0) as f:
            while time.perf_counter() < deadline:
                if oidx >= len(offsets): oidx = 0
                f.seek(offsets[oidx])
                f.write(write_block)
                total_bytes += self.BLOCK_SIZE_4K
                iops += 1; oidx += 1
            f.flush()

        elapsed   = time.perf_counter() - start
        speed_mbs = total_bytes / elapsed / 1e6
        real_iops = iops / elapsed
        score     = self._normalize(real_iops, 0, 700_000)

        return {
            "name":        "Random 4K Write (Q1T1)",
            "value":       round(real_iops, 0), "unit": "IOPS",
            "speed_mbs":   round(speed_mbs, 2), "raw": iops, "score": score,
            "description": f"{iops:,} random 4K writes in {elapsed:.2f}s."
        }

    def test_mixed_readwrite(self) -> dict:
        self.progress_cb("SSD: Mixed 70R/30W Workload...", 35)
        rng         = np.random.default_rng(seed=333)
        file_size   = os.path.getsize(self.test_file)
        max_offset  = (file_size - self.BLOCK_SIZE_4K) // self.BLOCK_SIZE_4K
        write_block = rng.integers(0, 256, self.BLOCK_SIZE_4K, dtype=np.uint8).tobytes()
        offsets = (rng.integers(0, max_offset, 100_000) * self.BLOCK_SIZE_4K).tolist()
        ops_rw  = (rng.random(100_000) < 0.7).tolist()
        total_bytes = 0; iops = 0; reads = 0; writes = 0; oidx = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION_SEC

        with open(self.test_file, 'r+b', buffering=0) as f:
            while time.perf_counter() < deadline:
                if oidx >= len(offsets): oidx = 0
                f.seek(offsets[oidx])
                if ops_rw[oidx]:
                    f.read(self.BLOCK_SIZE_4K)
                    reads += 1
                else:
                    f.write(write_block)
                    writes += 1
                total_bytes += self.BLOCK_SIZE_4K
                iops += 1; oidx += 1

        elapsed   = time.perf_counter() - start
        real_iops = iops / elapsed
        score     = self._normalize(real_iops, 0, 500_000)

        return {
            "name":        "Mixed 4K Read/Write (70%R / 30%W)",
            "value":       round(real_iops, 0), "unit": "IOPS",
            "reads":       reads, "writes": writes,
            "raw":         iops, "score": score,
            "description": f"{iops:,} ops in {elapsed:.2f}s."
        }

    def test_access_time(self) -> dict:
        self.progress_cb("SSD: Access Time / Seek Latency...", 40)
        file_size  = os.path.getsize(self.test_file)
        rng        = np.random.default_rng(seed=444)
        N_PROBES   = 10_000
        max_offset = (file_size - self.BLOCK_SIZE_4K) // self.BLOCK_SIZE_4K
        offsets    = (rng.integers(0, max_offset, N_PROBES) * self.BLOCK_SIZE_4K).tolist()
        latencies  = []

        with open(self.test_file, 'rb', buffering=0) as f:
            for offset in offsets:
                t0 = time.perf_counter()
                f.seek(offset)
                f.read(512)
                latencies.append((time.perf_counter() - t0) * 1e6)

        lat_arr   = np.array(latencies)
        avg_us    = float(np.mean(lat_arr))
        p50_us    = float(np.percentile(lat_arr, 50))
        p99_us    = float(np.percentile(lat_arr, 99))
        score     = self._normalize(1 / avg_us if avg_us > 0 else 0, 0, 1)

        return {
            "name":        "Random Access Latency (Seek Time)",
            "value":       round(avg_us, 3), "unit": "µs (average)",
            "p50_us":      round(p50_us, 3), "p99_us": round(p99_us, 3),
            "raw":         N_PROBES, "score": score,
            "description": f"{N_PROBES:,} random 512B accesses. Avg: {avg_us:.1f}µs."
        }

    # ── EXTENDED TESTS ─────────────────────────────────────────────

    def test_sustained_write_slc_cache(self) -> dict:
        self.progress_cb("SSD: Sustained Write + SLC Cache Detection...", 45)
        CHUNK_MB    = 512
        MAX_GB      = 16
        BLOCK_SIZE  = self.BLOCK_128K
        free_gb     = _get_free_space_gb(self.drive_root)
        write_gb    = min(MAX_GB, max(1, free_gb * 0.2))
        tmp_file    = f"{self._tmp_prefix}slc_test.tmp"
        random_data = _make_random_data(BLOCK_SIZE, seed=1)

        speed_samples   = []
        total_written   = 0
        chunk_start     = time.perf_counter()
        chunk_bytes     = 0
        slc_end_gb      = None
        slc_speed       = None
        post_slc_speed  = None

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                target_bytes = int(write_gb * 1e9)
                while total_written < target_bytes:
                    f.write(random_data)
                    total_written += len(random_data)
                    chunk_bytes   += len(random_data)

                    if chunk_bytes >= CHUNK_MB * 1e6:
                        elapsed_c = time.perf_counter() - chunk_start
                        speed_mbs = chunk_bytes / elapsed_c / 1e6
                        gb_written = total_written / 1e9
                        speed_samples.append((round(gb_written, 2), round(speed_mbs, 1)))

                        if len(speed_samples) >= 3 and slc_end_gb is None:
                            speeds   = [s[1] for s in speed_samples]
                            avg_3    = sum(speeds[-3:]) / 3
                            if len(speeds) > 3:
                                avg_prev = sum(speeds[:-3]) / max(len(speeds)-3, 1)
                                if avg_3 < avg_prev * 0.6:
                                    slc_end_gb   = gb_written
                                    slc_speed    = round(avg_prev, 1)
                                    post_slc_speed = round(avg_3, 1)

                        chunk_start = time.perf_counter()
                        chunk_bytes = 0

                f.flush(); os.fsync(f.fileno())
        finally:
            _safe_remove(tmp_file)

        if speed_samples:
            all_speeds = [s[1] for s in speed_samples]
            peak_speed = max(all_speeds)
            final_speed = all_speeds[-1]
            avg_speed = statistics.mean(all_speeds)
        else:
            peak_speed = final_speed = avg_speed = 0

        score = self._normalize(slc_speed or avg_speed, 0, 7000)

        return {
            "name":              "Sustained Write + SLC Cache Exhaustion",
            "value":             peak_speed, "unit": "MB/s (peak)",
            "slc_detected":      slc_end_gb is not None, "slc_end_gb": slc_end_gb,
            "avg_speed_mbs":     round(avg_speed, 1), "raw": total_written, "score": score,
            "description": f"Peak: {peak_speed:.0f}MB/s | Avg: {avg_speed:.0f}MB/s. SLC cache drop: {'detected' if slc_end_gb else 'none'}."
        }

    def test_write_amplification(self) -> dict:
        self.progress_cb("SSD: Write Amplification Factor Estimation...", 52)
        DURATION   = self.DURATION_SHORT
        tmp_seq    = f"{self._tmp_prefix}waf_seq.tmp"
        tmp_rand   = f"{self._tmp_prefix}waf_rand.tmp"
        rng        = np.random.default_rng(seed=22)
        seq_block  = _make_random_data(self.BLOCK_1M,  seed=10)
        rand_block = _make_random_data(self.BLOCK_4K,  seed=11)

        seq_bytes  = 0
        end_seq    = time.perf_counter() + DURATION
        try:
            with open(tmp_seq, 'wb', buffering=0) as f:
                while time.perf_counter() < end_seq:
                    f.write(seq_block)
                    seq_bytes += len(seq_block)
                f.flush(); os.fsync(f.fileno())
        finally:
            _safe_remove(tmp_seq)
        seq_mbs = seq_bytes / DURATION / 1e6

        FILE_SIZE_MB = 512
        n_blocks     = (FILE_SIZE_MB * 1024 * 1024) // self.BLOCK_4K
        try:
            with open(tmp_rand, 'wb', buffering=0) as f:
                chunk = rand_block * 256
                for _ in range(FILE_SIZE_MB): f.write(chunk)
                f.flush(); os.fsync(f.fileno())

            rand_bytes = 0
            offsets    = (rng.integers(0, n_blocks - 1, 100_000) * self.BLOCK_4K).tolist()
            oidx       = 0
            end_rand   = time.perf_counter() + DURATION
            with open(tmp_rand, 'r+b', buffering=0) as f:
                while time.perf_counter() < end_rand:
                    if oidx >= len(offsets): oidx = 0
                    f.seek(offsets[oidx])
                    f.write(rand_block)
                    rand_bytes += len(rand_block)
                    oidx += 1
        finally:
            _safe_remove(tmp_rand)
        rand_mbs = rand_bytes / DURATION / 1e6

        block_ratio = self.BLOCK_1M / self.BLOCK_4K
        waf_estimate = (seq_mbs / max(rand_mbs, 0.1)) / block_ratio
        waf_estimate = max(1.0, min(waf_estimate * 50, 20.0))
        score = self._normalize(1.0 / max(waf_estimate, 1.0), 0, 1.0)

        return {
            "name":             "Write Amplification Factor (WAF)",
            "value":            round(waf_estimate, 2), "unit": "× estimated WAF",
            "seq_mbs":          round(seq_mbs, 1), "rand_4k_mbs": round(rand_mbs, 2),
            "raw":              rand_bytes + seq_bytes, "score": score,
            "description": f"Sequential 1MB: {seq_mbs:.0f}MB/s | Random 4K: {rand_mbs:.1f}MB/s. Estimated WAF: {waf_estimate:.2f}×."
        }

    def test_queue_depth_scaling(self) -> dict:
        self.progress_cb("SSD: NVMe Queue Depth Scaling QD1→QD256...", 58)
        DURATION    = 3.0
        FILE_SIZE_MB = 512
        tmp_file    = f"{self._tmp_prefix}qd_test.tmp"
        rng         = np.random.default_rng(seed=33)

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                chunk = _make_random_data(self.BLOCK_1M, seed=5)
                for _ in range(FILE_SIZE_MB): f.write(chunk)
                f.flush(); os.fsync(f.fileno())

            n_blocks = (FILE_SIZE_MB * 1024 * 1024) // self.BLOCK_4K
            iops_by_qd = {}
            queue_depths = [1, 2, 4, 8, 16, 32, 64, 128, 256]

            for qd in queue_depths:
                offsets = (rng.integers(0, n_blocks - 1, 200_000) * self.BLOCK_4K).tolist()
                thread_iops  = [0] * qd
                stop_evt     = threading.Event()

                def reader(tid, ofs_list):
                    oidx = tid
                    tc = 0
                    try:
                        with open(tmp_file, 'rb', buffering=0) as fh:
                            while not stop_evt.is_set():
                                if oidx >= len(ofs_list): oidx = tid
                                fh.seek(ofs_list[oidx])
                                fh.read(self.BLOCK_4K)
                                tc += 1; oidx += qd
                    except Exception: pass
                    thread_iops[tid] = tc

                threads = [threading.Thread(target=reader, args=(i, offsets), daemon=True) for i in range(qd)]
                start = time.perf_counter()
                for t in threads: t.start()
                time.sleep(DURATION)
                stop_evt.set()
                for t in threads: t.join(timeout=3)

                elapsed = time.perf_counter() - start
                total_iops_n = sum(thread_iops) / elapsed
                iops_by_qd[f"QD{qd}"] = round(total_iops_n, 0)

        finally:
            _safe_remove(tmp_file)

        iops_values = list(iops_by_qd.values())
        saturation_qd = queue_depths[0]
        for i in range(1, len(iops_values)):
            if iops_values[i] < iops_values[i-1] * 1.05:
                saturation_qd = queue_depths[i]; break

        peak_iops = max(iops_values) if iops_values else 0
        qd1_iops  = iops_values[0] if iops_values else 0
        scaling   = peak_iops / max(qd1_iops, 1)
        score = self._normalize(peak_iops, 0, 1_000_000)

        return {
            "name":           "NVMe Queue Depth Scaling (QD1–QD256)",
            "value":          peak_iops, "unit": "IOPS (peak)",
            "qd1_iops":       qd1_iops, "peak_iops": peak_iops, "saturates_at_qd": saturation_qd,
            "scaling_factor": round(scaling, 2), "raw": len(queue_depths), "score": score,
            "description": f"QD1: {qd1_iops:.0f} IOPS → Peak: {peak_iops:.0f} IOPS. Scaling: {scaling:.1f}×."
        }

    def test_compression_sensitivity(self) -> dict:
        self.progress_cb("SSD: Compressible vs Incompressible Speed...", 64)
        DURATION   = self.DURATION_SHORT / 5
        BLOCK      = self.BLOCK_128K
        tmp_file   = f"{self._tmp_prefix}compress_test.tmp"

        def measure_write_speed(data: bytes) -> float:
            total = 0
            end   = time.perf_counter() + DURATION
            try:
                with open(tmp_file, 'wb', buffering=0) as f:
                    while time.perf_counter() < end:
                        f.write(data); total += len(data)
                    f.flush(); os.fsync(f.fileno())
            finally:
                _safe_remove(tmp_file)
            return total / DURATION / 1e6

        data_rand  = _make_random_data(BLOCK, seed=1)
        speed_rand = measure_write_speed(data_rand)

        data_zero  = b'\x00' * BLOCK
        speed_zero = measure_write_speed(data_zero)

        compression_gain_zero = speed_zero / max(speed_rand, 0.1)
        has_compression = compression_gain_zero > 1.3
        score = self._normalize(speed_rand, 0, 7000)

        return {
            "name":                "Compressible vs Incompressible Speed",
            "value":               round(speed_rand, 1), "unit": "MB/s",
            "random_mbs":          round(speed_rand, 1), "all_zeros_mbs": round(speed_zero, 1),
            "has_compression":     has_compression, "raw": 2, "score": score,
            "description": f"Random: {speed_rand:.0f}MB/s | All-zero: {speed_zero:.0f}MB/s. Compression engine: {'DETECTED' if has_compression else 'NOT detected'}."
        }

    def test_write_consistency(self) -> dict:
        self.progress_cb("SSD: Sequential Write Consistency...", 70)
        N_WRITES    = 1000
        BLOCK_SIZE  = self.BLOCK_128K
        tmp_file    = f"{self._tmp_prefix}consist_test.tmp"
        data        = _make_random_data(BLOCK_SIZE, seed=7)
        latencies   = []

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                for i in range(N_WRITES):
                    t0 = time.perf_counter()
                    f.write(data)
                    latencies.append((time.perf_counter() - t0) * 1000)
                f.flush(); os.fsync(f.fileno())
        finally:
            _safe_remove(tmp_file)

        lat_arr    = np.array(latencies, dtype=np.float64)
        avg_ms     = float(np.mean(lat_arr))
        std_ms     = float(np.std(lat_arr))
        cv              = std_ms / max(avg_ms, 0.001)
        consistency_pct = max(0, 100 - cv * 100)
        score = self._normalize(consistency_pct, 0, 100)

        return {
            "name":              "Sequential Write Consistency",
            "value":             round(consistency_pct, 1), "unit": "% consistency score",
            "avg_lat_ms":        round(avg_ms, 3), "std_lat_ms": round(std_ms, 3),
            "cv":                round(cv, 4), "raw": N_WRITES, "score": score,
            "description": f"{N_WRITES} sequential writes. Latency avg={avg_ms:.1f}ms. Consistency: {consistency_pct:.0f}%."
        }

    def test_over_provisioning_effect(self) -> dict:
        self.progress_cb("SSD: Over-Provisioning Effect Test...", 76)
        DURATION_PER_LEVEL = 3.0
        BLOCK_SIZE         = self.BLOCK_128K
        data               = _make_random_data(BLOCK_SIZE, seed=9)
        free_gb     = _get_free_space_gb(self.drive_root)
        if free_gb < 2.0:
            return {"name": "Over-Provisioning Effect Test", "error": "Insufficient free space", "score": 0}

        fill_pct_targets = [0, 50]
        speeds_by_fill   = {}
        fill_files       = []

        try:
            for fill_pct in fill_pct_targets:
                current_free = _get_free_space_gb(self.drive_root)
                target_fill_gb = (free_gb * fill_pct / 100)
                already_filled = free_gb - current_free
                to_fill = max(0, target_fill_gb - already_filled)

                if to_fill > 0.05:
                    fill_path = f"{self._tmp_prefix}fill_{fill_pct}.tmp"
                    fill_files.append(fill_path)
                    fill_chunk = _make_random_data(self.BLOCK_1M, seed=fill_pct)
                    try:
                        with open(fill_path, 'wb', buffering=0) as ff:
                            for _ in range(int(to_fill * 1000)): ff.write(fill_chunk)
                            ff.flush(); os.fsync(ff.fileno())
                    except OSError: pass

                tmp_measure = f"{self._tmp_prefix}measure_{fill_pct}.tmp"
                total_bytes = 0
                try:
                    with open(tmp_measure, 'wb', buffering=0) as f:
                        end_t = time.perf_counter() + DURATION_PER_LEVEL
                        while time.perf_counter() < end_t:
                            f.write(data); total_bytes += len(data)
                        f.flush(); os.fsync(f.fileno())
                except OSError: pass
                finally: _safe_remove(tmp_measure)

                speeds_by_fill[f"{fill_pct}%"] = round(total_bytes / DURATION_PER_LEVEL / 1e6, 1)

        finally:
            for fp in fill_files: _safe_remove(fp)

        if speeds_by_fill:
            peak_speed  = max(speeds_by_fill.values())
            worst_speed = min(speeds_by_fill.values())
            degradation = (1 - worst_speed / max(peak_speed, 1)) * 100
        else:
            peak_speed = worst_speed = degradation = 0

        score = self._normalize(worst_speed, 0, 5000)
        return {
            "name":              "Over-Provisioning Effect Test",
            "value":             round(degradation, 1), "unit": "% degradation",
            "peak_speed_mbs":    round(peak_speed, 1), "worst_speed_mbs": round(worst_speed, 1),
            "raw":               len(speeds_by_fill), "score": score,
            "description": f"Peak: {peak_speed:.0f}MB/s | Worst: {worst_speed:.0f}MB/s. Degradation: {degradation:.0f}%."
        }

    def test_steady_state_mixed(self) -> dict:
        self.progress_cb("SSD: Steady-State Mixed Workload...", 82)
        FILE_SIZE_MB  = 128
        BLOCK_SIZE    = self.BLOCK_4K
        DURATION      = self.DURATION_LONG
        rng           = np.random.default_rng(seed=77)
        tmp_file      = f"{self._tmp_prefix}steady_state.tmp"
        write_block   = _make_random_data(BLOCK_SIZE, seed=3)

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                chunk = _make_random_data(self.BLOCK_1M, seed=0)
                for _ in range(FILE_SIZE_MB): f.write(chunk)
                f.flush(); os.fsync(f.fileno())

            n_blocks = (FILE_SIZE_MB * 1024 * 1024) // BLOCK_SIZE
            offsets  = (rng.integers(0, n_blocks - 1, 100_000) * BLOCK_SIZE).tolist()
            is_read  = (rng.random(100_000) < 0.7).tolist()

            total_iops  = 0; oidx = 0
            start       = time.perf_counter()
            end_t       = start + DURATION

            with open(tmp_file, 'r+b', buffering=0) as f:
                while time.perf_counter() < end_t:
                    if oidx >= len(offsets): oidx = 0
                    f.seek(offsets[oidx])
                    if is_read[oidx]: f.read(BLOCK_SIZE)
                    else: f.write(write_block)
                    total_iops += 1; oidx += 1

            elapsed   = time.perf_counter() - start
            real_iops = total_iops / elapsed
        finally:
            _safe_remove(tmp_file)

        score = self._normalize(real_iops, 0, 500_000)
        return {
            "name":          "Steady-State Mixed Workload (70R/30W)",
            "value":         round(real_iops, 0), "unit": "IOPS",
            "raw":           total_iops, "score": score,
            "description": f"Conditioned steady-state: {real_iops:.0f} IOPS."
        }

    def test_read_after_write_latency(self) -> dict:
        self.progress_cb("SSD: Read-After-Write Latency...", 88)
        N_CYCLES   = 200
        BLOCK_SIZE = self.BLOCK_4K
        rng        = np.random.default_rng(seed=44)
        tmp_file   = f"{self._tmp_prefix}raw_test.tmp"

        try:
            file_data = _make_random_data(BLOCK_SIZE * 256, seed=8)
            with open(tmp_file, 'wb', buffering=0) as f:
                f.write(file_data); f.flush(); os.fsync(f.fileno())

            n_blocks  = len(file_data) // BLOCK_SIZE
            offsets   = (rng.integers(0, n_blocks - 1, N_CYCLES) * BLOCK_SIZE).tolist()
            write_blk = _make_random_data(BLOCK_SIZE, seed=2)

            lat_a = []
            with open(tmp_file, 'r+b', buffering=0) as f:
                for offset in offsets:
                    f.seek(offset); f.write(write_blk)
                    t0 = time.perf_counter()
                    f.seek(offset); f.read(BLOCK_SIZE)
                    lat_a.append((time.perf_counter() - t0) * 1e6)
        finally:
            _safe_remove(tmp_file)

        avg_raw_us = float(np.mean(lat_a)) if lat_a else 0
        score      = self._normalize(1.0 / max(avg_raw_us, 1), 0, 1)
        return {
            "name":          "Read-After-Write (RAW) Latency",
            "value":         round(avg_raw_us, 2), "unit": "µs",
            "raw":           N_CYCLES, "score": score,
            "description": f"RAW latency (immediate): {avg_raw_us:.1f}µs avg."
        }

    def test_thermal_throttle_detection(self) -> dict:
        self.progress_cb("SSD: Thermal Throttle Detection...", 93)
        INTERVAL_SEC = 2
        N_INTERVALS  = 5
        BLOCK_SIZE   = self.BLOCK_1M
        data         = _make_random_data(BLOCK_SIZE, seed=55)
        tmp_file     = f"{self._tmp_prefix}thermal_test.tmp"
        speed_by_interval = []
        throttle_detected = False

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                for interval in range(N_INTERVALS):
                    interval_bytes = 0
                    end_int = time.perf_counter() + INTERVAL_SEC
                    while time.perf_counter() < end_int:
                        try:
                            f.write(data); interval_bytes += len(data)
                        except OSError:
                            f.seek(0)
                    speed_by_interval.append(round(interval_bytes / INTERVAL_SEC / 1e6, 1))
                f.flush()
        finally:
            _safe_remove(tmp_file)

        if len(speed_by_interval) >= 3:
            baseline = speed_by_interval[0]
            for i in range(1, len(speed_by_interval)):
                if (baseline - speed_by_interval[i]) / max(baseline, 1) > 0.20:
                    throttle_detected = True; break

        peak_speed  = max(speed_by_interval) if speed_by_interval else 0
        final_speed = speed_by_interval[-1]  if speed_by_interval else 0
        speed_drop  = (1 - final_speed / max(peak_speed, 1)) * 100
        score = self._normalize(final_speed, 0, 7000)

        return {
            "name":               "Thermal Throttle Detection",
            "value":              round(speed_drop, 1), "unit": "% speed drop",
            "throttle_detected":  throttle_detected, "raw": N_INTERVALS, "score": score,
            "description": f"Peak: {peak_speed:.0f}MB/s | Final: {final_speed:.0f}MB/s. Thermal throttle: {'⚠️ DETECTED' if throttle_detected else '✅ None'}."
        }

    def test_fragmentation_degradation(self) -> dict:
        self.progress_cb("SSD: Fragmentation Degradation Analysis...", 97)
        DURATION  = self.DURATION_SHORT / 3
        tmp_large = f"{self._tmp_prefix}frag_large.tmp"
        data_1m   = _make_random_data(self.BLOCK_1M, seed=20)
        bytes_a   = 0
        try:
            with open(tmp_large, 'wb', buffering=0) as f:
                end_a = time.perf_counter() + DURATION
                while time.perf_counter() < end_a:
                    f.write(data_1m); bytes_a += len(data_1m)
                f.flush(); os.fsync(f.fileno())
        finally:
            _safe_remove(tmp_large)
        speed_a = bytes_a / DURATION / 1e6

        data_small  = _make_random_data(4096, seed=21)
        small_files = []
        bytes_b     = 0; end_b = time.perf_counter() + DURATION; file_idx = 0
        while time.perf_counter() < end_b:
            fname = f"{self._tmp_prefix}frag_sm_{file_idx}.tmp"
            small_files.append(fname)
            try:
                with open(fname, 'wb', buffering=0) as f:
                    f.write(data_small); bytes_b += len(data_small)
                file_idx += 1
            except OSError: break
        for sf in small_files: _safe_remove(sf)
        speed_b = bytes_b / DURATION / 1e6

        frag_sensitivity = (1 - speed_b / max(speed_a, 1)) * 100
        score = self._normalize(100 - frag_sensitivity, 0, 100)

        return {
            "name":               "Fragmentation Degradation Analysis",
            "value":              round(frag_sensitivity, 1), "unit": "% degradation",
            "contiguous_mbs":     round(speed_a, 1), "fragmented_mbs": round(speed_b, 1),
            "raw":                3, "score": score,
            "description": f"Contiguous: {speed_a:.0f}MB/s | Fragmented: {speed_b:.0f}MB/s. Sensitivity: {frag_sensitivity:.0f}%."
        }

    # ── RUN ALL ───────────────────────────────────────────────────

    def run_all(self) -> dict:
        self._create_test_file(self.SEQ_FILE_SIZE_MB, show_progress=True)

        tests = [
            # Basic Tests
            self.test_sequential_read,
            self.test_sequential_write,
            self.test_random_4k_read_q1t1,
            self.test_random_4k_read_q32,
            self.test_random_4k_write_q1t1,
            self.test_mixed_readwrite,
            self.test_access_time,
            # Extended Tests
            self.test_sustained_write_slc_cache,
            self.test_write_amplification,
            self.test_queue_depth_scaling,
            self.test_compression_sensitivity,
            self.test_write_consistency,
            self.test_over_provisioning_effect,
            self.test_steady_state_mixed,
            self.test_read_after_write_latency,
            self.test_thermal_throttle_detection,
            self.test_fragmentation_degradation,
        ]

        results = []
        for idx, fn in enumerate(tests):
            try:
                r = fn()
                results.append(r)
                self.progress_cb(f"✅ {r['name'][:50]}", int((idx + 1) / len(tests) * 100))
            except Exception as e:
                results.append({"name": fn.__name__, "error": str(e), "score": 0})

        self._cleanup()
        scoreable = [r["score"] for r in results if "score" in r and "error" not in r]
        overall   = int(np.mean(scoreable)) if scoreable else 0
        self.progress_cb("SSD Benchmark Complete!", 100)

        return {
            "component":     "SSD",
            "overall_score": overall,
            "grade":         self._grade(overall),
            "tier":          self._tier(overall),
            "tests":         results,
        }

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
        if score >= 85_000: return "PCIe 5.0 NVMe"
        if score >= 70_000: return "PCIe 4.0 NVMe"
        if score >= 55_000: return "PCIe 3.0 NVMe"
        if score >= 40_000: return "SATA SSD"
        if score >= 25_000: return "Entry SATA SSD"
        return "HDD / Legacy"
