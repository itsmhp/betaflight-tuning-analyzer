"""
Internationalization (i18n) module.

Supported languages:
  en – English (default)
  id – Bahasa Indonesia
  es – Español
  de – Deutsch

Usage:
    from gui.i18n import t, set_lang, current_lang, LANGUAGE_OPTIONS

    set_lang("id")
    label.setText(t("analyze_btn"))
"""
from __future__ import annotations

# ── Language metadata ──────────────────────────────────────────────────────────
LANGUAGE_OPTIONS: list[tuple[str, str]] = [
    ("en", "English"),
    ("id", "Bahasa Indonesia"),
    ("es", "Español"),
    ("de", "Deutsch"),
]

_current_lang: str = "en"


def current_lang() -> str:
    return _current_lang


def set_lang(code: str) -> None:
    global _current_lang
    if code in TRANSLATIONS:
        _current_lang = code


def t(key: str) -> str:
    """Return translated string for *key* in the current language."""
    lang_dict = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"])
    # fall back to English if key missing in target language
    return lang_dict.get(key, TRANSLATIONS["en"].get(key, key))


# ── Translation tables ─────────────────────────────────────────────────────────
TRANSLATIONS: dict[str, dict[str, str]] = {

    # ──────────────────────────────────────────────────────────────────────────
    "en": {
        # Window / app
        "app_title":            "Betaflight Tuning Analyzer",
        "app_subtitle":         "Upload your CLI dump and optional blackbox log for comprehensive tuning analysis.",
        "language_label":       "Language",
        "window_title":         "Betaflight Tuning Analyzer",

        # File section
        "files_group":          "Flight Data Files",
        "cli_section":          "CLI Dump File",
        "cli_required":         "(required)",
        "cli_hint":             "Betaflight CLI 'dump all' output (.txt / .log / .cli)",
        "cli_btn":              "  Click to select CLI dump file…",
        "bbl_section":          "Blackbox Log File",
        "bbl_optional":         "(optional)",
        "bbl_hint":             "Blackbox flight log (.bbl / .bfl / .csv)",
        "bbl_btn":              "  Click to select BBL file (optional)…",
        "bbl_clear":            "✕ Clear BBL",
        "cli_missing_error":    "  Please select a CLI dump file first.",

        # Quad profile
        "profile_group":        "Quad Profile  (optional – improves recommendations)",
        "frame_size_lbl":       "Frame Size",
        "prop_size_lbl":        "Prop Size",
        "prop_size_placeholder": "e.g. 5045, 3018, 51303",
        "battery_lbl":          "Battery (S count)",
        "motor_kv_lbl":         "Motor KV",
        "weight_lbl":           "AUW Weight (g)",
        "fc_lbl":               "FC Board",
        "fc_placeholder":       "e.g. SpeedyBee F405 V4",
        "esc_lbl":              "ESC",
        "esc_placeholder":      "e.g. BLHeli_32 55A 4in1",
        "style_lbl":            "Flying Style",

        # Frame size options
        "frame_65mm":           "65mm (Tiny Whoop)",
        "frame_75mm":           "75mm (Whoop)",
        "frame_3inch":          "3\" Micro / Toothpick",
        "frame_3inch_cw":       "3\" CineWhoop",
        "frame_4inch":          "4\" Micro",
        "frame_5inch":          "5\" Freestyle",
        "frame_5inch_race":     "5\" Race",
        "frame_6inch":          "6\" Long Range",
        "frame_7inch":          "7\" Long Range",
        "frame_8inch":          "8\"+ X-Class",

        # Battery options
        "battery_unknown":      "0 – Unknown",

        # Flying style options
        "style_freestyle":      "Freestyle",
        "style_cinematic":      "Cinematic / Smooth",
        "style_racing":         "Racing",
        "style_longrange":      "Long Range / Cruise",

        # Presets
        "preset_group":         "Tuning Preset  (optional)",
        "preset_desc":          "Choose a tuning aggression level. The analyzer will compare your tune against the preset.",
        "preset_none":          "None",
        "preset_none_tip":      "Analyze only – no preset comparison",
        "preset_low":           "Low",
        "preset_low_tip":       "Smooth & gentle. Great for cinematic.",
        "preset_medium":        "Medium",
        "preset_medium_tip":    "Balanced for everyday freestyle.",
        "preset_high":          "High",
        "preset_high_tip":      "Aggressive, snappy. Motors run warmer.",
        "preset_ultra":         "Ultra",
        "preset_ultra_tip":     "Maximum authority. Racing builds only.",

        # Analyze button
        "analyze_btn":          "  Analyze Tuning",

        # Loading page
        "loading_title":        "Analyzing…",
        "loading_sub":          "Parsing CLI dump and running analysis pipeline…",
        "loading_hint":         "This may take a few seconds for large blackbox files.",

        # Results page
        "results_title":        "Analysis Results",
        "results_unknown_craft": "Unknown Craft",
        "results_errors":       "{n} Errors",
        "results_warnings":     "{n} Warnings",
        "results_info":         "{n} Info",
        "results_total":        "{n} Total",
        "tab_overview":         "Overview",
        "tab_cli":              "CLI Commands",
        "tab_charts":           "Charts",
        "back_btn":             "← Analyze Another File",

        # Overview tab
        "overview_issues":      "Issues Requiring Attention",
        "overview_warnings":    "Warnings ({n})",
        "no_findings":          "No findings in this category.",

        # CLI tab
        "cli_tab_title":        "Ready-to-Paste CLI Commands",
        "cli_copy_all":         "Copy All",
        "cli_changes":          "{n} changes",
        "cli_empty":            "# No CLI commands generated.",
        "cli_paste_hint":       "Paste this entire block into the Betaflight CLI tab, then type 'save'.",

        # Charts tab
        "charts_empty":         "No chart data available. Upload a blackbox log for flight charts.",

        # Config summary
        "config_summary":       "Configuration Summary",
        "config_board":         "Board",
        "config_firmware":      "Firmware",
        "config_craft":         "Craft",
        "config_pid_profile":   "PID Profile",
        "config_rate_profile":  "Rate Profile",

        # Copy button
        "copy_btn":             "Copy",

        # Error dialog
        "error_title":          "Analysis Error",
        "error_text":           "Analysis failed:",
    },

    # ──────────────────────────────────────────────────────────────────────────
    "id": {
        # Window / app
        "app_title":            "Betaflight Tuning Analyzer",
        "app_subtitle":         "Unggah file CLI dump dan log blackbox untuk analisis tuning yang komprehensif.",
        "language_label":       "Bahasa",
        "window_title":         "Betaflight Tuning Analyzer",

        # File section
        "files_group":          "File Data Penerbangan",
        "cli_section":          "File CLI Dump",
        "cli_required":         "(wajib)",
        "cli_hint":             "Output CLI Betaflight 'dump all' (.txt / .log / .cli)",
        "cli_btn":              "  Klik untuk memilih file CLI dump…",
        "bbl_section":          "File Log Blackbox",
        "bbl_optional":         "(opsional)",
        "bbl_hint":             "Log penerbangan blackbox (.bbl / .bfl / .csv)",
        "bbl_btn":              "  Klik untuk memilih file BBL (opsional)…",
        "bbl_clear":            "✕ Hapus BBL",
        "cli_missing_error":    "  Pilih file CLI dump terlebih dahulu.",

        # Quad profile
        "profile_group":        "Profil Quad  (opsional – meningkatkan rekomendasi)",
        "frame_size_lbl":       "Ukuran Frame",
        "prop_size_lbl":        "Ukuran Propeller",
        "prop_size_placeholder": "mis. 5045, 3018, 51303",
        "battery_lbl":          "Baterai (jumlah S)",
        "motor_kv_lbl":         "Motor KV",
        "weight_lbl":           "Berat AUW (g)",
        "fc_lbl":               "FC Board",
        "fc_placeholder":       "mis. SpeedyBee F405 V4",
        "esc_lbl":              "ESC",
        "esc_placeholder":      "mis. BLHeli_32 55A 4in1",
        "style_lbl":            "Gaya Terbang",

        # Frame size options
        "frame_65mm":           "65mm (Tiny Whoop)",
        "frame_75mm":           "75mm (Whoop)",
        "frame_3inch":          "3\" Mikro / Toothpick",
        "frame_3inch_cw":       "3\" CineWhoop",
        "frame_4inch":          "4\" Mikro",
        "frame_5inch":          "5\" Freestyle",
        "frame_5inch_race":     "5\" Balap",
        "frame_6inch":          "6\" Jarak Jauh",
        "frame_7inch":          "7\" Jarak Jauh",
        "frame_8inch":          "8\"+ X-Class",

        # Battery options
        "battery_unknown":      "0 – Tidak Diketahui",

        # Flying style options
        "style_freestyle":      "Freestyle",
        "style_cinematic":      "Sinematik / Halus",
        "style_racing":         "Balap",
        "style_longrange":      "Jarak Jauh / Cruise",

        # Presets
        "preset_group":         "Preset Tuning  (opsional)",
        "preset_desc":          "Pilih tingkat agresivitas tuning. Analyzer akan membandingkan tune Anda dengan preset.",
        "preset_none":          "Tidak Ada",
        "preset_none_tip":      "Hanya analisis – tanpa perbandingan preset",
        "preset_low":           "Rendah",
        "preset_low_tip":       "Halus & lembut. Cocok untuk sinematik.",
        "preset_medium":        "Sedang",
        "preset_medium_tip":    "Seimbang untuk freestyle sehari-hari.",
        "preset_high":          "Tinggi",
        "preset_high_tip":      "Agresif, responsif. Motor lebih panas.",
        "preset_ultra":         "Ultra",
        "preset_ultra_tip":     "Otoritas maksimum. Khusus untuk balap.",

        # Analyze button
        "analyze_btn":          "  Analisis Tuning",

        # Loading page
        "loading_title":        "Menganalisis…",
        "loading_sub":          "Memproses CLI dump dan menjalankan pipeline analisis…",
        "loading_hint":         "Ini mungkin memerlukan beberapa detik untuk file blackbox yang besar.",

        # Results page
        "results_title":        "Hasil Analisis",
        "results_unknown_craft": "Quad Tidak Diketahui",
        "results_errors":       "{n} Error",
        "results_warnings":     "{n} Peringatan",
        "results_info":         "{n} Info",
        "results_total":        "{n} Total",
        "tab_overview":         "Ringkasan",
        "tab_cli":              "Perintah CLI",
        "tab_charts":           "Grafik",
        "back_btn":             "← Analisis File Lain",

        # Overview tab
        "overview_issues":      "Masalah yang Perlu Diperhatikan",
        "overview_warnings":    "Peringatan ({n})",
        "no_findings":          "Tidak ada temuan dalam kategori ini.",

        # CLI tab
        "cli_tab_title":        "Perintah CLI Siap Tempel",
        "cli_copy_all":         "Salin Semua",
        "cli_changes":          "{n} perubahan",
        "cli_empty":            "# Tidak ada perintah CLI yang dihasilkan.",
        "cli_paste_hint":       "Tempel seluruh blok ini ke tab CLI Betaflight, lalu ketik 'save'.",

        # Charts tab
        "charts_empty":         "Tidak ada data grafik. Unggah log blackbox untuk grafik penerbangan.",

        # Config summary
        "config_summary":       "Ringkasan Konfigurasi",
        "config_board":         "Board",
        "config_firmware":      "Firmware",
        "config_craft":         "Nama Quad",
        "config_pid_profile":   "Profil PID",
        "config_rate_profile":  "Profil Rate",

        # Copy button
        "copy_btn":             "Salin",

        # Error dialog
        "error_title":          "Error Analisis",
        "error_text":           "Analisis gagal:",
    },

    # ──────────────────────────────────────────────────────────────────────────
    "es": {
        # Window / app
        "app_title":            "Betaflight Tuning Analyzer",
        "app_subtitle":         "Sube tu CLI dump y el log de blackbox para un análisis completo del tuning.",
        "language_label":       "Idioma",
        "window_title":         "Betaflight Tuning Analyzer",

        # File section
        "files_group":          "Archivos de Datos de Vuelo",
        "cli_section":          "Archivo CLI Dump",
        "cli_required":         "(requerido)",
        "cli_hint":             "Salida del CLI de Betaflight 'dump all' (.txt / .log / .cli)",
        "cli_btn":              "  Haz clic para seleccionar archivo CLI dump…",
        "bbl_section":          "Archivo Log Blackbox",
        "bbl_optional":         "(opcional)",
        "bbl_hint":             "Log de vuelo blackbox (.bbl / .bfl / .csv)",
        "bbl_btn":              "  Haz clic para seleccionar archivo BBL (opcional)…",
        "bbl_clear":            "✕ Quitar BBL",
        "cli_missing_error":    "  Selecciona un archivo CLI dump primero.",

        # Quad profile
        "profile_group":        "Perfil del Quad  (opcional – mejora las recomendaciones)",
        "frame_size_lbl":       "Tamaño del Frame",
        "prop_size_lbl":        "Tamaño de Hélice",
        "prop_size_placeholder": "ej. 5045, 3018, 51303",
        "battery_lbl":          "Batería (celdas S)",
        "motor_kv_lbl":         "Motor KV",
        "weight_lbl":           "Peso AUW (g)",
        "fc_lbl":               "Placa FC",
        "fc_placeholder":       "ej. SpeedyBee F405 V4",
        "esc_lbl":              "ESC",
        "esc_placeholder":      "ej. BLHeli_32 55A 4in1",
        "style_lbl":            "Estilo de Vuelo",

        # Frame size options
        "frame_65mm":           "65mm (Tiny Whoop)",
        "frame_75mm":           "75mm (Whoop)",
        "frame_3inch":          "3\" Micro / Toothpick",
        "frame_3inch_cw":       "3\" CineWhoop",
        "frame_4inch":          "4\" Micro",
        "frame_5inch":          "5\" Freestyle",
        "frame_5inch_race":     "5\" Carreras",
        "frame_6inch":          "6\" Largo Alcance",
        "frame_7inch":          "7\" Largo Alcance",
        "frame_8inch":          "8\"+ X-Class",

        # Battery options
        "battery_unknown":      "0 – Desconocido",

        # Flying style options
        "style_freestyle":      "Freestyle",
        "style_cinematic":      "Cinematográfico / Suave",
        "style_racing":         "Carreras",
        "style_longrange":      "Largo Alcance / Crucero",

        # Presets
        "preset_group":         "Preset de Tuning  (opcional)",
        "preset_desc":          "Elige un nivel de agresividad. El analizador comparará tu tune con el preset.",
        "preset_none":          "Ninguno",
        "preset_none_tip":      "Solo análisis – sin comparación de preset",
        "preset_low":           "Bajo",
        "preset_low_tip":       "Suave y gentil. Ideal para cinematografía.",
        "preset_medium":        "Medio",
        "preset_medium_tip":    "Equilibrado para freestyle cotidiano.",
        "preset_high":          "Alto",
        "preset_high_tip":      "Agresivo y veloz. Los motores se calientan más.",
        "preset_ultra":         "Ultra",
        "preset_ultra_tip":     "Máxima autoridad. Solo para builds de carreras.",

        # Analyze button
        "analyze_btn":          "  Analizar Tuning",

        # Loading page
        "loading_title":        "Analizando…",
        "loading_sub":          "Procesando CLI dump y ejecutando el pipeline de análisis…",
        "loading_hint":         "Esto puede tardar unos segundos para archivos blackbox grandes.",

        # Results page
        "results_title":        "Resultados del Análisis",
        "results_unknown_craft": "Quad Desconocido",
        "results_errors":       "{n} Errores",
        "results_warnings":     "{n} Advertencias",
        "results_info":         "{n} Info",
        "results_total":        "{n} Total",
        "tab_overview":         "Resumen",
        "tab_cli":              "Comandos CLI",
        "tab_charts":           "Gráficos",
        "back_btn":             "← Analizar Otro Archivo",

        # Overview tab
        "overview_issues":      "Problemas que Requieren Atención",
        "overview_warnings":    "Advertencias ({n})",
        "no_findings":          "No hay hallazgos en esta categoría.",

        # CLI tab
        "cli_tab_title":        "Comandos CLI Listos para Pegar",
        "cli_copy_all":         "Copiar Todo",
        "cli_changes":          "{n} cambios",
        "cli_empty":            "# No se generaron comandos CLI.",
        "cli_paste_hint":       "Pega todo este bloque en la pestaña CLI de Betaflight y escribe 'save'.",

        # Charts tab
        "charts_empty":         "No hay datos de gráficos. Sube un log blackbox para ver gráficos de vuelo.",

        # Config summary
        "config_summary":       "Resumen de Configuración",
        "config_board":         "Placa",
        "config_firmware":      "Firmware",
        "config_craft":         "Nombre del Quad",
        "config_pid_profile":   "Perfil PID",
        "config_rate_profile":  "Perfil de Rates",

        # Copy button
        "copy_btn":             "Copiar",

        # Error dialog
        "error_title":          "Error de Análisis",
        "error_text":           "El análisis falló:",
    },

    # ──────────────────────────────────────────────────────────────────────────
    "de": {
        # Window / app
        "app_title":            "Betaflight Tuning Analyzer",
        "app_subtitle":         "Lade deinen CLI-Dump und optionalen Blackbox-Log für eine umfassende Tuning-Analyse.",
        "language_label":       "Sprache",
        "window_title":         "Betaflight Tuning Analyzer",

        # File section
        "files_group":          "Flugdatendateien",
        "cli_section":          "CLI-Dump-Datei",
        "cli_required":         "(erforderlich)",
        "cli_hint":             "Betaflight CLI 'dump all' Ausgabe (.txt / .log / .cli)",
        "cli_btn":              "  Klicken um CLI-Dump-Datei auszuwählen…",
        "bbl_section":          "Blackbox-Log-Datei",
        "bbl_optional":         "(optional)",
        "bbl_hint":             "Blackbox-Flugprotokoll (.bbl / .bfl / .csv)",
        "bbl_btn":              "  Klicken um BBL-Datei auszuwählen (optional)…",
        "bbl_clear":            "✕ BBL entfernen",
        "cli_missing_error":    "  Bitte erst eine CLI-Dump-Datei auswählen.",

        # Quad profile
        "profile_group":        "Quad-Profil  (optional – verbessert Empfehlungen)",
        "frame_size_lbl":       "Rahmengröße",
        "prop_size_lbl":        "Propellergröße",
        "prop_size_placeholder": "z.B. 5045, 3018, 51303",
        "battery_lbl":          "Akku (S-Anzahl)",
        "motor_kv_lbl":         "Motor KV",
        "weight_lbl":           "Fluggewicht AUW (g)",
        "fc_lbl":               "FC-Board",
        "fc_placeholder":       "z.B. SpeedyBee F405 V4",
        "esc_lbl":              "ESC",
        "esc_placeholder":      "z.B. BLHeli_32 55A 4in1",
        "style_lbl":            "Flugstil",

        # Frame size options
        "frame_65mm":           "65mm (Tiny Whoop)",
        "frame_75mm":           "75mm (Whoop)",
        "frame_3inch":          "3\" Mikro / Toothpick",
        "frame_3inch_cw":       "3\" CineWhoop",
        "frame_4inch":          "4\" Mikro",
        "frame_5inch":          "5\" Freestyle",
        "frame_5inch_race":     "5\" Rennen",
        "frame_6inch":          "6\" Langstrecke",
        "frame_7inch":          "7\" Langstrecke",
        "frame_8inch":          "8\"+ X-Class",

        # Battery options
        "battery_unknown":      "0 – Unbekannt",

        # Flying style options
        "style_freestyle":      "Freestyle",
        "style_cinematic":      "Kinematisch / Sanft",
        "style_racing":         "Rennen",
        "style_longrange":      "Langstrecke / Cruise",

        # Presets
        "preset_group":         "Tuning-Preset  (optional)",
        "preset_desc":          "Wähle eine Aggressivitätsstufe. Der Analyzer vergleicht dein Tuning mit dem Preset.",
        "preset_none":          "Keins",
        "preset_none_tip":      "Nur Analyse – kein Preset-Vergleich",
        "preset_low":           "Niedrig",
        "preset_low_tip":       "Sanft & weich. Ideal für cinematisch.",
        "preset_medium":        "Mittel",
        "preset_medium_tip":    "Ausgewogen für alltäglichen Freestyle.",
        "preset_high":          "Hoch",
        "preset_high_tip":      "Aggressiv & reaktionsschnell. Motoren werden wärmer.",
        "preset_ultra":         "Ultra",
        "preset_ultra_tip":     "Maximale Kontrolle. Nur für Renn-Builds.",

        # Analyze button
        "analyze_btn":          "  Tuning analysieren",

        # Loading page
        "loading_title":        "Analysiere…",
        "loading_sub":          "Verarbeite CLI-Dump und führe Analyse-Pipeline aus…",
        "loading_hint":         "Das kann bei großen Blackbox-Dateien einige Sekunden dauern.",

        # Results page
        "results_title":        "Analyseergebnisse",
        "results_unknown_craft": "Unbekannter Quad",
        "results_errors":       "{n} Fehler",
        "results_warnings":     "{n} Warnungen",
        "results_info":         "{n} Info",
        "results_total":        "{n} Gesamt",
        "tab_overview":         "Übersicht",
        "tab_cli":              "CLI-Befehle",
        "tab_charts":           "Diagramme",
        "back_btn":             "← Andere Datei analysieren",

        # Overview tab
        "overview_issues":      "Probleme, die Aufmerksamkeit erfordern",
        "overview_warnings":    "Warnungen ({n})",
        "no_findings":          "Keine Befunde in dieser Kategorie.",

        # CLI tab
        "cli_tab_title":        "Einfügefertige CLI-Befehle",
        "cli_copy_all":         "Alles kopieren",
        "cli_changes":          "{n} Änderungen",
        "cli_empty":            "# Keine CLI-Befehle generiert.",
        "cli_paste_hint":       "Füge diesen gesamten Block in den Betaflight CLI-Tab ein und tippe dann 'save'.",

        # Charts tab
        "charts_empty":         "Keine Diagrammdaten. Lade ein Blackbox-Log für Flugdiagramme.",

        # Config summary
        "config_summary":       "Konfigurationsübersicht",
        "config_board":         "Board",
        "config_firmware":      "Firmware",
        "config_craft":         "Quad-Name",
        "config_pid_profile":   "PID-Profil",
        "config_rate_profile":  "Rate-Profil",

        # Copy button
        "copy_btn":             "Kopieren",

        # Error dialog
        "error_title":          "Analysefehler",
        "error_text":           "Analyse fehlgeschlagen:",
    },
}
