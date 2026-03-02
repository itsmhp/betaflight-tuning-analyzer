"""
Noise Analyzer – FFT-based frequency analysis of blackbox gyro data.

Uses scipy.fft to identify noise peaks in gyro signals, compare
pre-filter / post-filter spectra, and correlate noise with motor RPMs.
"""
from __future__ import annotations

import numpy as np
from typing import Optional, Dict, Any, List, Tuple

from ..parsers.bbl_data_parser import FlightData
from ..parsers.bbl_header_parser import BBLHeaderData
from ..knowledge.best_practices import (
    AnalysisReport, Category, Finding, Severity,
)

try:
    from scipy.fft import rfft, rfftfreq  # type: ignore
    from scipy.signal import welch  # type: ignore
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class NoiseAnalyzer:
    """Analyze noise characteristics from flight data FFT."""

    # ---- public API -------------------------------------------------
    def analyze_flight_data(
        self,
        flight_data: FlightData,
        header: Optional[BBLHeaderData],
        report: AnalysisReport,
    ):
        """Run all noise sub-analyses."""
        if not HAS_SCIPY:
            report.add_finding(Finding(
                category=Category.NOISE,
                severity=Severity.WARNING,
                title="scipy not installed",
                description="Cannot perform FFT noise analysis. Install scipy.",
            ))
            return

        # Determine effective sample rate (Hz)
        sample_rate = self._infer_sample_rate(flight_data, header)

        # ---- Gyro filtered spectrum (per axis) -----
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            signal = flight_data.gyro_filtered[axis]
            if signal is not None and len(signal) > 256:
                self._analyze_axis_noise(signal, axis, label, sample_rate, report)

        # ---- Pre-filter vs post-filter comparison ----
        self._compare_pre_post_filter(flight_data, sample_rate, report)

        # ---- Motor RPM correlation ----
        if flight_data.erpm[0] is not None:
            self._analyze_rpm_noise_correlation(flight_data, sample_rate, report)

        # ---- Motor noise magnitude ----
        self._analyze_overall_noise_level(flight_data, sample_rate, report)

    # ---- internals ---------------------------------------------------
    @staticmethod
    def _infer_sample_rate(
        flight_data: FlightData,
        header: Optional[BBLHeaderData],
    ) -> float:
        """Best-effort sample rate detection from data or header."""
        if header:
            rate = header.get_blackbox_sample_rate()
            if rate and rate > 0:
                return float(rate)
        # Fall back to time column
        if flight_data.time_us is not None and len(flight_data.time_us) > 100:
            dt = np.median(np.diff(flight_data.time_us[:2000])) / 1e6  # seconds
            if dt > 0:
                return 1.0 / dt
        return 4000.0  # default 4 kHz

    # ---- per-axis noise ----------------------------------------------
    def _analyze_axis_noise(
        self,
        signal: np.ndarray,
        axis: int,
        label: str,
        sample_rate: float,
        report: AnalysisReport,
    ):
        """Perform FFT on a single gyro axis and flag peaks."""
        freqs, psd = self._compute_psd(signal, sample_rate)
        if freqs is None:
            return

        # Overall noise floor (mean PSD above 100 Hz)
        mask_above_100 = freqs > 100
        noise_floor = float(np.mean(psd[mask_above_100])) if np.any(mask_above_100) else 0
        noise_rms = float(np.sqrt(noise_floor))

        # Find dominant peaks
        peaks = self._find_peaks(freqs, psd, threshold_mult=5.0)

        sev = Severity.INFO
        if noise_rms > 5.0:
            sev = Severity.WARNING
        if noise_rms > 15.0:
            sev = Severity.ERROR

        desc = f"Noise floor RMS (>100 Hz): {noise_rms:.1f} deg/s"
        if peaks:
            peak_str = ", ".join(f"{f:.0f} Hz ({a:.1f})" for f, a in peaks[:5])
            desc += f"\nTop peaks: {peak_str}"

        report.add_finding(Finding(
            category=Category.NOISE,
            severity=sev,
            title=f"{label} Gyro Noise",
            description=desc,
            data={"freqs": freqs.tolist(), "psd": psd.tolist(), "axis": label},
        ))

        # Flag specific frequency ranges
        self._flag_frequency_ranges(freqs, psd, label, report)

    def _flag_frequency_ranges(
        self,
        freqs: np.ndarray,
        psd: np.ndarray,
        label: str,
        report: AnalysisReport,
    ):
        """Flag common noise bands."""
        # Motor noise (typically 150-500 Hz)
        motor_mask = (freqs > 150) & (freqs < 500)
        high_mask = freqs > 500

        if np.any(motor_mask) and np.any(high_mask):
            motor_power = float(np.mean(psd[motor_mask]))
            high_power = float(np.mean(psd[high_mask]))

            if motor_power > 10:
                report.add_finding(Finding(
                    category=Category.NOISE,
                    severity=Severity.WARNING,
                    title=f"{label}: Significant Motor Noise (150-500 Hz)",
                    description=f"Strong noise in motor frequency range. Power: {motor_power:.1f}. "
                               f"Check prop balance, motor bearings, and RPM filter setup.",
                    explanation="Motor noise in this range is typically from unbalanced props or "
                               "damaged motors. RPM filter targets this effectively.",
                ))

            if high_power > 5:
                report.add_finding(Finding(
                    category=Category.NOISE,
                    severity=Severity.WARNING,
                    title=f"{label}: High Frequency Noise (>500 Hz)",
                    description=f"Noise above 500 Hz. Power: {high_power:.1f}. "
                               f"May need lower LPF cutoff frequencies.",
                    cli_commands=[
                        "set gyro_lpf1_dyn_min_hz = 200",
                        "set gyro_lpf1_dyn_max_hz = 400",
                    ],
                ))

    # ---- pre-filter vs post-filter -----------------------------------
    def _compare_pre_post_filter(
        self,
        flight_data: FlightData,
        sample_rate: float,
        report: AnalysisReport,
    ):
        """Compare unfiltered vs filtered gyro spectra."""
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            unfiltered = flight_data.gyro_unfiltered[axis]
            filtered = flight_data.gyro_filtered[axis]
            if unfiltered is None or filtered is None:
                continue
            if len(unfiltered) < 256 or len(filtered) < 256:
                continue

            n = min(len(unfiltered), len(filtered))
            freqs_u, psd_u = self._compute_psd(unfiltered[:n], sample_rate)
            freqs_f, psd_f = self._compute_psd(filtered[:n], sample_rate)
            if freqs_u is None or freqs_f is None:
                continue

            # Filter attenuation above 100 Hz
            mask = freqs_u > 100
            if not np.any(mask):
                continue

            pre_power = float(np.mean(psd_u[mask]))
            post_power = float(np.mean(psd_f[mask]))

            if pre_power > 0:
                attenuation_db = 10 * np.log10(max(post_power, 1e-10) / pre_power)
            else:
                attenuation_db = 0

            sev = Severity.INFO
            if attenuation_db > -6:
                sev = Severity.WARNING

            report.add_finding(Finding(
                category=Category.NOISE,
                severity=sev,
                title=f"{label}: Filter Attenuation {attenuation_db:.1f} dB",
                description=f"Pre-filter noise power: {pre_power:.1f}, "
                           f"Post-filter: {post_power:.1f}. "
                           f"Total attenuation: {attenuation_db:.1f} dB.",
                explanation="Good filtering typically shows -10 dB to -20 dB attenuation. "
                           "Less than -6 dB means filters are not adequately reducing noise.",
                data={
                    "freqs": freqs_u.tolist(),
                    "psd_pre": psd_u.tolist(),
                    "psd_post": psd_f.tolist(),
                    "axis": label,
                },
            ))

    # ---- RPM correlated noise ----------------------------------------
    def _analyze_rpm_noise_correlation(
        self,
        flight_data: FlightData,
        sample_rate: float,
        report: AnalysisReport,
    ):
        """Check if noise peaks correlate with motor RPM."""
        # Get average RPM from all motors
        rpms = []
        for i in range(4):
            if flight_data.erpm[i] is not None:
                erpm = flight_data.erpm[i]
                # eRPM / (motor_poles / 2) = mechanical RPM
                rpm = erpm / 6.0  # Assume 12 poles (common)
                mean_rpm = float(np.mean(rpm[rpm > 100]))  # only when spinning
                rpms.append(mean_rpm)

        if not rpms:
            return

        avg_rpm = np.mean(rpms)
        fundamental_hz = avg_rpm / 60.0  # RPM -> Hz

        if fundamental_hz < 50:
            return

        report.add_finding(Finding(
            category=Category.NOISE,
            severity=Severity.INFO,
            title=f"Motor Fundamental: ~{fundamental_hz:.0f} Hz (avg {avg_rpm:.0f} RPM)",
            description=f"Average motor RPM: {avg_rpm:.0f}. "
                       f"Fundamental frequency: {fundamental_hz:.0f} Hz. "
                       f"Harmonics at: {fundamental_hz*2:.0f}, {fundamental_hz*3:.0f} Hz.",
            explanation="RPM filter targets the motor fundamental and its harmonics. "
                       "Check that noise peaks align with these frequencies.",
        ))

    # ---- overall noise level -----------------------------------------
    def _analyze_overall_noise_level(
        self,
        flight_data: FlightData,
        sample_rate: float,
        report: AnalysisReport,
    ):
        """Compute combined noise metric across all axes."""
        noise_values = []
        for axis in range(3):
            sig = flight_data.gyro_filtered[axis]
            if sig is not None and len(sig) > 256:
                # RMS of high-pass filtered signal (>100 Hz)
                freqs, psd = self._compute_psd(sig, sample_rate)
                if freqs is not None:
                    mask = freqs > 100
                    if np.any(mask):
                        noise_values.append(float(np.sqrt(np.mean(psd[mask]))))

        if not noise_values:
            return

        combined = float(np.sqrt(np.mean(np.array(noise_values) ** 2)))

        sev = Severity.INFO
        grade = "Excellent"
        if combined > 2:
            grade = "Good"
        if combined > 5:
            sev = Severity.WARNING
            grade = "Moderate"
        if combined > 10:
            sev = Severity.ERROR
            grade = "Bad"
        if combined > 20:
            sev = Severity.CRITICAL
            grade = "Very Bad"

        report.add_finding(Finding(
            category=Category.NOISE,
            severity=sev,
            title=f"Overall Noise Level: {combined:.1f} ({grade})",
            description=f"Combined gyro noise RMS above 100 Hz: {combined:.1f} deg/s. "
                       f"Grade: {grade}.",
            explanation="Lower is better. <2 = excellent, 2-5 = good, 5-10 = moderate, "
                       ">10 = bad (consider prop/motor check, frame stiffness).",
        ))

    # ---- helpers -----------------------------------------------------
    @staticmethod
    def _compute_psd(
        signal: np.ndarray,
        sample_rate: float,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Compute power spectral density using Welch's method."""
        if not HAS_SCIPY or signal is None or len(signal) < 256:
            return None, None
        try:
            # nperseg = 1024 gives ~4 Hz resolution at 4 kHz
            nperseg = min(1024, len(signal) // 2)
            freqs, psd = welch(signal, fs=sample_rate, nperseg=nperseg)
            return freqs, psd
        except Exception:
            return None, None

    @staticmethod
    def _find_peaks(
        freqs: np.ndarray,
        psd: np.ndarray,
        threshold_mult: float = 5.0,
    ) -> List[Tuple[float, float]]:
        """Find peaks in PSD that exceed threshold_mult * median."""
        median_psd = float(np.median(psd[freqs > 50]))
        if median_psd <= 0:
            return []

        threshold = median_psd * threshold_mult
        peak_indices = []

        # Simple peak detection: local maxima above threshold
        for i in range(1, len(psd) - 1):
            if psd[i] > threshold and psd[i] > psd[i - 1] and psd[i] > psd[i + 1]:
                peak_indices.append(i)

        # Sort by amplitude
        peak_indices.sort(key=lambda idx: psd[idx], reverse=True)

        return [(float(freqs[i]), float(psd[i])) for i in peak_indices[:10]]
