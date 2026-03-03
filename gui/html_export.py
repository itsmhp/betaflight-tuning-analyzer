"""
HTML Report Exporter.

Generates a standalone dark-themed HTML report with:
  - Score ring (pure CSS)
  - All findings organized by severity & category
  - Embedded chart images (base64 PNG)
  - Ready-to-paste CLI commands
  - Quad profile & config summary
"""
from __future__ import annotations

import base64
import io
from datetime import datetime
from typing import Optional

from gui.i18n import t


def _severity_color(sev: str) -> tuple[str, str, str]:
    """Return (bg, fg, border) for a severity value."""
    colors = {
        "critical": ("#5a0a25", "#ff4081", "#8a1040"),
        "error":    ("#3d0a0a", "#ff6b6b", "#7d2020"),
        "warning":  ("#3d2d00", "#ffc107", "#7d5a00"),
        "info":     ("#00243d", "#64b5f6", "#0a4f7d"),
    }
    return colors.get(sev.lower(), colors["info"])


def _score_color(score: int) -> str:
    if score >= 80:
        return "#2ecc71"
    elif score >= 60:
        return "#f1c40f"
    elif score >= 40:
        return "#e67e22"
    return "#e74c3c"


def _charts_to_base64(chart_data: dict) -> list[tuple[str, str]]:
    """Render all charts to base64-encoded PNGs. Returns [(title, b64_str), ...]."""
    results = []
    try:
        from gui.charts import build_all_charts
        charts = build_all_charts(chart_data)
        for title, canvas in charts:
            buf = io.BytesIO()
            canvas.figure.savefig(buf, format="png", dpi=120,
                                  facecolor=canvas.figure.get_facecolor(),
                                  bbox_inches="tight")
            buf.seek(0)
            b64 = base64.b64encode(buf.read()).decode("ascii")
            results.append((title, b64))
            # Clean up matplotlib memory
            import matplotlib.pyplot as plt
            plt.close(canvas.figure)
    except Exception:
        pass
    return results


