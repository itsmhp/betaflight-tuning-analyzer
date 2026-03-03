"""
Anti-Gravity Tuning Assistant.

Detects throttle punch events and measures attitude drift (gyro
deviation) during them.  High drift indicates that Anti-Gravity
gain (or I-term behaviour) is insufficient to counteract the
torque change caused by rapid throttle transitions.

Algorithm (improved over FPV Nexus):
  1. Detect throttle punch-up / punch-down events
  2. Measure per-axis gyro drift during each punch window
  3. Compute drift magnitude  = √(roll² + pitch²)
  4. Classify severity and suggest Anti-Gravity gain adjustments
  5. Detect roll/pitch axis bias (>1.5× difference)
"""
from __future__ import annotations

import math
from typing import List, Dict, Any, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PUNCH_UP_RATIO = 0.35        # proportion of throttle range
PUNCH_DOWN_RATIO = 0.25
MIN_PUNCH_SAMPLES = 5        # minimum samples in a punch event
MIN_THROTTLE_VARIATION = 100  # minimum range to detect punches


def _detect_punches(
    throttle: np.ndarray,
) -> List[Dict[str, Any]]:
    """Detect punch-up and punch-down events from throttle data."""
    n = len(throttle)
    if n < 50:
        return []

    tmin = float(np.min(throttle))
    tmax = float(np.max(throttle))
    trange = tmax - tmin
    if trange < MIN_THROTTLE_VARIATION:
        return []

    up_thresh = PUNCH_UP_RATIO * trange
    down_thresh = PUNCH_DOWN_RATIO * trange

    # Compute per-sample delta (smoothed over 3 samples to reject noise)
    delta = np.diff(throttle, prepend=throttle[0])
    if n > 5:
        kernel = np.ones(3) / 3
        delta = np.convolve(delta, kernel, mode="same")

    events: List[Dict[str, Any]] = []
    in_event = False
    event_start = 0
    event_type = ""

    for i in range(n):
        if not in_event:
            if delta[i] > up_thresh / 10:  # rising fast
                in_event = True
                event_start = i
                event_type = "punch_up"
            elif delta[i] < -down_thresh / 10:  # falling fast
                in_event = True
                event_start = i
                event_type = "punch_down"
        else:
            # End event when delta returns to low magnitude
            if abs(delta[i]) < max(up_thresh, down_thresh) / 30:
                if i - event_start >= MIN_PUNCH_SAMPLES:
                    events.append({
                        "start": event_start,
                        "end": i,
                        "type": event_type,
                        "duration": i - event_start,
                        "throttle_change": float(throttle[i] - throttle[event_start]),
                    })
                in_event = False

    return events


def _compute_drift(
    flight_data,
    events: List[Dict[str, Any]],
    n: int,
) -> Dict[str, Any]:
    """Compute per-axis drift during punch events."""
    roll_drifts = []
    pitch_drifts = []
    yaw_drifts = []

    gyro_r = flight_data.gyro_roll
    gyro_p = flight_data.gyro_pitch
    gyro_y = flight_data.gyro_yaw

    if gyro_r is None or gyro_p is None:
        return {}

    for ev in events:
        s, e = ev["start"], min(ev["end"], n)
        if s >= n or e <= s:
            continue

        r_drift = float(np.mean(np.abs(gyro_r[s:e].astype(np.float64))))
        p_drift = float(np.mean(np.abs(gyro_p[s:e].astype(np.float64))))
        y_drift = float(np.mean(np.abs(gyro_y[s:e].astype(np.float64)))) if gyro_y is not None and len(gyro_y) >= e else 0.0

        roll_drifts.append(r_drift)
        pitch_drifts.append(p_drift)
        yaw_drifts.append(y_drift)

        ev["roll_drift"] = round(r_drift, 2)
        ev["pitch_drift"] = round(p_drift, 2)
        ev["yaw_drift"] = round(y_drift, 2)
        ev["magnitude"] = round(math.sqrt(r_drift ** 2 + p_drift ** 2), 2)

    if not roll_drifts:
        return {}

    avg_roll = float(np.mean(roll_drifts))
    avg_pitch = float(np.mean(pitch_drifts))
    avg_yaw = float(np.mean(yaw_drifts))
    avg_magnitude = math.sqrt(avg_roll ** 2 + avg_pitch ** 2)

    # Axis bias detection
    axis_bias = None
    if avg_roll > 0 and avg_pitch > 0:
        if avg_roll > 1.5 * avg_pitch:
            axis_bias = "Roll"
        elif avg_pitch > 1.5 * avg_roll:
            axis_bias = "Pitch"

    # Status classification
    if avg_magnitude < 15:
        status = "Excellent"
    elif avg_magnitude < 25:
        status = "Good"
    elif avg_magnitude < 35:
        status = "Moderate"
    elif avg_magnitude < 50:
        status = "Poor"
    else:
        status = "Critical"

    return {
        "avg_roll_drift": round(avg_roll, 2),
        "avg_pitch_drift": round(avg_pitch, 2),
        "avg_yaw_drift": round(avg_yaw, 2),
        "avg_magnitude": round(avg_magnitude, 2),
        "axis_bias": axis_bias,
        "status": status,
        "num_punches": len(events),
        "punch_up_count": sum(1 for e in events if e["type"] == "punch_up"),
        "punch_down_count": sum(1 for e in events if e["type"] == "punch_down"),
    }


