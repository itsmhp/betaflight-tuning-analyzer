"""
PID Tuning Analyzer.

Analyzes PID configuration from CLI dump and optionally
from blackbox flight data to provide tuning recommendations.
"""
from typing import Optional

from ..parsers.cli_parser import CLIData, PIDProfile
from ..knowledge.best_practices import (
    AnalysisReport, BestPractices, Category, Finding, Severity,
)


class PIDAnalyzer:
    """Analyze PID tuning configuration and performance."""

    def analyze_config(self, cli_data: CLIData, report: AnalysisReport):
        """Analyze PID configuration from CLI dump."""
        # Get active PID profile
        active_profile = None
        for p in cli_data.pid_profiles:
            if p.index == cli_data.active_pid_profile:
                active_profile = p
                break

        if not active_profile:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.ERROR,
                title="No Active PID Profile Found",
                description="Could not determine the active PID profile from CLI dump.",
            ))
            return

        self._analyze_pid_values(active_profile, report)
        self._analyze_d_min_setup(active_profile, report)
        self._analyze_feedforward(active_profile, cli_data, report)
        self._analyze_iterm(active_profile, report)
        self._analyze_anti_gravity(active_profile, report)
        self._analyze_tpa(active_profile, report)
        self._analyze_simplified_tuning(active_profile, report)
        self._analyze_dynamic_idle(active_profile, cli_data, report)
        self._analyze_vbat_sag(active_profile, report)
        self._analyze_throttle_boost(active_profile, report)

    def _analyze_pid_values(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze raw PID values."""
        axes = [
            ("Roll", profile.p_roll, profile.i_roll, profile.d_roll, profile.f_roll),
            ("Pitch", profile.p_pitch, profile.i_pitch, profile.d_pitch, profile.f_pitch),
            ("Yaw", profile.p_yaw, profile.i_yaw, profile.d_yaw, profile.f_yaw),
        ]

        for axis, p, i, d, f in axes:
            # P analysis
            if p < 25:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.WARNING,
                    title=f"Low {axis} P-term ({p})",
                    description=f"{axis} P={p} is quite low. The quad may feel sluggish "
                               f"and have poor attitude holding.",
                    explanation="P-term provides the main correction force. Too low = slow response.",
                    recommended_value="40-70 for most quads",
                ))
            elif p > 85:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.WARNING,
                    title=f"High {axis} P-term ({p})",
                    description=f"{axis} P={p} is very high. May cause oscillation, "
                               f"especially at high throttle.",
                    explanation="Very high P causes fast oscillation. Check blackbox for "
                               "high-frequency oscillation or listen for motor hum.",
                    recommended_value="40-70 for most quads",
                ))

            # I analysis
            if i < 40 and axis != "Yaw":
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.WARNING,
                    title=f"Low {axis} I-term ({i})",
                    description=f"{axis} I={i} is low. The quad may drift or not hold "
                               f"attitude during forward flight.",
                    explanation="I-term corrects persistent errors. Low I = drift and "
                               "inability to hold angle against wind or prop wash.",
                    recommended_value="80-120 for most quads",
                ))
            elif i > 160:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.WARNING,
                    title=f"High {axis} I-term ({i})",
                    description=f"{axis} I={i} is very high. Can cause slow oscillation "
                               f"(bounceback) after moves.",
                    explanation="Excessive I-term causes the quad to overshoot corrections, "
                               "leading to a slow oscillation or wobble after maneuvers.",
                    recommended_value="80-120 for most quads",
                ))

            # D analysis (skip yaw D which is intentionally 0 in most setups)
            if axis != "Yaw":
                if d < 20 and d > 0:
                    report.add_finding(Finding(
                        category=Category.PID,
                        severity=Severity.WARNING,
                        title=f"Low {axis} D-term ({d})",
                        description=f"{axis} D={d} is low. May not adequately dampen "
                                   f"oscillations and propwash.",
                        explanation="D-term dampens P oscillations and helps with propwash handling. "
                                   "Too low = visible propwash oscillation during descents.",
                        recommended_value="35-55 for most quads",
                    ))
                elif d > 65:
                    report.add_finding(Finding(
                        category=Category.PID,
                        severity=Severity.WARNING,
                        title=f"High {axis} D-term ({d})",
                        description=f"{axis} D={d} is quite high. This amplifies noise "
                                   f"and can overheat motors.",
                        explanation="D-term amplifies noise. High D = hot motors, audible noise. "
                                   "The benefit of high D (propwash control) has diminishing returns "
                                   "beyond a certain point.",
                        recommended_value="35-55 for most quads",
                    ))

        # P/I ratio check
        for axis, p, i, d, f in axes:
            if i > 0 and p > 0:
                pi_ratio = p / i
                if pi_ratio > 1.2:
                    report.add_finding(Finding(
                        category=Category.PID,
                        severity=Severity.INFO,
                        title=f"{axis} P/I Ratio High ({pi_ratio:.1f})",
                        description=f"{axis} P/I ratio is {pi_ratio:.1f}. Higher P relative to I "
                                   f"gives snappier response but may not hold attitude well.",
                        explanation="Typical P/I ratio is around 0.5-0.7 in BF 4.5. "
                                   "Higher ratio = more responsive but less stable.",
                    ))

        # Pitch vs Roll symmetry check
        if abs(profile.p_roll - profile.p_pitch) > 15:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title="Asymmetric Roll/Pitch P-terms",
                description=f"Roll P={profile.p_roll}, Pitch P={profile.p_pitch}. "
                           f"Significant asymmetry between axes.",
                explanation="Some asymmetry is normal since quads are usually not perfectly "
                           "symmetrical (camera tilts the CG). But large differences suggest "
                           "either intentional tuning for a specific setup or potential issues.",
            ))

    def _analyze_d_min_setup(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze D_min / D_max setup."""
        # D_min should be lower than D_max (d_roll, d_pitch)
        if profile.d_min_roll > profile.d_roll:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.ERROR,
                title="D_min > D_max on Roll",
                description=f"d_min_roll ({profile.d_min_roll}) > d_roll ({profile.d_roll}). "
                           f"d_min must be <= D value.",
                explanation="D_min sets the minimum D-term during smooth flight. "
                           "D_max (the d_roll/d_pitch value) is used during fast maneuvers. "
                           "D_min must not exceed D_max.",
                cli_commands=[f"set d_min_roll = {min(profile.d_min_roll, profile.d_roll)}"],
            ))

        if profile.d_min_pitch > profile.d_pitch:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.ERROR,
                title="D_min > D_max on Pitch",
                description=f"d_min_pitch ({profile.d_min_pitch}) > d_pitch ({profile.d_pitch}). "
                           f"d_min must be <= D value.",
                cli_commands=[f"set d_min_pitch = {min(profile.d_min_pitch, profile.d_pitch)}"],
            ))

        # D_min gap analysis
        if profile.d_roll > 0 and profile.d_min_roll > 0:
            d_gap_roll = profile.d_roll - profile.d_min_roll
            if d_gap_roll > 25:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.INFO,
                    title="Large D_min/D_max Gap on Roll",
                    description=f"D_min={profile.d_min_roll} to D_max={profile.d_roll} "
                               f"(gap={d_gap_roll}). Large gap means very different D behavior "
                               f"between calm and aggressive flying.",
                    explanation="A large gap gives low noise during cruising (low D) but "
                               "strong damping during fast moves (high D). Gap of 10-15 is typical.",
                ))
            elif d_gap_roll == 0:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.INFO,
                    title="D_min Equals D_max on Roll",
                    description=f"d_min_roll={profile.d_min_roll} equals d_roll={profile.d_roll}. "
                               f"D-term is constant regardless of stick activity.",
                    explanation="Setting d_min = d_max disables the dynamic D feature. "
                               "This is fine if your filters handle noise well, but you could "
                               "benefit from a lower d_min (e.g., d_min = d_max - 10) for cooler motors.",
                ))

        # D_max_gain check
        if profile.d_max_gain == 0:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title="D_max Gain Disabled",
                description="d_max_gain=0 means D_min/D_max dynamic behavior is disabled.",
                explanation="d_max_gain controls how quickly D rises from d_min to d_max "
                           "during stick inputs. 0 = always use d_min. Default 37 is recommended.",
                recommended_value="37",
                cli_commands=["set d_max_gain = 37"],
            ))

    def _analyze_feedforward(self, profile: PIDProfile, cli_data: CLIData,
                              report: AnalysisReport):
        """Analyze feedforward setup."""
        has_ff = any([profile.f_roll, profile.f_pitch, profile.f_yaw])

        if not has_ff:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title="Feedforward Disabled",
                description="Feedforward (F-term) is 0 on all axes. This is fine for "
                           "cinematic/cinewhoop flying but may reduce stick response for freestyle/racing.",
                explanation="Feedforward predicts the desired response from stick input, "
                           "reducing latency. It's most useful for freestyle and racing. "
                           "For cinematic flying, keeping it off can give smoother video.",
            ))
        else:
            # Check feedforward averaging
            if profile.feedforward_averaging == "OFF" and has_ff:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.INFO,
                    title="Feedforward Averaging Off",
                    description="Feedforward averaging is OFF. Consider 2_POINT for smoother FF response.",
                    explanation="Feedforward averaging smooths jittery RC input that creates "
                               "spiky feedforward. 2_POINT is the recommended default.",
                    recommended_value="2_POINT",
                    cli_commands=["set feedforward_averaging = 2_POINT"],
                ))

            # Jitter factor
            if profile.feedforward_jitter_factor > 15:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.INFO,
                    title=f"High Feedforward Jitter Factor ({profile.feedforward_jitter_factor})",
                    description="High jitter factor suppresses feedforward during steady sticks "
                               "but may reduce responsiveness.",
                    explanation="Jitter factor determines how much feedforward is suppressed "
                               "when stick input is small/jittery. 7-10 is typical.",
                    recommended_value="7-10",
                ))

    def _analyze_iterm(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze I-term configuration."""
        # I-term relax
        if profile.iterm_relax == "OFF":
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.WARNING,
                title="I-term Relax Disabled",
                description="I-term relax is OFF. This can cause I-term buildup during "
                           "fast maneuvers, leading to bounceback.",
                explanation="I-term relax reduces I-term accumulation during rapid stick movements, "
                           "preventing the 'bounceback' effect after flips and rolls.",
                recommended_value="RP (Roll & Pitch)",
                cli_commands=["set iterm_relax = RP"],
            ))

        # I-term relax cutoff
        if profile.iterm_relax_cutoff < 10:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title=f"Low I-term Relax Cutoff ({profile.iterm_relax_cutoff})",
                description="Very low cutoff means I-term relax activates on very slow movements too.",
                explanation="Lower cutoff = more aggressive I-term relaxation. "
                           "Default 15 works well for most setups. Lower values (10-12) "
                           "help if you see bounceback.",
            ))

    def _analyze_anti_gravity(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze anti-gravity setup."""
        if profile.anti_gravity_gain < 30:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title=f"Low Anti-Gravity Gain ({profile.anti_gravity_gain})",
                description="Low anti-gravity gain means less I-term boost during throttle changes. "
                           "The quad may wobble during quick throttle punches.",
                explanation="Anti-gravity boosts I-term during throttle transitions to maintain "
                           "stability. Default is 80. Lower values = less correction.",
                recommended_value="65-100",
            ))

    def _analyze_tpa(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze TPA (Throttle PID Attenuation) setup."""
        if profile.tpa_rate == 0:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title="TPA Disabled",
                description="TPA rate is 0. PID values are constant across all throttle positions.",
                explanation="TPA reduces D-term (or PID) at high throttle to prevent oscillation. "
                           "Most quads benefit from TPA since motors produce more noise at high RPM. "
                           "Default is 65% starting at 1350.",
                recommended_value="tpa_rate=65, tpa_breakpoint=1350",
                cli_commands=[
                    "set tpa_rate = 65",
                    "set tpa_breakpoint = 1350",
                ],
            ))

        if profile.tpa_breakpoint < 1100:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.WARNING,
                title=f"Very Low TPA Breakpoint ({profile.tpa_breakpoint})",
                description="TPA starts reducing PID very early. This can make the quad feel "
                           "mushy at mid-throttle.",
                recommended_value="1250-1400",
            ))

    def _analyze_simplified_tuning(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze simplified tuning setup."""
        if profile.simplified_pids_mode == "OFF":
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title="Simplified PID Tuning Disabled",
                description="Using manual PID values (simplified tuning is OFF). "
                           "This allows full control but means you've set each PID value manually.",
                explanation="Simplified tuning uses multiplier sliders to adjust PIDs proportionally. "
                           "It's great for quick tuning. Manual mode gives more control but requires "
                           "more knowledge. Both approaches are valid.",
            ))
        elif profile.simplified_pids_mode in ("RPY", "RP"):
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title=f"Simplified Tuning: {profile.simplified_pids_mode}",
                description=f"Master multiplier: {profile.simplified_master_multiplier}, "
                           f"PI gain: {profile.simplified_pi_gain}, "
                           f"D gain: {profile.simplified_d_gain}, "
                           f"FF gain: {profile.simplified_feedforward_gain}",
                explanation="Simplified tuning lets you adjust all PIDs proportionally "
                           "using these multiplier sliders.",
            ))

    def _analyze_dynamic_idle(self, profile: PIDProfile, cli_data: CLIData,
                               report: AnalysisReport):
        """Analyze dynamic idle configuration."""
        if profile.dyn_idle_min_rpm == 0:
            # Check if DShot bidir is on (required for dynamic idle)
            if cli_data.dshot_bidir == "ON":
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.WARNING,
                    title="Dynamic Idle Disabled (DShot Bidir Available)",
                    description="You have bidirectional DShot enabled but dynamic idle is off. "
                               "Dynamic idle significantly improves low-throttle performance and "
                               "prevents desync.",
                    explanation="Dynamic idle uses RPM telemetry to keep motors above a minimum RPM "
                               "instead of using a fixed idle value. This prevents motor desync on "
                               "low-throttle maneuvers and improves propwash handling.",
                    recommended_value="dyn_idle_min_rpm = 20-40 (depends on motor/prop combo)",
                    cli_commands=[
                        "set dyn_idle_min_rpm = 25",
                        "set dyn_idle_p_gain = 50",
                        "set dyn_idle_i_gain = 50",
                        "set dyn_idle_d_gain = 50",
                    ],
                ))
            else:
                report.add_finding(Finding(
                    category=Category.PID,
                    severity=Severity.INFO,
                    title="Dynamic Idle Unavailable",
                    description="Dynamic idle requires bidirectional DShot for RPM telemetry. "
                               "Consider enabling dshot_bidir for better performance.",
                ))

    def _analyze_vbat_sag(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze Vbat sag compensation."""
        if profile.vbat_sag_compensation == 0:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title="Vbat Sag Compensation Off",
                description="Vbat sag compensation is disabled. Flight feel may change "
                           "as battery voltage drops.",
                explanation="Vbat sag compensation boosts PID output as battery voltage drops "
                           "to maintain consistent flight feel throughout the pack. "
                           "Values of 50-100 are common. Start with 0 if motors run hot.",
            ))

    def _analyze_throttle_boost(self, profile: PIDProfile, report: AnalysisReport):
        """Analyze throttle boost configuration."""
        if profile.throttle_boost > 10:
            report.add_finding(Finding(
                category=Category.PID,
                severity=Severity.INFO,
                title=f"High Throttle Boost ({profile.throttle_boost})",
                description="Throttle boost amplifies rapid throttle changes. "
                           "Very high values can cause aggressive/twitchy throttle.",
                recommended_value="5 (default)",
            ))
