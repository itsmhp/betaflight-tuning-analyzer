"""
FeedForward Tuning Assistant.

Analyses setpoint-to-gyro tracking to evaluate FeedForward
performance across axes and speed bands.

Algorithm (improved over FPV Nexus):
  1. Detect manoeuvre windows from setpoint data (10-sample windows)
  2. Cross-correlate setpoint vs gyro to find tracking lag
  3. Compute per-manoeuvre metrics: error%, tracking ratio, overshoot
  4. Classify FF_TOO_HIGH, FF_TOO_LOW, or FF_OK per manoeuvre
  5. Compute FF health score with 5 penalty factors
  6. Suggest FF value adjustments per axis
  7. Speed-band analysis (slow / medium / fast manoeuvres)

Enhanced over FPV Nexus with:
  - Separate undershoot/overshoot tracking
  - Settling time measurement
  - Axis imbalance detection
  - Specific CLI command suggestions
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
WINDOW_SIZE = 10           # samples per manoeuvre window
MIN_SETPOINT_RANGE = 5     # minimum setpoint variation to count as manoeuvre
MAX_MANOEUVRES = 500       # cap for analysis
CROSS_CORR_MAX_LAG = 5     # max lag in samples for cross-correlation

# Speed bands (deg/s)
SPEED_SLOW = 200
SPEED_FAST = 500


def _cross_correlate(sp: np.ndarray, gy: np.ndarray, max_lag: int = CROSS_CORR_MAX_LAG) -> int:
    """Find lag of best correlation between setpoint and gyro."""
    best_corr = -1e9
    best_lag = 0
    n = len(sp)
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            a = sp[:n - lag]
            b = gy[lag:]
        else:
            a = sp[-lag:]
            b = gy[:n + lag]
        if len(a) < 3:
            continue
        corr = float(np.sum(a * b))
        if corr > best_corr:
            best_corr = corr
            best_lag = lag
    return best_lag


def _detect_manoeuvres(
    setpoint: np.ndarray,
    gyro: np.ndarray,
    sample_rate: float,
) -> List[Dict[str, Any]]:
    """Detect manoeuvre windows and compute per-manoeuvre metrics."""
    n = min(len(setpoint), len(gyro))
    if n < WINDOW_SIZE * 2:
        return []

    sp = setpoint[:n].astype(np.float64)
    gy = gyro[:n].astype(np.float64)

    manoeuvres = []
    dt = 1.0 / max(sample_rate, 1)

    for start in range(0, n - WINDOW_SIZE, WINDOW_SIZE):
        end = start + WINDOW_SIZE
        sp_win = sp[start:end]
        gy_win = gy[start:end]

        sp_range = float(np.max(sp_win) - np.min(sp_win))
        if sp_range < MIN_SETPOINT_RANGE:
            continue

        # Cross-correlation lag
        lag = _cross_correlate(sp_win, gy_win)

        # Metrics
        sp_mag = float(np.mean(np.abs(sp_win)))
        if sp_mag < 1:
            continue
        avg_error = float(np.mean(np.abs(sp_win - gy_win)))
        tracking_ratio = max(0.1, min(1.0, 1.0 - avg_error / sp_mag))
        error_pct = avg_error / sp_mag * 100

        # Overshoot: where |gyro| > |setpoint| in same direction
        overshoot_mask = (np.sign(gy_win) == np.sign(sp_win)) & (np.abs(gy_win) > np.abs(sp_win))
        overshoot = float(np.mean(np.abs(gy_win[overshoot_mask]) - np.abs(sp_win[overshoot_mask]))) if np.any(overshoot_mask) else 0

        # Undershoot: where |gyro| < |setpoint|
        undershoot = float(np.mean(np.abs(sp_win) - np.abs(gy_win)))

        # Speed
        max_sp_rate = sp_range / (WINDOW_SIZE * dt)

        # Settling time: how many samples until error < 10% of sp_range
        settling = WINDOW_SIZE
        for j in range(WINDOW_SIZE):
            if abs(sp_win[j] - gy_win[j]) < 0.1 * sp_range:
                settling = j
                break

        # FF diagnosis
        if error_pct > 35 and lag > 0.5:
            diagnosis = "FF_TOO_LOW"
        elif overshoot > 5:
            diagnosis = "FF_TOO_HIGH"
        else:
            diagnosis = "FF_OK"

        manoeuvres.append({
            "start": start,
            "sp_range": round(sp_range, 1),
            "max_sp_rate": round(max_sp_rate, 0),
            "avg_error": round(avg_error, 2),
            "error_pct": round(error_pct, 1),
            "tracking_ratio": round(tracking_ratio, 3),
            "lag_samples": lag,
            "overshoot": round(overshoot, 2),
            "undershoot": round(undershoot, 2),
            "settling_samples": settling,
            "diagnosis": diagnosis,
        })

        if len(manoeuvres) >= MAX_MANOEUVRES:
            break

    return manoeuvres


def _compute_ff_health(manoeuvres: List[Dict[str, Any]]) -> float:
    """Compute FF health score 0-100 with penalty factors."""
    if not manoeuvres:
        return 50.0

    avg_error = float(np.mean([m["error_pct"] for m in manoeuvres]))
    avg_lag = float(np.mean([m["lag_samples"] for m in manoeuvres]))
    avg_overshoot = float(np.mean([m["overshoot"] for m in manoeuvres]))
    avg_undershoot = float(np.mean([m["undershoot"] for m in manoeuvres]))
    avg_settling = float(np.mean([m["settling_samples"] for m in manoeuvres]))
    excessive_overshoot_frac = sum(1 for m in manoeuvres if m["overshoot"] > 10) / len(manoeuvres)

    # Base score from error
    if avg_error <= 20:
        score = 100.0
    elif avg_error <= 25:
        score = 100 - (avg_error - 20) / 5 * 5  # 100→95
    elif avg_error < 100:
        score = 95 * (1 - (avg_error - 25) / 75)
    else:
        score = 0

    # Penalties
    if avg_lag > 0.3:
        score -= 3 * (avg_lag - 0.3)
    score -= (avg_overshoot / 30) * 25
    score -= (avg_undershoot / 40) * 15
    score -= (avg_settling / 100) * 10
    score -= excessive_overshoot_frac * 20

    return round(max(0, min(100, score)), 1)


def _suggest_ff(
    manoeuvres: List[Dict[str, Any]],
    current_ff: int = 100,
) -> Tuple[int, str]:
    """Suggest FF value based on manoeuvre analysis."""
    if not manoeuvres:
        return current_ff, "FF_OK"

    # Majority vote
    counts = {"FF_TOO_HIGH": 0, "FF_TOO_LOW": 0, "FF_OK": 0}
    for m in manoeuvres:
        counts[m["diagnosis"]] += 1

    primary = max(counts, key=counts.get)

    avg_lag = float(np.mean([m["lag_samples"] for m in manoeuvres]))
    avg_overshoot = float(np.mean([m["overshoot"] for m in manoeuvres]))
    avg_undershoot = float(np.mean([m["undershoot"] for m in manoeuvres]))
    avg_settling = float(np.mean([m["settling_samples"] for m in manoeuvres]))
    avg_tracking = float(np.mean([m["tracking_ratio"] for m in manoeuvres]))

    adjustment = 0
    if primary == "FF_TOO_HIGH":
        # Reduce 15-40 based on overshoot and settling
        base_reduce = 15 + min(25, int(avg_overshoot * 2 + avg_settling * 0.5))
        adjustment = -base_reduce
        if avg_tracking > 0.95:
            adjustment -= 10
    elif primary == "FF_TOO_LOW":
        # Increase 15-40 based on lag and undershoot
        base_increase = 15 + min(25, int(avg_lag * 5 + avg_undershoot * 0.5))
        adjustment = base_increase
        if avg_tracking < 0.7:
            adjustment += 20

    suggested = max(0, min(200, current_ff + adjustment))
    return suggested, primary


def _speed_band_analysis(manoeuvres: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Analyse FF performance by speed band."""
    bands = {
        "slow": [m for m in manoeuvres if m["max_sp_rate"] < SPEED_SLOW],
        "medium": [m for m in manoeuvres if SPEED_SLOW <= m["max_sp_rate"] < SPEED_FAST],
        "fast": [m for m in manoeuvres if m["max_sp_rate"] >= SPEED_FAST],
    }

    result = {}
    for band_name, band_ms in bands.items():
        if band_ms:
            result[band_name] = {
                "count": len(band_ms),
                "avg_error_pct": round(float(np.mean([m["error_pct"] for m in band_ms])), 1),
                "avg_tracking": round(float(np.mean([m["tracking_ratio"] for m in band_ms])), 3),
                "avg_lag": round(float(np.mean([m["lag_samples"] for m in band_ms])), 2),
                "avg_overshoot": round(float(np.mean([m["overshoot"] for m in band_ms])), 2),
            }
    return result


