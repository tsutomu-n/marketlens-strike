from __future__ import annotations

from pathlib import Path

from sis.reports.execution_adapter_status_writer import write_execution_adapter_status_report
from sis.storage.jsonl_store import read_json


def test_write_execution_adapter_status_report_preserves_section_order(
    tmp_path: Path,
) -> None:
    out_path = tmp_path / "execution_adapter.md"
    summary_path = tmp_path / "execution_adapter_summary.json"
    summary = {
        "quick_navigation": {"current": "data/reports/current.md"},
        "related_reports": {"next": "data/reports/next.md"},
        "status": "ok",
    }

    text = write_execution_adapter_status_report(
        title="Execution Adapter Status",
        summary=summary,
        detail_lines=["- status: ok"],
        out_path=out_path,
        summary_path=summary_path,
    )

    assert text.index("## Quick Navigation") < text.index("## Related Reports")
    assert text.index("## Related Reports") < text.index("## Overview")
    assert text.index("## Overview") < text.index("## Recommended Read Order")
    assert "- current: data/reports/current.md" in text
    assert "- next: data/reports/next.md" in text
    assert "- status: ok" in text
    assert out_path.read_text(encoding="utf-8") == text
    assert read_json(summary_path) == summary


def test_write_execution_adapter_status_report_omits_empty_navigation() -> None:
    text = write_execution_adapter_status_report(
        title="Execution Adapter Status",
        summary={},
        detail_lines=["- status: missing"],
    )

    assert "## Quick Navigation" not in text
    assert "## Related Reports" not in text
    assert "## Overview" in text
    assert "- status: missing" in text
    assert "## Recommended Read Order" in text
