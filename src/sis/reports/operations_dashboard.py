from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_bundle_history_flat_fields,
    audit_bundle_flat_fields,
    audit_dashboard_flat_fields,
    audit_timeline_flat_fields,
    latest_execution_lineage_flat_lines,
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
    phase_gate_issue_preview_lines,
)
from sis.storage.jsonl_store import write_json


def _report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def _quick_navigation(summary: dict[str, object]) -> dict[str, str]:
    phase_gate_summary_path = (
        Path(summary["phase_gate_summary_path"])
        if isinstance(summary.get("phase_gate_summary_path"), str)
        else None
    )
    items = (
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        (
            "current_state_index_report",
            _report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "paper_operations_runbook_report",
            _report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md"),
        ),
        (
            "ops_review_report",
            _report_path_for_summary(phase_gate_summary_path, "ops_review_report.md"),
        ),
        (
            "remediation_scoreboard_report",
            _report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
    )
    return {
        key: value
        for key, value in items
        if isinstance(value, str) and value
    }


def _related_reports(summary: dict[str, object]) -> dict[str, str]:
    phase_gate_summary_path = (
        Path(summary["phase_gate_summary_path"])
        if isinstance(summary.get("phase_gate_summary_path"), str)
        else None
    )
    items = (
        ("operations_dashboard_report", summary.get("operations_dashboard_report_path")),
        (
            "current_state_index_report",
            _report_path_for_summary(phase_gate_summary_path, "current_state_index.md"),
        ),
        (
            "readiness_snapshot_report",
            _report_path_for_summary(phase_gate_summary_path, "readiness_snapshot.md"),
        ),
        ("phase_gate_review_report", summary.get("phase_gate_review_report_path")),
        (
            "paper_operations_runbook_report",
            _report_path_for_summary(phase_gate_summary_path, "paper_operations_runbook.md"),
        ),
        (
            "ops_review_report",
            _report_path_for_summary(phase_gate_summary_path, "ops_review_report.md"),
        ),
        (
            "remediation_scoreboard_report",
            _report_path_for_summary(phase_gate_summary_path, "remediation_scoreboard.md"),
        ),
        (
            "operations_bundle_report",
            _report_path_for_summary(phase_gate_summary_path, "operations_bundle_manifest.md"),
        ),
        (
            "operations_audit_pack_report",
            _report_path_for_summary(phase_gate_summary_path, "operations_audit_pack.md"),
        ),
        (
            "audit_dashboard_report",
            _report_path_for_summary(phase_gate_summary_path, "audit_dashboard.md"),
        ),
        (
            "audit_bundle_report",
            _report_path_for_summary(phase_gate_summary_path, "audit_bundle_manifest.md"),
        ),
    )
    return {
        key: value
        for key, value in items
        if isinstance(value, str) and value
    }


def _execution_adapter_fields(source: dict[str, object], *, prefix: str, mapping: dict[str, str]) -> dict[str, object]:
    if not isinstance(source, dict):
        return {}
    return {
        f"{prefix}_{target}": source.get(source_key)
        for target, source_key in mapping.items()
    }


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
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    execution_balance_fields = _execution_adapter_fields(
        execution_balance_status,
        prefix="execution_balance_status",
        mapping={
            "venue": "venue",
            "currency": "currency",
            "equity": "equity",
            "available_cash": "available_cash",
            "margin_used": "margin_used",
            "notional_usd": "notional_usd",
            "unrealized_pnl": "unrealized_pnl",
            "cumulative_rollover_usd": "cumulative_rollover_usd",
            "snapshot_exists": "balance_snapshot_exists",
            "report_path": "balance_status_report_path",
        },
    )
    execution_fill_fields = _execution_adapter_fields(
        execution_fill_status,
        prefix="execution_fill_status",
        mapping={
            "venue": "venue",
            "fills_count": "fills_count",
            "latest_fill_id": "latest_fill_id",
            "latest_fill_status": "latest_fill_status",
            "report_path": "fill_status_report_path",
        },
    )
    execution_order_fields = _execution_adapter_fields(
        execution_order_status,
        prefix="execution_order_status",
        mapping={
            "venue": "venue",
            "order_id": "order_id",
            "status": "status",
            "symbol": "symbol",
            "report_path": "order_status_report_path",
        },
    )
    execution_cancel_fields = _execution_adapter_fields(
        execution_cancel_order,
        prefix="execution_cancel_order",
        mapping={
            "venue": "venue",
            "action": "action",
            "target": "target",
            "success": "success",
            "status": "status",
            "report_path": "cancel_order_report_path",
        },
    )
    execution_close_fields = _execution_adapter_fields(
        execution_close_position,
        prefix="execution_close_position",
        mapping={
            "venue": "venue",
            "action": "action",
            "target": "target",
            "success": "success",
            "status": "status",
            "report_path": "close_position_report_path",
        },
    )
    execution_reconcile_fields = _execution_adapter_fields(
        execution_reconcile_positions,
        prefix="execution_reconcile_positions",
        mapping={
            "venue": "venue",
            "run_id": "run_id",
            "matched": "matched",
            "missing_in_adapter_count": "missing_in_adapter_count",
            "missing_in_internal_count": "missing_in_internal_count",
            "report_path": "reconcile_positions_report_path",
        },
    )
    execution_read_only_surface_fields = {
        "execution_read_only_surfaces_venue_count": execution_read_only_surfaces.get("venue_count"),
        "execution_read_only_surfaces_with_balance_snapshot_count": execution_read_only_surfaces.get(
            "with_balance_snapshot_count"
        ),
        "execution_read_only_surfaces_with_positions_snapshot_count": execution_read_only_surfaces.get(
            "with_positions_snapshot_count"
        ),
        "execution_read_only_surfaces_with_fills_snapshot_count": execution_read_only_surfaces.get(
            "with_fills_snapshot_count"
        ),
        "execution_read_only_surfaces_with_order_status_snapshot_count": execution_read_only_surfaces.get(
            "with_order_status_snapshot_count"
        ),
        "execution_read_only_surfaces_reconciled_venue_count": execution_read_only_surfaces.get(
            "reconciled_venue_count"
        ),
        "execution_read_only_surfaces_with_positions_financial_totals_count": execution_read_only_surfaces.get(
            "with_positions_financial_totals_count"
        ),
        "execution_read_only_surfaces_with_positions_leverage_metrics_count": execution_read_only_surfaces.get(
            "with_positions_leverage_metrics_count"
        ),
        "execution_read_only_surfaces_with_positions_quantity_metrics_count": execution_read_only_surfaces.get(
            "with_positions_quantity_metrics_count"
        ),
        "execution_read_only_surfaces_positions_notional_usd_total": execution_read_only_surfaces.get(
            "positions_notional_usd_total"
        ),
        "execution_read_only_surfaces_positions_unrealized_pnl_usd_total": execution_read_only_surfaces.get(
            "positions_unrealized_pnl_usd_total"
        ),
        "execution_read_only_surfaces_positions_collateral_used_usd_total": execution_read_only_surfaces.get(
            "positions_collateral_used_usd_total"
        ),
        "execution_read_only_surfaces_positions_max_withdrawable_usd_total": execution_read_only_surfaces.get(
            "positions_max_withdrawable_usd_total"
        ),
        "execution_read_only_surfaces_positions_average_leverage": execution_read_only_surfaces.get(
            "positions_average_leverage"
        ),
        "execution_read_only_surfaces_positions_total_quantity": execution_read_only_surfaces.get(
            "positions_total_quantity"
        ),
        "execution_read_only_surfaces_positions_total_realized_pnl": execution_read_only_surfaces.get(
            "positions_total_realized_pnl"
        ),
        "execution_read_only_surfaces_latest_positions_server_time_ms": execution_read_only_surfaces.get(
            "latest_positions_server_time_ms"
        ),
        "execution_read_only_surfaces_latest_positions_open_timestamp_ms": execution_read_only_surfaces.get(
            "latest_positions_open_timestamp_ms"
        ),
        "execution_read_only_surfaces_latest_positions_updated_at": execution_read_only_surfaces.get(
            "latest_positions_updated_at"
        ),
        "execution_read_only_surfaces_report_path": execution_read_only_surfaces.get(
            "execution_read_only_surfaces_report_path"
        ),
    }
    state_daemon_fields = {
        "daemon_manifest_mode": daemon_manifest.get("mode"),
        "daemon_manifest_command": daemon_manifest.get("command"),
        "daemon_manifest_state_store_path": daemon_manifest.get("state_store_path"),
        "daemon_manifest_report_path": daemon_manifest.get("daemon_manifest_report_path"),
        "state_export_snapshot_path": state_export.get("snapshot_path"),
        "state_export_audit_overall_status": state_export.get("audit_overall_status"),
        "state_export_phase_gate_decision": state_export.get("phase_gate_decision"),
        "state_export_readiness_next_phase_candidate": state_export.get(
            "readiness_next_phase_candidate"
        ),
        "state_export_report_path": state_export.get("state_export_report_path"),
        "state_restore_restored": state_restore.get("restored"),
        "state_restore_snapshot_path": state_restore.get("snapshot_path"),
        "state_restore_audit_overall_status": state_restore.get("audit_overall_status"),
        "state_restore_phase_gate_decision": state_restore.get("phase_gate_decision"),
        "state_restore_report_path": state_restore.get("state_restore_report_path"),
    }
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
        "state_export_summary": state_export,
        "state_restore_summary": state_restore,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        **execution_balance_fields,
        **execution_fill_fields,
        **execution_order_fields,
        **execution_cancel_fields,
        **execution_close_fields,
        **execution_reconcile_fields,
        **execution_read_only_surface_fields,
        **state_daemon_fields,
        **audit_dashboard_fields,
        **audit_bundle_fields,
        **audit_timeline_fields,
        **operations_timeline_fields,
        **audit_bundle_history_fields,
        **phase_gate_fields,
        "phase_gate_phase2_entry_allowed": phase_gate_fields.get("phase2_entry_allowed"),
        "phase_gate_summary_path": str(phase_gate_summary_path) if phase_gate_summary_path else None,
        "operations_dashboard_report_path": str(out_path) if out_path is not None else None,
        "comparison_report_exists": comparison_exists,
        "weekly_review_exists": weekly_exists,
        "lifecycle_report_exists": lifecycle_exists,
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
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
            "data/ops/state_export_summary.json",
            "data/ops/state_restore_summary.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
        ],
    }
    summary["quick_navigation"] = _quick_navigation(summary)
    summary["related_reports"] = _related_reports(summary)

    lines = [
        "# Operations Dashboard",
        "",
        "## Overall",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- monitoring_status: {summary['monitoring_status']}",
        f"- ops_latest_status: {summary['ops_latest_status']}",
        f"- operations_count: {summary['operations_count']}",
        "",
        "## Quick Navigation",
        "",
    ]
    for key, value in summary["quick_navigation"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Decision State",
            "",
            f"- decision_mode: {summary['decision_mode']}",
            f"- executed_count: {summary['executed_count']}",
            f"- blocked_count: {summary['blocked_count']}",
            f"- execution_overall_status: {summary['execution_overall_status']}",
            f"- execution_venue_count: {summary['execution_venue_count']}",
            f"- execution_comparison_all_registries_present: {summary['execution_comparison_all_registries_present']}",
            f"- execution_diagnostics_status: {summary['execution_diagnostics_status']}",
            f"- execution_balance_gap_detected: {summary['execution_balance_gap_detected']}",
            f"- execution_fills_gap_detected: {summary['execution_fills_gap_detected']}",
            f"- execution_gap_history_entry_count: {summary['execution_gap_history_entry_count']}",
            f"- execution_gap_history_latest_status: {summary['execution_gap_history_latest_status']}",
            f"- execution_gap_history_latest_diagnostics_status: {summary['execution_gap_history_latest_diagnostics_status']}",
            f"- execution_state_comparison_entry_count: {summary['execution_state_comparison_entry_count']}",
            (
                "- execution_state_comparison_latest_status_match: "
                f"{summary['execution_state_comparison_latest_status_match']}"
            ),
            (
                "- execution_state_comparison_mismatching_count: "
                f"{summary['execution_state_comparison_mismatching_count']}"
            ),
            f"- execution_snapshot_drift_entry_count: {summary['execution_snapshot_drift_entry_count']}",
            (
                "- execution_snapshot_drift_latest_status_match: "
                f"{summary['execution_snapshot_drift_latest_status_match']}"
            ),
            (
                "- execution_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['execution_snapshot_drift_mismatching_snapshot_count']}"
            ),
            f"- execution_drift_overview_status: {summary['execution_drift_overview_status']}",
            (
                "- execution_drift_overview_diagnostics_alignment_match: "
                f"{summary['execution_drift_overview_diagnostics_alignment_match']}"
            ),
            (
                "- execution_drift_overview_state_comparison_mismatching_count: "
                f"{summary['execution_drift_overview_state_comparison_mismatching_count']}"
            ),
            (
                "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
            ),
            "",
            "## Execution Adapter Surfaces",
            "",
            f"- execution_balance_status_venue: {summary.get('execution_balance_status_venue')}",
            f"- execution_balance_status_currency: {summary.get('execution_balance_status_currency')}",
            f"- execution_balance_status_equity: {summary.get('execution_balance_status_equity')}",
            f"- execution_balance_status_available_cash: {summary.get('execution_balance_status_available_cash')}",
            f"- execution_balance_status_margin_used: {summary.get('execution_balance_status_margin_used')}",
            f"- execution_balance_status_notional_usd: {summary.get('execution_balance_status_notional_usd')}",
            f"- execution_balance_status_unrealized_pnl: {summary.get('execution_balance_status_unrealized_pnl')}",
            f"- execution_balance_status_cumulative_rollover_usd: {summary.get('execution_balance_status_cumulative_rollover_usd')}",
            f"- execution_fill_status_venue: {summary.get('execution_fill_status_venue')}",
            f"- execution_fill_status_fills_count: {summary.get('execution_fill_status_fills_count')}",
            f"- execution_fill_status_latest_fill_id: {summary.get('execution_fill_status_latest_fill_id')}",
            f"- execution_fill_status_latest_fill_status: {summary.get('execution_fill_status_latest_fill_status')}",
            f"- execution_order_status_order_id: {summary.get('execution_order_status_order_id')}",
            f"- execution_order_status_status: {summary.get('execution_order_status_status')}",
            f"- execution_cancel_order_target: {summary.get('execution_cancel_order_target')}",
            f"- execution_cancel_order_status: {summary.get('execution_cancel_order_status')}",
            f"- execution_close_position_target: {summary.get('execution_close_position_target')}",
            f"- execution_close_position_status: {summary.get('execution_close_position_status')}",
            f"- execution_reconcile_positions_matched: {summary.get('execution_reconcile_positions_matched')}",
            (
                "- execution_reconcile_positions_missing_in_adapter_count: "
                f"{summary.get('execution_reconcile_positions_missing_in_adapter_count')}"
            ),
            (
                "- execution_reconcile_positions_missing_in_internal_count: "
                f"{summary.get('execution_reconcile_positions_missing_in_internal_count')}"
            ),
            f"- execution_read_only_surfaces_venue_count: {summary.get('execution_read_only_surfaces_venue_count')}",
            (
                "- execution_read_only_surfaces_with_balance_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_balance_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_fills_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_fills_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_order_status_snapshot_count: "
                f"{summary.get('execution_read_only_surfaces_with_order_status_snapshot_count')}"
            ),
            (
                "- execution_read_only_surfaces_reconciled_venue_count: "
                f"{summary.get('execution_read_only_surfaces_reconciled_venue_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_financial_totals_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_financial_totals_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_leverage_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_leverage_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_with_positions_quantity_metrics_count: "
                f"{summary.get('execution_read_only_surfaces_with_positions_quantity_metrics_count')}"
            ),
            (
                "- execution_read_only_surfaces_positions_notional_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_notional_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_unrealized_pnl_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_unrealized_pnl_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_collateral_used_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_collateral_used_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_max_withdrawable_usd_total: "
                f"{summary.get('execution_read_only_surfaces_positions_max_withdrawable_usd_total')}"
            ),
            (
                "- execution_read_only_surfaces_positions_average_leverage: "
                f"{summary.get('execution_read_only_surfaces_positions_average_leverage')}"
            ),
            (
                "- execution_read_only_surfaces_positions_total_quantity: "
                f"{summary.get('execution_read_only_surfaces_positions_total_quantity')}"
            ),
            (
                "- execution_read_only_surfaces_positions_total_realized_pnl: "
                f"{summary.get('execution_read_only_surfaces_positions_total_realized_pnl')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_server_time_ms: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_server_time_ms')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_open_timestamp_ms: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_open_timestamp_ms')}"
            ),
            (
                "- execution_read_only_surfaces_latest_positions_updated_at: "
                f"{summary.get('execution_read_only_surfaces_latest_positions_updated_at')}"
            ),
            f"- execution_read_only_surfaces_report_path: {summary.get('execution_read_only_surfaces_report_path')}",
            "",
            "## State And Daemon Surfaces",
            "",
            f"- daemon_manifest_mode: {summary.get('daemon_manifest_mode')}",
            f"- daemon_manifest_command: {summary.get('daemon_manifest_command')}",
            f"- daemon_manifest_state_store_path: {summary.get('daemon_manifest_state_store_path')}",
            f"- state_export_snapshot_path: {summary.get('state_export_snapshot_path')}",
            f"- state_export_audit_overall_status: {summary.get('state_export_audit_overall_status')}",
            f"- state_export_phase_gate_decision: {summary.get('state_export_phase_gate_decision')}",
            (
                "- state_export_readiness_next_phase_candidate: "
                f"{summary.get('state_export_readiness_next_phase_candidate')}"
            ),
            f"- state_restore_restored: {summary.get('state_restore_restored')}",
            f"- state_restore_snapshot_path: {summary.get('state_restore_snapshot_path')}",
            f"- state_restore_audit_overall_status: {summary.get('state_restore_audit_overall_status')}",
            f"- state_restore_phase_gate_decision: {summary.get('state_restore_phase_gate_decision')}",
            "",
            "## Audit State",
            "",
            f"- audit_overall_status: {summary['audit_overall_status']}",
            f"- audit_latest_operation: {summary['audit_latest_operation']}",
            f"- audit_entry_count: {summary['audit_entry_count']}",
            f"- audit_bundle_snapshot_count: {summary['audit_bundle_snapshot_count']}",
            f"- audit_bundle_history_snapshot_count: {summary['audit_bundle_history_snapshot_count']}",
            f"- audit_bundle_history_ok_count: {summary['audit_bundle_history_ok_count']}",
            *latest_execution_lineage_flat_lines(summary),
            f"- timeline_latest_remediation_planner_status: {summary['timeline_latest_remediation_planner_status']}",
            f"- timeline_latest_remediation_planner_next_best_command: {summary['timeline_latest_remediation_planner_next_best_command']}",
            f"- timeline_latest_remediation_execution_plan_status: {summary['timeline_latest_remediation_execution_plan_status']}",
            f"- timeline_latest_remediation_execution_plan_next_action_command: {summary['timeline_latest_remediation_execution_plan_next_action_command']}",
            f"- timeline_latest_remediation_session_status: {summary['timeline_latest_remediation_session_status']}",
            f"- timeline_latest_remediation_session_next_pending_command: {summary['timeline_latest_remediation_session_next_pending_command']}",
            f"- timeline_latest_remediation_checkpoint_status: {summary['timeline_latest_remediation_checkpoint_status']}",
            f"- timeline_latest_remediation_checkpoint_next_action_command: {summary['timeline_latest_remediation_checkpoint_next_action_command']}",
            f"- timeline_latest_remediation_scoreboard_status: {summary['timeline_latest_remediation_scoreboard_status']}",
            f"- timeline_latest_remediation_scoreboard_next_action_command: {summary['timeline_latest_remediation_scoreboard_next_action_command']}",
            "",
            "## Phase Gate State",
            "",
            f"- phase_gate_decision: {summary['phase_gate_decision']}",
            f"- phase2_entry_allowed: {summary['phase_gate_phase2_entry_allowed']}",
            f"- phase_gate_reason: {summary['phase_gate_reason']}",
            f"- strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
            f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
            f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
            f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
            "",
            "## Related Reports",
            "",
        ]
    )
    for key, value in summary["related_reports"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Strict Validation Preview",
            "",
        ]
    )
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(
        [
            "",
            "## Artifact Coverage",
            "",
            f"- comparison_report_exists: {summary['comparison_report_exists']}",
            f"- weekly_review_exists: {summary['weekly_review_exists']}",
            f"- lifecycle_report_exists: {summary['lifecycle_report_exists']}",
            "",
            "## Recommended Read Order",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    if monitoring:
        lines.extend(
            [
                "## Monitoring Hints",
                "",
                f"- decision_summary_exists: {monitoring.get('decision_summary_exists')}",
                f"- daily_pnl_exists: {monitoring.get('daily_pnl_exists')}",
                f"- operation_chain_exists: {monitoring.get('operation_chain_exists')}",
                "",
            ]
        )

    if ops_review:
        lines.extend(
            [
                "## Ops Review Hints",
                "",
                f"- latest_operation: {ops_review_fields.get('ops_latest_operation')}",
                f"- latest_scheduled_for: {ops_review_fields.get('ops_latest_scheduled_for')}",
                "",
            ]
        )

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
