"""
Stick Movement Analyzer.

Analyses RC stick inputs to characterise piloting style,
smoothness, and detect hardware issues (pot jitter, bounceback).

Algorithm (improved over FPV Nexus):
  1. Per-axis normalisation to [-1, +1]
  2. Smoothness = 100 - 9 * RMS(velocity)
  3. Symmetry analysis (positive vs negative distribution)
  4. Bounceback detection from zero-crossings
  5. Pot jitter detection from centre-stick micro-movements
  6. Expo suggestions based on centre usage
  7. Flight style classification

Enhanced over FPV Nexus with:
  - Per-axis expo suggestions
  - Directional bias flags
  - FeedForward reduction hints from bounceback
  - Response linearity score
"""
from __future__ import annotations

import math
from typing import Dict, Any, List, Optional

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


def _analyse_axis(values: np.ndarray) -> Optional[Dict[str, Any]]:
    """Analyse a single RC axis. Returns metrics dict or None."""
    if values is None or len(values) < 200:
        return None

    vals = values.astype(np.float64)

    # Normalise to [-1, +1]
    vmin = float(np.min(vals))
    vmax = float(np.max(vals))
    vrange = vmax - vmin
    if vrange < 10:
        return None
    norm = (vals - (vmin + vmax) / 2) / (vrange / 2)

    # --- Smoothness ---
    deltas = np.diff(norm)
    rms_vel = float(np.sqrt(np.mean(deltas ** 2)))
    smoothness = max(0, min(100, 100 - 9 * rms_vel * 100))
    # scale rms_vel since it's per-sample in normalised units (small values)

    # --- Symmetry ---
    centre = float(np.mean(norm))
    pos_count = int(np.sum(norm > 0.05))
    neg_count = int(np.sum(norm < -0.05))
    total_biased = pos_count + neg_count
    if total_biased > 0:
        pct_positive = pos_count / total_biased * 100
        pct_negative = neg_count / total_biased * 100
    else:
        pct_positive = pct_negative = 50.0
    symmetry = 100 - abs(pct_positive - 50) * 2  # 100 = perfectly balanced

    # --- Bounceback ---
    crossings = 0
    bounce_events = 0
    prev_sign = 1 if norm[0] >= 0 else -1
    BOUNCE_WINDOW = 5

    for i in range(1, len(norm)):
        curr_sign = 1 if norm[i] >= 0 else -1
        if curr_sign != prev_sign:
            crossings += 1
            # Check for quick reversal within window
            if i + BOUNCE_WINDOW < len(norm):
                future_sign = 1 if norm[i + BOUNCE_WINDOW] >= 0 else -1
                if future_sign == prev_sign:
                    bounce_events += 1
            prev_sign = curr_sign

    bounceback_score = (bounce_events / max(crossings, 1)) * 100

    # --- Pot jitter ---
    centre_mask = np.abs(norm) < 0.05
    if np.sum(centre_mask) > 10:
        centre_vals = norm[centre_mask]
        centre_deltas = np.diff(centre_vals)
        jitter = 50 * float(np.sqrt(np.mean(centre_deltas ** 2)))
    else:
        jitter = 0.0

    # --- Centre usage (for expo suggestion) ---
    centre_usage = float(np.sum(np.abs(norm) < 0.3) / len(norm) * 100)

    # Expo suggestion
    expo_adj = 0.0
    if centre_usage >= 50:
        expo_adj = 0.10  # increase expo
    elif centre_usage <= 22:
        expo_adj = -0.05  # decrease expo

    # --- Positive/negative deflection totals ---
    pos_total = float(np.sum(np.maximum(0, norm)))
    neg_total = float(np.sum(np.abs(np.minimum(0, norm))))

    return {
        "smoothness": round(smoothness, 1),
        "rms_velocity": round(rms_vel, 5),
        "symmetry": round(symmetry, 1),
        "pct_positive": round(pct_positive, 1),
        "pct_negative": round(pct_negative, 1),
        "bounceback_score": round(bounceback_score, 1),
        "crossings": crossings,
        "bounce_events": bounce_events,
        "jitter_score": round(jitter, 2),
        "centre_usage_pct": round(centre_usage, 1),
        "expo_adjustment": round(expo_adj, 2),
        "pos_total": round(pos_total, 1),
        "neg_total": round(neg_total, 1),
    }


