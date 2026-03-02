"""
Betaflight CLI Dump Parser.

Parses the output of 'dump all' command from Betaflight CLI
and extracts all configuration parameters into structured data.
"""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PIDProfile:
    """Single PID profile data."""
    index: int = 0
    name: str = ""
    # PID values
    p_roll: int = 0
    i_roll: int = 0
    d_roll: int = 0
    f_roll: int = 0
    p_pitch: int = 0
    i_pitch: int = 0
    d_pitch: int = 0
    f_pitch: int = 0
    p_yaw: int = 0
    i_yaw: int = 0
    d_yaw: int = 0
    f_yaw: int = 0
    # D limits
    d_min_roll: int = 0
    d_min_pitch: int = 0
    d_min_yaw: int = 0
    d_max_gain: int = 0
    d_max_advance: int = 0
    # Dterm filters
    dterm_lpf1_type: str = "PT1"
    dterm_lpf1_static_hz: int = 0
    dterm_lpf1_dyn_min_hz: int = 0
    dterm_lpf1_dyn_max_hz: int = 0
    dterm_lpf1_dyn_expo: int = 0
    dterm_lpf2_type: str = "PT1"
    dterm_lpf2_static_hz: int = 0
    dterm_notch_hz: int = 0
    dterm_notch_cutoff: int = 0
    # I-term
    iterm_relax: str = "RP"
    iterm_relax_type: str = "SETPOINT"
    iterm_relax_cutoff: int = 15
    iterm_windup: int = 85
    iterm_limit: int = 400
    iterm_rotation: str = "OFF"
    # Anti-gravity
    anti_gravity_gain: int = 80
    anti_gravity_cutoff_hz: int = 5
    anti_gravity_p_gain: int = 100
    # TPA
    tpa_mode: str = "D"
    tpa_rate: int = 65
    tpa_breakpoint: int = 1350
    tpa_low_rate: int = 20
    tpa_low_breakpoint: int = 1050
    tpa_low_always: str = "OFF"
    # Feedforward
    feedforward_transition: int = 0
    feedforward_averaging: str = "OFF"
    feedforward_smooth_factor: int = 25
    feedforward_jitter_factor: int = 7
    feedforward_boost: int = 15
    feedforward_max_rate_limit: int = 90
    # Throttle
    throttle_boost: int = 5
    throttle_boost_cutoff: int = 15
    # Angle / Horizon
    angle_p_gain: int = 50
    angle_limit: int = 60
    angle_earth_ref: int = 100
    angle_feedforward: int = 50
    angle_feedforward_smoothing_ms: int = 80
    horizon_level_strength: int = 75
    horizon_limit_sticks: int = 75
    horizon_limit_degrees: int = 135
    horizon_delay_ms: int = 500
    # Other
    vbat_sag_compensation: int = 0
    pid_at_min_throttle: str = "ON"
    yaw_lowpass_hz: int = 100
    pidsum_limit: int = 500
    pidsum_limit_yaw: int = 400
    crash_recovery: str = "OFF"
    use_integrated_yaw: str = "OFF"
    motor_output_limit: int = 100
    thrust_linear: int = 0
    # Dynamic idle
    dyn_idle_min_rpm: int = 0
    dyn_idle_p_gain: int = 50
    dyn_idle_i_gain: int = 50
    dyn_idle_d_gain: int = 50
    dyn_idle_max_increase: int = 150
    dyn_idle_start_increase: int = 50
    # Simplified tuning
    simplified_pids_mode: str = "OFF"
    simplified_master_multiplier: int = 100
    simplified_i_gain: int = 100
    simplified_d_gain: int = 100
    simplified_pi_gain: int = 100
    simplified_dmax_gain: int = 100
    simplified_feedforward_gain: int = 100
    simplified_pitch_d_gain: int = 100
    simplified_pitch_pi_gain: int = 100
    simplified_dterm_filter: str = "ON"
    simplified_dterm_filter_multiplier: int = 100
    # EZ landing
    ez_landing_threshold: int = 25
    ez_landing_limit: int = 15
    ez_landing_speed: int = 50
    # Abs control
    abs_control_gain: int = 0


