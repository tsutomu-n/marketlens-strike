from __future__ import annotations

from html import escape
from typing import Any


REQUIRED_REPORT_SECTIONS = [
    "Run Summary",
    "Scope and Non-Scope",
    "Config Summary",
    "Data Manifest",
    "Data Quality",
    "Strategy Summary",
    "Performance Summary",
    "Benchmark Comparison",
    "Scenario Sensitivity",
    "Split Validation",
    "Parameter Sweep",
    "Trade List Summary",
    "Blocked Events",
    "Session / Market Status Breakdown",
    "Cost Breakdown",
    "Open Position at End",
    "Warnings / Known Limitations",
    "Artifact Paths",
]


def render_backtest_markdown(
    *,
    metrics: dict[str, Any],
    artifacts: dict[str, str],
    warnings: list[str] | None = None,
) -> str:
    lines = ["# Trade[XYZ] Backtest Report", ""]
    for section in REQUIRED_REPORT_SECTIONS:
        lines.extend([f"## {section}", ""])
        if section == "Performance Summary":
            for key, value in sorted(metrics.items()):
                lines.append(f"- `{key}`: {value}")
        elif section == "Warnings / Known Limitations":
            for warning in warnings or []:
                lines.append(f"- {warning}")
        elif section == "Artifact Paths":
            for key, value in sorted(artifacts.items()):
                lines.append(f"- `{key}`: `{value}`")
        else:
            lines.append("_v0.1 artifact-backed section._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_backtest_html(markdown: str) -> str:
    body_lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            body_lines.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body_lines.append(f"<p>{escape(line)}</p>")
        elif line:
            body_lines.append(f"<p>{escape(line)}</p>")
    return "<!doctype html>\n<html><body>\n" + "\n".join(body_lines) + "\n</body></html>\n"
