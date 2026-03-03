"""
Motor Health Analyzer – Motor Doctor.

Computes per-motor health scores using:
  - Stability (1 − stddev/mean)
  - Power balance (deviation from other motors' mean)
  - Responsiveness (rate of change normalised)
  - Cross-motor Pearson correlation
  - Gyro noise RMS

Based on the Motor Doctor approach used in professional FPV tuning tools.
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Per-motor metrics
# ---------------------------------------------------------------------------

def _per_motor_metrics(motor_arrays: List[np.ndarray]) -> List[Dict[str, Any]]:
    """Compute stability, responsiveness, power balance per motor."""
    num_motors = len(motor_arrays)
    means = []
    results = []

    for arr in motor_arrays:
        m = float(np.mean(arr))
        means.append(m)

    for idx, arr in enumerate(motor_arrays):
        n = len(arr)
        mean = means[idx]
        variance = float(np.mean((arr - mean) ** 2))
        stddev = math.sqrt(variance)

        # Stability: 1 − stddev/mean (clamped 0–1)
        stability = max(0.0, 1.0 - (stddev / mean)) if mean > 0 else 0.0

        # Responsiveness: normalised rate of change
        if n > 1:
            total_change = float(np.sum(np.abs(np.diff(arr))))
            responsiveness = min(1.0, (total_change / (n - 1)) / 50.0)
        else:
            responsiveness = 0.0

        # Power balance: deviation from other motors' mean
        other_means = [means[j] for j in range(num_motors) if j != idx]
        avg_other = sum(other_means) / len(other_means) if other_means else mean
        abs_deviation = abs(mean - avg_other)
        pct_deviation = (abs_deviation / avg_other * 100) if avg_other > 0 else 0.0
        power_balance = max(0.5, 1.0 - pct_deviation / 50.0)

        # Health score (weighted)
        score = (0.70 * max(0.5, min(1.0, stability + 0.3))
                 + 0.25 * power_balance
                 + 0.05 * min(0.2, 0.4 * responsiveness))

        # Penalties
        if pct_deviation > 80:
            score *= 0.85
        if stability < 0.1:
            score *= 0.90
        if mean > 0 and stddev > 1.2 * mean:
            score *= 0.95
        score *= 0.99  # calibration

        score = max(0.0, min(1.0, score))

        results.append({
            "motor_index": idx,
            "mean": round(mean, 2),
            "stddev": round(stddev, 2),
            "stability": round(stability, 3),
            "responsiveness": round(responsiveness, 3),
            "power_balance": round(power_balance, 3),
            "deviation_pct": round(pct_deviation, 2),
            "health_score": round(score * 100, 1),
        })

    return results


# ---------------------------------------------------------------------------
# Cross-motor correlation
# ---------------------------------------------------------------------------

def _motor_correlations(motor_arrays: List[np.ndarray]) -> List[Dict[str, Any]]:
    """Pearson correlation between all motor pairs."""
    results = []
    num = len(motor_arrays)
    n = min(len(a) for a in motor_arrays)

    for i in range(num):
        for j in range(i + 1, num):
            a = motor_arrays[i][:n].astype(np.float64)
            b = motor_arrays[j][:n].astype(np.float64)
            mean_a = np.mean(a)
            mean_b = np.mean(b)
            cov = np.mean((a - mean_a) * (b - mean_b))
            std_a = np.std(a)
            std_b = np.std(b)
            if std_a > 0 and std_b > 0:
                r = cov / (std_a * std_b)
            else:
                r = 0.0
            results.append({
                "motor_a": i + 1,
                "motor_b": j + 1,
                "correlation": round(float(r), 3),
            })
    return results


# ---------------------------------------------------------------------------
# Gyro noise RMS
# ---------------------------------------------------------------------------

def _gyro_noise_rms(flight_data) -> Dict[str, float]:
    """RMS noise per gyro axis."""
    axes = {"roll": flight_data.gyro_roll,
            "pitch": flight_data.gyro_pitch,
            "yaw": flight_data.gyro_yaw}
    rms = {}
    total = 0.0
    for name, arr in axes.items():
        if arr is not None and len(arr) > 0:
            val = float(np.sqrt(np.mean(arr.astype(np.float64) ** 2)))
            rms[name] = round(val, 2)
            total += val
        else:
            rms[name] = 0.0
    rms["total"] = round(total, 2)
    return rms


# ---------------------------------------------------------------------------
# Motor position labels
# ---------------------------------------------------------------------------

_MOTOR_LABELS = {
    0: "BR",  # Back Right
    1: "FR",  # Front Right
    2: "BL",  # Back Left
    3: "FL",  # Front Left
}


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class MotorHealthAnalyzer:
    """Motor Doctor — per-motor health scoring with visual quad layout data."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        """Compute motor health metrics and add findings."""
        # Collect motor arrays
        motor_arrays = []
        for i in range(4):
            arr = flight_data.motor[i]
            if arr is not None and len(arr) > 100:
                motor_arrays.append(arr.astype(np.float64))

        if len(motor_arrays) < 2:
            return

        # Per-motor metrics
        metrics = _per_motor_metrics(motor_arrays)

        # Cross-motor correlations
        correlations = _motor_correlations(motor_arrays)

        # Gyro noise
        gyro_rms = _gyro_noise_rms(flight_data)

        # Issues detection
        issues: List[str] = []

        # Low sync motors
        for corr in correlations:
            if abs(corr["correlation"]) < 0.7:
                issues.append(
                    f"Motor {corr['motor_a']} ↔ {corr['motor_b']} sync is low "
                    f"(r={corr['correlation']:.2f}). Check for mechanical issues."
                )

        # High gyro noise
        if gyro_rms["total"] > 1000:
            issues.append(
                f"High total gyro noise RMS ({gyro_rms['total']:.0f}). "
                "Consider vibration dampening or filter tuning."
            )

        # Poor motor
        for m in metrics:
            if m["health_score"] < 60:
                label = _MOTOR_LABELS.get(m["motor_index"], str(m["motor_index"] + 1))
                issues.append(
                    f"Motor {m['motor_index']+1} ({label}) health {m['health_score']:.0f}% — "
                    f"deviation {m['deviation_pct']:.1f}%, stability {m['stability']:.2f}."
                )

        # Overall health = average
        avg_health = sum(m["health_score"] for m in metrics) / len(metrics)

        if avg_health >= 80:
            sev = Severity.INFO
            label = "Good"
        elif avg_health >= 60:
            sev = Severity.WARNING
            label = "Fair"
        else:
            sev = Severity.ERROR
            label = "Poor"

        data = {
            "type": "motor_health",
            "motors": metrics,
            "correlations": correlations,
            "gyro_rms": gyro_rms,
            "avg_health": round(avg_health, 1),
            "motor_labels": {i: _MOTOR_LABELS.get(i, str(i + 1)) for i in range(len(metrics))},
            "issues": issues,
        }

        desc = f"Average motor health: {avg_health:.0f}% ({label})"
        for m in metrics:
            lbl = _MOTOR_LABELS.get(m["motor_index"], str(m["motor_index"] + 1))
            desc += f" | M{m['motor_index']+1}({lbl}): {m['health_score']:.0f}%"

        report.add_finding(Finding(
            category=Category.MOTOR,
            title="Motor Health Analysis",
            severity=sev,
            description=desc,
            explanation="\n".join(issues) if issues else "All motors are operating well.",
            data=data,
        ))
