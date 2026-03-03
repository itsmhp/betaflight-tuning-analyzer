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
    import numpy as _np
    fig, ax = _base_fig(height=4.2)
    all_filter_lines = []
    max_noise_freq = 0.0

    for i, s in enumerate(spectra[:3]):
        label  = s.get("axis", f"Axis {i}")
        freqs  = s.get("freqs", [])
        psd    = s.get("psd", [])
        peaks  = s.get("peaks", [])
        if freqs and psd:
            # Convert to dB scale (like Blackbox Log Viewer PSD view)
            psd_arr  = _np.array(psd, dtype=float)
            psd_db   = 10.0 * _np.log10(_np.clip(psd_arr, 1e-12, None))
            ax.plot(freqs, psd_db, color=COLORS[i % len(COLORS)],
                    linewidth=1.5, label=label, alpha=0.85)
            # Mark detected peaks with dotted verticals
            for fx, _ in peaks[:4]:
                ax.axvline(fx, color=COLORS[i % len(COLORS)],
                           linewidth=0.7, alpha=0.45, linestyle=":")
        if not all_filter_lines and s.get("filter_lines"):
            all_filter_lines = s["filter_lines"]
        if s.get("max_noise_freq", 0) > max_noise_freq:
            max_noise_freq = s["max_noise_freq"]

    # ── Draw filter overlays ──────────────────────────────────────────────────
    ymin, ymax = ax.get_ylim()
    drawn_labels: set = set()
    for fm in all_filter_lines:
        lbl     = fm.get("label", "")
        hz      = fm.get("hz", 0)
        col     = fm.get("color", "#ffffff")
        sty     = fm.get("style", "--")
        if hz <= 0 or lbl in drawn_labels:
            continue
        if sty == "notch":
            # V-shape notch: flares from center down to ±cutoff (like Blackbox Log Viewer)
            cutoff = fm.get("cutoff_hz", hz * 0.7)
            width  = hz - cutoff
            vx = [cutoff, hz, hz * 2 - cutoff]
            vy = [ymin,   ymax * 0.5 if ymax > 0 else ymin + (ymax - ymin) * 0.5, ymin]
            ax.plot(vx, vy, color=col, linewidth=1.2, alpha=0.80,
                    linestyle="-", label=f"{lbl} {hz:.0f}Hz")
        else:
            ax.axvline(hz, color=col, linewidth=1.2, linestyle=sty,
                       alpha=0.90, label=f"{lbl} {hz:.0f}Hz")
        drawn_labels.add(lbl)

    # ── Max noise frequency marker (red, like Blackbox Log Viewer) ────────────
    if max_noise_freq > 0:
        ax.axvline(max_noise_freq, color="#ff1744", linewidth=1.8,
                   alpha=0.85, linestyle="-",
                   label=f"Max noise {max_noise_freq:.0f}Hz")

    ax.set_xlabel("Frequency (Hz)", color=TEXT)
    ax.set_ylabel("PSD (dBm/Hz)", color=TEXT)
    ax.set_title("Gyro Noise Spectrum + Filter Cutoffs", color=TEXT, fontsize=11)
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=8,
              loc="upper right", ncol=2)
    return _canvas(fig)


