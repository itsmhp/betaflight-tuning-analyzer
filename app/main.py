"""
Betaflight Tuning Analyzer – FastAPI Application.

Main web application that ties together parsers, analyzers, and generators.
"""
from __future__ import annotations

import os
import shutil
import traceback
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import (
    UPLOAD_DIR, TEMPLATES_DIR, STATIC_DIR,
    MAX_UPLOAD_SIZE_MB, ALLOWED_CLI_EXT, ALLOWED_BBL_EXT,
)
from .core import run_analysis as _run_analysis_core
from .knowledge.best_practices import AnalysisReport
from .knowledge.presets import QuadProfile, get_preset, get_all_presets_for_size

# ---------------------------------------------------------------------------

app = FastAPI(title="Betaflight Tuning Analyzer", version="1.0.0")

# Static files & templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Ensure upload dir exists
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Upload page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    cli_file: UploadFile = File(...),
    bbl_file: Optional[UploadFile] = File(None),
    # Quad profile fields (all optional)
    frame_size: str = Form(""),
    prop_size: str = Form(""),
    battery_cells: int = Form(0),
    motor_kv: int = Form(0),
    weight_grams: int = Form(0),
    fc_name: str = Form(""),
    esc_name: str = Form(""),
    flying_style: str = Form("freestyle"),
    preset_level: str = Form("none"),
):
    """
    Receive CLI dump + optional BBL file + optional quad profile,
    run full analysis, render results page.
    """
    errors = []
    cli_text = ""
    bbl_path: Optional[Path] = None

    try:
        # ------ validate & read CLI file ------
        if cli_file.filename:
            ext = Path(cli_file.filename).suffix.lower()
            if ext not in ALLOWED_CLI_EXT:
                errors.append(f"CLI file must be {', '.join(ALLOWED_CLI_EXT)} (got {ext})")
        if not errors:
            raw = await cli_file.read()
            if len(raw) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                errors.append(f"CLI file too large (>{MAX_UPLOAD_SIZE_MB} MB)")
            cli_text = raw.decode("utf-8", errors="replace")

        # ------ validate & save BBL file ------
        if bbl_file and bbl_file.filename:
            ext = Path(bbl_file.filename).suffix.lower()
            if ext not in ALLOWED_BBL_EXT:
                errors.append(f"BBL file must be {', '.join(ALLOWED_BBL_EXT)} (got {ext})")
            if not errors:
                bbl_raw = await bbl_file.read()
                if len(bbl_raw) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    errors.append(f"BBL file too large (>{MAX_UPLOAD_SIZE_MB} MB)")
                else:
                    bbl_path = UPLOAD_DIR / bbl_file.filename
                    with open(bbl_path, "wb") as f:
                        f.write(bbl_raw)

        if errors:
            return templates.TemplateResponse("index.html", {
                "request": request, "errors": errors,
            })

        # ------ build quad profile ------
        quad_profile = QuadProfile(
            frame_size=frame_size or "",
            prop_size=prop_size or "",
            battery_cells=battery_cells or 0,
            motor_kv=motor_kv or 0,
            weight_grams=weight_grams or 0,
            fc_name=fc_name or "",
            esc_name=esc_name or "",
            flying_style=flying_style or "freestyle",
            preset_level=preset_level if preset_level != "none" else "",
        )

        # ------ run analysis pipeline ------
        result = _run_analysis(cli_text, bbl_path, quad_profile)

        return templates.TemplateResponse("results.html", {
            "request": request, **result,
        })

    except Exception as exc:
        tb = traceback.format_exc()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "errors": [f"Analysis error: {exc}", tb],
        })
    finally:
        # Cleanup uploaded BBL
        if bbl_path and bbl_path.exists():
            try:
                bbl_path.unlink()
            except OSError:
                pass


@app.post("/api/analyze", response_class=JSONResponse)
async def api_analyze(
    cli_file: UploadFile = File(...),
    bbl_file: Optional[UploadFile] = File(None),
):
    """JSON API endpoint for programmatic access."""
    try:
        cli_text = (await cli_file.read()).decode("utf-8", errors="replace")

        bbl_path: Optional[Path] = None
        if bbl_file and bbl_file.filename:
            bbl_raw = await bbl_file.read()
            bbl_path = UPLOAD_DIR / bbl_file.filename
            with open(bbl_path, "wb") as f:
                f.write(bbl_raw)

        result = _run_analysis(cli_text, bbl_path, QuadProfile())

        # Cleanup
        if bbl_path and bbl_path.exists():
            bbl_path.unlink(missing_ok=True)

        return JSONResponse({
            "score": result["report"].overall_score,
            "findings": [
                {
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "explanation": f.explanation,
                    "recommended_value": f.recommended_value,
                    "cli_commands": f.cli_commands,
                }
                for f in result["report"].findings
            ],
            "cli_script": result["cli_script"],
        })
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# ---------------------------------------------------------------------------
# Analysis Pipeline
# ---------------------------------------------------------------------------
# Analysis Pipeline – delegates to app.core (shared with Qt GUI)
# ---------------------------------------------------------------------------

