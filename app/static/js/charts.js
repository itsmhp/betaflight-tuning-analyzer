/**
 * Betaflight Tuning Analyzer – Plotly chart rendering.
 *
 * Renders up to 12 chart types from analysis data:
 *  1. Noise Spectrum (per axis)
 *  2. Pre-filter vs Post-filter
 *  3. Motor Balance (bar + error)
 *  4. PID Term Contributions (grouped bar)
 *  5. Setpoint vs Gyro overlay (time domain)
 *  6. Motor Outputs over time
 *  7. Battery Voltage over time
 *  8. Throttle Trace
 *  9. PID Error Histogram
 * 10. Rate Curves
 * 11. PID Radar / Spider chart
 * 12. Tracking Error Summary
 */

const AXIS_COLORS = {
    Roll:  '#ff6b6b',
    Pitch: '#51cf66',
    Yaw:   '#339af0',
};
const MOTOR_COLORS = ['#ff6b6b', '#51cf66', '#339af0', '#fcc419'];
const PID_COLORS   = { P: '#339af0', I: '#51cf66', D: '#ff6b6b', FF: '#fcc419' };

function renderCharts(data, layout) {
    if (!data || typeof Plotly === 'undefined') return;

    // ================================================================
    // 1. Noise Spectrum
    // ================================================================
    if (data.noise_spectra && document.getElementById('chart-noise-spectrum')) {
        const traces = data.noise_spectra.map(spec => ({
            x: spec.freqs,
            y: spec.psd,
            type: 'scatter',
            mode: 'lines',
            name: spec.axis || 'Gyro',
            line: { width: 1.5, color: AXIS_COLORS[spec.axis] },
        }));
        Plotly.newPlot('chart-noise-spectrum', traces, {
            ...layout,
            title: { text: 'Gyro Noise Spectrum', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Frequency (Hz)', type: 'log', range: [Math.log10(50), Math.log10(2000)] },
            yaxis: { ...layout.yaxis, title: 'Power Spectral Density (dB/Hz)', type: 'log' },
            legend: { x: 1, xanchor: 'right', y: 1, font: { color: '#aaa' } },
        }, { responsive: true });
    }

    // ================================================================
    // 2. Pre-filter vs Post-filter
    // ================================================================
    if (data.pre_post_spectra && document.getElementById('chart-pre-post')) {
        const traces = [];
        data.pre_post_spectra.forEach(spec => {
            const c = AXIS_COLORS[spec.axis] || '#888';
            traces.push({
                x: spec.freqs, y: spec.psd_pre,
                type: 'scatter', mode: 'lines',
                name: spec.axis + ' Pre-filter',
                line: { color: c, width: 1, dash: 'dot' },
            });
            traces.push({
                x: spec.freqs, y: spec.psd_post,
                type: 'scatter', mode: 'lines',
                name: spec.axis + ' Post-filter',
                line: { color: c, width: 2 },
            });
        });
        Plotly.newPlot('chart-pre-post', traces, {
            ...layout,
            title: { text: 'Pre-Filter vs Post-Filter Spectrum', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Frequency (Hz)', type: 'log' },
            yaxis: { ...layout.yaxis, title: 'PSD', type: 'log' },
        }, { responsive: true });
    }

    // ================================================================
    // 3. Motor Balance
    // ================================================================
    if (data.motor_balance && document.getElementById('chart-motor-balance')) {
        const means = data.motor_balance.motor_means || [];
        const stds  = data.motor_balance.motor_stds  || [];
        const labels = means.map((_, i) => 'Motor ' + (i + 1));

        Plotly.newPlot('chart-motor-balance', [{
            x: labels, y: means,
            error_y: { type: 'data', array: stds, visible: true, color: '#888' },
            type: 'bar',
            marker: { color: MOTOR_COLORS, line: { color: '#fff', width: 1 } },
        }], {
            ...layout,
            title: { text: 'Motor Balance (Average Output)', font: { color: '#e0e0e0', size: 14 } },
            yaxis: { ...layout.yaxis, title: 'Average Output' },
        }, { responsive: true });
    }

    // ================================================================
    // 4. PID Term Contributions
    // ================================================================
    if (data.pid_contributions && document.getElementById('chart-pid-contrib')) {
        const axes   = data.pid_contributions.map(d => d.axis);
        const p_vals = data.pid_contributions.map(d => d.p_rms);
        const i_vals = data.pid_contributions.map(d => d.i_rms);
        const d_vals = data.pid_contributions.map(d => d.d_rms);
        const f_vals = data.pid_contributions.map(d => d.f_rms);

        Plotly.newPlot('chart-pid-contrib', [
            { x: axes, y: p_vals, name: 'P',  type: 'bar', marker: { color: PID_COLORS.P } },
            { x: axes, y: i_vals, name: 'I',  type: 'bar', marker: { color: PID_COLORS.I } },
            { x: axes, y: d_vals, name: 'D',  type: 'bar', marker: { color: PID_COLORS.D } },
            { x: axes, y: f_vals, name: 'FF', type: 'bar', marker: { color: PID_COLORS.FF } },
        ], {
            ...layout,
            barmode: 'group',
            title: { text: 'PID Term Contributions (RMS)', font: { color: '#e0e0e0', size: 14 } },
            yaxis: { ...layout.yaxis, title: 'RMS Value' },
        }, { responsive: true });
    }

    // ================================================================
    // 5. Setpoint vs Gyro (time domain)
    // ================================================================
    if (data.setpoint_vs_gyro && document.getElementById('chart-sp-gyro')) {
        const time = data.setpoint_vs_gyro.time;
        const traces = [];
        for (const axis of ['Roll', 'Pitch', 'Yaw']) {
            if (data.setpoint_vs_gyro[axis]) {
                const d = data.setpoint_vs_gyro[axis];
                const c = AXIS_COLORS[axis];
                traces.push({
                    x: time, y: d.setpoint,
                    type: 'scatter', mode: 'lines',
                    name: axis + ' Setpoint',
                    line: { color: c, width: 1, dash: 'dot' },
                    opacity: 0.6,
                });
                traces.push({
                    x: time, y: d.gyro,
                    type: 'scatter', mode: 'lines',
                    name: axis + ' Gyro',
                    line: { color: c, width: 1.5 },
                });
            }
        }
        Plotly.newPlot('chart-sp-gyro', traces, {
            ...layout,
            title: { text: 'Setpoint vs Gyro Response', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Time (s)' },
            yaxis: { ...layout.yaxis, title: 'deg/s' },
            legend: { x: 1, xanchor: 'right', y: 1, font: { color: '#aaa', size: 10 } },
        }, { responsive: true });
    }

    // ================================================================
    // 6. Motor Outputs over time
    // ================================================================
    if (data.motor_outputs && document.getElementById('chart-motor-time')) {
        const time = data.motor_outputs.time;
        const traces = [];
        for (let i = 1; i <= 4; i++) {
            const key = 'Motor ' + i;
            if (data.motor_outputs[key]) {
                traces.push({
                    x: time, y: data.motor_outputs[key],
                    type: 'scatter', mode: 'lines',
                    name: key,
                    line: { color: MOTOR_COLORS[i - 1], width: 1 },
                });
            }
        }
        Plotly.newPlot('chart-motor-time', traces, {
            ...layout,
            title: { text: 'Motor Outputs Over Time', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Time (s)' },
            yaxis: { ...layout.yaxis, title: 'Motor Output' },
        }, { responsive: true });
    }

    // ================================================================
    // 7. Battery Voltage
    // ================================================================
    if (data.vbat_trace && document.getElementById('chart-vbat')) {
        Plotly.newPlot('chart-vbat', [{
            x: data.vbat_trace.time,
            y: data.vbat_trace.voltage,
            type: 'scatter', mode: 'lines',
            name: 'Voltage',
            line: { color: '#fcc419', width: 2 },
            fill: 'tozeroy',
            fillcolor: 'rgba(252, 196, 25, 0.08)',
        }], {
            ...layout,
            title: { text: 'Battery Voltage', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Time (s)' },
            yaxis: { ...layout.yaxis, title: 'Voltage (V)' },
        }, { responsive: true });
    }

    // ================================================================
    // 8. Throttle Trace
    // ================================================================
    if (data.throttle_trace && document.getElementById('chart-throttle')) {
        Plotly.newPlot('chart-throttle', [{
            x: data.throttle_trace.time,
            y: data.throttle_trace.throttle,
            type: 'scatter', mode: 'lines',
            name: 'Throttle',
            line: { color: '#a855f7', width: 1.5 },
            fill: 'tozeroy',
            fillcolor: 'rgba(168, 85, 247, 0.08)',
        }], {
            ...layout,
            title: { text: 'Throttle Input', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Time (s)' },
            yaxis: { ...layout.yaxis, title: 'Throttle' },
        }, { responsive: true });
    }

    // ================================================================
    // 9. PID Error Histogram
    // ================================================================
    if (data.error_histogram && document.getElementById('chart-error-hist')) {
        const traces = [];
        for (const axis of ['Roll', 'Pitch', 'Yaw']) {
            if (data.error_histogram[axis]) {
                const d = data.error_histogram[axis];
                traces.push({
                    x: d.bins, y: d.counts,
                    type: 'bar', name: axis,
                    marker: { color: AXIS_COLORS[axis], opacity: 0.65 },
                });
            }
        }
        Plotly.newPlot('chart-error-hist', traces, {
            ...layout,
            barmode: 'overlay',
            title: { text: 'PID Tracking Error Distribution', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Error (deg/s)' },
            yaxis: { ...layout.yaxis, title: 'Count' },
        }, { responsive: true });
    }

    // ================================================================
    // 10. Rate Curves
    // ================================================================
    if (data.rate_curves && document.getElementById('chart-rate-curves')) {
        const stickPct = data.rate_curves.stick_pct;
        const traces = [];
        for (const axis of ['Roll', 'Pitch', 'Yaw']) {
            if (data.rate_curves[axis]) {
                traces.push({
                    x: stickPct, y: data.rate_curves[axis],
                    type: 'scatter', mode: 'lines',
                    name: axis,
                    line: { color: AXIS_COLORS[axis], width: 2.5 },
                });
            }
        }
        Plotly.newPlot('chart-rate-curves', traces, {
            ...layout,
            title: { text: 'Rate Curves (Stick Input → deg/s)', font: { color: '#e0e0e0', size: 14 } },
            xaxis: { ...layout.xaxis, title: 'Stick Position (%)', range: [0, 100] },
            yaxis: { ...layout.yaxis, title: 'Rate (deg/s)' },
            legend: { x: 0.02, y: 0.98, font: { color: '#aaa' } },
        }, { responsive: true });
    }

    // ================================================================
    // 11. PID Radar / Spider Chart
    // ================================================================
    if (data.pid_radar && document.getElementById('chart-pid-radar')) {
        const theta = data.pid_radar.axes.concat([data.pid_radar.axes[0]]);
        const vals  = data.pid_radar.values.concat([data.pid_radar.values[0]]);
        const ref   = data.pid_radar.reference.concat([data.pid_radar.reference[0]]);

        Plotly.newPlot('chart-pid-radar', [
            {
                type: 'scatterpolar', mode: 'lines+markers',
                r: vals, theta: theta, name: 'Your Tune',
                line: { color: '#58a6ff', width: 2 },
                marker: { size: 6, color: '#58a6ff' },
                fill: 'toself', fillcolor: 'rgba(88,166,255,0.12)',
            },
            {
                type: 'scatterpolar', mode: 'lines',
                r: ref, theta: theta, name: 'BF Default',
                line: { color: '#6e7681', width: 1, dash: 'dot' },
            },
        ], {
            ...layout,
            title: { text: 'PID Tune Shape', font: { color: '#e0e0e0', size: 14 } },
            polar: {
                bgcolor: 'rgba(22,33,62,0.6)',
                radialaxis: { visible: true, color: '#6e7681', gridcolor: '#2a2a4a' },
                angularaxis: { color: '#8b949e', gridcolor: '#2a2a4a' },
            },
            showlegend: true,
            legend: { font: { color: '#aaa' } },
        }, { responsive: true });
    }

    // ================================================================
    // 12. Tracking Error Summary (bar chart)
    // ================================================================
    if (data.tracking_errors && document.getElementById('chart-tracking')) {
        const axes = data.tracking_errors.map(d => d.axis);
        const rms  = data.tracking_errors.map(d => d.rms_error);
        const maxE = data.tracking_errors.map(d => d.max_error);

        Plotly.newPlot('chart-tracking', [
            {
                x: axes, y: rms, name: 'RMS Error',
                type: 'bar', marker: { color: '#58a6ff' },
            },
            {
                x: axes, y: maxE, name: 'Max Error',
                type: 'bar', marker: { color: '#ff6b6b', opacity: 0.6 },
            },
        ], {
            ...layout,
            barmode: 'group',
            title: { text: 'Tracking Error per Axis', font: { color: '#e0e0e0', size: 14 } },
            yaxis: { ...layout.yaxis, title: 'Error (deg/s)' },
        }, { responsive: true });
    }
}