def pre_post_filter_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    spectra = chart_data.get("pre_post_spectra")
    if not spectra:
        return None
    import numpy as _np
    n = min(len(spectra), 3)
    fig, axes_arr = _base_fig(nrows=n, ncols=1, height=3.2)
    if n == 1:
        axes_arr = [axes_arr]
    for i, s in enumerate(spectra[:n]):
        ax    = axes_arr[i]
        freqs = s.get("freqs", [])
        pre   = s.get("psd_pre", [])
        post  = s.get("psd", [])
        label = s.get("axis", f"Axis {i}")
        flines = s.get("filter_lines", [])
        if freqs and pre:
            pre_db = 10.0 * _np.log10(_np.clip(_np.array(pre, dtype=float), 1e-12, None))
            ax.plot(freqs, pre_db, color="#ef5350", linewidth=1.2, alpha=0.85,
                    label="Pre-filter (raw)")
        if freqs and post:
            post_db = 10.0 * _np.log10(_np.clip(_np.array(post, dtype=float), 1e-12, None))
            ax.plot(freqs, post_db, color="#4db6ac", linewidth=1.5, alpha=0.85,
                    label="Post-filter")
        # Draw filter cutoff lines + notch V-shapes
        drawn: set = set()
        ymin, ymax = ax.get_ylim()
        for fm in flines:
            lbl = fm.get("label", "")
            hz  = fm.get("hz", 0)
            col = fm.get("color", "#aaaaaa")
            sty = fm.get("style", "--")
            if hz <= 0 or lbl in drawn:
                continue
            if sty == "notch":
                cutoff = fm.get("cutoff_hz", hz * 0.7)
                vx = [cutoff, hz, hz * 2 - cutoff]
                vy = [ymin, ymax * 0.5 if ymax > 0 else ymin + (ymax - ymin) * 0.5, ymin]
                ax.plot(vx, vy, color=col, linewidth=1.0, alpha=0.75,
                        linestyle="-", label=f"{lbl} {hz:.0f}Hz")
            else:
                ax.axvline(hz, color=col, linewidth=1.0, linestyle=sty,
                           alpha=0.8, label=f"{lbl} {hz:.0f}Hz")
            drawn.add(lbl)
        ax.set_ylabel("PSD (dBm/Hz)", color=TEXT, fontsize=9)
        ax.set_title(f"Pre vs Post Filter – {label}", color=TEXT, fontsize=10)
        ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT,
                  fontsize=7, loc="upper right", ncol=2)
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


# ── New analyzer charts ───────────────────────────────────────────────────────

def step_response_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    """Per-axis step response overlay: setpoint vs gyro + P/D terms."""
    sr_list = chart_data.get("step_response")
    if not sr_list:
        return None
    n = min(len(sr_list), 3)
    fig, axes_arr = _base_fig(nrows=n, ncols=1, height=3.0)
    if n == 1:
        axes_arr = [axes_arr]
    for i, sr in enumerate(sr_list[:n]):
        ax = axes_arr[i]
        axis_name = sr.get("axis", f"Axis {i}")
        sp = sr.get("chart_setpoint", [])
        resp = sr.get("chart_response", [])
        p_term = sr.get("chart_p_term", [])
        d_term = sr.get("chart_d_term", [])
        x = list(range(len(sp))) if sp else []

        if sp:
            ax.plot(x, sp, color="#ffc107", linewidth=1.2, alpha=0.9, label="Setpoint")
        if resp:
            ax.plot(x[:len(resp)], resp, color="#4361ee", linewidth=1.5, alpha=0.85, label="Response")
        if p_term:
            ax.plot(x[:len(p_term)], p_term, color="#f06292", linewidth=0.8, alpha=0.6, label="P-term")
        if d_term:
            ax.plot(x[:len(d_term)], d_term, color="#4db6ac", linewidth=0.8, alpha=0.6, label="D-term")

        # Annotations
        quality = sr.get("pid_quality", 0)
        damping = sr.get("damping_ratio", 0)
        error = sr.get("setpoint_error_pct", 0)
        ax.set_title(
            f"Step Response – {axis_name}  "
            f"(Quality: {quality:.0f}%  Damping: {damping:.2f}  Error: {error:.1f}%)",
            color=TEXT, fontsize=10
        )
        ax.set_ylabel("°/s", color=TEXT, fontsize=9)
        ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=7,
                  loc="upper right", ncol=4)
    axes_arr[-1].set_xlabel("Sample", color=TEXT)
    return _canvas(fig)


