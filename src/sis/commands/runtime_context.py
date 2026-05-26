from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import typer

from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.ops.scheduler import next_interval_run, schedule_run, write_schedule_with_audit
from sis.ops.monitoring import build_monitoring_snapshot, write_monitoring_snapshot
from sis.reports.comparison import build_paper_live_comparison_report
from sis.reports.doc_paths import recommended_read_order
from sis.reports.lifecycle import build_strategy_lifecycle_report
from sis.reports.state_command_status import (
    build_daemon_manifest_report,
    build_state_export_report,
    build_state_restore_report,
)
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_lineage_payload_from_summary,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    phase_gate_issue_note_lines,
    readiness_flat_fields,
)
from sis.reports.weekly_review import build_weekly_review_report
from sis.state.store import StateStore
from sis.storage.jsonl_store import read_json, write_json


def _state_store(settings_data_dir: Path, state_path: Path | None) -> StateStore:
    return StateStore(state_path or (settings_data_dir / "state/marketlens.sqlite"))


def _write_weekly_review(settings_data_dir: Path) -> tuple[Path, str]:
    out = settings_data_dir / "reports/weekly_strategy_review.md"
    text = build_weekly_review_report(
        backtest_metrics_path=settings_data_dir / "research/backtest_metrics.json",
        daily_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        paper_last_run_path=_paper_last_run_path(settings_data_dir),
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


def _paper_last_run_path(settings_data_dir: Path) -> Path | None:
    paper_last_run_path = settings_data_dir / "state/paper_last_run.json"
    if not paper_last_run_path.exists():
        store = _state_store(settings_data_dir, None)
        paper_last_run = store.get_json("paper_last_run")
        if paper_last_run is not None:
            paper_last_run_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(paper_last_run_path, paper_last_run)
    return paper_last_run_path if paper_last_run_path.exists() else None


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


def _paper_last_run_audit_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "audit",
        _read_audit_schedule_summary,
    )


def _paper_last_run_phase_gate_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "phase_gate",
        _read_phase_gate_schedule_summary,
    )


def _paper_last_run_execution_drift_overview_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_drift_overview_summary",
        _read_execution_drift_overview_schedule_summary,
    )


def _paper_last_run_readiness_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "readiness_summary",
        _read_readiness_schedule_summary,
    )


def _paper_last_run_execution_gap_history_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_gap_history_summary",
        _read_execution_gap_history_schedule_summary,
    )


def _paper_last_run_execution_state_comparison_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_state_comparison_summary",
        _read_execution_state_comparison_schedule_summary,
    )


def _paper_last_run_execution_snapshot_drift_summary(settings_data_dir: Path) -> dict:
    return _paper_last_run_summary(
        settings_data_dir,
        "execution_snapshot_drift_summary",
        _read_execution_snapshot_drift_schedule_summary,
    )


def _read_execution_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_snapshot_summary.json",
        normalizer=normalize_execution_snapshot_summary,
        report_path="reports/execution_snapshot.md",
    )


def _paper_last_run_payload(settings_data_dir: Path) -> dict:
    paper_last_run_path = _paper_last_run_path(settings_data_dir)
    if paper_last_run_path is not None:
        return _read_json_dict(paper_last_run_path)
    return {}


def _read_json_dict(path: Path) -> dict:
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _read_normalized_schedule_summary(
    settings_data_dir: Path,
    *,
    path: Path,
    normalizer: Callable[[dict], dict],
    report_path: str | None = None,
    default: dict | None = None,
) -> dict:
    if not path.exists():
        return dict(default or {})
    payload = _read_json_dict(path)
    if not payload:
        return dict(default or {})
    if report_path is not None:
        payload = {
            **payload,
            "report_path": str(settings_data_dir / report_path),
        }
    return normalizer(payload)


def _paper_last_run_summary(
    settings_data_dir: Path,
    key: str,
    fallback_reader: Callable[[Path], dict],
) -> dict:
    payload = _paper_last_run_payload(settings_data_dir)
    summary = payload.get(key) if isinstance(payload, dict) else None
    if isinstance(summary, dict):
        return summary
    return fallback_reader(settings_data_dir)


