"""
Tracking Analyzer – PID tracking quality from blackbox data.

Compares setpoint vs gyro to evaluate how well the PID loop tracks
the pilot's input. Also evaluates step response and latency.
"""
from __future__ import annotations

import numpy as np
from typing import Optional, List, Tuple

from ..parsers.bbl_data_parser import FlightData
from ..parsers.bbl_header_parser import BBLHeaderData
from ..knowledge.best_practices import (
    AnalysisReport, Category, Finding, Severity,
)


class TrackingAnalyzer:
    """Analyze PID tracking quality: how well does gyro follow setpoint?"""

    def analyze_flight_data(
        self,
        flight_data: FlightData,
        header: Optional[BBLHeaderData],
        report: AnalysisReport,
    ):
        """Run tracking sub-analyses."""
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            self._analyze_tracking_error(flight_data, axis, label, report)
            self._analyze_step_response(flight_data, axis, label, report)
            self._analyze_overshoot(flight_data, axis, label, report)

        self._analyze_pid_terms(flight_data, report)

    # ------------------------------------------------------------------
    def _analyze_tracking_error(
        self,
        fd: FlightData,
        axis: int,
        label: str,
        report: AnalysisReport,
    ):
        """Compute RMS tracking error = gyro – setpoint."""
        setpoint = fd.setpoint[axis]
        gyro = fd.gyro_filtered[axis]
        if setpoint is None or gyro is None:
            return
        n = min(len(setpoint), len(gyro))
        if n < 100:
            return

        error = gyro[:n] - setpoint[:n]
        rms_error = float(np.sqrt(np.mean(error ** 2)))
        mean_abs = float(np.mean(np.abs(error)))
        max_error = float(np.max(np.abs(error)))

        # Context: RMS error relative to setpoint magnitude
        sp_rms = float(np.sqrt(np.mean(setpoint[:n] ** 2)))
        ratio = rms_error / sp_rms * 100 if sp_rms > 1 else 0

        sev = Severity.INFO
        grade = "Excellent"
        if ratio > 5:
            grade = "Good"
        if ratio > 10:
            sev = Severity.WARNING
            grade = "Fair"
        if ratio > 20:
            sev = Severity.ERROR
            grade = "Poor"

        report.add_finding(Finding(
            category=Category.TRACKING,
            severity=sev,
            title=f"{label} Tracking: {grade} (RMS error {rms_error:.1f}°/s)",
            description=f"Tracking error RMS: {rms_error:.1f}°/s, "
                       f"Mean absolute: {mean_abs:.1f}°/s, "
                       f"Max: {max_error:.0f}°/s. "
                       f"Error/setpoint ratio: {ratio:.1f}%.",
            explanation="Lower tracking error = better PID response. "
                       "High error suggests P gain too low, D too high, or filter delay.",
            data={
                "axis": label,
                "rms_error": rms_error,
                "mean_abs": mean_abs,
                "max_error": max_error,
                "ratio_pct": ratio,
            },
        ))

    def _analyze_step_response(
        self,
        fd: FlightData,
        axis: int,
        label: str,
        report: AnalysisReport,
    ):
        """Estimate step response by finding quick sticks and measuring rise time."""
        setpoint = fd.setpoint[axis]
        gyro = fd.gyro_filtered[axis]
        if setpoint is None or gyro is None:
            return
        n = min(len(setpoint), len(gyro))
        if n < 500:
            return

        sp = setpoint[:n]
        gy = gyro[:n]

        # Find "step" events: large setpoint change in short window
        # Look at derivative of setpoint
        ds_dt = np.diff(sp)
        threshold = float(np.std(ds_dt)) * 3

        step_indices = np.where(np.abs(ds_dt) > threshold)[0]
        if len(step_indices) == 0:
            return

        # Cluster nearby indices (within 50 samples)
        clusters: List[int] = []
        last = -100
        for idx in step_indices:
            if idx - last > 50:
                clusters.append(int(idx))
            last = idx

        if len(clusters) < 3:
            return

        # Measure rise time and settling for each step
        rise_times = []
        overshoot_pcts = []

        for start_idx in clusters[:20]:  # Limit to first 20 steps
            if start_idx + 100 >= n:
                continue

            # Target setpoint (average of next 20 samples)
            end = min(start_idx + 100, n)
            target = float(np.mean(sp[start_idx + 10 : start_idx + 30]))
            initial = float(gy[start_idx])

            if abs(target - initial) < 50:  # Too small a step
                continue

            # Rise time: time for gyro to reach 90% of target
            target_90 = initial + 0.9 * (target - initial)
            for j in range(start_idx, end):
                if (target > initial and gy[j] >= target_90) or \
                   (target < initial and gy[j] <= target_90):
                    rise_times.append(j - start_idx)
                    break

            # Overshoot: max excursion beyond target
            window = gy[start_idx : end]
            if target > initial:
                peak = float(np.max(window))
                overshoot = (peak - target) / (target - initial) * 100
            else:
                peak = float(np.min(window))
                overshoot = (target - peak) / (initial - target) * 100
            if overshoot > 0:
                overshoot_pcts.append(overshoot)

        if rise_times:
            avg_rise = float(np.mean(rise_times))
            report.add_finding(Finding(
                category=Category.TRACKING,
                severity=Severity.INFO,
                title=f"{label} Step Rise Time: ~{avg_rise:.0f} samples",
                description=f"Average rise time (to 90% of target): {avg_rise:.0f} samples "
                           f"across {len(rise_times)} detected steps.",
                explanation="Faster rise time = more responsive. Very fast rise can lead to overshoot.",
            ))

    def _analyze_overshoot(
        self,
        fd: FlightData,
        axis: int,
        label: str,
        report: AnalysisReport,
    ):
        """Detect overshoot/bounceback in PID response."""
        setpoint = fd.setpoint[axis]
        gyro = fd.gyro_filtered[axis]
        if setpoint is None or gyro is None:
            return
        n = min(len(setpoint), len(gyro))
        if n < 500:
            return

        sp = setpoint[:n]
        gy = gyro[:n]
        error = gy - sp

        # Look for sign changes in error (oscillation)
        sign_changes = np.where(np.diff(np.sign(error)))[0]
        if len(sign_changes) < 10:
            return

        # Calculate oscillation frequency
        # Average samples between zero crossings
        intervals = np.diff(sign_changes)
        valid_intervals = intervals[(intervals > 2) & (intervals < 500)]

        if len(valid_intervals) < 5:
            return

        avg_half_period = float(np.mean(valid_intervals))
        # This represents half a cycle

        # Check for sustained oscillation (consistent intervals)
        interval_cv = float(np.std(valid_intervals) / np.mean(valid_intervals))

        if interval_cv < 0.3:
            # Consistent oscillation pattern
            report.add_finding(Finding(
                category=Category.TRACKING,
                severity=Severity.WARNING,
                title=f"{label}: Oscillation Detected",
                description=f"Consistent oscillation pattern with ~{avg_half_period:.0f} sample "
                           f"half-period ({len(sign_changes)} zero crossings). "
                           f"CV of intervals: {interval_cv:.2f}.",
                explanation="Consistent oscillation suggests P too high or D too low. "
                           "Slow oscillation → I too high. Fast oscillation → P too high.",
            ))

    def _analyze_pid_terms(self, fd: FlightData, report: AnalysisReport):
        """Analyze PID term contributions from blackbox data."""
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            p = fd.pid_p[axis]
            i = fd.pid_i[axis]
            d = fd.pid_d[axis]
            f = fd.pid_f[axis]

            if p is None or i is None:
                continue

            # RMS of each term
            p_rms = float(np.sqrt(np.mean(p ** 2))) if p is not None and len(p) > 0 else 0
            i_rms = float(np.sqrt(np.mean(i ** 2))) if i is not None and len(i) > 0 else 0
            d_rms = float(np.sqrt(np.mean(d ** 2))) if d is not None and len(d) > 0 else 0
            f_rms = float(np.sqrt(np.mean(f ** 2))) if f is not None and len(f) > 0 else 0

            total = p_rms + i_rms + d_rms + f_rms
            if total == 0:
                continue

            report.add_finding(Finding(
                category=Category.TRACKING,
                severity=Severity.INFO,
                title=f"{label} PID Contributions",
                description=f"P: {p_rms:.1f} ({p_rms/total*100:.0f}%), "
                           f"I: {i_rms:.1f} ({i_rms/total*100:.0f}%), "
                           f"D: {d_rms:.1f} ({d_rms/total*100:.0f}%), "
                           f"FF: {f_rms:.1f} ({f_rms/total*100:.0f}%)",
                data={
                    "axis": label,
                    "p_rms": p_rms, "i_rms": i_rms,
                    "d_rms": d_rms, "f_rms": f_rms,
                },
            ))

            # Check for D-term dominance (noisy or over-tuned)
            if d_rms > p_rms and d_rms > 0:
                report.add_finding(Finding(
                    category=Category.TRACKING,
                    severity=Severity.WARNING,
                    title=f"{label}: D-term Dominant Over P-term",
                    description=f"D-term RMS ({d_rms:.1f}) exceeds P-term ({p_rms:.1f}). "
                               f"This may indicate D is fighting noise rather than stabilizing.",
                    explanation="In a healthy tune, P should be the dominant corrective term. "
                               "D-term larger than P suggests either D too high, "
                               "P too low, or excessive noise amplification.",
                ))

            # Check I-term windup
            if i is not None and len(i) > 100:
                i_max = float(np.max(np.abs(i)))
                if i_max > 400:
                    report.add_finding(Finding(
                        category=Category.TRACKING,
                        severity=Severity.WARNING,
                        title=f"{label}: High I-term Values (max {i_max:.0f})",
                        description="I-term is reaching very high values, suggesting possible "
                                   "I-term windup. Check iterm_relax settings.",
                        cli_commands=[
                            "set iterm_relax = RP",
                            "set iterm_relax_cutoff = 15",
                        ],
                    ))