def _run_analysis(
    cli_text: str,
    bbl_path: Optional[Path] = None,
    quad_profile: Optional[QuadProfile] = None,
) -> dict:
    """Thin wrapper – delegates to :func:`app.core.run_analysis`."""
    return _run_analysis_core(cli_text, bbl_path, quad_profile)


    if bbl_path and bbl_path.exists():
        bbl_raw = bbl_path.read_bytes()

        # Parse headers
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
    findings_by_category = {}
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
    charts = {}

    # ================================================================
    # A) From analysis findings
    # ================================================================

    # Noise spectrum charts
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

    # Motor balance from findings
    motor_findings = [
        f.data for f in report.findings
        if f.data and "motor_means" in f.data
    ]
    if motor_findings:
        charts["motor_balance"] = motor_findings[0]

    # PID contributions from findings
    pid_contribs = [
        f.data for f in report.findings
        if f.data and "p_rms" in f.data
    ]
    if pid_contribs:
        charts["pid_contributions"] = pid_contribs

    # Tracking error from findings
    tracking_data = [
        f.data for f in report.findings
        if f.data and "rms_error" in f.data
    ]
    if tracking_data:
        charts["tracking_errors"] = tracking_data

    # Motor percentile distributions
    motor_percentiles = [
        f.data for f in report.findings
        if f.data and "percentiles" in f.data
    ]
    if motor_percentiles:
        charts["motor_percentiles"] = motor_percentiles

    # ================================================================
    # B) Time-series from flight data (downsampled for browser)
    # ================================================================
    if flight_data:
        MAX_POINTS = 2000  # downsample for smooth Plotly rendering

        def _downsample(arr, n=MAX_POINTS):
            """Downsample array to n points using simple decimation."""
            if arr is None or len(arr) == 0:
                return None
            if len(arr) <= n:
                return arr.tolist()
            step = max(1, len(arr) // n)
            return arr[::step].tolist()

        def _time_seconds(fd):
            """Time axis in seconds."""
            if fd.time_us is not None and len(fd.time_us) > 0:
                t = (fd.time_us - fd.time_us[0]) / 1e6
                return _downsample(t)
            return None

        time_s = _time_seconds(flight_data)

        # ---- Setpoint vs Gyro (per axis) ----
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

        # ---- Motor outputs over time ----
        motor_traces = {}
        for i in range(4):
            if flight_data.motor[i] is not None and len(flight_data.motor[i]) > 100:
                motor_traces[f"Motor {i+1}"] = _downsample(flight_data.motor[i])
        if motor_traces:
            motor_traces["time"] = time_s
            charts["motor_outputs"] = motor_traces

        # ---- Battery voltage over time ----
        if flight_data.vbat is not None and len(flight_data.vbat) > 100:
            charts["vbat_trace"] = {
                "time": time_s,
                "voltage": _downsample(flight_data.vbat),
            }

        # ---- Throttle trace ----
        throttle = flight_data.rc_command[3] if len(flight_data.rc_command) > 3 else None
        if throttle is not None and len(throttle) > 100:
            charts["throttle_trace"] = {
                "time": time_s,
                "throttle": _downsample(throttle),
            }

        # ---- PID error histogram ----
        error_hists = {}
        for axis, label in enumerate(("Roll", "Pitch", "Yaw")):
            sp = flight_data.setpoint[axis]
            gy = flight_data.gyro_filtered[axis]
            if sp is not None and gy is not None:
                n = min(len(sp), len(gy))
                if n > 100:
                    err = gy[:n] - sp[:n]
                    # Create histogram bins
                    counts, bin_edges = np.histogram(err, bins=80,
                                                     range=(-200, 200))
                    bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()
                    error_hists[label] = {
                        "bins": bin_centers,
                        "counts": counts.tolist(),
                    }
        if error_hists:
            charts["error_histogram"] = error_hists

    # ================================================================
    # C) Rate curve visualization (from CLI data, no BBL needed)
    # ================================================================
    if cli_data:
        active_rate = None
        for r in cli_data.rate_profiles:
            if r.index == cli_data.active_rate_profile:
                active_rate = r
                break

        if active_rate and active_rate.rates_type == "ACTUAL":
            rate_curves = {}
            stick_pcts = list(range(0, 101, 2))  # 0% to 100%

            for axis_name, rc_rate, srate, expo in [
                ("Roll", active_rate.roll_rc_rate, active_rate.roll_srate, active_rate.roll_expo),
                ("Pitch", active_rate.pitch_rc_rate, active_rate.pitch_srate, active_rate.pitch_expo),
                ("Yaw", active_rate.yaw_rc_rate, active_rate.yaw_srate, active_rate.yaw_expo),
            ]:
                center = rc_rate * 10  # deg/s at center
                max_rate = (rc_rate + srate) * 10  # deg/s at full stick
                expo_frac = expo / 100.0 if expo else 0

                curve = []
                for pct in stick_pcts:
                    stick = pct / 100.0
                    # ACTUAL rates formula with expo
                    if expo_frac > 0:
                        stick_shaped = stick * ((1 - expo_frac) + expo_frac * stick * stick)
                    else:
                        stick_shaped = stick
                    deg_s = center + (max_rate - center) * stick_shaped
                    curve.append(round(deg_s, 1))

                rate_curves[axis_name] = curve

            rate_curves["stick_pct"] = stick_pcts
            charts["rate_curves"] = rate_curves

        # ---- PID values radar data ----
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