def motor_health_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    """Motor Doctor: per-motor health scores as bar chart."""
    mh = chart_data.get("motor_health")
    if not mh or "motors" not in mh:
        return None
    motors = mh["motors"]
    labels = mh.get("motor_labels", [f"M{i+1}" for i in range(len(motors))])
    scores = [m.get("health_score", 0) * 100 for m in motors]
    stabilities = [m.get("stability", 0) * 100 for m in motors]
    deviations = [m.get("pct_deviation", 0) for m in motors]

    fig, axes_arr = _base_fig(nrows=1, ncols=2, height=3.5)
    if hasattr(axes_arr, "flat"):
        axes_arr = list(axes_arr.flat)

    # Health score bars
    ax1 = axes_arr[0]
    x = np.arange(len(labels))
    bar_colors = []
    for s in scores:
        if s >= 80:
            bar_colors.append("#4db6ac")
        elif s >= 60:
            bar_colors.append("#ffb74d")
        else:
            bar_colors.append("#ef5350")
    bars = ax1.bar(x, scores, color=bar_colors, alpha=0.9, zorder=3)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, color=TEXT)
    ax1.set_ylabel("Health Score (%)", color=TEXT)
    ax1.set_title("Motor Health Scores", color=TEXT, fontsize=10)
    ax1.set_ylim(0, 110)
    for bar, val in zip(bars, scores):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"{val:.0f}%", ha="center", va="bottom", fontsize=9, color=TEXT)

    # Stability vs Deviation scatter-like bar
    ax2 = axes_arr[1]
    w = 0.35
    ax2.bar(x - w/2, stabilities, w, label="Stability %", color="#4361ee", alpha=0.9, zorder=3)
    ax2.bar(x + w/2, deviations, w, label="Deviation %", color="#f06292", alpha=0.9, zorder=3)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(labels, color=TEXT)
    ax2.set_ylabel("Percentage", color=TEXT)
    ax2.set_title("Stability & Deviation", color=TEXT, fontsize=10)
    ax2.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=8)

    return _canvas(fig)


def tpa_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    """D-term energy vs throttle with breakpoint marker."""
    tpa = chart_data.get("tpa_analysis")
    if not tpa:
        return None
    throttle_pcts = tpa.get("chart_throttle_pcts", [])
    bucket_means = tpa.get("chart_bucket_means", [])
    bp_pct = tpa.get("breakpoint_pct", 50)
    suggested = tpa.get("suggested_rate", 0)
    rms_ratio = tpa.get("rms_ratio", 0)

    if not throttle_pcts or not bucket_means:
        return None

    fig, ax = _base_fig(height=3.8)
    ax.bar(throttle_pcts, bucket_means, width=2.2, color="#4361ee", alpha=0.85, zorder=3)

    # Breakpoint line
    ax.axvline(bp_pct, color="#ff1744", linewidth=2.0, linestyle="--",
               label=f"Breakpoint {bp_pct:.0f}%", zorder=4)

    # Low/high regions
    ax.axvspan(0, 35, alpha=0.08, color="#4db6ac", zorder=1)
    ax.axvspan(65, 100, alpha=0.08, color="#ef5350", zorder=1)

    ax.set_xlabel("Throttle (%)", color=TEXT)
    ax.set_ylabel("D-term Energy (smoothed)", color=TEXT)
    ax.set_title(
        f"TPA Analysis – Breakpoint: {bp_pct:.0f}%  "
        f"Rate: {suggested}%  RMS Ratio: {rms_ratio:.2f}×",
        color=TEXT, fontsize=10
    )
    ax.legend(facecolor="#1a1a38", edgecolor=AXIS, labelcolor=TEXT, fontsize=9)
    return _canvas(fig)


