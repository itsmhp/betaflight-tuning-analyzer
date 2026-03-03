"""
Betaflight Tuning Analyzer – Core analysis pipeline.

This module is framework-agnostic and can be called directly
from the Qt GUI or via the FastAPI web layer.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .parsers.cli_parser import CLIParser
from .parsers.bbl_header_parser import BBLHeaderParser
from .parsers.bbl_data_parser import BBLDataParser
from .analyzers.pid_analyzer import PIDAnalyzer
from .analyzers.filter_analyzer import FilterAnalyzer
from .analyzers.rate_analyzer import RateAnalyzer
from .analyzers.general_analyzer import GeneralAnalyzer
from .analyzers.noise_analyzer import NoiseAnalyzer
from .analyzers.motor_analyzer import MotorAnalyzer
from .analyzers.tracking_analyzer import TrackingAnalyzer
from .generators.cli_generator import CLIGenerator
from .knowledge.best_practices import AnalysisReport
from .knowledge.presets import QuadProfile, get_preset


def run_analysis(
    cli_text: str,
    bbl_path: Optional[Path] = None,
    quad_profile: Optional[QuadProfile] = None,
) -> dict:
    """
    Execute the full analysis pipeline.

    Returns
    -------
    dict  Context dictionary containing:
        report, cli_data, bbl_header, flight_data, cli_script, cli_diff,
        findings_by_category, chart_data, has_bbl, quad_profile,
        preset_data, preset_cli
    """
    report = AnalysisReport()
    if quad_profile is None:
        quad_profile = QuadProfile()

    # ---- Phase 1: CLI dump analysis ----
    cli_parser = CLIParser()
    cli_data = cli_parser.parse(cli_text)

    PIDAnalyzer().analyze_config(cli_data, report)
    FilterAnalyzer().analyze_config(cli_data, report)
    RateAnalyzer().analyze_config(cli_data, report)
    GeneralAnalyzer().analyze_config(cli_data, report)
    MotorAnalyzer().analyze_config(cli_data, report)

    # ---- Phase 2: BBL header analysis ----
    bbl_header = None
    flight_data = None

    if bbl_path and bbl_path.exists():
        bbl_raw = bbl_path.read_bytes()

        header_parser = BBLHeaderParser()
        bbl_header = header_parser.parse(bbl_raw)

        # ---- Phase 3: Flight data analysis ----
        data_parser = BBLDataParser()
        flight_data = data_parser.parse_bbl_file(str(bbl_path))

        if flight_data:
            NoiseAnalyzer().analyze_flight_data(flight_data, bbl_header, report)
            MotorAnalyzer().analyze_flight_data(flight_data, bbl_header, report)
            TrackingAnalyzer().analyze_flight_data(flight_data, bbl_header, report)

    # ---- Preset comparison (if requested) ----
    preset_data = None
    preset_cli = ""
    if quad_profile.preset_level and quad_profile.is_provided:
        frame_class = quad_profile.inferred_class
        if frame_class:
            preset_data = get_preset(frame_class, quad_profile.preset_level)
            if preset_data:
                from .knowledge.presets import generate_preset_cli
                preset_cli = generate_preset_cli(
                    frame_class, quad_profile.preset_level,
                    active_pid_profile=cli_data.active_pid_profile,
                    active_rate_profile=cli_data.active_rate_profile,
                )

    # ---- Generate CLI commands ----
    generator = CLIGenerator()
    cli_script = generator.generate(
        report,
        active_pid_profile=cli_data.active_pid_profile,
        active_rate_profile=cli_data.active_rate_profile,
        craft_name=cli_data.craft_name,
    )
    cli_diff = generator.generate_diff(report)

    # ---- Organize findings by category ----
    findings_by_category: dict = {}
    for finding in report.findings:
        cat = finding.category.value
        if cat not in findings_by_category:
            findings_by_category[cat] = []
        findings_by_category[cat].append(finding)

    # ---- Prepare chart data ----
    chart_data = _prepare_chart_data(report, flight_data, cli_data)

    return {
        "report": report,
        "cli_data": cli_data,
        "bbl_header": bbl_header,
        "flight_data": flight_data,
        "cli_script": cli_script,
        "cli_diff": cli_diff,
        "findings_by_category": findings_by_category,
        "chart_data": chart_data,
        "has_bbl": bbl_path is not None,
        "quad_profile": quad_profile,
        "preset_data": preset_data,
        "preset_cli": preset_cli,
    }


def _prepare_chart_data(report: AnalysisReport, flight_data, cli_data=None) -> dict:
    """Extract chart-ready data from findings, flight data, and CLI settings."""
    charts: dict = {}

    # ---- From analysis findings ----
    noise_spectra = []
    pre_post_spectra = []
    for finding in report.findings:
        if finding.data:
            if "psd" in finding.data and "freqs" in finding.data:
                if "psd_pre" in finding.data:
                    pre_post_spectra.append(finding.data)
                else:
                    noise_spectra.append(finding.data)

    if noise_spectra:
        charts["noise_spectra"] = noise_spectra
    if pre_post_spectra:
        charts["pre_post_spectra"] = pre_post_spectra

    motor_findings = [f.data for f in report.findings if f.data and "motor_means" in f.data]
    if motor_findings:
        charts["motor_balance"] = motor_findings[0]

    pid_contribs = [f.data for f in report.findings if f.data and "p_rms" in f.data]
    if pid_contribs:
        charts["pid_contributions"] = pid_contribs

    tracking_data = [f.data for f in report.findings if f.data and "rms_error" in f.data]
    if tracking_data:
        charts["tracking_errors"] = tracking_data

    motor_percentiles = [f.data for f in report.findings if f.data and "percentiles" in f.data]
    if motor_percentiles:
        charts["motor_percentiles"] = motor_percentiles

    # ---- Time-series from flight data ----
    if flight_data:
        MAX_POINTS = 2000

        def _downsample(arr, n=MAX_POINTS):
            if arr is None or len(arr) == 0:
                return None
            if len(arr) <= n:
                return arr.tolist()
            step = max(1, len(arr) // n)
            return arr[::step].tolist()

        def _time_seconds(fd):
            if fd.time_us is not None and len(fd.time_us) > 0:
                t = (fd.time_us - fd.time_us[0]) / 1e6
                return _downsample(t)
            return None

        time_s = _time_seconds(flight_data)

        sp_gyro = {}
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            sp = flight_data.setpoint[axis]
            gy = flight_data.gyro_filtered[axis]
            if sp is not None and gy is not None and len(sp) > 100:
                sp_gyro[label] = {
                    "setpoint": _downsample(sp),
                    "gyro": _downsample(gy),
                }
        if sp_gyro:
            sp_gyro["time"] = time_s
            charts["setpoint_vs_gyro"] = sp_gyro

        motor_traces = {}
        for i in range(4):
            if flight_data.motor[i] is not None and len(flight_data.motor[i]) > 100:
                motor_traces[f"Motor {i+1}"] = _downsample(flight_data.motor[i])
        if motor_traces:
            motor_traces["time"] = time_s
            charts["motor_outputs"] = motor_traces

        if flight_data.vbat is not None and len(flight_data.vbat) > 100:
            charts["vbat_trace"] = {"time": time_s, "voltage": _downsample(flight_data.vbat)}

        throttle = flight_data.rc_command[3] if len(flight_data.rc_command) > 3 else None
        if throttle is not None and len(throttle) > 100:
            charts["throttle_trace"] = {"time": time_s, "throttle": _downsample(throttle)}

        error_hists = {}
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            sp = flight_data.setpoint[axis]
            gy = flight_data.gyro_filtered[axis]
            if sp is not None and gy is not None:
                n = min(len(sp), len(gy))
                if n > 100:
                    err = gy[:n] - sp[:n]
                    counts, bin_edges = np.histogram(err, bins=80, range=(-200, 200))
                    bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()
                    error_hists[label] = {"bins": bin_centers, "counts": counts.tolist()}
        if error_hists:
            charts["error_histogram"] = error_hists

    # ---- Rate curve visualization ----
    if cli_data:
        active_rate = None
        for r in cli_data.rate_profiles:
            if r.index == cli_data.active_rate_profile:
                active_rate = r
                break

        if active_rate and active_rate.rates_type == "ACTUAL":
            rate_curves: dict = {}
            stick_pcts = list(range(0, 101, 2))

            for axis_name, rc_rate, srate, expo in [
                ("Roll", active_rate.roll_rc_rate, active_rate.roll_srate, active_rate.roll_expo),
                ("Pitch", active_rate.pitch_rc_rate, active_rate.pitch_srate, active_rate.pitch_expo),
                ("Yaw", active_rate.yaw_rc_rate, active_rate.yaw_srate, active_rate.yaw_expo),
            ]:
                center = rc_rate * 10
                max_rate = (rc_rate + srate) * 10
                expo_frac = expo / 100.0 if expo else 0
                curve = []
                for pct in stick_pcts:
                    stick = pct / 100.0
                    if expo_frac > 0:
                        stick_shaped = stick * ((1 - expo_frac) + expo_frac * stick * stick)
                    else:
                        stick_shaped = stick
                    deg_s = center + (max_rate - center) * stick_shaped
                    curve.append(round(deg_s, 1))
                rate_curves[axis_name] = curve

            rate_curves["stick_pct"] = stick_pcts
            charts["rate_curves"] = rate_curves

        ap = cli_data.active_pid_profile
        pid = None
        for pp in cli_data.pid_profiles:
            if pp.index == ap:
                pid = pp
                break
        if pid:
            charts["pid_radar"] = {
                "axes": ["P Roll", "P Pitch", "P Yaw",
                         "I Roll", "I Pitch", "I Yaw",
                         "D Roll", "D Pitch", "D Yaw"],
                "values": [
                    pid.p_roll, pid.p_pitch, pid.p_yaw,
                    pid.i_roll, pid.i_pitch, pid.i_yaw,
                    pid.d_roll, pid.d_pitch, pid.d_yaw,
                ],
                "reference": [45, 47, 45, 80, 80, 80, 30, 32, 0],
            }

    return charts
