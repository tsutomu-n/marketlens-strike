from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.ops.alerts import queue_notification, render_alert_message, write_alert
from sis.ops.manifest_chain import (
    append_operation_manifest,
    create_operation_manifest,
    latest_operation_manifest,
)
from sis.ops.scheduler import (
    next_interval_run,
    schedule_run,
    write_schedule,
    write_schedule_with_audit,
)
from sis.reports.weekly_review import build_weekly_review_report


def test_schedule_run_and_write_schedule(tmp_path) -> None:
    scheduled = schedule_run(
        run_type="paper",
        scheduled_for=datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc),
        command="uv run sis paper-step",
    )
    interval_run = next_interval_run(
        run_type="healthcheck",
        every_minutes=30,
        command="uv run sis healthcheck",
        now=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )
    out = write_schedule(tmp_path / "schedule.json", scheduled)

    assert out.exists()
    assert scheduled.run_type == "paper"
    assert interval_run.scheduled_for.isoformat() == "2026-05-24T12:30:00+00:00"


def test_write_schedule_with_audit(tmp_path) -> None:
    scheduled = schedule_run(
        run_type="paper",
        scheduled_for=datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc),
        command="uv run sis paper-step",
    )
    out = write_schedule_with_audit(
        tmp_path / "schedule_with_audit.json",
        scheduled,
        audit_summary={"overall_status": "ok", "latest_operation": "audit_bundle_snapshot"},
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "strict_validation_issue_count": 2,
            "checked_files": 7,
        },
        execution_diagnostics_summary={"overall_status": "degraded", "balance_gap_detected": True},
        execution_drift_overview_summary={
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        },
        readiness_summary={
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        },
    )

    assert out.exists()
    assert '"overall_status": "ok"' in out.read_text(encoding="utf-8")
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in out.read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in out.read_text(
        encoding="utf-8"
    )
    assert '"phase2_entry_allowed": false' in out.read_text(encoding="utf-8")
    assert (
        '"phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears"'
        in out.read_text(encoding="utf-8")
    )
    assert (
        '"phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears"'
        in out.read_text(encoding="utf-8")
    )
    assert '"phase_gate_strict_validation_passed": true' in out.read_text(encoding="utf-8")
    assert '"phase_gate_strict_validation_issue_count": 2' in out.read_text(encoding="utf-8")
    assert '"phase_gate_checked_files": 7' in out.read_text(encoding="utf-8")
    assert '"strict_validation_issue_count": 2' in out.read_text(encoding="utf-8")
    assert '"checked_files": 7' in out.read_text(encoding="utf-8")
    assert '"audit_summary": {' in out.read_text(encoding="utf-8")
    assert '"phase_gate_summary": {' in out.read_text(encoding="utf-8")
    assert '"execution_diagnostics_summary": {' in out.read_text(encoding="utf-8")
    assert '"execution_drift_overview_summary": {' in out.read_text(encoding="utf-8")
    assert '"readiness_summary": {' in out.read_text(encoding="utf-8")
    assert '"execution_diagnostics_status": "degraded"' in out.read_text(encoding="utf-8")
    assert '"execution_balance_gap_detected": true' in out.read_text(encoding="utf-8")
    assert '"execution_fills_gap_detected": null' in out.read_text(encoding="utf-8")
    assert '"balance_gap_detected": true' in out.read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in out.read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in out.read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in out.read_text(encoding="utf-8")
    assert '"next_phase_candidate": "Stay Phase 1"' in out.read_text(encoding="utf-8")


def test_alert_render_and_write(tmp_path) -> None:
    text = render_alert_message(
        level="warn", title="Stale data", body="recollect live evidence", source="healthcheck"
    )
    out = write_alert(
        tmp_path / "alert.txt",
        level="warn",
        title="Stale data",
        body="recollect live evidence",
        source="healthcheck",
    )

    assert "[WARN] Stale data" in text
    assert out.exists()
    assert "source: healthcheck" in out.read_text(encoding="utf-8")


def test_queue_notification_writes_outbox_and_latest(tmp_path) -> None:
    record = queue_notification(
        outbox_path=tmp_path / "notifications/outbox.jsonl",
        latest_path=tmp_path / "notifications/latest_notification.json",
        level="warn",
        title="Stale data",
        body="recollect live evidence",
        source="healthcheck",
        sink="local_outbox",
        now=datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc),
    )

    assert record["status"] == "queued"
    assert record["notification_id"] == "20260525_000000_000000"
    assert "recollect live evidence" in (tmp_path / "notifications/outbox.jsonl").read_text(
        encoding="utf-8"
    )
    assert "Stale data" in (tmp_path / "notifications/latest_notification.json").read_text(
        encoding="utf-8"
    )


def test_operation_manifest_chain_append_and_read_latest(tmp_path) -> None:
    manifest = create_operation_manifest(
        operation="daemon_dry_run",
        mode="paper",
        command="uv run sis paper-step",
        status="planned",
        scheduled_for="2026-05-24T12:30:00+00:00",
        artifacts=["data/ops/scheduled_run.json"],
        notes=["dry_run"],
        now=datetime(2026, 5, 24, 12, 0, tzinfo=timezone.utc),
    )
    out = append_operation_manifest(tmp_path / "operation_manifests.jsonl", manifest)
    latest = latest_operation_manifest(out)

    assert out.exists()
    assert latest is not None
    assert latest["operation"] == "daemon_dry_run"
    assert latest["status"] == "planned"


def test_build_weekly_review_report_uses_backtest_and_paper_inputs(tmp_path) -> None:
    backtest_path = tmp_path / "backtest_metrics.json"
    daily_pnl_path = tmp_path / "daily_pnl.parquet"
    pl.DataFrame([{"venue": "gtrade", "canonical_symbol": "QQQ", "trade_count": 3}]).write_json(
        backtest_path
    )
    pl.DataFrame(
        [{"date": "2026-05-24", "realized_pnl": 12.5, "fills_count": 2, "open_positions": 1}]
    ).write_parquet(daily_pnl_path)

    text = build_weekly_review_report(
        backtest_metrics_path=backtest_path,
        daily_pnl_path=daily_pnl_path,
        out_path=tmp_path / "weekly.md",
    )

    assert "Weekly Strategy Review" in text
    assert "Backtest Metrics Snapshot" in text
    assert "Paper PnL Snapshot" in text
