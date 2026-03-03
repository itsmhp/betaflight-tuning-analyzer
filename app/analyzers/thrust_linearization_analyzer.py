"""
Thrust Linearization Analysis.

Analyses the throttle-to-motor output relationship to detect
non-linearity and recommend thrust_linear settings.

Algorithm (improved over FPV Nexus):
  1. Throttle normalisation to percentage
  2. Baseline linear regression on bottom 30% of data
  3. MAPE (Mean Absolute Percentage Error)
  4. Non-linear onset detection via residual & slope methods
  5. PID effort regression
  6. Hover throttle detection (gyro-calm histogram mode)
  7. Severity classification and CLI suggestions

Enhanced over FPV Nexus with:
  - PID-effort slope thresholds for TPA/linearisation decision
  - Explicit onset % for user reference
  - Dual severity (MAPE + PID escalation)
"""
from __future__ import annotations

import math
from typing import Dict, Any, Optional, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


def _linear_regression(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Least-squares y = mx + b."""
    n = len(x)
    if n < 2:
        return 0.0, 0.0
    sx = float(np.sum(x))
    sy = float(np.sum(y))
    sxy = float(np.sum(x * y))
    sxx = float(np.sum(x * x))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-12:
        return 0.0, float(sy / n) if n else 0.0
    m = (n * sxy - sx * sy) / denom
    b = (sy - m * sx) / n
    return m, b


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Mean Absolute Percentage Error (skip near-zero actuals)."""
    mask = np.abs(actual) > 1
    if not np.any(mask):
        return 0.0
    return float(np.mean(100 * np.abs(actual[mask] - predicted[mask]) / np.abs(actual[mask])))


def _median_absolute_deviation(arr: np.ndarray) -> float:
    med = float(np.median(arr))
    return float(np.median(np.abs(arr - med)))


class ThrustLinearizationAnalyzer:
    """Analyse throttle-to-motor linearity and recommend thrust_linear settings."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        sample_rate = bbl_header.get_blackbox_sample_rate()
        if sample_rate <= 0:
            return

        # --- Gather data ---
        throttle = flight_data.rc_command[3] if len(flight_data.rc_command) > 3 else None
        if throttle is None or len(throttle) < 200:
            return

        motors = []
        for i in range(4):
            if flight_data.motor[i] is not None and len(flight_data.motor[i]) > 200:
                motors.append(flight_data.motor[i])
        if not motors:
            return

        n = min(len(throttle), min(len(m) for m in motors))
        thr = throttle[:n].astype(np.float64)
        avg_motor = np.mean([m[:n].astype(np.float64) for m in motors], axis=0)

        # --- Throttle normalisation ---
        thr_min = float(np.min(thr))
        thr_max = float(np.max(thr))
        thr_range = thr_max - thr_min
        if thr_range < 50:
            return  # not enough throttle variation

        thr_pct = (thr - thr_min) / thr_range * 100

        # Similarly for motor
        mot_min = float(np.min(avg_motor))
        mot_max = float(np.max(avg_motor))
        mot_range = mot_max - mot_min
        if mot_range < 50:
            return
        mot_pct = (avg_motor - mot_min) / mot_range * 100

        # Sort by throttle for regression
        order = np.argsort(thr_pct)
        thr_sorted = thr_pct[order]
        mot_sorted = mot_pct[order]

        # --- Baseline linear regression on bottom 30% ---
        cutoff = max(10, int(n * 0.3))
        x_base = thr_sorted[:cutoff]
        y_base = mot_sorted[:cutoff]
        m_base, b_base = _linear_regression(x_base, y_base)

        # Predicted for all points
        predicted = m_base * thr_sorted + b_base

        # MAPE
        mape = _mape(mot_sorted, predicted)

        # Residuals
        residuals = mot_sorted - predicted
        base_residuals = residuals[:cutoff]
        mad = _median_absolute_deviation(base_residuals)

        # --- Non-linear onset: Method 1 - residual threshold ---
        onset1 = None
        for i in range(cutoff, n):
            if abs(residuals[i]) > 2.5 * max(mad, 0.5):
                onset1 = float(thr_sorted[i])
                break

        # --- Non-linear onset: Method 2 - slope deviation ---
        slopes = np.zeros(n)
        half_win = 5
        for i in range(half_win, n - half_win):
            local_x = thr_sorted[i - half_win:i + half_win]
            local_y = mot_sorted[i - half_win:i + half_win]
            m_loc, _ = _linear_regression(local_x, local_y)
            slopes[i] = m_loc

        base_slopes = slopes[half_win:cutoff]
        slope_mad = _median_absolute_deviation(base_slopes) if len(base_slopes) > 2 else 1

        onset2 = None
        for i in range(cutoff, n - half_win):
            if slopes[i] > 1.6 * max(slope_mad, 0.1):
                onset2 = float(thr_sorted[i])
                break

        onset_pct = None
        if onset1 is not None and onset2 is not None:
            onset_pct = min(onset1, onset2)
        elif onset1 is not None:
            onset_pct = onset1
        elif onset2 is not None:
            onset_pct = onset2

        # --- PID effort regression ---
        pid_p = [flight_data.pid_p[a] for a in range(3) if flight_data.pid_p[a] is not None]
        pid_d = [flight_data.pid_d[a] for a in range(3) if flight_data.pid_d[a] is not None]

        pid_effort_slope = None
        if pid_p or pid_d:
            pid_sums = np.zeros(n)
            for arr in pid_p + pid_d:
                if len(arr) >= n:
                    pid_sums += np.abs(arr[:n].astype(np.float64))
            m_pid, _ = _linear_regression(avg_motor[:n], pid_sums)
            pid_effort_slope = float(m_pid)

        # --- Hover detection: gyro calm + throttle histogram ---
        gyro_r = flight_data.gyro_roll
        gyro_p = flight_data.gyro_pitch
        gyro_y = flight_data.gyro_yaw
        hover_pct = None

        if gyro_r is not None and gyro_p is not None and gyro_y is not None:
            calm_mask = np.ones(n, dtype=bool)
            for g in [gyro_r, gyro_p, gyro_y]:
                if len(g) >= n:
                    calm_mask &= np.abs(g[:n]) < 40
            calm_thr = thr_pct[calm_mask]
            if len(calm_thr) > 50:
                # Histogram binning
                bins = np.arange(10, 81, 2)
                counts, edges = np.histogram(calm_thr, bins=bins)
                if np.max(counts) > 0:
                    peak_idx = int(np.argmax(counts))
                    hover_pct = float((edges[peak_idx] + edges[peak_idx + 1]) / 2)

        # --- Diagnosis ---
        if mape < 3:
            diagnosis = "Linear"
            diag_detail = "Thrust curve is effectively linear. No strong need for thrust_linear."
            sev = Severity.INFO
        elif mape < 8:
            diagnosis = "Mild"
            diag_detail = "Mild non-linearity. Light thrust_linear may help."
            sev = Severity.INFO
        elif mape < 15:
            diagnosis = "Noticeable"
            diag_detail = "Noticeable non-linearity. High-throttle region likely inflating P/D gains."
            sev = Severity.WARNING
        else:
            diagnosis = "Severe"
            diag_detail = "Severe non-linearity. Controller operating on exaggerated thrust response."
            sev = Severity.WARNING

        # PID escalation insight
        pid_insight = ""
        if pid_effort_slope is not None:
            if pid_effort_slope > 0.03:
                pid_insight = "Strong upward PID effort escalation — classic TPA reliance."
            elif pid_effort_slope > 0.015:
                pid_insight = "Moderate PID escalation; partial TPA likely sufficient."
            else:
                pid_insight = "Low PID escalation; may reduce/remove TPA after linearisation."

        # --- Recommendations ---
        recs = [diag_detail]
        cli_cmds = []
        if mape >= 8:
            recs.append(
                "Apply thrust_linear first to flatten the curve, "
                "then retune P/D mid-band and reassess TPA."
            )
            # Suggest value: rough heuristic based on MAPE
            suggested_tl = max(0, min(150, int(mape * 5)))
            cli_cmds.append(f"set thrust_linear = {suggested_tl}")
        elif mape >= 3:
            recs.append("Optional mild thrust_linear if chasing consistent feel.")

        if pid_insight:
            recs.append(pid_insight)

        if onset_pct is not None:
            recs.append(f"Non-linear behaviour starts near {onset_pct:.0f}% throttle.")

        if hover_pct is not None:
            recs.append(f"Estimated hover throttle: {hover_pct:.0f}%.")

        desc = (
            f"Thrust Linearity: MAPE = {mape:.1f}% ({diagnosis})"
            f" | Onset at {onset_pct:.0f}%" if onset_pct else
            f"Thrust Linearity: MAPE = {mape:.1f}% ({diagnosis})"
        )

        data = {
            "type": "thrust_linearization",
            "mape": round(mape, 1),
            "diagnosis": diagnosis,
            "onset_pct": round(onset_pct, 1) if onset_pct else None,
            "pid_effort_slope": round(pid_effort_slope, 5) if pid_effort_slope else None,
            "hover_pct": round(hover_pct, 1) if hover_pct else None,
            "baseline_slope": round(m_base, 4),
            "baseline_intercept": round(b_base, 2),
            "thrust_curve": {
                "throttle_pct": thr_sorted[::max(1, n // 200)].tolist(),
                "motor_pct": mot_sorted[::max(1, n // 200)].tolist(),
                "predicted": predicted[::max(1, n // 200)].tolist(),
            },
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.MOTOR,
            title="Thrust Linearization",
            severity=sev,
            description=desc,
            explanation="\n".join(recs),
            cli_commands=cli_cmds if cli_cmds else None,
            data=data,
        ))