def generate_html_report(result: dict, chart_data: Optional[dict] = None) -> str:
    """
    Generate a complete standalone HTML report string.

    Parameters
    ----------
    result : dict
        The result dictionary from run_analysis().
    chart_data : dict, optional
        Chart data dict for embedding chart images.

    Returns
    -------
    str
        Complete HTML document.
    """
    report = result["report"]
    cli_data = result.get("cli_data")
    cli_script = result.get("cli_script", "")
    findings_by_cat = result.get("findings_by_category", {})
    score = report.overall_score
    score_clr = _score_color(score)

    # Craft info
    craft_name = getattr(cli_data, "craft_name", "Unknown") or "Unknown"
    board_name = getattr(cli_data, "board_name", "?") or "?"
    fw_version = getattr(cli_data, "firmware_version", "?") or "?"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build chart images
    chart_images = []
    if chart_data:
        chart_images = _charts_to_base64(chart_data)

    # Counts
    error_count = report.error_count + report.critical_count
    warning_count = report.warning_count
    info_count = report.info_count
    total_count = len(report.findings)

    # Build findings HTML
    findings_html = ""
    for cat_name, findings in findings_by_cat.items():
        findings_html += f'<h3 class="cat-title">{_esc(cat_name)} ({len(findings)})</h3>\n'
        for f in findings:
            sev = f.severity.value.lower()
            bg, fg, border = _severity_color(sev)
            cli_cmds_html = ""
            if f.cli_commands:
                cmds = "\n".join(f.cli_commands)
                cli_cmds_html = f'<pre class="cli-block">{_esc(cmds)}</pre>'

            cur_rec_html = ""
            if f.current_value:
                cur_rec_html += f'<span class="current-val">Current: {_esc(str(f.current_value))}</span>'
            if f.recommended_value:
                cur_rec_html += f' <span class="rec-val">→ {_esc(str(f.recommended_value))}</span>'

            explanation_html = ""
            if f.explanation:
                explanation_html = f'<p class="explanation">{_esc(f.explanation)}</p>'

            findings_html += f"""
            <div class="finding-card" style="border-left: 3px solid {fg};">
                <div class="finding-header">
                    <span class="severity-badge" style="background:{bg};color:{fg};border:1px solid {border};">{_esc(sev.upper())}</span>
                    <span class="finding-cat">{_esc(f.category.value)}</span>
                    <span class="finding-title">{_esc(f.title)}</span>
                    {cur_rec_html}
                </div>
                {f'<p class="finding-desc">{_esc(f.description)}</p>' if f.description else ''}
                {explanation_html}
                {cli_cmds_html}
            </div>
            """

    # Build charts HTML
    charts_html = ""
    if chart_images:
        charts_html += '<h2 class="section-title">Charts</h2>\n'
        for title, b64 in chart_images:
            charts_html += f"""
            <div class="chart-block">
                <h4 class="chart-title">{_esc(title)}</h4>
                <img src="data:image/png;base64,{b64}" alt="{_esc(title)}" class="chart-img"/>
            </div>
            """

    # CLI section
    cli_html = ""
    if cli_script:
        cli_html = f"""
        <h2 class="section-title">CLI Commands</h2>
        <p class="hint">Paste this entire block into the Betaflight CLI tab, then type 'save'.</p>
        <pre class="cli-output">{_esc(cli_script)}</pre>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Betaflight Tuning Report – {_esc(craft_name)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    background: #0d0d1a;
    color: #e0e0f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    padding: 30px 40px;
    max-width: 1100px;
    margin: 0 auto;
}}
h1 {{ color: #fff; font-size: 24px; margin-bottom: 4px; }}
.subtitle {{ color: #7070a0; font-size: 13px; margin-bottom: 20px; }}
.header-card {{
    background: #111128;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 20px 24px;
    display: flex;
    align-items: center;
    gap: 24px;
    margin-bottom: 24px;
}}
.score-ring {{
    width: 100px; height: 100px;
    border-radius: 50%;
    border: 8px solid #1e1e38;
    border-top-color: {score_clr};
    border-right-color: {score_clr};
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; font-weight: bold; color: #fff;
    flex-shrink: 0;
    position: relative;
}}
.score-ring::after {{
    content: '/100';
    position: absolute;
    bottom: 16px;
    font-size: 10px;
    color: #7070a0;
    font-weight: normal;
}}
.craft-info {{ color: #a0a0d0; font-size: 13px; }}
.pills {{ display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }}
.pill {{
    padding: 3px 10px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 12px;
    display: inline-block;
}}
.pill-error {{ background: #3d0a0a; color: #ff6b6b; border: 1px solid #7d2020; }}
.pill-warning {{ background: #3d2d00; color: #ffc107; border: 1px solid #7d5a00; }}
.pill-info {{ background: #00243d; color: #64b5f6; border: 1px solid #0a4f7d; }}
.pill-total {{ background: #1a1a38; color: #c0c0e0; border: 1px solid #2a2a5a; }}
.section-title {{
    color: #9090d0;
    font-size: 16px;
    margin: 24px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #2a2a4a;
}}
.cat-title {{
    color: #7070d0;
    font-size: 14px;
    margin: 16px 0 8px 0;
}}
.finding-card {{
    background: #0e0e1e;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 12px 14px;
    margin-bottom: 8px;
}}
.finding-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}}
.severity-badge {{
    border-radius: 3px;
    padding: 2px 8px;
    font-weight: bold;
    font-size: 11px;
}}
.finding-cat {{ color: #6060a0; font-size: 11px; }}
.finding-title {{ color: #e0e0f0; font-weight: bold; font-size: 13px; }}
.current-val {{ color: #a0a0c0; font-size: 11px; }}
.rec-val {{ color: #4db6ac; font-size: 11px; font-weight: bold; }}
.finding-desc {{ color: #c0c0e0; font-size: 12px; margin-top: 6px; }}
.explanation {{ color: #8080b0; font-size: 11px; font-style: italic; margin-top: 4px; }}
.cli-block {{
    background: #060c14;
    border: 1px solid #1a1a3a;
    border-radius: 4px;
    padding: 6px 10px;
    margin-top: 6px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    color: #a8ff78;
    overflow-x: auto;
}}
.cli-output {{
    background: #060c14;
    border: 1px solid #1a1a3a;
    border-radius: 4px;
    padding: 12px 16px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    color: #a8ff78;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-all;
}}
.hint {{ color: #6060a0; font-size: 12px; margin-bottom: 8px; }}
.chart-block {{ margin-bottom: 20px; }}
.chart-title {{ color: #9090d0; font-size: 13px; margin-bottom: 6px; }}
.chart-img {{ max-width: 100%; border-radius: 4px; border: 1px solid #1a1a3a; }}
.footer {{
    color: #3a3a6a;
    font-size: 11px;
    text-align: center;
    margin-top: 40px;
    padding-top: 16px;
    border-top: 1px solid #1a1a3a;
}}
.config-table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 8px;
}}
.config-table td {{
    padding: 4px 12px;
    border-bottom: 1px solid #1a1a3a;
}}
.config-label {{ color: #6060a0; font-size: 12px; width: 140px; }}
.config-value {{ color: #e0e0f0; font-size: 12px; }}
</style>
</head>
<body>
<h1>Betaflight Tuning Analyzer Report</h1>
<p class="subtitle">{_esc(craft_name)} &bull; {_esc(board_name)} &bull; Betaflight {_esc(fw_version)} &bull; {now}</p>

<div class="header-card">
    <div class="score-ring">{score}</div>
    <div>
        <div style="font-size:18px;font-weight:bold;color:#fff;">Analysis Score: {score}/100</div>
        <div class="craft-info">{_esc(craft_name)} &bull; {_esc(board_name)} &bull; Betaflight {_esc(fw_version)}</div>
        <div class="pills">
            <span class="pill pill-error">{error_count} Errors</span>
            <span class="pill pill-warning">{warning_count} Warnings</span>
            <span class="pill pill-info">{info_count} Info</span>
            <span class="pill pill-total">{total_count} Total</span>
        </div>
    </div>
</div>

<h2 class="section-title">Configuration Summary</h2>
<table class="config-table">
    <tr><td class="config-label">Board</td><td class="config-value">{_esc(board_name)}</td></tr>
    <tr><td class="config-label">Firmware</td><td class="config-value">Betaflight {_esc(fw_version)}</td></tr>
    <tr><td class="config-label">Craft Name</td><td class="config-value">{_esc(craft_name)}</td></tr>
    <tr><td class="config-label">PID Profile</td><td class="config-value">{getattr(cli_data, 'active_pid_profile', '?') or '?'}</td></tr>
    <tr><td class="config-label">Rate Profile</td><td class="config-value">{getattr(cli_data, 'active_rate_profile', '?') or '?'}</td></tr>
</table>

<h2 class="section-title">Findings</h2>
{findings_html}

{charts_html}

{cli_html}

<div class="footer">
    Generated by Betaflight Tuning Analyzer &bull; {now}
</div>
</body>
</html>"""
    return html


def _esc(text: str) -> str:
    """HTML-escape a string."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
