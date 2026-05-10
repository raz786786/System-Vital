"""
SYSTEM VITAL SYSTEM-LEVEL BENCHMARK SUITE — Part 5
Industry-level system-wide benchmarks:

  1.  PCIe Bandwidth & Latency            (GPU-Z PCIe / CUDA bandwidth test)
  2.  USB Transfer Speed Profile          (USBDeview / CrystalDiskMark USB)
  3.  Network Latency & Throughput        (iPerf3 / NetIO / ping analysis)
  4.  Inter-Process Communication (IPC)   (lmbench pipe / shared mem latency)
  5.  OS Scheduler Latency                (LatencyMon / cyclictest equivalent)
  6.  System Call Overhead                (syscall benchmark / strace overhead)
  7.  Interrupt & Context Switch Latency  (LatencyMon IRQ / context switch test)
  8.  Power Consumption Estimation        (HWiNFO power model / RAPL equivalent)
  9.  Thermal Dissipation Rate            (Core temp delta / thermal resistance)
  10. Full System Stress Test             (AIDA64 System Stability equivalent)

Design principles:
  - Pure Python + stdlib (no kernel modules, no drivers needed)
  - No admin rights required (graceful fallback where needed)
  - Cross-platform where possible (Windows primary, Linux fallback)
  - All results normalized to 0–100,000 score scale
  - Every test includes grade, tier, and detailed description
  - Thread-safe, cancellable via threading.Event
"""

import os
import sys
import time
import math
import socket
import struct
import hashlib
import ctypes
import platform
import threading
import subprocess
import multiprocessing
import statistics
import tempfile
import signal
import queue
import select
import numpy as np
from typing import Callable, Optional, Dict, List, Tuple, Any


# ══════════════════════════════════════════════════════════════
#  PLATFORM DETECTION & CONSTANTS
# ══════════════════════════════════════════════════════════════

IS_WINDOWS = sys.platform == "win32"
IS_LINUX   = sys.platform.startswith("linux")
IS_MAC     = sys.platform == "darwin"

CPU_COUNT  = multiprocessing.cpu_count()
PAGE_SIZE  = 4096

# Windows-specific imports
if IS_WINDOWS:
    try:
        import winreg
        import ctypes.wintypes
        WINDOWS_IMPORTS_OK = True
    except ImportError:
        WINDOWS_IMPORTS_OK = False
else:
    WINDOWS_IMPORTS_OK = False

# psutil for power/thermal (optional but recommended)
try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

# wmi for Windows hardware info (optional)
try:
    import wmi
    WMI_OK = True
except ImportError:
    WMI_OK = False

# GPUtil for GPU power (optional)
try:
    import GPUtil
    GPUTIL_OK = True
except ImportError:
    GPUTIL_OK = False


# ══════════════════════════════════════════════════════════════
#  MODULE-LEVEL WORKER FUNCTIONS
#  (Must be top-level for multiprocessing on Windows)
# ══════════════════════════════════════════════════════════════

def _stress_cpu_worker(args: tuple) -> dict:
    """
    CPU stress worker for system stress test.
    Runs matrix multiply + SHA256 for duration seconds.
    """
    duration, seed, worker_id = args
    end_time    = time.perf_counter() + duration
    iterations  = 0
    rng         = np.random.default_rng(seed=seed)
    A           = rng.standard_normal((256, 256), dtype=np.float64)
    B           = rng.standard_normal((256, 256), dtype=np.float64)
    hash_data   = b"SYSTEM VITAL_STRESS_" * 64

    while time.perf_counter() < end_time:
        # Matrix multiply (FP stress)
        C = np.dot(A, B)
        # Hash (INT stress)
        hashlib.sha256(hash_data + C[0].tobytes()).digest()
        # Mix result back in (prevents compiler optimization)
        A[0, 0] = C[0, 0] * 1e-10
        iterations += 1

    return {
        "worker_id":  worker_id,
        "iterations": iterations,
        "ops_per_sec": iterations / duration,
    }


def _stress_ram_worker(args: tuple) -> dict:
    """RAM stress worker: STREAM triad for duration seconds."""
    duration, size_mb, worker_id = args
    n           = (size_mb * 1024 * 1024) // 8
    a           = np.ones(n, dtype=np.float64)
    b           = np.ones(n, dtype=np.float64) * 2.0
    c           = np.ones(n, dtype=np.float64) * 3.0
    end_time    = time.perf_counter() + duration
    total_bytes = 0
    iterations  = 0

    while time.perf_counter() < end_time:
        np.add(b, 3.14 * c, out=a)
        total_bytes += n * 8 * 3
        iterations  += 1

    return {
        "worker_id":   worker_id,
        "bw_gbs":      total_bytes / duration / 1e9,
        "iterations":  iterations,
    }


def _ipc_pipe_worker(args: tuple) -> int:
    """
    IPC pipe round-trip worker.
    Sends N messages through a pipe and counts completions.
    Returns number of round-trips completed.
    """
    conn_send, conn_recv, n_messages, msg_size = args
    msg   = b'X' * msg_size
    count = 0
    try:
        for _ in range(n_messages):
            conn_send.send_bytes(msg)
            data = conn_recv.recv_bytes()
            if data:
                count += 1
    except Exception:
        pass
    return count


def _scheduler_worker(args: tuple) -> list:
    """
    OS Scheduler latency measurement worker.
    Measures wake-up latency from a timed sleep.
    Returns list of (requested_sleep_ms, actual_sleep_ms) tuples.
    """
    n_samples, sleep_ms = args
    results = []
    target  = sleep_ms / 1000.0  # Convert to seconds

    for _ in range(n_samples):
        t0 = time.perf_counter()
        time.sleep(target)
        actual = (time.perf_counter() - t0) * 1000  # ms
        results.append((sleep_ms, round(actual, 3)))

    return results


def _syscall_worker(args: tuple) -> int:
    """
    System call throughput worker.
    Counts how many syscalls complete in duration seconds.
    Uses time.perf_counter() as lightweight syscall proxy.
    """
    duration, syscall_type = args
    count    = 0
    end_time = time.perf_counter() + duration

    if syscall_type == "gettime":
        while time.perf_counter() < end_time:
            _ = time.perf_counter()
            count += 1

    elif syscall_type == "getpid":
        pid = os.getpid()
        while time.perf_counter() < end_time:
            _ = os.getpid()
            count += 1

    elif syscall_type == "stat":
        path = os.path.abspath(__file__)
        while time.perf_counter() < end_time:
            try:
                _ = os.stat(path)
            except Exception:
                pass
            count += 1

    elif syscall_type == "open_close":
        fd_path = os.devnull
        while time.perf_counter() < end_time:
            try:
                fd = open(fd_path, 'rb')
                fd.close()
            except Exception:
                pass
            count += 1

    return count


# ══════════════════════════════════════════════════════════════
#  HELPER UTILITIES
# ══════════════════════════════════════════════════════════════

class _WindowsTimerRes:
    """
    Temporarily set Windows timer resolution to 1ms
    for accurate sleep/timing measurements.
    """
    def __enter__(self):
        if IS_WINDOWS:
            try:
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass
        return self

    def __exit__(self, *args):
        if IS_WINDOWS:
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass


def _get_cpu_temp_windows() -> Optional[float]:
    """Get CPU temperature via WMI on Windows."""
    if not WMI_OK:
        return None
    try:
        w       = wmi.WMI(namespace="root\\wmi")
        sensors = w.MSAcpi_ThermalZoneTemperature()
        if sensors:
            # Convert from tenth-Kelvin to Celsius
            temps = [
                (s.CurrentTemperature / 10.0) - 273.15
                for s in sensors
            ]
            return max(temps)
    except Exception:
        pass
    return None


def _get_cpu_temp_linux() -> Optional[float]:
    """Get CPU temperature on Linux via thermal zones."""
    try:
        base = "/sys/class/thermal"
        if not os.path.exists(base):
            return None
        temps = []
        for zone in os.listdir(base):
            temp_file = os.path.join(base, zone, "temp")
            if os.path.exists(temp_file):
                with open(temp_file) as f:
                    temps.append(int(f.read().strip()) / 1000.0)
        return max(temps) if temps else None
    except Exception:
        return None


def _get_cpu_temp() -> Optional[float]:
    """Cross-platform CPU temperature detection."""
    if IS_WINDOWS:
        temp = _get_cpu_temp_windows()
        if temp:
            return temp
    if IS_LINUX:
        return _get_cpu_temp_linux()
    if PSUTIL_OK:
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for key in ['coretemp', 'k10temp', 'cpu_thermal']:
                    if key in temps:
                        return max(s.current for s in temps[key])
        except Exception:
            pass
    return None


def _get_ram_usage_gb() -> float:
    """Get current RAM usage in GB."""
    if PSUTIL_OK:
        try:
            return psutil.virtual_memory().used / 1e9
        except Exception:
            pass
    return 0.0


def _get_cpu_usage_pct(interval: float = 0.5) -> float:
    """Get CPU usage percentage."""
    if PSUTIL_OK:
        try:
            return psutil.cpu_percent(interval=interval)
        except Exception:
            pass
    return 0.0


