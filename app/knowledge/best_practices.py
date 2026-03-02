"""
Betaflight Tuning Best Practices & Knowledge Base.

Contains tuning rules, recommendations, and diagnostic patterns
based on the Betaflight wiki, tuning guides, and community knowledge.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum


class Severity(Enum):
    """Issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Category(Enum):
    """Analysis categories."""
    PID = "PID Tuning"
    FILTER = "Filter Settings"
    RATE = "Rates & RC"
    MOTOR = "Motor & ESC"
    GENERAL = "General Config"
    NOISE = "Noise Analysis"
    TRACKING = "PID Tracking"
    PERFORMANCE = "Performance"


@dataclass
class Finding:
    """A single analysis finding/recommendation."""
    category: Category
    severity: Severity
    title: str
    description: str
    current_value: str = ""
    recommended_value: str = ""
    cli_commands: List[str] = field(default_factory=list)
    explanation: str = ""
    reference_url: str = ""


@dataclass
class AnalysisReport:
    """Complete analysis report."""
    findings: List[Finding] = field(default_factory=list)
    summary_score: int = 100  # 0-100 overall tuning score
    cli_output: str = ""  # Ready-to-paste CLI commands

    # Stats
    critical_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    # Flight data analysis results (if available)
    noise_data: Optional[dict] = None
    tracking_data: Optional[dict] = None
    motor_data: Optional[dict] = None

    def add_finding(self, finding: Finding):
        """Add a finding and update stats."""
        self.findings.append(finding)
        if finding.severity == Severity.CRITICAL:
            self.critical_count += 1
            self.summary_score -= 15
        elif finding.severity == Severity.ERROR:
            self.error_count += 1
            self.summary_score -= 8
        elif finding.severity == Severity.WARNING:
            self.warning_count += 1
            self.summary_score -= 3
        else:
            self.info_count += 1

        self.summary_score = max(0, self.summary_score)

    @property
    def overall_score(self) -> int:
        """Alias for summary_score for template compatibility."""
        return self.summary_score


