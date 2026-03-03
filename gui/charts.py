"""
Matplotlib chart rendering for the Qt GUI.

Each function accepts chart_data (the dict from app.core._prepare_chart_data)
and returns a matplotlib FigureCanvasQTAgg widget ready to embed in a layout.
"""
from __future__ import annotations

from typing import Optional

import matplotlib
matplotlib.use("QtAgg")                             # must be before pyplot import
import matplotlib.pyplot as plt                     # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure               # noqa: E402
import numpy as np                                 # noqa: E402

# ── Dark palette ──────────────────────────────────────────────────────────────
BG     = "#0d0d1a"
PLOT   = "#111128"
GRID   = "#1e1e38"
TEXT   = "#c0c0e0"
AXIS   = "#3a3a6a"
COLORS = ["#4361ee", "#f06292", "#4db6ac", "#ffb74d", "#ce93d8", "#80cbc4"]


def _base_fig(nrows=1, ncols=1, height=3.5) -> tuple[Figure, object]:
    """Create a styled dark figure + axes (or array of axes)."""
    fig = Figure(figsize=(8, height * nrows), facecolor=BG)
    if nrows == 1 and ncols == 1:
        ax = fig.add_subplot(1, 1, 1)
        axes = ax
    else:
        axes = fig.subplots(nrows, ncols)
        ax = axes.flat[0] if hasattr(axes, "flat") else axes[0]

    def _style_ax(a):
        a.set_facecolor(PLOT)
        a.tick_params(colors=TEXT, labelsize=9)
        a.xaxis.label.set_color(TEXT)
        a.yaxis.label.set_color(TEXT)
        for spine in a.spines.values():
            spine.set_edgecolor(AXIS)
        a.grid(True, color=GRID, linewidth=0.5)

    if nrows == 1 and ncols == 1:
        _style_ax(ax)
    elif hasattr(axes, "flat"):
        for a in axes.flat:
            _style_ax(a)
    else:
        for a in axes:
            _style_ax(a)

    fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.12)
    return fig, axes


def _canvas(fig: Figure) -> FigureCanvasQTAgg:
    return FigureCanvasQTAgg(fig)


# ── Individual chart builders ─────────────────────────────────────────────────