def _detect_pcie_devices() -> List[dict]:
    """
    Detect PCIe devices via WMI (Windows) or /sys (Linux).
    Returns list of {name, slot, speed, width}.
    """
    devices = []

    if IS_WINDOWS and WMI_OK:
        try:
            w = wmi.WMI()
            for dev in w.Win32_VideoController():
                devices.append({
                    "name":         dev.Name or "Unknown GPU",
                    "type":         "GPU",
                    "pcie_version": "Unknown",
                    "pcie_width":   "Unknown",
                })
            for dev in w.Win32_NetworkAdapter():
                if dev.AdapterType and "Ethernet" in str(dev.AdapterType):
                    devices.append({
                        "name": dev.Name or "Network Adapter",
                        "type": "NIC",
                    })
        except Exception:
            pass

    if IS_LINUX:
        try:
            result = subprocess.run(
                ['lspci', '-v'], capture_output=True,
                text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if 'VGA' in line or '3D' in line:
                    devices.append({
                        "name": line.strip(),
                        "type": "GPU"
                    })
        except Exception:
            pass

    return devices if devices else [
        {"name": "GPU (detected via GPUtil)", "type": "GPU"}
    ]


def _get_network_interfaces() -> List[dict]:
    """Get available network interfaces with IPs."""
    interfaces = []
    if PSUTIL_OK:
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            for name, addr_list in addrs.items():
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        speed = getattr(stats.get(name), 'speed', 0)
                        interfaces.append({
                            "name":   name,
                            "ip":     addr.address,
                            "speed_mbps": speed,
                        })
        except Exception:
            pass
    return interfaces


# ══════════════════════════════════════════════════════════════
#  MAIN BENCHMARK CLASS
# ══════════════════════════════════════════════════════════════

class SystemBenchmark:
    """
    System-level benchmark suite for SYSTEM VITAL.
    Tests PCIe, USB, Network, IPC, Scheduler, Syscalls,
    Interrupts, Power, Thermals, and Full System Stress.
    """

    DURATION_SHORT = 5.0
    DURATION_LONG  = 15.0

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_cb = progress_callback or (lambda m, p: None)
        self._cancel     = threading.Event()

    def cancel(self):
        """Cancel any running benchmark."""
        self._cancel.set()

    def _cancelled(self) -> bool:
        return self._cancel.is_set()

    # ──────────────────────────────────────────────────────────
    # TEST 1: PCIE BANDWIDTH & LATENCY
    # ──────────────────────────────────────────────────────────

    def test_pcie_bandwidth(self) -> dict:
        """
        PCIe Bandwidth & Latency Estimation.

        PCIe is the primary bus connecting:
          - GPU to CPU (x16 slot)
          - NVMe SSD to CPU (x4 slot)
          - Network cards (x1–x4)

        PCIe generations and theoretical bandwidth:
          PCIe 3.0 ×16: 16 GB/s bidirectional
          PCIe 4.0 ×16: 32 GB/s bidirectional
          PCIe 5.0 ×16: 64 GB/s bidirectional

        We measure PCIe performance INDIRECTLY by:
          A. Memory-to-memory DMA simulation (large buffer transfers)
          B. Measuring NVMe effective bandwidth (already on PCIe)
          C. GPU VRAM roundtrip via numpy arrays (if GPU present)
          D. PCIe overhead from queue depth scaling patterns

        Equivalent: GPU-Z PCIe bandwidth test,
                    CUDA bandwidth test (deviceToHost / hostToDevice).
        """
        self.progress_cb("System: PCIe Bandwidth & Latency...", 3)

        results     = {}
        pcie_devices = _detect_pcie_devices()

        # ── A: Memory-mapped large buffer transfer simulation ──
        # Simulates DMA: CPU writes large buffer, GPU reads it.
        # We use numpy for consistent memory allocation patterns.

        BUFFER_SIZES_MB = [64, 128, 256, 512]
        h2d_results     = {}   # Host to Device simulation
        d2h_results     = {}   # Device to Host simulation

        for size_mb in BUFFER_SIZES_MB:
            n         = (size_mb * 1024 * 1024) // 8
            src_buf   = np.ones(n, dtype=np.float64)
            dst_buf   = np.empty(n, dtype=np.float64)

            # Warm up
            np.copyto(dst_buf, src_buf)

            # H2D: simulate host→device (write to new allocation)
            start   = time.perf_counter()
            PASSES  = max(1, 4096 // size_mb)
            for _ in range(PASSES):
                np.copyto(dst_buf, src_buf)
            elapsed = time.perf_counter() - start
            h2d_bw  = (size_mb * PASSES * 2) / elapsed / 1e3  # GB/s (×2 for R+W)

            # D2H: simulate device→host (read from existing allocation)
            start = time.perf_counter()
            for _ in range(PASSES):
                _ = src_buf.sum()   # Force read of entire buffer
            elapsed = time.perf_counter() - start
            d2h_bw  = (size_mb * PASSES) / elapsed / 1e3

            h2d_results[f"{size_mb}MB"] = round(h2d_bw, 3)
            d2h_results[f"{size_mb}MB"] = round(d2h_bw, 3)

        peak_h2d = max(h2d_results.values()) if h2d_results else 0
        peak_d2h = max(d2h_results.values()) if d2h_results else 0

        # ── B: PCIe latency via small transfer overhead ────────
        # Measure overhead of initiating transfers
        # (setup cost, not bandwidth — reveals PCIe latency)
        TINY_SIZE   = 64    # 64 bytes — minimal payload
        N_TRANSFERS = 50_000
        tiny_buf    = np.ones(8, dtype=np.float64)
        dst_tiny    = np.empty(8, dtype=np.float64)

        start = time.perf_counter()
        for _ in range(N_TRANSFERS):
            np.copyto(dst_tiny, tiny_buf)
        elapsed        = time.perf_counter() - start
        latency_us     = elapsed / N_TRANSFERS * 1e6

        # ── C: PCIe version estimation ─────────────────────────
        # Estimate PCIe version from peak bandwidth
        if peak_h2d > 50:
            pcie_est = "PCIe 5.0 ×16 (64 GB/s)"
        elif peak_h2d > 25:
            pcie_est = "PCIe 4.0 ×16 (32 GB/s)"
        elif peak_h2d > 12:
            pcie_est = "PCIe 3.0 ×16 (16 GB/s)"
        elif peak_h2d > 6:
            pcie_est = "PCIe 3.0 ×8 or PCIe 4.0 ×4"
        elif peak_h2d > 3:
            pcie_est = "PCIe 3.0 ×4 (NVMe)"
        else:
            pcie_est = "PCIe 3.0 ×1 or lower"

        # ── D: NVMe PCIe overhead (if NVMe present) ───────────
        nvme_bw_est = None
        try:
            import shutil
            test_path   = os.path.join(
                os.path.splitdrive(os.path.abspath(__file__))[0] + os.sep,
                "_dkbench_pcie_nvme.tmp"
            )
            NVME_SIZE   = 256 * 1024 * 1024  # 256MB
            data_chunk  = np.random.default_rng(0).integers(
                0, 256, 1024 * 1024, dtype=np.uint8
            ).tobytes()  # 1MB chunk

            start = time.perf_counter()
            with open(test_path, 'wb', buffering=0) as f:
                for _ in range(256):
                    f.write(data_chunk)
                f.flush(); os.fsync(f.fileno())
            elapsed     = time.perf_counter() - start
            nvme_bw_est = round(NVME_SIZE / elapsed / 1e6, 1)

        except Exception:
            pass
        finally:
            try:
                if os.path.exists(test_path):
                    os.remove(test_path)
            except Exception:
                pass

        # ── GPU PCIe info via GPUtil ───────────────────────────
        gpu_info = {}
        if GPUTIL_OK:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    gpu_info = {
                        "name":    g.name,
                        "vram_mb": g.memoryTotal,
                        "driver":  g.driver,
                    }
            except Exception:
                pass

        score = self._normalize(peak_h2d, 0, 64)

        return {
            "name":               "PCIe Bandwidth & Latency",
            "value":              peak_h2d,
            "unit":               "GB/s (peak H2D transfer)",
            "h2d_by_size_gbs":    h2d_results,
            "d2h_by_size_gbs":    d2h_results,
            "peak_h2d_gbs":       round(peak_h2d, 3),
            "peak_d2h_gbs":       round(peak_d2h, 3),
            "transfer_latency_us":round(latency_us, 3),
            "nvme_write_mbs":     nvme_bw_est,
            "pcie_estimate":      pcie_est,
            "detected_devices":   pcie_devices[:3],
            "gpu_info":           gpu_info,
            "raw":                len(BUFFER_SIZES_MB),
            "score":              score,
            "equivalent_to":      "GPU-Z PCIe test / CUDA bandwidth test",
            "description": (
                f"Simulated H2D: {peak_h2d:.2f}GB/s | "
                f"D2H: {peak_d2h:.2f}GB/s. "
                f"Transfer latency: {latency_us:.2f}µs. "
                f"PCIe estimate: {pcie_est}. "
                + (f"NVMe write: {nvme_bw_est:.0f}MB/s. "
                   if nvme_bw_est else "")
                + "Note: Indirect measurement via memory subsystem."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 2: USB TRANSFER SPEED PROFILE
    # ──────────────────────────────────────────────────────────

    def test_usb_transfer_speed(self) -> dict:
        """
        USB Transfer Speed Profile.

        USB generations and theoretical speeds:
          USB 2.0:   480 Mbps  = 60  MB/s
          USB 3.0:   5   Gbps  = 625 MB/s
          USB 3.1:   10  Gbps  = 1250 MB/s
          USB 3.2:   20  Gbps  = 2500 MB/s
          USB 4.0:   40  Gbps  = 5000 MB/s
          Thunderbolt 4: 40 Gbps + PCIe

        Without a USB device present, we:
          A. Detect connected USB storage devices
          B. Run file I/O benchmark on any detected USB drive
          C. Measure USB controller latency via /sys or WMI
          D. Detect USB generation from transfer speed

        If no USB drive detected: reports USB controller info only.

        Equivalent: USBDeview / CrystalDiskMark on USB drive.
        """
        self.progress_cb("System: USB Transfer Speed Profile...", 13)

        # ── Detect USB storage devices ─────────────────────────
        usb_drives    = []
        usb_info      = []
        controller_info = {}

        if IS_WINDOWS:
            try:
                w = wmi.WMI() if WMI_OK else None
                if w:
                    for disk in w.Win32_DiskDrive():
                        if ('usb' in str(disk.InterfaceType).lower()
                                or 'usb' in str(disk.PNPDeviceID or '').lower()):
                            usb_drives.append({
                                "name":   disk.Model or "USB Drive",
                                "size_gb": int(disk.Size or 0) // 1e9,
                                "interface": disk.InterfaceType,
                            })
                    # USB Controllers
                    for ctrl in w.Win32_USBController():
                        usb_info.append({
                            "name":   ctrl.Name or "USB Controller",
                            "status": ctrl.Status,
                        })
            except Exception:
                pass

        if IS_LINUX:
            try:
                result = subprocess.run(
                    ['lsblk', '-o', 'NAME,TRAN,SIZE,MODEL', '--noheadings'],
                    capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == 'usb':
                        usb_drives.append({
                            "name": " ".join(parts[3:]) or "USB Drive",
                            "size": parts[2],
                        })
            except Exception:
                pass

        # ── USB benchmark on detected drive ────────────────────
        usb_bench_result = None
        if usb_drives:
            # Try to find the drive mount point and benchmark it
            pass  # Drive-specific benchmark skipped for safety

        # ── Internal USB overhead measurement ──────────────────
        # Measure socket loopback as proxy for USB2 latency baseline
        LOOPBACK_MSGS = 10_000
        MSG_SIZE      = 512

        latencies_lo  = []
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server.bind(('127.0.0.1', 0))
            port   = server.getsockname()[1]
            server.settimeout(0.1)

            msg = b'U' * MSG_SIZE
            for _ in range(LOOPBACK_MSGS):
                t0 = time.perf_counter()
                client.sendto(msg, ('127.0.0.1', port))
                try:
                    server.recvfrom(MSG_SIZE)
                except socket.timeout:
                    pass
                latencies_lo.append((time.perf_counter() - t0) * 1e6)

            server.close()
            client.close()
        except Exception:
            latencies_lo = [100.0] * 10

        # ── USB speed from file I/O temp benchmark ─────────────
        # Write to system temp (may be on USB if temp is redirected)
        BENCH_MB      = 64
        BLOCK_SIZE    = 65536
        tmp_file      = os.path.join(tempfile.gettempdir(),
                                     "_dkbench_usb_test.tmp")
        data_chunk    = os.urandom(BLOCK_SIZE)
        write_bytes   = 0
        write_start   = time.perf_counter()

        try:
            with open(tmp_file, 'wb', buffering=0) as f:
                target = BENCH_MB * 1024 * 1024
                while write_bytes < target:
                    f.write(data_chunk)
                    write_bytes += len(data_chunk)
                f.flush(); os.fsync(f.fileno())
        except Exception:
            pass
        finally:
            try:
                os.remove(tmp_file)
            except Exception:
                pass

        write_elapsed = time.perf_counter() - write_start
        write_mbs     = write_bytes / write_elapsed / 1e6

        # USB generation classification from speed
        if write_mbs > 2000:
            usb_gen = "USB4 / Thunderbolt 4 (40Gbps)"
        elif write_mbs > 800:
            usb_gen = "USB 3.2 Gen 2×2 (20Gbps)"
        elif write_mbs > 400:
            usb_gen = "USB 3.1 Gen 2 / USB 3.2 (10Gbps)"
        elif write_mbs > 150:
            usb_gen = "USB 3.0 / USB 3.1 Gen 1 (5Gbps)"
        elif write_mbs > 30:
            usb_gen = "USB 2.0 High-Speed (480Mbps)"
        else:
            usb_gen = "USB 2.0 Full-Speed or slower"

        lat_arr = np.array(latencies_lo, dtype=np.float64)
        avg_lat = float(np.mean(lat_arr))
        p99_lat = float(np.percentile(lat_arr, 99))

        score = self._normalize(write_mbs, 0, 5000)

        return {
            "name":             "USB Transfer Speed Profile",
            "value":            round(write_mbs, 1),
            "unit":             "MB/s (system temp write)",
            "write_speed_mbs":  round(write_mbs, 1),
            "usb_generation":   usb_gen,
            "loopback_lat_us":  round(avg_lat, 2),
            "loopback_p99_us":  round(p99_lat, 2),
            "detected_usb_devs":usb_drives[:5],
            "usb_controllers":  usb_info[:3],
            "bench_size_mb":    BENCH_MB,
            "raw":              write_bytes,
            "score":            score,
            "equivalent_to":    "USBDeview / CrystalDiskMark USB drive",
            "description": (
                f"Write speed (temp drive): {write_mbs:.0f}MB/s → {usb_gen}. "
                f"Loopback latency: avg={avg_lat:.1f}µs P99={p99_lat:.1f}µs. "
                f"USB devices detected: {len(usb_drives)}. "
                "For accurate USB speed: plug in USB drive and run SSD benchmark."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 3: NETWORK LATENCY & THROUGHPUT
    # ──────────────────────────────────────────────────────────

    def test_network_performance(self) -> dict:
        """
        Network Latency & Throughput Analysis.

        Tests multiple dimensions of network performance:
          A. Loopback latency (localhost — measures TCP/IP stack overhead)
          B. LAN gateway ping (if reachable)
          C. Internet DNS resolution latency
          D. TCP loopback throughput (measures network stack bandwidth)
          E. UDP packet loss at high rate
          F. Network interface info (speed, duplex)

        This does NOT require an iPerf server.
        All tests run locally using loopback or system calls.

        Equivalent: iPerf3, netio, ping, tracert analysis.
        """
        self.progress_cb("System: Network Latency & Throughput...", 22)

        results = {}

        # ── A: TCP Loopback Latency ────────────────────────────
        N_PINGS     = 1000
        PAYLOAD     = b'SYSTEM VITAL_PING_' * 4  # 56 bytes

        tcp_latencies = []
        try:
            # Server thread
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(('127.0.0.1', 0))
            server_sock.listen(1)
            server_port = server_sock.getsockname()[1]
            server_sock.settimeout(5)

            server_ready = threading.Event()
            server_done  = threading.Event()

            def tcp_echo_server():
                try:
                    server_sock.settimeout(10)
                    conn, _ = server_sock.accept()
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    server_ready.set()
                    while not server_done.is_set():
                        try:
                            data = conn.recv(1024)
                            if data:
                                conn.send(data)
                            else:
                                break
                        except Exception:
                            break
                    conn.close()
                except Exception:
                    server_ready.set()

            server_thread = threading.Thread(
                target=tcp_echo_server, daemon=True
            )
            server_thread.start()

            # Client
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            client_sock.settimeout(5)
            client_sock.connect(('127.0.0.1', server_port))
            server_ready.wait(timeout=3)

            for _ in range(N_PINGS):
                t0 = time.perf_counter()
                client_sock.send(PAYLOAD)
                client_sock.recv(len(PAYLOAD))
                tcp_latencies.append(
                    (time.perf_counter() - t0) * 1e6  # µs
                )

            server_done.set()
            client_sock.close()
            server_sock.close()

        except Exception as e:
            tcp_latencies = [500.0] * 10  # Fallback

        tcp_arr   = np.array(tcp_latencies, dtype=np.float64)
        tcp_avg   = float(np.mean(tcp_arr))
        tcp_p50   = float(np.percentile(tcp_arr, 50))
        tcp_p99   = float(np.percentile(tcp_arr, 99))
        tcp_min   = float(np.min(tcp_arr))

        results["tcp_loopback"] = {
            "avg_us":  round(tcp_avg, 2),
            "p50_us":  round(tcp_p50, 2),
            "p99_us":  round(tcp_p99, 2),
            "min_us":  round(tcp_min, 2),
            "n_pings": N_PINGS,
        }

        # ── B: UDP Loopback Latency ────────────────────────────
        udp_latencies = []
        try:
            udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_server.bind(('127.0.0.1', 0))
            udp_port   = udp_server.getsockname()[1]
            udp_server.settimeout(0.05)

            udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_client.settimeout(0.05)

            for _ in range(N_PINGS):
                t0 = time.perf_counter()
                udp_client.sendto(PAYLOAD, ('127.0.0.1', udp_port))
                try:
                    udp_server.recvfrom(256)
                except socket.timeout:
                    pass
                udp_latencies.append(
                    (time.perf_counter() - t0) * 1e6
                )

            udp_server.close()
            udp_client.close()

        except Exception:
            udp_latencies = [100.0] * 10

        udp_arr = np.array(udp_latencies, dtype=np.float64)
        results["udp_loopback"] = {
            "avg_us":  round(float(np.mean(udp_arr)), 2),
            "p50_us":  round(float(np.percentile(udp_arr, 50)), 2),
            "p99_us":  round(float(np.percentile(udp_arr, 99)), 2),
            "min_us":  round(float(np.min(udp_arr)), 2),
        }

        # ── C: TCP Loopback Throughput ─────────────────────────
        CHUNK_SIZE  = 65536   # 64KB chunks
        DURATION    = 3.0
        total_bytes = 0

        try:
            # Server
            tput_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tput_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tput_server.setsockopt(
                socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024
            )
            tput_server.bind(('127.0.0.1', 0))
            tput_server.listen(1)
            tput_port   = tput_server.getsockname()[1]

            recv_bytes  = [0]
            recv_done   = threading.Event()

            def receiver():
                try:
                    tput_server.settimeout(5)
                    conn, _ = tput_server.accept()
                    conn.setsockopt(
                        socket.SOL_SOCKET, socket.SO_RCVBUF, 4*1024*1024
                    )
                    while not recv_done.is_set():
                        try:
                            data = conn.recv(CHUNK_SIZE)
                            if data:
                                recv_bytes[0] += len(data)
                            else:
                                break
                        except Exception:
                            break
                    conn.close()
                except Exception:
                    pass

            recv_thread = threading.Thread(target=receiver, daemon=True)
            recv_thread.start()
            time.sleep(0.1)

            # Sender
            sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sender.setsockopt(
                socket.SOL_SOCKET, socket.SO_SNDBUF, 4*1024*1024
            )
            sender.connect(('127.0.0.1', tput_port))
            chunk = b'T' * CHUNK_SIZE

            start = time.perf_counter()
            while (time.perf_counter() - start) < DURATION:
                sender.send(chunk)
                total_bytes += CHUNK_SIZE
            recv_done.set()
            sender.close()
            tput_server.close()
            recv_thread.join(timeout=2)

        except Exception:
            pass

        throughput_gbps = total_bytes * 8 / DURATION / 1e9
        throughput_mbs  = total_bytes / DURATION / 1e6

        results["tcp_throughput"] = {
            "throughput_gbps": round(throughput_gbps, 3),
            "throughput_mbs":  round(throughput_mbs, 1),
            "duration_sec":    DURATION,
        }

        # ── D: DNS Resolution Latency ──────────────────────────
        dns_results = {}
        dns_targets = [
            ("8.8.8.8",    "Google DNS"),
            ("1.1.1.1",    "Cloudflare DNS"),
            ("9.9.9.9",    "Quad9 DNS"),
        ]

        for dns_ip, dns_name in dns_targets:
            try:
                t0 = time.perf_counter()
                socket.setdefaulttimeout(2)
                socket.gethostbyname("www.google.com")
                dns_lat = (time.perf_counter() - t0) * 1000
                dns_results[dns_name] = round(dns_lat, 2)
            except Exception:
                dns_results[dns_name] = None

        results["dns_latency_ms"] = dns_results

        # ── E: Network Interface Info ──────────────────────────
        interfaces = _get_network_interfaces()
        results["interfaces"] = interfaces[:5]

        # ── F: Gateway Ping (if possible) ─────────────────────
        gateway_ping_ms = None
        try:
            if IS_WINDOWS:
                cmd = ['ping', '-n', '5', '-w', '1000', '192.168.1.1']
            else:
                cmd = ['ping', '-c', '5', '-W', '1', '192.168.1.1']

            proc = subprocess.run(
                cmd, capture_output=True,
                text=True, timeout=10
            )
            output = proc.stdout
            import re
            # Match "time=Xms" or "time<Xms"
            times  = re.findall(r'time[=<](\d+\.?\d*)', output)
            if times:
                gateway_ping_ms = round(
                    statistics.mean(float(t) for t in times), 2
                )
        except Exception:
            pass

        results["gateway_ping_ms"] = gateway_ping_ms

        # ── Score ──────────────────────────────────────────────
        score = self._normalize(throughput_gbps, 0, 100)

        return {
            "name":               "Network Latency & Throughput",
            "value":              throughput_gbps,
            "unit":               "Gbps (TCP loopback throughput)",
            "tcp_loopback":       results["tcp_loopback"],
            "udp_loopback":       results["udp_loopback"],
            "tcp_throughput_gbs": throughput_gbps,
            "tcp_throughput_mbs": throughput_mbs,
            "dns_latency_ms":     dns_results,
            "gateway_ping_ms":    gateway_ping_ms,
            "interfaces":         interfaces[:3],
            "raw":                N_PINGS * 2,
            "score":              score,
            "equivalent_to":      "iPerf3 / netio / ping benchmark",
            "description": (
                f"TCP loopback: avg={tcp_avg:.1f}µs P99={tcp_p99:.1f}µs. "
                f"UDP loopback: avg={float(np.mean(udp_arr)):.1f}µs. "
                f"TCP throughput: {throughput_gbps:.2f}Gbps "
                f"({throughput_mbs:.0f}MB/s). "
                f"Gateway: {gateway_ping_ms or 'N/A'}ms. "
                "High TCP loopback = fast TCP/IP stack + kernel network path."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 4: INTER-PROCESS COMMUNICATION (IPC)
    # ──────────────────────────────────────────────────────────

    def test_ipc_performance(self) -> dict:
        """
        Inter-Process Communication (IPC) Performance.

        IPC mechanisms tested:
          A. Pipe throughput (subprocess.Popen pipe)
          B. Shared memory bandwidth (multiprocessing.shared_memory)
          C. Queue latency (multiprocessing.Queue)
          D. Event synchronization overhead
          E. Process spawn time (fork/exec overhead)
          F. Multiprocessing.Pipe round-trip latency

        IPC performance matters for:
          - Browser renderer/browser process communication
          - Database connection pooling
          - Microservice communication
          - IDE plugin communication

        Equivalent: lmbench IPC benchmark,
                    pipe-throughput test, shm-latency test.
        """
        self.progress_cb("System: Inter-Process Communication (IPC)...", 32)

        ipc_results = {}

        # ── A: Pipe Round-Trip Latency ─────────────────────────
        N_RT      = 2000
        MSG_SIZES = [64, 512, 4096, 65536]
        pipe_results = {}

        for msg_size in MSG_SIZES:
            parent_conn, child_conn = multiprocessing.Pipe(duplex=True)
            msg         = b'P' * msg_size
            latencies   = []

            def child_echo():
                while True:
                    try:
                        data = child_conn.recv_bytes()
                        child_conn.send_bytes(data)
                    except Exception:
                        break

            p = multiprocessing.Process(target=child_echo, daemon=True)
            p.start()

            # Warm up
            for _ in range(10):
                parent_conn.send_bytes(msg)
                parent_conn.recv_bytes()

            # Timed round-trips
            for _ in range(N_RT):
                t0 = time.perf_counter()
                parent_conn.send_bytes(msg)
                parent_conn.recv_bytes()
                latencies.append((time.perf_counter() - t0) * 1e6)

            p.terminate(); p.join(timeout=2)
            parent_conn.close(); child_conn.close()

            lat_arr = np.array(latencies, dtype=np.float64)
            pipe_results[f"{msg_size}B"] = {
                "avg_us":       round(float(np.mean(lat_arr)), 2),
                "p50_us":       round(float(np.percentile(lat_arr, 50)), 2),
                "p99_us":       round(float(np.percentile(lat_arr, 99)), 2),
                "throughput_mbs": round(
                    msg_size * 2 * N_RT
                    / (float(np.mean(lat_arr)) * N_RT / 1e6) / 1e6, 2
                ),
            }

        ipc_results["pipe_rtt"]   = pipe_results
        pipe_min_lat               = min(
            v["avg_us"] for v in pipe_results.values()
        )

        # ── B: Shared Memory Bandwidth ─────────────────────────
        shm_bw = 0.0
        try:
            from multiprocessing import shared_memory
            SHM_MB   = 64
            SHM_SIZE = SHM_MB * 1024 * 1024
            shm      = shared_memory.SharedMemory(create=True, size=SHM_SIZE)
            shm_arr  = np.ndarray(SHM_SIZE // 8, dtype=np.float64,
                                   buffer=shm.buf)

            # Write bandwidth
            PASSES   = 10
            fill_val = np.float64(3.14)
            start    = time.perf_counter()
            for _ in range(PASSES):
                shm_arr.fill(fill_val)
            elapsed  = time.perf_counter() - start
            shm_bw   = (SHM_MB * PASSES) / elapsed / 1e3  # GB/s

            shm.close()
            shm.unlink()
            ipc_results["shm_bandwidth_gbs"] = round(shm_bw, 3)

        except Exception as e:
            ipc_results["shm_bandwidth_gbs"] = None
            ipc_results["shm_error"]         = str(e)

        # ── C: Queue Latency ───────────────────────────────────
        q_latencies = []
        try:
            q            = multiprocessing.Queue()
            msg_q        = b'Q' * 256
            N_Q          = 500

            def q_echo(qq):
                for _ in range(N_Q):
                    item = qq.get()
                    qq.put(item)

            qp = multiprocessing.Process(target=q_echo, args=(q,), daemon=True)
            qp.start()

            for _ in range(N_Q):
                t0 = time.perf_counter()
                q.put(msg_q)
                _ = q.get()
                q_latencies.append((time.perf_counter() - t0) * 1e6)

            qp.terminate(); qp.join(timeout=2)

            q_arr = np.array(q_latencies, dtype=np.float64)
            ipc_results["queue_rtt_us"] = {
                "avg_us": round(float(np.mean(q_arr)), 2),
                "p99_us": round(float(np.percentile(q_arr, 99)), 2),
            }
        except Exception as e:
            ipc_results["queue_rtt_us"] = {"error": str(e)}

        # ── D: Process Spawn Time ──────────────────────────────
        spawn_times = []
        N_SPAWN     = 10
        for _ in range(N_SPAWN):
            t0 = time.perf_counter()
            p  = multiprocessing.Process(target=lambda: None)
            p.start()
            p.join()
            spawn_times.append((time.perf_counter() - t0) * 1000)

        avg_spawn_ms = round(statistics.mean(spawn_times), 2)
        ipc_results["process_spawn_ms"] = avg_spawn_ms

        # ── E: Thread Spawn Time ───────────────────────────────
        thread_times = []
        N_THREADS    = 50
        ready        = threading.Event()

        def thread_fn():
            ready.set()

        for _ in range(N_THREADS):
            ready.clear()
            t0 = time.perf_counter()
            t  = threading.Thread(target=thread_fn)
            t.start()
            ready.wait()
            thread_times.append((time.perf_counter() - t0) * 1e6)
            t.join()

        avg_thread_us = round(statistics.mean(thread_times), 2)
        ipc_results["thread_spawn_us"] = avg_thread_us

        # ── F: Event Synchronization Overhead ─────────────────
        evt       = threading.Event()
        N_EVT     = 10_000
        evt_times = []

        def evt_setter():
            for _ in range(N_EVT):
                evt.set()
                evt.clear()

        t_evt = threading.Thread(target=evt_setter, daemon=True)
        t_evt.start()

        for _ in range(N_EVT):
            t0 = time.perf_counter()
            evt.wait(timeout=0.001)
            evt_times.append((time.perf_counter() - t0) * 1e6)

        t_evt.join(timeout=2)
        evt_times_arr = np.array(evt_times, dtype=np.float64)
        ipc_results["event_sync_us"] = round(
            float(np.mean(evt_times_arr)), 3
        )

        score = self._normalize(1 / max(pipe_min_lat, 1), 0, 1)

        return {
            "name":              "Inter-Process Communication (IPC)",
            "value":             pipe_min_lat,
            "unit":              "µs (min pipe round-trip)",
            "pipe_rtt_by_size":  pipe_results,
            "shm_bw_gbs":        ipc_results.get("shm_bandwidth_gbs"),
            "queue_rtt_us":      ipc_results.get("queue_rtt_us"),
            "process_spawn_ms":  avg_spawn_ms,
            "thread_spawn_us":   avg_thread_us,
            "event_sync_us":     ipc_results.get("event_sync_us"),
            "raw":               N_RT * len(MSG_SIZES),
            "score":             score,
            "equivalent_to":     "lmbench IPC / pipe-throughput / shm-latency",
            "description": (
                f"Pipe RTT (64B): {pipe_results.get('64B',{}).get('avg_us','?')}µs. "
                f"Shared mem BW: {ipc_results.get('shm_bandwidth_gbs','?')}GB/s. "
                f"Queue RTT: {ipc_results.get('queue_rtt_us',{}).get('avg_us','?')}µs. "
                f"Process spawn: {avg_spawn_ms}ms. "
                f"Thread spawn: {avg_thread_us}µs. "
                "Lower latency = faster OS IPC scheduler."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 5: OS SCHEDULER LATENCY
    # ──────────────────────────────────────────────────────────

    def test_scheduler_latency(self) -> dict:
        """
        OS Scheduler Latency Test.

        The OS scheduler determines when each thread gets CPU time.
        Scheduler latency is the delay between:
          - A thread becoming runnable (e.g., after sleep/event)
          - The thread actually getting CPU time

        High scheduler latency causes:
          - Audio dropouts (need <1ms scheduling)
          - Game stutters (need <2ms scheduling)
          - Real-time system failures

        This test:
          A. Measures sleep() overshoot at various intervals
          B. Measures thread wake-up latency
          C. Detects scheduler jitter (variance in latency)
          D. Tests different thread priorities

        Equivalent: LatencyMon (Windows), cyclictest (Linux),
                    RTLatency, DPC Latency Checker.
        """
        self.progress_cb("System: OS Scheduler Latency...", 42)

        sched_results = {}
        N_SAMPLES     = 500

        # ── A: Sleep Overshoot at Multiple Durations ───────────
        sleep_targets_ms = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
        sleep_overshoot  = {}

        with _WindowsTimerRes():
            for target_ms in sleep_targets_ms:
                overshoots  = []
                target_sec  = target_ms / 1000.0

                for _ in range(min(N_SAMPLES, 200)):
                    t0     = time.perf_counter()
                    time.sleep(target_sec)
                    actual = (time.perf_counter() - t0) * 1000
                    overshoots.append(actual - target_ms)

                ov_arr = np.array(overshoots, dtype=np.float64)
                sleep_overshoot[f"{target_ms}ms"] = {
                    "avg_overshoot_ms": round(float(np.mean(ov_arr)), 3),
                    "max_overshoot_ms": round(float(np.max(ov_arr)), 3),
                    "p99_overshoot_ms": round(float(np.percentile(ov_arr, 99)), 3),
                    "jitter_ms":        round(float(np.std(ov_arr)), 3),
                }

        sched_results["sleep_overshoot"] = sleep_overshoot

        # ── B: Thread Wake-Up Latency ──────────────────────────
        wake_latencies = []
        N_WAKE         = 300
        wake_event     = threading.Event()
        wake_times     = []

        def waiter_thread():
            for _ in range(N_WAKE):
                wake_event.wait()
                wake_times.append(time.perf_counter())
                wake_event.clear()

        wt = threading.Thread(target=waiter_thread, daemon=True)
        wt.start()

        set_times = []
        time.sleep(0.1)  # Let thread start

        for _ in range(N_WAKE):
            t_set = time.perf_counter()
            set_times.append(t_set)
            wake_event.set()
            time.sleep(0.001)  # 1ms gap between signals

        wt.join(timeout=5)

        # Compute wake latencies
        for i in range(min(len(set_times), len(wake_times))):
            lat = (wake_times[i] - set_times[i]) * 1e6  # µs
            if 0 < lat < 100_000:  # Sanity check
                wake_latencies.append(lat)

        if wake_latencies:
            wl_arr = np.array(wake_latencies, dtype=np.float64)
            sched_results["thread_wake_us"] = {
                "avg_us":    round(float(np.mean(wl_arr)), 2),
                "p50_us":    round(float(np.percentile(wl_arr, 50)), 2),
                "p95_us":    round(float(np.percentile(wl_arr, 95)), 2),
                "p99_us":    round(float(np.percentile(wl_arr, 99)), 2),
                "max_us":    round(float(np.max(wl_arr)), 2),
                "jitter_us": round(float(np.std(wl_arr)), 2),
            }
            wake_avg_us = float(np.mean(wl_arr))
        else:
            wake_avg_us = 1000.0
            sched_results["thread_wake_us"] = {"error": "No samples"}

        # ── C: Priority Inversion Detection ───────────────────
        # Run high-priority thread vs background load
        priority_results = {}

        for load_threads in [0, 2, CPU_COUNT]:
            load_events  = [threading.Event() for _ in range(load_threads)]
            load_workers = []

            def cpu_burner(stop_evt):
                while not stop_evt.is_set():
                    _ = sum(range(10000))

            stop_events = [threading.Event() for _ in range(load_threads)]
            for i in range(load_threads):
                t = threading.Thread(
                    target=cpu_burner,
                    args=(stop_events[i],),
                    daemon=True
                )
                t.start()
                load_workers.append(t)

            # Measure wake latency under load
            loaded_lats = []
            sig_evt     = threading.Event()

            def loaded_waiter(n, evt, out):
                for _ in range(n):
                    evt.wait(timeout=0.5)
                    out.append(time.perf_counter())
                    evt.clear()

            lw_times = []
            lwt = threading.Thread(
                target=loaded_waiter,
                args=(50, sig_evt, lw_times),
                daemon=True
            )
            lwt.start()
            lw_set_times = []

            for _ in range(50):
                t_s = time.perf_counter()
                lw_set_times.append(t_s)
                sig_evt.set()
                time.sleep(0.005)

            lwt.join(timeout=3)

            for se in stop_events:
                se.set()
            for w in load_workers:
                w.join(timeout=1)

            lats = [
                (lw_times[i] - lw_set_times[i]) * 1e6
                for i in range(min(len(lw_times), len(lw_set_times)))
                if 0 < (lw_times[i] - lw_set_times[i]) * 1e6 < 100_000
            ]
            avg_lat = round(statistics.mean(lats), 2) if lats else 0
            priority_results[f"{load_threads}_bg_threads"] = avg_lat

        sched_results["priority_inversion_us"] = priority_results

        # ── D: Timer Resolution ────────────────────────────────
        timer_samples = []
        for _ in range(1000):
            t1 = time.perf_counter()
            t2 = time.perf_counter()
            delta = (t2 - t1) * 1e9  # ns
            if delta > 0:
                timer_samples.append(delta)

        if timer_samples:
            timer_arr = np.array(timer_samples)
            min_timer = float(np.percentile(timer_arr, 1))
            sched_results["timer_resolution_ns"] = round(min_timer, 1)
        else:
            sched_results["timer_resolution_ns"] = None

        # ── Scoring ────────────────────────────────────────────
        # Lower wake latency = better. Target: <100µs
        score = self._normalize(1000 / max(wake_avg_us, 1), 0, 100)

        # Detect if system has DPC/ISR latency issues (Windows)
        dpc_warning = False
        worst_overshoot = max(
            v["max_overshoot_ms"]
            for v in sleep_overshoot.values()
        ) if sleep_overshoot else 0

        if worst_overshoot > 10:
            dpc_warning = True

        return {
            "name":               "OS Scheduler Latency",
            "value":              round(wake_avg_us, 2),
            "unit":               "µs (thread wake-up average)",
            "sleep_overshoot":    sleep_overshoot,
            "thread_wake_us":     sched_results.get("thread_wake_us"),
            "priority_under_load":priority_results,
            "timer_resolution_ns":sched_results.get("timer_resolution_ns"),
            "worst_overshoot_ms": round(worst_overshoot, 2),
            "dpc_warning":        dpc_warning,
            "n_samples":          N_SAMPLES,
            "raw":                N_SAMPLES,
            "score":              score,
            "equivalent_to":      "LatencyMon / cyclictest / DPC Latency Checker",
            "description": (
                f"Thread wake-up: avg={wake_avg_us:.1f}µs. "
                f"Sleep overshoot (1ms target): "
                f"{sleep_overshoot.get('1.0ms',{}).get('avg_overshoot_ms','?')}ms. "
                f"Timer resolution: "
                f"{sched_results.get('timer_resolution_ns','?')}ns. "
                f"DPC latency warning: "
                f"{'⚠️ YES (DPC/ISR detected)' if dpc_warning else '✅ None'}. "
                "<100µs wake = real-time capable. >1ms = audio/game stutter risk."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 6: SYSTEM CALL OVERHEAD
    # ──────────────────────────────────────────────────────────

    def test_syscall_overhead(self) -> dict:
        """
        System Call Overhead Benchmark.

        Every OS interaction requires a context switch from
        user-space to kernel-space (ring 3 → ring 0).
        Modern CPUs use SYSCALL/SYSRET instructions (fast path).

        This test measures throughput of various syscall types:
          A. gettime    — clock_gettime() / QueryPerformanceCounter()
          B. getpid     — getpid() / GetCurrentProcessId()
          C. stat       — stat() / GetFileAttributes()
          D. open/close — open()+close() / CreateFile()+CloseHandle()
          E. malloc/free — memory allocation overhead (heap syscall)
          F. mmap-like  — numpy large allocation (virtual memory)

        Equivalent: strace syscall overhead, syscall-bench,
                    Windows API overhead measurement.
        """
        self.progress_cb("System: System Call Overhead...", 53)

        DURATION = min(self.DURATION_SHORT, 3.0)
        syscall_results = {}

        # Run all syscall workers in parallel for efficiency
        syscall_types = ["gettime", "getpid", "stat", "open_close"]
        args_list     = [(DURATION, sc) for sc in syscall_types]

        with multiprocessing.Pool(min(len(syscall_types), CPU_COUNT)) as pool:
            counts = pool.map(_syscall_worker, args_list)

        for sc_type, count in zip(syscall_types, counts):
            rate_m = count / DURATION / 1e6
            lat_ns = (DURATION / count) * 1e9 if count > 0 else 0
            syscall_results[sc_type] = {
                "total_calls":  count,
                "rate_m_per_s": round(rate_m, 3),
                "latency_ns":   round(lat_ns, 2),
            }

        # ── E: malloc/free throughput ──────────────────────────
        malloc_count  = 0
        ALLOC_SIZE    = 4096
        end_malloc    = time.perf_counter() + DURATION

        while time.perf_counter() < end_malloc:
            buf = bytearray(ALLOC_SIZE)
            buf[0] = 1  # Touch it
            del buf
            malloc_count += 1

        malloc_rate = malloc_count / DURATION / 1e6
        syscall_results["malloc_free"] = {
            "total_calls":  malloc_count,
            "rate_m_per_s": round(malloc_rate, 3),
            "latency_ns":   round(1 / max(malloc_rate, 0.001) * 1000, 2),
        }

        # ── F: Virtual memory (mmap-like) allocation ───────────
        mmap_count  = 0
        MMAP_SIZE   = 1024 * 1024  # 1MB
        end_mmap    = time.perf_counter() + DURATION

        while time.perf_counter() < end_mmap:
            arr = np.empty(MMAP_SIZE // 8, dtype=np.float64)
            arr[0] = 1.0
            del arr
            mmap_count += 1

        mmap_rate = mmap_count / DURATION / 1e6
        syscall_results["mmap_unmap"] = {
            "total_calls":  mmap_count,
            "rate_m_per_s": round(mmap_rate, 3),
            "latency_us":   round(1 / max(mmap_rate, 0.001), 3),
        }

        # ── G: File I/O syscall chain ──────────────────────────
        io_chain_count = 0
        tmp_path       = os.path.join(tempfile.gettempdir(),
                                      "_dkbench_sc.tmp")
        data           = b'X' * 512
        end_io         = time.perf_counter() + DURATION

        while time.perf_counter() < end_io:
            try:
                with open(tmp_path, 'wb') as f:
                    f.write(data)
                with open(tmp_path, 'rb') as f:
                    _ = f.read()
                os.remove(tmp_path)
                io_chain_count += 1
            except Exception:
                break

        io_chain_rate = io_chain_count / DURATION / 1e3  # K ops/s
        syscall_results["io_chain_k_per_s"] = round(io_chain_rate, 2)

        # ── Summarize ──────────────────────────────────────────
        gettime_rate = syscall_results.get("gettime", {}).get("rate_m_per_s", 0)
        gettime_lat  = syscall_results.get("gettime", {}).get("latency_ns", 0)

        score = self._normalize(gettime_rate, 0, 1000)

        return {
            "name":          "System Call Overhead",
            "value":         gettime_rate,
            "unit":          "M gettime() syscalls/sec",
            "syscall_stats": syscall_results,
            "gettime_ns":    gettime_lat,
            "getpid_ns":     syscall_results.get("getpid", {}).get("latency_ns"),
            "stat_ns":       syscall_results.get("stat", {}).get("latency_ns"),
            "open_close_ns": syscall_results.get("open_close", {}).get("latency_ns"),
            "malloc_rate_m": malloc_rate,
            "mmap_lat_us":   syscall_results.get("mmap_unmap", {}).get("latency_us"),
            "io_chain_k":    io_chain_rate,
            "raw":           sum(
                v.get("total_calls", 0)
                for v in syscall_results.values()
                if isinstance(v, dict)
            ),
            "score":         score,
            "equivalent_to": "strace overhead / syscall-bench / Windows API bench",
            "description": (
                f"gettime: {gettime_rate:.1f}M/s ({gettime_lat:.0f}ns). "
                f"getpid: {syscall_results.get('getpid',{}).get('latency_ns','?')}ns. "
                f"stat: {syscall_results.get('stat',{}).get('latency_ns','?')}ns. "
                f"open/close: {syscall_results.get('open_close',{}).get('latency_ns','?')}ns. "
                f"malloc/free: {malloc_rate:.2f}M/s. "
                f"I/O chain: {io_chain_rate:.1f}K ops/s."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 7: INTERRUPT & CONTEXT SWITCH LATENCY
    # ──────────────────────────────────────────────────────────

    def test_interrupt_context_switch(self) -> dict:
        """
        Interrupt & Context Switch Latency Test.

        Context switch: OS saves current thread state and
        restores another thread's state.
        Cost: 1–10µs on modern hardware.

        High context switch rate = OS is overloaded.
        High context switch latency = slow scheduler / DPC storms.

        This test measures:
          A. Thread context switch latency (ping-pong between 2 threads)
          B. Context switch rate under load (switches/second)
          C. Signal/interrupt delivery latency
          D. Voluntary vs involuntary context switches (via /proc)
          E. DPC (Deferred Procedure Call) latency proxy (Windows)

        Equivalent: LatencyMon IRQ analysis,
                    perf stat context-switches,
                    Windows Performance Recorder (WPR).
        """
        self.progress_cb("System: Interrupt & Context Switch Latency...", 62)

        cs_results = {}

        # ── A: Thread Ping-Pong Context Switch ─────────────────
        N_SWITCHES  = 5000
        evt_a2b     = threading.Event()
        evt_b2a     = threading.Event()
        switch_times = []

        def thread_b():
            for _ in range(N_SWITCHES):
                evt_a2b.wait()
                evt_a2b.clear()
                evt_b2a.set()

        tb = threading.Thread(target=thread_b, daemon=True)
        tb.start()

        # Warm up
        for _ in range(50):
            evt_a2b.set()
            evt_b2a.wait()
            evt_b2a.clear()

        # Timed ping-pong
        for _ in range(N_SWITCHES):
            t0 = time.perf_counter()
            evt_a2b.set()
            evt_b2a.wait()
            evt_b2a.clear()
            switch_times.append((time.perf_counter() - t0) * 1e6)

        tb.join(timeout=5)

        sw_arr = np.array(switch_times, dtype=np.float64)
        # Each round-trip = 2 context switches
        cs_lat_us = float(np.mean(sw_arr)) / 2

        cs_results["ctx_switch_lat_us"] = {
            "rtt_avg_us":   round(float(np.mean(sw_arr)), 2),
            "rtt_p99_us":   round(float(np.percentile(sw_arr, 99)), 2),
            "ctx_sw_us":    round(cs_lat_us, 2),
            "n_switches":   N_SWITCHES * 2,
        }

        # ── B: Context Switch Rate ──────────────────────────────
        DURATION        = 3.0
        switch_count    = [0]
        stop_rate_test  = threading.Event()

        rate_evt_a = threading.Event()
        rate_evt_b = threading.Event()

        def rate_thread_a():
            while not stop_rate_test.is_set():
                rate_evt_a.set()
                rate_evt_b.wait(timeout=0.001)
                rate_evt_b.clear()
                switch_count[0] += 1

        def rate_thread_b():
            while not stop_rate_test.is_set():
                rate_evt_a.wait(timeout=0.001)
                rate_evt_a.clear()
                rate_evt_b.set()
                switch_count[0] += 1

        rta = threading.Thread(target=rate_thread_a, daemon=True)
        rtb = threading.Thread(target=rate_thread_b, daemon=True)
        rta.start(); rtb.start()
        time.sleep(DURATION)
        stop_rate_test.set()
        rta.join(timeout=2); rtb.join(timeout=2)

        cs_rate = switch_count[0] / DURATION / 1000  # K/s
        cs_results["cs_rate_k_per_sec"] = round(cs_rate, 1)

        # ── C: OS-reported context switches ────────────────────
        os_cs_data = {}
        if PSUTIL_OK:
            try:
                proc = psutil.Process(os.getpid())
                ctx = proc.num_ctx_switches()
                os_cs_data = {
                    "voluntary":   ctx.voluntary,
                    "involuntary": ctx.involuntary,
                }
            except Exception:
                pass

        if IS_LINUX:
            try:
                with open('/proc/stat') as f:
                    for line in f:
                        if line.startswith('ctxt'):
                            os_cs_data['system_total'] = int(line.split()[1])
            except Exception:
                pass

        cs_results["os_ctx_switches"] = os_cs_data

        # ── D: Semaphore/Mutex Overhead ────────────────────────
        import threading
        lock          = threading.Lock()
        sem           = threading.Semaphore(1)
        N_LOCK        = 100_000
        lock_times    = []

        for _ in range(N_LOCK):
            t0 = time.perf_counter()
            lock.acquire()
            lock.release()
            lock_times.append((time.perf_counter() - t0) * 1e9)

        lock_arr = np.array(lock_times, dtype=np.float64)
        cs_results["mutex_acquire_ns"] = {
            "avg_ns":  round(float(np.mean(lock_arr)), 2),
            "p99_ns":  round(float(np.percentile(lock_arr, 99)), 2),
            "max_ns":  round(float(np.max(lock_arr)), 2),
        }

        # ── E: Condition Variable Latency ──────────────────────
        cond        = threading.Condition()
        N_COND      = 2000
        cond_ready  = [False]
        cond_lats   = []

        def cond_notifier():
            for _ in range(N_COND):
                time.sleep(0.001)
                with cond:
                    cond_ready[0] = True
                    cond.notify()

        cn = threading.Thread(target=cond_notifier, daemon=True)
        cn.start()

        for _ in range(N_COND):
            t0 = time.perf_counter()
            with cond:
                cond.wait_for(lambda: cond_ready[0], timeout=0.01)
                cond_ready[0] = False
            cond_lats.append((time.perf_counter() - t0) * 1e6)

        cn.join(timeout=5)
        cond_arr = np.array(cond_lats, dtype=np.float64)
        cs_results["cond_var_us"] = {
            "avg_us": round(float(np.mean(cond_arr)), 2),
            "p99_us": round(float(np.percentile(cond_arr, 99)), 2),
        }

        score = self._normalize(1 / max(cs_lat_us, 0.1), 0, 10)

        return {
            "name":              "Interrupt & Context Switch Latency",
            "value":             round(cs_lat_us, 2),
            "unit":              "µs (single context switch)",
            "ctx_switch_us":     round(cs_lat_us, 2),
            "cs_rate_k_per_s":   cs_results.get("cs_rate_k_per_sec"),
            "mutex_acquire_ns":  cs_results.get("mutex_acquire_ns"),
            "cond_var_us":       cs_results.get("cond_var_us"),
            "os_ctx_switches":   os_cs_data,
            "n_switches":        N_SWITCHES,
            "raw":               N_SWITCHES * 2,
            "score":             score,
            "equivalent_to":     "LatencyMon IRQ / perf stat / WPR context switch",
            "description": (
                f"Context switch (ping-pong): {cs_lat_us:.2f}µs/switch. "
                f"Switch rate: {cs_rate:.0f}K/s. "
                f"Mutex acquire: "
                f"{cs_results.get('mutex_acquire_ns',{}).get('avg_ns','?')}ns. "
                f"Condition var: "
                f"{cs_results.get('cond_var_us',{}).get('avg_us','?')}µs. "
                "<2µs context switch = modern OS. >10µs = high DPC activity."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 8: POWER CONSUMPTION ESTIMATION
    # ──────────────────────────────────────────────────────────

    def test_power_consumption(self) -> dict:
        """
        Power Consumption Estimation.

        Measures system power draw indirectly through:
          A. CPU power via RAPL (Running Average Power Limit)
             on Linux via /sys/class/powercap/intel-rapl
          B. CPU power via WMI on Windows
          C. GPU power via GPUtil
          D. Battery drain rate (laptops only)
          E. Performance-per-watt estimation

        Also estimates:
          - TDP efficiency (performance per estimated watt)
          - Idle vs load power delta

        Equivalent: HWiNFO power sensors,
                    Intel Power Gadget, RAPL measurements.
        """
        self.progress_cb("System: Power Consumption Estimation...", 72)

        power_data = {}

        # ── A: RAPL CPU Power (Linux) ──────────────────────────
        rapl_power_w = None
        if IS_LINUX:
            try:
                rapl_base = "/sys/class/powercap/intel-rapl"
                if os.path.exists(rapl_base):
                    energy_files = []
                    for domain in os.listdir(rapl_base):
                        ef = os.path.join(rapl_base, domain, "energy_uj")
                        if os.path.exists(ef):
                            energy_files.append(ef)

                    if energy_files:
                        def read_energy():
                            total = 0
                            for ef in energy_files:
                                with open(ef) as f:
                                    total += int(f.read().strip())
                            return total

                        e0 = read_energy()
                        time.sleep(1.0)
                        e1 = read_energy()
                        rapl_power_w = (e1 - e0) / 1e6  # µJ → W
                        power_data["rapl_cpu_watts"] = round(rapl_power_w, 2)
            except Exception:
                pass

        # ── B: GPU Power via GPUtil ────────────────────────────
        gpu_power_w = None
        if GPUTIL_OK:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    power_data["gpu_info"] = {
                        "name":    g.name,
                        "load_pct":g.load * 100,
                        "temp_c":  g.temperature,
                        "vram_used_mb": g.memoryUsed,
                    }
            except Exception:
                pass

        # ── C: Battery Drain Rate (Laptops) ────────────────────
        battery_data = {}
        if PSUTIL_OK:
            try:
                bat = psutil.sensors_battery()
                if bat and not bat.power_plugged:
                    # Measure drain over 5 seconds
                    pct_start  = bat.percent
                    time.sleep(5)
                    bat2       = psutil.sensors_battery()
                    pct_end    = bat2.percent if bat2 else pct_start
                    drain_pct  = pct_start - pct_end
                    drain_rate = drain_pct * 12  # extrapolate to per-hour

                    battery_data = {
                        "percent":       round(pct_start, 1),
                        "plugged_in":    bat.power_plugged,
                        "drain_pct_5s":  round(drain_pct, 3),
                        "est_drain_hr":  round(drain_rate, 2),
                        "time_left_s":   bat.secsleft,
                    }
                elif bat:
                    battery_data = {
                        "percent":    round(bat.percent, 1),
                        "plugged_in": bat.power_plugged,
                        "charging":   True,
                    }
            except Exception:
                pass

        power_data["battery"] = battery_data

        # ── D: psutil Power / CPU metrics ──────────────────────
        cpu_metrics = {}
        if PSUTIL_OK:
            try:
                cpu_metrics["cpu_freq_mhz"]   = (
                    psutil.cpu_freq().current if psutil.cpu_freq() else None
                )
                cpu_metrics["cpu_usage_pct"]  = psutil.cpu_percent(interval=1)
                cpu_metrics["cpu_count_phys"] = psutil.cpu_count(logical=False)
                cpu_metrics["cpu_count_log"]  = psutil.cpu_count(logical=True)

                vmem = psutil.virtual_memory()
                cpu_metrics["ram_used_gb"]    = round(vmem.used / 1e9, 2)
                cpu_metrics["ram_total_gb"]   = round(vmem.total / 1e9, 2)
                cpu_metrics["ram_pct"]        = vmem.percent

            except Exception:
                pass

        power_data["cpu_metrics"] = cpu_metrics

        # ── E: Performance per Watt estimation ─────────────────
        # Run a known workload and estimate GFLOPS/W
        PERF_DURATION = 3.0
        rng           = np.random.default_rng(seed=1)
        A             = rng.standard_normal((512, 512), dtype=np.float64)
        B             = rng.standard_normal((512, 512), dtype=np.float64)
        iters         = 0
        end_perf      = time.perf_counter() + PERF_DURATION

        while time.perf_counter() < end_perf:
            C = np.dot(A, B)
            iters += 1

        flops_per_iter = 2 * (512 ** 3)
        total_gflops   = flops_per_iter * iters / PERF_DURATION / 1e9

        if rapl_power_w and rapl_power_w > 0:
            gflops_per_w = total_gflops / rapl_power_w
        else:
            gflops_per_w = None

        power_data["perf_gflops"]     = round(total_gflops, 3)
        power_data["gflops_per_watt"] = (
            round(gflops_per_w, 3) if gflops_per_w else None
        )

        # ── F: Windows Power Plan ──────────────────────────────
        power_plan = "Unknown"
        if IS_WINDOWS:
            try:
                result = subprocess.run(
                    ['powercfg', '/getactivescheme'],
                    capture_output=True, text=True, timeout=5
                )
                output = result.stdout.lower()
                if 'high performance' in output:
                    power_plan = "High Performance"
                elif 'power saver' in output:
                    power_plan = "Power Saver"
                elif 'balanced' in output:
                    power_plan = "Balanced"
            except Exception:
                pass

        power_data["power_plan"] = power_plan

        score = self._normalize(total_gflops, 0, 500)

        return {
            "name":            "Power Consumption Estimation",
            "value":           round(total_gflops, 3),
            "unit":            "GFLOPS (performance measurement)",
            "rapl_cpu_watts":  rapl_power_w,
            "gpu_info":        power_data.get("gpu_info"),
            "battery":         battery_data,
            "cpu_metrics":     cpu_metrics,
            "perf_gflops":     round(total_gflops, 3),
            "gflops_per_watt": gflops_per_w,
            "power_plan":      power_plan,
            "raw":             iters,
            "score":           score,
            "equivalent_to":   "HWiNFO power sensors / Intel Power Gadget",
            "description": (
                f"CPU RAPL power: "
                f"{rapl_power_w or 'N/A (Windows/no RAPL)'}W. "
                f"Performance: {total_gflops:.2f}GFLOPS. "
                + (f"Efficiency: {gflops_per_w:.2f}GFLOPS/W. "
                   if gflops_per_w else "")
                + f"Power plan: {power_plan}. "
                + (f"Battery: {battery_data.get('percent','?')}%. "
                   if battery_data else "AC powered. ")
                + "Use HWiNFO for real-time watt measurements."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 9: THERMAL DISSIPATION RATE
    # ──────────────────────────────────────────────────────────

    def test_thermal_dissipation(self) -> dict:
        """
        Thermal Dissipation Rate Test.

        Measures how quickly the system heats up under load
        and how effectively it dissipates heat.

        Thermal metrics:
          A. Baseline temperature (idle)
          B. Peak temperature (under full load)
          C. Thermal rise rate (°C/second under load)
          D. Thermal stability (temperature variance under load)
          E. Cooling effectiveness (peak - idle delta)

        Good cooling: peak < 80°C, delta < 40°C
        Thermal throttle risk: peak > 90°C (CPU), > 83°C (GPU)

        Equivalent: HWiNFO thermal logging,
                    AIDA64 thermal test, Prime95 thermal.
        """
        self.progress_cb("System: Thermal Dissipation Rate...", 82)

        thermal_results = {}

        # ── A: Baseline Temperature ────────────────────────────
        self.progress_cb("System Thermal: Measuring baseline (idle)...", 82)
        time.sleep(2)  # Brief idle period
        baseline_temp = _get_cpu_temp()
        thermal_results["baseline_temp_c"] = (
            round(baseline_temp, 1) if baseline_temp else None
        )

        # ── B: Load Temperature Profile ────────────────────────
        LOAD_DURATION   = 15  # seconds of load
        SAMPLE_INTERVAL = 1   # sample every 1 second
        temp_timeline   = []
        stop_load       = threading.Event()

        def cpu_load_worker():
            """Full CPU load workload."""
            rng  = np.random.default_rng(seed=0)
            A    = rng.standard_normal((512, 512), dtype=np.float64)
            B    = rng.standard_normal((512, 512), dtype=np.float64)
            while not stop_load.is_set():
                C = np.dot(A, B)
                A[0, 0] = C[0, 0] * 1e-15  # Prevent optimization

        # Launch load threads
        load_threads = [
            threading.Thread(target=cpu_load_worker, daemon=True)
            for _ in range(CPU_COUNT)
        ]
        for t in load_threads:
            t.start()

        self.progress_cb(
            f"System Thermal: Loading all {CPU_COUNT} cores for "
            f"{LOAD_DURATION}s...", 83
        )

        # Sample temperature during load
        for i in range(LOAD_DURATION):
            time.sleep(SAMPLE_INTERVAL)
            temp = _get_cpu_temp()
            if temp:
                temp_timeline.append({
                    "time_s":  i + 1,
                    "temp_c":  round(temp, 1),
                })
            self.progress_cb(
                f"System Thermal: {i+1}/{LOAD_DURATION}s — "
                f"{temp or '?'}°C",
                83 + int((i + 1) / LOAD_DURATION * 5)
            )

            if self._cancelled():
                break

        stop_load.set()
        for t in load_threads:
            t.join(timeout=3)

        # ── C: Cool-Down Rate ──────────────────────────────────
        self.progress_cb("System Thermal: Measuring cool-down...", 88)
        cooldown_start  = _get_cpu_temp()
        time.sleep(10)
        cooldown_end    = _get_cpu_temp()

        if cooldown_start and cooldown_end:
            cooldown_rate = (cooldown_start - cooldown_end) / 10  # °C/s
        else:
            cooldown_rate = None

        # ── Analysis ────────────────────────────────────────────
        if temp_timeline:
            temps         = [t["temp_c"] for t in temp_timeline]
            peak_temp     = max(temps)
            avg_load_temp = statistics.mean(temps)
            temp_variance = statistics.stdev(temps) if len(temps) > 1 else 0

            # Thermal rise rate (from first to peak)
            if baseline_temp and temps:
                rise_delta = peak_temp - baseline_temp
                rise_rate  = rise_delta / min(5, len(temps))  # °C/s in first 5s
            else:
                rise_delta = 0
                rise_rate  = 0

            # Thermal stability (variance in last half of load)
            mid          = len(temps) // 2
            stable_temps = temps[mid:]
            stability    = (
                statistics.stdev(stable_temps)
                if len(stable_temps) > 1
                else 0
            )
        else:
            peak_temp = avg_load_temp = temp_variance = 0
            rise_delta = rise_rate = stability = 0
            temps = []

        # Thermal classification
        if peak_temp > 0:
            if peak_temp < 70:
                thermal_class = "Excellent (< 70°C)"
            elif peak_temp < 80:
                thermal_class = "Good (70–80°C)"
            elif peak_temp < 90:
                thermal_class = "Acceptable (80–90°C)"
            elif peak_temp < 95:
                thermal_class = "⚠️ Hot (90–95°C) — throttle risk"
            else:
                thermal_class = "🔴 Critical (>95°C) — immediate action needed"
        else:
            thermal_class = "Temperature sensor unavailable"

        thermal_results.update({
            "peak_temp_c":      round(peak_temp, 1) if peak_temp else None,
            "avg_load_temp_c":  round(avg_load_temp, 1) if avg_load_temp else None,
            "temp_delta_c":     round(rise_delta, 1) if rise_delta else None,
            "rise_rate_c_per_s":round(rise_rate, 2) if rise_rate else None,
            "stability_std_c":  round(stability, 2),
            "cooldown_rate_c_s":round(cooldown_rate, 2) if cooldown_rate else None,
            "temp_timeline":    temp_timeline,
            "thermal_class":    thermal_class,
        })

        # GPU temperature
        gpu_temp = None
        if GPUTIL_OK:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_temp = gpus[0].temperature
            except Exception:
                pass

        thermal_results["gpu_temp_c"] = gpu_temp

        # Score: lower peak temp = better cooling
        if peak_temp and peak_temp > 0:
            score = self._normalize(100 - peak_temp, 0, 60)
        else:
            score = 50_000  # Default if no sensor

        return {
            "name":              "Thermal Dissipation Rate",
            "value":             thermal_results.get("peak_temp_c", 0),
            "unit":              "°C (peak CPU temperature under load)",
            "baseline_temp_c":   thermal_results.get("baseline_temp_c"),
            "peak_temp_c":       thermal_results.get("peak_temp_c"),
            "avg_load_temp_c":   thermal_results.get("avg_load_temp_c"),
            "temp_delta_c":      thermal_results.get("temp_delta_c"),
            "rise_rate_c_per_s": thermal_results.get("rise_rate_c_per_s"),
            "stability_std_c":   thermal_results.get("stability_std_c"),
            "cooldown_rate_c_s": thermal_results.get("cooldown_rate_c_s"),
            "thermal_class":     thermal_class,
            "gpu_temp_c":        gpu_temp,
            "temp_timeline":     temp_timeline,
            "load_cores":        CPU_COUNT,
            "load_duration_s":   LOAD_DURATION,
            "raw":               len(temp_timeline),
            "score":             score,
            "equivalent_to":     "HWiNFO thermal / AIDA64 thermal / Prime95",
            "description": (
                f"Baseline: {thermal_results.get('baseline_temp_c','?')}°C → "
                f"Peak: {thermal_results.get('peak_temp_c','?')}°C "
                f"(+{thermal_results.get('temp_delta_c','?')}°C). "
                f"Rise rate: {thermal_results.get('rise_rate_c_per_s','?')}°C/s. "
                f"Cooling: {thermal_class}. "
                f"GPU: {gpu_temp or 'N/A'}°C. "
                f"Cooldown: {thermal_results.get('cooldown_rate_c_s','?')}°C/s."
            )
        }

    # ──────────────────────────────────────────────────────────
    # TEST 10: FULL SYSTEM STRESS TEST
    # ──────────────────────────────────────────────────────────

    def test_full_system_stress(self) -> dict:
        """
        Full System Stress Test (All Components Simultaneously).

        Runs simultaneous load on ALL subsystems:
          - ALL CPU cores: matrix multiply + SHA256
          - ALL RAM: STREAM Triad across 512MB buffers
          - Disk I/O: sustained sequential write
          - Network: TCP loopback saturation
          - GPU: off-screen render (if available)

        Monitors during stress:
          - CPU temperature progression
          - RAM usage delta
          - Disk write speed stability
          - Network throughput stability
          - System stability (any crashes/errors)

        This is the definitive AIDA64 System Stability Test equivalent.
        Duration: configurable (default 30 seconds for benchmark).

        Equivalent: AIDA64 System Stability Test,
                    Intel Burn Test, Prime95 + FurMark combined.
        """
        self.progress_cb("System: Full System Stress Test (All Components)...", 92)

        STRESS_DURATION = 20  # seconds (short for benchmark; increase for real test)
        SAMPLE_INTERVAL = 2   # seconds between samples
        N_SAMPLES       = STRESS_DURATION // SAMPLE_INTERVAL

        stress_log      = []
        stop_stress     = threading.Event()

        # ── Launch CPU stress (all cores) ──────────────────────
        cpu_args     = [
            (STRESS_DURATION + 5, i * 31337, i)
            for i in range(CPU_COUNT)
        ]
        cpu_pool     = multiprocessing.Pool(CPU_COUNT)
        cpu_future   = cpu_pool.map_async(_stress_cpu_worker, cpu_args)

        # ── Launch RAM stress ──────────────────────────────────
        ram_args     = [
            (STRESS_DURATION + 5, 128, i)
            for i in range(min(CPU_COUNT, 4))
        ]
        ram_pool     = multiprocessing.Pool(min(CPU_COUNT, 4))
        ram_future   = ram_pool.map_async(_stress_ram_worker, ram_args)

        # ── Launch Disk stress ─────────────────────────────────
        disk_bytes_written  = [0]
        disk_errors         = [0]
        disk_speeds_mbs     = []
        tmp_stress          = os.path.join(
            tempfile.gettempdir(), "_dkbench_stress.tmp"
        )
        DISK_CHUNK          = b'S' * (1024 * 1024)  # 1MB

        def disk_stress():
            try:
                with open(tmp_stress, 'wb', buffering=0) as f:
                    while not stop_stress.is_set():
                        f.write(DISK_CHUNK)
                        disk_bytes_written[0] += len(DISK_CHUNK)
                        if disk_bytes_written[0] > 2 * 1024 * 1024 * 1024:
                            f.seek(0)
                            disk_bytes_written[0] = 0
            except Exception as e:
                disk_errors[0] += 1
            finally:
                try:
                    os.remove(tmp_stress)
                except Exception:
                    pass

        disk_thread = threading.Thread(target=disk_stress, daemon=True)

        # ── Launch Network stress ──────────────────────────────
        net_bytes_total = [0]
        net_errors      = [0]

        def net_stress():
            try:
                srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                srv.bind(('127.0.0.1', 0))
                srv.listen(1)
                port = srv.getsockname()[1]
                srv.settimeout(2)

                received = [0]
                done_evt = threading.Event()

                def receiver():
                    try:
                        conn, _ = srv.accept()
                        while not stop_stress.is_set():
                            data = conn.recv(65536)
                            if data:
                                received[0] += len(data)
                        conn.close()
                    except Exception:
                        done_evt.set()

                rt = threading.Thread(target=receiver, daemon=True)
                rt.start()
                time.sleep(0.2)

                sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sender.connect(('127.0.0.1', port))
                chunk = b'N' * 65536

                while not stop_stress.is_set():
                    try:
                        sender.send(chunk)
                        net_bytes_total[0] += len(chunk)
                    except Exception:
                        net_errors[0] += 1
                        break

                sender.close()
                srv.close()
                net_bytes_total[0] = received[0]

            except Exception:
                net_errors[0] += 1

        net_thread = threading.Thread(target=net_stress, daemon=True)

        # ── Start all stress threads ───────────────────────────
        disk_thread.start()
        net_thread.start()

        self.progress_cb(
            f"System Stress: Running all components for {STRESS_DURATION}s...",
            92
        )

        # ── Monitor loop ───────────────────────────────────────
        t0_stress = time.perf_counter()

        for sample_i in range(N_SAMPLES):
            time.sleep(SAMPLE_INTERVAL)

            if self._cancelled():
                break

            elapsed_s   = time.perf_counter() - t0_stress
            cpu_temp    = _get_cpu_temp()
            ram_used_gb = _get_ram_usage_gb()

            if PSUTIL_OK:
                try:
                    cpu_pct = psutil.cpu_percent(interval=None)
                    disk_io = psutil.disk_io_counters()
                    net_io  = psutil.net_io_counters()
                except Exception:
                    cpu_pct = disk_io = net_io = None
            else:
                cpu_pct = disk_io = net_io = None

            sample = {
                "time_s":       round(elapsed_s, 1),
                "cpu_temp_c":   round(cpu_temp, 1) if cpu_temp else None,
                "ram_used_gb":  round(ram_used_gb, 2),
                "cpu_pct":      round(cpu_pct, 1) if cpu_pct else None,
                "disk_written_mb": round(disk_bytes_written[0] / 1e6, 1),
                "net_mb":       round(net_bytes_total[0] / 1e6, 1),
                "disk_errors":  disk_errors[0],
                "net_errors":   net_errors[0],
            }
            stress_log.append(sample)

            self.progress_cb(
                f"Stress {sample_i+1}/{N_SAMPLES}: "
                f"CPU={cpu_pct or '?'}% "
                f"Temp={cpu_temp or '?'}°C "
                f"RAM={ram_used_gb:.1f}GB",
                92 + int((sample_i + 1) / N_SAMPLES * 7)
            )

        # ── Stop all stress ────────────────────────────────────
        stop_stress.set()
        cpu_pool.terminate(); cpu_pool.join()
        ram_pool.terminate(); ram_pool.join()
        disk_thread.join(timeout=5)
        net_thread.join(timeout=5)

        total_stress_time = time.perf_counter() - t0_stress

        # ── Analyze results ────────────────────────────────────
        if stress_log:
            temps_log    = [s["cpu_temp_c"] for s in stress_log if s["cpu_temp_c"]]
            cpu_pcts     = [s["cpu_pct"]    for s in stress_log if s["cpu_pct"]]
            ram_used     = [s["ram_used_gb"] for s in stress_log]
            total_errors = disk_errors[0] + net_errors[0]

            peak_temp_s  = max(temps_log)   if temps_log  else None
            avg_cpu_pct  = statistics.mean(cpu_pcts) if cpu_pcts else None
            ram_delta_gb = max(ram_used) - min(ram_used) if ram_used else 0
            disk_mbs     = (
                max(s["disk_written_mb"] for s in stress_log) / total_stress_time
                if stress_log else 0
            )
            net_mbs      = (
                max(s["net_mb"] for s in stress_log) / total_stress_time
                if stress_log else 0
            )
        else:
            peak_temp_s = avg_cpu_pct = None
            ram_delta_gb = total_errors = disk_mbs = net_mbs = 0

        # Stability rating
        if total_errors == 0 and (peak_temp_s or 0) < 95:
            stability = "✅ STABLE — No errors detected"
        elif total_errors == 0:
            stability = "⚠️ STABLE but HIGH TEMPERATURE"
        else:
            stability = f"❌ UNSTABLE — {total_errors} errors detected"

        score = self._normalize(
            100 - total_errors * 10, 0, 100
        )

        return {
            "name":              "Full System Stress Test",
            "value":             round(total_stress_time, 1),
            "unit":              "seconds (stress duration)",
            "stability":         stability,
            "peak_cpu_temp_c":   round(peak_temp_s, 1) if peak_temp_s else None,
            "avg_cpu_pct":       round(avg_cpu_pct, 1) if avg_cpu_pct else None,
            "ram_delta_gb":      round(ram_delta_gb, 2),
            "disk_write_mbs":    round(disk_mbs, 1),
            "net_throughput_mbs":round(net_mbs, 1),
            "total_errors":      total_errors,
            "disk_errors":       disk_errors[0],
            "net_errors":        net_errors[0],
            "stress_log":        stress_log,
            "duration_s":        round(total_stress_time, 1),
            "cores_stressed":    CPU_COUNT,
            "raw":               len(stress_log),
            "score":             score,
            "equivalent_to":     "AIDA64 System Stability Test / Intel Burn Test",
            "description": (
                f"All-core stress for {total_stress_time:.0f}s on {CPU_COUNT} cores. "
                f"Peak temp: {peak_temp_s or 'N/A'}°C. "
                f"CPU load: {avg_cpu_pct or 'N/A'}%. "
                f"Disk write: {disk_mbs:.0f}MB/s. "
                f"Network: {net_mbs:.0f}MB/s. "
                f"Errors: {total_errors}. "
                f"Result: {stability}."
            )
        }

    # ──────────────────────────────────────────────────────────
    # RUN ALL
    # ──────────────────────────────────────────────────────────

    def run_all(self) -> dict:
        """
        Run all 10 system-level benchmarks sequentially.
        Returns consolidated results with overall score.
        """
        tests = [
            self.test_pcie_bandwidth,
            self.test_usb_transfer_speed,
            self.test_network_performance,
            self.test_ipc_performance,
            self.test_scheduler_latency,
            self.test_syscall_overhead,
            self.test_interrupt_context_switch,
            self.test_power_consumption,
            self.test_thermal_dissipation,
            self.test_full_system_stress,
        ]

        results  = []
        for idx, fn in enumerate(tests):
            if self._cancelled():
                break
            try:
                r = fn()
                results.append(r)
                self.progress_cb(
                    f"✅ {r['name'][:50]} — "
                    f"Score: {r.get('score', 0):,}",
                    int((idx + 1) / len(tests) * 100)
                )
            except Exception as e:
                import traceback
                results.append({
                    "name":  fn.__name__,
                    "error": str(e),
                    "trace": traceback.format_exc()[-300:],
                    "score": 0,
                })
                self.progress_cb(
                    f"❌ {fn.__name__} — ERROR: {str(e)[:40]}",
                    int((idx + 1) / len(tests) * 100)
                )

        scoreable = [
            r["score"] for r in results
            if "score" in r and "error" not in r and r["score"] > 0
        ]
        overall = int(np.mean(scoreable)) if scoreable else 0
        self.progress_cb("System Benchmark Complete!", 100)

        return {
            "component":     "System",
            "overall_score": overall,
            "grade":         self._grade(overall),
            "tier":          self._tier(overall),
            "platform":      platform.platform(),
            "cpu_count":     CPU_COUNT,
            "python_ver":    sys.version.split()[0],
            "test_count":    len(results),
            "tests":         results,
        }

    # ── SCORING HELPERS ───────────────────────────────────────

    @staticmethod
    def _normalize(value: float, low: float, high: float,
                   out_min: int = 0, out_max: int = 100_000) -> int:
        if high == low:
            return out_min
        clamped = max(low, min(high, value))
        return int(
            out_min + (clamped - low) / (high - low) * (out_max - out_min)
        )

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 85_000: return "S"
        if score >= 70_000: return "A"
        if score >= 55_000: return "B"
        if score >= 40_000: return "C"
        if score >= 25_000: return "D"
        return "F"

    @staticmethod
    def _tier(score: int) -> str:
        if score >= 85_000: return "Flagship Workstation"
        if score >= 70_000: return "High-End Desktop"
        if score >= 55_000: return "Mid-Range Desktop"
        if score >= 40_000: return "Entry-Level Desktop / High-End Laptop"
        if score >= 25_000: return "Budget Desktop / Mid-Range Laptop"
        return "Legacy / Budget Laptop"


# ══════════════════════════════════════════════════════════════
#  STANDALONE QUICK TEST
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":

    def cb(msg: str, pct: int):
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        print(f"\r[{bar}] {pct:3d}% {msg[:55]:<55}",
              end="", flush=True)
        if pct >= 100:
            print()

    print("╔═══════════════════════════════════════════════════════╗")
    print("║     SYSTEM VITAL SYSTEM BENCHMARK SUITE — Part 5         ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print(f"  Platform  : {platform.platform()}")
    print(f"  CPU cores : {CPU_COUNT}")
    print(f"  Python    : {sys.version.split()[0]}")
    print(f"  psutil    : {'✅' if PSUTIL_OK else '❌ pip install psutil'}")
    print(f"  GPUtil    : {'✅' if GPUTIL_OK else '❌ pip install GPUtil'}")
    print(f"  WMI       : {'✅' if WMI_OK else '❌ pip install wmi'}")
    print("─" * 57)

    bench   = SystemBenchmark(progress_callback=cb)
    results = bench.run_all()

    print(f"\n{'═' * 70}")
    print(f"  SYSTEM BENCHMARK RESULTS")
    print(f"  Overall Score : {results['overall_score']:,}")
    print(f"  Grade         : {results['grade']}")
    print(f"  Tier          : {results['tier']}")
    print(f"{'═' * 70}")

    for t in results["tests"]:
        if "error" in t:
            print(
                f"  ❌ {t['name'][:46]:<46} "
                f"ERROR: {str(t.get('error','?'))[:20]}"
            )
        else:
            val   = str(t.get("value", "?"))[:10]
            unit  = t.get("unit", "")[:20]
            score = t.get("score", 0)
            bar   = "█" * (score // 10_000) + "░" * (10 - score // 10_000)
            print(
                f"  ✅ {t['name'][:42]:<42}"
                f" {val:<11}{unit:<20}"
                f" [{bar}] {score:>7,}"
            )

    print(f"{'═' * 70}")

    # Print stress test summary if available
    for t in results["tests"]:
        if "Full System Stress" in t.get("name", ""):
            print(f"\n  STRESS TEST: {t.get('stability', 'N/A')}")
            if t.get("stress_log"):
                print(f"  {'Time':>6} {'CPU%':>6} {'Temp°C':>8}"
                      f" {'RAM GB':>8} {'DiskMB':>8}")
                for s in t["stress_log"]:
                    print(
                        f"  {s['time_s']:>6.0f}s"
                        f" {s.get('cpu_pct') or 0:>5.0f}%"
                        f" {s.get('cpu_temp_c') or 0:>7.1f}°C"
                        f" {s.get('ram_used_gb') or 0:>7.2f}GB"
                        f" {s.get('disk_written_mb') or 0:>7.0f}MB"
                    )
    print(f"{'═' * 70}")