@dataclass
class RateProfile:
    """Single rate profile data."""
    index: int = 0
    name: str = ""
    rates_type: str = "ACTUAL"
    thr_mid: int = 50
    thr_expo: int = 0
    roll_rc_rate: int = 7
    pitch_rc_rate: int = 7
    yaw_rc_rate: int = 7
    roll_expo: int = 0
    pitch_expo: int = 0
    yaw_expo: int = 0
    roll_srate: int = 67
    pitch_srate: int = 67
    yaw_srate: int = 67
    throttle_limit_type: str = "OFF"
    throttle_limit_percent: int = 100
    roll_rate_limit: int = 1998
    pitch_rate_limit: int = 1998
    yaw_rate_limit: int = 1998


@dataclass
class CLIData:
    """Complete parsed CLI dump data."""
    # Firmware info
    firmware_version: str = ""
    firmware_target: str = ""
    firmware_date: str = ""
    board_name: str = ""
    manufacturer_id: str = ""
    craft_name: str = ""
    pilot_name: str = ""
    mcu_type: str = ""

    # Motor / ESC
    motor_pwm_protocol: str = ""
    motor_poles: int = 12
    motor_kv: int = 0
    dshot_bidir: str = "OFF"
    dshot_idle_value: int = 550
    dshot_burst: str = "AUTO"
    min_throttle: int = 1070
    max_throttle: int = 2000
    motor_output_reordering: str = ""
    mixer_type: str = "LEGACY"
    yaw_motors_reversed: str = "OFF"

    # Gyro filters
    gyro_hardware_lpf: str = "NORMAL"
    gyro_lpf1_type: str = "PT1"
    gyro_lpf1_static_hz: int = 0
    gyro_lpf1_dyn_min_hz: int = 0
    gyro_lpf1_dyn_max_hz: int = 500
    gyro_lpf1_dyn_expo: int = 5
    gyro_lpf2_type: str = "PT1"
    gyro_lpf2_static_hz: int = 0
    gyro_notch1_hz: int = 0
    gyro_notch1_cutoff: int = 0
    gyro_notch2_hz: int = 0
    gyro_notch2_cutoff: int = 0
    dyn_notch_count: int = 3
    dyn_notch_q: int = 300
    dyn_notch_min_hz: int = 150
    dyn_notch_max_hz: int = 600

    # RPM filter
    rpm_filter_harmonics: int = 3
    rpm_filter_weights: str = "100,100,100"
    rpm_filter_q: int = 500
    rpm_filter_min_hz: int = 100
    rpm_filter_fade_range_hz: int = 50
    rpm_filter_lpf_hz: int = 150

    # Gyro settings
    simplified_gyro_filter: str = "ON"
    simplified_gyro_filter_multiplier: int = 100
    gyro_to_use: str = "FIRST"

    # Looptime
    pid_process_denom: int = 2
    gyro_sync_denom: int = 1

    # RC
    serialrx_provider: str = ""
    rc_smoothing: str = "ON"
    rc_smoothing_auto_factor: int = 30
    rc_smoothing_auto_factor_throttle: int = 30
    rc_smoothing_setpoint_cutoff: int = 0
    rc_smoothing_feedforward_cutoff: int = 0
    rc_smoothing_throttle_cutoff: int = 0
    deadband: int = 0
    yaw_deadband: int = 0

    # Features
    features: list = field(default_factory=list)

    # Blackbox
    blackbox_device: str = ""
    blackbox_sample_rate: str = ""

    # Battery
    vbat_max_cell_voltage: int = 440
    vbat_min_cell_voltage: int = 350
    vbat_warning_cell_voltage: int = 360
    vbat_scale: int = 110
    ibata_scale: int = 400
    current_meter: str = "ADC"
    battery_meter: str = "ADC"

    # Failsafe
    failsafe_procedure: str = "DROP"
    failsafe_delay: int = 10

    # Airmode
    airmode_start_throttle_percent: int = 25

    # OSD
    osd_displayport_device: str = ""
    vcd_video_system: str = ""

    # Debug
    debug_mode: str = ""

    # Profiles
    pid_profiles: list = field(default_factory=list)
    rate_profiles: list = field(default_factory=list)
    active_pid_profile: int = 0
    active_rate_profile: int = 0

    # Aux modes
    aux_modes: list = field(default_factory=list)

    # Serial ports
    serial_ports: list = field(default_factory=list)

    # Raw settings dict for anything not explicitly modeled
    raw_settings: dict = field(default_factory=dict)


