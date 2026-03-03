"""
I-Term Build-Up Visualizer.

Analyses integral (I-term) windup across flight axes.
Detects excessive I-term accumulation that can cause:
  - Sluggish attitude recovery
  - Unexpected attitude shifts
  - Post-flip/roll drift

Metrics:
  - pctHigh: % of samples where |I-term| > threshold
  - maxVal: peak absolute I-term
  - Health classification: Good / Fair / Poor per axis

Enhanced over FPV Nexus with:
  - Multiple threshold levels (25, 50, 75, 100)
  - Windup event detection (sustained high I-term)
  - Rate-of-change analysis for rapid buildup detection
  - CLI recommendations for iterm_relax settings
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ITERM_HIGH_THRESHOLD = 75      # Primary threshold (matching Nexus)
ITERM_EXTREME_THRESHOLD = 150  # Additional extreme level
MIN_SAMPLES = 100
SUSTAINED_WINDOW = 50          # samples for sustained windup detection


def _analyze_axis(values: np.ndarray) -> Optional[Dict[str, Any]]:
    """Analyse I-term data for one axis."""
    if values is None or len(values) < MIN_SAMPLES:
        return None

    vals = values.astype(np.float64)
    abs_vals = np.abs(vals)
    n = len(vals)

    # Percentage of samples above thresholds
    pct_high = float(np.sum(abs_vals > ITERM_HIGH_THRESHOLD) / n * 100)
    pct_extreme = float(np.sum(abs_vals > ITERM_EXTREME_THRESHOLD) / n * 100)
    max_val = float(np.max(abs_vals))
    mean_val = float(np.mean(abs_vals))
    std_val = float(np.std(abs_vals))

    # Health classification (matching Nexus: <10% Good, 10-20% Fair, >=20% Poor)
    if pct_high < 10:
        health = "Good"
    elif pct_high < 20:
        health = "Fair"
    else:
        health = "Poor"

    # Enhanced: Rate of change analysis for rapid buildup
    iterm_delta = np.diff(vals, prepend=vals[0])
    rms_delta = float(np.sqrt(np.mean(iterm_delta ** 2)))
    max_delta = float(np.max(np.abs(iterm_delta)))

    # Enhanced: Sustained windup event detection
    # Find segments where |I-term| > threshold for > SUSTAINED_WINDOW samples
    above = abs_vals > ITERM_HIGH_THRESHOLD
    windup_events = 0
    total_windup_samples = 0
    in_windup = False
    windup_start = 0

    for i in range(n):
        if above[i] and not in_windup:
            in_windup = True
            windup_start = i
        elif not above[i] and in_windup:
            in_windup = False
            duration = i - windup_start
            if duration >= SUSTAINED_WINDOW:
                windup_events += 1
                total_windup_samples += duration

    if in_windup:
        duration = n - windup_start
        if duration >= SUSTAINED_WINDOW:
            windup_events += 1
            total_windup_samples += duration

    # Enhanced: Positive vs negative bias
    pos_sum = float(np.sum(vals[vals > 0]))
    neg_sum = float(np.sum(np.abs(vals[vals < 0])))
    total_sum = pos_sum + neg_sum
    bias_pct = ((pos_sum - neg_sum) / total_sum * 100) if total_sum > 0 else 0

    return {
        "pct_high": round(pct_high, 1),
        "pct_extreme": round(pct_extreme, 1),
        "max_val": round(max_val, 1),
        "mean_val": round(mean_val, 1),
        "std_val": round(std_val, 1),
        "health": health,
        "rms_delta": round(rms_delta, 2),
        "max_delta": round(max_delta, 1),
        "windup_events": windup_events,
        "windup_time_pct": round(total_windup_samples / n * 100, 1),
        "bias_pct": round(bias_pct, 1),
    }


class ITermBuildupAnalyzer:
    """I-Term Build-Up Visualizer."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        axis_names = ["Roll", "Pitch", "Yaw"]
        iterm_sources = [
            flight_data.pid_i_roll,
            flight_data.pid_i_pitch,
            flight_data.pid_i_yaw,
        ]

        axis_results = {}
        any_data = False

        for axis_name, iterm_data in zip(axis_names, iterm_sources):
            result = _analyze_axis(iterm_data)
            if result:
                axis_results[axis_name] = result
                any_data = True

        if not any_data:
            return

        # Overall assessment
        worst_health = "Good"
        worst_axis = None
        max_pct = 0
        total_windup_events = 0

        for axis_name, r in axis_results.items():
            if r["pct_high"] > max_pct:
                max_pct = r["pct_high"]
                worst_axis = axis_name
            if r["health"] == "Poor":
                worst_health = "Poor"
            elif r["health"] == "Fair" and worst_health == "Good":
                worst_health = "Fair"
            total_windup_events += r["windup_events"]

        # Severity
        if worst_health == "Poor":
            sev = Severity.WARNING
        elif worst_health == "Fair":
            sev = Severity.INFO
        else:
            sev = Severity.INFO

        # Recommendations (enhanced over Nexus)
        recs = []
        cli_cmds = []

        if worst_health == "Poor":
            recs.append(
                f"I-term on {worst_axis} axis has {max_pct:.0f}% of samples above threshold. "
                "This indicates sustained integral windup."
            )
            recs.append("Enable or tune iterm_relax to prevent excessive I-term accumulation.")
            cli_cmds.append("set iterm_relax = RP")
            cli_cmds.append("set iterm_relax_type = SETPOINT")
            cli_cmds.append("set iterm_relax_cutoff = 15")

            # Check for rapid buildup
            for axis_name, r in axis_results.items():
                if r["rms_delta"] > 5:
                    recs.append(
                        f"{axis_name} shows rapid I-term changes (RMS Δ = {r['rms_delta']:.1f}). "
                        "This may indicate mechanical issues or too-aggressive I-gains."
                    )

        elif worst_health == "Fair":
            recs.append(
                f"I-term buildup is moderate ({max_pct:.0f}% on {worst_axis}). "
                "Monitor during aggressive manoeuvres."
            )
            if total_windup_events > 3:
                recs.append(
                    f"Detected {total_windup_events} sustained windup events. "
                    "Consider enabling iterm_relax if not already active."
                )
                cli_cmds.append("set iterm_relax = RP")
        else:
            recs.append("I-term buildup is within normal limits. No changes needed.")

        # Bias detection
        for axis_name, r in axis_results.items():
            if abs(r["bias_pct"]) > 30:
                direction = "positive" if r["bias_pct"] > 0 else "negative"
                recs.append(
                    f"{axis_name} I-term has a {direction} bias ({r['bias_pct']:.0f}%). "
                    "Check for CG offset or motor/prop asymmetry."
                )

        desc_parts = []
        for axis_name in axis_names:
            if axis_name in axis_results:
                r = axis_results[axis_name]
                desc_parts.append(f"{axis_name}: {r['health']} ({r['pct_high']:.0f}%)")

        desc = f"I-Term Health: {' | '.join(desc_parts)}"

        # Chart data - downsampled I-term traces
        chart_iterm = {}
        max_pts = 2000
        for axis_name, iterm_data in zip(axis_names, iterm_sources):
            if iterm_data is not None and len(iterm_data) > 10:
                step = max(1, len(iterm_data) // max_pts)
                chart_iterm[axis_name] = [round(float(v), 1) for v in iterm_data[::step]]

        data = {
            "type": "iterm_buildup",
            "axis_results": axis_results,
            "worst_health": worst_health,
            "worst_axis": worst_axis,
            "total_windup_events": total_windup_events,
            "chart_iterm": chart_iterm,
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.PID,
            title="I-Term Build-Up Analysis",
            severity=sev,
            description=desc,
            explanation="\n".join(recs),
            cli_commands=cli_cmds if cli_cmds else None,
            data=data,
        ))
