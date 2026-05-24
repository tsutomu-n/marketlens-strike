from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    audit_summary_fields,
    audit_dashboard_flat_fields,
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
    normalize_phase_gate_summary,
    phase_gate_flat_fields,
    phase_gate_issue_preview_lines,
)
from sis.storage.jsonl_store import read_json, write_json


def _safe_read_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def build_current_state_index(
    *,
    operations_dashboard_summary_path: Path | None = None,
    operations_bundle_manifest_path: Path | None = None,
    audit_dashboard_summary_path: Path | None = None,
    audit_bundle_manifest_path: Path | None = None,
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
    research_quality_report_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations_dashboard = _safe_read_json(operations_dashboard_summary_path)
    operations_bundle = _safe_read_json(operations_bundle_manifest_path)
    audit_dashboard = _safe_read_json(audit_dashboard_summary_path)
    audit_bundle = _safe_read_json(audit_bundle_manifest_path)
    phase_gate = normalize_phase_gate_summary(_safe_read_json(phase_gate_summary_path))
    execution_snapshot = normalize_execution_snapshot_summary(_safe_read_json(execution_snapshot_summary_path))
    execution_comparison = normalize_execution_comparison_summary(
        _safe_read_json(execution_venue_comparison_summary_path)
    )
    execution_diagnostics = normalize_execution_diagnostics_summary(
        _safe_read_json(execution_venue_diagnostics_summary_path)
    )
    execution_gap_history = normalize_execution_gap_history_summary(
        _safe_read_json(execution_gap_history_summary_path)
    )
    execution_state_comparison_history = normalize_execution_state_comparison_summary(
        _safe_read_json(execution_state_comparison_history_summary_path)
    )
    execution_snapshot_drift_history = normalize_execution_snapshot_drift_summary(
        _safe_read_json(execution_snapshot_drift_history_summary_path)
    )
    execution_drift_overview = normalize_execution_drift_overview_summary(
        _safe_read_json(execution_drift_overview_summary_path)
    )
    execution_snapshot_fields = execution_snapshot_flat_fields(execution_snapshot)
    execution_comparison_fields = execution_comparison_flat_fields(execution_comparison)
    execution_diagnostics_fields = execution_diagnostics_flat_fields(execution_diagnostics)
    execution_gap_history_fields = execution_gap_history_flat_fields(execution_gap_history)
    execution_state_comparison_fields = execution_state_comparison_flat_fields(
        execution_state_comparison_history
    )
    execution_snapshot_drift_fields = execution_snapshot_drift_flat_fields(
        execution_snapshot_drift_history
    )
    phase_gate_fields = phase_gate_flat_fields(phase_gate)
    execution_drift_fields = execution_drift_overview_flat_fields(execution_drift_overview)
    audit_dashboard_fields = audit_dashboard_flat_fields(audit_dashboard)
    audit_summary = audit_summary_fields(audit_dashboard, audit_bundle)
    backtest_metrics_summary = _safe_read_json(backtest_metrics_summary_path)
    live_evidence_summary = _safe_read_json(live_evidence_summary_path)

    summary = {
        "overall_status": operations_dashboard.get("overall_status") or operations_bundle.get("overall_status"),
        "phase_gate_summary": phase_gate,
        "audit_summary": audit_summary,
        **phase_gate_fields,
        **audit_dashboard_fields,
        "operations_cycle_count": operations_bundle.get("cycle_count"),
        "execution_summary": execution_snapshot,
        "execution_comparison_summary": execution_comparison,
        "execution_diagnostics_summary": execution_diagnostics,
        "execution_gap_history_summary": execution_gap_history,
        "execution_state_comparison_summary": execution_state_comparison_history,
        "execution_snapshot_drift_summary": execution_snapshot_drift_history,
        "execution_drift_overview_summary": execution_drift_overview,
        **execution_snapshot_fields,
        **execution_comparison_fields,
        **execution_diagnostics_fields,
        "execution_comparison_ready": execution_comparison_fields.get(
            "execution_comparison_all_registries_present"
        ),
        **execution_gap_history_fields,
        **execution_state_comparison_fields,
        **execution_snapshot_drift_fields,
        **execution_drift_fields,
        "backtest_total_trade_count": backtest_metrics_summary.get("total_trade_count"),
        "backtest_symbols": backtest_metrics_summary.get("symbols", []),
        "live_evidence_status": live_evidence_summary.get("status"),
        "live_evidence_decision": live_evidence_summary.get("decision"),
        "live_evidence_run_id": live_evidence_summary.get("run_id"),
        "research_quality_report_exists": bool(research_quality_report_path and research_quality_report_path.exists()),
        "artifacts": {
            "operations_dashboard_summary": str(operations_dashboard_summary_path) if operations_dashboard_summary_path else None,
            "operations_bundle_manifest": str(operations_bundle_manifest_path) if operations_bundle_manifest_path else None,
            "audit_dashboard_summary": str(audit_dashboard_summary_path) if audit_dashboard_summary_path else None,
            "audit_bundle_manifest": str(audit_bundle_manifest_path) if audit_bundle_manifest_path else None,
            "phase_gate_summary": str(phase_gate_summary_path) if phase_gate_summary_path else None,
            "execution_snapshot_summary": str(execution_snapshot_summary_path) if execution_snapshot_summary_path else None,
            "execution_venue_comparison_summary": (
                str(execution_venue_comparison_summary_path)
                if execution_venue_comparison_summary_path
                else None
            ),
            "execution_venue_diagnostics_summary": (
                str(execution_venue_diagnostics_summary_path)
                if execution_venue_diagnostics_summary_path
                else None
            ),
            "execution_gap_history_summary": (
                str(execution_gap_history_summary_path) if execution_gap_history_summary_path else None
            ),
            "execution_state_comparison_history_summary": (
                str(execution_state_comparison_history_summary_path)
                if execution_state_comparison_history_summary_path
                else None
            ),
            "execution_snapshot_drift_history_summary": (
                str(execution_snapshot_drift_history_summary_path)
                if execution_snapshot_drift_history_summary_path
                else None
            ),
            "execution_drift_overview_summary": (
                str(execution_drift_overview_summary_path) if execution_drift_overview_summary_path else None
            ),
            "backtest_metrics_summary": str(backtest_metrics_summary_path) if backtest_metrics_summary_path else None,
            "live_evidence_summary": str(live_evidence_summary_path) if live_evidence_summary_path else None,
            "research_quality_report": str(research_quality_report_path) if research_quality_report_path else None,
        },
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/current_state_index.json",
            "data/ops/phase_gate_review_summary.json",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_gap_history_summary.json",
            "data/ops/execution_state_comparison_history_summary.json",
            "data/ops/execution_snapshot_drift_history_summary.json",
            "data/ops/execution_drift_overview_summary.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/audit_dashboard_summary.json",
            "data/ops/operations_bundle_manifest.json",
            "data/ops/audit_bundle_manifest.json",
            "data/research/backtest_metrics_summary.json",
        ],
    }

    lines = [
        "# Current State Index",
        "",
        "## Overview",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- phase_gate_decision: {summary['phase_gate_decision']}",
        f"- phase2_entry_allowed: {summary['phase2_entry_allowed']}",
        f"- phase_gate_reason: {summary['phase_gate_reason']}",
        f"- phase_gate_strict_validation_passed: {summary['phase_gate_strict_validation_passed']}",
        f"- phase_gate_strict_validation_issue_count: {summary['phase_gate_strict_validation_issue_count']}",
        f"- phase_gate_checked_files: {summary['phase_gate_checked_files']}",
        f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
        f"- audit_overall_status: {summary['audit_overall_status']}",
        f"- audit_latest_operation: {summary['audit_latest_operation']}",
        "",
        "## Strict Validation Preview",
        "",
    ]
    validation_issue_previews = phase_gate_issue_preview_lines(summary)
    if validation_issue_previews:
        lines.extend(f"- {item}" for item in validation_issue_previews)
    else:
        lines.append("- issues: none")
    lines.extend(
        [
            "",
        "## Research And Backtest",
        "",
        f"- execution_overall_status: {summary['execution_overall_status']}",
        f"- execution_venue_count: {summary['execution_venue_count']}",
        f"- execution_comparison_ready: {summary['execution_comparison_ready']}",
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
        f"- backtest_total_trade_count: {summary['backtest_total_trade_count']}",
        f"- backtest_symbols: {summary['backtest_symbols']}",
        f"- research_quality_report_exists: {summary['research_quality_report_exists']}",
        "",
        "## Live Evidence",
        "",
        f"- live_evidence_status: {summary['live_evidence_status']}",
        f"- live_evidence_decision: {summary['live_evidence_decision']}",
        f"- live_evidence_run_id: {summary['live_evidence_run_id']}",
        "",
        "## Operations",
        "",
        f"- operations_cycle_count: {summary['operations_cycle_count']}",
        "",
        "## Artifact Paths",
        "",
        ]
    )
    for key, value in summary["artifacts"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