def _paper_last_run_latest_execution_payload(settings_data_dir: Path) -> dict:
    return latest_execution_lineage_payload_from_summary(
        _paper_last_run_payload(settings_data_dir)
    )


def _read_execution_comparison_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        normalizer=normalize_execution_comparison_summary,
        report_path="reports/execution_venue_comparison.md",
    )


def _read_execution_diagnostics_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        normalizer=normalize_execution_diagnostics_summary,
        report_path="reports/execution_venue_diagnostics.md",
    )


def _read_execution_gap_history_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_gap_history_summary.json",
        normalizer=normalize_execution_gap_history_summary,
        report_path="reports/execution_gap_history.md",
        default={"entry_count": 0, "latest_status": None, "latest_execution_diagnostics_status": None},
    )


def _read_execution_state_comparison_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_state_comparison_history_summary.json",
        normalizer=normalize_execution_state_comparison_summary,
        report_path="reports/execution_state_comparison_history.md",
        default={"entry_count": 0, "latest_status_match": None, "mismatching_count": 0},
    )


def _read_execution_snapshot_drift_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_snapshot_drift_history_summary.json",
        normalizer=normalize_execution_snapshot_drift_summary,
        report_path="reports/execution_snapshot_drift_history.md",
        default={"entry_count": 0, "latest_status_match": None, "mismatching_snapshot_count": 0},
    )


def _read_execution_drift_overview_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        normalizer=normalize_execution_drift_overview_summary,
        report_path="reports/execution_drift_overview.md",
        default={
            "overall_status": None,
            "diagnostics_alignment_match": None,
            "state_comparison_mismatching_count": None,
            "snapshot_drift_mismatching_snapshot_count": None,
        },
    )


def _read_readiness_schedule_summary(settings_data_dir: Path) -> dict:
    readiness_path = settings_data_dir / "ops/readiness_snapshot.json"
    if not readiness_path.exists():
        return {}
    payload = _read_json_dict(readiness_path)
    if not payload:
        return {}
    return normalize_readiness_summary(
        {
            "overall_status": payload.get("overall_status"),
            "next_phase_candidate": payload.get("next_phase_candidate"),
            "execution_ready": payload.get("execution_ready"),
            "readiness_next_phase_candidate": payload.get("readiness_next_phase_candidate"),
            "readiness_execution_ready": payload.get("readiness_execution_ready"),
            "phase2_entry_allowed": payload.get("phase2_entry_allowed"),
            "report_path": str(settings_data_dir / "reports/readiness_snapshot.md"),
        }
    )


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
        run = next_interval_run(run_type=run_type, every_minutes=every_minutes or 0, command=command)
    out = write_schedule_with_audit(
        settings_data_dir / "ops/scheduled_run.json",
        run,
        audit_summary=_read_audit_schedule_summary(settings_data_dir),
        phase_gate_summary=_read_phase_gate_schedule_summary(settings_data_dir),
        execution_summary=_read_execution_schedule_summary(settings_data_dir),
        execution_comparison_summary=_read_execution_comparison_schedule_summary(settings_data_dir),
        execution_diagnostics_summary=_read_execution_diagnostics_schedule_summary(settings_data_dir),
        execution_gap_history_summary=_read_execution_gap_history_schedule_summary(settings_data_dir),
        execution_state_comparison_summary=_read_execution_state_comparison_schedule_summary(
            settings_data_dir
        ),
        execution_snapshot_drift_summary=_read_execution_snapshot_drift_schedule_summary(
            settings_data_dir
        ),
        execution_drift_overview_summary=_read_execution_drift_overview_schedule_summary(settings_data_dir),
        readiness_summary=_read_readiness_schedule_summary(settings_data_dir),
    )
    return run, out


