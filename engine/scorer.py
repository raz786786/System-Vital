"""
SYSTEM VITAL SCORING ENGINE
Handles score normalization, calibration against
real hardware reference table, percentile ranking,
and overall system score computation.
"""

import os
import json
import math
import numpy as np
from typing import Optional

# ── Load reference data ────────────────────────────────────────
_REF_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "reference_scores.json"
)

def _load_reference() -> dict:
    try:
        with open(_REF_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

REFERENCE = _load_reference()


class ScoreNormalizer:
    """
    Converts raw benchmark values to our 0–100,000 scale
    using piecewise linear interpolation against the
    reference hardware table.
    """

    def __init__(self, component: str):
        self.component  = component.upper()
        # Some component keys map like SSD_Extended -> SSD
        base_comp = self.component.split("_")[0]
        self.ref_data   = REFERENCE.get(base_comp, {})
        self.tiers      = self.ref_data.get("tiers", {})
        self.ref_hw     = self.ref_data.get("reference_hardware", {})
        self.thresholds = self.ref_data.get(
            "grade_thresholds",
            {"S": 85000, "A": 70000, "B": 55000, "C": 40000, "D": 25000}
        )

    def normalize(self, raw_value: float,
                  low: float, high: float) -> int:
        """
        Linear normalization with clamping.
        Maps raw_value in [low, high] → [0, 100_000].
        """
        if high <= low:
            return 0
        clamped = max(low, min(high, raw_value))
        return int((clamped - low) / (high - low) * 100_000)

    def grade(self, score: int) -> str:
        if score >= self.thresholds.get("S", 85000): return "S"
        if score >= self.thresholds.get("A", 70000): return "A"
        if score >= self.thresholds.get("B", 55000): return "B"
        if score >= self.thresholds.get("C", 40000): return "C"
        if score >= self.thresholds.get("D", 25000): return "D"
        return "F"

    def tier(self, score: int) -> str:
        for tier_name, bounds in reversed(list(self.tiers.items())):
            if score >= bounds["min"]:
                examples = bounds.get("examples", [])
                ex_str   = f" ({examples[0]})" if examples else ""
                return f"{tier_name}{ex_str}"
        return "Unknown"

    def percentile_rank(self, score: int) -> float:
        """
        Estimate what percentile this score is in among
        reference hardware. 100th = best, 0th = worst.
        """
        if not self.ref_hw:
            return 50.0
        ref_scores = sorted(v.get("score", 0)
                            for v in self.ref_hw.values()
                            if isinstance(v, dict))
        if not ref_scores:
            return 50.0
        below = sum(1 for s in ref_scores if s <= score)
        return round(below / len(ref_scores) * 100, 1)

    def closest_hardware(self, score: int,
                          n: int = 3) -> list:
        """
        Find the N closest reference hardware by score.
        Returns list of (name, ref_score, delta_pct).
        """
        if not self.ref_hw:
            return []
        matches = []
        for name, data in self.ref_hw.items():
            if not isinstance(data, dict):
                continue
            ref_score = data.get("score", 0)
            delta_pct = (score - ref_score) / max(ref_score, 1) * 100
            matches.append((name, ref_score, round(delta_pct, 1)))
        matches.sort(key=lambda x: abs(x[2]))
        return matches[:n]

    def full_report(self, score: int) -> dict:
        """
        Generate a full scoring report for a component.
        """
        return {
            "score":       score,
            "grade":       self.grade(score),
            "tier":        self.tier(score),
            "percentile":  self.percentile_rank(score),
            "closest_hw":  self.closest_hardware(score),
            "thresholds":  self.thresholds,
        }


class SystemScoreAggregator:
    """
    Combines individual component scores into an
    overall system score with weighted averaging.
    """

    # Weights for overall system score
    WEIGHTS = {
        "CPU":          0.25,
        "CPU_Extended": 0.10,
        "GPU":          0.25,
        "GPU_Extended": 0.10,
        "RAM":          0.15,
        "RAM_Extended": 0.05,
        "SSD":          0.08,
        "SSD_Extended": 0.02,
        "HDD":          0.00,  # Excluded from overall (not everyone has HDD)
        "System":       0.00,  # Informational only
    }

    def __init__(self):
        self.normalizers = {
            comp: ScoreNormalizer(comp)
            for comp in self.WEIGHTS
        }

    def compute_overall(self, component_scores: dict) -> dict:
        """
        Compute weighted overall score from component scores.
        component_scores: {component_name: score_int}
        """
        total_weight  = 0.0
        weighted_sum  = 0.0
        included      = {}
        excluded      = {}

        for comp, score in component_scores.items():
            weight = self.WEIGHTS.get(comp, 0)
            if weight > 0 and score > 0:
                weighted_sum  += score * weight
                total_weight  += weight
                included[comp] = score
            else:
                excluded[comp] = score

        if total_weight == 0:
            overall = 0
        else:
            overall = int(weighted_sum / total_weight)

        norm = ScoreNormalizer("CPU")  # Use CPU thresholds for overall
        return {
            "overall_score":    overall,
            "overall_grade":    norm.grade(overall),
            "overall_tier":     self._system_tier(overall),
            "overall_percentile": norm.percentile_rank(overall),
            "included":         included,
            "excluded":         excluded,
            "weights_used":     {k: v for k, v in self.WEIGHTS.items()
                                 if k in included},
        }

    @staticmethod
    def _system_tier(score: int) -> str:
        if score >= 85_000: return "🏆 Flagship Workstation"
        if score >= 70_000: return "⚡ High-End Gaming / Creator PC"
        if score >= 55_000: return "🎮 Mid-Range Gaming PC"
        if score >= 40_000: return "💻 Entry-Level Gaming / Office PC"
        if score >= 25_000: return "🖥️ Budget / Legacy PC"
        return "⚠️ Very Old / Degraded System"
