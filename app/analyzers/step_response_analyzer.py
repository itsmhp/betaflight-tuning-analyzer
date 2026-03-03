"""
PID Step Response Analyzer – Detailed PID Visualization.

Based on the analysis approach used in professional FPV tuning tools:
  - Detects manoeuvre segments from setpoint data
  - Averages multiple step responses
  - Computes: setpoint error, gyro noise level, PID quality score,
    settling time, rise time, damping ratio, overshoot, oscillations,
    peak timing diff, phase margin (estimated)
  - Produces step response chart data per axis (Roll/Pitch/Yaw)
"""
from __future__ import annotations

import math
from typing import Optional, List, Dict, Any, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Thresholds & rating helpers
# ---------------------------------------------------------------------------

def _rate_setpoint_error(pct: float) -> Tuple[str, Severity]:
    if pct <= 5:
        return "Good", Severity.INFO
    if pct <= 10:
        return "OK", Severity.WARNING
    if pct <= 20:
        return "Poor", Severity.WARNING
    return "Looking Rough", Severity.ERROR


def _rate_gyro_noise(pct: float) -> Tuple[str, Severity]:
    if pct <= 2:
        return "Excellent", Severity.INFO
    if pct <= 5:
        return "OK", Severity.WARNING
    if pct <= 15:
        return "Poor", Severity.WARNING
    return "Poor", Severity.ERROR


def _rate_pid_quality(score: float) -> Tuple[str, Severity]:
    if score >= 80:
        return "Excellent", Severity.INFO
    if score >= 60:
        return "Good", Severity.INFO
    if score >= 40:
        return "Fair", Severity.WARNING
    return "Poor", Severity.ERROR


def _rate_settling(frames: int, total: int) -> Tuple[str, Severity]:
    ratio = frames / max(total, 1)
    if ratio <= 0.3:
        return "Excellent", Severity.INFO
    if ratio <= 0.6:
        return "Good", Severity.INFO
    return "Slow", Severity.WARNING


def _rate_rise_time(frames: int, total: int) -> Tuple[str, Severity]:
    ratio = frames / max(total, 1)
    if ratio <= 0.15:
        return "Excellent", Severity.INFO
    if ratio <= 0.3:
        return "Good", Severity.INFO
    return "Slow", Severity.WARNING


def _rate_damping(dr: float) -> Tuple[str, Severity]:
    if 0.6 <= dr <= 1.0:
        return "Excellent", Severity.INFO
    if 0.4 <= dr <= 1.2:
        return "Fair", Severity.WARNING
    return "Poor", Severity.ERROR


def _rate_peak_timing(diff: int) -> Tuple[str, Severity]:
    if abs(diff) <= 3:
        return "Perfect", Severity.INFO
    if abs(diff) <= 8:
        return "Good", Severity.INFO
    if diff > 8:
        return "Slow (Over)", Severity.WARNING
    return "Fast (Under)", Severity.WARNING


def _rate_oscillations(count: int) -> Tuple[str, Severity]:
    if count == 0:
        return "Perfect", Severity.INFO
    if count <= 2:
        return "Minor", Severity.WARNING
    return "Excessive", Severity.ERROR


# ---------------------------------------------------------------------------
# Manoeuvre detection
# ---------------------------------------------------------------------------

def _detect_manoeuvres(
    setpoint: np.ndarray,
    response: np.ndarray,
    p_term: Optional[np.ndarray] = None,
    d_term: Optional[np.ndarray] = None,
) -> List[Dict[str, np.ndarray]]:
    """
    Detect manoeuvre segments where |setpoint| exceeds a dynamic threshold.
    Returns list of dicts with 'setpoint', 'response', 'p', 'd' arrays.
    """
    n = len(setpoint)
    if n < 100:
        return []

    abs_sp = np.abs(setpoint)
    max_sp = float(np.max(abs_sp))
    if max_sp < 5:
        return []

    threshold = max(30.0, min(100.0, 0.5 * max_sp))
    lookback = 10
    min_len = 50

    def _scan(thresh):
        segs = []
        in_step = False
        start = 0
        for i in range(n):
            if abs_sp[i] > thresh and not in_step:
                in_step = True
                start = max(0, i - lookback)
            if in_step and abs_sp[i] < thresh:
                length = i - start
                if length >= min_len:
                    seg = {
                        "setpoint": setpoint[start:i].copy(),
                        "response": response[start:i].copy(),
                    }
                    if p_term is not None:
                        seg["p"] = p_term[start:i].copy()
                    if d_term is not None:
                        seg["d"] = d_term[start:i].copy()
                    segs.append(seg)
                in_step = False
        # close trailing segment
        if in_step and (n - start) >= min_len:
            seg = {
                "setpoint": setpoint[start:].copy(),
                "response": response[start:].copy(),
            }
            if p_term is not None:
                seg["p"] = p_term[start:].copy()
            if d_term is not None:
                seg["d"] = d_term[start:].copy()
            segs.append(seg)
        return segs

    segments = _scan(threshold)
    # Fallback: lower threshold
    if not segments and threshold > 30:
        segments = _scan(20.0)
    # Fallback: entire dataset
    if not segments:
        seg = {"setpoint": setpoint.copy(), "response": response.copy()}
        if p_term is not None:
            seg["p"] = p_term.copy()
        if d_term is not None:
            seg["d"] = d_term.copy()
        segments = [seg]

    return segments


