from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.ops.manifest_chain import append_operation_manifest, create_operation_manifest
from sis.ops.scheduler import next_interval_run, write_schedule_with_audit
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_comparison_summary,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_readiness_summary,
    defaulted_all_latest_execution_lineage_fields,
    phase_gate_flat_fields,
    phase_gate_nested_fields,
    readiness_flat_fields,
)
from sis.storage.jsonl_store import write_json


@dataclass(frozen=True)
class DaemonRunManifest:
    run_id: str
    created_at: str
    mode: str
    command: str
    state_store_path: str
    notes: list[str]


@dataclass(frozen=True)
class DaemonDryRunResult:
    run_id: str
    status: str
    scheduled_for: str
    daemon_manifest_path: Path
    schedule_path: Path
    operation_chain_path: Path
    dry_run_snapshot_path: Path


def create_daemon_manifest(*, mode: str, command: str, state_store_path: Path, notes: list[str] | None = None) -> DaemonRunManifest:
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    return DaemonRunManifest(
        run_id=run_id,
        created_at=now.isoformat(),
        mode=mode,
        command=command,
        state_store_path=str(state_store_path),
        notes=notes or [],
    )


def write_daemon_manifest(path: Path, manifest: DaemonRunManifest) -> Path:
    write_json(
        path,
        {
            "run_id": manifest.run_id,
            "created_at": manifest.created_at,
            "mode": manifest.mode,
            "command": manifest.command,
            "state_store_path": manifest.state_store_path,
            "notes": manifest.notes,
        },
    )
    return path


