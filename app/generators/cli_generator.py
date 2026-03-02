"""
CLI Command Generator.

Collects all CLI commands from analysis findings and generates
a structured, ready-to-paste script for the Betaflight CLI.
"""
from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from ..knowledge.best_practices import AnalysisReport, Finding, Severity, Category


class CLIGenerator:
    """Generate ready-to-paste Betaflight CLI commands from analysis."""

    def generate(
        self,
        report: AnalysisReport,
        active_pid_profile: int = 0,
        active_rate_profile: int = 0,
        craft_name: str = "",
    ) -> str:
        """
        Generate a complete CLI command script.

        Returns a string that can be pasted directly into Betaflight CLI.
        """
        lines: List[str] = []

        # Header
        lines.append("#")
        lines.append(f"# Betaflight Tuning Recommendations")
        lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if craft_name:
            lines.append(f"# Craft: {craft_name}")
        lines.append(f"# Analysis Score: {report.overall_score}/100")
        lines.append(f"# Findings: {len(report.findings)} "
                     f"({report.error_count} errors, "
                     f"{report.warning_count} warnings)")
        lines.append("#")
        lines.append("")

        # Collect all findings with CLI commands
        commands_by_category = self._group_commands(report)

        if not commands_by_category:
            lines.append("# No CLI changes recommended - configuration looks good!")
            return "\n".join(lines)

        # Batch header
        lines.append("# ---- START OF RECOMMENDED CHANGES ----")
        lines.append("")

        # Profile selection
        lines.append(f"profile {active_pid_profile}")
        lines.append("")

        # PID commands
        if Category.PID in commands_by_category:
            lines.append("# === PID Tuning ===")
            for finding, cmds in commands_by_category[Category.PID]:
                lines.append(f"# {finding.title}")
                if finding.severity in (Severity.ERROR, Severity.CRITICAL):
                    lines.append(f"# [!] {finding.severity.value.upper()}: {finding.description[:100]}")
                for cmd in cmds:
                    lines.append(cmd)
            lines.append("")

        # Filter commands
        if Category.FILTER in commands_by_category:
            lines.append("# === Filters ===")
            for finding, cmds in commands_by_category[Category.FILTER]:
                lines.append(f"# {finding.title}")
                for cmd in cmds:
                    lines.append(cmd)
            lines.append("")

        # Rate profile
        lines.append(f"rateprofile {active_rate_profile}")
        lines.append("")

        # Rate commands
        if Category.RATE in commands_by_category:
            lines.append("# === Rates ===")
            for finding, cmds in commands_by_category[Category.RATE]:
                lines.append(f"# {finding.title}")
                for cmd in cmds:
                    lines.append(cmd)
            lines.append("")

        # Motor / General / Other
        for cat in (Category.MOTOR, Category.GENERAL, Category.PERFORMANCE,
                    Category.NOISE, Category.TRACKING):
            if cat in commands_by_category:
                lines.append(f"# === {cat.value} ===")
                for finding, cmds in commands_by_category[cat]:
                    lines.append(f"# {finding.title}")
                    for cmd in cmds:
                        lines.append(cmd)
                lines.append("")

        # Save
        lines.append("# ---- END OF RECOMMENDED CHANGES ----")
        lines.append("save")
        lines.append("")

        return "\n".join(lines)

    def generate_selective(
        self,
        report: AnalysisReport,
        selected_finding_ids: Optional[List[int]] = None,
        min_severity: Severity = Severity.INFO,
        active_pid_profile: int = 0,
        active_rate_profile: int = 0,
    ) -> str:
        """
        Generate CLI commands only for selected findings or above a severity.

        If *selected_finding_ids* is None, all findings at *min_severity* or
        above are included.
        """
        severity_order = {
            Severity.INFO: 0,
            Severity.WARNING: 1,
            Severity.ERROR: 2,
            Severity.CRITICAL: 3,
        }

        lines: List[str] = []
        lines.append(f"profile {active_pid_profile}")
        lines.append(f"rateprofile {active_rate_profile}")
        lines.append("")

        for idx, finding in enumerate(report.findings):
            if finding.cli_commands:
                if selected_finding_ids is not None:
                    if idx not in selected_finding_ids:
                        continue
                elif severity_order.get(finding.severity, 0) < severity_order.get(min_severity, 0):
                    continue

                lines.append(f"# {finding.title}")
                for cmd in finding.cli_commands:
                    lines.append(cmd)

        lines.append("")
        lines.append("save")
        return "\n".join(lines)

    def generate_diff(
        self,
        report: AnalysisReport,
    ) -> List[dict]:
        """
        Return a list of dicts suitable for JSON/template rendering.

        Each entry:
          {
            "category": "PID",
            "severity": "WARNING",
            "title": "...",
            "description": "...",
            "commands": ["set ..."],
            "index": 0,
          }
        """
        results = []
        for idx, finding in enumerate(report.findings):
            if finding.cli_commands:
                results.append({
                    "index": idx,
                    "category": finding.category.value,
                    "severity": finding.severity.value,
                    "title": finding.title,
                    "description": finding.description,
                    "explanation": finding.explanation or "",
                    "recommended_value": finding.recommended_value or "",
                    "commands": finding.cli_commands,
                })
        return results

    # ------------------------------------------------------------------
    @staticmethod
    def _group_commands(
        report: AnalysisReport,
    ) -> dict:
        """Group findings with CLI commands by category."""
        grouped: dict = {}
        for finding in report.findings:
            if finding.cli_commands:
                cat = finding.category
                if cat not in grouped:
                    grouped[cat] = []
                grouped[cat].append((finding, finding.cli_commands))
        return grouped
