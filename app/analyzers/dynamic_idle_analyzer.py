"""
Dynamic Idle Analyzer – determines optimal dynamic idle RPM setting.

Detects stable ground-idle windows from flight data by analysing:
  - Gyro stillness (low angular rates)
  - Throttle baseline (near minimum)
  - Motor minimum values
  - ERPM data when available

Implements adaptive relaxation with 2 passes for threshold
widening, selects best segment by length then variance, and
suggests a dynamic_idle_min_rpm value.

Based on the analysis approach used in professional FPV tuning tools.
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GYRO_STILLNESS_THRESHOLD = 12.0  # deg/s, all axes
THROTTLE_MARGIN = 3.0  # above baseline
MOTOR_MARGIN = 8.0  # above per-motor minimum
FIRST_30S_SAMPLES = None  # computed from sample rate

# Adaptive relaxation multipliers
RELAXATION_PASSES = [
    {"gyro": 1.0, "throttle": 1.0, "motor": 1.0},
    {"gyro": 1.5, "throttle": 1.5, "motor": 1.5},
]

MIN_SEGMENT_SAMPLES = 50  # minimum idle segment length


# ---------------------------------------------------------------------------
# Baseline detection
# ---------------------------------------------------------------------------

def _throttle_baseline(throttle: np.ndarray) -> float:
    """Throttle baseline = min(min_value, 5th percentile)."""
    return float(min(np.min(throttle), np.percentile(throttle, 5)))


def _motor_minimums(
    flight_data,
    first_n: int,
) -> List[float]:
    """Per-motor minimum from first `first_n` samples."""
    mins = []
    for m in range(4):
        if flight_data.motor[m] is not None:
            data = flight_data.motor[m][:first_n].astype(np.float64)
            mins.append(float(np.min(data)))
        else:
            mins.append(0.0)
    return mins


# ---------------------------------------------------------------------------
# Idle window detection
# ---------------------------------------------------------------------------

def _detect_idle_windows(
    flight_data,
    sample_rate: float,
    relaxation: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Find contiguous idle segments where:
      - all gyro axes < GYRO_STILLNESS_THRESHOLD * relax
      - throttle <= baseline + THROTTLE_MARGIN * relax
      - each motor <= motorMin + MOTOR_MARGIN * relax
    """
    first_30s = int(min(sample_rate * 30, 100000))
    n = len(flight_data.gyro_roll) if flight_data.gyro_roll is not None else 0
    if n < 100:
        return []

    # Get throttle
    throttle = None
    if flight_data.rc_command_throttle is not None:
        throttle = flight_data.rc_command_throttle[:n].astype(np.float64)
    elif flight_data.setpoint_throttle is not None:
        throttle = flight_data.setpoint_throttle[:n].astype(np.float64)

    if throttle is None or len(throttle) < 100:
        return []

    baseline = _throttle_baseline(throttle)
    motor_mins = _motor_minimums(flight_data, first_30s)

    gyro_thresh = GYRO_STILLNESS_THRESHOLD * relaxation["gyro"]
    thr_thresh = baseline + THROTTLE_MARGIN * relaxation["throttle"]
    mot_margin = MOTOR_MARGIN * relaxation["motor"]

    # Build per-sample boolean mask
    is_idle = np.ones(n, dtype=bool)

    # Gyro check
    for g in [flight_data.gyro_roll, flight_data.gyro_pitch, flight_data.gyro_yaw]:
        if g is not None and len(g) >= n:
            is_idle &= np.abs(g[:n].astype(np.float64)) < gyro_thresh

    # Throttle check
    is_idle &= throttle[:n] <= thr_thresh

    # Motor check
    for m_idx in range(4):
        if flight_data.motor[m_idx] is not None and len(flight_data.motor[m_idx]) >= n:
            mot_data = flight_data.motor[m_idx][:n].astype(np.float64)
            is_idle &= mot_data <= (motor_mins[m_idx] + mot_margin)

    # Extract contiguous segments
    segments = []
    in_seg = False
    seg_start = 0
    for i in range(n):
        if is_idle[i] and not in_seg:
            in_seg = True
            seg_start = i
        elif not is_idle[i] and in_seg:
            in_seg = False
            seg_len = i - seg_start
            if seg_len >= MIN_SEGMENT_SAMPLES:
                segments.append({
                    "start": seg_start,
                    "end": i,
                    "length": seg_len,
                    "duration_ms": round(seg_len / sample_rate * 1000, 1),
                })

    if in_seg:
        seg_len = n - seg_start
        if seg_len >= MIN_SEGMENT_SAMPLES:
            segments.append({
                "start": seg_start,
                "end": n,
                "length": seg_len,
                "duration_ms": round(seg_len / sample_rate * 1000, 1),
            })

    return segments


