"""
Throttle & Axis Manager.

Analyses throttle behaviour and RC axis usage to identify
hover point, throttle consistency, and flight style.

Algorithm (improved over FPV Nexus):
  1. Basic throttle stats (peak, min, avg, full-throttle time)
  2. Hover detection Method 1: gyro-calm histogram mode (accelerometer optional)
  3. Hover detection Method 2: statistical mode fallback
  4. Throttle consistency near hover
  5. Per-axis RC usage and flight style classification

Enhanced over FPV Nexus with:
  - Throttle sag awareness (voltage correlation)
  - Battery usage profile
  - Detailed per-axis control percentages
"""
from __future__ import annotations

import math
from typing import Dict, Any, Optional, List

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


def _detect_hover_gyro_calm(
    throttle: np.ndarray,
    gyro_r: np.ndarray,
    gyro_p: np.ndarray,
    gyro_y: np.ndarray,
    n: int,
) -> Optional[float]:
    """Hover detection via gyro-calm period histogramming."""
    calm_mask = np.ones(n, dtype=bool)
    for g in [gyro_r, gyro_p, gyro_y]:
        if g is not None and len(g) >= n:
            calm_mask &= np.abs(g[:n].astype(np.float64)) < 20

    # Need throttle above idle
    thr = throttle[:n].astype(np.float64)
    valid = calm_mask & (thr > np.min(thr) + 50)

    calm_thr = thr[valid]
    if len(calm_thr) < 30:
        return None

    # Histogram binning
    thr_min = float(np.min(calm_thr))
    thr_max = float(np.max(calm_thr))
    nbins = max(10, int((thr_max - thr_min) / 10))
    counts, edges = np.histogram(calm_thr, bins=nbins)

    if np.max(counts) == 0:
        return None

    # Find mode — skip very low throttle bins (bottom 10%)
    range_10pct = (thr_max - thr_min) * 0.1
    peak_idx = -1
    peak_count = 0
    for i in range(len(counts)):
        bin_centre = (edges[i] + edges[i + 1]) / 2
        if bin_centre < thr_min + range_10pct:
            continue
        if counts[i] > peak_count:
            peak_count = counts[i]
            peak_idx = i

    if peak_idx < 0:
        return None

    return float((edges[peak_idx] + edges[peak_idx + 1]) / 2)


def _detect_hover_statistical(throttle: np.ndarray) -> Optional[float]:
    """Fallback hover detection via histogram mode."""
    thr = throttle.astype(np.float64)
    thr_min = float(np.min(thr))
    thr_max = float(np.max(thr))
    if thr_max - thr_min < 50:
        return None

    valid = thr[thr > thr_min + 50]
    if len(valid) < 30:
        return None

    nbins = max(10, int((thr_max - thr_min) / 20))
    counts, edges = np.histogram(valid, bins=nbins)

    # Peak detection — find local maxima above 15% of max count
    threshold = np.max(counts) * 0.15
    for i in range(1, len(counts) - 1):
        if counts[i] > threshold and counts[i] >= counts[i - 1] and counts[i] >= counts[i + 1]:
            return float((edges[i] + edges[i + 1]) / 2)

    # Fallback to global mode
    peak_idx = int(np.argmax(counts))
    return float((edges[peak_idx] + edges[peak_idx + 1]) / 2)


def _throttle_to_pct(raw: float, thr_min: float, thr_range: float) -> float:
    if thr_range < 1:
        return 0
    return (raw - thr_min) / thr_range * 100


