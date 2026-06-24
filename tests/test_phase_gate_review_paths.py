from __future__ import annotations

from pathlib import Path

from sis.reports.phase_gate_review_paths import (
    latest_path,
    quick_navigation,
    read_only_collector_gate,
    related_reports,
    required_artifact_paths,
    reports_dir,
)


def test_reports_dir_uses_data_reports_sibling() -> None:
    assert reports_dir(Path("data")) == Path("data/reports")


def test_quick_navigation_filters_missing_and_non_string_values() -> None:
    summary = {
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "unexpected_non_string": 123,
    }

    assert quick_navigation(summary, Path("data")) == {
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
    }


def test_related_reports_includes_expected_phase_gate_order() -> None:
    summary = {
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
    }

    assert related_reports(summary, Path("data")) == {
        "phase_gate_review_report": "data/reports/phase_gate_review.md",
        "operations_dashboard_report": "data/reports/operations_dashboard.md",
        "current_state_index_report": "data/reports/current_state_index.md",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "paper_operations_runbook_report": "data/reports/paper_operations_runbook.md",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "go_no_go_report": "data/research/go_no_go_report.md",
        "paper_vs_backtest_comparison_report": "data/reports/paper_vs_backtest_comparison.md",
    }


def test_latest_path_uses_sorted_match_order(tmp_path: Path) -> None:
    root = tmp_path / "quotes"
    root.mkdir()
    older = root / "2026-05-26.jsonl"
    newer = root / "2026-05-27.jsonl"
    older.write_text("older\n", encoding="utf-8")
    newer.write_text("newer\n", encoding="utf-8")

    assert latest_path(root, "*.jsonl") == newer
    assert latest_path(root, "*.csv") is None


def test_read_only_collector_gate_reports_missing_artifacts(tmp_path: Path) -> None:
    assert read_only_collector_gate(tmp_path) == {
        "read_only_collector_gate_passed": False,
        "read_only_collector_blockers": [
            "missing_trade_xyz_registry",
            "missing_trade_xyz_quote_window",
            "missing_trade_xyz_quote_collection_summary",
        ],
        "latest_trade_xyz_registry_path": None,
        "latest_trade_xyz_quote_path": None,
        "latest_trade_xyz_summary_path": None,
        "latest_gtrade_backend_manifest_path": None,
        "latest_gtrade_backend_status": None,
        "latest_gtrade_backend_event_count": None,
        "latest_gtrade_backend_reconnect_count": None,
        "latest_gtrade_backend_deep_reorg_detected": None,
        "latest_ostium_constraint_path": None,
        "latest_ostium_constraint_status": None,
        "latest_ostium_constraint_failures": [],
        "latest_ostium_python_sdk_status": None,
        "latest_ostium_builder_prices_artifact_path": None,
    }


def test_read_only_collector_gate_reports_latest_trade_xyz_artifacts(tmp_path: Path) -> None:
    registry = tmp_path / "registry/trade_xyz_instrument_registry.json"
    summary = tmp_path / "ops/trade_xyz_quote_collection_summary.json"
    quote_root = tmp_path / "raw/quotes/trade_xyz"
    older_quote = quote_root / "2026-05-26.jsonl"
    newer_quote = quote_root / "2026-05-27.jsonl"
    registry.parent.mkdir(parents=True)
    summary.parent.mkdir(parents=True)
    quote_root.mkdir(parents=True)
    registry.write_text("{}", encoding="utf-8")
    summary.write_text("{}", encoding="utf-8")
    older_quote.write_text("older\n", encoding="utf-8")
    newer_quote.write_text("newer\n", encoding="utf-8")

    gate = read_only_collector_gate(tmp_path)

    assert gate["read_only_collector_gate_passed"] is True
    assert gate["read_only_collector_blockers"] == []
    assert gate["latest_trade_xyz_registry_path"] == str(registry)
    assert gate["latest_trade_xyz_quote_path"] == str(newer_quote)
    assert gate["latest_trade_xyz_summary_path"] == str(summary)


def test_required_artifact_paths_keeps_only_trade_xyz_artifact_strings() -> None:
    summary = {
        "latest_trade_xyz_registry_path": "data/registry/trade_xyz_instrument_registry.json",
        "latest_trade_xyz_quote_path": "data/raw/quotes/trade_xyz/2026-05-27.jsonl",
        "latest_trade_xyz_summary_path": 123,
        "latest_gtrade_backend_manifest_path": "ignored",
    }

    assert required_artifact_paths(summary) == {
        "latest_trade_xyz_registry_path": "data/registry/trade_xyz_instrument_registry.json",
        "latest_trade_xyz_quote_path": "data/raw/quotes/trade_xyz/2026-05-27.jsonl",
        "latest_trade_xyz_summary_path": None,
    }