def rate_curves_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    rc = chart_data.get("rate_curves")
    if not rc:
        return None
    fig, ax = _base_fig(height=3.5)
    stick = rc.get("stick_pct", list(range(0, 101, 2)))
    for i, axis in enumerate(("Roll", "Pitch", "Yaw")):
        if axis in rc:
            ax.plot(stick, rc[axis], label=axis, color=COLORS[i], linewidth=2)
    ax.set_xlabel("Stick (%)", color=TEXT)
    ax.set_ylabel("Rate (deg/s)", color=TEXT)
    ax.set_title("Rate Curves", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    return _canvas(fig)


def pid_radar_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    pr = chart_data.get("pid_radar")
    if not pr:
        return None
    axes_labels = pr["axes"]
    values      = pr["values"]
    reference   = pr.get("reference", [])

    x = range(len(axes_labels))
    fig, ax = _base_fig(height=3.8)
    bars = ax.bar(x, values, color="#4361ee", alpha=0.85, label="Current", zorder=3)
    if reference:
        ref_v = [reference[i] if i < len(reference) else 0 for i in x]
        ax.bar(x, ref_v, color="#ffffff", alpha=0.12, label="BF Default", zorder=2)
    ax.set_xticks(list(x))
    ax.set_xticklabels(axes_labels, rotation=35, ha="right", fontsize=9, color=TEXT)
    ax.set_ylabel("Value", color=TEXT)
    ax.set_title("PID Values vs Betaflight Defaults", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    # Annotate bar values
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, str(int(h)),
                    ha="center", va="bottom", fontsize=7, color=TEXT)
    return _canvas(fig)


def noise_spectrum_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    spectra = chart_data.get("noise_spectra")
    if not spectra:
        return None
    fig, ax = _base_fig(height=3.5)
    for i, s in enumerate(spectra[:4]):
        label = s.get("axis", f"Axis {i}")
        freqs  = s.get("freqs", [])
        psd    = s.get("psd", [])
        if freqs and psd:
            ax.semilogy(freqs, psd, color=COLORS[i % len(COLORS)], linewidth=1.5, label=label)
    ax.set_xlabel("Frequency (Hz)", color=TEXT)
    ax.set_ylabel("PSD", color=TEXT)
    ax.set_title("Gyro Noise Spectrum (FFT)", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    return _canvas(fig)


def pre_post_filter_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    spectra = chart_data.get("pre_post_spectra")
    if not spectra:
        return None
    n = min(len(spectra), 3)
    fig, axes_arr = _base_fig(nrows=n, ncols=1, height=2.8)
    if n == 1:
        axes_arr = [axes_arr]
    for i, s in enumerate(spectra[:n]):
        ax = axes_arr[i]
        freqs = s.get("freqs", [])
        pre   = s.get("psd_pre", [])
        post  = s.get("psd", [])
        label = s.get("axis", f"Axis {i}")
        if freqs and pre:
            ax.semilogy(freqs, pre,  color="#ef5350", linewidth=1.2, alpha=0.9, label="Pre-filter")
        if freqs and post:
            ax.semilogy(freqs, post, color="#4db6ac", linewidth=1.5, alpha=0.9, label="Post-filter")
        ax.set_ylabel("PSD", color=TEXT, fontsize=9)
        ax.set_title(f"Filter Attenuation – {label}", color=TEXT, fontsize=10)
        ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    axes_arr[-1].set_xlabel("Frequency (Hz)", color=TEXT)
    return _canvas(fig)


def setpoint_vs_gyro_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    sig = chart_data.get("setpoint_vs_gyro")
    if not sig:
        return None
    time = sig.get("time")
    axes_found = [a for a in ("Roll", "Pitch", "Yaw") if a in sig]
    n = len(axes_found)
    if n == 0:
        return None
    fig, axes_arr = _base_fig(nrows=n, ncols=1, height=2.8)
    if n == 1:
        axes_arr = [axes_arr]
    for i, label in enumerate(axes_found):
        ax = axes_arr[i]
        d  = sig[label]
        sp = d.get("setpoint", [])
        gy = d.get("gyro", [])
        x  = time if time else list(range(len(sp)))
        if sp:
            ax.plot(x, sp, color="#ffc107", linewidth=1.0, alpha=0.9, label="Setpoint")
        if gy:
            ax.plot(x, gy, color="#4361ee", linewidth=1.2, alpha=0.85, label="Gyro")
        ax.set_ylabel(f"{label} (°/s)", color=TEXT, fontsize=9)
        ax.set_title(f"Setpoint vs Gyro – {label}", color=TEXT, fontsize=10)
        ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=8)
    axes_arr[-1].set_xlabel("Time (s)", color=TEXT)
    return _canvas(fig)


def motor_balance_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    mb = chart_data.get("motor_balance")
    if not mb or "motor_means" not in mb:
        return None
    means = mb["motor_means"]
    stds  = mb.get("motor_stds", [0]*len(means))
    labels = [f"M{i+1}" for i in range(len(means))]
    fig, ax = _base_fig(height=3.2)
    bars = ax.bar(labels, means, yerr=stds, color=COLORS[:len(means)],
                  capsize=5, error_kw=dict(ecolor=TEXT, elinewidth=1.5),
                  zorder=3, alpha=0.9)
    ax.set_ylabel("Average Output (%)", color=TEXT)
    ax.set_title("Motor Balance", color=TEXT, fontsize=11)
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=9, color=TEXT)
    return _canvas(fig)