class ThrottleAxisAnalyzer:
    """Analyse throttle behaviour and axis usage."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        throttle = flight_data.rc_command[3] if len(flight_data.rc_command) > 3 else None
        if throttle is None or len(throttle) < 200:
            return

        n = len(throttle)
        thr = throttle[:n].astype(np.float64)

        thr_min = float(np.min(thr))
        thr_max = float(np.max(thr))
        thr_range = thr_max - thr_min
        if thr_range < 50:
            return

        thr_avg = float(np.mean(thr))

        # Top/bottom 10%
        sorted_thr = np.sort(thr)
        n10 = max(1, n // 10)
        bottom10_avg = float(np.mean(sorted_thr[:n10]))
        top10_avg = float(np.mean(sorted_thr[-n10:]))

        # Full throttle time
        full_thr_threshold = thr_max - 0.05 * thr_range  # top 5% = full
        full_thr_pct = float(np.sum(thr >= full_thr_threshold) / n * 100)

        # --- Hover detection ---
        gyro_r = flight_data.gyro_roll
        gyro_p = flight_data.gyro_pitch
        gyro_y = flight_data.gyro_yaw

        hover_raw = _detect_hover_gyro_calm(throttle, gyro_r, gyro_p, gyro_y, n)
        detection_method = "Gyro-Calm Histogram"

        if hover_raw is None:
            hover_raw = _detect_hover_statistical(throttle)
            detection_method = "Statistical Mode"

        hover_pct = _throttle_to_pct(hover_raw, thr_min, thr_range) if hover_raw else None

        # Throttle consistency near hover
        consistency = None
        if hover_raw is not None:
            near_hover = thr[np.abs(thr - hover_raw) < 50]
            if len(near_hover) > 10:
                consistency = float(np.std(near_hover))

        # --- Voltage-throttle correlation (sag awareness) ---
        vbat_corr = None
        if flight_data.vbat is not None and len(flight_data.vbat) >= n:
            vbat = flight_data.vbat[:n].astype(np.float64)
            if np.std(vbat) > 0.01 and np.std(thr) > 0.01:
                r = float(np.corrcoef(thr, vbat)[0, 1])
                if not math.isnan(r):
                    vbat_corr = round(r, 3)

        # --- Per-axis usage ---
        axis_analysis = {}
        axis_names = ["Roll", "Pitch", "Yaw"]
        rc_sources = [
            flight_data.rc_command[0] if len(flight_data.rc_command) > 0 else None,
            flight_data.rc_command[1] if len(flight_data.rc_command) > 1 else None,
            flight_data.rc_command[2] if len(flight_data.rc_command) > 2 else None,
        ]

        axis_totals = {}
        for name, rc in zip(axis_names, rc_sources):
            if rc is None or len(rc) < 200:
                continue
            vals = rc[:n].astype(np.float64) if len(rc) >= n else rc.astype(np.float64)
            centre = float((np.min(vals) + np.max(vals)) / 2)
            pos = float(np.sum(np.maximum(0, vals - centre)))
            neg = float(np.sum(np.abs(np.minimum(0, vals - centre))))
            total = pos + neg
            axis_totals[name] = total
            if total > 0:
                axis_analysis[name] = {
                    "positive": round(pos, 0),
                    "negative": round(neg, 0),
                    "total": round(total, 0),
                    "centre": round(centre, 0),
                    "pct_positive": round(pos / total * 100, 1),
                    "pct_negative": round(neg / total * 100, 1),
                }

        # Add percentage of total control per axis
        grand_total = sum(axis_totals.values())
        if grand_total > 0:
            for name in axis_analysis:
                axis_analysis[name]["pct_of_total"] = round(
                    axis_totals[name] / grand_total * 100, 1
                )

        # Flight style
        flight_style = "Unknown"
        if axis_totals:
            roll_t = axis_totals.get("Roll", 0)
            pitch_t = axis_totals.get("Pitch", 0)
            yaw_t = axis_totals.get("Yaw", 0)

            pitch_r = axis_analysis.get("Pitch", {})
            if pitch_r.get("pct_positive", 50) > 66:
                flight_style = "Primarily Forward Flight"
            elif roll_t > 1.5 * pitch_t and roll_t > yaw_t:
                flight_style = "Lateral/Rolling Dominant"
            elif yaw_t > 1.5 * roll_t and yaw_t > pitch_t:
                flight_style = "Spinning/Yaw Dominant"
            elif pitch_t > 1.5 * roll_t and pitch_t > yaw_t:
                flight_style = "Forward/Backward Dominant"
            else:
                flight_style = "Balanced Multi-Axis"

        # --- Build finding ---
        recs = []
        sev = Severity.INFO

        if hover_pct is not None:
            recs.append(f"Hover at ~{hover_pct:.0f}% throttle ({detection_method}).")
        if consistency is not None:
            if consistency > 50:
                recs.append(f"Throttle consistency near hover is poor (σ={consistency:.0f}). Consider throttle expo.")
                sev = Severity.WARNING
            else:
                recs.append(f"Throttle consistency near hover: σ={consistency:.0f}.")

        if full_thr_pct > 20:
            recs.append(f"Full throttle used {full_thr_pct:.1f}% of flight — check motor/prop combo.")
            sev = Severity.WARNING
        elif full_thr_pct > 5:
            recs.append(f"Full throttle used {full_thr_pct:.1f}% of flight.")

        if vbat_corr is not None and vbat_corr < -0.3:
            recs.append(f"Voltage sag correlates with throttle (r={vbat_corr:.2f}). Battery may be stressed.")
            sev = Severity.WARNING

        recs.append(f"Flight style: {flight_style}")

        desc = (
            f"Hover: {hover_pct:.0f}%" if hover_pct else "Hover: N/A"
        ) + f" | Full-thr: {full_thr_pct:.1f}% | Style: {flight_style}"

        data = {
            "type": "throttle_axis",
            "peak_max": round(thr_max, 0),
            "min_throttle": round(thr_min, 0),
            "avg_throttle": round(thr_avg, 0),
            "top10_avg": round(top10_avg, 0),
            "bottom10_avg": round(bottom10_avg, 0),
            "full_throttle_pct": round(full_thr_pct, 1),
            "hover_raw": round(hover_raw, 0) if hover_raw else None,
            "hover_pct": round(hover_pct, 1) if hover_pct else None,
            "detection_method": detection_method,
            "throttle_consistency": round(consistency, 1) if consistency else None,
            "vbat_correlation": vbat_corr,
            "axis_analysis": axis_analysis,
            "flight_style": flight_style,
            "throttle_histogram": {
                "values": thr[::max(1, n // 300)].tolist(),
            },
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.GENERAL,
            title="Throttle & Axis Manager",
            severity=sev,
            description=desc,
            explanation="\n".join(recs),
            data=data,
        ))
