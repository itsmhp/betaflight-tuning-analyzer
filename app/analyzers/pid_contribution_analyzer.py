"""
PID Contribution Analyzer.

Analyses the relative contributions of P, D, and FeedForward
terms across all axes, identifying dominant terms and imbalances.

Algorithm (improved over FPV Nexus):
  1. Sum absolute values of P, D, F per axis
  2. Compute P/D/F ratio (I-term excluded from ratio, shown separately)
  3. Highlight high D-term contributions
  4. Detect axis-to-axis PID ratio imbalance
  5. Suggest PID adjustments

Enhanced over FPV Nexus with:
  - Axis imbalance detection and cross-axis comparison
  - D-term dominance warnings with CLI suggestions
  - I-term severity tracking (separate but visible)
  - Per-axis PID balance radar data for charting
"""
from __future__ import annotations

from typing import Dict, Any, Optional

import numpy as np

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


class PIDContributionAnalyzer:
    """Analyse P/D/F/I contributions and force balance."""

    def analyze_flight_data(
        self,
        flight_data,
        bbl_header,
        report: AnalysisReport,
    ) -> None:
        axis_names = ["Roll", "Pitch", "Yaw"]
        axis_results: Dict[str, Dict[str, Any]] = {}

        for axis_idx, axis_name in enumerate(axis_names):
            p = flight_data.pid_p[axis_idx] if axis_idx < len(flight_data.pid_p) else None
            i = flight_data.pid_i[axis_idx] if axis_idx < len(flight_data.pid_i) else None
            d = flight_data.pid_d[axis_idx] if axis_idx < len(flight_data.pid_d) else None
            f = flight_data.pid_f[axis_idx] if axis_idx < len(flight_data.pid_f) else None

            sums = {}
            if p is not None and len(p) > 100:
                sums["P"] = float(np.sum(np.abs(p.astype(np.float64))))
            if d is not None and len(d) > 100:
                sums["D"] = float(np.sum(np.abs(d.astype(np.float64))))
            if f is not None and len(f) > 100:
                sums["F"] = float(np.sum(np.abs(f.astype(np.float64))))

            i_sum = 0.0
            if i is not None and len(i) > 100:
                i_sum = float(np.sum(np.abs(i.astype(np.float64))))

            # Need at least P and one of D/F to compute ratio
            total_pdf = sum(sums.values())
            if total_pdf < 1:
                continue

            ratios = {k: round(v / total_pdf * 100, 1) for k, v in sums.items()}

            axis_results[axis_name] = {
                "sums": {k: round(v, 0) for k, v in sums.items()},
                "ratios": ratios,
                "i_sum": round(i_sum, 0),
                "i_pct_of_total": round(i_sum / (total_pdf + i_sum) * 100, 1) if (total_pdf + i_sum) > 0 else 0,
                "total_pdf": round(total_pdf, 0),
            }

        if not axis_results:
            return

        # --- Analysis ---
        recs = []
        sev = Severity.INFO

        for axis_name, r in axis_results.items():
            ratios = r["ratios"]

            # D-term dominance checks (Nexus thresholds)
            d_pct = ratios.get("D", 0)
            if d_pct > 40:
                recs.append(
                    f"{axis_name}: D-term is dominant ({d_pct:.0f}% of P/D/F). "
                    "This may indicate oscillation-fighting or excessive D gain. "
                    "Consider reducing D or adding D-term filtering."
                )
                sev = Severity.WARNING
            elif d_pct > 30:
                recs.append(
                    f"{axis_name}: D-term is elevated ({d_pct:.0f}%). Monitor for hot motors."
                )

            # Low FF contribution
            f_pct = ratios.get("F", 0)
            if f_pct < 5 and "F" in ratios:
                recs.append(
                    f"{axis_name}: FeedForward contribution is very low ({f_pct:.0f}%). "
                    "Consider increasing feedforward for sharper stick response."
                )

            # High I-term
            if r["i_pct_of_total"] > 30:
                recs.append(
                    f"{axis_name}: I-term is {r['i_pct_of_total']:.0f}% of total output. "
                    "Check for sustained forces (CG offset, wind) or reduce iterm_relax cutoff."
                )

        # Cross-axis comparison
        if len(axis_results) >= 2:
            d_pcts = {a: r["ratios"].get("D", 0) for a, r in axis_results.items()}
            if d_pcts:
                max_d_axis = max(d_pcts, key=d_pcts.get)
                min_d_axis = min(d_pcts, key=d_pcts.get)
                if d_pcts[max_d_axis] > 1.5 * max(d_pcts[min_d_axis], 1):
                    recs.append(
                        f"D-term imbalance: {max_d_axis} ({d_pcts[max_d_axis]:.0f}%) vs "
                        f"{min_d_axis} ({d_pcts[min_d_axis]:.0f}%). "
                        "Consider per-axis D tuning."
                    )

        # Summary description
        desc_parts = []
        for axis_name, r in axis_results.items():
            ratios = r["ratios"]
            parts = [f"{k}:{v:.0f}%" for k, v in sorted(ratios.items())]
            desc_parts.append(f"{axis_name} [{'/'.join(parts)}]")
        desc = "PID Contributions: " + " | ".join(desc_parts)

        data = {
            "type": "pid_contribution",
            "axis_results": axis_results,
            "recommendations": recs,
        }

        report.add_finding(Finding(
            category=Category.PID,
            title="PID Contribution Analysis",
            severity=sev,
            description=desc,
            explanation="\n".join(recs) if recs else "PID contributions are well balanced.",
            data=data,
        ))
