"""
SYSTEM VITAL CPU BENCHMARK ENGINE
Industry-level CPU tests covering:
  - Integer Arithmetic (IPS)
  - Floating Point (FLOPS)
  - Multi-core Parallelism
  - Prime Sieve (algorithmic throughput)
  - AES Cryptographic Hashing (SHA-256 throughput)
  - Data Compression (zlib throughput)
  - FFT Signal Processing
  - Matrix Multiplication (GFLOPS)
  - Sorting (algorithmic)
  - Memory Bandwidth (CPU side)
  - Extended tests: AES-256, Monte Carlo Pi, N-Queens, Fibonacci, POPCNT, CRC32, MT19937 RNG, Mandelbrot, JSON, String Processing
"""

import time
import math
import hashlib
import zlib
import struct
import json
import random
import string
import secrets
import multiprocessing
import threading
import numpy as np
from typing import Callable, Optional

# ─────────────────────────────────────────────
#  WORKER FUNCTIONS (must be at module level)
# ─────────────────────────────────────────────

def _worker_integer(duration: float) -> int:
    end_time = time.perf_counter() + duration
    count = 0
    a, b = 123456789, 987654321
    while time.perf_counter() < end_time:
        a = (a ^ b) & 0xFFFFFFFF
        b = (b + a) & 0xFFFFFFFF
        a = (a * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFF
        b = (b >> 3) | ((b & 0x7) << 29)
        a = a ^ (b << 5)
        b = (b - a) & 0xFFFFFFFF
        a = (a + 0xDEADBEEF) & 0xFFFFFFFF
        b = b ^ (a >> 2)
        a = ~a & 0xFFFFFFFF
        b = (b << 1 | b >> 31) & 0xFFFFFFFF
        a = (a // (b if b else 1)) + b
        b = (a * 31337) & 0xFFFFFFFF
        a = a ^ 0xCAFEBABE
        b = (b + a) & 0xFFFFFFFF
        a = (a >> 7) ^ b
        b = (b + 1) & 0xFFFFFFFF
        a = a * 3
        b = b ^ a
        a = (a + b) & 0xFFFFFFFF
        b = (b - 1) & 0xFFFFFFFF
        count += 20
    return count

def _worker_prime_sieve(limit: int) -> int:
    sieve = bytearray([1]) * (limit + 1)
    sieve[0] = sieve[1] = 0
    for i in range(2, int(limit ** 0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = bytearray(len(sieve[i*i::i]))
    return sum(sieve)

def _worker_sha256(duration: float) -> tuple:
    end_time = time.perf_counter() + duration
    count = 0
    data = b"SYSTEM VITALBenchmarkPayload" * 64
    total_bytes = 0
    while time.perf_counter() < end_time:
        hashlib.sha256(data).digest()
        count += 1
        total_bytes += len(data)
    return count, total_bytes

def _worker_compression(duration: float) -> tuple:
    end_time = time.perf_counter() + duration
    rng = np.random.default_rng(42)
    data = bytes(rng.integers(0, 256, 65536, dtype=np.uint8).tolist())
    count = 0
    total_bytes = 0
    while time.perf_counter() < end_time:
        compressed = zlib.compress(data, level=6)
        zlib.decompress(compressed)
        count += 1
        total_bytes += len(data) * 2
    return count, total_bytes

def _worker_fft(n_samples: int, iterations: int) -> float:
    rng = np.random.default_rng(seed=0)
    signal = rng.standard_normal(n_samples).astype(np.float64)
    start = time.perf_counter()
    for _ in range(iterations):
        spectrum = np.fft.fft(signal)
        signal = np.fft.ifft(spectrum).real
    elapsed = time.perf_counter() - start
    flops_per_fft = 5 * n_samples * math.log2(n_samples)
    total_flops = flops_per_fft * iterations * 2
    return total_flops / elapsed / 1e6

def _worker_matmul(size: int, iterations: int) -> float:
    rng = np.random.default_rng(seed=1)
    A = rng.standard_normal((size, size)).astype(np.float64)
    B = rng.standard_normal((size, size)).astype(np.float64)
    _ = np.dot(A, B)
    start = time.perf_counter()
    for _ in range(iterations):
        C = np.dot(A, B)
    elapsed = time.perf_counter() - start
    flops = 2 * (size ** 3) * iterations
    return flops / elapsed / 1e9

def _multicore_worker(args) -> int:
    duration, seed = args
    end_time = time.perf_counter() + duration
    count = 0
    a = seed
    b = seed ^ 0xDEADBEEF
    while time.perf_counter() < end_time:
        a = (a ^ b) & 0xFFFFFFFF
        b = (b + a) & 0xFFFFFFFF
        a = (a * 6364136223846793005 + 1) & 0xFFFFFFFF
        b = (b >> 3) | ((b & 0x7) << 29)
        count += 4
    return count

def _aes_worker(args: tuple) -> tuple:
    duration, seed = args
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
        return bytearray([
            s[0],  s[5],  s[10], s[15],
            s[4],  s[9],  s[14], s[3],
            s[8],  s[13], s[2],  s[7],
            s[12], s[1],  s[6],  s[11],
        ])

    def xtime(a: int) -> int:
        return (((a << 1) ^ 0x1B) & 0xFF) if (a & 0x80) else (a << 1)

    def mix_column(col: list) -> list:
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
            mc  = mix_column(col)
            for r in range(4):
                result[c*4+r] = mc[r]
        return result

    def add_round_key(state: bytearray, rk: bytes) -> bytearray:
        return bytearray(a ^ b for a, b in zip(state, rk))

    def expand_key(key: bytes) -> list:
        RCON = [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]
        w    = list(key)
        for i in range(8, 60):
            temp = w[(i-1)*4 : i*4]
            if i % 8 == 0:
                temp = [SBOX[temp[1]] ^ RCON[i//8-1], SBOX[temp[2]], SBOX[temp[3]], SBOX[temp[0]]]
            elif i % 8 == 4:
                temp = [SBOX[b] for b in temp]
            word = [w[(i-8)*4+j] ^ temp[j] for j in range(4)]
            w.extend(word)
        return [bytes(w[i:i+16]) for i in range(0, 15*16, 16)]

    def aes256_encrypt_block(block: bytes, round_keys: list) -> bytes:
        state = bytearray(block)
        state = add_round_key(state, round_keys[0])
        for rnd in range(1, 14):
            state = sub_bytes(state)
            state = shift_rows(state)
            state = mix_columns(state)
            state = add_round_key(state, round_keys[rnd])
        state = sub_bytes(state)
        state = shift_rows(state)
        state = add_round_key(state, round_keys[14])
        return bytes(state)

    rng       = random.Random(seed)
    key       = bytes(rng.getrandbits(8) for _ in range(32))
    plaintext = bytes(rng.getrandbits(8) for _ in range(16))
    rk        = expand_key(key)

    count       = 0
    total_bytes = 0
    end_time    = time.perf_counter() + duration

    while time.perf_counter() < end_time:
        for _ in range(64):
            plaintext = aes256_encrypt_block(plaintext, rk)
        count       += 64
        total_bytes += 64 * 16

    return count, total_bytes

def _monte_carlo_worker(args: tuple) -> int:
    n_samples, seed = args
    rng    = np.random.default_rng(seed)
    x      = rng.uniform(0, 1, n_samples)
    y      = rng.uniform(0, 1, n_samples)
    inside = int(np.sum(x*x + y*y <= 1.0))
    return inside

def _nqueens_worker(n: int) -> int:
    cols      = set()
    diag1     = set()
    diag2     = set()
    solutions = [0]

    def backtrack(row: int):
        if row == n:
            solutions[0] += 1
            return
        for col in range(n):
            if col in cols or (row - col) in diag1 or (row + col) in diag2:
                continue
            cols.add(col);       diag1.add(row - col); diag2.add(row + col)
            backtrack(row + 1)
            cols.discard(col);   diag1.discard(row - col); diag2.discard(row + col)

    backtrack(0)
    return solutions[0]

def _crc32_worker(duration: float) -> tuple:
    rng         = np.random.default_rng(42)
    chunk       = bytes(rng.integers(0, 256, 65536, dtype=np.uint8).tolist())
    count       = 0
    total_bytes = 0
    end_time    = time.perf_counter() + duration
    prev_crc    = 0
    while time.perf_counter() < end_time:
        prev_crc     = zlib.crc32(chunk, prev_crc) & 0xFFFFFFFF
        count       += 1
        total_bytes += len(chunk)
    return count, total_bytes

def _popcnt_worker(duration: float) -> int:
    end_time = time.perf_counter() + duration
    count    = 0
    val      = 0xDEADBEEFCAFEBABE
    while time.perf_counter() < end_time:
        count += bin(val).count('1')
        count += bin(val ^ 0xFFFFFFFFFFFFFFFF).count('1')
        count += bin(val & 0x0F0F0F0F0F0F0F0F).count('1')
        count += bin(val | 0xF0F0F0F0F0F0F0F0).count('1')
        count += bin(val >> 4).count('1')
        count += bin(val << 4 & 0xFFFFFFFFFFFFFFFF).count('1')
        count += bin(val ^ (val >> 1)).count('1')
        count += bin(val ^ (val << 1)).count('1')
        val    = val ^ (val << 3) ^ 0xABCDEF1234567890
        val   &= 0xFFFFFFFFFFFFFFFF
    return count

def _rng_worker(duration: float) -> tuple:
    rng         = np.random.default_rng(seed=12345)
    BATCH       = 100_000
    count       = 0
    total_bytes = 0
    end_time    = time.perf_counter() + duration
    while time.perf_counter() < end_time:
        arr          = rng.integers(0, 2**63, BATCH, dtype=np.int64)
        count       += BATCH
        total_bytes += BATCH * 8
    return count, total_bytes

def _mandelbrot_cpu_worker(width: int, height: int, max_iter: int) -> np.ndarray:
    x     = np.linspace(-2.5, 1.0, width,  dtype=np.float64)
    y     = np.linspace(-1.25, 1.25, height, dtype=np.float64)
    C     = x[np.newaxis, :] + 1j * y[:, np.newaxis]
    Z     = np.zeros_like(C)
    M     = np.zeros(C.shape, dtype=np.int32)
    mask  = np.ones(C.shape, dtype=bool)

    for i in range(max_iter):
        Z[mask]  = Z[mask] ** 2 + C[mask]
        escaped  = mask & (np.abs(Z) > 2.0)
        M[escaped] = i
        mask[escaped] = False

    return M


# ─────────────────────────────────────────────
#  MAIN BENCHMARK CLASS
# ─────────────────────────────────────────────

class CPUBenchmark:
    """
    Industry-grade CPU benchmark suite.
    Each test is isolated, threaded, and produces
    a standardized score on a 0–100,000 scale.
    Combines both basic and extended tests.
    """

    DURATION      = 5.0   # seconds per test
    PRIME_LIMIT   = 5_000_000
    FFT_SAMPLES   = 65536
    FFT_ITERS     = 200
    MATMUL_SIZE   = 512
    MATMUL_ITERS  = 20
    
    # Extended config
    MONTE_SAMPLES = 50_000_000
    NQUEENS_N     = 14
    MANDEL_W      = 1920
    MANDEL_H      = 1080
    MANDEL_ITERS  = 256

    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_cb = progress_callback or (lambda msg, pct: None)
        self.results     = {}
        self.core_count  = multiprocessing.cpu_count()

    # ── BASIC TESTS ──────────────────────────────

    def test_integer_singlecore(self) -> dict:
        self.progress_cb("CPU: Integer Single-Core...", 2)
        ops = _worker_integer(self.DURATION)
        score = self._normalize(ops / self.DURATION, 0, 3_000_000_000)
        return {
            "name":        "Integer Performance (Single-Core)",
            "value":       round(ops / self.DURATION / 1e6, 2),
            "unit":        "MIPS",
            "raw":         ops,
            "score":       score,
            "description": "Pure integer arithmetic operations per second on one core."
        }

    def test_integer_multicore(self) -> dict:
        self.progress_cb("CPU: Integer Multi-Core...", 8)
        args = [(self.DURATION, i * 31337) for i in range(self.core_count)]
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(processes=self.core_count) as pool:
            counts = pool.map(_multicore_worker, args)
        total_ops  = sum(counts)
        total_mips = total_ops / self.DURATION / 1e6
        score      = self._normalize(total_mips, 0, 3_000_000_000 * self.core_count / 1e6)
        return {
            "name":        f"Integer Performance (Multi-Core ×{self.core_count})",
            "value":       round(total_mips, 2),
            "unit":        "MIPS",
            "raw":         total_ops,
            "score":       score,
            "description": f"Parallel integer workload across all {self.core_count} logical cores."
        }

    def test_prime_sieve(self) -> dict:
        self.progress_cb("CPU: Prime Sieve...", 14)
        start = time.perf_counter()
        prime_count = _worker_prime_sieve(self.PRIME_LIMIT)
        elapsed     = time.perf_counter() - start
        throughput  = self.PRIME_LIMIT / elapsed / 1e6  # M numbers/sec
        score       = self._normalize(throughput, 0, 500)
        return {
            "name":        "Prime Sieve (Algorithmic Throughput)",
            "value":       round(throughput, 2),
            "unit":        "M numbers/sec",
            "raw":         prime_count,
            "score":       score,
            "description": f"Sieve of Eratosthenes on {self.PRIME_LIMIT:,} numbers. Found {prime_count:,} primes."
        }

    def test_sha256(self) -> dict:
        self.progress_cb("CPU: SHA-256 Cryptographic Throughput...", 18)
        count, total_bytes = _worker_sha256(self.DURATION)
        throughput_mbps    = total_bytes / self.DURATION / 1e6
        score              = self._normalize(count / self.DURATION, 0, 500_000)
        return {
            "name":        "SHA-256 Cryptographic Throughput",
            "value":       round(throughput_mbps, 2),
            "unit":        "MB/s",
            "raw":         count,
            "score":       score,
            "description": f"SHA-256 hashing speed ({count:,} hashes in {self.DURATION:.0f}s)."
        }

    def test_compression(self) -> dict:
        self.progress_cb("CPU: Compression Throughput...", 24)
        count, total_bytes = _worker_compression(self.DURATION)
        throughput_mbps    = total_bytes / self.DURATION / 1e6
        score              = self._normalize(throughput_mbps, 0, 5000)
        return {
            "name":        "zlib Compression Throughput",
            "value":       round(throughput_mbps, 2),
            "unit":        "MB/s",
            "raw":         count,
            "score":       score,
            "description": f"zlib compress+decompress cycles ({count:,} in {self.DURATION:.0f}s)."
        }

    def test_fft(self) -> dict:
        self.progress_cb("CPU: FFT Signal Processing (MFLOPS)...", 28)
        mflops = _worker_fft(self.FFT_SAMPLES, self.FFT_ITERS)
        score  = self._normalize(mflops, 0, 50_000)
        return {
            "name":        "FFT Signal Processing",
            "value":       round(mflops, 2),
            "unit":        "MFLOPS",
            "raw":         mflops,
            "score":       score,
            "description": f"Forward+inverse FFT on {self.FFT_SAMPLES:,}-sample signal × {self.FFT_ITERS} iterations."
        }

    def test_matrix_multiply(self) -> dict:
        self.progress_cb("CPU: Matrix Multiplication (GFLOPS)...", 34)
        gflops = _worker_matmul(self.MATMUL_SIZE, self.MATMUL_ITERS)
        score  = self._normalize(gflops, 0, 500)
        return {
            "name":        "Matrix Multiplication (GEMM)",
            "value":       round(gflops, 4),
            "unit":        "GFLOPS",
            "raw":         gflops,
            "score":       score,
            "description": (
                f"{self.MATMUL_SIZE}×{self.MATMUL_SIZE} double-precision matrix multiply "
                f"× {self.MATMUL_ITERS} iterations (numpy BLAS backend)."
            )
        }

    def test_sorting(self) -> dict:
        self.progress_cb("CPU: Sorting Algorithm...", 40)
        SIZE  = 5_000_000
        rng   = np.random.default_rng(seed=99)
        data  = rng.integers(0, 2**31, SIZE, dtype=np.int64)
        start = time.perf_counter()
        data.sort()
        elapsed = time.perf_counter() - start
        throughput = SIZE / elapsed / 1e6  # M elements/sec
        score = self._normalize(throughput, 0, 1000)
        return {
            "name":        "Sort Throughput",
            "value":       round(throughput, 2),
            "unit":        "M elements/sec",
            "raw":         SIZE,
            "score":       score,
            "description": f"NumPy introsort on {SIZE:,} 64-bit integers. Elapsed: {elapsed*1000:.1f}ms."
        }

    # ── EXTENDED TESTS ─────────────────────────────

    def test_aes256_throughput(self) -> dict:
        self.progress_cb("CPU: AES-256 Encryption Throughput...", 46)

        args = [(self.DURATION, i * 31337) for i in range(self.core_count)]
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(self.core_count) as pool:
            results_mp = pool.map(_aes_worker, args)

        total_count = sum(r[0] for r in results_mp)
        total_bytes = sum(r[1] for r in results_mp)
        throughput_mbs = total_bytes / self.DURATION / 1e6
        blocks_per_sec = total_count / self.DURATION

        sc_count, sc_bytes = _aes_worker((self.DURATION, 0))
        sc_mbs = sc_bytes / self.DURATION / 1e6

        score = self._normalize(sc_mbs, 0, 500)

        return {
            "name":             "AES-256 Encryption",
            "value":            round(sc_mbs, 3),
            "unit":             "MB/s (single-core)",
            "multicore_mbs":    round(throughput_mbs, 3),
            "blocks_per_sec":   round(blocks_per_sec, 0),
            "raw":              total_count,
            "score":            score,
            "description": (
                f"Single-core: {sc_mbs:.2f} MB/s | "
                f"Multi-core ({self.core_count}T): {throughput_mbs:.2f} MB/s. "
            )
        }

    def test_monte_carlo_pi(self) -> dict:
        self.progress_cb("CPU: Monte Carlo Pi (FP64 Stress)...", 52)

        samples_per_core = self.MONTE_SAMPLES // self.core_count
        seeds            = [i * 99991 + 1 for i in range(self.core_count)]
        args             = [(samples_per_core, s) for s in seeds]

        start = time.perf_counter()
        ctx = multiprocessing.get_context('spawn')
        with ctx.Pool(self.core_count) as pool:
            inside_counts = pool.map(_monte_carlo_worker, args)
        elapsed = time.perf_counter() - start

        total_inside = sum(inside_counts)
        total_samples = samples_per_core * self.core_count
        pi_estimate  = 4.0 * total_inside / total_samples
        error_ppm    = abs(pi_estimate - math.pi) / math.pi * 1e6
        throughput   = total_samples / elapsed / 1e6

        score = self._normalize(throughput, 0, 2000)

        return {
            "name":           "Monte Carlo π Estimation",
            "value":          round(throughput, 2),
            "unit":           "M samples/sec",
            "raw":            total_inside,
            "score":          score,
            "description": (
                f"{total_samples:,} samples. "
                f"π ≈ {pi_estimate:.8f} (error: {error_ppm:.2f} ppm)."
            )
        }

    def test_nqueens(self) -> dict:
        self.progress_cb("CPU: N-Queens Backtracking Solver...", 58)

        start     = time.perf_counter()
        solutions = _nqueens_worker(self.NQUEENS_N)
        elapsed   = time.perf_counter() - start

        score = self._normalize(1 / elapsed, 0, 20)

        return {
            "name":          f"N-Queens Solver (N={self.NQUEENS_N})",
            "value":         round(elapsed * 1000, 2),
            "unit":          "ms (lower is better)",
            "score":         self._normalize(1 / max(elapsed, 0.001), 0, 20),
            "raw":           solutions,
            "description": (
                f"Found {solutions:,} solutions in {elapsed*1000:.2f}ms."
            )
        }

    def test_fibonacci_branch_prediction(self) -> dict:
        self.progress_cb("CPU: Fibonacci Branch Prediction Test...", 64)

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

        N          = 35
        ITERS_ITER = 50_000
        ITERS_MEMO = 50_000

        start = time.perf_counter()
        for _ in range(ITERS_ITER):
            result = fib_iterative(N)
        iter_time = time.perf_counter() - start
        iter_ops  = ITERS_ITER / iter_time

        fib_memo(N)  # warm up
        start = time.perf_counter()
        for _ in range(ITERS_MEMO):
            fib_memo.cache_clear()
            result = fib_memo(N)
        memo_time = time.perf_counter() - start
        memo_ops  = ITERS_MEMO / memo_time

        score = self._normalize(iter_ops, 0, 5_000_000)

        return {
            "name":             "Fibonacci: Iterative vs Memoized",
            "value":            round(iter_ops / 1000, 2),
            "unit":             "K ops/sec",
            "raw":              ITERS_ITER,
            "score":            score,
            "description": (
                f"Iterative: {iter_ops/1000:.1f}K ops/s | "
                f"Memoized: {memo_ops/1000:.1f}K ops/s."
            )
        }

    def test_popcnt_throughput(self) -> dict:
        self.progress_cb("CPU: POPCNT Instruction Throughput...", 70)

        count   = _popcnt_worker(self.DURATION)
        rate_m  = count / self.DURATION / 1e6
        score   = self._normalize(rate_m, 0, 5000)

        return {
            "name":          "POPCNT Bitwise Instruction Throughput",
            "value":         round(rate_m, 2),
            "unit":          "M POPCNT/sec",
            "raw":           count,
            "score":         score,
            "description": (
                f"{count/1e9:.3f}B ops in {self.DURATION:.0f}s."
            )
        }

    def test_crc32_throughput(self) -> dict:
        self.progress_cb("CPU: CRC32 Checksum Throughput...", 76)

        count_c, bytes_c = _crc32_worker(self.DURATION)
        throughput_c     = bytes_c / self.DURATION / 1e6
        score            = self._normalize(throughput_c, 0, 50_000)

        return {
            "name":             "CRC32 Checksum Throughput",
            "value":            round(throughput_c, 2),
            "unit":             "MB/s",
            "raw":              count_c,
            "score":            score,
            "description":      f"C-accelerated: {throughput_c:.1f} MB/s."
        }

    def test_rng_throughput(self) -> dict:
        self.progress_cb("CPU: Mersenne Twister RNG Throughput...", 82)

        count, total_bytes = _rng_worker(self.DURATION)
        throughput_mbs     = total_bytes / self.DURATION / 1e6
        throughput_mn      = count / self.DURATION / 1e6

        score = self._normalize(throughput_mn, 0, 5000)

        return {
            "name":          "Mersenne Twister RNG Throughput",
            "value":         round(throughput_mn, 2),
            "unit":          "M numbers/sec",
            "raw":           count,
            "score":         score,
            "description": (
                f"{throughput_mn:.1f}M numbers/sec = {throughput_mbs:.1f} MB/s."
            )
        }

    def test_cpu_mandelbrot_fp64(self) -> dict:
        self.progress_cb("CPU: Mandelbrot FP64 (1080p CPU Render)...", 88)

        start  = time.perf_counter()
        M      = _mandelbrot_cpu_worker(self.MANDEL_W, self.MANDEL_H, self.MANDEL_ITERS)
        elapsed = time.perf_counter() - start

        total_pixels = self.MANDEL_W * self.MANDEL_H
        mpixels_sec  = total_pixels / elapsed / 1e6

        score = self._normalize(mpixels_sec, 0, 500)

        return {
            "name":          f"CPU Mandelbrot FP64",
            "value":         round(mpixels_sec, 3),
            "unit":          "Mpixels/sec",
            "raw":           total_pixels,
            "score":         score,
            "description": (
                f"{self.MANDEL_W}×{self.MANDEL_H} rendered "
                f"in {elapsed*1000:.1f}ms."
            )
        }

    def test_json_throughput(self) -> dict:
        self.progress_cb("CPU: JSON Serialize/Deserialize Throughput...", 94)

        rng     = np.random.default_rng(seed=55)
        payload = {"user_id": 123456789, "active": True, "scores": [int(rng.integers(1000, 99999)) for _ in range(50)]}

        ser_count    = 0
        start        = time.perf_counter()
        deadline     = start + self.DURATION / 2

        while time.perf_counter() < deadline:
            s = json.dumps(payload, separators=(',', ':'))
            ser_count += 1

        ser_ops     = ser_count / (time.perf_counter() - start)

        json_str  = json.dumps(payload)
        des_count = 0
        start     = time.perf_counter()
        deadline  = start + self.DURATION / 2

        while time.perf_counter() < deadline:
            _ = json.loads(json_str)
            des_count += 1

        des_ops     = des_count / (time.perf_counter() - start)

        score = self._normalize((ser_ops + des_ops) / 2, 0, 100_000)

        return {
            "name":         "JSON Serialize / Deserialize",
            "value":        round(ser_ops, 0),
            "unit":         "ops/sec",
            "raw":          ser_count + des_count,
            "score":        score,
            "description": (
                f"Serialize: {ser_ops:.0f} ops/s | Deserialize: {des_ops:.0f} ops/s."
            )
        }

    def test_string_processing(self) -> dict:
        self.progress_cb("CPU: String Processing Throughput...", 98)
        import re

        text = "SYSTEM VITAL benchmark performance cpu memory latency " * 200
        pattern = re.compile(r'\b(cpu|memory)\b', re.IGNORECASE)

        find_count  = 0
        start       = time.perf_counter()
        deadline    = start + self.DURATION
        while time.perf_counter() < deadline:
            matches = pattern.findall(text)
            find_count += 1
            
        find_ops     = find_count / (time.perf_counter() - start)
        score   = self._normalize(find_ops, 0, 50_000)

        return {
            "name":         "String Processing Throughput",
            "value":        round(find_ops, 2),
            "unit":         "ops/sec",
            "raw":          find_count,
            "score":        score,
            "description": (
                f"Regex find: {find_ops:.0f}/s."
            )
        }

    # ── RUN ALL ───────────────────────────────

    def run_all(self) -> dict:
        """Run all CPU tests and return consolidated results."""
        tests = [
            # Basic tests
            self.test_integer_singlecore,
            self.test_integer_multicore,
            self.test_prime_sieve,
            self.test_sha256,
            self.test_compression,
            self.test_fft,
            self.test_matrix_multiply,
            self.test_sorting,
            # Extended tests
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
        for test_fn in tests:
            try:
                result = test_fn()
                results.append(result)
            except Exception as e:
                results.append({
                    "name":  test_fn.__name__,
                    "error": str(e),
                    "score": 0
                })

        overall_score = int(np.mean([r.get("score", 0) for r in results]))
        self.progress_cb("CPU Benchmark Complete!", 100)

        return {
            "component":     "CPU",
            "overall_score": overall_score,
            "grade":         self._grade(overall_score),
            "tier":          self._tier(overall_score),
            "tests":         results,
            "core_count":    self.core_count,
        }

    # ── HELPERS ───────────────────────────────

    @staticmethod
    def _normalize(value: float, low: float, high: float,
                   out_min: int = 0, out_max: int = 100_000) -> int:
        """Map raw value to 0–100,000 score scale."""
        if high == low:
            return out_min
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