class FeedForwardAnalyzer:
    """FeedForward Tuning Assistant."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        sample_rate = bbl_header.get_blackbox_sample_rate()
        if sample_rate <= 0:
            return

        axis_names = ["Roll", "Pitch", "Yaw"]
        sp_sources = [flight_data.setpoint_roll, flight_data.setpoint_pitch, flight_data.setpoint_yaw]
        gy_sources = [flight_data.gyro_roll, flight_data.gyro_pitch, flight_data.gyro_yaw]

        all_axis_results = {}
        any_data = False

        for axis_name, sp, gy in zip(axis_names, sp_sources, gy_sources):
            if sp is None or gy is None or len(sp) < 100 or len(gy) < 100:
                continue

            manoeuvres = _detect_manoeuvres(sp, gy, sample_rate)
            if not manoeuvres:
                continue

            health = _compute_ff_health(manoeuvres)
            suggested_ff, primary_diag = _suggest_ff(manoeuvres)
            speed_bands = _speed_band_analysis(manoeuvres)

            diag_counts = {}
            for m in manoeuvres:
                diag_counts[m["diagnosis"]] = diag_counts.get(m["diagnosis"], 0) + 1

            all_axis_results[axis_name] = {
                "health_score": health,
                "primary_diagnosis": primary_diag,
                "suggested_ff": suggested_ff,
                "num_manoeuvres": len(manoeuvres),
                "diag_counts": diag_counts,
                "avg_error_pct": round(float(np.mean([m["error_pct"] for m in manoeuvres])), 1),
                "avg_tracking": round(float(np.mean([m["tracking_ratio"] for m in manoeuvres])), 3),
                "avg_lag": round(float(np.mean([m["lag_samples"] for m in manoeuvres])), 2),
                "avg_overshoot": round(float(np.mean([m["overshoot"] for m in manoeuvres])), 2),
                "speed_bands": speed_bands,
            }
            any_data = True

        if not any_data:
            return

        # Overall assessment
        healths = [r["health_score"] for r in all_axis_results.values()]
        avg_health = float(np.mean(healths))
        min_health = min(healths)

        # Axis imbalance detection
        if len(healths) >= 2:
            health_spread = max(healths) - min(healths)
        else:
            health_spread = 0

        # Severity
        if min_health < 50:
            sev = Severity.WARNING
        elif min_health < 70:
            sev = Severity.INFO
        else:
            sev = Severity.INFO

        # Recommendations
        recs = []
        cli_cmds = []
        for axis_name, r in all_axis_results.items():
            if r["primary_diagnosis"] == "FF_TOO_HIGH":
                recs.append(
                    f"{axis_name}: REDUCE feedforward — "
                    f"{r['diag_counts'].get('FF_TOO_HIGH', 0)}/{r['num_manoeuvres']} "
                    f"manoeuvres show overshoot. Suggested FF = {r['suggested_ff']}."
                )
            elif r["primary_diagnosis"] == "FF_TOO_LOW":
                recs.append(
                    f"{axis_name}: INCREASE feedforward — "
                    f"{r['diag_counts'].get('FF_TOO_LOW', 0)}/{r['num_manoeuvres']} "
                    f"manoeuvres show lag. Suggested FF = {r['suggested_ff']}."
                )
            else:
                recs.append(
                    f"{axis_name}: FeedForward looks good (health: {r['health_score']:.0f}%)."
                )

            # Speed band insight
            bands = r.get("speed_bands", {})
            if "fast" in bands and "slow" in bands:
                fast_err = bands["fast"]["avg_error_pct"]
                slow_err = bands["slow"]["avg_error_pct"]
                if fast_err > slow_err * 1.5:
                    recs.append(
                        f"  {axis_name}: Fast manoeuvres have {fast_err:.0f}% error vs "
                        f"{slow_err:.0f}% slow — consider increasing ff_boost."
                    )

        if health_spread > 20:
            recs.append(
                "Significant axis imbalance detected — "
                f"health spread = {health_spread:.0f}%. "
                "Tune axes individually rather than using linked roll/pitch."
            )

        # Generate CLI suggestions
        for axis_name, r in all_axis_results.items():
            axis_lower = axis_name.lower()
            if r["primary_diagnosis"] != "FF_OK":
                cli_cmds.append(f"set feedforward_{axis_lower} = {r['suggested_ff']}")

        desc_parts = []
        for axis_name, r in all_axis_results.items():
            desc_parts.append(f"{axis_name}: {r['health_score']:.0f}%")
        desc = f"FeedForward Health: {' | '.join(desc_parts)} | Avg: {avg_health:.0f}%"

        data = {
            "type": "feedforward_analysis",
            "axis_results": all_axis_results,
            "avg_health": round(avg_health, 1),
            "health_spread": round(health_spread, 1),
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.PID,
            title="FeedForward Tuning",
            severity=sev,
            description=desc,
            explanation="\n".join(recs),
            cli_commands=cli_cmds if cli_cmds else None,
            data=data,
        ))
