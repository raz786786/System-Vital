"""
SYSTEM VITAL REPORT EXPORTER
Generates PDF and HTML benchmark reports.
"""

import os
import json
import datetime
from typing import Optional


class ReportExporter:
    """
    Exports benchmark results to HTML and PDF formats.
    HTML is always available. PDF requires either
    weasyprint or fpdf2 (optional).
    """

    GRADE_COLORS = {
        "S": "#FFD700", "A": "#00B894", "B": "#74B9FF",
        "C": "#FDCB6E", "D": "#E17055", "F": "#D63031",
    }

    def export_html(self,
                    results: dict,
                    comparisons: dict,
                    ai_summary: str,
                    output_path: str) -> str:
        """
        Generate a self-contained HTML benchmark report.
        Returns the output path.
        """
        html = self._build_html(results, comparisons, ai_summary)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path

    def export_pdf(self,
                   results: dict,
                   comparisons: dict,
                   ai_summary: str,
                   output_path: str) -> Optional[str]:
        """
        Generate PDF report. Requires fpdf2.
        Returns path on success, None on failure.
        """
        try:
            from fpdf import FPDF
            return self._build_pdf(
                results, comparisons, ai_summary,
                output_path
            )
        except ImportError:
            # Fall back to HTML
            html_path = output_path.replace(".pdf", ".html")
            return self.export_html(
                results, comparisons, ai_summary, html_path
            )
        except Exception:
            return None

    def _build_html(self, results, comparisons, ai_summary) -> str:
        now    = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cards  = ""

        for comp, result in results.items():
            score   = result.get("overall_score", 0)
            grade   = result.get("grade", "?")
            tier    = result.get("tier", "?")
            cmp     = comparisons.get(comp, {})
            delta   = cmp.get("delta_pct", 0)
            status  = cmp.get("status", "")
            color   = self.GRADE_COLORS.get(grade, "#888")

            delta_color = (
                "#D63031" if delta < -5
                else "#FDCB6E" if delta < 0
                else "#00B894"
            )
            delta_str = f"{delta:+.1f}%" if delta != 0 else "Baseline"

            # Test rows
            test_rows = ""
            for t in result.get("tests", []):
                if "error" in t:
                    test_rows += f"""
                    <tr>
                        <td>{t.get('name','?')}</td>
                        <td style="color:#D63031">ERROR</td>
                        <td>{t.get('error','')[:50]}</td>
                        <td>0</td>
                    </tr>"""
                else:
                    val  = t.get("value", "?")
                    unit = t.get("unit", "")
                    sc   = t.get("score", 0)
                    test_rows += f"""
                    <tr>
                        <td>{t.get('name','?')}</td>
                        <td>{val}</td>
                        <td>{unit}</td>
                        <td>{sc:,}</td>
                    </tr>"""

            cards += f"""
            <div class="card">
                <div class="card-header">
                    <span class="comp-name">{comp}</span>
                    <span class="grade" style="color:{color}">{grade}</span>
                    <span class="score">{score:,}</span>
                </div>
                <div class="card-body">
                    <p class="tier">{tier}</p>
                    <p class="delta" style="color:{delta_color}">
                        vs Baseline: {delta_str}
                        &nbsp;|&nbsp; {status}
                    </p>
                    <table class="test-table">
                        <thead>
                            <tr>
                                <th>Test</th>
                                <th>Value</th>
                                <th>Unit</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>{test_rows}</tbody>
                    </table>
                </div>
            </div>"""

        ai_html = (
            f'<div class="ai-box"><h3>🤖 AI Analysis</h3>'
            f'<pre>{ai_summary}</pre></div>'
            if ai_summary else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SYSTEM VITAL Benchmark Report — {now}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
      font-family: 'Segoe UI', Consolas, monospace;
      background: #0f0f0f; color: #eaeaea;
      padding: 20px;
  }}
  h1 {{ color: #e94560; font-size: 2em; margin-bottom: 5px; }}
  .meta {{ color: #888; margin-bottom: 20px; font-size: 0.9em; }}
  .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
      gap: 16px;
  }}
  .card {{
      background: #1a1a2e; border-radius: 10px;
      border: 1px solid #333; overflow: hidden;
  }}
  .card-header {{
      background: #16213e; padding: 14px 18px;
      display: flex; align-items: center; gap: 15px;
  }}
  .comp-name {{ font-size: 1.2em; font-weight: bold; color: #74b9ff; }}
  .grade {{ font-size: 2em; font-weight: bold; }}
  .score {{ font-size: 1.5em; color: #eaeaea; margin-left: auto; }}
  .card-body {{ padding: 14px 18px; }}
  .tier {{ color: #888; font-size: 0.9em; margin-bottom: 5px; }}
  .delta {{ font-size: 0.95em; margin-bottom: 10px; }}
  .test-table {{ width: 100%; border-collapse: collapse; font-size: 0.82em; }}
  .test-table th {{
      background: #0f3460; color: #74b9ff;
      padding: 6px 8px; text-align: left;
  }}
  .test-table td {{ padding: 5px 8px; border-bottom: 1px solid #222; }}
  .test-table tr:hover {{ background: #1e2a4a; }}
  .ai-box {{
      background: #1a1a2e; border: 1px solid #e94560;
      border-radius: 10px; padding: 18px; margin-top: 16px;
  }}
  .ai-box h3 {{ color: #e94560; margin-bottom: 10px; }}
  .ai-box pre {{
      white-space: pre-wrap; font-size: 0.9em;
      color: #eaeaea; font-family: 'Segoe UI', sans-serif;
  }}
  footer {{ color: #444; font-size: 0.8em; margin-top: 20px; text-align: center; }}
</style>
</head>
<body>
  <h1>⚡ SYSTEM VITAL Benchmark Report</h1>
  <p class="meta">Generated: {now} &nbsp;|&nbsp;
     SYSTEM VITAL Benchmark Suite v1.0</p>
  <div class="grid">{cards}</div>
  {ai_html}
  <footer>SYSTEM VITAL Benchmark Suite — All rights reserved</footer>
</body>
</html>"""

    def _build_pdf(self, results, comparisons,
                   ai_summary, output_path) -> str:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Header
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(233, 69, 96)
        pdf.cell(0, 10, "SYSTEM VITAL Benchmark Report", ln=True)

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(136, 136, 136)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 6, f"Generated: {now}", ln=True)
        pdf.ln(5)

        # Component sections
        for comp, result in results.items():
            score   = result.get("overall_score", 0)
            grade   = result.get("grade", "?")
            tier    = result.get("tier", "?")
            cmp     = comparisons.get(comp, {})
            delta   = cmp.get("delta_pct", 0)

            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(116, 185, 255)
            pdf.cell(0, 8, f"{comp} — Score: {score:,}  Grade: {grade}", ln=True)

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(200, 200, 200)
            pdf.cell(0, 5, f"Tier: {tier}", ln=True)
            pdf.cell(
                0, 5,
                f"vs Baseline: {delta:+.1f}%  {cmp.get('status','')}",
                ln=True
            )
            pdf.ln(3)

            # Test results table
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(116, 185, 255)
            col_w = [90, 40, 30, 25]
            headers = ["Test Name", "Value", "Unit", "Score"]
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 6, h, border=1)
            pdf.ln()

            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(220, 220, 220)
            for t in result.get("tests", [])[:15]:
                name  = str(t.get("name", "?"))[:45]
                val   = str(t.get("value", "?"))[:15]
                unit  = str(t.get("unit", ""))[:12]
                sc    = str(t.get("score", 0))
                pdf.cell(col_w[0], 5, name,  border=1)
                pdf.cell(col_w[1], 5, val,   border=1)
                pdf.cell(col_w[2], 5, unit,  border=1)
                pdf.cell(col_w[3], 5, sc,    border=1)
                pdf.ln()

            pdf.ln(5)

        # AI Summary
        if ai_summary:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(233, 69, 96)
            pdf.cell(0, 8, "AI Analysis", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(200, 200, 200)
            pdf.multi_cell(0, 5, ai_summary[:800])

        pdf.output(output_path)
        return output_path