def _daemon_dry_run_context(settings_data_dir: Path) -> dict:
    return {
        "execution_summary": _read_execution_schedule_summary(settings_data_dir),
        "execution_comparison_summary": _read_execution_comparison_schedule_summary(settings_data_dir),
        "execution_diagnostics_summary": _read_execution_diagnostics_schedule_summary(settings_data_dir),
        "execution_gap_history_summary": _read_execution_gap_history_schedule_summary(settings_data_dir),
        "execution_state_comparison_summary": _read_execution_state_comparison_schedule_summary(settings_data_dir),
        "execution_snapshot_drift_summary": _read_execution_snapshot_drift_schedule_summary(settings_data_dir),
        "execution_drift_overview_summary": _read_execution_drift_overview_schedule_summary(settings_data_dir),
        "readiness_summary": _read_readiness_schedule_summary(settings_data_dir),
    }


def _write_monitoring_snapshot(settings_data_dir: Path, state_path: Path | None) -> tuple[Path, dict]:
    store = _state_store(settings_data_dir, state_path)
    kill_switch = KillSwitch(settings_data_dir / "state/kill_switch.flag")
    health = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        reconciliation_store_present=store.latest_reconciliation() is not None,
    )
    snapshot = build_monitoring_snapshot(
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        daily_pnl_path=settings_data_dir / "paper/daily_pnl.parquet",
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        execution_venue_comparison_summary_path=settings_data_dir / "ops/execution_venue_comparison_summary.json",
        execution_venue_diagnostics_summary_path=settings_data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=settings_data_dir / "ops/execution_gap_history_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        last_healthcheck=health,
    )
    out = write_monitoring_snapshot(settings_data_dir / "ops/monitoring_status.json", snapshot)
    return out, snapshot


def _read_audit_schedule_summary(settings_data_dir: Path) -> dict:
    audit_dashboard_path = settings_data_dir / "ops/audit_dashboard_summary.json"
    audit_bundle_path = settings_data_dir / "ops/audit_bundle_manifest.json"
    audit_dashboard = _read_json_dict(audit_dashboard_path) if audit_dashboard_path.exists() else {}
    audit_bundle = _read_json_dict(audit_bundle_path) if audit_bundle_path.exists() else {}
    return audit_summary_fields(audit_dashboard, audit_bundle)


def _read_phase_gate_schedule_summary(settings_data_dir: Path) -> dict:
    return _read_normalized_schedule_summary(
        settings_data_dir,
        path=settings_data_dir / "ops/phase_gate_review_summary.json",
        normalizer=normalize_phase_gate_summary,
    )


def _phase_gate_note_lines(phase_gate: dict) -> list[str]:
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    lines = [
        f"phase_gate_decision={phase_gate_fields.get('phase_gate_decision')}",
        f"phase2_entry_allowed={phase_gate_fields.get('phase2_entry_allowed')}",
        f"phase_gate_reason={phase_gate_fields.get('phase_gate_reason')}",
        f"phase_gate_strict_validation_passed={phase_gate_fields.get('phase_gate_strict_validation_passed')}",
        (
            "phase_gate_strict_validation_issue_count="
            f"{phase_gate_fields.get('phase_gate_strict_validation_issue_count')}"
        ),
        f"phase_gate_checked_files={phase_gate_fields.get('phase_gate_checked_files')}",
    ]
    lines.append(
        f"phase_gate_review_report_path={phase_gate_fields.get('phase_gate_review_report_path')}"
    )
    lines.extend(phase_gate_issue_note_lines(phase_gate_fields))
    return lines


def _echo_audit_summary(summary: dict) -> None:
    audit_summary = audit_summary_fields(summary, summary)
    typer.echo(f"audit_overall_status={audit_summary.get('overall_status')}")
    typer.echo(f"audit_latest_operation={audit_summary.get('latest_operation')}")
    typer.echo(
        "audit_bundle_history_snapshot_count="
        f"{audit_summary.get('bundle_history_snapshot_count')}"
    )


def _readiness_note_lines(readiness: dict) -> list[str]:
    readiness_fields = readiness_flat_fields(readiness)
    return [
        f"readiness_next_phase={readiness_fields.get('readiness_next_phase_candidate')}",
        f"readiness_execution_ready={readiness_fields.get('readiness_execution_ready')}",
    ]


