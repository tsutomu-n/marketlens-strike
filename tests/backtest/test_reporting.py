from __future__ import annotations

from pathlib import Path

from sis.backtest.reporting import bool_line, kv_line, write_markdown_report


def test_write_markdown_report_preserves_existing_line_join_format(tmp_path: Path) -> None:
    path = tmp_path / "reports" / "report.md"

    result = write_markdown_report(path, ["# Title", "", "- status: pass"])

    assert result == path
    assert path.read_text(encoding="utf-8") == "# Title\n\n- status: pass\n"


def test_report_line_helpers_match_existing_plain_format() -> None:
    assert bool_line("permits_live_order", False) == "- permits_live_order: false"
    assert bool_line("paper_only", True) == "- paper_only: true"
    assert kv_line("status", "pass") == "- status: pass"
    assert kv_line("count", 3) == "- count: 3"
