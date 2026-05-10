"""
SYSTEM VITAL HDD FULL BENCHMARK SUITE — Part 4B
Complete hard disk drive benchmark suite:

  1.  Sequential Transfer Rate Curve      (HDTune Sequential)
  2.  Full / Average / Track-to-Track Seek Time (HDTune Seek)
  3.  Rotational Latency Measurement      (WinDFT rotational)
  4.  SMR vs CMR Detection                (Shingled Magnetic Recording)
  5.  Buffer / Cache Effect Analysis      (HDTune Cache)
  6.  Sustained Write Consistency         (IOMeter sustained HDD)
  7.  Head Parking Detection              (APM idle park test)
  8.  Zone Transfer Rate Map              (Zone-based speed map)
  9.  Random vs Sequential Ratio          (HDTach comparison)
  10. HDD Health Score                    (Composite SMART-like)
"""

import os
import sys
import time
import math
import random
import statistics
import threading
import numpy as np
from typing import Callable, Optional, List, Dict, Tuple


def _make_data_block(size: int, seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed=seed)
    return rng.integers(0, 256, size, dtype=np.uint8).tobytes()

def _get_drive_root(ref: str = None) -> str:
    path  = ref or os.path.abspath(__file__)
    drive = os.path.splitdrive(path)[0]
    return (drive + os.sep) if drive else os.sep

def _free_space_gb(path: str) -> float:
    try:
        import shutil
        return shutil.disk_usage(path).free / 1e9
    except Exception:
        return 0.0

def _is_likely_hdd(drive_root: str) -> bool:
    try:
        if sys.platform == "win32":
            try:
                import wmi
                w = wmi.WMI()
                for disk in w.Win32_DiskDrive():
                    if hasattr(disk, 'MediaType'):
                        mt = str(disk.MediaType).lower()
                        if 'external hard disk' in mt or 'fixed hard disk' in mt:
                            return True
                        if 'solid state' in mt:
                            return False
            except Exception:
                pass
    except Exception:
        pass
    return True

class _TmpFile:
    def __init__(self, path: str, size_mb: int, block_size: int = 1048576):
        self.path      = path
        self.size_mb   = size_mb
        self.block_size = block_size

    def __enter__(self) -> str:
        data = _make_data_block(self.block_size, seed=0)
        with open(self.path, 'wb', buffering=0) as f:
            for _ in range(self.size_mb):
                f.write(data)
            f.flush()
            os.fsync(f.fileno())
        return self.path

    def __exit__(self, *args):
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
        except Exception:
            pass


