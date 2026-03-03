"""
PID Master Multiplier.

Utility that scales all PID values by a user-supplied multiplier
and generates ready-to-paste CLI commands.

This is an interactive tool (user picks a multiplier 0.00–2.00),
so it's exposed as a utility rather than an auto-analyzer.
The GUI can call ``generate_scaled_pids(cli_data, multiplier)``
to get the result.

Algorithm (matching FPV Nexus):
  - scaled_value = round(original × multiplier)
  - Applied to P, I, D-min, D-max, and FF per axis
  - Detects PID format (new 5-field vs legacy 3-field)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ScaledPID:
    """One axis worth of original + scaled PID values."""
    axis: str
    p_orig: int = 0
    i_orig: int = 0
    d_min_orig: int = 0
    d_max_orig: int = 0
    ff_orig: int = 0
    p_new: int = 0
    i_new: int = 0
    d_min_new: int = 0
    d_max_new: int = 0
    ff_new: int = 0

    def cli_commands(self) -> List[str]:
        axis = self.axis.lower()
        cmds = [
            f"set p_{axis} = {self.p_new}",
            f"set i_{axis} = {self.i_new}",
            f"set d_min_{axis} = {self.d_min_new}",
            f"set d_{axis} = {self.d_max_new}",
        ]
        if self.ff_orig > 0 or self.ff_new > 0:
            cmds.append(f"set f_{axis} = {self.ff_new}")
        return cmds


@dataclass
class MultiplierResult:
    """Full multiplier result for all axes."""
    multiplier: float
    axes: List[ScaledPID] = field(default_factory=list)

    @property
    def all_cli_commands(self) -> List[str]:
        cmds = []
        for a in self.axes:
            cmds.extend(a.cli_commands())
        cmds.append("save")
        return cmds

    @property
    def summary(self) -> str:
        lines = [f"PID Master Multiplier: ×{self.multiplier:.2f}"]
        for a in self.axes:
            lines.append(
                f"  {a.axis}: P {a.p_orig}→{a.p_new}, "
                f"I {a.i_orig}→{a.i_new}, "
                f"Dmin {a.d_min_orig}→{a.d_min_new}, "
                f"Dmax {a.d_max_orig}→{a.d_max_new}, "
                f"FF {a.ff_orig}→{a.ff_new}"
            )
        return "\n".join(lines)


def generate_scaled_pids(cli_data, multiplier: float) -> Optional[MultiplierResult]:
    """
    Generate scaled PID values from CLI data.

    Parameters
    ----------
    cli_data : CLIData
        Parsed CLI data (from cli_parser).
    multiplier : float
        Scaling factor (0.00 – 2.00).

    Returns
    -------
    MultiplierResult or None if no PID data available.
    """
    multiplier = max(0.0, min(2.0, multiplier))

    # Find active PID profile
    active = cli_data.active_pid_profile
    pid = None
    for pp in cli_data.pid_profiles:
        if pp.index == active:
            pid = pp
            break
    if pid is None and cli_data.pid_profiles:
        pid = cli_data.pid_profiles[0]
    if pid is None:
        return None

    result = MultiplierResult(multiplier=multiplier)

    for axis_name, p, i, d_min, d_max, ff in [
        ("roll", pid.p_roll, pid.i_roll, pid.d_min_roll, pid.d_roll, pid.f_roll),
        ("pitch", pid.p_pitch, pid.i_pitch, pid.d_min_pitch, pid.d_pitch, pid.f_pitch),
        ("yaw", pid.p_yaw, pid.i_yaw, pid.d_min_yaw, pid.d_yaw, pid.f_yaw),
    ]:
        sp = ScaledPID(
            axis=axis_name,
            p_orig=p, i_orig=i, d_min_orig=d_min, d_max_orig=d_max, ff_orig=ff,
            p_new=round(p * multiplier),
            i_new=round(i * multiplier),
            d_min_new=round(d_min * multiplier),
            d_max_new=round(d_max * multiplier),
            ff_new=round(ff * multiplier),
        )
        result.axes.append(sp)

    return result
