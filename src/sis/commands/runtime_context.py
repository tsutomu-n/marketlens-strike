from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

import typer

from sis.commands.runtime_context_notes import _phase_gate_note_lines
from sis.commands.runtime_paper_last_run_summaries import (
    paper_last_run_audit_summary as _paper_last_run_audit_summary,
    paper_last_run_execution_drift_overview_summary as _paper_last_run_execution_drift_overview_summary,
    paper_last_run_execution_gap_history_summary as _paper_last_run_execution_gap_history_summary,
    paper_last_run_execution_snapshot_drift_summary as _paper_last_run_execution_snapshot_drift_summary,
    paper_last_run_execution_state_comparison_summary as _paper_last_run_execution_state_comparison_summary,
    paper_last_run_latest_execution_payload as _paper_last_run_latest_execution_payload,
    paper_last_run_path as _paper_last_run_path,
    paper_last_run_phase_gate_summary as _paper_last_run_phase_gate_summary,
    paper_last_run_readiness_summary as _paper_last_run_readiness_summary,
)
from sis.commands.runtime_read_order import (
    runtime_recommended_read_order as _recommended_read_order,
)
from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.ops.monitoring import build_monitoring_snapshot, write_monitoring_snapshot
from sis.ops.scheduler import next_interval_run, schedule_run, write_schedule_with_audit
from sis.reports.comparison import build_paper_live_comparison_report
from sis.reports.lifecycle import build_strategy_lifecycle_report
from sis.reports.state_command_status import (
    build_daemon_manifest_report,
    build_state_export_report,
    build_state_restore_report,
)
from sis.commands.runtime_schedule_summaries import (
    daemon_dry_run_context as _daemon_dry_run_context,
    read_audit_schedule_summary as _read_audit_schedule_summary,
    read_execution_comparison_schedule_summary as _read_execution_comparison_schedule_summary,
    read_execution_diagnostics_schedule_summary as _read_execution_diagnostics_schedule_summary,
    read_execution_drift_overview_schedule_summary as _read_execution_drift_overview_schedule_summary,
    read_execution_gap_history_schedule_summary as _read_execution_gap_history_schedule_summary,
    read_execution_schedule_summary as _read_execution_schedule_summary,
    read_execution_snapshot_drift_schedule_summary as _read_execution_snapshot_drift_schedule_summary,
    read_execution_state_comparison_schedule_summary as _read_execution_state_comparison_schedule_summary,
    read_phase_gate_schedule_summary as _read_phase_gate_schedule_summary,
    read_readiness_schedule_summary as _read_readiness_schedule_summary,
)
from sis.reports.summary_normalizers import audit_summary_fields
from sis.reports.weekly_review import build_weekly_review_report
from sis.state.store import StateStore
from sis.storage.jsonl_store import read_json


__all__ = [
    "_daemon_dry_run_context",
    "_echo_audit_summary",
    "_echo_phase_gate_summary",
    "_paper_last_run_audit_summary",
    "_paper_last_run_execution_drift_overview_summary",
    "_paper_last_run_execution_gap_history_summary",
    "_paper_last_run_execution_snapshot_drift_summary",
    "_paper_last_run_execution_state_comparison_summary",
    "_paper_last_run_latest_execution_payload",
    "_paper_last_run_phase_gate_summary",
    "_paper_last_run_readiness_summary",
    "_read_audit_schedule_summary",
    "_read_execution_comparison_schedule_summary",
    "_read_execution_diagnostics_schedule_summary",
    "_read_execution_drift_overview_schedule_summary",
    "_read_execution_gap_history_schedule_summary",
    "_read_execution_schedule_summary",
    "_read_execution_snapshot_drift_schedule_summary",
    "_read_execution_state_comparison_schedule_summary",
    "_read_readiness_schedule_summary",
    "_recommended_read_order",
    "_state_store",
    "_write_comparison_report",
    "_write_daemon_manifest_artifacts",
    "_write_lifecycle_report",
    "_write_monitoring_snapshot",
    "_write_schedule_run_with_audit",
    "_write_state_export_artifacts",
    "_write_state_restore_artifacts",
    "_write_weekly_review",
]


def _state_store(settings_data_dir: Path, state_path: Path | None) -> StateStore:
    return StateStore(state_path or (settings_data_dir / "state/marketlens.sqlite"))