class CLIParser:
    """Parse Betaflight CLI dump output into structured data."""

    def __init__(self):
        self.data = CLIData()
        self._current_pid_profile: Optional[PIDProfile] = None
        self._current_rate_profile: Optional[RateProfile] = None
        self._section = "master"  # master, profile, rateprofile

    def parse(self, cli_text: str) -> CLIData:
        """Parse full CLI dump text and return structured data."""
        self.data = CLIData()
        self._current_pid_profile = None
        self._current_rate_profile = None
        self._section = "master"

        lines = cli_text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("dump all"):
                continue
            self._parse_line(line)

        # Save last profile if any
        self._save_current_profiles()

        # Determine active profiles
        self._detect_active_profiles(cli_text)

        return self.data

    def _parse_line(self, line: str):
        """Parse a single line from CLI dump."""
        # Version comment
        if line.startswith("# Betaflight"):
            self._parse_version(line)
            return

        # Comments
        if line.startswith("#"):
            # Check for name
            m = re.match(r"#\s*name:\s*(.+)", line)
            if m:
                self.data.craft_name = m.group(1).strip()
            # Check for profile sections
            m = re.match(r"#\s*profile\s+(\d+)", line)
            if m:
                return
            m = re.match(r"#\s*rateprofile\s+(\d+)", line)
            if m:
                return
            return

        # Board name
        if line.startswith("board_name"):
            self.data.board_name = line.split(None, 1)[1] if len(line.split()) > 1 else ""
            return

        # Manufacturer ID
        if line.startswith("manufacturer_id"):
            self.data.manufacturer_id = line.split(None, 1)[1] if len(line.split()) > 1 else ""
            return

        # Profile switch
        m = re.match(r"^profile\s+(\d+)\s*$", line)
        if m:
            self._save_current_profiles()
            idx = int(m.group(1))
            self._current_pid_profile = PIDProfile(index=idx)
            self._current_rate_profile = None
            self._section = "profile"
            return

        # Rate profile switch
        m = re.match(r"^rateprofile\s+(\d+)\s*$", line)
        if m:
            self._save_current_profiles()
            idx = int(m.group(1))
            self._current_rate_profile = RateProfile(index=idx)
            self._current_pid_profile = None
            self._section = "rateprofile"
            return

        # Feature lines
        if line.startswith("feature "):
            feat = line[8:].strip()
            if feat.startswith("-"):
                fname = feat[1:]
                if fname in self.data.features:
                    self.data.features.remove(fname)
            else:
                if feat not in self.data.features:
                    self.data.features.append(feat)
            return

        # Serial lines
        if line.startswith("serial "):
            self.data.serial_ports.append(line)
            return

        # Aux mode lines
        if line.startswith("aux "):
            self.data.aux_modes.append(line)
            return

        # Mixer
        if line.startswith("mixer "):
            parts = line.split()
            if len(parts) >= 2:
                self.data.mixer_type = parts[1]
            return

        # Set commands
        m = re.match(r"^set\s+(\S+)\s*=\s*(.+)$", line)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            self._apply_setting(key, value)
            return

    def _parse_version(self, line: str):
        """Parse version comment line."""
        # # Betaflight / STM32F405 (S405) 4.5.3 Feb 17 2026 / 06:41:25 ...
        m = re.match(
            r"#\s*Betaflight\s*/\s*(\S+)\s*\(\S+\)\s*([\d.]+)\s*(.*?)(?:/|$)",
            line,
        )
        if m:
            self.data.mcu_type = m.group(1)
            self.data.firmware_version = m.group(2)
            self.data.firmware_date = m.group(3).strip()
            self.data.firmware_target = m.group(1)

    def _apply_setting(self, key: str, value: str):
        """Apply a 'set key = value' setting to the appropriate data structure."""
        # Store raw
        self.data.raw_settings[key] = value

        # Route to correct profile or master
        if self._section == "profile" and self._current_pid_profile:
            self._apply_pid_profile_setting(key, value)
        elif self._section == "rateprofile" and self._current_rate_profile:
            self._apply_rate_profile_setting(key, value)
        else:
            self._apply_master_setting(key, value)

    def _apply_master_setting(self, key: str, value: str):
        """Apply a master-level setting."""
        mapping = {
            "motor_pwm_protocol": ("motor_pwm_protocol", str),
            "motor_poles": ("motor_poles", int),
            "motor_kv": ("motor_kv", int),
            "dshot_bidir": ("dshot_bidir", str),
            "dshot_idle_value": ("dshot_idle_value", int),
            "dshot_burst": ("dshot_burst", str),
            "min_throttle": ("min_throttle", int),
            "max_throttle": ("max_throttle", int),
            "yaw_motors_reversed": ("yaw_motors_reversed", str),
            "gyro_hardware_lpf": ("gyro_hardware_lpf", str),
            "gyro_lpf1_type": ("gyro_lpf1_type", str),
            "gyro_lpf1_static_hz": ("gyro_lpf1_static_hz", int),
            "gyro_lpf1_dyn_min_hz": ("gyro_lpf1_dyn_min_hz", int),
            "gyro_lpf1_dyn_max_hz": ("gyro_lpf1_dyn_max_hz", int),
            "gyro_lpf1_dyn_expo": ("gyro_lpf1_dyn_expo", int),
            "gyro_lpf2_type": ("gyro_lpf2_type", str),
            "gyro_lpf2_static_hz": ("gyro_lpf2_static_hz", int),
            "gyro_notch1_hz": ("gyro_notch1_hz", int),
            "gyro_notch1_cutoff": ("gyro_notch1_cutoff", int),
            "gyro_notch2_hz": ("gyro_notch2_hz", int),
            "gyro_notch2_cutoff": ("gyro_notch2_cutoff", int),
            "dyn_notch_count": ("dyn_notch_count", int),
            "dyn_notch_q": ("dyn_notch_q", int),
            "dyn_notch_min_hz": ("dyn_notch_min_hz", int),
            "dyn_notch_max_hz": ("dyn_notch_max_hz", int),
            "rpm_filter_harmonics": ("rpm_filter_harmonics", int),
            "rpm_filter_weights": ("rpm_filter_weights", str),
            "rpm_filter_q": ("rpm_filter_q", int),
            "rpm_filter_min_hz": ("rpm_filter_min_hz", int),
            "rpm_filter_fade_range_hz": ("rpm_filter_fade_range_hz", int),
            "rpm_filter_lpf_hz": ("rpm_filter_lpf_hz", int),
            "simplified_gyro_filter": ("simplified_gyro_filter", str),
            "simplified_gyro_filter_multiplier": ("simplified_gyro_filter_multiplier", int),
            "pid_process_denom": ("pid_process_denom", int),
            "serialrx_provider": ("serialrx_provider", str),
            "rc_smoothing": ("rc_smoothing", str),
            "rc_smoothing_auto_factor": ("rc_smoothing_auto_factor", int),
            "rc_smoothing_auto_factor_throttle": ("rc_smoothing_auto_factor_throttle", int),
            "rc_smoothing_setpoint_cutoff": ("rc_smoothing_setpoint_cutoff", int),
            "rc_smoothing_feedforward_cutoff": ("rc_smoothing_feedforward_cutoff", int),
            "rc_smoothing_throttle_cutoff": ("rc_smoothing_throttle_cutoff", int),
            "deadband": ("deadband", int),
            "yaw_deadband": ("yaw_deadband", int),
            "blackbox_device": ("blackbox_device", str),
            "blackbox_sample_rate": ("blackbox_sample_rate", str),
            "vbat_max_cell_voltage": ("vbat_max_cell_voltage", int),
            "vbat_min_cell_voltage": ("vbat_min_cell_voltage", int),
            "vbat_warning_cell_voltage": ("vbat_warning_cell_voltage", int),
            "vbat_scale": ("vbat_scale", int),
            "ibata_scale": ("ibata_scale", int),
            "current_meter": ("current_meter", str),
            "battery_meter": ("battery_meter", str),
            "failsafe_procedure": ("failsafe_procedure", str),
            "failsafe_delay": ("failsafe_delay", int),
            "airmode_start_throttle_percent": ("airmode_start_throttle_percent", int),
            "osd_displayport_device": ("osd_displayport_device", str),
            "vcd_video_system": ("vcd_video_system", str),
            "debug_mode": ("debug_mode", str),
            "craft_name": ("craft_name", str),
            "pilot_name": ("pilot_name", str),
            "gyro_to_use": ("gyro_to_use", str),
            "motor_output_reordering": ("motor_output_reordering", str),
        }

        if key in mapping:
            attr, type_fn = mapping[key]
            try:
                setattr(self.data, attr, type_fn(value))
            except (ValueError, TypeError):
                setattr(self.data, attr, value)

    def _apply_pid_profile_setting(self, key: str, value: str):
        """Apply a setting to the current PID profile."""
        p = self._current_pid_profile
        if not p:
            return

        int_fields = {
            "p_pitch", "i_pitch", "d_pitch", "f_pitch",
            "p_roll", "i_roll", "d_roll", "f_roll",
            "p_yaw", "i_yaw", "d_yaw", "f_yaw",
            "d_min_roll", "d_min_pitch", "d_min_yaw",
            "d_max_gain", "d_max_advance",
            "dterm_lpf1_static_hz", "dterm_lpf1_dyn_min_hz",
            "dterm_lpf1_dyn_max_hz", "dterm_lpf1_dyn_expo",
            "dterm_lpf2_static_hz",
            "dterm_notch_hz", "dterm_notch_cutoff",
            "iterm_relax_cutoff", "iterm_windup", "iterm_limit",
            "anti_gravity_gain", "anti_gravity_cutoff_hz", "anti_gravity_p_gain",
            "tpa_rate", "tpa_breakpoint", "tpa_low_rate", "tpa_low_breakpoint",
            "feedforward_transition", "feedforward_smooth_factor",
            "feedforward_jitter_factor", "feedforward_boost",
            "feedforward_max_rate_limit",
            "throttle_boost", "throttle_boost_cutoff",
            "angle_p_gain", "angle_limit", "angle_earth_ref",
            "angle_feedforward", "angle_feedforward_smoothing_ms",
            "horizon_level_strength", "horizon_limit_sticks",
            "horizon_limit_degrees", "horizon_delay_ms",
            "vbat_sag_compensation",
            "yaw_lowpass_hz", "pidsum_limit", "pidsum_limit_yaw",
            "motor_output_limit", "thrust_linear",
            "dyn_idle_min_rpm", "dyn_idle_p_gain", "dyn_idle_i_gain",
            "dyn_idle_d_gain", "dyn_idle_max_increase", "dyn_idle_start_increase",
            "simplified_master_multiplier", "simplified_i_gain",
            "simplified_d_gain", "simplified_pi_gain",
            "simplified_dmax_gain", "simplified_feedforward_gain",
            "simplified_pitch_d_gain", "simplified_pitch_pi_gain",
            "simplified_dterm_filter_multiplier",
            "ez_landing_threshold", "ez_landing_limit", "ez_landing_speed",
            "abs_control_gain",
        }
        str_fields = {
            "profile_name", "dterm_lpf1_type", "dterm_lpf2_type",
            "iterm_relax", "iterm_relax_type", "iterm_rotation",
            "tpa_mode", "tpa_low_always",
            "feedforward_averaging",
            "pid_at_min_throttle", "crash_recovery",
            "use_integrated_yaw",
            "simplified_pids_mode", "simplified_dterm_filter",
        }

        if key == "profile_name":
            p.name = value
        elif key in int_fields:
            try:
                setattr(p, key, int(value))
            except ValueError:
                pass
        elif key in str_fields:
            if hasattr(p, key):
                setattr(p, key, value)

    def _apply_rate_profile_setting(self, key: str, value: str):
        """Apply a setting to the current rate profile."""
        r = self._current_rate_profile
        if not r:
            return

        int_fields = {
            "thr_mid", "thr_expo",
            "roll_rc_rate", "pitch_rc_rate", "yaw_rc_rate",
            "roll_expo", "pitch_expo", "yaw_expo",
            "roll_srate", "pitch_srate", "yaw_srate",
            "throttle_limit_percent",
            "roll_rate_limit", "pitch_rate_limit", "yaw_rate_limit",
        }
        str_fields = {
            "rateprofile_name", "rates_type", "throttle_limit_type",
        }

        if key == "rateprofile_name":
            r.name = value
        elif key in int_fields:
            try:
                setattr(r, key, int(value))
            except ValueError:
                pass
        elif key in str_fields:
            if key == "rates_type":
                r.rates_type = value
            elif key == "throttle_limit_type":
                r.throttle_limit_type = value

    def _save_current_profiles(self):
        """Save current profile to the profiles list."""
        if self._current_pid_profile is not None:
            # Check if already exists (update) or new
            existing = [p for p in self.data.pid_profiles
                        if p.index == self._current_pid_profile.index]
            if existing:
                idx = self.data.pid_profiles.index(existing[0])
                self.data.pid_profiles[idx] = self._current_pid_profile
            else:
                self.data.pid_profiles.append(self._current_pid_profile)
            self._current_pid_profile = None

        if self._current_rate_profile is not None:
            existing = [r for r in self.data.rate_profiles
                        if r.index == self._current_rate_profile.index]
            if existing:
                idx = self.data.rate_profiles.index(existing[0])
                self.data.rate_profiles[idx] = self._current_rate_profile
            else:
                self.data.rate_profiles.append(self._current_rate_profile)
            self._current_rate_profile = None

    def _detect_active_profiles(self, cli_text: str):
        """Detect which profile/rateprofile is active (from restore lines)."""
        # Look for "# restore original profile selection" followed by "profile X"
        lines = cli_text.strip().split("\n")
        for i, line in enumerate(lines):
            if "restore original profile selection" in line:
                if i + 1 < len(lines):
                    m = re.match(r"profile\s+(\d+)", lines[i + 1].strip())
                    if m:
                        self.data.active_pid_profile = int(m.group(1))
            if "restore original rateprofile selection" in line:
                if i + 1 < len(lines):
                    m = re.match(r"rateprofile\s+(\d+)", lines[i + 1].strip())
                    if m:
                        self.data.active_rate_profile = int(m.group(1))

    def get_active_pid_profile(self) -> Optional[PIDProfile]:
        """Return the currently active PID profile."""
        for p in self.data.pid_profiles:
            if p.index == self.data.active_pid_profile:
                return p
        return self.data.pid_profiles[0] if self.data.pid_profiles else None

    def get_active_rate_profile(self) -> Optional[RateProfile]:
        """Return the currently active rate profile."""
        for r in self.data.rate_profiles:
            if r.index == self.data.active_rate_profile:
                return r
        return self.data.rate_profiles[0] if self.data.rate_profiles else None