class HDDBenchmark:
    BLOCK_512     = 512
    BLOCK_4K      = 4096
    BLOCK_64K     = 65536
    BLOCK_512K    = 524288
    BLOCK_1M      = 1048576
    BLOCK_8M      = 8388608
    DURATION      = 5.0

    def __init__(self,
                 test_drive: str = None,
                 progress_callback: Optional[Callable] = None):
        self.progress_cb  = progress_callback or (lambda m, p: None)
        self.drive_root   = _get_drive_root(test_drive)
        self._prefix      = os.path.join(self.drive_root, "_dkbench_hdd_")
        self._is_hdd      = _is_likely_hdd(self.drive_root)

    def test_sequential_transfer_curve(self) -> dict:
        self.progress_cb("HDD: Sequential Transfer Rate Curve...", 10)
        FILE_SIZE_MB = min(2048, max(512, int(_free_space_gb(self.drive_root) * 1e3 * 0.2)))
        FILE_SIZE_MB = max(256, FILE_SIZE_MB)
        BLOCK_SIZE   = self.BLOCK_8M
        N_ZONES      = 8
        tmp_file     = f"{self._prefix}seq_curve.tmp"
        zone_speeds = []; total_read = 0

        try:
            with _TmpFile(tmp_file, FILE_SIZE_MB) as fp:
                file_size_bytes = FILE_SIZE_MB * 1024 * 1024
                zone_size       = file_size_bytes // N_ZONES
                with open(fp, 'rb', buffering=0) as f:
                    for zone in range(N_ZONES):
                        zone_offset = zone * zone_size
                        n_reads     = zone_size // BLOCK_SIZE
                        zone_bytes  = 0
                        f.seek(zone_offset)
                        start = time.perf_counter()
                        for _ in range(n_reads):
                            data = f.read(BLOCK_SIZE)
                            if not data: break
                            zone_bytes += len(data)
                        elapsed = time.perf_counter() - start
                        speed_mbs = zone_bytes / elapsed / 1e6
                        pct_pos   = zone / N_ZONES * 100
                        zone_speeds.append({
                            "zone": zone + 1, "offset_gb": round(zone_offset / 1e9, 2),
                            "pct_from_start": round(pct_pos, 0), "speed_mbs": round(speed_mbs, 1),
                        })
                        total_read += zone_bytes
        except Exception as e:
            return {"name": "Sequential Transfer Rate Curve", "error": str(e), "score": 0}

        if zone_speeds:
            speeds = [z["speed_mbs"] for z in zone_speeds]
            outer_speed = speeds[0]; inner_speed = speeds[-1]
            avg_speed = statistics.mean(speeds)
            speed_dropoff = (outer_speed - inner_speed) / max(outer_speed, 1) * 100
        else:
            outer_speed = inner_speed = avg_speed = speed_dropoff = 0

        hdd_signature = speed_dropoff > 15
        score = self._normalize(avg_speed, 0, 300)

        return {
            "name":            "Sequential Transfer Rate Curve",
            "value":           round(avg_speed, 1), "unit": "MB/s",
            "outer_speed_mbs": round(outer_speed, 1), "inner_speed_mbs": round(inner_speed, 1),
            "speed_dropoff_pct": round(speed_dropoff, 1), "hdd_signature": hdd_signature,
            "raw":             total_read, "score": score,
            "description": f"Outer: {outer_speed:.0f}MB/s | Inner: {inner_speed:.0f}MB/s | Avg: {avg_speed:.0f}MB/s. Drop: {speed_dropoff:.0f}%."
        }

    def test_seek_time(self) -> dict:
        self.progress_cb("HDD: Seek Time Profiling...", 20)
        FILE_SIZE_MB  = 512
        N_SEEKS       = 500
        READ_SIZE     = self.BLOCK_512
        tmp_file      = f"{self._prefix}seek_test.tmp"
        rng           = np.random.default_rng(seed=11)

        try:
            with _TmpFile(tmp_file, FILE_SIZE_MB) as fp:
                file_size = FILE_SIZE_MB * 1024 * 1024
                max_pos   = file_size - READ_SIZE
                full_latencies = []
                with open(fp, 'rb', buffering=0) as f:
                    positions = []
                    for i in range(N_SEEKS // 2):
                        if i % 2 == 0: positions.append(int(rng.integers(0, max_pos // 4)))
                        else: positions.append(int(rng.integers(3 * max_pos // 4, max_pos)))
                    for pos in positions:
                        t0 = time.perf_counter(); f.seek(pos); f.read(READ_SIZE)
                        full_latencies.append((time.perf_counter() - t0) * 1000)

                avg_latencies  = []
                all_positions  = rng.integers(0, max_pos, N_SEEKS, dtype=np.int64).tolist()
                with open(fp, 'rb', buffering=0) as f:
                    for pos in all_positions:
                        t0 = time.perf_counter(); f.seek(pos); f.read(READ_SIZE)
                        avg_latencies.append((time.perf_counter() - t0) * 1000)

                ttt_latencies = []; TRACK_STEP = 131072
                with open(fp, 'rb', buffering=0) as f:
                    pos = 0
                    for _ in range(N_SEEKS):
                        f.seek(pos)
                        t0 = time.perf_counter(); f.read(READ_SIZE)
                        ttt_latencies.append((time.perf_counter() - t0) * 1000)
                        pos = (pos + TRACK_STEP) % max_pos

        except Exception as e:
            return {"name": "Seek Time Profiling", "error": str(e), "score": 0}

        def s(lats):
            if not lats: return {}
            a = np.array(lats, dtype=np.float64)
            a = a[a < np.percentile(a, 99)]
            return {"avg_ms": round(float(np.mean(a)), 3)}

        full_stats = s(full_latencies); avg_stats = s(avg_latencies); ttt_stats = s(ttt_latencies)
        avg_seek_ms = avg_stats.get("avg_ms", 0)

        if avg_seek_ms > 5: drive_type = "HDD (mechanical)"
        elif avg_seek_ms > 0.5: drive_type = "Hybrid / Slow SSD"
        else: drive_type = "SSD (solid state)"

        score = self._normalize(1.0 / max(avg_seek_ms, 0.01), 0, 100)

        return {
            "name":           "Seek Time Profiling",
            "value":          avg_seek_ms, "unit": "ms (avg seek)",
            "drive_type":     drive_type, "raw": N_SEEKS * 3, "score": score,
            "description": f"Full={full_stats.get('avg_ms','?')}ms | Avg={avg_seek_ms:.3f}ms | TtT={ttt_stats.get('avg_ms','?')}ms. Type: {drive_type}."
        }

    def test_rotational_latency(self) -> dict:
        self.progress_cb("HDD: Rotational Latency Measurement...", 30)
        FILE_SIZE_MB = 128
        TRACK_SIZE   = 131072
        N_SAMPLES    = 200
        tmp_file     = f"{self._prefix}rot_lat.tmp"
        rng          = np.random.default_rng(seed=22)

        try:
            with _TmpFile(tmp_file, FILE_SIZE_MB) as fp:
                within_track_lats = []
                offsets_in_track  = rng.integers(0, TRACK_SIZE - 512, N_SAMPLES, dtype=np.int64)
                with open(fp, 'rb', buffering=0) as f:
                    f.seek(TRACK_SIZE * 10); f.read(512)
                    for offset in offsets_in_track:
                        t0 = time.perf_counter()
                        f.seek(int(TRACK_SIZE * 10 + offset)); f.read(512)
                        within_track_lats.append((time.perf_counter() - t0) * 1000)

                same_sector_lats = []
                BASE_POS = TRACK_SIZE * 50
                with open(fp, 'rb', buffering=0) as f:
                    for _ in range(N_SAMPLES):
                        f.seek(BASE_POS)
                        t0 = time.perf_counter(); f.read(512)
                        same_sector_lats.append((time.perf_counter() - t0) * 1000)
        except Exception as e:
            return {"name": "Rotational Latency Measurement", "error": str(e), "score": 0}

        wt_arr = np.array(within_track_lats, dtype=np.float64)
        wt_arr = wt_arr[wt_arr < np.percentile(wt_arr, 99)]
        avg_wt_ms = float(np.mean(wt_arr))
        max_wt_ms = float(np.max(wt_arr))

        estimated_rpm = None
        if max_wt_ms > 1.0:
            estimated_rpm = round(60_000 / (max_wt_ms * 2), 0)

        rpm_class = "Unknown"
        if estimated_rpm:
            if 10500 > estimated_rpm > 9500: rpm_class = "10000 RPM (Enterprise)"
            elif 7500 > estimated_rpm > 7000: rpm_class = "7200 RPM (Desktop HDD)"
            elif 5800 > estimated_rpm > 5200: rpm_class = "5400 RPM (Laptop HDD)"
            else: rpm_class = f"~{estimated_rpm:.0f} RPM"
        elif avg_wt_ms < 0.5: rpm_class = "SSD"

        score = self._normalize(1.0 / max(avg_wt_ms, 0.001), 0, 1000)
        return {
            "name":               "Rotational Latency",
            "value":              round(avg_wt_ms, 3), "unit": "ms",
            "estimated_rpm":      estimated_rpm, "rpm_classification": rpm_class,
            "raw":                N_SAMPLES * 2, "score": score,
            "description": f"Within-track avg: {avg_wt_ms:.2f}ms. Est RPM: {estimated_rpm or 'N/A'} → {rpm_class}."
        }

    def test_smr_cmr_detection(self) -> dict:
        self.progress_cb("HDD: SMR vs CMR Detection...", 40)
        DURATION     = self.DURATION
        BLOCK_LARGE  = self.BLOCK_512K
        BLOCK_SMALL  = self.BLOCK_4K
        FILE_SIZE_MB = 128
        tmp_seq      = f"{self._prefix}smr_seq.tmp"
        tmp_rand     = f"{self._prefix}smr_rand.tmp"
        rng          = np.random.default_rng(seed=33)

        data_large   = _make_data_block(BLOCK_LARGE, seed=1)
        data_small   = _make_data_block(BLOCK_SMALL, seed=2)
        seq_bytes = 0

        try:
            with open(tmp_seq, 'wb', buffering=0) as f:
                end_s = time.perf_counter() + DURATION
                while time.perf_counter() < end_s:
                    f.write(data_large); seq_bytes += len(data_large)
                f.flush(); os.fsync(f.fileno())
        finally:
            try: os.remove(tmp_seq)
            except: pass
        seq_mbs = seq_bytes / DURATION / 1e6

        rand_bytes = 0
        try:
            with open(tmp_rand, 'wb', buffering=0) as f:
                for _ in range(FILE_SIZE_MB * 2): f.write(data_large)
                f.flush(); os.fsync(f.fileno())

            n_blocks = (FILE_SIZE_MB * 2 * 1024 * 1024) // BLOCK_SMALL
            offsets  = (rng.integers(0, n_blocks - 1, 50_000) * BLOCK_SMALL).tolist()
            oidx     = 0
            with open(tmp_rand, 'r+b', buffering=0) as f:
                end_r = time.perf_counter() + DURATION
                while time.perf_counter() < end_r:
                    if oidx >= len(offsets): oidx = 0
                    f.seek(offsets[oidx])
                    f.write(data_small); rand_bytes += BLOCK_SMALL; oidx += 1
        finally:
            try: os.remove(tmp_rand)
            except: pass

        rand_mbs  = rand_bytes / DURATION / 1e6
        rand_to_seq_ratio = rand_mbs / max(seq_mbs, 1)
        smr_detected = rand_to_seq_ratio < 0.05 and self._is_hdd

        score = self._normalize(rand_mbs, 0, 200)
        return {
            "name":               "SMR vs CMR Detection",
            "value":              round(rand_to_seq_ratio * 100, 2), "unit": "% rand/seq",
            "seq_write_mbs":      round(seq_mbs, 1), "rand_write_mbs": round(rand_mbs, 2),
            "smr_detected":       smr_detected, "raw": seq_bytes + rand_bytes, "score": score,
            "description": f"Seq write: {seq_mbs:.0f}MB/s | Rand 4K: {rand_mbs:.1f}MB/s ({rand_to_seq_ratio*100:.1f}%). SMR: {'⚠️ DETECTED' if smr_detected else '✅ CMR'}."
        }

    def test_buffer_cache_effect(self) -> dict:
        self.progress_cb("HDD: Buffer / Cache Effect Analysis...", 50)
        BLOCK_SIZE     = self.BLOCK_1M
        N_READS        = 32
        tmp_file       = f"{self._prefix}cache_test.tmp"
        FILE_SIZE_MB   = N_READS

        try:
            with _TmpFile(tmp_file, FILE_SIZE_MB) as fp:
                cold_speeds = []
                with open(fp, 'rb', buffering=0) as f:
                    for i in range(N_READS):
                        t0 = time.perf_counter(); data = f.read(BLOCK_SIZE)
                        if data: cold_speeds.append(len(data) / (time.perf_counter() - t0) / 1e6)

                warm_speeds = []
                with open(fp, 'rb', buffering=0) as f:
                    for i in range(N_READS):
                        t0 = time.perf_counter(); data = f.read(BLOCK_SIZE)
                        if data: warm_speeds.append(len(data) / (time.perf_counter() - t0) / 1e6)
        except Exception as e:
            return {"name": "Buffer / Cache Effect", "error": str(e), "score": 0}

        cold_avg = statistics.mean(cold_speeds) if cold_speeds else 0
        warm_avg = statistics.mean(warm_speeds) if warm_speeds else 0
        seq_speedup = warm_avg / max(cold_avg, 0.1)

        buffer_detected = seq_speedup > 1.3
        score = self._normalize(warm_avg, 0, 300)

        return {
            "name":              "Buffer / Cache Effect Analysis",
            "value":             round(seq_speedup, 2), "unit": "× speedup",
            "cold_seq_mbs":      round(cold_avg, 1), "warm_seq_mbs": round(warm_avg, 1),
            "buffer_detected":   buffer_detected, "raw": N_READS * 2, "score": score,
            "description": f"Cold: {cold_avg:.0f}MB/s → Warm: {warm_avg:.0f}MB/s ({seq_speedup:.1f}× speedup). Buffer: {'detected' if buffer_detected else 'not significant'}."
        }

    def test_sustained_write_consistency(self) -> dict:
        self.progress_cb("HDD: Sustained Write Consistency...", 60)
        N_WRITES   = 500
        BLOCK_SIZE = self.BLOCK_512K
        tmp_file   = f"{self._prefix}writ_consist.tmp"
        data       = _make_data_block(BLOCK_SIZE, seed=4)
        latencies  = []

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                for i in range(N_WRITES):
                    t0 = time.perf_counter()
                    f.write(data)
                    latencies.append((time.perf_counter() - t0) * 1000)
                f.flush(); os.fsync(f.fileno())
        finally:
            try: os.remove(tmp_file)
            except: pass

        lat_arr     = np.array(latencies, dtype=np.float64)
        avg_ms      = float(np.mean(lat_arr))
        std_ms      = float(np.std(lat_arr))
        avg_mbs     = BLOCK_SIZE / (avg_ms / 1000) / 1e6
        cv          = std_ms / max(avg_ms, 0.001)
        consistency = max(0, 100 - cv * 100)

        score = self._normalize(avg_mbs, 0, 300)
        return {
            "name":              "Sustained Write Consistency",
            "value":             round(avg_mbs, 1), "unit": "MB/s",
            "consistency_pct":   round(consistency, 1), "raw": N_WRITES, "score": score,
            "description": f"Avg speed: {avg_mbs:.0f}MB/s. Consistency: {consistency:.0f}%."
        }

    def test_head_parking_detection(self) -> dict:
        self.progress_cb("HDD: Head Parking Detection...", 70)
        BLOCK_SIZE     = self.BLOCK_4K
        tmp_file       = f"{self._prefix}park_test.tmp"
        WAIT_TIMES_SEC = [0, 1, 5, 8]
        latencies_by_wait = {}

        try:
            with _TmpFile(tmp_file, 64) as fp:
                for wait_sec in WAIT_TIMES_SEC:
                    with open(fp, 'rb', buffering=0) as f: f.read(BLOCK_SIZE)
                    time.sleep(wait_sec)
                    sample_lats = []
                    with open(fp, 'rb', buffering=0) as f:
                        for _ in range(3):
                            f.seek(0)
                            t0 = time.perf_counter(); f.read(BLOCK_SIZE)
                            sample_lats.append((time.perf_counter() - t0) * 1000)
                    latencies_by_wait[f"{wait_sec}s"] = round(statistics.mean(sample_lats), 2)
        except Exception as e:
            return {"name": "Head Parking Detection", "error": str(e), "score": 0}

        base_lat = latencies_by_wait.get("0s", 0)
        max_lat = max(latencies_by_wait.values()) if latencies_by_wait else 0
        park_ratio = max_lat / max(base_lat, 0.1)
        park_detected = park_ratio > 3.0

        score = self._normalize(1.0 / max(park_ratio, 1.0), 0, 1.0)
        return {
            "name":               "Head Parking Detection (APM)",
            "value":              round(park_ratio, 2), "unit": "× wake latency vs baseline",
            "park_ratio_x":       round(park_ratio, 2), "parking_detected": park_detected,
            "raw":                len(WAIT_TIMES_SEC), "score": score,
            "description": f"Base lat: {base_lat:.1f}ms | Max: {max_lat:.1f}ms. Ratio: {park_ratio:.1f}×. Head parking: {'⚠️ DETECTED' if park_detected else '✅ Not detected'}."
        }

    def test_zone_transfer_map(self) -> dict:
        self.progress_cb("HDD: Zone Transfer Rate Map...", 80)
        N_ZONES    = 4
        ZONE_MB    = 32
        BLOCK_SIZE = self.BLOCK_1M
        total_mb   = N_ZONES * ZONE_MB
        tmp_file   = f"{self._prefix}zone_map.tmp"
        zone_results = []

        try:
            data = _make_data_block(BLOCK_SIZE, seed=6)
            with open(tmp_file, 'wb', buffering=0) as f:
                for _ in range(total_mb): f.write(data)
                f.flush(); os.fsync(f.fileno())

            zone_size_bytes = ZONE_MB * 1024 * 1024
            with open(tmp_file, 'rb', buffering=0) as f:
                for zone in range(N_ZONES):
                    start_byte = zone * zone_size_bytes
                    f.seek(start_byte)
                    zone_bytes = 0
                    start = time.perf_counter()
                    deadline = start + 1.0
                    while time.perf_counter() < deadline:
                        chunk = f.read(BLOCK_SIZE)
                        if not chunk: break
                        zone_bytes += len(chunk)
                    speed_mbs = zone_bytes / (time.perf_counter() - start) / 1e6
                    zone_results.append(speed_mbs)
        except Exception as e:
            return {"name": "Zone Transfer Rate Map", "error": str(e), "score": 0}
        finally:
            try: os.remove(tmp_file)
            except: pass

        if zone_results:
            outer_speed = zone_results[0]; inner_speed = zone_results[-1]
            avg_speed = statistics.mean(zone_results)
            uniformity = (1 - (outer_speed - inner_speed) / max(outer_speed, 1)) * 100
        else:
            outer_speed = inner_speed = avg_speed = uniformity = 0

        score = self._normalize(avg_speed, 0, 300)
        return {
            "name":          "Zone Transfer Rate Map",
            "value":         round(avg_speed, 1), "unit": "MB/s",
            "uniformity_pct":round(uniformity, 1), "raw": N_ZONES, "score": score,
            "description": f"Outer: {outer_speed:.0f}MB/s | Inner: {inner_speed:.0f}MB/s | Avg: {avg_speed:.0f}MB/s. Uniformity: {uniformity:.0f}%."
        }

    def test_random_vs_sequential_ratio(self) -> dict:
        self.progress_cb("HDD: Random vs Sequential Performance Ratio...", 90)
        DURATION     = 1.0
        FILE_SIZE_MB = 128
        tmp_file     = f"{self._prefix}rsratio.tmp"
        rng          = np.random.default_rng(seed=77)

        block_sizes = [(4096, "4KB"), (1048576, "1MB")]
        results = {}

        try:
            data_1m = _make_data_block(self.BLOCK_1M, seed=7)
            with open(tmp_file, 'wb', buffering=0) as f:
                for _ in range(FILE_SIZE_MB): f.write(data_1m)
                f.flush(); os.fsync(f.fileno())

            file_size = FILE_SIZE_MB * 1024 * 1024

            for block_sz, label in block_sizes:
                n_blocks = file_size // block_sz
                seq_bytes = 0
                with open(tmp_file, 'rb', buffering=0) as f:
                    end_s = time.perf_counter() + DURATION
                    while time.perf_counter() < end_s:
                        chunk = f.read(block_sz)
                        if not chunk: f.seek(0)
                        else: seq_bytes += len(chunk)
                seq_mbs = seq_bytes / DURATION / 1e6

                rand_offsets = (rng.integers(0, n_blocks - 1, 50_000) * block_sz).tolist()
                rand_bytes = 0; oidx = 0
                with open(tmp_file, 'rb', buffering=0) as f:
                    end_r = time.perf_counter() + DURATION
                    while time.perf_counter() < end_r:
                        if oidx >= len(rand_offsets): oidx = 0
                        f.seek(rand_offsets[oidx]); f.read(block_sz)
                        rand_bytes += block_sz; oidx += 1
                rand_mbs = rand_bytes / DURATION / 1e6

                ratio_pct = rand_mbs / max(seq_mbs, 0.001) * 100
                results[label] = {"seq_mbs": seq_mbs, "rand_mbs": rand_mbs, "ratio_pct": ratio_pct}
        finally:
            try: os.remove(tmp_file)
            except: pass

        ratio_4k = results.get("4KB", {}).get("ratio_pct", 0)
        avg_seq  = results.get("1MB", {}).get("seq_mbs", 0)
        avg_rand = results.get("4KB", {}).get("rand_mbs", 0)
        score    = self._normalize(ratio_4k, 0, 100)

        if ratio_4k > 30: drive_char = "NVMe SSD (excellent random)"
        elif ratio_4k > 15: drive_char = "SATA SSD (good random)"
        elif ratio_4k > 5: drive_char = "Hybrid / Fast HDD"
        else: drive_char = "HDD (poor random — seek-limited)"

        return {
            "name":            "Random vs Sequential Performance Ratio",
            "value":           round(ratio_4k, 2), "unit": "% random/sequential (4K)",
            "drive_character": drive_char, "raw": len(block_sizes), "score": score,
            "description": f"4K ratio: {ratio_4k:.1f}%. Drive: {drive_char}. Avg seq: {avg_seq:.0f}MB/s | Avg rand: {avg_rand:.1f}MB/s."
        }

    def test_hdd_health_score(self) -> dict:
        self.progress_cb("HDD: Health Composite Score...", 95)
        FILE_SIZE_MB   = 32
        BLOCK_SIZE     = self.BLOCK_4K
        N_CYCLES       = 100
        tmp_file       = f"{self._prefix}health.tmp"
        rng            = np.random.default_rng(seed=99)
        health_score   = 100

        try:
            data_blocks = [_make_data_block(BLOCK_SIZE, seed=i) for i in range(16)]
            with open(tmp_file, 'wb', buffering=0) as f:
                for i in range(FILE_SIZE_MB * 256):
                    f.write(data_blocks[i % 16])
                f.flush(); os.fsync(f.fileno())

            n_blocks  = FILE_SIZE_MB * 1024 * 1024 // BLOCK_SIZE
            stable_pos = rng.integers(0, n_blocks // 2, N_CYCLES // 4, dtype=np.int64) * BLOCK_SIZE
            read_errors = 0
            with open(tmp_file, 'rb', buffering=0) as f:
                for pos in stable_pos:
                    f.seek(int(pos)); read1 = f.read(BLOCK_SIZE)
                    f.seek(int(pos)); read2 = f.read(BLOCK_SIZE)
                    if read1 != read2: read_errors += 1

            stability = (1 - read_errors / max(len(stable_pos), 1)) * 100
            health_score = stability

        except Exception as e:
            return {"name": "HDD Health Composite Score", "error": str(e), "score": 0}
        finally:
            try: os.remove(tmp_file)
            except: pass

        score = self._normalize(health_score, 0, 100)
        return {
            "name":          "HDD Health Composite Score",
            "value":         round(health_score, 1), "unit": "% health score",
            "raw":           N_CYCLES, "score": score,
            "description": f"Composite health: {health_score:.1f}%."
        }

    def run_all(self) -> dict:
        tests = [
            self.test_sequential_transfer_curve,
            self.test_seek_time,
            self.test_rotational_latency,
            self.test_smr_cmr_detection,
            self.test_buffer_cache_effect,
            self.test_sustained_write_consistency,
            self.test_head_parking_detection,
            self.test_zone_transfer_map,
            self.test_random_vs_sequential_ratio,
            self.test_hdd_health_score,
        ]

        results = []
        for idx, fn in enumerate(tests):
            try:
                r = fn()
                results.append(r)
                self.progress_cb(f"✅ {r['name'][:50]}", int((idx + 1) / len(tests) * 100))
            except Exception as e:
                results.append({"name": fn.__name__, "error": str(e), "score": 0})

        scoreable = [r["score"] for r in results if "score" in r and "error" not in r]
        overall   = int(np.mean(scoreable)) if scoreable else 0
        self.progress_cb("HDD Benchmark Complete!", 100)

        return {
            "component":     "HDD",
            "overall_score": overall,
            "grade":         self._grade(overall),
            "tier":          self._tier(overall),
            "is_hdd":        self._is_hdd,
            "drive_root":    self.drive_root,
            "tests":         results,
        }

    @staticmethod
    def _normalize(v, lo, hi, omin=0, omax=100_000):
        if hi == lo: return omin
        return int(omin + (max(lo, min(hi, v)) - lo) / (hi - lo) * (omax - omin))

    @staticmethod
    def _grade(s):
        if s >= 85_000: return "S"
        if s >= 70_000: return "A"
        if s >= 55_000: return "B"
        if s >= 40_000: return "C"
        if s >= 25_000: return "D"
        return "F"

    @staticmethod
    def _tier(s):
        if s >= 70_000: return "Enterprise HDD / Fast SSD"
        if s >= 55_000: return "7200 RPM Desktop HDD"
        if s >= 40_000: return "5400 RPM Laptop HDD"
        if s >= 25_000: return "SMR HDD / Old HDD"
        return "Failing / Very Old HDD"
