from __future__ import annotations

from pathlib import Path

from sis.reports.audit_bundle import build_audit_bundle_manifest
from sis.reports.audit_bundle_history import build_audit_bundle_history_report
from sis.reports.audit_dashboard import build_audit_dashboard
from sis.reports.audit_timeline import build_audit_timeline_report
from sis.reports.current_state_index import build_current_state_index
from sis.reports.execution_drift_overview import build_execution_drift_overview_report
from sis.reports.execution_gap_history import build_execution_gap_history_report
from sis.reports.execution_snapshot_drift_history import (
    build_execution_snapshot_drift_history_report,
)
from sis.reports.execution_state_comparison_history import (
    build_execution_state_comparison_history_report,
)
from sis.reports.operations_audit_pack import build_operations_audit_pack
from sis.reports.operations_bundle import build_operations_bundle_manifest
from sis.reports.operations_dashboard import build_operations_dashboard
from sis.reports.operations_timeline import build_operations_timeline_report
from sis.reports.ops_review import build_ops_review_report
from sis.reports.paper_cycle_history import build_paper_cycle_history_report
from sis.reports.paper_operations_runbook import build_paper_operations_runbook
from sis.reports.phase_gate_review import build_phase_gate_review
from sis.reports.readiness_snapshot import build_readiness_snapshot
from sis.reports.remediation_command_results import build_remediation_command_results
from sis.reports.remediation_evaluator import build_remediation_evaluator
from sis.reports.remediation_evidence import build_remediation_evidence
from sis.reports.remediation_execution_plan import build_remediation_execution_plan
from sis.reports.remediation_planner import build_remediation_planner
from sis.reports.remediation_scoreboard import build_remediation_scoreboard
from sis.reports.remediation_session import build_remediation_session
from sis.reports.remediation_session_checkpoint import build_remediation_session_checkpoint


