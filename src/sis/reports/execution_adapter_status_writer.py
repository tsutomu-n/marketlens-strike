from __future__ import annotations

from pathlib import Path
from typing import Mapping

from sis.reports.execution_adapter_status_navigation import (
    execution_adapter_recommended_read_order as _recommended_read_order,
)
from sis.storage.jsonl_store import write_json


def write_execution_adapter_status_report(
    *,
    title: str,
    summary: Mapping[str, object],
    detail_lines: list[str],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    quick_navigation = summary.get("quick_navigation")
    related_reports = summary.get("related_reports")
    lines = [f"# {title}", ""]
    if isinstance(quick_navigation, dict) and quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if isinstance(related_reports, dict) and related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(["## Overview", "", *detail_lines, "", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in _recommended_read_order())
    lines.append("")
    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