def prop_wash_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    """Prop wash severity and frequency overview."""
    pw = chart_data.get("prop_wash")
    if not pw:
        return None
    freq_info = pw.get("freq_info", {})
    severity = pw.get("severity_scores", {})
    overall = pw.get("overall_severity", 0)

    fig, axes_arr = _base_fig(nrows=1, ncols=2, height=3.5)
    if hasattr(axes_arr, "flat"):
        axes_arr = list(axes_arr.flat)

    # Severity breakdown
    ax1 = axes_arr[0]
    cats = ["Density", "Avg Severity", "Freq Score", "Correlation"]
    vals = [
        severity.get("density", 0),
        severity.get("avg_severity", 0),
        severity.get("freq_score", 0),
        severity.get("correlation", 0),
    ]
    bar_colors = ["#4361ee", "#f06292", "#4db6ac", "#ffb74d"]
    bars = ax1.bar(cats, vals, color=bar_colors, alpha=0.9, zorder=3)
    ax1.set_ylabel("Score", color=TEXT)
    ax1.set_title(f"Prop Wash Severity: {overall:.0f}%", color=TEXT, fontsize=10)
    ax1.tick_params(axis='x', rotation=25)
    for bar, val in zip(bars, vals):
        if val > 0:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                     f"{val:.0f}", ha="center", va="bottom", fontsize=8, color=TEXT)

    # Frequency band distribution
    ax2 = axes_arr[1]
    band_names = ["Stick\n<20Hz", "PropWash\n20-100Hz", "Frame\n100-250Hz", "Motor\n>250Hz"]
    band_vals = [
        freq_info.get("stick_inputs", 0),
        freq_info.get("prop_wash", 0),
        freq_info.get("frame_resonance", 0),
        freq_info.get("motor_noise", 0),
    ]
    band_colors = ["#ffb74d", "#ef5350", "#ce93d8", "#4db6ac"]
    bars2 = ax2.bar(band_names, band_vals, color=band_colors, alpha=0.9, zorder=3)
    ax2.set_ylabel("Energy (%)", color=TEXT)
    ax2.set_title("Frequency Band Distribution", color=TEXT, fontsize=10)
    for bar, val in zip(bars2, band_vals):
        if val > 0:
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                     f"{val:.0f}%", ha="center", va="bottom", fontsize=8, color=TEXT)

    return _canvas(fig)


# ── Anti-Gravity chart ────────────────────────────────────────────────────────

def anti_gravity_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    ag = chart_data.get("anti_gravity")
    if not ag:
        return None

    fig, axes = _base_fig(nrows=1, ncols=2, height=3.5)
    ax1, ax2 = axes.flat if hasattr(axes, "flat") else axes

    # Left: drift magnitudes as grouped bar
    labels = []
    up_vals = []
    down_vals = []
    for ev_type in ["punch_up", "punch_down"]:
        ev = ag.get(ev_type, {})
        if ev:
            labels.append(ev_type.replace("_", " ").title())
            up_vals.append(ev.get("avg_roll_drift", 0))
            down_vals.append(ev.get("avg_pitch_drift", 0))

    if labels:
        x = np.arange(len(labels))
        w = 0.35
        ax1.bar(x - w/2, up_vals, w, label="Roll Drift", color=COLORS[0], alpha=0.85)
        ax1.bar(x + w/2, down_vals, w, label="Pitch Drift", color=COLORS[1], alpha=0.85)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, fontsize=8)
        ax1.set_ylabel("Drift (°/s)", color=TEXT)
        ax1.set_title("Anti-Gravity Drift", color=TEXT, fontsize=10)
        ax1.legend(fontsize=7, facecolor=BG, edgecolor=AXIS, labelcolor=TEXT)
    else:
        ax1.text(0.5, 0.5, "No punch events", transform=ax1.transAxes,
                 ha="center", color=TEXT)

    # Right: overall status and magnitude
    status = ag.get("status", "N/A")
    magnitude = ag.get("drift_magnitude", 0)
    colors_map = {"Excellent": "#4db6ac", "Good": "#81c784", "Moderate": "#ffb74d",
                  "Poor": "#ef5350", "Critical": "#ff1744"}
    col = colors_map.get(status, TEXT)
    ax2.text(0.5, 0.6, f"{magnitude:.0f}°/s", transform=ax2.transAxes,
             ha="center", va="center", fontsize=36, fontweight="bold", color=col)
    ax2.text(0.5, 0.35, status, transform=ax2.transAxes,
             ha="center", va="center", fontsize=16, color=col)
    ax2.set_title("Overall Drift Magnitude", color=TEXT, fontsize=10)
    ax2.set_xticks([])
    ax2.set_yticks([])

    fig.tight_layout(pad=1.0)
    return _canvas(fig)


# ── I-Term Build-Up chart ────────────────────────────────────────────────────

