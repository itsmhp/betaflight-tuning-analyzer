"""
Betaflight Blackbox Log Header Parser.

Parses the ASCII header section of .bbl files which contains
flight configuration metadata (same info as CLI dump but captured at flight time).
"""
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class BBLHeaderData:
    """Parsed blackbox log header data."""
    # Firmware
    firmware_type: str = ""
    firmware_revision: str = ""
    firmware_date: str = ""
    board_info: str = ""
    craft_name: str = ""
    log_start_datetime: str = ""

    # Data structure
    field_i_names: List[str] = field(default_factory=list)
    field_s_names: List[str] = field(default_factory=list)

    # Loop timing
    looptime: int = 0  # microseconds
    gyro_sync_denom: int = 1
    pid_process_denom: int = 2
    i_interval: int = 1
    p_interval: int = 1
    p_ratio: int = 1

    # PID
    roll_pid: Tuple[int, int, int] = (0, 0, 0)  # P, I, D
    pitch_pid: Tuple[int, int, int] = (0, 0, 0)
    yaw_pid: Tuple[int, int, int] = (0, 0, 0)
    d_min: Tuple[int, int, int] = (0, 0, 0)  # roll, pitch, yaw
    d_max_gain: int = 0
    d_max_advance: int = 0

    # Rates
    rates_type: int = 0  # 0=BF, 1=raceflight, 2=KISS, 3=ACTUAL, 4=Quick
    rc_rates: Tuple[int, int, int] = (0, 0, 0)
    rc_expo: Tuple[int, int, int] = (0, 0, 0)
    rates: Tuple[int, int, int] = (0, 0, 0)
    rate_limits: Tuple[int, int, int] = (1998, 1998, 1998)

    # Throttle
    minthrottle: int = 1000
    maxthrottle: int = 2000
    thr_mid: int = 50
    thr_expo: int = 0
    tpa_mode: int = 0
    tpa_rate: int = 0
    tpa_breakpoint: int = 0
    tpa_low_rate: int = 0
    tpa_low_breakpoint: int = 0

    # Filters - Gyro
    gyro_lpf1_type: int = 0
    gyro_lpf1_static_hz: int = 0
    gyro_lpf1_dyn_hz: Tuple[int, int] = (0, 0)
    gyro_lpf1_dyn_expo: int = 5
    gyro_lpf2_type: int = 0
    gyro_lpf2_static_hz: int = 0
    gyro_notch_hz: Tuple[int, int] = (0, 0)
    gyro_notch_cutoff: Tuple[int, int] = (0, 0)
    dyn_notch_count: int = 3
    dyn_notch_q: int = 300
    dyn_notch_min_hz: int = 150
    dyn_notch_max_hz: int = 600

    # Filters - Dterm
    dterm_lpf1_type: int = 0
    dterm_lpf1_static_hz: int = 0
    dterm_lpf1_dyn_hz: Tuple[int, int] = (0, 0)
    dterm_lpf1_dyn_expo: int = 5
    dterm_lpf2_type: int = 0
    dterm_lpf2_static_hz: int = 0
    dterm_notch_hz: int = 0
    dterm_notch_cutoff: int = 0
    yaw_lowpass_hz: int = 0

    # RPM filter
    dshot_bidir: int = 0
    motor_poles: int = 12
    rpm_filter_harmonics: int = 3
    rpm_filter_weights: Tuple[int, int, int] = (100, 100, 100)
    rpm_filter_q: int = 500
    rpm_filter_min_hz: int = 100
    rpm_filter_fade_range_hz: int = 50
    rpm_filter_lpf_hz: int = 150

    # Motor / ESC
    motor_output: Tuple[int, int] = (0, 0)
    motor_pwm_protocol: int = 0
    dshot_idle_value: int = 550
    motor_output_limit: int = 100

    # I-term
    iterm_relax: int = 0
    iterm_relax_type: int = 0
    iterm_relax_cutoff: int = 15
    iterm_windup: int = 85

    # Anti-gravity
    anti_gravity_gain: int = 80
    anti_gravity_cutoff_hz: int = 5
    anti_gravity_p_gain: int = 100

    # Feedforward
    feedforward_averaging: int = 0
    feedforward_smooth_factor: int = 25
    feedforward_jitter_factor: int = 7
    feedforward_boost: int = 15
    feedforward_max_rate_limit: int = 90

    # RC smoothing
    rc_smoothing: int = 1
    rc_smoothing_auto_factor: int = 30
    rc_smoothing_active_cutoffs_ff_sp_thr: Tuple[int, int, int] = (0, 0, 0)

    # Calibration
    acc_1G: int = 2048
    gyro_scale: str = ""
    vbat_scale: int = 0
    vbatcellvoltage: Tuple[int, int, int] = (0, 0, 0)

    # Simplified tuning
    simplified_pids_mode: int = 0
    simplified_master_multiplier: int = 100
    simplified_i_gain: int = 100
    simplified_d_gain: int = 100
    simplified_pi_gain: int = 100
    simplified_dmax_gain: int = 100
    simplified_feedforward_gain: int = 0
    simplified_pitch_d_gain: int = 100
    simplified_pitch_pi_gain: int = 100
    simplified_dterm_filter: int = 1
    simplified_dterm_filter_multiplier: int = 100
    simplified_gyro_filter: int = 1
    simplified_gyro_filter_multiplier: int = 100

    # Dynamic idle
    dyn_idle_min_rpm: int = 0
    dyn_idle_p_gain: int = 50
    dyn_idle_i_gain: int = 50
    dyn_idle_d_gain: int = 50

    # Debug
    debug_mode: int = 0
    features: int = 0
    serialrx_provider: int = 0

    # Vbat sag
    vbat_sag_compensation: int = 0

    # Throttle
    throttle_boost: int = 5
    throttle_boost_cutoff: int = 15

    # Other
    airmode_activate_throttle: int = 25

    # Raw header dict
    raw_headers: Dict[str, str] = field(default_factory=dict)