def _write_ops_review(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/ops_review_report.md"
    summary_out = settings_data_dir / "ops/ops_review_summary.json"
    text = build_ops_review_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        monitoring_snapshot_path=settings_data_dir / "ops/monitoring_status.json",
        daemon_dry_run_path=settings_data_dir / "ops/daemon_dry_run.json",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_operations_dashboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_dashboard.md"
    summary_out = settings_data_dir / "ops/operations_dashboard_summary.json"
    text = build_operations_dashboard(
        monitoring_snapshot_path=settings_data_dir / "ops/monitoring_status.json",
        operations_timeline_summary_path=settings_data_dir / "ops/operations_timeline_summary.json",
        ops_review_summary_path=settings_data_dir / "ops/ops_review_summary.json",
        decision_summary_path=settings_data_dir / "research/decision_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        execution_balance_status_summary_path=settings_data_dir
        / "ops/execution_balance_status_summary.json",
        execution_fill_status_summary_path=settings_data_dir
        / "ops/execution_fill_status_summary.json",
        execution_order_status_summary_path=settings_data_dir
        / "ops/execution_order_status_summary.json",
        execution_cancel_order_summary_path=settings_data_dir
        / "ops/execution_cancel_order_summary.json",
        execution_close_position_summary_path=settings_data_dir
        / "ops/execution_close_position_summary.json",
        execution_reconcile_positions_summary_path=settings_data_dir
        / "ops/execution_reconcile_positions_summary.json",
        execution_read_only_surfaces_summary_path=settings_data_dir
        / "ops/execution_read_only_surfaces_summary.json",
        daemon_manifest_summary_path=settings_data_dir / "ops/daemon_manifest_summary.json",
        daemon_loop_summary_path=settings_data_dir / "ops/daemon_loop_summary.json",
        notification_outbox_summary_path=settings_data_dir / "ops/notification_outbox_summary.json",
        state_export_summary_path=settings_data_dir / "ops/state_export_summary.json",
        state_restore_summary_path=settings_data_dir / "ops/state_restore_summary.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_summary_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        comparison_report_path=settings_data_dir / "reports/paper_vs_backtest_comparison.md",
        weekly_review_path=settings_data_dir / "reports/weekly_strategy_review.md",
        lifecycle_report_path=settings_data_dir / "reports/strategy_lifecycle_report.md",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_paper_operations_runbook(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/paper_operations_runbook.md"
    summary_out = settings_data_dir / "ops/paper_operations_runbook_summary.json"
    text = build_paper_operations_runbook(
        scheduled_run_path=settings_data_dir / "ops/scheduled_run.json",
        daemon_manifest_path=settings_data_dir / "ops/daemon_manifest.json",
        monitoring_snapshot_path=settings_data_dir / "ops/monitoring_status.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        ops_dashboard_summary_path=settings_data_dir / "ops/operations_dashboard_summary.json",
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_paper_cycle_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/paper_cycle_history_report.md"
    summary_out = settings_data_dir / "ops/paper_cycle_history_summary.json"
    text = build_paper_cycle_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_gap_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_gap_history.md"
    summary_out = settings_data_dir / "ops/execution_gap_history_summary.json"
    text = build_execution_gap_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_state_comparison_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_state_comparison_history.md"
    summary_out = settings_data_dir / "ops/execution_state_comparison_history_summary.json"
    text = build_execution_state_comparison_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_snapshot_drift_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_snapshot_drift_history.md"
    summary_out = settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
    text = build_execution_snapshot_drift_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_execution_drift_overview(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/execution_drift_overview.md"
    summary_out = settings_data_dir / "ops/execution_drift_overview_summary.json"
    text = build_execution_drift_overview_report(
        execution_gap_history_summary_path=settings_data_dir
        / "ops/execution_gap_history_summary.json",
        execution_state_comparison_history_summary_path=(
            settings_data_dir / "ops/execution_state_comparison_history_summary.json"
        ),
        execution_snapshot_drift_history_summary_path=(
            settings_data_dir / "ops/execution_snapshot_drift_history_summary.json"
        ),
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_phase_gate_review(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/phase_gate_review.md"
    summary_out = settings_data_dir / "ops/phase_gate_review_summary.json"
    text = build_phase_gate_review(
        settings_data_dir,
        schema_root=Path(__file__).resolve().parents[3] / "schemas",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_planner(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_planner.md"
    summary_out = settings_data_dir / "ops/remediation_planner_summary.json"
    text = build_remediation_planner(
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_execution_plan(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_execution_plan.md"
    summary_out = settings_data_dir / "ops/remediation_execution_plan_summary.json"
    text = build_remediation_execution_plan(
        remediation_planner_summary_path=settings_data_dir / "ops/remediation_planner_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_session(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_session.md"
    summary_out = settings_data_dir / "ops/remediation_session_summary.json"
    text = build_remediation_session(
        remediation_execution_plan_summary_path=settings_data_dir
        / "ops/remediation_execution_plan_summary.json",
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_session_checkpoint(
    settings_data_dir: Path,
    *,
    action_key: str | None = None,
    result: str | None = None,
    note: str | None = None,
    evidence_path: str | None = None,
    observed_signal: str | None = None,
    stdout_summary: str | None = None,
    stderr_summary: str | None = None,
    exit_code: int | None = None,
) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_session_checkpoint.md"
    summary_out = settings_data_dir / "ops/remediation_session_checkpoint_summary.json"
    text = build_remediation_session_checkpoint(
        remediation_session_summary_path=settings_data_dir / "ops/remediation_session_summary.json",
        checkpoint_summary_path=summary_out,
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
        action_key=action_key,
        result=result,
        note=note,
        evidence_path=evidence_path,
        observed_signal=observed_signal,
        stdout_summary=stdout_summary,
        stderr_summary=stderr_summary,
        exit_code=exit_code,
    )
    return out, summary_out, text


def _write_remediation_scoreboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_scoreboard.md"
    summary_out = settings_data_dir / "ops/remediation_scoreboard_summary.json"
    text = build_remediation_scoreboard(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        remediation_command_results_summary_path=settings_data_dir
        / "ops/remediation_command_results_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_evaluator(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_evaluator.md"
    summary_out = settings_data_dir / "ops/remediation_evaluator_summary.json"
    text = build_remediation_evaluator(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_evidence(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_evidence.md"
    summary_out = settings_data_dir / "ops/remediation_evidence_summary.json"
    text = build_remediation_evidence(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        remediation_evaluator_summary_path=settings_data_dir
        / "ops/remediation_evaluator_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_remediation_command_results(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/remediation_command_results.md"
    summary_out = settings_data_dir / "ops/remediation_command_results_summary.json"
    text = build_remediation_command_results(
        remediation_session_checkpoint_summary_path=settings_data_dir
        / "ops/remediation_session_checkpoint_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_operations_bundle(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_bundle_manifest.md"
    manifest_out = settings_data_dir / "ops/operations_bundle_manifest.json"
    text = build_operations_bundle_manifest(
        monitoring_summary_path=settings_data_dir / "ops/monitoring_status.json",
        ops_review_summary_path=settings_data_dir / "ops/ops_review_summary.json",
        dashboard_summary_path=settings_data_dir / "ops/operations_dashboard_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
        paper_cycle_history_summary_path=settings_data_dir / "ops/paper_cycle_history_summary.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_operations_timeline(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_timeline_report.md"
    summary_out = settings_data_dir / "ops/operations_timeline_summary.json"
    text = build_operations_timeline_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_operations_audit_pack(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/operations_audit_pack.md"
    manifest_out = settings_data_dir / "ops/operations_audit_pack.json"
    text = build_operations_audit_pack(
        bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        timeline_summary_path=settings_data_dir / "ops/operations_timeline_summary.json",
        cycle_history_summary_path=settings_data_dir / "ops/paper_cycle_history_summary.json",
        runbook_summary_path=settings_data_dir / "ops/paper_operations_runbook_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_audit_timeline(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_timeline_report.md"
    summary_out = settings_data_dir / "ops/audit_timeline_summary.json"
    text = build_audit_timeline_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_audit_dashboard(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_dashboard.md"
    summary_out = settings_data_dir / "ops/audit_dashboard_summary.json"
    text = build_audit_dashboard(
        bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        audit_pack_path=settings_data_dir / "ops/operations_audit_pack.json",
        audit_timeline_summary_path=settings_data_dir / "ops/audit_timeline_summary.json",
        audit_bundle_history_summary_path=settings_data_dir
        / "ops/audit_bundle_history_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_audit_bundle(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_bundle_manifest.md"
    manifest_out = settings_data_dir / "ops/audit_bundle_manifest.json"
    text = build_audit_bundle_manifest(
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_timeline_summary_path=settings_data_dir / "ops/audit_timeline_summary.json",
        audit_pack_path=settings_data_dir / "ops/operations_audit_pack.json",
        audit_bundle_history_summary_path=settings_data_dir
        / "ops/audit_bundle_history_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        readiness_summary_path=settings_data_dir / "ops/readiness_snapshot.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
        out_path=out,
        manifest_path=manifest_out,
    )
    return out, manifest_out, text


def _write_audit_bundle_history(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/audit_bundle_history_report.md"
    summary_out = settings_data_dir / "ops/audit_bundle_history_summary.json"
    text = build_audit_bundle_history_report(
        operation_chain_path=settings_data_dir / "ops/operation_manifests.jsonl",
        execution_snapshot_summary_path=settings_data_dir / "ops/execution_snapshot_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _latest_live_evidence_summary_path() -> Path | None:
    summaries_root = Path("logs/live_evidence/summaries")
    paths = sorted(summaries_root.glob("live_evidence_summary_*.json"))
    return paths[-1] if paths else None


def _write_current_state_index(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/current_state_index.md"
    summary_out = settings_data_dir / "ops/current_state_index.json"
    text = build_current_state_index(
        operations_dashboard_summary_path=settings_data_dir
        / "ops/operations_dashboard_summary.json",
        operations_bundle_manifest_path=settings_data_dir / "ops/operations_bundle_manifest.json",
        audit_dashboard_summary_path=settings_data_dir / "ops/audit_dashboard_summary.json",
        audit_bundle_manifest_path=settings_data_dir / "ops/audit_bundle_manifest.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        backtest_metrics_summary_path=settings_data_dir / "research/backtest_metrics_summary.json",
        live_evidence_summary_path=_latest_live_evidence_summary_path(),
        research_quality_report_path=settings_data_dir / "research/research_quality_report.md",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text


def _write_readiness_snapshot(settings_data_dir: Path) -> tuple[Path, Path, str]:
    out = settings_data_dir / "reports/readiness_snapshot.md"
    summary_out = settings_data_dir / "ops/readiness_snapshot.json"
    text = build_readiness_snapshot(
        current_state_index_path=settings_data_dir / "ops/current_state_index.json",
        phase_gate_summary_path=settings_data_dir / "ops/phase_gate_review_summary.json",
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
        execution_drift_overview_summary_path=settings_data_dir
        / "ops/execution_drift_overview_summary.json",
        backtest_metrics_summary_path=settings_data_dir / "research/backtest_metrics_summary.json",
        live_evidence_summary_path=_latest_live_evidence_summary_path(),
        operations_dashboard_summary_path=settings_data_dir
        / "ops/operations_dashboard_summary.json",
        out_path=out,
        summary_path=summary_out,
    )
    return out, summary_out, text
