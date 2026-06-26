from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order
from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports import operations_dashboard_navigation
from sis.reports.operations_dashboard_fields import (
    execution_adapter_status_fields as _execution_adapter_status_fields,
    read_only_surface_fields as _read_only_surface_fields,
    state_daemon_fields as _state_daemon_fields,
)
from sis.reports.operations_dashboard_markdown import render_operations_dashboard_markdown
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_bundle_flat_fields,
    audit_dashboard_flat_fields,
    audit_timeline_flat_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    ops_review_flat_fields,
    normalize_phase_gate_summary,
    merged_latest_execution_lineage_fields,
    phase_gate_flat_fields,
)
from sis.storage.jsonl_store import write_json


_report_path_for_summary = operations_dashboard_navigation.report_path_for_summary
_quick_navigation = operations_dashboard_navigation.quick_navigation
_related_reports = operations_dashboard_navigation.related_reports


def build_operations_dashboard(
    *,
    monitoring_snapshot_path: Path | None = None,
    ops_review_summary_path: Path | None = None,
    operations_timeline_summary_path: Path | None = None,
    decision_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    execution_balance_status_summary_path: Path | None = None,
    execution_fill_status_summary_path: Path | None = None,
    execution_order_status_summary_path: Path | None = None,
    execution_cancel_order_summary_path: Path | None = None,
    execution_close_position_summary_path: Path | None = None,
    execution_reconcile_positions_summary_path: Path | None = None,
    execution_read_only_surfaces_summary_path: Path | None = None,
    daemon_manifest_summary_path: Path | None = None,
    daemon_loop_summary_path: Path | None = None,
    notification_outbox_summary_path: Path | None = None,
    state_export_summary_path: Path | None = None,
    state_restore_summary_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    comparison_report_path: Path | None = None,
    weekly_review_path: Path | None = None,
    lifecycle_report_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    monitoring = safe_read_json_dict(monitoring_snapshot_path)
    ops_review = safe_read_json_dict(ops_review_summary_path)
    operations_timeline = safe_read_json_dict(operations_timeline_summary_path)
    decision_summary = safe_read_json_dict(decision_summary_path)
    execution_snapshot = normalized_summary(
        execution_snapshot_summary_path,
        normalize_execution_snapshot_summary,
    )
    execution_comparison = normalized_summary(
        execution_venue_comparison_summary_path,
        normalize_execution_comparison_summary,
    )
    execution_diagnostics = normalized_summary(
        execution_venue_diagnostics_summary_path,
        normalize_execution_diagnostics_summary,
    )
    execution_gap_history = normalized_summary(
        execution_gap_history_summary_path,
        normalize_execution_gap_history_summary,
    )
    execution_state_comparison = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    execution_balance_status = safe_read_json_dict(execution_balance_status_summary_path)
    execution_fill_status = safe_read_json_dict(execution_fill_status_summary_path)
    execution_order_status = safe_read_json_dict(execution_order_status_summary_path)
    execution_cancel_order = safe_read_json_dict(execution_cancel_order_summary_path)
    execution_close_position = safe_read_json_dict(execution_close_position_summary_path)
    execution_reconcile_positions = safe_read_json_dict(execution_reconcile_positions_summary_path)
    execution_read_only_surfaces = safe_read_json_dict(execution_read_only_surfaces_summary_path)
    daemon_manifest = safe_read_json_dict(daemon_manifest_summary_path)
    daemon_loop = safe_read_json_dict(daemon_loop_summary_path)
    notification_outbox = safe_read_json_dict(notification_outbox_summary_path)
    state_export = safe_read_json_dict(state_export_summary_path)
    state_restore = safe_read_json_dict(state_restore_summary_path)
    audit_dashboard = safe_read_json_dict(audit_dashboard_summary_path)
    audit_bundle = safe_read_json_dict(audit_bundle_summary_path)
    operations_bundle = safe_read_json_dict(operations_bundle_manifest_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_snapshot)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(execution_snapshot_drift)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    execution_adapter_fields = _execution_adapter_status_fields(
        balance_status=execution_balance_status,
        fill_status=execution_fill_status,
        order_status=execution_order_status,
        cancel_order=execution_cancel_order,
        close_position=execution_close_position,
        reconcile_positions=execution_reconcile_positions,
    )
    execution_read_only_surface_fields = _read_only_surface_fields(execution_read_only_surfaces)
    state_daemon_fields = _state_daemon_fields(
        daemon_manifest=daemon_manifest,
        daemon_loop=daemon_loop,
        notification_outbox=notification_outbox,
        state_export=state_export,
        state_restore=state_restore,
    )
    ops_review_fields = ops_review_flat_fields(ops_review)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_bundle_fields = audit_bundle_flat_fields(audit_bundle)
    audit_timeline_fields = audit_timeline_flat_fields(audit_dashboard)
    operations_timeline_fields = {
        key: value
        for key, value in audit_timeline_flat_fields(operations_timeline).items()
        if key.startswith("timeline_latest_remediation_")
    }
    audit_bundle_history_fields = audit_bundle_history_flat_fields(audit_bundle)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    latest_execution_lineage = merged_latest_execution_lineage_fields(
        audit_dashboard,
        audit_bundle,
        operations_bundle,
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate)

    comparison_exists = bool(comparison_report_path and comparison_report_path.exists())
    weekly_exists = bool(weekly_review_path and weekly_review_path.exists())
    lifecycle_exists = bool(lifecycle_report_path and lifecycle_report_path.exists())

    overall_status = "ok"
    if monitoring.get("status") == "degraded":
        overall_status = "degraded"
    if ops_review_fields.get("ops_latest_status") == "blocked":
        overall_status = "blocked"

    summary = {
        "overall_status": overall_status,
        "monitoring_status": monitoring.get("status"),
        "ops_latest_status": ops_review_fields.get("ops_latest_status"),
        "operations_count": ops_review_fields.get("ops_operations_count"),
        "decision_mode": decision_summary.get("mode"),
        "executed_count": decision_summary.get("executed_count"),
        "blocked_count": decision_summary.get("blocked_count"),
        "phase_gate_summary": phase_gate,
        "audit_summary": audit_summary,
        **latest_execution_lineage,
        "execution_summary": execution_snapshot,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison,
        "execution_snapshot_drift_summary": execution_snapshot_drift,
        "execution_drift_overview_summary": execution_drift_overview,
        "execution_balance_status_summary": execution_balance_status,
        "execution_fill_status_summary": execution_fill_status,
        "execution_order_status_summary": execution_order_status,
        "execution_cancel_order_summary": execution_cancel_order,
        "execution_close_position_summary": execution_close_position,
        "execution_reconcile_positions_summary": execution_reconcile_positions,
        "execution_read_only_surfaces_summary": execution_read_only_surfaces,
        "daemon_manifest_summary": daemon_manifest,
        "daemon_loop_summary": daemon_loop,
        "notification_outbox_summary": notification_outbox,
        "state_export_summary": state_export,
        "state_restore_summary": state_restore,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **execution_adapter_fields,
        **execution_read_only_surface_fields,
        **state_daemon_fields,
        **audit_dashboard_fields,
        **audit_bundle_fields,
        **audit_timeline_fields,
        **operations_timeline_fields,
        **audit_bundle_history_fields,
        **phase_gate_fields,
        "phase_gate_phase2_entry_allowed": phase_gate_fields.get("phase2_entry_allowed"),
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path
        else None,
        "operations_dashboard_report_path": str(out_path) if out_path is not None else None,
        "comparison_report_exists": comparison_exists,
        "weekly_review_exists": weekly_exists,
        "lifecycle_report_exists": lifecycle_exists,
        "recommended_read_order": recommended_read_order(
            [
                "data/ops/execution_snapshot_summary.json",
                "data/ops/execution_venue_comparison_summary.json",
                "data/ops/execution_venue_diagnostics_summary.json",
                "data/ops/execution_gap_history_summary.json",
                "data/ops/execution_state_comparison_history_summary.json",
                "data/ops/execution_snapshot_drift_history_summary.json",
                "data/ops/execution_drift_overview_summary.json",
                "data/ops/execution_balance_status_summary.json",
                "data/ops/execution_fill_status_summary.json",
                "data/ops/execution_order_status_summary.json",
                "data/ops/execution_cancel_order_summary.json",
                "data/ops/execution_close_position_summary.json",
                "data/ops/execution_reconcile_positions_summary.json",
                "data/ops/execution_read_only_surfaces_summary.json",
                "data/ops/daemon_manifest_summary.json",
                "data/ops/daemon_loop_summary.json",
                "data/ops/notification_outbox_summary.json",
                "data/ops/state_export_summary.json",
                "data/ops/state_restore_summary.json",
                "data/ops/operations_dashboard_summary.json",
                "data/ops/audit_dashboard_summary.json",
                "data/ops/operations_bundle_manifest.json",
                "data/ops/audit_bundle_manifest.json",
            ]
        ),
    }
    quick_navigation = _quick_navigation(summary)
    related_reports = _related_reports(summary)
    recommended_read_order_items = recommended_read_order(
        [
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/execution_balance_status_summary.json",
            "data/ops/execution_fill_status_summary.json",
            "data/ops/execution_order_status_summary.json",
            "data/ops/execution_cancel_order_summary.json",
            "data/ops/execution_close_position_summary.json",
            "data/ops/execution_reconcile_positions_summary.json",
            "data/ops/execution_read_only_surfaces_summary.json",
            "data/ops/daemon_manifest_summary.json",
            "data/ops/daemon_loop_summary.json",
            "data/ops/notification_outbox_summary.json",
            "data/ops/state_export_summary.json",
            "data/ops/state_restore_summary.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
        ]
    )
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports
    summary["recommended_read_order"] = recommended_read_order_items

    text = render_operations_dashboard_markdown(
        summary,
        monitoring=monitoring,
        ops_review_fields=ops_review_fields if ops_review else None,
    )
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
