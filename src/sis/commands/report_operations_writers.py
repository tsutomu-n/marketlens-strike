from __future__ import annotations

from pathlib import Path

from sis.commands.report_writer_common import write_operation_chain_report
from sis.reports.operations_audit_pack import build_operations_audit_pack
from sis.reports.operations_bundle import build_operations_bundle_manifest
from sis.reports.operations_dashboard import build_operations_dashboard
from sis.reports.operations_timeline import build_operations_timeline_report
from sis.reports.ops_review import build_ops_review_report
from sis.reports.paper_cycle_history import build_paper_cycle_history_report
from sis.reports.paper_operations_runbook import build_paper_operations_runbook


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
    return write_operation_chain_report(
        settings_data_dir=settings_data_dir,
        report_filename="paper_cycle_history_report.md",
        summary_filename="paper_cycle_history_summary.json",
        build_report=build_paper_cycle_history_report,
    )


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
    return write_operation_chain_report(
        settings_data_dir=settings_data_dir,
        report_filename="operations_timeline_report.md",
        summary_filename="operations_timeline_summary.json",
        build_report=build_operations_timeline_report,
    )


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
