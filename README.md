# Betaflight Tuning Analyzer

A web application for analyzing drone tuning on **Betaflight** firmware. Upload your CLI dump and blackbox log — the app delivers comprehensive tuning recommendations with ready-to-paste CLI commands.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Betaflight](https://img.shields.io/badge/Betaflight-4.x-orange)

---

## Features

| Phase | Analysis |
|-------|----------|
| **Phase 1** | CLI dump – PID, Filter, Rates, Motor, General config |
| **Phase 2** | BBL header – cross-check blackbox configuration |
| **Phase 3** | Flight data – FFT noise, motor balance, PID tracking |

**New — Quad Profile & Tuning Presets:**
- Provide your quad hardware (frame size, props, battery, motors, weight) for context-aware recommendations
- Choose a tuning preset level (Low / Medium / High / Ultra) like KISS firmware — get a ready-to-paste CLI script to match that tune style

**Output:**
- Tuning score (0–100)
- Findings organized by category (Error / Warning / Info)
- Ready-to-paste CLI commands for Betaflight CLI

---

## How to Use

### 1. Get Your CLI Dump
1. Open **Betaflight Configurator**
2. Connect to your flight controller
3. Go to the **CLI** tab → type `dump all` → Enter
4. Click **"Save to File"**

### 2. Get Your Blackbox Log
- Copy the `.bbl` file from SD card or onboard flash to your computer

### 3. Upload to the App
- Open `http://localhost:8000`
- Upload CLI dump (required) + BBL log (optional)
- Optionally fill in your quad profile and select a tuning preset
- Click **Analyze Tuning**

---

## Local Installation

### Prerequisites
- Python 3.10+
- `blackbox_decode` (optional, for full flight data analysis)

### Setup
```bash
# Clone the repository
git clone https://github.com/itsmhp/betaflight-tuning-analyzer.git
cd betaflight-tuning-analyzer

# Install dependencies
pip install -r requirements.txt

# Run
python run.py
```

Open your browser to `http://127.0.0.1:8000`

### blackbox_decode (Optional)
For FFT noise analysis & motor data from `.bbl` files:
1. Download [blackbox-tools](https://github.com/betaflight/blackbox-tools/releases)
2. Place `blackbox_decode.exe` (Windows) or `blackbox_decode` (Linux/Mac) in the `tools/` folder

---

## Standalone Executable

A pre-built single-file `.exe` for Windows is available (built with PyInstaller):

```bash
python -m PyInstaller betaflight_analyzer.spec --clean
```

The output will be in `dist/betaflight_analyzer.exe`. Run it and open `http://127.0.0.1:8000`.

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

- **Backend:** Python, FastAPI, uvicorn
- **Templating:** Jinja2
- **Analysis:** NumPy, SciPy (FFT), Pandas
- **Charts:** Plotly.js (client-side)
- **Deployment:** Render.com / PyInstaller (exe)

---

## Supported FC / Firmware

- Betaflight 4.3+
- All flight controllers supported by Betaflight
- BBL format from onboard blackbox and SD card logging

---

Made with care for the FPV community