def run_daemon_dry_run(
    *,
    data_dir: Path,
    mode: str,
    command: str,
    state_store_path: Path,
    every_minutes: int,
    kill_switch: KillSwitch,
    decision_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    readiness_summary: dict | None = None,
    now: datetime | None = None,
) -> DaemonDryRunResult:
    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    current = now.astimezone(timezone.utc) if now and now.tzinfo else (now or datetime.now(timezone.utc))
    scheduled = next_interval_run(run_type=mode, every_minutes=every_minutes, command=command, now=current)
    manifest = create_daemon_manifest(
        mode=mode,
        command=command,
        state_store_path=state_store_path,
        notes=["foundation_only", "dry_run", f"interval_minutes={every_minutes}"],
    )
    daemon_manifest_path = write_daemon_manifest(data_dir / "ops/daemon_manifest.json", manifest)
    health = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=decision_summary_path,
        audit_dashboard_summary_path=audit_dashboard_summary_path,
        audit_bundle_summary_path=audit_bundle_summary_path,
        operations_bundle_manifest_path=operations_bundle_manifest_path,
        phase_gate_summary_path=phase_gate_summary_path,
        execution_summary_path=data_dir / "ops/execution_snapshot_summary.json",
        execution_comparison_summary_path=data_dir / "ops/execution_venue_comparison_summary.json",
        execution_diagnostics_summary_path=data_dir / "ops/execution_venue_diagnostics_summary.json",
        execution_gap_history_summary_path=data_dir / "ops/execution_gap_history_summary.json",
        execution_state_comparison_summary_path=data_dir / "ops/execution_state_comparison_history_summary.json",
        execution_snapshot_drift_summary_path=data_dir / "ops/execution_snapshot_drift_history_summary.json",
        reconciliation_store_present=False,
    )
    phase_gate_payload = phase_gate_nested_fields(health)
    phase_gate_fields = phase_gate_flat_fields(phase_gate_payload)
    execution_fields = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_fields = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    readiness_fields = readiness_flat_fields(normalized_readiness_summary)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_fields = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    execution_drift_fields = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    audit_summary = audit_summary_fields(health, health)
    latest_execution_lineage = defaulted_all_latest_execution_lineage_fields(health)
    audit_payload = {
        **audit_summary,
        **latest_execution_lineage,
    }
    schedule_path = write_schedule_with_audit(
        data_dir / "ops/scheduled_run.json",
        scheduled,
        audit_summary=audit_payload,
        phase_gate_summary=phase_gate_payload,
        execution_summary=normalized_execution_summary,
        execution_comparison_summary=normalized_execution_comparison_summary,
        execution_diagnostics_summary=normalized_execution_diagnostics_summary,
        execution_gap_history_summary=normalized_execution_gap_history_summary,
        execution_state_comparison_summary=normalized_execution_state_comparison_summary,
        execution_snapshot_drift_summary=normalized_execution_snapshot_drift_summary,
        execution_drift_overview_summary=normalized_execution_drift_overview_summary,
        readiness_summary=normalized_readiness_summary,
    )
    dry_run_snapshot_path = data_dir / "ops/daemon_dry_run.json"
    write_json(
        dry_run_snapshot_path,
        {
            "run_id": manifest.run_id,
            "created_at": manifest.created_at,
            "mode": manifest.mode,
            "command": manifest.command,
            "scheduled_for": scheduled.scheduled_for.isoformat(),
            "status": "blocked" if health["kill_switch_enabled"] else "planned",
            "healthcheck": health,
            "audit": audit_payload,
            "audit_summary": audit_payload,
            **latest_execution_lineage,
            "phase_gate": phase_gate_payload,
            "phase_gate_summary": phase_gate_payload,
            **phase_gate_fields,
            "execution": normalized_execution_summary,
            "execution_summary": normalized_execution_summary,
            **execution_fields,
            "execution_comparison": normalized_execution_comparison_summary,
            "execution_comparison_summary": normalized_execution_comparison_summary,
            **execution_comparison_fields,
            "execution_diagnostics": normalized_execution_diagnostics_summary,
            "execution_diagnostics_summary": normalized_execution_diagnostics_summary,
            **execution_diagnostics_fields,
            "execution_gap_history": normalized_execution_gap_history_summary,
            "execution_gap_history_summary": normalized_execution_gap_history_summary,
            **execution_gap_history_fields,
            "execution_state_comparison": normalized_execution_state_comparison_summary,
            "execution_state_comparison_summary": normalized_execution_state_comparison_summary,
            **execution_state_comparison_fields,
            "execution_snapshot_drift": normalized_execution_snapshot_drift_summary,
            "execution_snapshot_drift_summary": normalized_execution_snapshot_drift_summary,
            **execution_snapshot_drift_fields,
            "execution_drift_overview": normalized_execution_drift_overview_summary,
            "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
            **execution_drift_fields,
            "readiness": normalized_readiness_summary,
            "readiness_summary": normalized_readiness_summary,
            **readiness_fields,
            "artifacts": {
                "schedule": str(schedule_path),
                "daemon_manifest": str(daemon_manifest_path),
            },
        },
    )
    operation_manifest = create_operation_manifest(
        operation="daemon_dry_run",
        mode=mode,
        command=command,
        status="blocked" if health["kill_switch_enabled"] else "planned",
        scheduled_for=scheduled.scheduled_for.isoformat(),
        parent_run_id=manifest.run_id,
        artifacts=[str(schedule_path), str(daemon_manifest_path), str(dry_run_snapshot_path)],
        notes=[
            "dry_run",
            f"health_status={health['status']}",
            f"execution_diagnostics_status={execution_diagnostics_fields.get('execution_diagnostics_status')}",
            f"readiness_next_phase={readiness_fields.get('readiness_next_phase_candidate')}",
            f"readiness_execution_ready={readiness_fields.get('readiness_execution_ready')}",
        ],
        now=current,
    )
    operation_chain_path = append_operation_manifest(data_dir / "ops/operation_manifests.jsonl", operation_manifest)
    return DaemonDryRunResult(
        run_id=manifest.run_id,
        status=operation_manifest.status,
        scheduled_for=scheduled.scheduled_for.isoformat(),
        daemon_manifest_path=daemon_manifest_path,
        schedule_path=schedule_path,
        operation_chain_path=operation_chain_path,
        dry_run_snapshot_path=dry_run_snapshot_path,
    )
