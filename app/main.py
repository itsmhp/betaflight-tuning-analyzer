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
):
    """
    Receive CLI dump + optional BBL file, run full analysis,
    render results page.
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

        # ------ run analysis pipeline ------
        result = _run_analysis(cli_text, bbl_path)

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

        result = _run_analysis(cli_text, bbl_path)

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

def _run_analysis(cli_text: str, bbl_path: Optional[Path] = None) -> dict:
    """
    Execute the full analysis pipeline and return context dict for template.
    """
    report = AnalysisReport()

    # ---- Phase 1: CLI dump analysis ----
    cli_parser = CLIParser()
    cli_data = cli_parser.parse(cli_text)

    # Run config-based analyzers
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
    chart_data = _prepare_chart_data(report, flight_data)

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
    }


def _prepare_chart_data(report: AnalysisReport, flight_data) -> dict:
    """Extract chart-ready data from findings and flight data."""
    charts = {}

    # Noise spectrum charts from findings
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

    # Motor data from findings
    motor_findings = [
        f.data for f in report.findings
        if f.data and "motor_means" in f.data
    ]
    if motor_findings:
        charts["motor_balance"] = motor_findings[0]

    # PID contributions
    pid_contribs = [
        f.data for f in report.findings
        if f.data and "p_rms" in f.data
    ]
    if pid_contribs:
        charts["pid_contributions"] = pid_contribs

    return charts
