from __future__ import annotations

from pathlib import Path

from sis.reports.live_evidence_report_inputs import (
    count_jsonl_rows,
    default_markdown_output_path,
    latest_evidence_card,
    load_backtest_metrics,
    load_cost_rows,
    parse_run_status,
    started_finished,
    summary_from_manifest_or_evidence,
    summary_from_payload,
)


def test_parse_run_status_handles_missing_completed_failed_and_running(tmp_path: Path) -> None:
    assert parse_run_status(tmp_path / "missing.log") == "running"

    completed = tmp_path / "completed.log"
    completed.write_text("Live evidence refresh completed\n", encoding="utf-8")
    assert parse_run_status(completed) == "completed"

    failed = tmp_path / "failed.log"
    failed.write_text("Traceback\n", encoding="utf-8")
    assert parse_run_status(failed) == "failed"

    running = tmp_path / "running.log"
    running.write_text("still collecting\n", encoding="utf-8")
    assert parse_run_status(running) == "running"


def test_summary_helpers_prefer_manifest_over_evidence_payload() -> None:
    manifest = {"phase_gate_summary": {"decision": "manifest"}}
    evidence = {"phase_gate_summary": {"decision": "evidence"}}

    assert summary_from_payload(manifest, "phase_gate_summary") == {"decision": "manifest"}
    assert summary_from_payload({"phase_gate_summary": []}, "phase_gate_summary") == {}
    assert summary_from_manifest_or_evidence(manifest, evidence, "phase_gate_summary") == {
        "decision": "manifest"
    }
    assert summary_from_manifest_or_evidence({}, evidence, "phase_gate_summary") == {
        "decision": "evidence"
    }


def test_latest_evidence_card_uses_sorted_filename_order(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "data/evidence"
    evidence_dir.mkdir(parents=True)
    older = evidence_dir / "evidence_card_20260522_2308.json"
    newer = evidence_dir / "evidence_card_20260523_0001.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")

    assert latest_evidence_card(tmp_path / "data") == newer
    assert latest_evidence_card(tmp_path / "empty") is None


def test_count_jsonl_rows_ignores_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a":1}\n\n{"b":2}\n', encoding="utf-8")

    assert count_jsonl_rows(path) == 2
    assert count_jsonl_rows(tmp_path / "missing.jsonl") == 0


def test_load_cost_rows_and_backtest_metrics(tmp_path: Path) -> None:
    cost_path = tmp_path / "cost.csv"
    cost_path.write_text("venue,symbol,cost\ntrade_xyz,SPY,1.2\n", encoding="utf-8")
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text('[{"strategy":"baseline","sharpe":1.0}]', encoding="utf-8")

    assert load_cost_rows(cost_path) == [{"venue": "trade_xyz", "symbol": "SPY", "cost": "1.2"}]
    assert load_cost_rows(tmp_path / "missing.csv") == []
    assert load_backtest_metrics(metrics_path) == [{"strategy": "baseline", "sharpe": 1.0}]


def test_started_finished_extracts_first_start_and_latest_finish() -> None:
    assert started_finished(
        [
            "[2026-05-22T14:08:00Z] Scheduled live evidence run starting",
            "[2026-05-22T16:08:30Z] Live evidence refresh completed",
            "[2026-05-22T16:09:00Z] Live evidence refresh completed",
        ]
    ) == ("2026-05-22T14:08:00Z", "2026-05-22T16:09:00Z")


def test_default_markdown_output_path_uses_live_evidence_stem() -> None:
    assert default_markdown_output_path(
        Path("logs/live_evidence/manifests/live_evidence_20260522_2308.json")
    ) == Path("docs/live_evidence_reports/live_evidence_report_20260522_2308.md")
