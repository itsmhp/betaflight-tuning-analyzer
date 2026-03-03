"""
TPA Analyzer – Throttle PID Attenuation.

Determines optimal TPA breakpoint and rate by analysing D-term energy
vs throttle position. Implements 4 breakpoint detection methods:
  1. Threshold crossing (MAD-based)
  2. Gradient knee (2nd derivative max)
  3. Rise ratio ≥ 1.6
  4. Piecewise SSE (two-segment fit)

Also computes RMS ratio (high/low throttle), P95 peak noise, and
PID escalation metric.

Based on the analysis approach used in professional FPV tuning tools.
"""
from __future__ import annotations

import math
from typing import Optional, List, Dict, Any, Tuple

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_THROTTLE_FOR_SCAN = 0.1
SMOOTHING_WINDOW = 25
NUM_BUCKETS = 40  # each bucket = 2.5% throttle
LOW_THROTTLE_MAX = 0.35
HIGH_THROTTLE_MIN = 0.65


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _moving_average(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple causal moving average."""
    out = np.empty_like(arr)
    cumsum = np.cumsum(arr)
    for i in range(len(arr)):
        start = max(0, i - window + 1)
        out[i] = (cumsum[i] - (cumsum[start - 1] if start > 0 else 0)) / (i - start + 1)
    return out


def _median(arr: np.ndarray) -> float:
    """Median of non-zero values."""
    v = arr[arr > 0]
    if len(v) == 0:
        return 0.0
    return float(np.median(v))


def _mad(arr: np.ndarray, med: float) -> float:
    """Median absolute deviation."""
    v = arr[arr > 0]
    if len(v) == 0:
        return 0.0
    return float(np.median(np.abs(v - med)))


def _percentile(arr: np.ndarray, p: float) -> float:
    if len(arr) == 0:
        return 0.0
    return float(np.percentile(arr, p))


# ---------------------------------------------------------------------------
# D-term energy computation
# ---------------------------------------------------------------------------

def _compute_dterm_energy(
    flight_data,
    throttle_norm: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (dterm_energy, smoothed_energy, throttle_norm) arrays.
    Uses actual D-term axes if available, otherwise gyro derivative.
    """
    n = len(throttle_norm)

    # Try actual D-term columns
    d_axes = []
    for ax in range(3):
        d = flight_data.pid_d[ax]
        if d is not None and len(d) >= n:
            d_axes.append(d[:n].astype(np.float64))

    if d_axes:
        # RMS across axes per sample
        stacked = np.stack(d_axes, axis=0)
        energy = np.sqrt(np.mean(stacked ** 2, axis=0))
    else:
        # Gyro derivative proxy
        gyro_arrays = []
        for g in [flight_data.gyro_roll, flight_data.gyro_pitch, flight_data.gyro_yaw]:
            if g is not None and len(g) >= n:
                gyro_arrays.append(g[:n].astype(np.float64))
        if not gyro_arrays:
            return np.zeros(n), np.zeros(n), throttle_norm

        diffs = [np.diff(g, prepend=g[0]) for g in gyro_arrays]
        stacked = np.stack(diffs, axis=0)
        energy = np.sqrt(np.sum(stacked ** 2, axis=0))

    smoothed = _moving_average(energy, SMOOTHING_WINDOW)
    return energy, smoothed, throttle_norm


# ---------------------------------------------------------------------------
# Bucketing
# ---------------------------------------------------------------------------

def _bucket_dterm(
    smoothed: np.ndarray,
    throttle_norm: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Average D-term energy per throttle bucket.
    Returns (bucket_means, bucket_counts) of shape (NUM_BUCKETS,).
    """
    sums = np.zeros(NUM_BUCKETS)
    counts = np.zeros(NUM_BUCKETS, dtype=np.int64)

    for i in range(len(throttle_norm)):
        if throttle_norm[i] < MIN_THROTTLE_FOR_SCAN:
            continue
        bucket = min(int(throttle_norm[i] * NUM_BUCKETS), NUM_BUCKETS - 1)
        sums[bucket] += smoothed[i]
        counts[bucket] += 1

    means = np.zeros(NUM_BUCKETS)
    mask = counts > 0
    means[mask] = sums[mask] / counts[mask]
    return means, counts


# ---------------------------------------------------------------------------
# Breakpoint detection
# ---------------------------------------------------------------------------

def _detect_breakpoint(
    bucket_means: np.ndarray,
    bucket_counts: np.ndarray,
) -> Dict[str, Any]:
    """Run 4 detection methods, score, and pick best breakpoint."""

    # Threshold from low-throttle buckets
    min_bucket = max(0, int(MIN_THROTTLE_FOR_SCAN * NUM_BUCKETS))
    upper_bucket = min(NUM_BUCKETS, min_bucket + int(0.15 * NUM_BUCKETS))
    low_buckets = bucket_means[min_bucket:upper_bucket]
    low_valid = low_buckets[low_buckets > 0]

    if len(low_valid) < 2:
        baseline_med = float(np.median(bucket_means[bucket_means > 0])) if np.any(bucket_means > 0) else 1.0
    else:
        baseline_med = float(np.median(low_valid))

    baseline_mad = _mad(low_valid, baseline_med) if len(low_valid) >= 2 else baseline_med * 0.1
    threshold_val = baseline_med + 3 * baseline_mad

    candidates: List[Dict[str, Any]] = []

    # Method 1: Threshold crossing
    for b in range(min_bucket, NUM_BUCKETS):
        if bucket_counts[b] > 5 and bucket_means[b] > threshold_val:
            bp_pct = (b + 0.5) / NUM_BUCKETS * 100
            ratio = bucket_means[b] / bucket_means[max(0, b - 1)] if bucket_means[max(0, b - 1)] > 0 else 1.0
            candidates.append({
                "method": "threshold",
                "bucket": b,
                "breakpoint_pct": bp_pct,
                "magnitude": bucket_means[b],
                "rise_ratio": ratio,
                "bonus": 1.0,
            })
            break

    # Method 2: Gradient knee (max 2nd derivative)
    max_2nd = 0
    best_b2 = -1
    for b in range(min_bucket + 2, NUM_BUCKETS):
        if bucket_counts[b] > 4:
            d2 = bucket_means[b] - 2 * bucket_means[b - 1] + bucket_means[b - 2]
            if d2 > max_2nd:
                max_2nd = d2
                best_b2 = b
    if best_b2 >= 0:
        bp_pct = (best_b2 + 0.5) / NUM_BUCKETS * 100
        ratio = bucket_means[best_b2] / bucket_means[max(0, best_b2 - 1)] if bucket_means[max(0, best_b2 - 1)] > 0 else 1.0
        candidates.append({
            "method": "gradient_knee",
            "bucket": best_b2,
            "breakpoint_pct": bp_pct,
            "magnitude": bucket_means[best_b2],
            "rise_ratio": ratio,
            "bonus": 0.9,
        })

    # Method 3: Rise ratio >= 1.6
    for b in range(min_bucket + 1, NUM_BUCKETS):
        if bucket_counts[b] > 4 and bucket_means[b - 1] > 0:
            ratio = bucket_means[b] / bucket_means[b - 1]
            if ratio >= 1.6:
                bp_pct = (b + 0.5) / NUM_BUCKETS * 100
                candidates.append({
                    "method": "rise_ratio",
                    "bucket": b,
                    "breakpoint_pct": bp_pct,
                    "magnitude": bucket_means[b],
                    "rise_ratio": ratio,
                    "bonus": 0.8,
                })
                break

    # Method 4: Piecewise SSE
    best_sse = float("inf")
    best_split = -1
    for split in range(min_bucket + 2, NUM_BUCKETS - 2):
        left = bucket_means[min_bucket:split]
        right = bucket_means[split:NUM_BUCKETS]
        left_valid = left[left > 0]
        right_valid = right[right > 0]
        if len(left_valid) < 2 or len(right_valid) < 2:
            continue
        left_mean = np.mean(left_valid)
        right_mean = np.mean(right_valid)
        if right_mean <= 1.15 * left_mean:
            continue
        sse = float(np.sum((left_valid - left_mean) ** 2) + np.sum((right_valid - right_mean) ** 2))
        if sse < best_sse:
            best_sse = sse
            best_split = split
    if best_split >= 0:
        bp_pct = (best_split + 0.5) / NUM_BUCKETS * 100
        ratio = bucket_means[min(best_split + 1, NUM_BUCKETS - 1)] / bucket_means[max(0, best_split - 1)] if bucket_means[max(0, best_split - 1)] > 0 else 1.0
        candidates.append({
            "method": "piecewise_sse",
            "bucket": best_split,
            "breakpoint_pct": bp_pct,
            "magnitude": bucket_means[best_split],
            "rise_ratio": ratio,
            "bonus": 0.85,
        })

    if not candidates:
        return {
            "breakpoint_pct": 50.0,
            "method": "default",
            "confidence": 0.0,
        }

    # Score candidates
    max_mag = max(c["magnitude"] for c in candidates) or 1.0
    for c in candidates:
        mag_norm = c["magnitude"] / max_mag
        ratio_norm = min(2.0, c["rise_ratio"]) / 2.0
        c["score"] = (0.45 * mag_norm + 0.45 * ratio_norm) * c["bonus"]
        if c["method"] == "piecewise_sse":
            c["score"] += 0.05

    best = max(candidates, key=lambda c: c["score"])
    return {
        "breakpoint_pct": round(best["breakpoint_pct"], 1),
        "method": best["method"],
        "confidence": round(best["score"], 3),
        "all_candidates": candidates,
    }


# ---------------------------------------------------------------------------
# RMS & P95
# ---------------------------------------------------------------------------

def _rms_ratio(
    dterm_energy: np.ndarray,
    throttle_norm: np.ndarray,
) -> Dict[str, float]:
    """High vs low throttle D-term RMS and P95 ratios."""
    low = dterm_energy[throttle_norm <= LOW_THROTTLE_MAX]
    high = dterm_energy[throttle_norm >= HIGH_THROTTLE_MIN]

    rms_low = float(np.sqrt(np.mean(low ** 2))) if len(low) > 0 else 1.0
    rms_high = float(np.sqrt(np.mean(high ** 2))) if len(high) > 0 else 0.0
    rms_ratio_val = rms_high / rms_low if rms_low > 0 else 0.0

    p95_low = _percentile(low, 95) if len(low) > 10 else 1.0
    p95_high = _percentile(high, 95) if len(high) > 10 else 0.0
    p95_ratio = p95_high / p95_low if p95_low > 0 else 0.0

    return {
        "rms_low": round(rms_low, 2),
        "rms_high": round(rms_high, 2),
        "rms_ratio": round(rms_ratio_val, 2),
        "p95_low": round(p95_low, 2),
        "p95_high": round(p95_high, 2),
        "p95_ratio": round(p95_ratio, 2),
    }


# ---------------------------------------------------------------------------
# Suggested TPA rate
# ---------------------------------------------------------------------------

def _suggested_tpa_rate(rms_ratio_val: float, p95_ratio: float) -> int:
    """Compute suggested TPA rate (0–100%)."""
    if rms_ratio_val <= 1.0:
        return 0
    combined = 0.6 * rms_ratio_val + 0.4 * (p95_ratio if p95_ratio > 0 else rms_ratio_val)
    e = 1.0 - 1.0 / combined
    rate = int(round(max(5, min(100, 200 * e))))
    return rate


# ---------------------------------------------------------------------------
# PID escalation
# ---------------------------------------------------------------------------

def _pid_escalation(
    flight_data,
    throttle_norm: np.ndarray,
) -> Dict[str, Any]:
    """
    Check if PID effort increases with throttle (linear regression slope).
    """
    n = len(throttle_norm)
    # Compute PID sum per sample
    pid_sum = np.zeros(n)
    has_pid = False
    for ax in range(3):
        for term_list in [flight_data.pid_p, flight_data.pid_i, flight_data.pid_d]:
            if term_list and term_list[ax] is not None and len(term_list[ax]) >= n:
                pid_sum += np.abs(term_list[ax][:n].astype(np.float64))
                has_pid = True

    if not has_pid:
        return {"slope": 0.0, "label": "N/A", "available": False}

    # Bucket: average PID effort per throttle bucket (reuse NUM_BUCKETS)
    sums = np.zeros(NUM_BUCKETS)
    counts = np.zeros(NUM_BUCKETS)
    for i in range(n):
        if throttle_norm[i] >= MIN_THROTTLE_FOR_SCAN:
            b = min(int(throttle_norm[i] * NUM_BUCKETS), NUM_BUCKETS - 1)
            sums[b] += pid_sum[i]
            counts[b] += 1

    valid = counts > 0
    if np.sum(valid) < 3:
        return {"slope": 0.0, "label": "N/A", "available": False}

    x = np.arange(NUM_BUCKETS)[valid].astype(np.float64)
    y = (sums[valid] / counts[valid])

    # Linear regression
    n_pts = len(x)
    sx = np.sum(x)
    sy = np.sum(y)
    sxy = np.sum(x * y)
    sx2 = np.sum(x * x)
    denom = n_pts * sx2 - sx * sx
    slope = (n_pts * sxy - sx * sy) / max(denom, 1e-9)

    # Normalise slope relative to mean PID
    mean_pid = float(np.mean(y))
    pct = (slope * NUM_BUCKETS) / mean_pid * 100 if mean_pid > 0 else 0

    if pct > 30:
        label = "Strong"
    elif pct > 15:
        label = "Moderate"
    else:
        label = "Low"

    return {
        "slope": round(float(slope), 4),
        "escalation_pct": round(pct, 1),
        "label": label,
        "available": True,
    }


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class TPAAnalyzer:
    """TPA Analyzer – optimal breakpoint & rate from D-term vs throttle."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        """Run TPA analysis and add findings."""
        # Get throttle
        throttle = flight_data.rc_command_throttle
        if throttle is None or len(throttle) < 500:
            return

        throttle_f = throttle.astype(np.float64)
        n = len(throttle_f)

        # Normalise throttle to 0–1
        tmin = float(np.min(throttle_f))
        tmax = float(np.max(throttle_f))
        if tmax - tmin < 10:
            return  # no throttle variation
        if tmax > 1.5:
            # Raw RC values (1000–2000 range)
            throttle_norm = (throttle_f - tmin) / (tmax - tmin)
        elif tmax <= 1.0 and tmin >= 0:
            throttle_norm = throttle_f.copy()
        else:
            throttle_norm = (throttle_f - tmin) / max(tmax - tmin, 1.0)

        # D-term energy
        dterm_energy, smoothed, throttle_norm = _compute_dterm_energy(
            flight_data, throttle_norm
        )
        if np.max(dterm_energy) < 0.01:
            return  # no D-term activity

        # Bucket D-term
        bucket_means, bucket_counts = _bucket_dterm(smoothed, throttle_norm)

        # Breakpoint detection
        bp = _detect_breakpoint(bucket_means, bucket_counts)

        # RMS ratio
        ratios = _rms_ratio(dterm_energy, throttle_norm)

        # Suggested rate
        suggested_rate = _suggested_tpa_rate(ratios["rms_ratio"], ratios["p95_ratio"])

        # PID escalation
        escalation = _pid_escalation(flight_data, throttle_norm)

        # Throttle positions for breakpoint as raw value
        bp_throttle_raw = int(round(tmin + bp["breakpoint_pct"] / 100 * (tmax - tmin)))

        # Severity based on ratio
        if ratios["rms_ratio"] >= 1.5:
            sev = Severity.WARNING
        elif ratios["rms_ratio"] >= 1.2:
            sev = Severity.INFO
        else:
            sev = Severity.INFO

        # CLI commands
        cli_cmds = []
        if suggested_rate > 0:
            cli_cmds.append(f"set tpa_rate = {suggested_rate}")
            cli_cmds.append(f"set tpa_breakpoint = {bp_throttle_raw}")
            cli_cmds.append(f"set tpa_mode = D")

        desc = (
            f"TPA Breakpoint: {bp['breakpoint_pct']:.0f}% throttle | "
            f"Suggested Rate: {suggested_rate}% | "
            f"RMS Ratio: {ratios['rms_ratio']:.2f}× | "
            f"Peak Noise: {ratios['p95_ratio']:.2f}×"
        )

        explanation_lines = [
            f"The breakpoint marks where D-term (oscillation effort) significantly increases with throttle.",
            f"The suggested rate attempts to reduce PID gains so high-throttle D-term approaches the low-throttle baseline.",
        ]
        if ratios["rms_ratio"] > 1.2:
            explanation_lines.append(
                f"A ratio above 1.2× indicates TPA is needed. Current ratio: {ratios['rms_ratio']:.2f}×."
            )
        else:
            explanation_lines.append("D-term noise is similar across throttle range — TPA may not be needed.")

        if escalation["available"] and escalation["label"] != "Low":
            explanation_lines.append(
                f"PID escalation: {escalation['escalation_pct']:.1f}% ({escalation['label']}). "
                "High-throttle effort is elevated."
            )

        # Chart data: bucket averages
        bucket_throttle_pcts = [(b + 0.5) / NUM_BUCKETS * 100 for b in range(NUM_BUCKETS)]

        data = {
            "type": "tpa_analysis",
            "breakpoint_pct": bp["breakpoint_pct"],
            "breakpoint_raw": bp_throttle_raw,
            "breakpoint_method": bp["method"],
            "suggested_rate": suggested_rate,
            "rms_ratio": ratios["rms_ratio"],
            "p95_ratio": ratios["p95_ratio"],
            "rms_low": ratios["rms_low"],
            "rms_high": ratios["rms_high"],
            "escalation": escalation,
            "chart_throttle_pcts": bucket_throttle_pcts,
            "chart_bucket_means": [round(float(v), 2) for v in bucket_means],
            "chart_bucket_counts": [int(c) for c in bucket_counts],
            "threshold_val": round(float(bucket_means[bucket_means > 0].mean()), 2) if np.any(bucket_means > 0) else 0,
            "cli_commands": cli_cmds,
        }

        report.add_finding(Finding(
            category=Category.PID,
            title="TPA Analysis",
            severity=sev,
            description=desc,
            explanation="\n".join(explanation_lines),
            cli_commands=cli_cmds if cli_cmds else None,
            data=data,
        ))