def _write_weekly_review(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/weekly_strategy_review.md"
    text = build_weekly_review_report(
        backtest_metrics_path=settings_data_dir / "research/backtest_metrics.json",
        daily_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
        current_phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
    )
    return out, text


def _write_daemon_manifest_artifacts(settings_data_dir: Path) -> tuple[Path, Path, str] | None:
    manifest_path = settings_data_dir / "ops/daemon_manifest.json"
    if not manifest_path.exists():
        return None
    payload = read_json(manifest_path)
    if not isinstance(payload, dict):
        return None
    payload = cast(dict[str, object], payload)
    out = settings_data_dir / "reports/daemon_manifest.md"
    summary_out = settings_data_dir / "ops/daemon_manifest_summary.json"
    text = build_daemon_manifest_report(
        manifest=payload,
        manifest_path=str(manifest_path),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_state_export_artifacts(
    settings_data_dir: Path,
    *,
    state_store_path: Path | None = None,
) -> tuple[Path, Path, str] | None:
    snapshot_path = settings_data_dir / "state/state_snapshot.json"
    if not snapshot_path.exists():
        return None
    payload = read_json(snapshot_path)
    if not isinstance(payload, dict):
        return None
    payload = cast(dict[str, object], payload)
    out = settings_data_dir / "reports/state_export.md"
    summary_out = settings_data_dir / "ops/state_export_summary.json"
    text = build_state_export_report(
        snapshot=payload,
        snapshot_path=str(snapshot_path),
        state_store_path=str(state_store_path or (settings_data_dir / "state/marketlens.sqlite")),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_state_restore_artifacts(
    settings_data_dir: Path,
    *,
    snapshot_path: Path,
    state_store_path: Path | None = None,
    restored: bool,
) -> tuple[Path, Path, str] | None:
    if not snapshot_path.exists():
        return None
    payload = read_json(snapshot_path)
    if not isinstance(payload, dict):
        return None
    payload = cast(dict[str, object], payload)
    out = settings_data_dir / "reports/state_restore.md"
    summary_out = settings_data_dir / "ops/state_restore_summary.json"
    text = build_state_restore_report(
        snapshot=payload,
        snapshot_path=str(snapshot_path),
        state_store_path=str(state_store_path or (settings_data_dir / "state/marketlens.sqlite")),
        restored=restored,
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_lifecycle_report(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/strategy_lifecycle_report.md"
    text = build_strategy_lifecycle_report(
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
        out_path=out,
    )
    return out, text


def _write_comparison_report(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/paper_vs_backtest_comparison.md"
    text = build_paper_live_comparison_report(
        paper_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        backtest_metrics_path=settings_data_dir / "research/backtest_metrics.json",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
        out_path=out,
    )
    return out, text


def _write_schedule_run_with_audit(
    settings_data_dir: Path,
    *,
    run_type: str,
    command: str,
    at: str | None,
    every_minutes: int | None,
):
    if at is not None:
        scheduled_for = datetime.fromisoformat(at.replace("Z", "+00:00"))
        run = schedule_run(run_type=run_type, scheduled_for=scheduled_for, command=command)
    else:
        run = next_interval_run(
            run_type=run_type, every_minutes=every_minutes or 0, command=command
        )
    out = write_schedule_with_audit(
        settings_data_dir / "ops/scheduled_run.json",
        run,
        audit_summary=_read_audit_schedule_summary(settings_data_dir),
        phase_gate_summary=_read_phase_gate_schedule_summary(settings_data_dir),
        execution_summary=_read_execution_schedule_summary(settings_data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings_data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(
            settings_data_dir
        ),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(
            settings_data_dir
        ),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings_data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings_data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(
            settings_data_dir
        ),
        readiness_summary=_read_readiness_schedule_summary(settings_data_dir),
    )
    return run, out


def _write_monitoring_snapshot(
    settings_data_dir: Path, state_path: Path | None
) -> tuple[Path, dict]:
    store = _state_store(settings_data_dir, state_path)
    kill_switch = KillSwitch(settings_data_dir / "state/kill_switch.flag")
    health = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        reconciliation_store_present=store.latest_reconciliation() is not None,
    )
    snapshot = build_monitoring_snapshot(
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        daily_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir
        / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir
        / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        last_healthcheck=health,
    )
    out = write_monitoring_snapshot(settings_data_dir / "ops/monitoring_status.json", snapshot)
    return out, snapshot


def _echo_audit_summary(summary: dict) -> None:
    audit_summary = audit_summary_fields(summary, summary)
    typer.echo(f"audit_overall_status={audit_summary.get('overall_status')}")
    typer.echo(f"audit_latest_operation={audit_summary.get('latest_operation')}")
    typer.echo(
        f"audit_bundle_history_snapshot_count={audit_summary.get('bundle_history_snapshot_count')}"
    )


def _echo_phase_gate_summary(phase_gate: dict) -> None:
    for line in _phase_gate_note_lines(phase_gate):
        typer.echo(line)