def motor_outputs_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    mo = chart_data.get("motor_outputs")
    if not mo:
        return None
    time = mo.get("time")
    fig, ax = _base_fig(height=4)
    for i, key in enumerate(k for k in mo if k != "time"):
        vals = mo[key]
        x    = time if time else list(range(len(vals)))
        ax.plot(x, vals, color=COLORS[i % len(COLORS)], linewidth=1.0,
                alpha=0.85, label=key)
    ax.set_xlabel("Time (s)", color=TEXT)
    ax.set_ylabel("Throttle (%)", color=TEXT)
    ax.set_title("Motor Outputs Over Time", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    return _canvas(fig)


def error_histogram_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    eh = chart_data.get("error_histogram")
    if not eh:
        return None
    axes_found = list(eh.keys())
    n = len(axes_found)
    fig, axes_arr = _base_fig(nrows=1, ncols=n, height=3.2)
    if n == 1:
        axes_arr = [axes_arr]
    elif hasattr(axes_arr, "flat"):
        axes_arr = list(axes_arr.flat)
    for i, label in enumerate(axes_found):
        ax  = axes_arr[i]
        d   = eh[label]
        bins   = d.get("bins", [])
        counts = d.get("counts", [])
        if bins and counts:
            ax.bar(bins, counts, width=(bins[1]-bins[0]) if len(bins)>1 else 1,
                   color=COLORS[i % len(COLORS)], alpha=0.85, zorder=3)
        ax.set_title(f"Error Dist – {label}", color=TEXT, fontsize=10)
        ax.set_xlabel("Error (°/s)", color=TEXT, fontsize=9)
        if i == 0:
            ax.set_ylabel("Count", color=TEXT)
    return _canvas(fig)


def tracking_errors_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    te = chart_data.get("tracking_errors")
    if not te:
        return None
    axes_list = [d.get("axis", f"Axis {i}") for i, d in enumerate(te)]
    rms_vals  = [d.get("rms_error", 0)  for d in te]
    max_vals  = [d.get("max_error", 0)  for d in te]
    x = np.arange(len(axes_list))
    w = 0.35
    fig, ax = _base_fig(height=3.2)
    ax.bar(x - w/2, rms_vals, w, label="RMS Error",  color="#4361ee", alpha=0.9, zorder=3)
    ax.bar(x + w/2, max_vals, w, label="Max Error",  color="#ef5350", alpha=0.9, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(axes_list, color=TEXT)
    ax.set_ylabel("Tracking Error (°/s)", color=TEXT)
    ax.set_title("PID Tracking Error Summary", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    return _canvas(fig)


def pid_contributions_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    pc = chart_data.get("pid_contributions")
    if not pc:
        return None
    axes_list = [d.get("axis", f"Axis {i}") for i, d in enumerate(pc)]
    terms = ["p_rms", "i_rms", "d_rms", "ff_rms"]
    term_labels = ["P", "I", "D", "FF"]
    term_colors = ["#4361ee", "#f06292", "#4db6ac", "#ffb74d"]
    x = np.arange(len(axes_list))
    w = 0.18
    fig, ax = _base_fig(height=3.2)
    for j, (term, lbl, col) in enumerate(zip(terms, term_labels, term_colors)):
        vals = [d.get(term, 0) for d in pc]
        ax.bar(x + j*w - 1.5*w, vals, w, label=lbl, color=col, alpha=0.9, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(axes_list, color=TEXT)
    ax.set_ylabel("RMS Contribution", color=TEXT)
    ax.set_title("PID Term Contributions", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    return _canvas(fig)


def vbat_trace_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    vb = chart_data.get("vbat_trace")
    if not vb:
        return None
    time    = vb.get("time", [])
    voltage = vb.get("voltage", [])
    fig, ax = _base_fig(height=2.8)
    x = time if time else list(range(len(voltage)))
    ax.plot(x, voltage, color="#4db6ac", linewidth=1.5)
    ax.set_xlabel("Time (s)", color=TEXT)
    ax.set_ylabel("Voltage (V)", color=TEXT)
    ax.set_title("Battery Voltage Over Flight", color=TEXT, fontsize=11)
    return _canvas(fig)


def throttle_trace_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    tt = chart_data.get("throttle_trace")
    if not tt:
        return None
    time     = tt.get("time", [])
    throttle = tt.get("throttle", [])
    fig, ax = _base_fig(height=2.5)
    x = time if time else list(range(len(throttle)))
    ax.fill_between(x, throttle, alpha=0.6, color="#4361ee")
    ax.set_xlabel("Time (s)", color=TEXT)
    ax.set_ylabel("Throttle", color=TEXT)
    ax.set_title("Throttle Input", color=TEXT, fontsize=11)
    return _canvas(fig)


# ── Master builder – returns list of (title, canvas) pairs ───────────────────

def build_all_charts(chart_data: dict) -> list[tuple[str, FigureCanvasQTAgg]]:
    """Build all applicable charts from chart_data. Returns (title, canvas) list."""
    builders = [
        ("Rate Curves",             lambda: rate_curves_chart(chart_data)),
        ("PID Values",              lambda: pid_radar_chart(chart_data)),
        ("Gyro Noise Spectrum",     lambda: noise_spectrum_chart(chart_data)),
        ("Pre/Post Filter",         lambda: pre_post_filter_chart(chart_data)),
        ("Setpoint vs Gyro",        lambda: setpoint_vs_gyro_chart(chart_data)),
        ("PID Tracking Errors",     lambda: tracking_errors_chart(chart_data)),
        ("PID Contributions",       lambda: pid_contributions_chart(chart_data)),
        ("PID Error Distribution",  lambda: error_histogram_chart(chart_data)),
        ("Motor Balance",           lambda: motor_balance_chart(chart_data)),
        ("Motor Outputs",           lambda: motor_outputs_chart(chart_data)),
        ("Battery Voltage",         lambda: vbat_trace_chart(chart_data)),
        ("Throttle",                lambda: throttle_trace_chart(chart_data)),
    ]
    result = []
    for title, fn in builders:
        try:
            canvas = fn()
            if canvas is not None:
                result.append((title, canvas))
        except Exception:  # pylint: disable=broad-except
            pass
    return result