# ---------------------------------------------------------------------------
# Select best segment
# ---------------------------------------------------------------------------

def _select_best_segment(
    segments: List[Dict[str, Any]],
    flight_data,
) -> Optional[Dict[str, Any]]:
    """Select best idle segment: longest first, then lowest motor variance."""
    if not segments:
        return None

    # Sort by length descending, then by motor variance ascending
    def segment_score(seg):
        start, end = seg["start"], seg["end"]
        motor_var = 0.0
        count = 0
        for m_idx in range(4):
            if flight_data.motor[m_idx] is not None:
                m_data = flight_data.motor[m_idx][start:end].astype(np.float64)
                motor_var += float(np.var(m_data))
                count += 1
        avg_var = motor_var / max(count, 1)
        seg["motor_variance"] = round(avg_var, 2)
        return (-seg["length"], avg_var)

    segments.sort(key=segment_score)
    return segments[0]


# ---------------------------------------------------------------------------
# Idle RPM computation
# ---------------------------------------------------------------------------

def _compute_idle_rpm(
    flight_data,
    segment: Dict[str, Any],
    bbl_header,
) -> Dict[str, Any]:
    """
    Compute per-motor idle RPM from ERPM data or motor output.
    """
    start, end = segment["start"], segment["end"]
    motor_values = []
    per_motor = []

    for m_idx in range(4):
        # Try ERPM first
        erpm = flight_data.erpm[m_idx] if hasattr(flight_data, 'erpm') and flight_data.erpm[m_idx] is not None else None
        if erpm is not None and len(erpm) >= end:
            m_data = erpm[start:end].astype(np.float64)
            motor_values.append(m_data)
            avg_val = float(np.mean(m_data))
            # ERPM → RPM: ERPM / (motor_poles / 2)
            motor_poles = getattr(bbl_header, 'motor_poles', 14)
            rpm = avg_val / (motor_poles / 2)
            per_motor.append({
                "motor": m_idx + 1,
                "avg_erpm": round(avg_val, 0),
                "avg_rpm": round(rpm, 0),
                "std_erpm": round(float(np.std(m_data)), 1),
                "source": "erpm",
            })
        elif flight_data.motor[m_idx] is not None and len(flight_data.motor[m_idx]) >= end:
            m_data = flight_data.motor[m_idx][start:end].astype(np.float64)
            motor_values.append(m_data)
            avg_val = float(np.mean(m_data))
            per_motor.append({
                "motor": m_idx + 1,
                "avg_output": round(avg_val, 1),
                "std_output": round(float(np.std(m_data)), 1),
                "source": "motor_output",
            })

    # Compute average idle RPM (if ERPM available)
    erpm_motors = [m for m in per_motor if m["source"] == "erpm"]
    if erpm_motors:
        avg_idle_rpm = sum(m["avg_rpm"] for m in erpm_motors) / len(erpm_motors)
        suggested = int(round(avg_idle_rpm / 100)) * 100
    else:
        avg_idle_rpm = None
        suggested = None

    return {
        "per_motor": per_motor,
        "avg_idle_rpm": round(avg_idle_rpm, 0) if avg_idle_rpm else None,
        "suggested_setting": suggested,
    }


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class DynamicIdleAnalyzer:
    """Dynamic Idle Analyzer – optimal idle RPM from ground/hover idle data."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        """Run dynamic idle analysis."""
        sample_rate = bbl_header.get_blackbox_sample_rate()
        if sample_rate <= 0:
            return

        # Multi-pass detection with adaptive relaxation
        all_segments: List[Dict[str, Any]] = []
        for pass_params in RELAXATION_PASSES:
            segments = _detect_idle_windows(flight_data, sample_rate, pass_params)
            if segments:
                all_segments = segments
                break

        if not all_segments:
            # No idle windows found — report that
            report.add_finding(Finding(
                category=Category.MOTOR,
                title="Dynamic Idle Analysis",
                severity=Severity.INFO,
                description="No stable ground idle windows detected in the log.",
                explanation=(
                    "The log may not contain ground idle data (arming → takeoff with no pause). "
                    "Try recording a few seconds of ground idle before takeoff."
                ),
                data={"type": "dynamic_idle_analysis", "segments_found": 0},
            ))
            return

        # Select best segment
        best = _select_best_segment(all_segments, flight_data)
        if best is None:
            return

        # Compute idle RPM
        idle_info = _compute_idle_rpm(flight_data, best, bbl_header)

        # CLI commands
        cli_cmds = []
        if idle_info["suggested_setting"] is not None:
            suggested = idle_info["suggested_setting"]
            cli_cmds.append(f"set dyn_idle_min_rpm = {suggested}")
            cli_cmds.append("set dyn_idle_p_gain = 50")
            cli_cmds.append("set dyn_idle_i_gain = 50")
            cli_cmds.append("set dyn_idle_d_gain = 50")

        # Build description
        seg_dur = best["duration_ms"]
        if idle_info["avg_idle_rpm"] is not None:
            desc = (
                f"Idle Window: {seg_dur:.0f} ms | "
                f"Avg Idle RPM: {idle_info['avg_idle_rpm']:.0f} | "
                f"Suggested: {idle_info['suggested_setting']} RPM"
            )
        else:
            desc = (
                f"Idle Window: {seg_dur:.0f} ms | "
                f"Segments Found: {len(all_segments)} | "
                "ERPM data not available — suggestion based on motor output"
            )

        explanation_lines = [
            f"Detected {len(all_segments)} idle segment(s). Best segment: {seg_dur:.0f} ms.",
        ]
        for m_info in idle_info["per_motor"]:
            if m_info["source"] == "erpm":
                explanation_lines.append(
                    f"  Motor {m_info['motor']}: {m_info['avg_rpm']:.0f} RPM "
                    f"(σ = {m_info['std_erpm']:.1f})"
                )
            else:
                explanation_lines.append(
                    f"  Motor {m_info['motor']}: output = {m_info['avg_output']:.1f} "
                    f"(σ = {m_info['std_output']:.1f})"
                )

        if idle_info["suggested_setting"] is not None:
            explanation_lines.append(
                f"\nSuggested dyn_idle_min_rpm = {idle_info['suggested_setting']}."
            )

        data = {
            "type": "dynamic_idle_analysis",
            "segments_found": len(all_segments),
            "best_segment": {
                "start": best["start"],
                "end": best["end"],
                "duration_ms": best["duration_ms"],
                "motor_variance": best.get("motor_variance", 0),
            },
            "idle_info": idle_info,
            "cli_commands": cli_cmds,
        }

        report.add_finding(Finding(
            category=Category.MOTOR,
            title="Dynamic Idle Analysis",
            severity=Severity.INFO,
            description=desc,
            explanation="\n".join(explanation_lines),
            cli_commands=cli_cmds if cli_cmds else None,
            data=data,
        ))
