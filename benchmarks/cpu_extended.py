"""
SYSTEM VITAL CPU EXTENDED BENCHMARK — Part 1
Additional industry-level CPU tests:

1. AES-256 Encryption Throughput (VeraCrypt equivalent)
2. Monte Carlo Pi Estimation (SPEC FP equivalent)
3. N-Queens Backtracking Solver (SPEC INT recursive logic)
4. Fibonacci: Memoized vs Raw (Branch prediction stress)
5. Bitwise POPCNT Throughput (Hardware instruction IPC)
6. CRC32 Checksum Throughput (Data integrity throughput)
7. Mersenne Twister RNG Throughput (PRNG / random workload)
8. CPU-Side Mandelbrot (FP64) (Pure FP64 compute)
9. JSON Serialize/Deserialize (Real-world app workload)
10. String Search & Replace Throughput (Text processing workload)

All tests:
- Run for a fixed duration or fixed iteration count
- Return a normalized score (0–100,000 scale)
- Are thread-safe and pickling-safe for multiprocessing
- Include a grade (S/A/B/C/D/F) and tier label
"""

import time
import math
import json
import zlib
import struct
import random
import string
import hashlib
import secrets
import multiprocessing
import numpy as np
from typing import Callable, Optional

# ══════════════════════════════════════════════════════════════
# MODULE-LEVEL WORKER FUNCTIONS
# (Must be at module top-level for Windows multiprocessing)
# ══════════════════════════════════════════════════════════════

