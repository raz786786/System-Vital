"""
SYSTEM VITAL AI-POWERED DEGRADATION ANALYSIS
Integrates with Gemini/Nova to provide plain-English
explanations of performance changes.
"""

import json
from typing import Optional
from engine.ai_factory import AIFactory, BaseAIProvider

class DegradationAnalyzer:
    """
    Uses AI providers (Gemini, etc.) or rule-based logic
    to analyze performance data.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.provider = provider

    def analyze(self,
                component_results: dict,
                comparisons: dict,
                history_trends: dict) -> tuple:
        """
        Generate AI analysis of benchmark results.
        Returns (text_report, list_of_repair_ids).
        """
        repairs = self._get_suggested_repairs(comparisons)
        
        if self.provider and not isinstance(self.provider, AIFactory): # Check if provider is valid
            try:
                prompt = self._build_prompt(component_results, comparisons, history_trends)
                text = self.provider.generate_analysis(prompt)
                if text and "Error" not in text:
                    return text, repairs
            except Exception:
                pass
        
        return self._rule_based_analysis(comparisons), repairs

    def _build_prompt(self, results: dict, comparisons: dict, trends: dict) -> str:
        """Build the structured prompt for any AI provider."""
        summary = {
            comp: {
                "score":    results.get(comp, {}).get("overall_score", 0),
                "grade":    results.get(comp, {}).get("grade", "?"),
                "delta":    comparisons.get(comp, {}).get("delta_pct", 0),
                "status":   comparisons.get(comp, {}).get("status", "?"),
                "trend":    trends.get(comp, {}).get("trend", "?"),
            }
            for comp in results
        }
        
        degraded = {k: v for k, v in summary.items() if v.get("delta", 0) < -5}
        
        return f"""
        Analyze PC hardware performance:
        RESULTS: {json.dumps(summary)}
        DEGRADED: {json.dumps(degraded)}
        Provide a concise diagnosis and priority fix.
        """

    def _get_suggested_repairs(self, comparisons: dict) -> list:
        repairs = []
        for comp, cmp in comparisons.items():
            dp = cmp.get("delta_pct", 0)
            if dp < -5:
                # Mapping logic
                if "SSD" in comp or "HDD" in comp:
                    repairs.extend(["chkdsk", "sfc"])
                if "System" in comp:
                    repairs.extend(["sfc", "dism", "update_repair"])
                if "CPU" in comp or "GPU" in comp:
                    repairs.extend(["dism"])
        return list(set(repairs))

    def _ai_analysis(self,
                     results: dict,
                     comparisons: dict,
                     trends: dict) -> str:
        """Send structured summary to AI for analysis."""
        # Build compact summary (no raw data — token efficient)
        summary = {
            comp: {
                "score":    results.get(comp, {}).get("overall_score", 0),
                "grade":    results.get(comp, {}).get("grade", "?"),
                "delta":    comparisons.get(comp, {}).get("delta_pct", 0),
                "status":   comparisons.get(comp, {}).get("status", "?"),
                "trend":    trends.get(comp, {}).get("trend", "?"),
            }
            for comp in results
        }

        degraded = {
            k: v for k, v in summary.items()
            if v.get("delta", 0) < -5
        }

        prompt = f"""
You are an expert PC hardware diagnostic engineer.
Analyze this benchmark result and provide a concise,
actionable diagnosis in plain English.

CURRENT RESULTS:
{json.dumps(summary, indent=2)}

DEGRADED COMPONENTS (>5% drop from baseline):
{json.dumps(degraded, indent=2) if degraded else "None — all healthy"}

Provide:
1. Overall system health assessment (1-2 sentences)
2. For each degraded component: most likely cause + specific fix
3. Priority action item (most urgent fix)
4. Positive highlights (what's performing well)

Keep the response under 200 words. Be specific and actionable.
        """

        response = self.ai.generate_content(prompt)
        return response.text if hasattr(response, 'text') else str(response)

    @staticmethod
    def _rule_based_analysis(comparisons: dict) -> str:
        """
        Fallback rule-based analysis when no AI is available.
        """
        lines       = []
        degraded    = []
        healthy     = []
        improved    = []

        for comp, cmp in comparisons.items():
            dp = cmp.get("delta_pct", 0)
            if dp < -5:
                degraded.append((comp, dp))
            elif dp > 5:
                improved.append((comp, dp))
            else:
                healthy.append(comp)

        if not degraded:
            lines.append(
                "✅ All components are performing within normal range "
                "of your baseline. System is healthy."
            )
        else:
            lines.append(
                f"⚠️ {len(degraded)} component(s) show performance degradation:"
            )
            for comp, dp in degraded:
                lines.append(
                    f"  • {comp}: {dp:+.1f}% — "
                    + _get_quick_advice(comp, dp)
                )

        if improved:
            lines.append(
                f"\n🔵 Improved: "
                + ", ".join(f"{c} ({dp:+.1f}%)" for c, dp in improved)
            )

        if healthy:
            lines.append(
                f"\n🟢 Healthy: {', '.join(healthy)}"
            )

        return "\n".join(lines)


def _get_quick_advice(component: str, delta_pct: float) -> str:
    advice = {
        "CPU":    "Check CPU temperature and power plan.",
        "GPU":    "Check GPU temperature and driver version.",
        "RAM":    "Verify XMP/EXPO profile in BIOS.",
        "SSD":    "Check free space and TRIM status.",
        "HDD":    "Run defrag and check SMART data.",
        "System": "Run individual component tests.",
    }
    base_comp = component.split("_")[0]
    return advice.get(base_comp, "Run full diagnostics.")