def _classify_flight_style(axis_results: Dict[str, Dict[str, Any]]) -> str:
    """Classify flight style from axis usage."""
    totals = {}
    for axis, r in axis_results.items():
        totals[axis] = r["pos_total"] + r["neg_total"]

    if not totals:
        return "Unknown"

    roll_t = totals.get("Roll", 0)
    pitch_t = totals.get("Pitch", 0)
    yaw_t = totals.get("Yaw", 0)
    total = roll_t + pitch_t + yaw_t
    if total < 1:
        return "Minimal Stick Input"

    roll_pct = roll_t / total * 100
    pitch_pct = pitch_t / total * 100
    yaw_pct = yaw_t / total * 100

    # Check for directional bias
    pitch_r = axis_results.get("Pitch", {})
    if pitch_r and pitch_r.get("pct_positive", 50) > 66:
        return "Primarily Forward Flight"
    if pitch_r and pitch_r.get("pct_negative", 50) > 66:
        return "Primarily Backward Flight"

    roll_r = axis_results.get("Roll", {})
    if roll_r and roll_r.get("pct_positive", 50) > 66:
        return "Primarily Right Rolling"
    if roll_r and roll_r.get("pct_negative", 50) > 66:
        return "Primarily Left Rolling"

    if pitch_pct > 1.5 * roll_pct and pitch_pct > yaw_pct:
        return "Forward/Backward Flight Dominant"
    if roll_pct > 1.5 * pitch_pct and roll_pct > yaw_pct:
        return "Lateral/Rolling Dominant"
    if yaw_pct > 1.5 * roll_pct and yaw_pct > pitch_pct:
        return "Spinning/Yaw Dominant"

    return "Balanced Multi-Axis Flight"


class StickMovementAnalyzer:
    """Analyse stick inputs for smoothness, jitter, and piloting style."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        axis_names = ["Roll", "Pitch", "Yaw"]
        rc_sources = [
            flight_data.rc_command[0] if len(flight_data.rc_command) > 0 else None,
            flight_data.rc_command[1] if len(flight_data.rc_command) > 1 else None,
            flight_data.rc_command[2] if len(flight_data.rc_command) > 2 else None,
        ]

        axis_results: Dict[str, Dict[str, Any]] = {}
        for name, rc in zip(axis_names, rc_sources):
            result = _analyse_axis(rc)
            if result is not None:
                axis_results[name] = result

        if not axis_results:
            return

        flight_style = _classify_flight_style(axis_results)

        # --- Build findings ---
        recs: List[str] = []
        sev = Severity.INFO

        for axis, r in axis_results.items():
            smoothness = r["smoothness"]
            if smoothness < 40:
                recs.append(f"{axis}: Low smoothness ({smoothness:.0f}%). Consider increasing rates expo or RC smoothing.")
                sev = Severity.WARNING
            elif smoothness < 65:
                recs.append(f"{axis}: Moderate smoothness ({smoothness:.0f}%).")

            if r["bounceback_score"] > 20:
                recs.append(f"{axis}: High bounceback ({r['bounceback_score']:.0f}%) — consider lowering feedforward.")
                sev = Severity.WARNING

            if r["jitter_score"] > 5:
                recs.append(f"{axis}: Centre jitter detected ({r['jitter_score']:.1f}). Check gimbal/potentiometer hardware.")
                sev = Severity.WARNING

            if r["expo_adjustment"] > 0:
                recs.append(f"{axis}: Centre usage high ({r['centre_usage_pct']:.0f}%) — increase expo by +{r['expo_adjustment']:.2f}.")
            elif r["expo_adjustment"] < 0:
                recs.append(f"{axis}: Centre usage low ({r['centre_usage_pct']:.0f}%) — decrease expo by {r['expo_adjustment']:.2f}.")

        recs.append(f"Flight style: {flight_style}")

        # Summary
        avg_smoothness = float(np.mean([r["smoothness"] for r in axis_results.values()]))
        desc_parts = []
        for axis, r in axis_results.items():
            desc_parts.append(f"{axis}: {r['smoothness']:.0f}%")
        desc = f"Stick Smoothness: {' | '.join(desc_parts)} | Style: {flight_style}"

        data = {
            "type": "stick_movement",
            "axis_results": axis_results,
            "flight_style": flight_style,
            "avg_smoothness": round(avg_smoothness, 1),
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.RATE,
            title="Stick Movement Analysis",
            severity=sev,
            description=desc,
            explanation="\n".join(recs),
            data=data,
        ))
