"""
Filter Settings Analyzer.

Analyzes gyro and D-term filter configuration for optimal
noise rejection vs latency tradeoff.
"""
from ..parsers.cli_parser import CLIData, PIDProfile
from ..knowledge.best_practices import (
    AnalysisReport, BestPractices, Category, Finding, Severity,
)


class FilterAnalyzer:
    """Analyze filter configuration."""

    def analyze_config(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze all filter settings from CLI dump."""
        self._analyze_gyro_lpf(cli_data, report)
        self._analyze_dyn_notch(cli_data, report)
        self._analyze_rpm_filter(cli_data, report)
        self._analyze_dterm_filters(cli_data, report)
        self._analyze_simplified_filters(cli_data, report)
        self._analyze_filter_stack(cli_data, report)

    def _analyze_gyro_lpf(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze gyro low-pass filters."""
        # Gyro LPF1: Dynamic
        if cli_data.gyro_lpf1_dyn_min_hz == 0 and cli_data.gyro_lpf1_static_hz == 0:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title="Gyro LPF1 Disabled / Dynamic",
                description="Gyro LPF1 is configured with dynamic min=0. With RPM filter enabled, "
                           "this can work well. The dynamic range is 0-{}.".format(
                               cli_data.gyro_lpf1_dyn_max_hz),
                explanation="When dynamic LPF1 min is 0, the filter only engages when needed. "
                           "This minimizes latency at low noise conditions.",
            ))
        elif cli_data.gyro_lpf1_dyn_min_hz > 0:
            if cli_data.gyro_lpf1_dyn_min_hz < 100:
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title=f"Gyro LPF1 Dynamic Min Very Low ({cli_data.gyro_lpf1_dyn_min_hz}Hz)",
                    description="Very low dynamic LPF1 min adds significant latency at low speeds.",
                    explanation="The dynamic LPF adjusts its cutoff between min and max based on "
                               "detected noise. A very low minimum means heavy filtering at low throttle.",
                ))

        # Gyro LPF2: Static
        if cli_data.gyro_lpf2_static_hz > 0:
            if cli_data.gyro_lpf2_static_hz < 300:
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.INFO,
                    title=f"Gyro LPF2 at {cli_data.gyro_lpf2_static_hz}Hz",
                    description="Gyro LPF2 is relatively low. This adds filter latency but provides "
                               "good noise protection.",
                    explanation="Lower = more filtering = more delay. Higher = less filtering = more noise. "
                               "With RPM filter on, 500-675Hz is typical.",
                ))
            elif cli_data.gyro_lpf2_static_hz > 900:
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title=f"Gyro LPF2 Very High ({cli_data.gyro_lpf2_static_hz}Hz)",
                    description="High LPF2 provides minimal filtering. Ensure RPM filter and "
                               "dynamic notch are handling noise adequately.",
                ))
        else:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title="Gyro LPF2 Disabled",
                description="Gyro LPF2 is disabled (0Hz). Ensure other filters handle noise.",
            ))

        # Static notch filters (usually should be off with RPM filter)
        if cli_data.gyro_notch1_hz > 0:
            if cli_data.dshot_bidir == "ON":
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title="Static Gyro Notch 1 Enabled",
                    description=f"Static notch at {cli_data.gyro_notch1_hz}Hz is active alongside "
                               f"RPM filter. This may add unnecessary latency.",
                    explanation="With RPM filter handling motor harmonics, static notch filters "
                               "are usually not needed unless you have a specific frame resonance.",
                    cli_commands=["set gyro_notch1_hz = 0"],
                ))

        if cli_data.gyro_notch2_hz > 0:
            if cli_data.dshot_bidir == "ON":
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title="Static Gyro Notch 2 Enabled",
                    description=f"Static notch at {cli_data.gyro_notch2_hz}Hz is active alongside "
                               f"RPM filter.",
                    cli_commands=["set gyro_notch2_hz = 0"],
                ))

    def _analyze_dyn_notch(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze dynamic notch filter."""
        # Dynamic notch with RPM filter
        rpm_on = (cli_data.dshot_bidir == "ON" and
                  int(cli_data.raw_settings.get("rpm_filter_harmonics", "3")) > 0)

        if rpm_on and cli_data.dyn_notch_count > 2:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title=f"Dynamic Notch Count High ({cli_data.dyn_notch_count}) with RPM Filter",
                description="With RPM filter active, dynamic notch count of 1 is usually sufficient. "
                           "Extra notches add latency.",
                explanation="RPM filter handles motor noise harmonics. Dynamic notch catches "
                           "frame resonances. With RPM filter on, 1 dynamic notch at a wide Q "
                           "is typically enough.",
                recommended_value="1",
                cli_commands=["set dyn_notch_count = 1"],
            ))

        # Dynamic notch Q
        if cli_data.dyn_notch_q < 200:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title=f"Wide Dynamic Notch Q ({cli_data.dyn_notch_q})",
                description="Low Q = wider notch = more frequency range covered but more latency.",
                explanation="Q factor determines notch width. Lower Q = wider notch. "
                           "With RPM filter, a higher Q (400-500) is fine since the notch "
                           "only needs to catch frame resonances.",
            ))

        # Dynamic notch frequency range
        if cli_data.dyn_notch_min_hz < 80:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title=f"Dynamic Notch Min Hz Very Low ({cli_data.dyn_notch_min_hz})",
                description="Very low minimum allows the notch to track very low frequencies, "
                           "which adds latency and may falsely track non-noise signals.",
                recommended_value="100-150Hz",
            ))

    def _analyze_rpm_filter(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze RPM filter configuration."""
        bidir_on = cli_data.dshot_bidir == "ON"
        rpm_harmonics = int(cli_data.raw_settings.get("rpm_filter_harmonics", "3"))

        if bidir_on and rpm_harmonics > 0:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title=f"RPM Filter Active ({rpm_harmonics} harmonics)",
                description=f"RPM filter is running with {rpm_harmonics} harmonics, "
                           f"Q={cli_data.rpm_filter_q}, min_hz={cli_data.rpm_filter_min_hz}.",
                explanation="RPM filter is the most effective motor noise filter with minimal latency. "
                           "3 harmonics covers fundamental + 2nd + 3rd motor harmonic.",
            ))

            # RPM filter Q
            if cli_data.rpm_filter_q < 300:
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.INFO,
                    title=f"Wide RPM Filter Q ({cli_data.rpm_filter_q})",
                    description="Lower Q = wider notch per harmonic = more latency. "
                               "Default 500 works well for most setups.",
                    recommended_value="500",
                ))

            # Motor poles check
            if cli_data.motor_poles not in (12, 14):
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title=f"Unusual Motor Poles ({cli_data.motor_poles})",
                    description="Motor poles should match your actual motor. Most common: "
                               "12 poles (6 magnets) or 14 poles (7 magnets). Wrong value = "
                               "RPM filter tracking incorrect frequencies.",
                    explanation="Count the magnets inside your motor bell and multiply by 2 "
                               "to get pole count. Wrong pole count makes RPM filter ineffective.",
                ))
        elif bidir_on and rpm_harmonics == 0:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title="RPM Filter Disabled (Bidir DShot Available)",
                description="Bidirectional DShot is on but RPM filter harmonics = 0. "
                           "You're missing out on the best noise filtering.",
                cli_commands=["set rpm_filter_harmonics = 3"],
            ))
        elif not bidir_on:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title="Bidirectional DShot Disabled",
                description="Without bidir DShot, RPM filter is unavailable. Consider enabling it "
                           "for significantly better noise filtering.",
                explanation="Bidirectional DShot provides motor RPM telemetry which enables "
                           "RPM-based notch filters (the most effective filter in Betaflight). "
                           "Requires compatible ESC firmware (BLHeli_32, BLHeli_S with Bluejay, AM32).",
                cli_commands=["set dshot_bidir = ON"],
            ))

    def _analyze_dterm_filters(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze D-term filter settings."""
        # Get active profile's dterm filter settings
        active_profile = None
        for p in cli_data.pid_profiles:
            if p.index == cli_data.active_pid_profile:
                active_profile = p
                break

        if not active_profile:
            return

        # Dterm LPF1
        if active_profile.dterm_lpf1_dyn_min_hz > 0:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title=f"Dterm LPF1 Dynamic: {active_profile.dterm_lpf1_dyn_min_hz}-{active_profile.dterm_lpf1_dyn_max_hz}Hz",
                description="Dynamic D-term LPF1 adjusts based on noise levels.",
            ))

            if active_profile.dterm_lpf1_dyn_min_hz > 150:
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title="Dterm LPF1 Dynamic Min High",
                    description=f"Min={active_profile.dterm_lpf1_dyn_min_hz}Hz is high for D-term. "
                               f"D-term is very sensitive to noise. May cause hot motors.",
                    recommended_value="65-100Hz for min",
                ))

        # Dterm LPF2
        if active_profile.dterm_lpf2_static_hz > 0:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title=f"Dterm LPF2: {active_profile.dterm_lpf2_static_hz}Hz ({active_profile.dterm_lpf2_type})",
                description="D-term LPF2 provides additional noise filtering.",
            ))

            if active_profile.dterm_lpf2_static_hz > 300:
                report.add_finding(Finding(
                    category=Category.FILTER,
                    severity=Severity.WARNING,
                    title="Dterm LPF2 Very High",
                    description=f"Dterm LPF2 at {active_profile.dterm_lpf2_static_hz}Hz provides "
                               f"minimal D-term filtering.",
                ))

        # Dterm notch (usually should be off)
        if active_profile.dterm_notch_hz > 0:
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.WARNING,
                title=f"Dterm Static Notch Active ({active_profile.dterm_notch_hz}Hz)",
                description="Static D-term notch is rarely needed with modern Betaflight. "
                           "This adds latency to the D-term path.",
                explanation="With RPM filter and dynamic notch handling noise, a static D-term "
                           "notch is usually unnecessary overhead.",
                cli_commands=["set dterm_notch_hz = 0", "set dterm_notch_cutoff = 0"],
            ))

    def _analyze_simplified_filters(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze simplified filter tuning settings."""
        if cli_data.simplified_gyro_filter == "ON":
            mult = cli_data.simplified_gyro_filter_multiplier
            report.add_finding(Finding(
                category=Category.FILTER,
                severity=Severity.INFO,
                title=f"Simplified Gyro Filter: Multiplier {mult}%",
                description=f"Simplified gyro filter is ON with multiplier {mult}%. "
                           + ("Higher = less filtering = lower latency but more noise." if mult > 100
                              else "Lower = more filtering = higher latency but cleaner signal."
                              if mult < 100 else "Default multiplier level."),
                explanation="Simplified filter multiplier scales all gyro filter cutoffs proportionally. "
                           "100 = default, 150 = 50% higher cutoffs (less filter, less delay), "
                           "50 = 50% lower cutoffs (more filter, more delay).",
            ))

    def _analyze_filter_stack(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze the overall filter stack for efficiency."""
        rpm_on = (cli_data.dshot_bidir == "ON" and
                  int(cli_data.raw_settings.get("rpm_filter_harmonics", "3")) > 0)

        filter_count = 0
        filter_desc = []

        # Count active filters
        if cli_data.gyro_lpf1_static_hz > 0 or cli_data.gyro_lpf1_dyn_min_hz > 0:
            filter_count += 1
            filter_desc.append("Gyro LPF1")
        if cli_data.gyro_lpf2_static_hz > 0:
            filter_count += 1
            filter_desc.append("Gyro LPF2")
        if cli_data.gyro_notch1_hz > 0:
            filter_count += 1
            filter_desc.append("Gyro Notch1")
        if cli_data.gyro_notch2_hz > 0:
            filter_count += 1
            filter_desc.append("Gyro Notch2")
        if cli_data.dyn_notch_count > 0:
            filter_count += cli_data.dyn_notch_count
            filter_desc.append(f"Dynamic Notch x{cli_data.dyn_notch_count}")
        if rpm_on:
            harmonics = int(cli_data.raw_settings.get("rpm_filter_harmonics", "3"))
            filter_count += harmonics * 4  # per motor
            filter_desc.append(f"RPM Filter ({harmonics}h x 4 motors)")

        severity = Severity.INFO
        if filter_count > 20:
            severity = Severity.WARNING

        report.add_finding(Finding(
            category=Category.FILTER,
            severity=severity,
            title=f"Filter Stack: {filter_count} total filters",
            description=f"Active filters: {', '.join(filter_desc)}.",
            explanation="More filters = more latency but cleaner signal. "
                       "With RPM filter, you can often reduce other filters. "
                       "Typical optimized stack with RPM: RPM(3h) + DynNotch(1) + LPF1(dyn) + LPF2.",
        ))
