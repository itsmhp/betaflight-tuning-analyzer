"""
Motor Analyzer – motor output quality from blackbox data.

Evaluates motor balance, saturation, thermal load estimation,
and bidirectional DShot / eRPM data quality.
"""
from __future__ import annotations

import numpy as np
from typing import Optional

from ..parsers.bbl_data_parser import FlightData
from ..parsers.bbl_header_parser import BBLHeaderData
from ..parsers.cli_parser import CLIData
from ..knowledge.best_practices import (
    AnalysisReport, Category, Finding, Severity,
)


class MotorAnalyzer:
    """Analyze motor outputs and balance from blackbox data."""

    def analyze_flight_data(
        self,
        flight_data: FlightData,
        header: Optional[BBLHeaderData],
        report: AnalysisReport,
    ):
        """Run all motor sub-analyses using flight data."""
        self._analyze_motor_balance(flight_data, report)
        self._analyze_motor_saturation(flight_data, report)
        self._analyze_motor_range(flight_data, report)
        if flight_data.erpm[0] is not None:
            self._analyze_erpm_data(flight_data, report)
        if flight_data.vbat is not None:
            self._analyze_voltage_sag(flight_data, report)

    def analyze_config(self, cli_data: CLIData, report: AnalysisReport):
        """Static configuration checks (no flight data needed)."""
        self._analyze_motor_output_limit(cli_data, report)
        self._analyze_motor_direction(cli_data, report)

    # ------------------------------------------------------------------
    def _analyze_motor_balance(self, fd: FlightData, report: AnalysisReport):
        """Check how balanced the motors are during flight."""
        means = []
        stds = []
        for i in range(4):
            if fd.motor[i] is not None and len(fd.motor[i]) > 100:
                means.append(float(np.mean(fd.motor[i])))
                stds.append(float(np.std(fd.motor[i])))
            else:
                means.append(None)
                stds.append(None)

        valid = [m for m in means if m is not None]
        if len(valid) < 4:
            return

        spread = max(valid) - min(valid)
        spread_pct = spread / np.mean(valid) * 100

        sev = Severity.INFO
        grade = "Good"
        if spread_pct > 5:
            sev = Severity.WARNING
            grade = "Fair"
        if spread_pct > 10:
            sev = Severity.ERROR
            grade = "Poor"

        desc_parts = [f"Motor {i+1}: avg {means[i]:.0f}" for i in range(4)]
        desc = ", ".join(desc_parts)
        desc += f"\nSpread: {spread:.0f} ({spread_pct:.1f}%) – {grade}"

        report.add_finding(Finding(
            category=Category.MOTOR,
            severity=sev,
            title=f"Motor Balance: {grade} ({spread_pct:.1f}% spread)",
            description=desc,
            explanation="A spread >5% indicates imbalance (bent prop, failing motor, CG offset). "
                       "Check propellers, motor bearings, and ensure CG is centered.",
            data={
                "motor_means": means,
                "motor_stds": stds,
                "spread_pct": spread_pct,
            },
        ))

        # Identify worst offender
        avg = np.mean(valid)
        worst_idx = 0
        worst_diff = 0
        for i in range(4):
            if means[i] is not None:
                diff = abs(means[i] - avg)
                if diff > worst_diff:
                    worst_diff = diff
                    worst_idx = i
        if spread_pct > 5:
            direction = "above" if means[worst_idx] > avg else "below"
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.WARNING,
                title=f"Motor {worst_idx + 1} Outlier ({direction} average)",
                description=f"Motor {worst_idx + 1} averages {means[worst_idx]:.0f} vs "
                           f"fleet avg {avg:.0f} ({worst_diff:.0f} difference). "
                           f"Check prop and motor on position {worst_idx + 1}.",
            ))

    def _analyze_motor_saturation(self, fd: FlightData, report: AnalysisReport):
        """Check how often motors hit limits."""
        for i in range(4):
            if fd.motor[i] is None or len(fd.motor[i]) < 100:
                continue
            motor = fd.motor[i]
            total = len(motor)

            # Detect range – DShot values typically 0-2047 or motor output 1000-2000
            max_val = float(np.max(motor))
            min_val = float(np.min(motor))

            # Fraction of time at max (~97% of max)
            near_max = np.sum(motor > max_val * 0.97) / total * 100
            near_min = np.sum(motor < min_val + (max_val - min_val) * 0.03) / total * 100

            if near_max > 5:
                sev = Severity.WARNING if near_max < 20 else Severity.ERROR
                report.add_finding(Finding(
                    category=Category.MOTOR,
                    severity=sev,
                    title=f"Motor {i+1} Saturation: {near_max:.1f}% at max",
                    description=f"Motor {i+1} is near maximum output {near_max:.1f}% of the time. "
                               f"Max value seen: {max_val:.0f}.",
                    explanation="Excessive time at max means the PID controller cannot demand more "
                               "from this motor. Reduce PID gains, reduce weight, or use "
                               "higher-thrust propellers.",
                ))

    def _analyze_motor_range(self, fd: FlightData, report: AnalysisReport):
        """Analyze the typical operating range of motors."""
        for i in range(4):
            if fd.motor[i] is None or len(fd.motor[i]) < 100:
                continue
            motor = fd.motor[i]
            p10 = float(np.percentile(motor, 10))
            p50 = float(np.percentile(motor, 50))
            p90 = float(np.percentile(motor, 90))
            p99 = float(np.percentile(motor, 99))

            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.INFO,
                title=f"Motor {i+1} Range: P10={p10:.0f} P50={p50:.0f} P90={p90:.0f}",
                description=f"Motor {i+1} output distribution:\n"
                           f"  10th %ile: {p10:.0f}\n"
                           f"  50th %ile: {p50:.0f}\n"
                           f"  90th %ile: {p90:.0f}\n"
                           f"  99th %ile: {p99:.0f}",
                data={
                    "motor": i + 1,
                    "percentiles": {"p10": p10, "p50": p50, "p90": p90, "p99": p99},
                },
            ))

    def _analyze_erpm_data(self, fd: FlightData, report: AnalysisReport):
        """Analyze eRPM (bidirectional DShot telemetry) data."""
        for i in range(4):
            if fd.erpm[i] is None or len(fd.erpm[i]) < 100:
                continue
            erpm = fd.erpm[i]
            valid = erpm[erpm > 0]  # Only when spinning
            if len(valid) < 50:
                continue

            mean_erpm = float(np.mean(valid))
            max_erpm = float(np.max(valid))

            # Check for eRPM dropouts (sudden zeros during flight)
            total = len(erpm)
            zero_in_flight = 0
            # Simple heuristic: if neighboring samples are > 0 but current is 0
            for j in range(1, len(erpm) - 1):
                if erpm[j] == 0 and erpm[j - 1] > 100 and erpm[j + 1] > 100:
                    zero_in_flight += 1

            dropout_pct = zero_in_flight / total * 100

            if dropout_pct > 0.5:
                report.add_finding(Finding(
                    category=Category.MOTOR,
                    severity=Severity.WARNING,
                    title=f"Motor {i+1} eRPM Dropouts: {dropout_pct:.1f}%",
                    description=f"Motor {i+1} has {zero_in_flight} eRPM dropouts ({dropout_pct:.1f}%). "
                               f"This degrades RPM filter performance.",
                    explanation="eRPM dropouts cause the RPM filter to lose tracking. "
                               "Common causes: noisy ESC telemetry line, ESC firmware issues, "
                               "or electrical interference.",
                ))

        # eRPM range summary
        all_means = []
        for i in range(4):
            if fd.erpm[i] is not None:
                valid = fd.erpm[i][fd.erpm[i] > 0]
                if len(valid) > 0:
                    all_means.append(float(np.mean(valid)))

        if all_means:
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.INFO,
                title=f"eRPM Average: {np.mean(all_means):.0f}",
                description=f"Average eRPM across motors: "
                           + ", ".join(f"M{i+1}={m:.0f}" for i, m in enumerate(all_means)),
            ))

    def _analyze_voltage_sag(self, fd: FlightData, report: AnalysisReport):
        """Analyze battery voltage behavior during flight."""
        vbat = fd.vbat
        if vbat is None or len(vbat) < 100:
            return

        # Convert from 0.01V to V if values are > 100
        if float(np.max(vbat)) > 100:
            vbat = vbat / 100.0

        v_start = float(np.mean(vbat[:100]))
        v_end = float(np.mean(vbat[-100:]))
        v_min = float(np.min(vbat))
        v_max = float(np.max(vbat))
        sag = v_start - v_min

        report.add_finding(Finding(
            category=Category.PERFORMANCE,
            severity=Severity.INFO,
            title=f"Battery: {v_start:.1f}V → {v_end:.1f}V (min {v_min:.1f}V)",
            description=f"Start: {v_start:.2f}V, End: {v_end:.2f}V, "
                       f"Min: {v_min:.2f}V, Max: {v_max:.2f}V. "
                       f"Max sag: {sag:.2f}V.",
            data={"v_start": v_start, "v_end": v_end, "v_min": v_min, "sag": sag},
        ))

        # Estimate cell count
        cells = 0
        if v_max > 25:
            cells = 8
        elif v_max > 21:
            cells = 6
        elif v_max > 12.5:
            cells = 4
        elif v_max > 8.0:
            cells = 3
        elif v_max > 4.4:
            cells = 2
        else:
            cells = 1

        v_min_per_cell = v_min / cells if cells else v_min

        if v_min_per_cell < 3.3:
            report.add_finding(Finding(
                category=Category.PERFORMANCE,
                severity=Severity.ERROR,
                title=f"Low Cell Voltage! Min {v_min_per_cell:.2f}V/cell ({cells}S)",
                description=f"Minimum voltage per cell dropped to {v_min_per_cell:.2f}V. "
                           f"This damages LiPo batteries.",
                explanation="LiPo cells should not drop below 3.3V under load. "
                           "Land earlier or use less aggressive flying.",
            ))
        elif v_min_per_cell < 3.5:
            report.add_finding(Finding(
                category=Category.PERFORMANCE,
                severity=Severity.WARNING,
                title=f"Cell Voltage Low: {v_min_per_cell:.2f}V/cell ({cells}S)",
                description=f"Cell voltage dipped below 3.5V under load. Consider landing earlier.",
            ))

    def _analyze_motor_output_limit(self, cli_data: CLIData, report: AnalysisReport):
        """Check motor output limit from CLI."""
        # motor_output_limit lives on PIDProfile; get it from active profile
        active = None
        for p in cli_data.pid_profiles:
            if p.index == cli_data.active_pid_profile:
                active = p
                break
        limit = active.motor_output_limit if active else 100
        if limit < 100:
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.INFO,
                title=f"Motor Output Limit: {limit}%",
                description=f"Motor output is limited to {limit}%. Full authority not available.",
                explanation="Motor output limit reduces maximum motor output. Useful for limiting "
                           "power on overpowered builds.",
            ))

    def _analyze_motor_direction(self, cli_data: CLIData, report: AnalysisReport):
        """Check motor direction/reversal settings."""
        if cli_data.yaw_motors_reversed == "ON":
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.INFO,
                title="Reversed Motor Direction",
                description="Motor direction is inverted (props-out configuration).",
                explanation="Props-out (reversed) direction can improve yaw authority "
                           "and reduce prop wash effects in certain configurations.",
            ))
