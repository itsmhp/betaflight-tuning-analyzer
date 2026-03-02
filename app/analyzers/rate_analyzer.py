"""
Rate Profile & RC Analyzer.
"""
from ..parsers.cli_parser import CLIData, RateProfile
from ..knowledge.best_practices import (
    AnalysisReport, Category, Finding, Severity,
)


class RateAnalyzer:
    """Analyze rate profiles and RC configuration."""

    # Max degree/s lookup tables for ACTUAL rates
    # ACTUAL: max_rate = rc_rate * 200 + srate * 200 * (1 - abs(1 - 2*expo/100))
    # Simplified: with ACTUAL rates, max_rate ≈ (rc_rate * 10) * (1 + srate/100) deg/s roughly

    def analyze_config(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze rate configuration."""
        active_rate = None
        for r in cli_data.rate_profiles:
            if r.index == cli_data.active_rate_profile:
                active_rate = r
                break

        if not active_rate:
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.ERROR,
                title="No Active Rate Profile Found",
                description="Could not determine the active rate profile.",
            ))
            return

        self._analyze_rate_values(active_rate, report)
        self._analyze_rc_smoothing(cli_data, report)
        self._analyze_throttle_curve(active_rate, report)
        self._analyze_deadband(cli_data, report)

    def _analyze_rate_values(self, rate: RateProfile, report: AnalysisReport):
        """Analyze rate values and calculate max rates."""
        report.add_finding(Finding(
            category=Category.RATE,
            severity=Severity.INFO,
            title=f"Rate Type: {rate.rates_type}",
            description=f"Using {rate.rates_type} rates system.",
        ))

        # Calculate approximate max rates for ACTUAL rates
        if rate.rates_type == "ACTUAL":
            axes = [
                ("Roll", rate.roll_rc_rate, rate.roll_srate, rate.roll_expo),
                ("Pitch", rate.pitch_rc_rate, rate.pitch_srate, rate.pitch_expo),
                ("Yaw", rate.yaw_rc_rate, rate.yaw_srate, rate.yaw_expo),
            ]
            for axis, rc_rate, srate, expo in axes:
                # ACTUAL rates formula:
                # center sensitivity = rc_rate * 10 deg/s
                # max rate (at full stick) = (rc_rate + srate) * 10 deg/s
                # expo affects the curve shape, not max rate
                center_sens_dps = rc_rate * 10
                max_rate_dps = (rc_rate + srate) * 10

                report.add_finding(Finding(
                    category=Category.RATE,
                    severity=Severity.INFO,
                    title=f"{axis} Rate: center {center_sens_dps}°/s, max {max_rate_dps}°/s",
                    description=f"{axis}: rc_rate={rc_rate} ({center_sens_dps}°/s center), "
                               f"srate={srate}, expo={expo} → max ~{max_rate_dps}°/s.",
                    explanation="ACTUAL rates: center sensitivity = rc_rate×10 deg/s, "
                               "max rate = (rc_rate + srate)×10 deg/s. Expo affects the transition curve.",
                ))

                if max_rate_dps < 400:
                    report.add_finding(Finding(
                        category=Category.RATE,
                        severity=Severity.WARNING,
                        title=f"Low {axis} Max Rate (~{max_rate_dps} deg/s)",
                        description=f"Maximum rotation rate on {axis} is approximately "
                                   f"{max_rate_dps} deg/s. This may feel slow for freestyle.",
                        explanation="For freestyle, 600-900 deg/s is common. For racing, 800-1200. "
                                   "For cinematic, 200-500 is fine.",
                    ))
                elif max_rate_dps > 1400:
                    report.add_finding(Finding(
                        category=Category.RATE,
                        severity=Severity.INFO,
                        title=f"High {axis} Max Rate (~{max_rate_dps} deg/s)",
                        description=f"Very high max rate. Fine for racing but may make "
                                   f"precise movements harder.",
                    ))

            # Rate limit check
            for axis_name, limit in [("Roll", rate.roll_rate_limit),
                                      ("Pitch", rate.pitch_rate_limit),
                                      ("Yaw", rate.yaw_rate_limit)]:
                if limit < 1998:
                    report.add_finding(Finding(
                        category=Category.RATE,
                        severity=Severity.INFO,
                        title=f"{axis_name} Rate Limit: {limit} deg/s",
                        description="Rate limit is set below default 1998. This caps the maximum "
                                   "rotation speed regardless of rate settings.",
                    ))

        # Expo analysis
        if rate.rates_type == "ACTUAL":
            for axis, expo in [("Roll", rate.roll_expo),
                               ("Pitch", rate.pitch_expo),
                               ("Yaw", rate.yaw_expo)]:
                if expo > 60:
                    report.add_finding(Finding(
                        category=Category.RATE,
                        severity=Severity.INFO,
                        title=f"High {axis} Expo ({expo})",
                        description="High expo creates very non-linear response. Center stick "
                                   "is very slow, endpoints are very fast. This can reduce precision.",
                    ))

    def _analyze_rc_smoothing(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze RC smoothing settings."""
        if cli_data.rc_smoothing != "ON":
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.WARNING,
                title="RC Smoothing Disabled",
                description="RC smoothing is off. This can cause jittery motor output due to "
                           "discrete RC steps.",
                explanation="RC smoothing interpolates between RC data points for smoother "
                           "motor output. Should almost always be ON.",
                cli_commands=["set rc_smoothing = ON"],
            ))

        # Auto-factor
        if cli_data.rc_smoothing_auto_factor > 0:
            if cli_data.rc_smoothing_auto_factor > 50:
                report.add_finding(Finding(
                    category=Category.RATE,
                    severity=Severity.INFO,
                    title=f"RC Smoothing Factor: {cli_data.rc_smoothing_auto_factor}",
                    description="High auto-factor = less smoothing = lower latency but may show "
                               "RC steps in motor output.",
                    explanation="Default 30 balances smoothness and latency well. "
                               "Higher values for faster link rates (>250Hz). "
                               "Lower for slow links (50Hz PWM).",
                ))

    def _analyze_throttle_curve(self, rate: RateProfile, report: AnalysisReport):
        """Analyze throttle curve."""
        if rate.thr_mid != 50 or rate.thr_expo != 0:
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.INFO,
                title=f"Custom Throttle Curve (mid={rate.thr_mid}, expo={rate.thr_expo})",
                description="Non-default throttle curve. "
                           + (f"thr_mid={rate.thr_mid}% shifts the midpoint. " if rate.thr_mid != 50 else "")
                           + (f"thr_expo={rate.thr_expo} adds curve. " if rate.thr_expo != 0 else ""),
                explanation="Throttle curve can make the throttle feel more linear or give "
                           "more control at certain throttle ranges. thr_mid=50, expo=0 is linear.",
            ))

        # Throttle limit
        if rate.throttle_limit_type != "OFF":
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.INFO,
                title=f"Throttle Limit: {rate.throttle_limit_type} at {rate.throttle_limit_percent}%",
                description="Throttle output is limited. This reduces max power available.",
            ))

    def _analyze_deadband(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze deadband settings."""
        if cli_data.deadband > 5:
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.WARNING,
                title=f"Large Deadband ({cli_data.deadband})",
                description="Large deadband creates a dead zone around stick center. "
                           "This can make the quad feel unresponsive.",
                recommended_value="0 (with modern RC link)",
            ))
        if cli_data.yaw_deadband > 5:
            report.add_finding(Finding(
                category=Category.RATE,
                severity=Severity.WARNING,
                title=f"Large Yaw Deadband ({cli_data.yaw_deadband})",
                description="Large yaw deadband. May cause unresponsive yaw.",
                recommended_value="0",
            ))
