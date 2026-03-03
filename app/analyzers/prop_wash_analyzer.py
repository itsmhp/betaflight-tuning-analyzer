"""
Prop Wash Analyzer – detects prop-wash oscillation events.

Analyses gyro data for oscillations in the 20-100 Hz band that
correlate with motor activity, typically occurring during
rapid altitude changes (dives → pull-ups).

Implements:
  - FIR bandpass filter 20-100 Hz
  - Sliding RMS window with motor activity gating
  - FFT frequency analysis per event
  - Motor-gyro Pearson correlation
  - Composite severity score

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

BANDPASS_LOW_HZ = 20.0
BANDPASS_HIGH_HZ = 100.0
FIR_NUM_TAPS = 32

# Sliding window params
# Window = 10% of 1 second, overlap 50%
RMS_THRESHOLD = 15.0
MOTOR_ACTIVITY_THRESHOLD = 1000.0

# Frequency bands for classification
FREQ_BANDS = {
    "stick_inputs": (0, 20),
    "prop_wash": (20, 100),
    "frame_resonance": (100, 250),
    "motor_noise": (250, 1000),
}


# ---------------------------------------------------------------------------
# FIR bandpass filter
# ---------------------------------------------------------------------------

def _design_fir_bandpass(
    low_hz: float,
    high_hz: float,
    sample_rate: float,
    num_taps: int = FIR_NUM_TAPS,
) -> np.ndarray:
    """
    Design a simple FIR bandpass filter using windowed-sinc (Hamming).
    Returns filter coefficients.
    """
    nyq = sample_rate / 2.0
    if low_hz >= nyq or high_hz >= nyq:
        # Can't filter above Nyquist — return passthrough
        h = np.zeros(num_taps)
        h[num_taps // 2] = 1.0
        return h

    low_norm = low_hz / nyq
    high_norm = high_hz / nyq

    # Ideal lowpass sinc coefficients
    n = np.arange(num_taps) - (num_taps - 1) / 2.0
    n[n == 0] = 1e-20  # avoid /0

    # High cutoff lowpass
    h_high = np.sin(np.pi * high_norm * n) / (np.pi * n)
    # Low cutoff lowpass
    h_low = np.sin(np.pi * low_norm * n) / (np.pi * n)

    # Bandpass = highpass - lowpass
    h = h_high - h_low

    # Fix centre tap
    centre = (num_taps - 1) // 2
    h[centre] = high_norm - low_norm

    # Apply Hamming window
    window = np.hamming(num_taps)
    h = h * window

    # Normalise
    h = h / np.sum(np.abs(h))

    return h


def _apply_fir(signal: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    """Apply FIR filter via convolution."""
    return np.convolve(signal, coeffs, mode="same")


# ---------------------------------------------------------------------------
# Sliding window RMS
# ---------------------------------------------------------------------------

def _sliding_rms(signal: np.ndarray, window_size: int, hop: int) -> np.ndarray:
    """Compute RMS in sliding windows."""
    n = len(signal)
    num_windows = max(1, (n - window_size) // hop + 1)
    rms_vals = np.empty(num_windows)
    for i in range(num_windows):
        start = i * hop
        end = min(start + window_size, n)
        seg = signal[start:end]
        rms_vals[i] = float(np.sqrt(np.mean(seg ** 2)))
    return rms_vals


# ---------------------------------------------------------------------------
# Motor activity
# ---------------------------------------------------------------------------

def _motor_activity(flight_data, window_size: int, hop: int) -> np.ndarray:
    """
    Sum of motor variance per window — proxy for how hard
    motors are working (rapid throttle changes).
    """
    motors = []
    for m in range(4):
        if flight_data.motor[m] is not None:
            motors.append(flight_data.motor[m].astype(np.float64))

    if not motors:
        return np.zeros(1)

    n = min(len(m) for m in motors)
    motor_sum = np.zeros(n)
    for m in motors:
        motor_sum += m[:n]

    num_windows = max(1, (n - window_size) // hop + 1)
    activity = np.empty(num_windows)
    for i in range(num_windows):
        start = i * hop
        end = min(start + window_size, n)
        seg = motor_sum[start:end]
        if len(seg) > 1:
            activity[i] = float(np.var(seg) * len(motors))
        else:
            activity[i] = 0.0
    return activity


# ---------------------------------------------------------------------------
# Event detection
# ---------------------------------------------------------------------------

def _detect_events(
    rms_vals: np.ndarray,
    motor_act: np.ndarray,
    hop: int,
    sample_rate: float,
) -> List[Dict[str, Any]]:
    """Detect prop-wash events: RMS > threshold AND motor activity > threshold."""
    events = []
    n = min(len(rms_vals), len(motor_act))
    in_event = False
    event_start = 0

    for i in range(n):
        is_active = rms_vals[i] > RMS_THRESHOLD and motor_act[i] > MOTOR_ACTIVITY_THRESHOLD
        if is_active and not in_event:
            in_event = True
            event_start = i
        elif not is_active and in_event:
            in_event = False
            duration_samples = (i - event_start) * hop
            if duration_samples >= 20:  # minimum event length
                events.append({
                    "start_idx": event_start * hop,
                    "end_idx": i * hop,
                    "duration_ms": round(duration_samples / sample_rate * 1000, 1),
                    "peak_rms": round(float(np.max(rms_vals[event_start:i])), 2),
                    "avg_rms": round(float(np.mean(rms_vals[event_start:i])), 2),
                    "avg_motor_activity": round(float(np.mean(motor_act[event_start:i])), 2),
                })

    if in_event:
        i = n
        duration_samples = (i - event_start) * hop
        if duration_samples >= 20:
            events.append({
                "start_idx": event_start * hop,
                "end_idx": i * hop,
                "duration_ms": round(duration_samples / sample_rate * 1000, 1),
                "peak_rms": round(float(np.max(rms_vals[event_start:i])), 2),
                "avg_rms": round(float(np.mean(rms_vals[event_start:i])), 2),
                "avg_motor_activity": round(float(np.mean(motor_act[event_start:i])), 2),
            })

    return events


# ---------------------------------------------------------------------------
# FFT frequency analysis
# ---------------------------------------------------------------------------

def _fft_frequency_analysis(
    filtered_signal: np.ndarray,
    sample_rate: float,
) -> Dict[str, float]:
    """
    Compute band energy distribution from FFT.
    Returns {band_name: energy_pct}.
    """
    n = len(filtered_signal)
    if n < 64:
        return {}

    # Apply Hamming window
    windowed = filtered_signal * np.hamming(n)
    fft_vals = np.fft.rfft(windowed)
    magnitudes = np.abs(fft_vals)
    freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)

    total_energy = float(np.sum(magnitudes ** 2))
    if total_energy < 1e-12:
        return {}

    band_pct = {}
    for name, (lo, hi) in FREQ_BANDS.items():
        mask = (freqs >= lo) & (freqs < hi)
        band_energy = float(np.sum(magnitudes[mask] ** 2))
        band_pct[name] = round(band_energy / total_energy * 100, 1)

    # Dominant frequency in prop_wash band
    pw_mask = (freqs >= BANDPASS_LOW_HZ) & (freqs <= BANDPASS_HIGH_HZ)
    if np.any(pw_mask):
        pw_freqs = freqs[pw_mask]
        pw_mags = magnitudes[pw_mask]
        peak_idx = np.argmax(pw_mags)
        band_pct["dominant_freq_hz"] = round(float(pw_freqs[peak_idx]), 1)

    return band_pct


# ---------------------------------------------------------------------------
# Motor-gyro correlation
# ---------------------------------------------------------------------------

def _motor_gyro_correlation(flight_data, n: int) -> float:
    """
    Pearson correlation between total motor variance and total gyro magnitude.
    """
    # Motor sum
    motors = []
    for m in range(4):
        if flight_data.motor[m] is not None:
            motors.append(flight_data.motor[m][:n].astype(np.float64))
    if not motors:
        return 0.0

    motor_total = np.sum(np.stack(motors, axis=0), axis=0)

    # Gyro magnitude
    gyro_axes = []
    for g in [flight_data.gyro_roll, flight_data.gyro_pitch, flight_data.gyro_yaw]:
        if g is not None and len(g) >= n:
            gyro_axes.append(g[:n].astype(np.float64))
    if not gyro_axes:
        return 0.0

    gyro_mag = np.sqrt(sum(g ** 2 for g in gyro_axes))

    # Pearson
    if np.std(motor_total) < 1e-9 or np.std(gyro_mag) < 1e-9:
        return 0.0

    r = float(np.corrcoef(motor_total, gyro_mag)[0, 1])
    return round(r, 3)


# ---------------------------------------------------------------------------
# Composite severity score
# ---------------------------------------------------------------------------

def _compute_severity(
    events: List[Dict[str, Any]],
    total_duration_s: float,
    freq_info: Dict[str, float],
    motor_corr: float,
) -> Dict[str, float]:
    """
    Composite severity:
      0.4 × density + 0.3 × avgSeverity + 0.2 × freqScore + 0.1 × correlation
    """
    if total_duration_s <= 0:
        return {"overall": 0, "density": 0, "avg_severity": 0, "freq_score": 0, "correlation": 0}

    # Density: event time / total time, scaled to 0–100
    event_time_s = sum(e["duration_ms"] for e in events) / 1000.0
    density = min(100, event_time_s / total_duration_s * 100 * 5)  # 20% = 100

    # Average severity from peak RMS, normalised (RMS 50 → 100)
    if events:
        avg_severity = min(100, sum(e["peak_rms"] for e in events) / len(events) / 50 * 100)
    else:
        avg_severity = 0

    # Frequency score: percentage of energy in propwash band
    freq_score = freq_info.get("prop_wash", 0)

    # Correlation: abs correlation × 100
    corr = abs(motor_corr) * 100

    overall = 0.4 * density + 0.3 * avg_severity + 0.2 * freq_score + 0.1 * corr

    return {
        "overall": round(min(100, overall), 1),
        "density": round(density, 1),
        "avg_severity": round(avg_severity, 1),
        "freq_score": round(freq_score, 1),
        "correlation": round(corr, 1),
    }


# ---------------------------------------------------------------------------
# Main Analyzer
# ---------------------------------------------------------------------------

class PropWashAnalyzer:
    """Prop Wash Analyzer – detects and quantifies prop wash oscillations."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        """Run prop wash analysis."""
        # Need gyro data
        gyro_axes = []
        for g in [flight_data.gyro_roll, flight_data.gyro_pitch, flight_data.gyro_yaw]:
            if g is not None and len(g) > 200:
                gyro_axes.append(g.astype(np.float64))

        if len(gyro_axes) == 0:
            return

        n = min(len(g) for g in gyro_axes)
        sample_rate = bbl_header.get_blackbox_sample_rate()
        if sample_rate <= 0:
            return

        # Combined gyro magnitude
        gyro_combined = np.sqrt(sum(g[:n] ** 2 for g in gyro_axes))

        # Design bandpass filter
        fir_coeffs = _design_fir_bandpass(BANDPASS_LOW_HZ, BANDPASS_HIGH_HZ, sample_rate)
        filtered = _apply_fir(gyro_combined, fir_coeffs)

        # Sliding window parameters
        one_sec_samples = int(sample_rate)
        window_size = max(10, one_sec_samples // 10)  # 10% of 1 second
        hop = max(5, window_size // 2)  # 50% overlap

        # RMS in windows
        rms_vals = _sliding_rms(filtered, window_size, hop)

        # Motor activity
        motor_act = _motor_activity(flight_data, window_size, hop)

        # Event detection
        events = _detect_events(rms_vals, motor_act, hop, sample_rate)

        # FFT frequency analysis on filtered signal
        freq_info = _fft_frequency_analysis(filtered, sample_rate)

        # Motor-gyro correlation
        motor_corr = _motor_gyro_correlation(flight_data, n)

        # Total flight duration
        total_duration_s = n / sample_rate

        # Composite severity
        severity_scores = _compute_severity(events, total_duration_s, freq_info, motor_corr)

        # Determine finding severity
        overall = severity_scores["overall"]
        if overall >= 50:
            sev = Severity.WARNING
        elif overall >= 20:
            sev = Severity.INFO
        else:
            sev = Severity.INFO

        # Build recommendations
        recommendations = []
        if overall >= 30:
            recommendations.append("Consider increasing D-term gains slightly to dampen prop wash oscillations.")
            recommendations.append("Try increasing Dynamic Notch Count or widening Dynamic Notch range.")
        if freq_info.get("prop_wash", 0) > 50:
            dom = freq_info.get("dominant_freq_hz", 0)
            if dom > 0:
                recommendations.append(
                    f"Dominant prop wash frequency ≈{dom:.0f} Hz. "
                    "A dynamic notch filter centred on this frequency could help."
                )
        if motor_corr > 0.6:
            recommendations.append(
                "High motor-gyro correlation suggests motor RPM changes directly drive oscillation. "
                "Check for loose props or motor bearings."
            )
        if overall < 20:
            recommendations.append("Prop wash levels are acceptable — no immediate action needed.")

        desc = (
            f"Prop Wash Severity: {overall:.0f}% | "
            f"Events: {len(events)} | "
            f"Motor Correlation: {motor_corr:.0%} | "
            f"Freq Score: {severity_scores['freq_score']:.0f}%"
        )

        data = {
            "type": "prop_wash_analysis",
            "overall_severity": overall,
            "num_events": len(events),
            "events": events[:20],  # Limit for serialisation
            "freq_info": freq_info,
            "motor_correlation": motor_corr,
            "severity_scores": severity_scores,
            "recommendations": recommendations,
            "chart_rms_vals": [round(float(v), 2) for v in rms_vals[:500]],
            "chart_filtered_signal": [round(float(v), 2) for v in filtered[::max(1, n // 2000)]],
        }

        report.add_finding(Finding(
            category=Category.FILTER,
            title="Prop Wash Analysis",
            severity=sev,
            description=desc,
            explanation="\n".join(recommendations) if recommendations else "Prop wash analysis complete.",
            data=data,
        ))