def _aes_worker(args: tuple) -> tuple:
    """
    AES-256 encryption worker using Python's native hashlib-based
    block cipher emulation. We implement AES-256-CBC key schedule
    and block encryption from scratch to stress integer ALU,
    bitwise operations, and S-box lookups.
    """
    duration, seed = args

    # ── AES S-box (standard FIPS-197 forward S-box) ──
    SBOX = bytes([
        0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,
        0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
        0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,
        0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
        0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,
        0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
        0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,
        0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
        0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,
        0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
        0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,
        0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
        0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,
        0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
        0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,
        0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
        0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,
        0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
        0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,
        0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
        0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,
        0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
        0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,
        0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
        0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,
        0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
        0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,
        0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
        0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,
        0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
        0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,
        0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
    ])

    def sub_bytes(state: bytearray) -> bytearray:
        return bytearray(SBOX[b] for b in state)

    def shift_rows(s: bytearray) -> bytearray:
        """ShiftRows transformation on 4×4 state matrix."""
        return bytearray([
            s[0], s[5], s[10], s[15], # Row 0: no shift
            s[4], s[9], s[14], s[3],  # Row 1: shift 1
            s[8], s[13], s[2], s[7],  # Row 2: shift 2
            s[12], s[1], s[6], s[11], # Row 3: shift 3
        ])

    def xtime(a: int) -> int:
        """GF(2^8) multiplication by 2."""
        return (((a << 1) ^ 0x1B) & 0xFF) if (a & 0x80) else (a << 1)

    def mix_column(col: list) -> list:
        """MixColumns on a single column."""
        t = col[0] ^ col[1] ^ col[2] ^ col[3]
        return [
            col[0] ^ t ^ xtime(col[0] ^ col[1]),
            col[1] ^ t ^ xtime(col[1] ^ col[2]),
            col[2] ^ t ^ xtime(col[2] ^ col[3]),
            col[3] ^ t ^ xtime(col[3] ^ col[0]),
        ]

    def mix_columns(state: bytearray) -> bytearray:
        result = bytearray(16)
        for c in range(4):
            col = [state[c*4+r] for r in range(4)]
            mc = mix_column(col)
            for r in range(4):
                result[c*4+r] = mc[r]
        return result

    def add_round_key(state: bytearray, rk: bytes) -> bytearray:
        return bytearray(a ^ b for a, b in zip(state, rk))

    def expand_key(key: bytes) -> list:
        """AES-256 key expansion — generates 15 round keys."""
        RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]
        w = list(key) # 32 bytes = 8 words of 4 bytes
        for i in range(8, 60):
            temp = w[(i-1)*4 : i*4]
            if i % 8 == 0:
                temp = [SBOX[temp[1]] ^ RCON[i//8-1],
                        SBOX[temp[2]],
                        SBOX[temp[3]],
                        SBOX[temp[0]]]
            elif i % 8 == 4:
                temp = [SBOX[b] for b in temp]
            word = [w[(i-8)*4+j] ^ temp[j] for j in range(4)]
            w.extend(word)
        return [bytes(w[i:i+16]) for i in range(0, 15*16, 16)]

    def aes256_encrypt_block(block: bytes, round_keys: list) -> bytes:
        """Full AES-256 block encryption (10+4 rounds for 256-bit key = 14 rounds)."""
        state = bytearray(block)
        state = add_round_key(state, round_keys[0])
        for rnd in range(1, 14):
            state = sub_bytes(state)
            state = shift_rows(state)
            state = mix_columns(state)
            state = add_round_key(state, round_keys[rnd])
        # Final round (no MixColumns)
        state = sub_bytes(state)
        state = shift_rows(state)
        state = add_round_key(state, round_keys[14])
        return bytes(state)

    # ── Run benchmark ──────────────────────────────
    rng = random.Random(seed)
    key = bytes(rng.getrandbits(8) for _ in range(32)) # 256-bit key
    plaintext = bytes(rng.getrandbits(8) for _ in range(16)) # 1 block
    rk = expand_key(key)

    count = 0
    total_bytes = 0
    end_time = time.perf_counter() + duration

    while time.perf_counter() < end_time:
        # Encrypt 64 blocks per loop to reduce loop overhead
        for _ in range(64):
            plaintext = aes256_encrypt_block(plaintext, rk)
            count += 64
            total_bytes += 64 * 16 # 16 bytes per block

    return count, total_bytes

def _monte_carlo_worker(args: tuple) -> int:
    """
    Monte Carlo π estimation.
    Generates random (x,y) pairs and counts how many
    fall inside the unit circle. Pure FP64 stress test.
    """
    n_samples, seed = args
    rng = np.random.default_rng(seed)
    x = rng.uniform(0, 1, n_samples)
    y = rng.uniform(0, 1, n_samples)
    inside = int(np.sum(x*x + y*y <= 1.0))
    return inside

def _nqueens_worker(n: int) -> int:
    """
    N-Queens backtracking solver.
    Counts all solutions for an N×N board.
    Stresses branch prediction and recursive call overhead.
    """
    cols = set()
    diag1 = set() # row - col
    diag2 = set() # row + col
    solutions = [0]

    def backtrack(row: int):
        if row == n:
            solutions[0] += 1
            return
        for col in range(n):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                continue
            cols.add(col); diag1.add(row - col); diag2.add(row + col)
            backtrack(row + 1)
            cols.discard(col); diag1.discard(row - col); diag2.discard(row + col)

    backtrack(0)
    return solutions[0]

def _crc32_worker(duration: float) -> tuple:
    """CRC32 checksum throughput worker."""
    rng = np.random.default_rng(42)
    chunk = bytes(rng.integers(0, 256, 65536, dtype=np.uint8).tolist())
    count = 0
    total_bytes = 0
    end_time = time.perf_counter() + duration
    prev_crc = 0
    while time.perf_counter() < end_time:
        prev_crc = zlib.crc32(chunk, prev_crc) & 0xFFFFFFFF
        count += 1
        total_bytes += len(chunk)
    return count, total_bytes

def _popcnt_worker(duration: float) -> int:
    """
    POPCNT (population count) throughput.
    Measures integer bit manipulation IPC —
    mirrors CPU-Z's instruction throughput test.
    """
    end_time = time.perf_counter() + duration
    count = 0
    val = 0xDEADBEEFCAFEBABE
    while time.perf_counter() < end_time:
        # 16 POPCNT-equivalent ops per iteration
        count += bin(val).count('1')
        count += bin(val ^ 0xFFFFFFFFFFFFFFFF).count('1')
        count += bin(val & 0x0F0F0F0F0F0F0F0F).count('1')
        count += bin(val | 0xF0F0F0F0F0F0F0F0).count('1')
        count += bin(val >> 4).count('1')
        count += bin(val << 4 & 0xFFFFFFFFFFFFFFFF).count('1')
        count += bin(val ^ (val >> 1)).count('1')
        count += bin(val ^ (val << 1)).count('1')
        val = val ^ (val << 3) ^ 0xABCDEF1234567890
        val &= 0xFFFFFFFFFFFFFFFF
    return count

def _rng_worker(duration: float) -> tuple:
    """
    Mersenne Twister RNG throughput.
    Mirrors PRNG benchmarks used in cryptographic toolkits.
    """
    rng = np.random.default_rng(seed=12345)
    BATCH = 100_000
    count = 0
    total_bytes = 0
    end_time = time.perf_counter() + duration
    while time.perf_counter() < end_time:
        arr = rng.integers(0, 2**63, BATCH, dtype=np.int64)
        count += BATCH
        total_bytes += BATCH * 8
    return count, total_bytes

def _mandelbrot_cpu_worker(width: int, height: int, max_iter: int) -> np.ndarray:
    """
    Full CPU-side Mandelbrot computation using vectorized NumPy.
    Stresses FP64 with no GPU involvement.
    """
    x = np.linspace(-2.5, 1.0, width, dtype=np.float64)
    y = np.linspace(-1.25, 1.25, height, dtype=np.float64)
    C = x[np.newaxis, :] + 1j * y[:, np.newaxis]
    Z = np.zeros_like(C)
    M = np.zeros(C.shape, dtype=np.int32)
    mask = np.ones(C.shape, dtype=bool)

    for i in range(max_iter):
        Z[mask] = Z[mask] ** 2 + C[mask]
        escaped = mask & (np.abs(Z) > 2.0)
        M[escaped] = i
        mask[escaped] = False

    return M

# ══════════════════════════════════════════════════════════════
# MAIN CLASS
# ══════════════════════════════════════════════════════════════

class CPUExtendedBenchmark:
    """
    Additional CPU benchmarks for SYSTEM VITAL.
    Complements CPUBenchmark with 10 more industry-equivalent tests.
    Call run_all() for full suite or individual test methods.
    """

    DURATION = 5.0 # seconds per timed test
    MONTE_SAMPLES = 50_000_000
    NQUEENS_N = 14 # N=14 has 365,596 solutions — good solver stress
    MANDEL_W = 1920
    MANDEL_H = 1080
    MANDEL_ITERS = 256

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_cb = progress_callback or (lambda msg, pct: None)
        self.core_count = multiprocessing.cpu_count()

    def test_aes256_throughput(self) -> dict:
        self.progress_cb("CPU Extended: AES-256 Encryption Throughput...", 5)

        args = [(self.DURATION, i * 31337) for i in range(self.core_count)]
        with multiprocessing.Pool(self.core_count) as pool:
            results_mp = pool.map(_aes_worker, args)

        total_count = sum(r[0] for r in results_mp)
        total_bytes = sum(r[1] for r in results_mp)
        throughput_mbs = total_bytes / self.DURATION / 1e6
        blocks_per_sec = total_count / self.DURATION

        sc_count, sc_bytes = _aes_worker((self.DURATION, 0))
        sc_mbs = sc_bytes / self.DURATION / 1e6

        score = self._normalize(sc_mbs, 0, 500)

        return {
            "name": "AES-256 Encryption",
            "value": round(sc_mbs, 3),
            "unit": "MB/s",
            "multicore_mbs": round(throughput_mbs, 3),
            "blocks_per_sec": round(blocks_per_sec, 0),
            "raw": total_count,
            "score": score,
            "description": f"Single-core: {sc_mbs:.2f} MB/s | Multi-core ({self.core_count}T): {throughput_mbs:.2f} MB/s."
        }

    def test_monte_carlo_pi(self) -> dict:
        self.progress_cb("CPU Extended: Monte Carlo Pi (FP64 Stress)...", 15)

        samples_per_core = self.MONTE_SAMPLES // self.core_count
        seeds = [i * 99991 + 1 for i in range(self.core_count)]
        args = [(samples_per_core, s) for s in seeds]

        start = time.perf_counter()
        with multiprocessing.Pool(self.core_count) as pool:
            inside_counts = pool.map(_monte_carlo_worker, args)
        elapsed = time.perf_counter() - start

        total_inside = sum(inside_counts)
        total_samples = samples_per_core * self.core_count
        pi_estimate = 4.0 * total_inside / total_samples
        error_ppm = abs(pi_estimate - math.pi) / math.pi * 1e6
        throughput = total_samples / elapsed / 1e6

        score = self._normalize(throughput, 0, 2000)

        return {
            "name": "Monte Carlo π Estimation",
            "value": round(throughput, 2),
            "unit": "M samples/sec",
            "score": score,
            "description": f"{total_samples:,} samples. π ≈ {pi_estimate:.8f} (error: {error_ppm:.2f} ppm)."
        }

    def test_nqueens(self) -> dict:
        self.progress_cb("CPU Extended: N-Queens Backtracking Solver...", 25)

        start = time.perf_counter()
        solutions = _nqueens_worker(self.NQUEENS_N)
        elapsed = time.perf_counter() - start

        score = self._normalize(1 / elapsed, 0, 20)

        return {
            "name": f"N-Queens Solver (N={self.NQUEENS_N})",
            "value": round(elapsed * 1000, 2),
            "unit": "ms",
            "score": self._normalize(1 / max(elapsed, 0.001), 0, 20),
            "description": f"Found {solutions:,} solutions in {elapsed*1000:.2f}ms."
        }

    def test_fibonacci_branch_prediction(self) -> dict:
        self.progress_cb("CPU Extended: Fibonacci Branch Prediction Test...", 33)

        def fib_iterative(n: int) -> int:
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            return a

        from functools import lru_cache
        @lru_cache(maxsize=None)
        def fib_memo(n: int) -> int:
            if n < 2: return n
            return fib_memo(n-1) + fib_memo(n-2)

        N = 35
        ITERS_ITER = 50_000
        ITERS_MEMO = 50_000

        start = time.perf_counter()
        for _ in range(ITERS_ITER):
            result = fib_iterative(N)
        iter_time = time.perf_counter() - start
        iter_ops = ITERS_ITER / iter_time

        fib_memo(N) # warm up
        start = time.perf_counter()
        for _ in range(ITERS_MEMO):
            fib_memo.cache_clear()
            result = fib_memo(N)
        memo_time = time.perf_counter() - start
        memo_ops = ITERS_MEMO / memo_time

        score = self._normalize(iter_ops, 0, 5_000_000)

        return {
            "name": "Fibonacci Branch Prediction",
            "value": round(iter_ops / 1000, 2),
            "unit": "K ops/sec",
            "score": score,
            "description": f"Iterative: {iter_ops/1000:.1f}K ops/s | Memoized: {memo_ops/1000:.1f}K ops/s."
        }

    def test_popcnt_throughput(self) -> dict:
        self.progress_cb("CPU Extended: POPCNT Instruction Throughput...", 41)

        count = _popcnt_worker(self.DURATION)
        rate_m = count / self.DURATION / 1e6
        score = self._normalize(rate_m, 0, 5000)

        return {
            "name": "POPCNT Bitwise Throughput",
            "value": round(rate_m, 2),
            "unit": "M ops/sec",
            "score": score,
            "description": f"{count/1e9:.3f}B population-count ops in {self.DURATION:.0f}s."
        }

    def test_crc32_throughput(self) -> dict:
        self.progress_cb("CPU Extended: CRC32 Checksum Throughput...", 50)

        count_c, bytes_c = _crc32_worker(self.DURATION)
        throughput_c = bytes_c / self.DURATION / 1e6
        score = self._normalize(throughput_c, 0, 50_000)

        return {
            "name": "CRC32 Checksum Throughput",
            "value": round(throughput_c, 2),
            "unit": "MB/s",
            "score": score,
            "description": f"C-accelerated zlib: {throughput_c:.1f} MB/s."
        }

    def test_rng_throughput(self) -> dict:
        self.progress_cb("CPU Extended: Mersenne Twister RNG Throughput...", 60)

        count, total_bytes = _rng_worker(self.DURATION)
        throughput_mn = count / self.DURATION / 1e6
        score = self._normalize(throughput_mn, 0, 5000)

        return {
            "name": "Mersenne Twister RNG Throughput",
            "value": round(throughput_mn, 2),
            "unit": "M numbers/sec",
            "score": score,
            "description": f"{throughput_mn:.1f}M numbers/sec generated."
        }

    def test_cpu_mandelbrot_fp64(self) -> dict:
        self.progress_cb("CPU Extended: Mandelbrot FP64...", 70)

        start = time.perf_counter()
        M = _mandelbrot_cpu_worker(self.MANDEL_W, self.MANDEL_H, self.MANDEL_ITERS)
        elapsed = time.perf_counter() - start

        total_pixels = self.MANDEL_W * self.MANDEL_H
        mpixels_sec = total_pixels / elapsed / 1e6
        score = self._normalize(mpixels_sec, 0, 500)

        return {
            "name": f"CPU Mandelbrot FP64",
            "value": round(mpixels_sec, 3),
            "unit": "Mpixels/sec",
            "score": score,
            "description": f"{self.MANDEL_W}×{self.MANDEL_H} computed in {elapsed*1000:.1f}ms."
        }

    def test_json_throughput(self) -> dict:
        self.progress_cb("CPU Extended: JSON Serialize/Deserialize Throughput...", 80)
        rng = np.random.default_rng(seed=55)
        payload = {"user_id": 123456789, "active": True, "scores": [int(rng.integers(1000, 99999)) for _ in range(50)]}

        ser_count = 0
        start = time.perf_counter()
        deadline = start + self.DURATION / 2
        while time.perf_counter() < deadline:
            json.dumps(payload, separators=(',', ':'))
            ser_count += 1
        ser_ops = ser_count / (time.perf_counter() - start)

        json_str = json.dumps(payload)
        des_count = 0
        start = time.perf_counter()
        deadline = start + self.DURATION / 2
        while time.perf_counter() < deadline:
            json.loads(json_str)
            des_count += 1
        des_ops = des_count / (time.perf_counter() - start)

        score = self._normalize((ser_ops + des_ops) / 2, 0, 100_000)

        return {
            "name": "JSON Serialize / Deserialize",
            "value": round(ser_ops, 0),
            "unit": "ops/sec",
            "score": score,
            "description": f"Serialize: {ser_ops:.0f} ops/s | Deserialize: {des_ops:.0f} ops/s."
        }

    def test_string_processing(self) -> dict:
        self.progress_cb("CPU Extended: String Processing Throughput...", 90)
        import re
        text = "SYSTEM VITAL benchmark cpu memory latency " * 200
        pattern = re.compile(r'\b(cpu|memory)\b', re.IGNORECASE)

        find_count = 0
        start = time.perf_counter()
        deadline = start + self.DURATION
        while time.perf_counter() < deadline:
            pattern.findall(text)
            find_count += 1
        find_ops = find_count / (time.perf_counter() - start)

        score = self._normalize(find_ops, 0, 50_000)

        return {
            "name": "String Processing Throughput",
            "value": round(find_ops, 2),
            "unit": "ops/sec",
            "score": score,
            "description": f"Regex find: {find_ops:.0f}/s."
        }

    def run_all(self) -> dict:
        tests = [
            self.test_aes256_throughput,
            self.test_monte_carlo_pi,
            self.test_nqueens,
            self.test_fibonacci_branch_prediction,
            self.test_popcnt_throughput,
            self.test_crc32_throughput,
            self.test_rng_throughput,
            self.test_cpu_mandelbrot_fp64,
            self.test_json_throughput,
            self.test_string_processing,
        ]

        results = []
        for fn in tests:
            try:
                result = fn()
                results.append(result)
            except Exception as e:
                results.append({
                    "name": fn.__name__,
                    "error": str(e),
                    "score": 0
                })

        scoreable = [r["score"] for r in results if "score" in r and "error" not in r]
        overall_score = int(np.mean(scoreable)) if scoreable else 0
        self.progress_cb("CPU Extended Benchmark Complete!", 100)

        return {
            "component": "CPU_Extended",
            "overall_score": overall_score,
            "grade": self._grade(overall_score),
            "tier": self._tier(overall_score),
            "tests": results,
            "core_count": self.core_count,
        }

    @staticmethod
    def _normalize(value: float, low: float, high: float, out_min: int = 0, out_max: int = 100_000) -> int:
        if high == low: return out_min
        clamped = max(low, min(high, value))
        return int(out_min + (clamped - low) / (high - low) * (out_max - out_min))

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
        if score >= 85_000: return "Flagship"
        if score >= 70_000: return "High-End"
        if score >= 55_000: return "Mid-Range"
        if score >= 40_000: return "Entry-Level"
        return "Legacy"