def iterm_buildup_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    it = chart_data.get("iterm_buildup")
    if not it:
        return None

    fig, ax = _base_fig(height=3.5)
    axis_data = it.get("axis_results", {})
    if not axis_data:
        return None

    labels = list(axis_data.keys())
    pct_high = [axis_data[a].get("pct_high_75", 0) for a in labels]
    colors = []
    for p in pct_high:
        if p < 10:
            colors.append("#4db6ac")
        elif p < 20:
            colors.append("#ffb74d")
        else:
            colors.append("#ef5350")

    bars = ax.bar(labels, pct_high, color=colors, alpha=0.9, zorder=3)
    ax.axhline(10, color="#ffb74d", ls="--", lw=1, alpha=0.6, label="Fair threshold")
    ax.axhline(20, color="#ef5350", ls="--", lw=1, alpha=0.6, label="Poor threshold")
    ax.set_ylabel("% samples |I-term| > 75", color=TEXT)
    ax.set_title("I-Term Build-Up per Axis", color=TEXT, fontsize=10)
    ax.legend(fontsize=7, facecolor=BG, edgecolor=AXIS, labelcolor=TEXT)

    for bar, val in zip(bars, pct_high):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=9, color=TEXT)

    fig.tight_layout(pad=1.0)
    return _canvas(fig)


# ── FeedForward chart ─────────────────────────────────────────────────────────

