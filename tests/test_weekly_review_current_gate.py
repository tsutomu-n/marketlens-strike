from __future__ import annotations

from pathlib import Path

from sis.reports.weekly_review_current_gate import current_gate_section_lines


def test_current_gate_section_lines_formats_populated_summary() -> None:
    assert current_gate_section_lines(
        Path("data/ops/phase_gate_review_summary.json"),
        {
            "decision": "READ_ONLY_GO",
            "strict_validation_passed": True,
            "checked_files": 12,
            "diagnostics_symbols": ["SP500", "XYZ100", 7, "NVDA"],
        },
        [],
    ) == [
        "## Current Trade[XYZ] Gate Snapshot",
        "",
        "- source: data/ops/phase_gate_review_summary.json",
        "- decision: READ_ONLY_GO",
        "- strict_validation_passed: True",
        "- phase_gate_checked_files: 12",
        "- diagnostics_symbols: SP500, XYZ100, NVDA",
        "",
    ]


def test_current_gate_section_lines_formats_unavailable_summary() -> None:
    assert current_gate_section_lines(
        Path("data/ops/phase_gate_review_summary.json"),
        {},
        [],
    ) == [
        "## Current Trade[XYZ] Gate Snapshot",
        "",
        "- source: data/ops/phase_gate_review_summary.json",
        "- status: unavailable",
        "",
    ]


def test_current_gate_section_lines_adds_backtest_symbol_scope() -> None:
    assert current_gate_section_lines(
        Path("data/ops/phase_gate_review_summary.json"),
        {"decision": "READ_ONLY_GO"},
        ["QQQ", "SPY"],
    ) == [
        "## Current Trade[XYZ] Gate Snapshot",
        "",
        "- source: data/ops/phase_gate_review_summary.json",
        "- decision: READ_ONLY_GO",
        "- strict_validation_passed: None",
        "- phase_gate_checked_files: None",
        "- backtest_symbol_scope: historical_or_legacy_symbols",
        (
            "- interpretation: Backtest Metrics Snapshot is a historical/backtest input "
            "and is not the current Trade[XYZ] symbol universe."
        ),
        "",
    ]
