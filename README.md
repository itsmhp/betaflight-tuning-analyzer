# Betaflight Tuning Analyzer

Analyze your drone tuning on **Betaflight** firmware. Upload your CLI dump and blackbox log — the app delivers comprehensive tuning recommendations with ready-to-paste CLI commands.

Available in **two modes**:
- 🖥️ **Desktop GUI** (Windows `.exe`) — native window, no browser, no Python needed
- 🌐 **Web App** — run locally or deploy to Render.com

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-41cd52)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Betaflight](https://img.shields.io/badge/Betaflight-4.x-orange)

---

## Features

| Phase | Analysis |
|-------|----------|
| **Phase 1** | CLI dump – PID, Filter, Rates, Motor, General config |
| **Phase 2** | BBL header – cross-check blackbox configuration |
| **Phase 3** | Flight data – FFT noise, motor balance, PID tracking |

**Quad Profile & Tuning Presets:**
- Provide your quad hardware (frame size, props, battery, motors, weight) for context-aware recommendations
- Choose a tuning preset level (Low / Medium / High / Ultra) — get a ready-to-paste CLI script to match that tune style

**Output:**
- Tuning score (0–100)
- Findings organized by category (Error / Warning / Info)
- Ready-to-paste CLI commands for Betaflight CLI
- Interactive charts: rate curves, noise spectrum, PID tracking, motor balance, and more

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
| Build | PyInstaller |

---

## Supported FC / Firmware

- Betaflight 4.3+
- All flight controllers supported by Betaflight
- BBL format from onboard blackbox and SD card logging

---

Made with care for the FPV community