class AntiGravityAnalyzer:
    """Anti-Gravity Tuning Assistant."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        throttle = flight_data.rc_command_throttle
        if throttle is None or len(throttle) < 200:
            return

        throttle_f = throttle.astype(np.float64)
        n = len(throttle_f)

        events = _detect_punches(throttle_f)
        if not events:
            return

        drift_info = _compute_drift(flight_data, events, n)
        if not drift_info:
            return

        mag = drift_info["avg_magnitude"]
        status = drift_info["status"]

        # Severity mapping
        if mag > 50:
            sev = Severity.ERROR
        elif mag > 25:
            sev = Severity.WARNING
        else:
            sev = Severity.INFO

        # Recommendations
        recs = []
        cli_cmds = []
        if mag > 50:
            recs.append(f"Drift magnitude {mag:.0f}°/s is critical. Increase anti_gravity_gain by 20-30%.")
            recs.append("Consider also increasing I-term gains by 10-15% if attitude doesn't hold.")
            cli_cmds.append("set anti_gravity_gain = 5000")
        elif mag > 25:
            recs.append(f"Drift magnitude {mag:.0f}°/s is elevated. Increase anti_gravity_gain by 10-15%.")
            cli_cmds.append("set anti_gravity_gain = 4500")
        elif mag > 15:
            recs.append(f"Drift magnitude {mag:.0f}°/s is acceptable but could be improved.")
        else:
            recs.append(f"Drift magnitude {mag:.0f}°/s. Anti-Gravity tuning is good.")

        if drift_info["axis_bias"]:
            recs.append(
                f"{drift_info['axis_bias']} axis shows significantly more drift. "
                f"Consider increasing I-term on {drift_info['axis_bias'].lower()} axis."
            )

        # Enhacement over Nexus: distinguish punch-up vs punch-down
        up_events = [e for e in events if e["type"] == "punch_up"]
        down_events = [e for e in events if e["type"] == "punch_down"]
        if up_events and down_events:
            up_mag = float(np.mean([e.get("magnitude", 0) for e in up_events]))
            down_mag = float(np.mean([e.get("magnitude", 0) for e in down_events]))
            if down_mag > 1.5 * up_mag:
                recs.append(
                    "Punch-down events cause more drift than punch-ups. "
                    "This may indicate prop wash during descents — see Prop Wash analysis."
                )
            elif up_mag > 1.5 * down_mag:
                recs.append(
                    "Punch-up events cause more drift. "
                    "Anti-Gravity is most needed for throttle increases."
                )

        desc = (
            f"Anti-Gravity Status: {status} | "
            f"Drift: {mag:.1f}°/s | "
            f"Punches: {drift_info['num_punches']} "
            f"(↑{drift_info['punch_up_count']} ↓{drift_info['punch_down_count']})"
        )

        data = {
            "type": "anti_gravity_analysis",
            "drift_info": drift_info,
            "events_summary": events[:30],
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.PID,
            title="Anti-Gravity Tuning",
            severity=sev,
            description=desc,
            explanation="\n".join(recs),
            cli_commands=cli_cmds if cli_cmds else None,
            data=data,
        ))