class BestPractices:
    """Betaflight tuning best practices and rules engine."""

    # ==================== PID Ranges ====================
    # Format: (min_reasonable, max_reasonable) for 5" freestyle quad
    PID_RANGES_5INCH = {
        "p_roll": (30, 90),
        "p_pitch": (30, 95),
        "p_yaw": (25, 100),
        "i_roll": (50, 150),
        "i_pitch": (50, 150),
        "i_yaw": (50, 150),
        "d_roll": (20, 70),
        "d_pitch": (25, 75),
        "d_yaw": (0, 40),
        "f_roll": (0, 250),
        "f_pitch": (0, 250),
        "f_yaw": (0, 250),
    }

    # Smaller quads (3" - whoop - toothpick) tend to need higher PID
    PID_RANGES_SMALL = {
        "p_roll": (40, 120),
        "p_pitch": (40, 130),
        "p_yaw": (30, 120),
        "i_roll": (60, 180),
        "i_pitch": (60, 180),
        "i_yaw": (50, 180),
        "d_roll": (25, 80),
        "d_pitch": (30, 85),
        "d_yaw": (0, 50),
        "f_roll": (0, 300),
        "f_pitch": (0, 300),
        "f_yaw": (0, 300),
    }

    # ==================== Filter Frequency Limits ====================
    # Lower limit: below this causes too much latency
    # Upper limit: above this and noise will cause problems
    GYRO_LPF2_RANGE = (200, 1000)
    DTERM_LPF1_RANGE = (50, 200)
    DTERM_LPF2_RANGE = (100, 400)
    DYN_NOTCH_MIN_RANGE = (60, 250)
    DYN_NOTCH_MAX_RANGE = (300, 800)

    # ==================== Diagnostic Patterns ====================
    @staticmethod
    def diagnose_oscillation_from_pids(p_val: int, d_val: int, d_min: int,
                                        axis: str) -> Optional[Finding]:
        """Diagnose potential oscillation from PID values."""
        # High P with low D = likely oscillation under load
        if p_val > 70 and d_val < 30:
            return Finding(
                category=Category.PID,
                severity=Severity.WARNING,
                title=f"{axis} P/D Imbalance",
                description=f"{axis} P={p_val} is high relative to D={d_val}. "
                           f"This can cause oscillation especially during quick moves.",
                explanation="P drives the correction response while D dampens it. "
                           "When P is much higher than D, the system can oscillate. "
                           "Either reduce P or increase D.",
            )
        # Very high D = hot motors, possibly noisy
        if d_val > 60:
            return Finding(
                category=Category.PID,
                severity=Severity.WARNING,
                title=f"High {axis} D-term",
                description=f"{axis} D={d_val} is quite high. May cause hot motors "
                           f"and noise amplification.",
                explanation="High D-term amplifies noise and heats motors. "
                           "Consider lowering if motors run hot or you see D-term noise in blackbox.",
            )
        return None

    @staticmethod
    def diagnose_filter_setup(gyro_lpf1_hz: int, gyro_lpf2_hz: int,
                               dterm_lpf1_hz: int, dterm_lpf2_hz: int,
                               rpm_filter_on: bool, dyn_notch_count: int) -> List[Finding]:
        """Diagnose filter configuration issues."""
        findings = []

        # RPM filter check
        if not rpm_filter_on:
            findings.append(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title="RPM Filter Disabled",
                description="RPM filtering is not active. This requires bidirectional DShot.",
                explanation="RPM filter provides the best motor noise rejection with minimal latency. "
                           "Enable DShot bidirectional to use it.",
                cli_commands=["set dshot_bidir = ON", "set rpm_filter_harmonics = 3"],
            ))

        # If RPM filter is on, dynamic notch can be reduced
        if rpm_filter_on and dyn_notch_count > 2:
            findings.append(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title="Dynamic Notch Redundancy",
                description=f"Dynamic notch count is {dyn_notch_count} with RPM filter enabled. "
                           f"With RPM filter active, 1-2 dynamic notches is usually sufficient.",
                explanation="RPM filter handles motor harmonics. Dynamic notch handles "
                           "frame resonances. With RPM filter on, fewer notches = less latency.",
                recommended_value="1-2",
                cli_commands=["set dyn_notch_count = 1"],
            ))

        # Gyro LPF2 too low = excess latency
        if 0 < gyro_lpf2_hz < 200:
            findings.append(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title="Gyro LPF2 Very Low",
                description=f"Gyro LPF2 at {gyro_lpf2_hz}Hz adds significant latency.",
                explanation="This low-pass filter cutoff is very low which delays gyro data. "
                           "With RPM filter and dynamic notch, you may be able to raise this.",
            ))

        # Dterm LPF1 check
        if dterm_lpf1_hz > 200:
            findings.append(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title="Dterm LPF1 Too High",
                description=f"Dterm LPF1 at {dterm_lpf1_hz}Hz may let through too much noise.",
                explanation="D-term is very noise-sensitive. High filter cutoffs can cause "
                           "hot motors and noisy flight.",
            ))

        return findings

    # ==================== Common Quad Profiles ====================
    # Reasonable defaults for different quad sizes

    @staticmethod
    def get_recommended_profile(frame_class: str = "5inch_freestyle") -> dict:
        """Get recommended tuning profile for a frame class."""
        profiles = {
            "5inch_freestyle": {
                "p_roll": 45, "i_roll": 80, "d_roll": 40, "f_roll": 120,
                "p_pitch": 47, "i_pitch": 84, "d_pitch": 46, "f_pitch": 125,
                "p_yaw": 45, "i_yaw": 80, "d_yaw": 0, "f_yaw": 120,
                "d_min_roll": 30, "d_min_pitch": 34,
                "dterm_lpf1_dyn_min_hz": 75, "dterm_lpf1_dyn_max_hz": 150,
                "dterm_lpf2_static_hz": 150,
                "feedforward_jitter_factor": 7,
                "anti_gravity_gain": 80,
            },
            "5inch_race": {
                "p_roll": 50, "i_roll": 70, "d_roll": 30, "f_roll": 150,
                "p_pitch": 52, "i_pitch": 73, "d_pitch": 34, "f_pitch": 155,
                "p_yaw": 40, "i_yaw": 70, "d_yaw": 0, "f_yaw": 100,
                "d_min_roll": 25, "d_min_pitch": 28,
                "dterm_lpf1_dyn_min_hz": 80, "dterm_lpf1_dyn_max_hz": 170,
                "dterm_lpf2_static_hz": 170,
                "feedforward_jitter_factor": 10,
            },
            "3inch_cinewhoop": {
                "p_roll": 65, "i_roll": 100, "d_roll": 50, "f_roll": 0,
                "p_pitch": 68, "i_pitch": 105, "d_pitch": 55, "f_pitch": 0,
                "p_yaw": 60, "i_yaw": 100, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 35, "d_min_pitch": 40,
                "dterm_lpf1_dyn_min_hz": 70, "dterm_lpf1_dyn_max_hz": 140,
                "dterm_lpf2_static_hz": 140,
                "feedforward_jitter_factor": 5,
                "anti_gravity_gain": 65,
            },
            "toothpick_ultralight": {
                "p_roll": 55, "i_roll": 90, "d_roll": 45, "f_roll": 100,
                "p_pitch": 58, "i_pitch": 95, "d_pitch": 50, "f_pitch": 105,
                "p_yaw": 50, "i_yaw": 85, "d_yaw": 0, "f_yaw": 80,
                "d_min_roll": 30, "d_min_pitch": 34,
            },
            "whoop_1s": {
                "p_roll": 70, "i_roll": 120, "d_roll": 55, "f_roll": 0,
                "p_pitch": 75, "i_pitch": 125, "d_pitch": 60, "f_pitch": 0,
                "p_yaw": 70, "i_yaw": 120, "d_yaw": 0, "f_yaw": 0,
                "d_min_roll": 40, "d_min_pitch": 45,
                "anti_gravity_gain": 50,
            },
        }
        return profiles.get(frame_class, profiles["5inch_freestyle"])

    # ==================== Noise Thresholds ====================
    NOISE_THRESHOLDS = {
        # RMS noise levels in deg/s for gyro
        "gyro_noise_excellent": 2.0,
        "gyro_noise_good": 5.0,
        "gyro_noise_moderate": 10.0,
        "gyro_noise_poor": 20.0,
        "gyro_noise_terrible": 40.0,
        # D-term noise in the PID output
        "dterm_noise_excellent": 3.0,
        "dterm_noise_good": 8.0,
        "dterm_noise_moderate": 15.0,
        "dterm_noise_poor": 25.0,
    }

    # ==================== Tracking Quality Thresholds ====================
    TRACKING_THRESHOLDS = {
        # RMS tracking error (setpoint - gyro) in deg/s
        "excellent": 5.0,
        "good": 15.0,
        "moderate": 30.0,
        "poor": 50.0,
    }

    # ==================== Motor Balance Thresholds ====================
    MOTOR_THRESHOLDS = {
        # Standard deviation between motors as % of range
        "balanced": 3.0,
        "acceptable": 6.0,
        "imbalanced": 10.0,
        # Motor saturation threshold (% of time at max)
        "saturation_ok": 1.0,
        "saturation_warning": 5.0,
        "saturation_critical": 10.0,
    }

    # ==================== Betaflight Feature Flags ====================
    FEATURE_FLAGS = {
        "RX_PPM": 1 << 0,
        "INFLIGHT_ACC_CAL": 1 << 2,
        "RX_SERIAL": 1 << 3,
        "MOTOR_STOP": 1 << 4,
        "SERVO_TILT": 1 << 5,
        "SOFTSERIAL": 1 << 6,
        "GPS": 1 << 7,
        "RANGEFINDER": 1 << 9,
        "TELEMETRY": 1 << 10,
        "3D": 1 << 12,
        "RX_PARALLEL_PWM": 1 << 13,
        "RX_MSP": 1 << 14,
        "RSSI_ADC": 1 << 15,
        "LED_STRIP": 1 << 16,
        "DISPLAY": 1 << 17,
        "OSD": 1 << 18,
        "CHANNEL_FORWARDING": 1 << 20,
        "TRANSPONDER": 1 << 21,
        "AIRMODE": 1 << 22,
        "RX_SPI": 1 << 25,
        "ESC_SENSOR": 1 << 27,
        "ANTI_GRAVITY": 1 << 28,
    }
