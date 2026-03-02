# Betaflight Tuning Analyzer ✈️⚙️

Aplikasi web untuk menganalisis tuning drone yang menggunakan firmware **Betaflight**. Cukup upload file CLI dump dan blackbox log, aplikasi akan memberikan rekomendasi tuning lengkap dengan CLI commands siap paste.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Betaflight](https://img.shields.io/badge/Betaflight-4.x-orange)

---

## Fitur

| Phase | Analisis |
|-------|----------|
| **Phase 1** | CLI dump – PID, Filter, Rates, Motor, General config |
| **Phase 2** | BBL header – cross-check konfigurasi blackbox |
| **Phase 3** | Flight data – FFT noise, motor balance, PID tracking |

**Output:**
- Skor tuning (0–100)
- Temuan terorganisir per kategori (Error / Warning / Info)
- CLI commands siap paste ke Betaflight CLI

---

## Cara Pakai

### 1. Dapatkan CLI Dump
1. Buka **Betaflight Configurator**
2. Connect ke flight controller
3. Tab **CLI** → ketik `dump all` → Enter
4. Klik **"Save to File"**

### 2. Dapatkan Blackbox Log
- Copy file `.bbl` dari SD card / onboard flash ke komputer

### 3. Upload ke Aplikasi
- Buka `http://localhost:8000`
- Upload CLI dump (wajib) + BBL log (opsional)
- Klik **Analyze Tuning**

---

## Instalasi Lokal

### Prasyarat
- Python 3.10+
- `blackbox_decode` (opsional, untuk analisis flight data penuh)

### Setup
```bash
# Clone repository
git clone https://github.com/itsmhp/betaflight-tuning-analyzer.git
cd betaflight-tuning-analyzer

# Install dependencies
pip install -r requirements.txt

# Jalankan
python run.py
```

Buka browser ke `http://127.0.0.1:8000`

### blackbox_decode (Opsional)
Untuk analisis FFT noise & motor dari file `.bbl`:
1. Download [blackbox-tools](https://github.com/betaflight/blackbox-tools/releases)
2. Taruh `blackbox_decode.exe` (Windows) atau `blackbox_decode` (Linux/Mac) di folder `tools/`

---

## Deployment (Render.com)

Aplikasi ini dikonfigurasi untuk langsung deploy ke [Render.com](https://render.com) via `render.yaml`.

1. Fork/push repo ini ke GitHub
2. Login ke [render.com](https://render.com) → **New > Web Service**
3. Connect GitHub repo ini
4. Render akan otomatis detect `render.yaml`
5. Deploy!

---

## Tech Stack

- **Backend:** Python, FastAPI, uvicorn
- **Templating:** Jinja2
- **Analysis:** NumPy, SciPy (FFT), Pandas
- **Charts:** Plotly.js (client-side)
- **Deployment:** Render.com

---

## Supported FC / Firmware

- ✅ Betaflight 4.3+
- ✅ Semua flight controller yang didukung Betaflight
- ✅ BBL format dari blackbox onboard dan SD card

---

Made with ❤️ for the FPV community