def _average_manoeuvres(segments: List[Dict[str, np.ndarray]]) -> Dict[str, np.ndarray]:
    """Average manoeuvre segments, zero-padding to max length, using absolute values."""
    max_len = max(len(s["setpoint"]) for s in segments)
    keys = list(segments[0].keys())
    sums = {k: np.zeros(max_len) for k in keys}
    counts = np.zeros(max_len)

    for seg in segments:
        seg_len = len(seg["setpoint"])
        for k in keys:
            if k in seg:
                arr = np.abs(seg[k][:seg_len])
                sums[k][:seg_len] += arr
        counts[:seg_len] += 1

    counts = np.maximum(counts, 1)
    return {k: sums[k] / counts for k in keys}


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def _compute_metrics(
    setpoint_arr: np.ndarray,
    response_arr: np.ndarray,
) -> Dict[str, Any]:
    """Compute the full set of step response metrics."""
    n = len(setpoint_arr)
    peak_sp = float(np.max(setpoint_arr)) if n > 0 else 0
    peak_resp = float(np.max(response_arr)) if n > 0 else 0

    # --- Rise time (10% → 90% of peak setpoint) ---
    thresh_10 = 0.1 * peak_sp
    thresh_90 = 0.9 * peak_sp
    idx_10 = idx_90 = -1
    for i in range(n):
        if idx_10 == -1 and response_arr[i] >= thresh_10:
            idx_10 = i
        if idx_90 == -1 and response_arr[i] >= thresh_90:
            idx_90 = i
            break
    rise_time = (idx_90 - idx_10) if (idx_10 >= 0 and idx_90 >= 0) else n

    # --- Settling time (±5% of peak, min ±5, band around final) ---
    final_val = float(response_arr[-1]) if n > 0 else 0
    tolerance = max(0.05 * peak_sp, 5.0)
    upper = final_val + tolerance
    lower = final_val - tolerance
    settling_idx = 0
    for i in range(n - 1, -1, -1):
        if response_arr[i] > upper or response_arr[i] < lower:
            settling_idx = i + 1
            break

    # --- Overshoot ---
    overshoot = max(0, peak_resp - peak_sp)

    # --- Damping ratio from overshoot ---
    damping_ratio = 1.0
    if overshoot > 0 and peak_sp > 0:
        os_ratio = min(0.99, overshoot / peak_sp)
        if os_ratio > 0.01:
            ln_os = math.log(os_ratio)
            zeta = -ln_os / math.sqrt(math.pi ** 2 + ln_os ** 2)
            if 0 <= zeta <= 2 and math.isfinite(zeta):
                damping_ratio = zeta

    # --- Peak timing difference ---
    sp_peak_idx = int(np.argmax(setpoint_arr))
    resp_peak_idx = int(np.argmax(response_arr))
    peak_timing_diff = resp_peak_idx - sp_peak_idx

    # Adjust damping for under/over-damped
    is_underdamped = False
    is_overdamped = False
    if peak_timing_diff < -8:
        is_underdamped = True
        damping_ratio = min(2.0, damping_ratio + 0.3)
    elif peak_timing_diff > 8 or rise_time > 0.8 * n:
        is_overdamped = True
        damping_ratio = max(0.1, damping_ratio - 0.4)

    # --- Oscillation count (post-settling) ---
    oscillations = 0
    if settling_idx < n - 1:
        window_len = min(50, n - settling_idx)
        post = response_arr[settling_idx:settling_idx + window_len]
        if len(post) > 5:
            osc_thresh = 0.03 * abs(final_val) if abs(final_val) > 1 else 1.0
            crossings = 0
            last_sign = 0
            run_length = 0
            for i in range(1, len(post)):
                dev = post[i] - final_val
                sign_dev = (1 if dev > 0 else (-1 if dev < 0 else 0))
                if abs(dev) > osc_thresh:
                    if sign_dev != last_sign and last_sign != 0:
                        crossings += 1
                        run_length = 1
                    else:
                        run_length += 1
                    last_sign = sign_dev
                else:
                    run_length = 0
                    last_sign = 0
                if run_length >= 3:
                    crossings = max(0, crossings - 0.5)
            oscillations = int(crossings // 2)
            # Rapid triple sign change in first 20 samples
            early = post[:min(20, len(post))]
            rapid = 0
            for i in range(2, len(early)):
                d0 = early[i - 2] - final_val
                d1 = early[i - 1] - final_val
                d2 = early[i] - final_val
                s0 = (1 if d0 > 0 else -1) if abs(d0) > osc_thresh else 0
                s1 = (1 if d1 > 0 else -1) if abs(d1) > osc_thresh else 0
                s2 = (1 if d2 > 0 else -1) if abs(d2) > osc_thresh else 0
                if s0 != 0 and s1 != 0 and s2 != 0 and s0 != s1 and s1 != s2:
                    rapid += 1
            oscillations += rapid // 2

    # --- Phase margin estimate ---
    phase_margin = min(90, round(100 * damping_ratio)) if damping_ratio > 0 else 0

    return {
        "rise_time": rise_time,
        "settling_time": settling_idx,
        "overshoot": round(overshoot, 2),
        "damping_ratio": round(damping_ratio, 2),
        "peak_timing_diff": peak_timing_diff,
        "oscillations": oscillations,
        "phase_margin": phase_margin,
        "is_underdamped": is_underdamped,
        "is_overdamped": is_overdamped,
        "total_length": n,
    }


def _compute_setpoint_error(
    raw_setpoint: np.ndarray,
    raw_response: np.ndarray,
) -> float:
    """Mean absolute error as % of mean absolute setpoint."""
    n = min(len(raw_setpoint), len(raw_response))
    if n < 10:
        return 0.0
    sp = raw_setpoint[:n]
    resp = raw_response[:n]
    mean_abs_err = float(np.mean(np.abs(sp - resp)))
    mean_abs_sp = float(np.mean(np.abs(sp)))
    if mean_abs_sp < 1:
        return 0.0
    return (mean_abs_err / mean_abs_sp) * 100.0


def _compute_gyro_noise(
    raw_data_setpoint: np.ndarray,
    raw_data_response: np.ndarray,
    quiet_thresh: float = 20.0,
    ema_alpha: float = 0.05,
) -> float:
    """
    Gyro noise level as %.
    Collect response during low-setpoint periods, EMA smooth, RMS residual.
    """
    n = min(len(raw_data_setpoint), len(raw_data_response))
    if n < 20:
        return 0.0
    sp = raw_data_setpoint[:n]
    resp = raw_data_response[:n]

    # Quiet samples where |setpoint| < threshold
    quiet_mask = np.abs(sp) < quiet_thresh
    quiet = resp[quiet_mask]
    if len(quiet) < 10:
        return 0.0

    # EMA low-pass
    smoothed = np.empty_like(quiet)
    smoothed[0] = quiet[0]
    for i in range(1, len(quiet)):
        smoothed[i] = ema_alpha * quiet[i] + (1 - ema_alpha) * smoothed[i - 1]

    # RMS of residual
    rms_noise = float(np.sqrt(np.mean((quiet - smoothed) ** 2)))

    # Normalizer from active setpoint magnitudes
    active_mask = (np.abs(sp) >= 20) & (np.abs(sp) <= 1200)
    active_sp = np.abs(sp[active_mask])
    normalizer = 300.0
    if len(active_sp) > 0:
        normalizer = max(float(np.mean(active_sp)), 250.0)

    return (rms_noise / normalizer) * 100.0


def _compute_pid_quality(
    setpoint_error_pct: float,
    overshoot: float,
    gyro_noise_pct: float,
    rise_time: int,
    total_length: int,
) -> float:
    """PID quality score (0–100)."""
    score = (100.0
             - 0.8 * setpoint_error_pct
             - 0.15 * overshoot
             - 0.4 * gyro_noise_pct
             - (rise_time / max(1, total_length)) * 20.0)
    return max(0.0, min(100.0, score))


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class StepResponseAnalyzer:
    """Analyze PID step response: per-axis metrics + chart data."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        """Run step response analysis on each axis and add findings."""
        axis_names = ["Roll", "Pitch", "Yaw"]

        for axis_idx, axis_name in enumerate(axis_names):
            sp = flight_data.setpoint[axis_idx]
            gyro = flight_data.gyro_filtered[axis_idx]
            if sp is None or gyro is None:
                continue
            n = min(len(sp), len(gyro))
            if n < 200:
                continue

            sp_arr = sp[:n].astype(np.float64)
            gyro_arr = gyro[:n].astype(np.float64)

            p_term = None
            d_term = None
            pids_p = flight_data.pid_p
            pids_d = flight_data.pid_d
            if pids_p and pids_p[axis_idx] is not None and len(pids_p[axis_idx]) >= n:
                p_term = pids_p[axis_idx][:n].astype(np.float64)
            if pids_d and pids_d[axis_idx] is not None and len(pids_d[axis_idx]) >= n:
                d_term = pids_d[axis_idx][:n].astype(np.float64)

            # Detect manoeuvres
            segments = _detect_manoeuvres(sp_arr, gyro_arr, p_term, d_term)
            if not segments:
                continue

            # Average manoeuvres
            averaged = _average_manoeuvres(segments)
            avg_sp = averaged["setpoint"]
            avg_resp = averaged["response"]

            # Compute metrics on averaged response
            metrics = _compute_metrics(avg_sp, avg_resp)

            # Setpoint error on full raw data
            setpoint_error = _compute_setpoint_error(sp_arr, gyro_arr)

            # Gyro noise on full raw data
            gyro_noise = _compute_gyro_noise(sp_arr, gyro_arr)

            # PID quality
            pid_quality = _compute_pid_quality(
                setpoint_error,
                metrics["overshoot"],
                gyro_noise,
                metrics["rise_time"],
                metrics["total_length"],
            )

            # Rating labels
            sp_err_label, sp_err_sev = _rate_setpoint_error(setpoint_error)
            noise_label, noise_sev = _rate_gyro_noise(gyro_noise)
            pq_label, pq_sev = _rate_pid_quality(pid_quality)
            settle_label, _ = _rate_settling(metrics["settling_time"], metrics["total_length"])
            rise_label, _ = _rate_rise_time(metrics["rise_time"], metrics["total_length"])
            damp_label, damp_sev = _rate_damping(metrics["damping_ratio"])
            pt_label, pt_sev = _rate_peak_timing(metrics["peak_timing_diff"])
            osc_label, osc_sev = _rate_oscillations(metrics["oscillations"])

            # Overall severity = worst of key metrics
            overall_sev = max(sp_err_sev, noise_sev, pq_sev, damp_sev, osc_sev,
                              key=lambda s: s.value)

            # Build finding data dict
            data = {
                "type": "step_response",
                "axis": axis_name,
                # Top-row metrics
                "setpoint_error_pct": round(setpoint_error, 2),
                "setpoint_error_label": sp_err_label,
                "gyro_noise_pct": round(gyro_noise, 2),
                "gyro_noise_label": noise_label,
                "pid_quality": round(pid_quality, 1),
                "pid_quality_label": pq_label,
                # Detail metrics
                "settling_time": metrics["settling_time"],
                "settling_label": settle_label,
                "rise_time": metrics["rise_time"],
                "rise_label": rise_label,
                "damping_ratio": metrics["damping_ratio"],
                "damping_label": damp_label,
                "peak_timing_diff": metrics["peak_timing_diff"],
                "peak_timing_label": pt_label,
                "oscillations": metrics["oscillations"],
                "oscillation_label": osc_label,
                "phase_margin": metrics["phase_margin"],
                "overshoot": metrics["overshoot"],
                "is_underdamped": metrics["is_underdamped"],
                "is_overdamped": metrics["is_overdamped"],
                # Chart data (downsampled averages)
                "chart_setpoint": avg_sp.tolist(),
                "chart_response": avg_resp.tolist(),
                "chart_p_term": averaged.get("p", avg_sp * 0).tolist(),
                "chart_d_term": averaged.get("d", avg_sp * 0).tolist(),
            }

            # Build explanation lines
            lines = []
            if metrics["is_underdamped"]:
                lines.append("Response is UNDERDAMPED — consider reducing P gain or increasing D gain.")
            if metrics["is_overdamped"]:
                lines.append("Response is OVERDAMPED — consider increasing P gain.")
            if metrics["oscillations"] > 0:
                lines.append(f"{metrics['oscillations']} oscillation cycle(s) detected post-settling.")
            if setpoint_error > 15:
                lines.append("High setpoint error — PID gains may be too low.")
            if gyro_noise > 10:
                lines.append("High gyro noise level — check filters and motor/prop balance.")

            desc = (
                f"Setpoint Error {setpoint_error:.1f}% ({sp_err_label}), "
                f"Gyro Noise {gyro_noise:.1f}% ({noise_label}), "
                f"PID Quality {pid_quality:.0f}% ({pq_label})"
            )

            report.add_finding(Finding(
                category=Category.PID,
                title=f"{axis_name} Axis Step Response",
                severity=overall_sev,
                description=desc,
                explanation="\n".join(lines) if lines else "Step response looks reasonable.",
                data=data,
            ))
