/**
 * Betaflight Tuning Analyzer – Plotly chart rendering.
 */

function renderCharts(data, layout) {
    if (!data || typeof Plotly === 'undefined') return;

    // ---- Noise Spectrum ----
    if (data.noise_spectra && document.getElementById('chart-noise-spectrum')) {
        const traces = data.noise_spectra.map(spec => ({
            x: spec.freqs,
            y: spec.psd,
            type: 'scatter',
            mode: 'lines',
            name: spec.axis || 'Gyro',
            line: { width: 1.5 },
        }));
        Plotly.newPlot('chart-noise-spectrum', traces, {
            ...layout,
            xaxis: { ...layout.xaxis, title: 'Frequency (Hz)', type: 'log' },
            yaxis: { ...layout.yaxis, title: 'Power Spectral Density', type: 'log' },
            legend: { x: 1, xanchor: 'right', y: 1 },
        }, { responsive: true });
    }

    // ---- Pre-filter vs Post-filter ----
    if (data.pre_post_spectra && document.getElementById('chart-pre-post')) {
        const traces = [];
        const colors = { Roll: '#ff6b6b', Pitch: '#51cf66', Yaw: '#339af0' };
        data.pre_post_spectra.forEach(spec => {
            const c = colors[spec.axis] || '#888';
            traces.push({
                x: spec.freqs,
                y: spec.psd_pre,
                type: 'scatter',
                mode: 'lines',
                name: spec.axis + ' Pre',
                line: { color: c, width: 1, dash: 'dot' },
            });
            traces.push({
                x: spec.freqs,
                y: spec.psd_post,
                type: 'scatter',
                mode: 'lines',
                name: spec.axis + ' Post',
                line: { color: c, width: 2 },
            });
        });
        Plotly.newPlot('chart-pre-post', traces, {
            ...layout,
            xaxis: { ...layout.xaxis, title: 'Frequency (Hz)', type: 'log' },
            yaxis: { ...layout.yaxis, title: 'PSD', type: 'log' },
        }, { responsive: true });
    }

    // ---- Motor Balance ----
    if (data.motor_balance && document.getElementById('chart-motor-balance')) {
        const means = data.motor_balance.motor_means || [];
        const stds = data.motor_balance.motor_stds || [];
        const labels = means.map((_, i) => 'Motor ' + (i + 1));
        const colors = ['#ff6b6b', '#51cf66', '#339af0', '#fcc419'];

        Plotly.newPlot('chart-motor-balance', [{
            x: labels,
            y: means,
            error_y: {
                type: 'data',
                array: stds,
                visible: true,
                color: '#888',
            },
            type: 'bar',
            marker: { color: colors },
        }], {
            ...layout,
            yaxis: { ...layout.yaxis, title: 'Average Output' },
        }, { responsive: true });
    }

    // ---- PID Contributions ----
    if (data.pid_contributions && document.getElementById('chart-pid-contrib')) {
        const axes = data.pid_contributions.map(d => d.axis);
        const p_vals = data.pid_contributions.map(d => d.p_rms);
        const i_vals = data.pid_contributions.map(d => d.i_rms);
        const d_vals = data.pid_contributions.map(d => d.d_rms);
        const f_vals = data.pid_contributions.map(d => d.f_rms);

        Plotly.newPlot('chart-pid-contrib', [
            { x: axes, y: p_vals, name: 'P', type: 'bar', marker: { color: '#339af0' } },
            { x: axes, y: i_vals, name: 'I', type: 'bar', marker: { color: '#51cf66' } },
            { x: axes, y: d_vals, name: 'D', type: 'bar', marker: { color: '#ff6b6b' } },
            { x: axes, y: f_vals, name: 'FF', type: 'bar', marker: { color: '#fcc419' } },
        ], {
            ...layout,
            barmode: 'group',
            yaxis: { ...layout.yaxis, title: 'RMS Value' },
        }, { responsive: true });
    }
}
