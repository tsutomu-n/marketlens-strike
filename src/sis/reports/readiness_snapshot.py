from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import normalized_summary, safe_read_json_dict
from sis.reports import readiness_snapshot_navigation
from sis.reports.readiness_snapshot_inputs import execution_adapter_fields
from sis.reports.readiness_snapshot_markdown import render_readiness_snapshot_markdown
from sis.reports.readiness_snapshot_order import readiness_snapshot_recommended_read_order
from sis.reports.readiness_snapshot_status import (
    backtest_ready as backtest_is_ready,
    execution_ready as execution_is_ready,
    live_evidence_ready as live_evidence_is_ready,
    operations_ready as operations_is_ready,
    phase_candidate,
)
from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    latest_execution_lineage_fields_from_summary,
    phase_gate_flat_fields,
)
from sis.storage.jsonl_store import write_json


_remediation_fields_from_sources = readiness_snapshot_navigation.remediation_fields_from_sources
_restart_pointers_from_paths = readiness_snapshot_navigation.restart_pointers_from_paths
_artifacts_from_paths = readiness_snapshot_navigation.artifacts_from_paths
_related_reports = readiness_snapshot_navigation.related_reports
_quick_navigation = readiness_snapshot_navigation.quick_navigation


def build_readiness_snapshot(
    *,
    current_state_index_path: Path | None = None,
    phase_gate_summary_path: Path | None = None,
    execution_snapshot_summary_path: Path | None = None,
    execution_venue_comparison_summary_path: Path | None = None,
    execution_venue_diagnostics_summary_path: Path | None = None,
    execution_gap_history_summary_path: Path | None = None,
    execution_state_comparison_history_summary_path: Path | None = None,
    execution_snapshot_drift_history_summary_path: Path | None = None,
    execution_drift_overview_summary_path: Path | None = None,
    backtest_metrics_summary_path: Path | None = None,
    live_evidence_summary_path: Path | None = None,
    operations_dashboard_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    current_state = safe_read_json_dict(current_state_index_path)
    phase_gate = normalized_summary(phase_gate_summary_path, normalize_phase_gate_summary)
    execution = normalized_summary(
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
    execution_state_comparison_history = normalized_summary(
        execution_state_comparison_history_summary_path,
        normalize_execution_state_comparison_summary,
    )
    execution_snapshot_drift_history = normalized_summary(
        execution_snapshot_drift_history_summary_path,
        normalize_execution_snapshot_drift_summary,
    )
    execution_drift_overview = normalized_summary(
        execution_drift_overview_summary_path,
        normalize_execution_drift_overview_summary,
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    execution_snapshot_fields = execution_snapshot_flat_fields(execution)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison_history
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_history
    )
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    latest_execution_lineage = latest_execution_lineage_fields_from_summary(current_state)
    backtest = safe_read_json_dict(backtest_metrics_summary_path)
    live_evidence = safe_read_json_dict(live_evidence_summary_path)
    operations = safe_read_json_dict(operations_dashboard_summary_path)
    execution_adapter_summary_fields = execution_adapter_fields(operations)
    remediation_fields = _remediation_fields_from_sources(current_state, operations)
    restart_pointers = _restart_pointers_from_paths(
        out_path=out_path,
        current_state_index_path=current_state_index_path,
        operations_dashboard_summary_path=operations_dashboard_summary_path,
        live_evidence_summary_path=live_evidence_summary_path,
        live_evidence=live_evidence,
    )
    phase_gate_review_report_path = phase_gate_fields.get("phase_gate_review_report_path")
    quick_navigation = _quick_navigation(
        restart_pointers,
        phase_gate_review_report_path,
    )
    related_reports = _related_reports(
        restart_pointers,
        phase_gate_review_report_path,
    )
    artifacts = _artifacts_from_paths(
        current_state_index_path=current_state_index_path,
        phase_gate_summary_path=phase_gate_summary_path,
        execution_snapshot_summary_path=execution_snapshot_summary_path,
        execution_venue_comparison_summary_path=execution_venue_comparison_summary_path,
        execution_venue_diagnostics_summary_path=execution_venue_diagnostics_summary_path,
        execution_gap_history_summary_path=execution_gap_history_summary_path,
        execution_state_comparison_history_summary_path=execution_state_comparison_history_summary_path,
        execution_snapshot_drift_history_summary_path=execution_snapshot_drift_history_summary_path,
        execution_drift_overview_summary_path=execution_drift_overview_summary_path,
        backtest_metrics_summary_path=backtest_metrics_summary_path,
        live_evidence_summary_path=live_evidence_summary_path,
        operations_dashboard_summary_path=operations_dashboard_summary_path,
        restart_pointers=restart_pointers,
    )
    recommended_read_order_items = readiness_snapshot_recommended_read_order()

    phase2_entry_allowed = bool(phase_gate_fields.get("phase2_entry_allowed"))
    execution_ready = execution_is_ready(
        execution_snapshot_fields=execution_snapshot_fields,
        execution_comparison_fields=execution_comparison_fields,
        execution_diagnostics_fields=execution_diagnostics_fields,
        execution_gap_history_fields=execution_gap_history_fields,
        execution_state_comparison_fields=execution_state_comparison_fields,
        execution_snapshot_drift_fields=execution_snapshot_drift_fields,
        execution_drift_fields=execution_drift_fields,
    )
    backtest_ready = backtest_is_ready(backtest)
    live_evidence_ready = live_evidence_is_ready(live_evidence)
    operations_ready = operations_is_ready(operations)
    next_phase_candidate = phase_candidate(phase2_entry_allowed)

    summary = {
        "overall_status": current_state.get("overall_status") or operations.get("overall_status"),
        "phase_gate_decision": phase_gate_fields.get("phase_gate_decision"),
        "phase2_entry_allowed": phase2_entry_allowed,
        "phase2_entry_reason": phase_gate_fields.get("phase2_entry_reason"),
        "phase_gate_reason": phase_gate_fields.get("phase_gate_reason"),
        "phase_gate_strict_validation_passed": phase_gate_fields.get(
            "phase_gate_strict_validation_passed"
        ),
        "phase_gate_strict_validation_issue_count": phase_gate_fields.get(
            "phase_gate_strict_validation_issue_count"
        ),
        "phase_gate_checked_files": phase_gate_fields.get("phase_gate_checked_files"),
        "phase_gate_review_report_path": phase_gate_fields.get("phase_gate_review_report_path"),
        "phase_gate_strict_validation_issues": phase_gate_fields.get(
            "phase_gate_strict_validation_issues"
        ),
        "phase_gate_summary": phase_gate,
        **latest_execution_lineage,
        "execution_summary": execution,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison_history,
        "execution_snapshot_drift_summary": execution_snapshot_drift_history,
        "execution_drift_overview_summary": execution_drift_overview,
        "execution_ready": execution_ready,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        "backtest_ready": backtest_ready,
        "backtest_total_trade_count": backtest.get("total_trade_count"),
        "live_evidence_ready": live_evidence_ready,
        "live_evidence_status": live_evidence.get("status"),
        "live_evidence_decision": live_evidence.get("decision"),
        "live_evidence_report_path": restart_pointers.get("live_evidence_report"),
        "operations_ready": operations_ready,
        "operations_overall_status": operations.get("overall_status"),
        "research_quality_report_exists": current_state.get("research_quality_report_exists"),
        "next_phase_candidate": next_phase_candidate,
        "readiness_next_phase_candidate": next_phase_candidate,
        "readiness_execution_ready": execution_ready,
        **execution_adapter_summary_fields,
        **remediation_fields,
        "quick_navigation": quick_navigation,
        "restart_pointers": restart_pointers,
        "related_reports": related_reports,
        "artifacts": artifacts,
        "recommended_read_order": recommended_read_order_items,
    }

    text = render_readiness_snapshot_markdown(summary)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
