"""
Betaflight default values reference.

Contains default values for Betaflight 4.5.x settings,
used as baseline for comparison and recommendation.
"""


class BetaflightDefaults:
    """Betaflight 4.5.x default configuration values."""

    # Firmware reference
    VERSION = "4.5"

    # ==================== PID Defaults ====================
    PID = {
        "p_roll": 45,
        "i_roll": 80,
        "d_roll": 40,
        "f_roll": 120,
        "p_pitch": 47,
        "i_pitch": 84,
        "d_pitch": 46,
        "f_pitch": 125,
        "p_yaw": 45,
        "i_yaw": 80,
        "d_yaw": 0,
        "f_yaw": 120,
        "d_min_roll": 30,
        "d_min_pitch": 34,
        "d_min_yaw": 0,
        "d_max_gain": 37,
        "d_max_advance": 20,
    }

    # ==================== Filter Defaults ====================
    GYRO_FILTERS = {
        "gyro_lpf1_type": "PT1",
        "gyro_lpf1_static_hz": 250,
        "gyro_lpf1_dyn_min_hz": 250,
        "gyro_lpf1_dyn_max_hz": 500,
        "gyro_lpf1_dyn_expo": 5,
        "gyro_lpf2_type": "PT1",
        "gyro_lpf2_static_hz": 500,
        "gyro_notch1_hz": 0,
        "gyro_notch1_cutoff": 0,
        "gyro_notch2_hz": 0,
        "gyro_notch2_cutoff": 0,
    }

    DYN_NOTCH = {
        "dyn_notch_count": 3,
        "dyn_notch_q": 300,
        "dyn_notch_min_hz": 150,
        "dyn_notch_max_hz": 600,
    }

    RPM_FILTER = {
        "rpm_filter_harmonics": 3,
        "rpm_filter_q": 500,
        "rpm_filter_min_hz": 100,
        "rpm_filter_fade_range_hz": 50,
        "rpm_filter_lpf_hz": 150,
    }

    DTERM_FILTERS = {
        "dterm_lpf1_type": "PT1",
        "dterm_lpf1_static_hz": 75,
        "dterm_lpf1_dyn_min_hz": 75,
        "dterm_lpf1_dyn_max_hz": 150,
        "dterm_lpf1_dyn_expo": 5,
        "dterm_lpf2_type": "PT1",
        "dterm_lpf2_static_hz": 150,
        "dterm_notch_hz": 0,
        "dterm_notch_cutoff": 0,
    }

    # ==================== Rate Defaults ====================
    RATES = {
        "rates_type": "ACTUAL",
        "roll_rc_rate": 7,
        "pitch_rc_rate": 7,
        "yaw_rc_rate": 7,
        "roll_expo": 0,
        "pitch_expo": 0,
        "yaw_expo": 0,
        "roll_srate": 67,
        "pitch_srate": 67,
        "yaw_srate": 67,
    }

    # ==================== Motor/ESC Defaults ====================
    MOTOR = {
        "motor_pwm_protocol": "DSHOT300",
        "dshot_bidir": "ON",
        "dshot_idle_value": 550,
        "motor_poles": 14,
        "min_throttle": 1070,
        "max_throttle": 2000,
    }

    # ==================== Feature Defaults ====================
    ITERM = {
        "iterm_relax": "RP",
        "iterm_relax_type": "SETPOINT",
        "iterm_relax_cutoff": 15,
        "iterm_windup": 85,
        "iterm_limit": 400,
    }

    FEEDFORWARD = {
        "feedforward_averaging": "OFF",
        "feedforward_smooth_factor": 25,
        "feedforward_jitter_factor": 7,
        "feedforward_boost": 15,
        "feedforward_max_rate_limit": 90,
    }

    TPA = {
        "tpa_mode": "D",
        "tpa_rate": 65,
        "tpa_breakpoint": 1350,
        "tpa_low_rate": 20,
        "tpa_low_breakpoint": 1050,
    }

    ANTI_GRAVITY = {
        "anti_gravity_gain": 80,
        "anti_gravity_cutoff_hz": 5,
        "anti_gravity_p_gain": 100,
    }

    RC_SMOOTHING = {
        "rc_smoothing": "ON",
        "rc_smoothing_auto_factor": 30,
        "rc_smoothing_auto_factor_throttle": 30,
    }

    THROTTLE = {
        "throttle_boost": 5,
        "throttle_boost_cutoff": 15,
    }

    DYN_IDLE = {
        "dyn_idle_min_rpm": 0,
        "dyn_idle_p_gain": 50,
        "dyn_idle_i_gain": 50,
        "dyn_idle_d_gain": 50,
        "dyn_idle_max_increase": 150,
    }

    SIMPLIFIED = {
        "simplified_pids_mode": "RPY",
        "simplified_master_multiplier": 100,
        "simplified_i_gain": 100,
        "simplified_d_gain": 100,
        "simplified_pi_gain": 100,
        "simplified_dmax_gain": 100,
        "simplified_feedforward_gain": 100,
        "simplified_pitch_d_gain": 100,
        "simplified_pitch_pi_gain": 100,
        "simplified_dterm_filter": "ON",
        "simplified_dterm_filter_multiplier": 100,
        "simplified_gyro_filter": "ON",
        "simplified_gyro_filter_multiplier": 100,
    }

    # ==================== Loop / Timing ====================
    TIMING = {
        "pid_process_denom": 2,  # 4kHz PID on 8kHz gyro
        "gyro_sync_denom": 1,
    }

    # ==================== Debug Mode Reference ====================
    DEBUG_MODES = {
        0: "NONE",
        1: "CYCLETIME",
        2: "BATTERY",
        3: "GYRO_FILTERED",
        4: "ACCELEROMETER",
        5: "PIDLOOP",
        6: "GYRO_SCALED",
        7: "RC_INTERPOLATION",
        8: "ANGLERATE",
        9: "ESC_SENSOR",
        10: "SCHEDULER",
        11: "STACK",
        12: "ESC_SENSOR_RPM",
        13: "ESC_SENSOR_TMP",
        14: "ALTITUDE",
        15: "FFT",
        16: "FFT_TIME",
        17: "FFT_FREQ",
        18: "RX_FRSKY_SPI",
        19: "RX_SFHSS_SPI",
        20: "GYRO_RAW",
        21: "DUAL_GYRO_RAW",
        22: "DUAL_GYRO_DIFF",
        23: "MAX7456_SIGNAL",
        24: "MAX7456_SPICLOCK",
        25: "SBUS",
        26: "FPORT",
        27: "RANGEFINDER",
        28: "RANGEFINDER_QUALITY",
        29: "LIDAR_TF",
        30: "ADC_INTERNAL",
        31: "RUNAWAY_TAKEOFF",
        32: "SDIO",
        33: "CURRENT_SENSOR",
        34: "USB",
        35: "SMARTAUDIO",
        36: "RTH",
        37: "ITERM_RELAX",
        38: "ACRO_TRAINER",
        39: "RC_SMOOTHING",
        40: "RX_SIGNAL_LOSS",
        41: "RC_SMOOTHING_RATE",
        42: "ANTI_GRAVITY",
        43: "DYN_LPF",
        44: "RX_SPEKTRUM_SPI",
        45: "DSHOT_RPM_TELEMETRY",
        46: "RPM_FILTER",
        47: "D_MIN",
        48: "AC_CORRECTION",
        49: "AC_ERROR",
        50: "DUAL_GYRO_SCALED",
        51: "DSHOT_RPM_ERRORS",
        52: "CRSF_LINK_STATISTICS_UPLINK",
        53: "CRSF_LINK_STATISTICS_PWR",
        54: "CRSF_LINK_STATISTICS_DOWN",
        55: "BARO",
        56: "GPS_RESCUE_THROTTLE_PID",
        57: "DYN_IDLE",
        58: "FEEDFORWARD_LIMIT",
        59: "FEEDFORWARD",
        60: "BLACKBOX_OUTPUT",
        61: "GYRO_SAMPLE",
        62: "RX_TIMING",
        63: "D_LPF",
        64: "VTX_TRAMP",
        65: "GHST",
        66: "GHST_MSP",
        67: "SCHEDULER_DETERMINISM",
        68: "TIMING_ACCURACY",
        69: "RX_EXPRESSLRS_SPI",
        70: "RX_EXPRESSLRS_PHASELOCK",
        71: "RX_STATE_TIME",
        72: "GPS_RESCUE_VELOCITY",
        73: "GPS_RESCUE_HEADING",
        74: "GPS_RESCUE_TRACKING",
        75: "GPS_CONNECTION",
        76: "ATTITUDE",
        77: "VTX_MSP",
        78: "GPS_DOP",
        79: "FAILSAFE",
        80: "GYRO_CALIBRATION",
        81: "ANGLE_MODE",
        82: "ANGLE_TARGET",
        83: "CURRENT_ANGLE",
        84: "DSHOT_TELEMETRY_COUNTS",
        85: "RPM_FILTER",
        86: "FF_LIMIT",
    }

    # Motor protocol reference
    MOTOR_PROTOCOLS = {
        0: "PWM",
        1: "ONESHOT125",
        2: "ONESHOT42",
        3: "MULTISHOT",
        4: "BRUSHED",
        5: "DSHOT150",
        6: "DSHOT300",
        7: "DSHOT600",
        8: "PROSHOT1000",
        9: "DISABLED",
    }

    # Rate type reference
    RATE_TYPES = {
        0: "BETAFLIGHT",
        1: "RACEFLIGHT",
        2: "KISS",
        3: "ACTUAL",
        4: "QUICK",
    }

    # Serialrx provider reference
    SERIALRX_PROVIDERS = {
        0: "SPEK1024",
        1: "SPEK2048",
        2: "SBUS",
        3: "SUMD",
        4: "SUMH",
        5: "XB-B",
        6: "XB-B-RJ01",
        7: "IBUS",
        8: "JETIEXBUS",
        9: "CRSF",
        10: "SRXL",
        11: "CUSTOM",
        12: "FPORT",
        13: "SRXL2",
        14: "GHST",
    }
