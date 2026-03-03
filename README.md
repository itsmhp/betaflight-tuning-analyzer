# Betaflight Tuning Analyzer

Advanced drone tuning analysis for **Betaflight** firmware. Upload your CLI dump and blackbox log — the app delivers comprehensive tuning recommendations with ready-to-paste CLI commands, powered by **15 analysis tools** inspired by FPV Nexus.

Available in **two modes**:
- 🖥️ **Desktop GUI** (Windows `.exe`) — native window, no browser, no Python needed
- 🌐 **Web App** — run locally or deploy to Render.com

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-41cd52)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Betaflight](https://img.shields.io/badge/Betaflight-4.x-orange)
![Tools](https://img.shields.io/badge/Analysis%20Tools-15-blueviolet)

---

## Features

### Analysis Pipeline

| Phase | Analysis |
|-------|----------|
| **Phase 1 — CLI Dump** | PID, Filter, Rates, Motor, General configuration audit |
| **Phase 2 — BBL Header** | Cross-check blackbox configuration against CLI |
| **Phase 3 — Flight Data** | 15 deep-analysis tools on real flight data |

### 15 Quick Tuning Tools

| # | Tool | What it does |
|---|------|------|
| 1 | **Step Response** | Per-axis step response timing, overshoot %, damping ratio |
| 2 | **Motor Health** | Per-motor balance, cross-correlation vibration detection |
| 3 | **TPA (Throttle PID Attenuation)** | 4-method breakpoint detection, optimal TPA rate |
| 4 | **Prop Wash** | FIR bandpass 20–100 Hz, sliding RMS washout detection |
| 5 | **Dynamic Idle** | Idle-window detection, adaptive RPM relaxation scaling |
| 6 | **Anti-Gravity** | Throttle-punch drift analysis, 5-tier severity grading |
| 7 | **I-Term Buildup** | Multi-threshold accumulation detection, axis bias check |
| 8 | **Feedforward** | Stick-manoeuvre detection, cross-correlation FF lag, health score |
| 9 | **Thrust Linearization** | MAPE analysis, dual onset detection, PID effort slope |
| 10 | **Stick Movement** | Smoothness, jitter, bounceback, expo suggestions |
| 11 | **Throttle Axis** | Hover-point detection, axis usage histogram, flight style |
| 12 | **PID Contribution** | P/D/F RMS ratios, D-term dominance warnings |
| 13 | **Noise Analyzer** | FFT noise spectrum, RPM harmonics, filter audit |
| 14 | **Filter Analyzer** | Lowpass / notch filter configuration validation |
| 15 | **Master Multiplier** | Interactive PID scaling utility with CLI generation |

### Additional Features
- **Quad Profile & Tuning Presets** — provide hardware details for context-aware recommendations
- **HTML Report Export** — export dark-themed standalone HTML report with embedded charts
- **Multi-language UI** — English, Bahasa Indonesia, Español, Deutsch
- **23 embedded charts** — matplotlib dark-mode charts (noise spectrum, rate curves, PID radar, step response, motor health, and more)
- **Tuning score** (0–100) with severity-coded findings
- **Ready-to-paste CLI commands** — copy to Betaflight CLI and save

---

## Option 1 — Desktop App (Windows .exe)

> No Python, no browser, no installation needed. Just download and run.

### Download

👉 **[Download latest release](https://github.com/itsmhp/betaflight-tuning-analyzer/releases/latest)**

Download `BetaflightTuningAnalyzer.exe` from the Assets section and run it directly.

### Usage
1. Double-click `BetaflightTuningAnalyzer.exe`
2. A native desktop window opens (no browser needed)
3. Select your CLI dump file (required) and `.bbl` blackbox log (optional)
4. Fill in your quad profile and choose a tuning preset if desired
5. Click **Analyze Tuning** — results appear with score, findings, and charts
6. Browse findings by category tabs, view charts, copy CLI commands
7. Click **Export HTML Report** to save a standalone report file

### blackbox_decode (Optional, for flight data charts)
To unlock FFT noise analysis and motor data from `.bbl` files:
1. Download [blackbox-tools](https://github.com/betaflight/blackbox-tools/releases)
2. Place `blackbox_decode.exe` next to `BetaflightTuningAnalyzer.exe`

---

## Option 2 — Web App (Local / Server)

### Prerequisites
- Python 3.10+
- `blackbox_decode` (optional)

### Setup
```bash
# Clone the repository
git clone https://github.com/itsmhp/betaflight-tuning-analyzer.git
cd betaflight-tuning-analyzer

# Install dependencies
pip install -r requirements.txt

# Run web mode
python run.py
```

Open your browser to `http://127.0.0.1:8000`

### Run Desktop GUI from source
```bash
# Install GUI dependencies (PySide6 + matplotlib)
pip install -r requirements.txt

# Run native desktop window
python run_gui.py
```

### blackbox_decode (Optional)
For FFT noise analysis & motor data from `.bbl` files:
1. Download [blackbox-tools](https://github.com/betaflight/blackbox-tools/releases)
2. Place `blackbox_decode.exe` (Windows) or `blackbox_decode` (Linux/Mac) in the `tools/` folder

---

## How to Get Your Files

### CLI Dump
1. Open **Betaflight Configurator** → connect your FC
2. Go to **CLI** tab → type `dump all` → Enter
3. Click **"Save to File"**

### Blackbox Log
- Copy the `.bbl` file from SD card or onboard flash to your computer

---

## Project Structure

```
betaflight-tuning-analyzer/
├── run_gui.py                  # Desktop GUI entry point
├── run.py                      # Web server entry point
├── app/
│   ├── core.py                 # Analysis pipeline orchestrator
│   ├── parsers/                # CLI dump & BBL parsers
│   ├── analyzers/              # 15 analysis tools
│   │   ├── step_response_analyzer.py
│   │   ├── motor_health_analyzer.py
│   │   ├── tpa_analyzer.py
│   │   ├── prop_wash_analyzer.py
│   │   ├── dynamic_idle_analyzer.py
│   │   ├── anti_gravity_analyzer.py
│   │   ├── iterm_buildup_analyzer.py
│   │   ├── feedforward_analyzer.py
│   │   ├── thrust_linearization_analyzer.py
│   │   ├── stick_movement_analyzer.py
│   │   ├── throttle_axis_analyzer.py
│   │   ├── pid_contribution_analyzer.py
│   │   ├── noise_analyzer.py
│   │   ├── filter_analyzer.py
│   │   └── master_multiplier.py
│   ├── generators/             # CLI command generator
│   └── knowledge/              # Best practices, presets
├── gui/
│   ├── main_window.py          # QStackedWidget page manager
│   ├── charts.py               # 23 matplotlib chart builders
│   ├── html_export.py          # Standalone HTML report generator
│   ├── style.py                # Dark QSS theme
│   ├── i18n.py                 # 4-language translations
│   ├── worker.py               # Background analysis thread
│   └── pages/
│       ├── upload_page.py      # File picker + quad profile form
│       └── results_page.py     # Tabbed results (overview, charts, CLI)
├── requirements.txt
├── betaflight_analyzer_gui.spec  # PyInstaller build spec
└── README.md
```

---

## Build .exe from Source

```bash
pip install pyinstaller
python -m PyInstaller betaflight_analyzer_gui.spec --clean
```

Output: `dist/BetaflightTuningAnalyzer.exe`

---

## Deployment (Render.com)

This app is configured for one-click deploy to [Render.com](https://render.com) via `render.yaml`.

1. Fork or push this repo to GitHub
2. Log in to [render.com](https://render.com) → **New > Web Service**
3. Connect this GitHub repo
4. Render will auto-detect `render.yaml`
5. Deploy!

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Desktop GUI | PySide6 (Qt6), matplotlib |
| Web backend | Python, FastAPI, uvicorn |
| Templating | Jinja2 |
| Analysis | NumPy, SciPy (FFT), Pandas |
| Web charts | Plotly.js |
| Report Export | Standalone HTML with embedded base64 charts |
| Build | PyInstaller |
| i18n | 4 languages (EN, ID, ES, DE) |

---

## Supported FC / Firmware

- Betaflight 4.3+
- All flight controllers supported by Betaflight
- BBL format from onboard blackbox and SD card logging

---

Made with care for the FPV community
