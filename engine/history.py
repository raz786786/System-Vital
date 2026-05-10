"""
SYSTEM VITAL BENCHMARK HISTORY ENGINE (Upgraded)
Full SQLite-backed benchmark history with:
  - Baseline management
  - Degradation tracking
  - Run comparison
  - Statistical analysis over time
"""

import os
import json
import sqlite3
import datetime
import config
import numpy as np
from typing import Optional, List, Dict, Any

DB_PATH = config.DATABASE_PATH


class BenchmarkHistory:

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    # ── SCHEMA ────────────────────────────────────────────────

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date     TEXT    NOT NULL,
                    component    TEXT    NOT NULL,
                    overall_score INTEGER,
                    grade        TEXT,
                    tier         TEXT,
                    is_baseline  INTEGER DEFAULT 0,
                    notes        TEXT,
                    full_json    TEXT
                );

                CREATE TABLE IF NOT EXISTS baselines (
                    component    TEXT    PRIMARY KEY,
                    run_id       INTEGER,
                    overall_score INTEGER,
                    grade        TEXT,
                    tier         TEXT,
                    set_date     TEXT,
                    system_info  TEXT
                );

                CREATE TABLE IF NOT EXISTS system_snapshots (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    snap_date    TEXT    NOT NULL,
                    cpu_name     TEXT,
                    gpu_name     TEXT,
                    ram_gb       REAL,
                    os_version   TEXT,
                    snapshot_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_runs_component
                    ON runs(component);
                CREATE INDEX IF NOT EXISTS idx_runs_date
                    ON runs(run_date);
            """)
            
            # Migration: Ensure columns exist (for older DB versions)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(runs)")
            columns = [info[1] for info in cursor.fetchall()]
            
            if "overall_score" not in columns:
                conn.execute("ALTER TABLE runs ADD COLUMN overall_score INTEGER")
            if "grade" not in columns:
                conn.execute("ALTER TABLE runs ADD COLUMN grade TEXT")
            if "tier" not in columns:
                conn.execute("ALTER TABLE runs ADD COLUMN tier TEXT")
            if "full_json" not in columns:
                conn.execute("ALTER TABLE runs ADD COLUMN full_json TEXT")

    # ── SAVE RUN ──────────────────────────────────────────────

    def save_run(self, result: dict,
                 notes: str = "",
                 auto_baseline: bool = True) -> int:
        """
        Save a benchmark run result.
        Auto-sets as baseline if none exists for this component.
        Returns the new run ID.
        """
        comp    = result.get("component", "UNKNOWN")
        score   = result.get("overall_score", 0)
        grade   = result.get("grade", "?")
        tier    = result.get("tier", "?")
        ts      = datetime.datetime.now().isoformat()
        js      = json.dumps(result, default=str)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO runs
                   (run_date, component, overall_score, grade, tier, notes, full_json)
                   VALUES (?,?,?,?,?,?,?)""",
                (ts, comp, score, grade, tier, notes, js)
            )
            run_id = cur.lastrowid

        # Auto-set baseline if this is the first run
        if auto_baseline and not self.get_baseline(comp):
            self.set_baseline(comp, run_id)

        return run_id

    # ── BASELINE MANAGEMENT ───────────────────────────────────

    def set_baseline(self, component: str, run_id: int):
        """Set a specific run as the baseline for a component."""
        run = self.get_run(run_id)
        if not run:
            return

        ts = datetime.datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO baselines
                    (component, run_id, overall_score, grade, tier, set_date)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(component) DO UPDATE SET
                    run_id        = excluded.run_id,
                    overall_score = excluded.overall_score,
                    grade         = excluded.grade,
                    tier          = excluded.tier,
                    set_date      = excluded.set_date
            """, (
                component,
                run_id,
                run.get("overall_score", 0),
                run.get("grade", "?"),
                run.get("tier", "?"),
                ts,
            ))
            # Mark the run
            conn.execute(
                "UPDATE runs SET is_baseline=1 WHERE id=?", (run_id,)
            )
            # Unmark all others
            conn.execute(
                "UPDATE runs SET is_baseline=0 "
                "WHERE component=? AND id!=?",
                (component, run_id)
            )

    def get_baseline(self, component: str) -> Optional[dict]:
        """Retrieve the baseline for a component."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT run_id, overall_score, grade, tier, set_date
                   FROM baselines WHERE component=?""",
                (component,)
            ).fetchone()

        if not row:
            return None

        run_id, score, grade, tier, set_date = row
        full_run = self.get_run(run_id)
        return {
            "run_id":        run_id,
            "overall_score": score,
            "grade":         grade,
            "tier":          tier,
            "set_date":      set_date,
            "full_run":      full_run,
        }

    def clear_baseline(self, component: str):
        """Remove baseline for a component."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM baselines WHERE component=?", (component,)
            )
            conn.execute(
                "UPDATE runs SET is_baseline=0 WHERE component=?",
                (component,)
            )

    # ── COMPARISON ENGINE ──────────────────────────────────────

    def compare_to_baseline(self, component: str,
                             current_score: int) -> dict:
        """
        Compare current score to baseline.
        Returns detailed comparison with status and advice.
        """
        baseline = self.get_baseline(component)
        if not baseline:
            return {
                "status":  "no_baseline",
                "message": "No baseline set. This run IS the baseline.",
                "delta_pct": 0.0,
            }

        base_score = baseline["overall_score"]
        if base_score == 0:
            return {"status": "invalid_baseline", "delta_pct": 0.0}

        delta_pct = (current_score - base_score) / base_score * 100

        if delta_pct <= -15:
            status = "🔴 Critical Degradation"
            severity = "critical"
        elif delta_pct <= -5:
            status = "🟡 Minor Degradation"
            severity = "warning"
        elif delta_pct < 5:
            status = "🟢 Normal (±5% variation)"
            severity = "ok"
        elif delta_pct < 15:
            status = "🔵 Improved"
            severity = "improved"
        else:
            status = "⚡ Major Improvement"
            severity = "major_improved"

        advice = self._get_advice(component, delta_pct, severity)

        return {
            "status":         status,
            "severity":       severity,
            "baseline_score": base_score,
            "current_score":  current_score,
            "delta_pct":      round(delta_pct, 2),
            "delta_abs":      current_score - base_score,
            "baseline_date":  baseline["set_date"][:10],
            "baseline_grade": baseline["grade"],
            "advice":         advice,
        }

    @staticmethod
    def _get_advice(component: str,
                    delta_pct: float,
                    severity: str) -> str:
        if severity in ("ok", "improved", "major_improved"):
            return (
                "Performance is healthy. "
                + ("Consider setting this as the new baseline."
                   if severity == "major_improved" else "")
            )

        advice_map = {
            "CPU": {
                "warning": (
                    "CPU performance dropped. Check: "
                    "1) Thermal throttling (CPU > 90°C) "
                    "2) Power plan set to Balanced "
                    "3) Background apps consuming cores "
                    "4) Windows Update running in background."
                ),
                "critical": (
                    "CRITICAL CPU drop. Likely causes: "
                    "severe thermal throttling, failing CPU, "
                    "BIOS settings reset, or hardware degradation. "
                    "Run thermal test and check Event Viewer for errors."
                ),
            },
            "GPU": {
                "warning": (
                    "GPU performance dropped. Check: "
                    "1) GPU temperature (>83°C = throttle) "
                    "2) Driver regression (roll back GPU driver) "
                    "3) Power limit reduced in GPU software "
                    "4) VRAM pressure from background apps."
                ),
                "critical": (
                    "CRITICAL GPU drop. Check: "
                    "PCIe slot seating, GPU power connectors, "
                    "driver corruption (DDU reinstall), "
                    "or possible GPU hardware failure."
                ),
            },
            "RAM": {
                "warning": (
                    "RAM bandwidth dropped. Check: "
                    "1) XMP/EXPO profile disabled after BIOS update "
                    "2) Memory running at JEDEC speeds (not rated speed) "
                    "3) Single-channel mode (one stick loose/failed) "
                    "4) Memory-intensive background services."
                ),
                "critical": (
                    "CRITICAL RAM drop. Possible RAM stick failure. "
                    "Run MemTest86 immediately. Check BIOS memory settings. "
                    "Re-seat RAM modules."
                ),
            },
            "SSD": {
                "warning": (
                    "SSD speed dropped. Check: "
                    "1) Drive near full (keep >10% free) "
                    "2) TRIM not running (fsutil behavior query DisableDeleteNotify) "
                    "3) NVMe thermal throttle (>70°C) "
                    "4) SLC cache exhausted on QLC drive."
                ),
                "critical": (
                    "CRITICAL SSD drop. Possible SSD wear or failure. "
                    "Check S.M.A.R.T. data. Back up immediately. "
                    "Run CHKDSK. Check NVMe temperature."
                ),
            },
            "HDD": {
                "warning": (
                    "HDD performance dropped. Check: "
                    "1) Fragmentation (run Defrag) "
                    "2) Drive filling up "
                    "3) SMART errors (impending failure) "
                    "4) Power management parking heads aggressively."
                ),
                "critical": (
                    "CRITICAL HDD degradation. Immediate backup recommended. "
                    "Check SMART attributes for reallocated sectors. "
                    "Drive may be failing."
                ),
            },
            "System": {
                "warning":  "System performance degraded. Run individual component tests.",
                "critical": "Critical system degradation. Full diagnostic recommended.",
            },
        }

        comp_advice = advice_map.get(component.split("_")[0], {})
        return comp_advice.get(severity, "Performance degraded. Run diagnostics.")

    # ── HISTORY RETRIEVAL ──────────────────────────────────────

    def get_history(self, component: str,
                    limit: int = 50) -> List[dict]:
        """Get run history for a component, newest first."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT id, run_date, overall_score, grade, tier, is_baseline
                   FROM runs
                   WHERE component=?
                   ORDER BY run_date DESC
                   LIMIT ?""",
                (component, limit)
            ).fetchall()

        return [
            {
                "id":          r[0],
                "date":        r[1][:19].replace("T", " "),
                "score":       r[2],
                "grade":       r[3],
                "tier":        r[4],
                "is_baseline": bool(r[5]),
            }
            for r in rows
        ]

    def get_run(self, run_id: int) -> Optional[dict]:
        """Get full run data by ID."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT full_json FROM runs WHERE id=?", (run_id,)
            ).fetchone()
        if row and row[0]:
            try:
                return json.loads(row[0])
            except Exception:
                return None
        return None

    def get_all_components(self) -> List[str]:
        """List all components that have history."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT DISTINCT component FROM runs ORDER BY component"
            ).fetchall()
        return [r[0] for r in rows]

    def get_trend_data(self, component: str,
                       n_runs: int = 20) -> dict:
        """
        Compute trend analysis for a component.
        Returns: slope (improving/degrading), moving average,
                 best/worst scores, variance.
        """
        history = self.get_history(component, limit=n_runs)
        if len(history) < 2:
            return {"insufficient_data": True}

        scores = [h["score"] for h in reversed(history)]
        dates  = [h["date"]  for h in reversed(history)]

        scores_arr = np.array(scores, dtype=np.float64)
        x          = np.arange(len(scores_arr))

        # Linear regression for trend
        if len(x) > 1:
            coeffs    = np.polyfit(x, scores_arr, 1)
            slope     = float(coeffs[0])
            intercept = float(coeffs[1])
            trend_dir = (
                "📈 Improving" if slope > 100
                else "📉 Degrading" if slope < -100
                else "➡️ Stable"
            )
        else:
            slope = 0; trend_dir = "➡️ Stable"

        return {
            "component":    component,
            "n_runs":       len(scores),
            "scores":       scores,
            "dates":        dates,
            "best_score":   int(max(scores_arr)),
            "worst_score":  int(min(scores_arr)),
            "avg_score":    int(np.mean(scores_arr)),
            "std_score":    int(np.std(scores_arr)),
            "slope":        round(slope, 2),
            "trend":        trend_dir,
            "first_date":   dates[0],
            "last_date":    dates[-1],
        }

    def delete_run(self, run_id: int):
        """Delete a specific run."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM runs WHERE id=?", (run_id,))

    def clear_all_history(self, component: str = None):
        """Clear history. If component given, only that component."""
        with sqlite3.connect(self.db_path) as conn:
            if component:
                conn.execute(
                    "DELETE FROM runs WHERE component=?", (component,)
                )
                conn.execute(
                    "DELETE FROM baselines WHERE component=?", (component,)
                )
            else:
                conn.execute("DELETE FROM runs")
                conn.execute("DELETE FROM baselines")

    def get_statistics(self) -> dict:
        """Get overall database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_runs = conn.execute(
                "SELECT COUNT(*) FROM runs"
            ).fetchone()[0]
            components = conn.execute(
                "SELECT component, COUNT(*), MAX(run_date) "
                "FROM runs GROUP BY component"
            ).fetchall()
            baselines_set = conn.execute(
                "SELECT COUNT(*) FROM baselines"
            ).fetchone()[0]

        return {
            "total_runs":    total_runs,
            "baselines_set": baselines_set,
            "db_path":       self.db_path,
            "db_size_kb":    round(os.path.getsize(self.db_path) / 1024, 1)
                             if os.path.exists(self.db_path) else 0,
            "components":    [
                {
                    "name":      r[0],
                    "run_count": r[1],
                    "last_run":  r[2][:10] if r[2] else "Never",
                }
                for r in components
            ],
        }