def feedforward_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    ff = chart_data.get("feedforward")
    if not ff:
        return None

    axis_results = ff.get("axis_results", {})
    if not axis_results:
        return None

    fig, axes = _base_fig(nrows=1, ncols=2, height=3.5)
    ax1, ax2 = axes.flat if hasattr(axes, "flat") else axes

    # Left: health scores per axis
    labels = list(axis_results.keys())
    healths = [axis_results[a]["health_score"] for a in labels]
    hcolors = []
    for h in healths:
        if h >= 80:
            hcolors.append("#4db6ac")
        elif h >= 60:
            hcolors.append("#ffb74d")
        else:
            hcolors.append("#ef5350")

    bars = ax1.barh(labels, healths, color=hcolors, alpha=0.9, zorder=3)
    ax1.set_xlim(0, 100)
    ax1.set_xlabel("Health Score (%)", color=TEXT)
    ax1.set_title("FeedForward Health", color=TEXT, fontsize=10)
    for bar, val in zip(bars, healths):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                 f"{val:.0f}%", va="center", fontsize=9, color=TEXT)

    # Right: avg tracking + lag per axis
    tr = [axis_results[a].get("avg_tracking", 0) * 100 for a in labels]
    lag = [axis_results[a].get("avg_lag", 0) for a in labels]
    x = np.arange(len(labels))
    w = 0.35
    ax2.bar(x - w/2, tr, w, label="Tracking %", color=COLORS[0], alpha=0.85)
    ax2b = ax2.twinx()
    ax2b.bar(x + w/2, lag, w, label="Avg Lag (samples)", color=COLORS[1], alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel("Tracking (%)", color=TEXT)
    ax2b.set_ylabel("Lag (samples)", color=TEXT)
    ax2b.tick_params(colors=TEXT, labelsize=9)
    for spine in ax2b.spines.values():
        spine.set_edgecolor(AXIS)
    ax2.set_title("Tracking & Lag", color=TEXT, fontsize=10)

    fig.tight_layout(pad=1.0)
    return _canvas(fig)


# ── Thrust Linearization chart ────────────────────────────────────────────────

def thrust_linearization_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    tl = chart_data.get("thrust_linearization")
    if not tl:
        return None

    curve = tl.get("thrust_curve", {})
    thr_pct = curve.get("throttle_pct", [])
    mot_pct = curve.get("motor_pct", [])
    pred = curve.get("predicted", [])

    if not thr_pct or not mot_pct:
        return None

    fig, axes = _base_fig(nrows=1, ncols=2, height=3.5)
    ax1, ax2 = axes.flat if hasattr(axes, "flat") else axes

    # Left: throttle vs motor + linear fit
    ax1.scatter(thr_pct, mot_pct, s=1, alpha=0.3, color=COLORS[0], label="Actual")
    if pred:
        ax1.plot(thr_pct, pred, color=COLORS[1], lw=2, label="Linear Baseline", zorder=5)
    onset = tl.get("onset_pct")
    if onset is not None:
        ax1.axvline(onset, color="#ef5350", ls="--", lw=1.5, label=f"Onset: {onset:.0f}%")
    ax1.set_xlabel("Throttle (%)", color=TEXT)
    ax1.set_ylabel("Motor Output (%)", color=TEXT)
    ax1.set_title("Thrust Curve", color=TEXT, fontsize=10)
    ax1.legend(fontsize=7, facecolor=BG, edgecolor=AXIS, labelcolor=TEXT)

    # Right: summary text
    mape = tl.get("mape", 0)
    diag = tl.get("diagnosis", "N/A")
    hover = tl.get("hover_pct")
    slope = tl.get("pid_effort_slope")
    col = "#4db6ac" if mape < 3 else "#ffb74d" if mape < 8 else "#ef5350"
    text_lines = [
        f"MAPE: {mape:.1f}%",
        f"Diagnosis: {diag}",
    ]
    if onset is not None:
        text_lines.append(f"Non-linear onset: {onset:.0f}%")
    if hover is not None:
        text_lines.append(f"Hover throttle: {hover:.0f}%")
    if slope is not None:
        text_lines.append(f"PID effort slope: {slope:.4f}")

    ax2.text(0.5, 0.5, "\n".join(text_lines), transform=ax2.transAxes,
             ha="center", va="center", fontsize=12, color=col,
             family="monospace", linespacing=1.8)
    ax2.set_title("Linearity Summary", color=TEXT, fontsize=10)
    ax2.set_xticks([])
    ax2.set_yticks([])

    fig.tight_layout(pad=1.0)
    return _canvas(fig)


# ── Stick Movement chart ──────────────────────────────────────────────────────

def stick_movement_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    sm = chart_data.get("stick_movement")
    if not sm:
        return None

    axis_results = sm.get("axis_results", {})
    if not axis_results:
        return None

    fig, axes = _base_fig(nrows=1, ncols=3, height=3.5)
    ax_arr = axes.flat if hasattr(axes, "flat") else axes

    metrics = {
        "Smoothness": ("smoothness", 100),
        "Symmetry": ("symmetry", 100),
        "Jitter": ("jitter_score", 20),
    }

    for ax, (title, (key, vmax)) in zip(ax_arr, metrics.items()):
        labels = list(axis_results.keys())
        vals = [axis_results[a].get(key, 0) for a in labels]
        colors = []
        for v in vals:
            if key == "jitter_score":
                colors.append("#4db6ac" if v < 3 else "#ffb74d" if v < 8 else "#ef5350")
            else:
                colors.append("#4db6ac" if v > 70 else "#ffb74d" if v > 40 else "#ef5350")
        bars = ax.bar(labels, vals, color=colors, alpha=0.9, zorder=3)
        ax.set_ylim(0, vmax)
        ax.set_title(title, color=TEXT, fontsize=10)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8, color=TEXT)

    fig.suptitle(f"Flight Style: {sm.get('flight_style', 'Unknown')}",
                 color=TEXT, fontsize=11, y=0.98)
    fig.tight_layout(pad=1.0, rect=[0, 0, 1, 0.94])
    return _canvas(fig)


# ── Throttle & Axis chart ────────────────────────────────────────────────────