class BBLHeaderParser:
    """Parse the ASCII header from a Betaflight blackbox log file."""

    def parse(self, bbl_content: bytes) -> BBLHeaderData:
        """
        Parse BBL file content (bytes) and extract header data.
        Only reads the ASCII header lines (starting with 'H ').
        """
        data = BBLHeaderData()
        # Read header lines (ASCII portion at the start)
        header_lines = self._extract_header_lines(bbl_content)

        for line in header_lines:
            self._parse_header_line(line, data)

        return data

    def parse_from_text(self, header_text: str) -> BBLHeaderData:
        """Parse from already-extracted header text."""
        data = BBLHeaderData()
        for line in header_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("H "):
                self._parse_header_line(line, data)
        return data

    def _extract_header_lines(self, content: bytes) -> List[str]:
        """Extract all header lines from binary BBL content."""
        lines = []
        try:
            # Try to decode as ASCII/UTF-8, line by line
            text_portion = b""
            for byte in content:
                if byte == ord("\n"):
                    try:
                        line = text_portion.decode("ascii", errors="ignore").strip()
                        if line.startswith("H "):
                            lines.append(line)
                        elif lines and not line.startswith("H "):
                            # We've passed the header section
                            # But check for additional headers after data frames
                            pass
                        text_portion = b""
                    except Exception:
                        text_portion = b""
                else:
                    text_portion += bytes([byte])
        except Exception:
            pass

        # Alternative: split by lines
        if not lines:
            try:
                text = content.decode("ascii", errors="ignore")
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("H "):
                        lines.append(line)
            except Exception:
                pass

        return lines

    def _parse_header_line(self, line: str, data: BBLHeaderData):
        """Parse a single header line like 'H key:value'."""
        if not line.startswith("H "):
            return

        content = line[2:]  # Remove 'H '
        colon_idx = content.find(":")
        if colon_idx == -1:
            return

        key = content[:colon_idx].strip()
        value = content[colon_idx + 1:].strip()

        # Store raw
        data.raw_headers[key] = value

        # Parse specific fields
        try:
            self._apply_header(key, value, data)
        except (ValueError, IndexError):
            pass

    def _apply_header(self, key: str, value: str, data: BBLHeaderData):
        """Apply a header key-value pair to the data structure."""
        # String fields
        if key == "Firmware type":
            data.firmware_type = value
        elif key == "Firmware revision":
            data.firmware_revision = value
        elif key == "Firmware date":
            data.firmware_date = value
        elif key == "Board information":
            data.board_info = value
        elif key == "Craft name":
            data.craft_name = value
        elif key == "Log start datetime":
            data.log_start_datetime = value

        # Data fields
        elif key == "Field I name":
            data.field_i_names = value.split(",")
        elif key == "Field S name":
            data.field_s_names = value.split(",")

        # Timing
        elif key == "looptime":
            data.looptime = int(value)
        elif key == "gyro_sync_denom":
            data.gyro_sync_denom = int(value)
        elif key == "pid_process_denom":
            data.pid_process_denom = int(value)
        elif key == "I interval":
            data.i_interval = int(value)
        elif key == "P interval":
            data.p_interval = int(value)
        elif key == "P ratio":
            data.p_ratio = int(value)

        # PID
        elif key == "rollPID":
            parts = [int(x) for x in value.split(",")]
            data.roll_pid = tuple(parts[:3])
        elif key == "pitchPID":
            parts = [int(x) for x in value.split(",")]
            data.pitch_pid = tuple(parts[:3])
        elif key == "yawPID":
            parts = [int(x) for x in value.split(",")]
            data.yaw_pid = tuple(parts[:3])
        elif key == "d_min":
            parts = [int(x) for x in value.split(",")]
            data.d_min = tuple(parts[:3])
        elif key == "d_max_gain":
            data.d_max_gain = int(value)
        elif key == "d_max_advance":
            data.d_max_advance = int(value)

        # Rates
        elif key == "rates_type":
            data.rates_type = int(value)
        elif key == "rc_rates":
            parts = [int(x) for x in value.split(",")]
            data.rc_rates = tuple(parts[:3])
        elif key == "rc_expo":
            parts = [int(x) for x in value.split(",")]
            data.rc_expo = tuple(parts[:3])
        elif key == "rates":
            parts = [int(x) for x in value.split(",")]
            data.rates = tuple(parts[:3])
        elif key == "rate_limits":
            parts = [int(x) for x in value.split(",")]
            data.rate_limits = tuple(parts[:3])

        # Throttle
        elif key == "minthrottle":
            data.minthrottle = int(value)
        elif key == "maxthrottle":
            data.maxthrottle = int(value)
        elif key == "thr_mid":
            data.thr_mid = int(value)
        elif key == "thr_expo":
            data.thr_expo = int(value)
        elif key == "tpa_mode":
            data.tpa_mode = int(value)
        elif key == "tpa_rate":
            data.tpa_rate = int(value)
        elif key == "tpa_breakpoint":
            data.tpa_breakpoint = int(value)
        elif key == "tpa_low_rate":
            data.tpa_low_rate = int(value)
        elif key == "tpa_low_breakpoint":
            data.tpa_low_breakpoint = int(value)

        # Gyro filters
        elif key == "gyro_lpf1_type":
            data.gyro_lpf1_type = int(value)
        elif key == "gyro_lpf1_static_hz":
            data.gyro_lpf1_static_hz = int(value)
        elif key == "gyro_lpf1_dyn_hz":
            parts = [int(x) for x in value.split(",")]
            data.gyro_lpf1_dyn_hz = tuple(parts[:2])
        elif key == "gyro_lpf1_dyn_expo":
            data.gyro_lpf1_dyn_expo = int(value)
        elif key == "gyro_lpf2_type":
            data.gyro_lpf2_type = int(value)
        elif key == "gyro_lpf2_static_hz":
            data.gyro_lpf2_static_hz = int(value)
        elif key == "gyro_notch_hz":
            parts = [int(x) for x in value.split(",")]
            data.gyro_notch_hz = tuple(parts[:2])
        elif key == "gyro_notch_cutoff":
            parts = [int(x) for x in value.split(",")]
            data.gyro_notch_cutoff = tuple(parts[:2])
        elif key == "dyn_notch_count":
            data.dyn_notch_count = int(value)
        elif key == "dyn_notch_q":
            data.dyn_notch_q = int(value)
        elif key == "dyn_notch_min_hz":
            data.dyn_notch_min_hz = int(value)
        elif key == "dyn_notch_max_hz":
            data.dyn_notch_max_hz = int(value)

        # Dterm filters
        elif key == "dterm_lpf1_type":
            data.dterm_lpf1_type = int(value)
        elif key == "dterm_lpf1_static_hz":
            data.dterm_lpf1_static_hz = int(value)
        elif key == "dterm_lpf1_dyn_hz":
            parts = [int(x) for x in value.split(",")]
            data.dterm_lpf1_dyn_hz = tuple(parts[:2])
        elif key == "dterm_lpf1_dyn_expo":
            data.dterm_lpf1_dyn_expo = int(value)
        elif key == "dterm_lpf2_type":
            data.dterm_lpf2_type = int(value)
        elif key == "dterm_lpf2_static_hz":
            data.dterm_lpf2_static_hz = int(value)
        elif key == "dterm_notch_hz":
            data.dterm_notch_hz = int(value)
        elif key == "dterm_notch_cutoff":
            data.dterm_notch_cutoff = int(value)
        elif key == "yaw_lowpass_hz":
            data.yaw_lowpass_hz = int(value)

        # RPM filter
        elif key == "dshot_bidir":
            data.dshot_bidir = int(value)
        elif key == "motor_poles":
            data.motor_poles = int(value)
        elif key == "rpm_filter_harmonics":
            data.rpm_filter_harmonics = int(value)
        elif key == "rpm_filter_weights":
            parts = [int(x) for x in value.split(",")]
            data.rpm_filter_weights = tuple(parts[:3])
        elif key == "rpm_filter_q":
            data.rpm_filter_q = int(value)
        elif key == "rpm_filter_min_hz":
            data.rpm_filter_min_hz = int(value)
        elif key == "rpm_filter_fade_range_hz":
            data.rpm_filter_fade_range_hz = int(value)
        elif key == "rpm_filter_lpf_hz":
            data.rpm_filter_lpf_hz = int(value)

        # Motor
        elif key == "motorOutput":
            parts = [int(x) for x in value.split(",")]
            data.motor_output = tuple(parts[:2])
        elif key == "motor_pwm_protocol":
            data.motor_pwm_protocol = int(value)
        elif key == "dshot_idle_value":
            data.dshot_idle_value = int(value)
        elif key == "motor_output_limit":
            data.motor_output_limit = int(value)

        # I-term
        elif key == "iterm_relax":
            data.iterm_relax = int(value)
        elif key == "iterm_relax_type":
            data.iterm_relax_type = int(value)
        elif key == "iterm_relax_cutoff":
            data.iterm_relax_cutoff = int(value)
        elif key == "iterm_windup":
            data.iterm_windup = int(value)

        # Anti-gravity
        elif key == "anti_gravity_gain":
            data.anti_gravity_gain = int(value)
        elif key == "anti_gravity_cutoff_hz":
            data.anti_gravity_cutoff_hz = int(value)
        elif key == "anti_gravity_p_gain":
            data.anti_gravity_p_gain = int(value)

        # Feedforward
        elif key == "feedforward_averaging":
            data.feedforward_averaging = int(value)
        elif key == "feedforward_smooth_factor":
            data.feedforward_smooth_factor = int(value)
        elif key == "feedforward_jitter_factor":
            data.feedforward_jitter_factor = int(value)
        elif key == "feedforward_boost":
            data.feedforward_boost = int(value)
        elif key == "feedforward_max_rate_limit":
            data.feedforward_max_rate_limit = int(value)

        # RC smoothing
        elif key == "rc_smoothing":
            data.rc_smoothing = int(value)
        elif key == "rc_smoothing_auto_factor":
            data.rc_smoothing_auto_factor = int(value)
        elif key == "rc_smoothing_active_cutoffs_ff_sp_thr":
            parts = [int(x) for x in value.split(",")]
            data.rc_smoothing_active_cutoffs_ff_sp_thr = tuple(parts[:3])

        # Calibration
        elif key == "acc_1G":
            data.acc_1G = int(value)
        elif key == "gyro_scale":
            data.gyro_scale = value
        elif key == "vbat_scale":
            data.vbat_scale = int(value)
        elif key == "vbatcellvoltage":
            parts = [int(x) for x in value.split(",")]
            data.vbatcellvoltage = tuple(parts[:3])

        # Simplified tuning
        elif key == "simplified_pids_mode":
            data.simplified_pids_mode = int(value)
        elif key == "simplified_master_multiplier":
            data.simplified_master_multiplier = int(value)
        elif key == "simplified_i_gain":
            data.simplified_i_gain = int(value)
        elif key == "simplified_d_gain":
            data.simplified_d_gain = int(value)
        elif key == "simplified_pi_gain":
            data.simplified_pi_gain = int(value)
        elif key == "simplified_dmax_gain":
            data.simplified_dmax_gain = int(value)
        elif key == "simplified_feedforward_gain":
            data.simplified_feedforward_gain = int(value)
        elif key == "simplified_pitch_d_gain":
            data.simplified_pitch_d_gain = int(value)
        elif key == "simplified_pitch_pi_gain":
            data.simplified_pitch_pi_gain = int(value)
        elif key == "simplified_dterm_filter":
            data.simplified_dterm_filter = int(value)
        elif key == "simplified_dterm_filter_multiplier":
            data.simplified_dterm_filter_multiplier = int(value)
        elif key == "simplified_gyro_filter":
            data.simplified_gyro_filter = int(value)
        elif key == "simplified_gyro_filter_multiplier":
            data.simplified_gyro_filter_multiplier = int(value)

        # Dynamic idle
        elif key == "dyn_idle_min_rpm":
            data.dyn_idle_min_rpm = int(value)
        elif key == "dyn_idle_p_gain":
            data.dyn_idle_p_gain = int(value)
        elif key == "dyn_idle_i_gain":
            data.dyn_idle_i_gain = int(value)
        elif key == "dyn_idle_d_gain":
            data.dyn_idle_d_gain = int(value)

        # Other
        elif key == "debug_mode":
            data.debug_mode = int(value)
        elif key == "features":
            data.features = int(value)
        elif key == "serialrx_provider":
            data.serialrx_provider = int(value)
        elif key == "vbat_sag_compensation":
            data.vbat_sag_compensation = int(value)
        elif key == "throttle_boost":
            data.throttle_boost = int(value)
        elif key == "throttle_boost_cutoff":
            data.throttle_boost_cutoff = int(value)
        elif key == "airmode_activate_throttle":
            data.airmode_activate_throttle = int(value)

    def get_effective_gyro_rate(self, data: BBLHeaderData) -> float:
        """Calculate the effective gyro sampling rate in Hz."""
        if data.looptime > 0:
            base_rate = 1_000_000 / data.looptime  # base gyro rate
            return base_rate / data.gyro_sync_denom
        return 8000  # default assumption

    def get_effective_pid_rate(self, data: BBLHeaderData) -> float:
        """Calculate the effective PID loop rate in Hz."""
        gyro_rate = self.get_effective_gyro_rate(data)
        return gyro_rate / data.pid_process_denom

    def get_blackbox_sample_rate(self, data: BBLHeaderData) -> float:
        """Calculate the effective blackbox logging rate in Hz."""
        pid_rate = self.get_effective_pid_rate(data)
        if data.p_ratio > 0:
            return pid_rate / data.p_ratio
        return pid_rate
