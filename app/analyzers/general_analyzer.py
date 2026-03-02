"""
General Configuration Analyzer.

Checks overall system configuration, features, safety settings, etc.
"""
from ..parsers.cli_parser import CLIData
from ..knowledge.best_practices import (
    AnalysisReport, Category, Finding, Severity,
)


class GeneralAnalyzer:
    """Analyze general configuration."""

    def analyze_config(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze general configuration from CLI dump."""
        self._analyze_firmware(cli_data, report)
        self._analyze_motor_protocol(cli_data, report)
        self._analyze_features(cli_data, report)
        self._analyze_failsafe(cli_data, report)
        self._analyze_battery(cli_data, report)
        self._analyze_rx_setup(cli_data, report)
        self._analyze_blackbox(cli_data, report)
        self._analyze_loop_time(cli_data, report)
        self._analyze_osd(cli_data, report)

    def _analyze_firmware(self, cli_data: CLIData, report: AnalysisReport):
        """Check firmware version."""
        report.add_finding(Finding(
            category=Category.GENERAL,
            severity=Severity.INFO,
            title=f"Firmware: Betaflight {cli_data.firmware_version}",
            description=f"Board: {cli_data.board_name} ({cli_data.mcu_type}), "
                       f"Craft: {cli_data.craft_name}",
        ))

        # Check if on a recent version
        if cli_data.firmware_version:
            parts = cli_data.firmware_version.split(".")
            if len(parts) >= 2:
                major, minor = int(parts[0]), int(parts[1])
                if major < 4 or (major == 4 and minor < 4):
                    report.add_finding(Finding(
                        category=Category.GENERAL,
                        severity=Severity.WARNING,
                        title="Older Firmware Version",
                        description=f"Betaflight {cli_data.firmware_version} is not the latest. "
                                   f"Consider updating for improved filtering and PID algorithms.",
                        explanation="Newer versions have significant improvements in filtering, "
                                   "PID controllers, and features like improved RPM filter.",
                    ))

    def _analyze_motor_protocol(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze motor/ESC protocol."""
        protocol = cli_data.motor_pwm_protocol

        report.add_finding(Finding(
            category=Category.MOTOR,
            severity=Severity.INFO,
            title=f"Motor Protocol: {protocol}",
            description=f"DShot Bidir: {cli_data.dshot_bidir}, "
                       f"Motor Poles: {cli_data.motor_poles}, "
                       f"Motor KV: {cli_data.motor_kv}",
        ))

        # Check for slower protocols
        if protocol in ("PWM", "ONESHOT125", "ONESHOT42", "MULTISHOT"):
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.WARNING,
                title="Legacy Motor Protocol",
                description=f"{protocol} is a legacy protocol. DShot provides better performance "
                           f"and enables advanced features like bidirectional communication.",
                recommended_value="DSHOT300 or DSHOT600",
                cli_commands=["set motor_pwm_protocol = DSHOT300"],
            ))

        # DShot300 vs DShot600 on F4
        if protocol == "DSHOT600" and "F405" in (cli_data.board_name or ""):
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.INFO,
                title="DShot600 on F4 Processor",
                description="DShot600 on F4 may cause timing issues with bidirectional DShot. "
                           "DShot300 is recommended for F4 boards with bidir enabled.",
                recommended_value="DSHOT300",
                cli_commands=["set motor_pwm_protocol = DSHOT300"],
            ))

        # DShot idle
        if cli_data.dshot_idle_value > 800:
            report.add_finding(Finding(
                category=Category.MOTOR,
                severity=Severity.INFO,
                title=f"High DShot Idle Value ({cli_data.dshot_idle_value})",
                description="DShot idle controls minimum motor speed. High values mean "
                           "motors spin faster at idle. With dynamic idle enabled, this is less important.",
                explanation="Default is 550. Higher values prevent desync but reduce "
                           "low-throttle authority. If you have dynamic idle, this is the fallback.",
            ))

        # Motor KV info
        if cli_data.motor_kv > 0:
            if cli_data.motor_kv > 2500:
                report.add_finding(Finding(
                    category=Category.MOTOR,
                    severity=Severity.INFO,
                    title=f"High KV Motors ({cli_data.motor_kv}KV)",
                    description="High KV motors (likely small prop setup). May benefit from higher "
                               "D-term and more aggressive filtering.",
                ))

    def _analyze_features(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze enabled features."""
        features = cli_data.features

        # Airmode check
        if "AIRMODE" not in features:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.WARNING,
                title="AIRMODE Disabled",
                description="Airmode is not enabled as a feature. Without airmode, "
                           "PID control is reduced at zero throttle.",
                explanation="Airmode keeps full PID authority at zero throttle, allowing "
                           "for stable inverted flight and better low-throttle handling. "
                           "Essential for acro flying.",
                cli_commands=["feature AIRMODE"],
            ))

        # Anti-gravity check
        if "ANTI_GRAVITY" not in features:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.WARNING,
                title="ANTI_GRAVITY Feature Disabled",
                description="Anti-gravity feature is off. The quad may wobble during "
                           "rapid throttle changes.",
                cli_commands=["feature ANTI_GRAVITY"],
            ))

        # Motor stop check
        if "MOTOR_STOP" in features:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.WARNING,
                title="MOTOR_STOP Enabled",
                description="Motors stop when armed at zero throttle. This disables airmode "
                           "behavior and can cause dangerous situations.",
                explanation="With motor stop, disarming mid-air causes motors to stop immediately. "
                           "This is generally unsafe for acro flying.",
                cli_commands=["feature -MOTOR_STOP"],
            ))

    def _analyze_failsafe(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze failsafe configuration."""
        report.add_finding(Finding(
            category=Category.GENERAL,
            severity=Severity.INFO,
            title=f"Failsafe: {cli_data.failsafe_procedure} (delay: {cli_data.failsafe_delay})",
            description=f"Failsafe procedure is set to {cli_data.failsafe_procedure}.",
        ))

        if cli_data.failsafe_delay < 5:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.WARNING,
                title=f"Short Failsafe Delay ({cli_data.failsafe_delay})",
                description="Very short failsafe delay. May trigger failsafe on brief signal loss.",
                recommended_value="10-15 (0.5-1.5 seconds)",
            ))

    def _analyze_battery(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze battery monitoring setup."""
        if cli_data.battery_meter == "NONE":
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.WARNING,
                title="No Battery Voltage Monitoring",
                description="Battery voltage monitoring is disabled. You cannot see battery level.",
                cli_commands=["set battery_meter = ADC"],
            ))

        # Cell voltage check
        if cli_data.vbat_min_cell_voltage < 320:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.WARNING,
                title=f"Low Min Cell Voltage ({cli_data.vbat_min_cell_voltage/100:.2f}V)",
                description="Minimum cell voltage is set very low. This can damage LiPo batteries.",
                recommended_value="3.50V (350)",
                cli_commands=[f"set vbat_min_cell_voltage = 350"],
            ))

    def _analyze_rx_setup(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze receiver setup."""
        report.add_finding(Finding(
            category=Category.GENERAL,
            severity=Severity.INFO,
            title=f"RX Protocol: {cli_data.serialrx_provider}",
            description=f"Serial RX provider is {cli_data.serialrx_provider}.",
        ))

        # SBUS has lower resolution
        if cli_data.serialrx_provider in ("SBUS", "IBUS"):
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.INFO,
                title=f"Legacy RC Protocol ({cli_data.serialrx_provider})",
                description=f"{cli_data.serialrx_provider} has lower resolution and update rate "
                           f"compared to CRSF/ELRS/GHST. Consider upgrading for better control feel.",
            ))

    def _analyze_blackbox(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze blackbox logging setup."""
        if not cli_data.blackbox_device or cli_data.blackbox_device == "NONE":
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.INFO,
                title="Blackbox Logging Disabled",
                description="No blackbox device configured. Cannot record flight data for analysis.",
            ))
        else:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.INFO,
                title=f"Blackbox: {cli_data.blackbox_device} ({cli_data.blackbox_sample_rate})",
                description=f"Logging to {cli_data.blackbox_device} at {cli_data.blackbox_sample_rate} rate.",
            ))

        # Debug mode
        if cli_data.debug_mode and cli_data.debug_mode != "NONE":
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.INFO,
                title=f"Debug Mode: {cli_data.debug_mode}",
                description="Debug data is being logged. This provides additional diagnostic "
                           "data in blackbox logs.",
            ))

    def _analyze_loop_time(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze PID loop timing."""
        pid_denom = cli_data.pid_process_denom
        # F4 typically runs 8kHz gyro
        gyro_khz = 8
        pid_khz = gyro_khz / pid_denom

        report.add_finding(Finding(
            category=Category.PERFORMANCE,
            severity=Severity.INFO,
            title=f"PID Loop: {pid_khz:.1f}kHz (denom={pid_denom})",
            description=f"Gyro rate ~{gyro_khz}kHz, PID running at ~{pid_khz:.1f}kHz.",
        ))

        if pid_denom > 4:
            report.add_finding(Finding(
                category=Category.PERFORMANCE,
                severity=Severity.WARNING,
                title=f"Slow PID Loop ({pid_khz:.1f}kHz)",
                description="PID loop is running slower than typical. This increases latency.",
                recommended_value="pid_process_denom = 2 (4kHz) for F4",
            ))

    def _analyze_osd(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze OSD setup."""
        if cli_data.osd_displayport_device:
            report.add_finding(Finding(
                category=Category.GENERAL,
                severity=Severity.INFO,
                title=f"OSD: {cli_data.osd_displayport_device} ({cli_data.vcd_video_system})",
                description=f"OSD display via {cli_data.osd_displayport_device}, "
                           f"video system: {cli_data.vcd_video_system}.",
            ))