def throttle_axis_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    ta = chart_data.get("throttle_axis")
    if not ta:
        return None

    fig, axes = _base_fig(nrows=1, ncols=2, height=3.5)
    ax1, ax2 = axes.flat if hasattr(axes, "flat") else axes

    # Left: throttle histogram with hover line
    hist_vals = ta.get("throttle_histogram", {}).get("values", [])
    if hist_vals:
        ax1.hist(hist_vals, bins=40, color=COLORS[0], alpha=0.8, edgecolor=AXIS)
        hover = ta.get("hover_raw")
        if hover is not None:
            ax1.axvline(hover, color="#f06292", ls="--", lw=2,
                       label=f"Hover: {ta.get('hover_pct', 0):.0f}%")
            ax1.legend(fontsize=7, facecolor=BG, edgecolor=AXIS, labelcolor=TEXT)
    ax1.set_xlabel("Throttle", color=TEXT)
    ax1.set_ylabel("Samples", color=TEXT)
    ax1.set_title("Throttle Distribution", color=TEXT, fontsize=10)

    # Right: axis usage pie or bar
    axis_analysis = ta.get("axis_analysis", {})
    if axis_analysis:
        labels = list(axis_analysis.keys())
        totals = [axis_analysis[a].get("pct_of_total", 0) for a in labels]
        ax2.bar(labels, totals, color=COLORS[:len(labels)], alpha=0.9, zorder=3)
        ax2.set_ylabel("% of Total Control", color=TEXT)
        ax2.set_title("Axis Usage", color=TEXT, fontsize=10)
        for i, (lbl, val) in enumerate(zip(labels, totals)):
            ax2.text(i, val + 0.5, f"{val:.0f}%", ha="center", fontsize=9, color=TEXT)
    else:
        ax2.text(0.5, 0.5, "No axis data", transform=ax2.transAxes,
                 ha="center", color=TEXT)

    fig.suptitle(f"Style: {ta.get('flight_style', 'Unknown')}",
                 color=TEXT, fontsize=11, y=0.98)
    fig.tight_layout(pad=1.0, rect=[0, 0, 1, 0.94])
    return _canvas(fig)


# ── PID Contribution chart ────────────────────────────────────────────────────

def pid_contribution_detail_chart(chart_data: dict) -> Optional[FigureCanvasQTAgg]:
    pc = chart_data.get("pid_contribution")
    if not pc:
        return None

    axis_results = pc.get("axis_results", {})
    if not axis_results:
        return None

    fig, ax = _base_fig(height=4)
    labels = list(axis_results.keys())
    terms = ["P", "D", "F"]
    term_colors = [COLORS[0], COLORS[1], COLORS[2]]

    x = np.arange(len(labels))
    width = 0.2

    for i, term in enumerate(terms):
        vals = [axis_results[a]["ratios"].get(term, 0) for a in labels]
        bars = ax.bar(x + i * width, vals, width, label=term, color=term_colors[i], alpha=0.9, zorder=3)
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                        f"{val:.0f}%", ha="center", va="bottom", fontsize=8, color=TEXT)

    # D-term warning lines
    ax.axhline(30, color="#ffb74d", ls="--", lw=1, alpha=0.5)
    ax.axhline(40, color="#ef5350", ls="--", lw=1, alpha=0.5)

    ax.set_xticks(x + width)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Contribution (%)", color=TEXT)
    ax.set_title("P/D/F Contribution Ratio (I excluded)", color=TEXT, fontsize=10)
    ax.legend(fontsize=8, facecolor=BG, edgecolor=AXIS, labelcolor=TEXT)

    fig.tight_layout(pad=1.0)
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
        ("Step Response",           lambda: step_response_chart(chart_data)),
        ("PID Tracking Errors",     lambda: tracking_errors_chart(chart_data)),
        ("PID Contributions",       lambda: pid_contributions_chart(chart_data)),
        ("PID Contribution Detail", lambda: pid_contribution_detail_chart(chart_data)),
        ("PID Error Distribution",  lambda: error_histogram_chart(chart_data)),
        ("TPA Analysis",            lambda: tpa_chart(chart_data)),
        ("Motor Health",            lambda: motor_health_chart(chart_data)),
        ("Motor Balance",           lambda: motor_balance_chart(chart_data)),
        ("Motor Outputs",           lambda: motor_outputs_chart(chart_data)),
        ("Prop Wash",               lambda: prop_wash_chart(chart_data)),
        ("Anti-Gravity",            lambda: anti_gravity_chart(chart_data)),
        ("I-Term Build-Up",         lambda: iterm_buildup_chart(chart_data)),
        ("FeedForward",             lambda: feedforward_chart(chart_data)),
        ("Thrust Linearization",    lambda: thrust_linearization_chart(chart_data)),
        ("Stick Movement",          lambda: stick_movement_chart(chart_data)),
        ("Throttle & Axis",         lambda: throttle_axis_chart(chart_data)),
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