def _execution_drift_note_lines(drift_overview: dict) -> list[str]:
    drift_fields = execution_drift_overview_flat_fields(drift_overview)
    return [
        f"execution_drift_overview_status={drift_fields.get('execution_drift_overview_status')}",
        (
            "execution_drift_overview_diagnostics_alignment_match="
            f"{drift_fields.get('execution_drift_overview_diagnostics_alignment_match')}"
        ),
        (
            "execution_drift_overview_state_comparison_mismatching_count="
            f"{drift_fields.get('execution_drift_overview_state_comparison_mismatching_count')}"
        ),
        (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
            f"{drift_fields.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
        ),
    ]


def _execution_gap_history_note_lines(gap_history: dict) -> list[str]:
    gap_history_fields = execution_gap_history_flat_fields(gap_history)
    return [
        f"execution_gap_history_entry_count={gap_history_fields.get('execution_gap_history_entry_count')}",
        f"execution_gap_history_latest_status={gap_history_fields.get('execution_gap_history_latest_status')}",
        (
            "execution_gap_history_latest_diagnostics_status="
            f"{gap_history_fields.get('execution_gap_history_latest_diagnostics_status')}"
        ),
    ]


def _execution_diagnostics_note_lines(execution_diagnostics: dict) -> list[str]:
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    return [
        (
            "execution_diagnostics_status="
            f"{execution_diagnostics_fields.get('execution_diagnostics_status')}"
        )
    ]


def _execution_summary_note_lines(execution_summary: dict) -> list[str]:
    execution_fields = execution_snapshot_flat_fields(execution_summary)
    return [
        f"execution_overall_status={execution_fields.get('execution_overall_status')}",
        f"execution_venue_count={execution_fields.get('execution_venue_count')}",
    ]


def _execution_comparison_note_lines(execution_comparison: dict) -> list[str]:
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    return [
        (
            "execution_comparison_all_registries_present="
            f"{execution_comparison_fields.get('execution_comparison_all_registries_present')}"
        )
    ]


def _execution_state_comparison_note_lines(state_comparison: dict) -> list[str]:
    state_comparison_fields = execution_state_comparison_flat_fields(state_comparison)
    return [
        (
            "execution_state_comparison_entry_count="
            f"{state_comparison_fields.get('execution_state_comparison_entry_count')}"
        ),
        (
            "execution_state_comparison_latest_status_match="
            f"{state_comparison_fields.get('execution_state_comparison_latest_status_match')}"
        ),
        (
            "execution_state_comparison_mismatching_count="
            f"{state_comparison_fields.get('execution_state_comparison_mismatching_count')}"
        ),
    ]


def _execution_snapshot_drift_note_lines(snapshot_drift: dict) -> list[str]:
    snapshot_drift_fields = execution_snapshot_drift_flat_fields(snapshot_drift)
    return [
        (
            "execution_snapshot_drift_entry_count="
            f"{snapshot_drift_fields.get('execution_snapshot_drift_entry_count')}"
        ),
        (
            "execution_snapshot_drift_latest_status_match="
            f"{snapshot_drift_fields.get('execution_snapshot_drift_latest_status_match')}"
        ),
        (
            "execution_snapshot_drift_mismatching_snapshot_count="
            f"{snapshot_drift_fields.get('execution_snapshot_drift_mismatching_snapshot_count')}"
        ),
    ]


def _echo_phase_gate_summary(phase_gate: dict) -> None:
    for line in _phase_gate_note_lines(phase_gate):
        typer.echo(line)


def _recommended_read_order(settings_data_dir: Path) -> list[str]:
    bundle_manifest_path = settings_data_dir / "ops/operations_bundle_manifest.json"
    if bundle_manifest_path.exists():
        payload = read_json(bundle_manifest_path)
        if isinstance(payload, dict):
            order = payload.get("recommended_read_order")
            if isinstance(order, list):
                return [str(item) for item in order]
    dashboard_summary_path = settings_data_dir / "ops/operations_dashboard_summary.json"
    if dashboard_summary_path.exists():
        payload = read_json(dashboard_summary_path)
        if isinstance(payload, dict):
            order = payload.get("recommended_read_order")
            if isinstance(order, list):
                return [str(item) for item in order]
    return recommended_read_order(
        [
            "data/ops/execution_snapshot_summary.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
        ]
    )
