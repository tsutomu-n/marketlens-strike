from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.reports.live_evidence_sections import (
    latest_execution_lineage_flat_values,
    latest_execution_lineage_markdown_lines,
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
    phase_gate_flat_fields,
    readiness_flat_fields,
)


def render_live_evidence_followup(data: Any) -> str:
    audit_summary_flat = audit_summary_fields(data.audit_summary, data.audit_summary)
    phase_gate_flat = phase_gate_flat_fields(data.phase_gate_summary)
    readiness_flat = readiness_flat_fields(data.readiness_summary)
    latest_execution_flat = latest_execution_lineage_flat_values(data)
    execution_summary_flat = execution_snapshot_flat_fields(data.execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(data.execution_comparison_summary)
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        data.execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        data.execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        data.execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        data.execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        data.execution_drift_overview_summary
    )
    path_source = (
        data.log_path
        if str(data.log_path) not in {"", "."}
        else (data.manifest_path or data.log_path)
    )
    reports_dir = (
        data.output_path.parent if data.output_path.parent != Path(".") else Path("data/reports")
    )
    quick_navigation = [
        f"- live_evidence_followup_report: `{default_followup_output_path(path_source)}`",
        f"- live_evidence_report: `{data.output_path}`",
        f"- current_state_index_report: `{reports_dir / 'current_state_index.md'}`",
        f"- readiness_snapshot_report: `{reports_dir / 'readiness_snapshot.md'}`",
        f"- phase_gate_review_report: `{phase_gate_flat.get('phase_gate_review_report_path') or (reports_dir / 'phase_gate_review.md')}`",
        f"- remediation_scoreboard_report: `{reports_dir / 'remediation_scoreboard.md'}`",
    ]
    related_reports = [
        f"- live_evidence_followup_report: `{default_followup_output_path(path_source)}`",
        f"- live_evidence_report: `{data.output_path}`",
        f"- operations_dashboard_report: `{reports_dir / 'operations_dashboard.md'}`",
        f"- ops_review_report: `{reports_dir / 'ops_review.md'}`",
        f"- current_state_index_report: `{reports_dir / 'current_state_index.md'}`",
        f"- readiness_snapshot_report: `{reports_dir / 'readiness_snapshot.md'}`",
        f"- phase_gate_review_report: `{phase_gate_flat.get('phase_gate_review_report_path') or (reports_dir / 'phase_gate_review.md')}`",
        f"- paper_operations_runbook_report: `{reports_dir / 'paper_operations_runbook.md'}`",
        "- go_no_go_report: `data/research/go_no_go_report.md`",
        f"- paper_vs_backtest_comparison_report: `{reports_dir / 'paper_vs_backtest_comparison.md'}`",
    ]
    lines = [
        "# Live Evidence Follow-up",
        "",
        "## Current State",
        "",
        f"- run_status: `{data.status}`",
        f"- decision: `{data.decision}`",
        f"- markdown_report: `{data.output_path}`",
        f"- html_report: `{default_html_output_path(path_source)}`",
        f"- manifest_path: `{data.manifest_path}`",
        "",
        "## Quick Navigation",
        "",
        *quick_navigation,
        "",
        "## Related Reports",
        "",
        *related_reports,
        "",
        "## Audit Summary",
        "",
        f"- overall_status: `{audit_summary_flat.get('overall_status')}`",
        f"- latest_operation: `{audit_summary_flat.get('latest_operation')}`",
        (
            "- bundle_history_snapshot_count: "
            f"`{audit_summary_flat.get('bundle_history_snapshot_count')}`"
        ),
        "",
        "## Phase Gate Summary",
        "",
        f"- decision: `{phase_gate_flat.get('phase_gate_decision')}`",
        f"- phase2_entry_allowed: `{phase_gate_flat.get('phase2_entry_allowed')}`",
        f"- phase_gate_reason: `{phase_gate_flat.get('phase_gate_reason')}`",
        f"- strict_validation_passed: `{phase_gate_flat.get('strict_validation_passed')}`",
        (
            "- phase_gate_strict_validation_issue_count: "
            f"`{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}`"
        ),
        f"- phase_gate_checked_files: `{phase_gate_flat.get('phase_gate_checked_files')}`",
        "",
        "## Readiness Summary",
        "",
        f"- next_phase_candidate: `{readiness_flat.get('readiness_next_phase_candidate')}`",
        f"- execution_ready: `{readiness_flat.get('readiness_execution_ready')}`",
        "",
        "## Latest Execution Lineage",
        "",
        *latest_execution_lineage_markdown_lines(latest_execution_flat),
        "",
        "## Execution Snapshot",
        "",
        f"- overall_status: `{execution_summary_flat.get('execution_overall_status')}`",
        f"- venue_count: `{execution_summary_flat.get('execution_venue_count')}`",
        f"- report_path: `{execution_summary_flat.get('execution_report_path')}`",
        "",
        "## Execution Venue Comparison",
        "",
        f"- all_registries_present: `{execution_comparison_flat.get('execution_comparison_all_registries_present')}`",
        f"- report_path: `{execution_comparison_flat.get('execution_comparison_report_path')}`",
        "",
        "## Execution Venue Diagnostics",
        "",
        f"- overall_status: `{execution_diagnostics_flat.get('execution_diagnostics_status')}`",
        f"- balance_gap_detected: `{execution_diagnostics_flat.get('execution_balance_gap_detected')}`",
        f"- fills_gap_detected: `{execution_diagnostics_flat.get('execution_fills_gap_detected')}`",
        f"- report_path: `{execution_diagnostics_flat.get('execution_diagnostics_report_path')}`",
        "",
        "## Execution Gap History",
        "",
        f"- entry_count: `{execution_gap_history_flat.get('execution_gap_history_entry_count')}`",
        f"- latest_status: `{execution_gap_history_flat.get('execution_gap_history_latest_status')}`",
        f"- latest_execution_diagnostics_status: `{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status')}`",
        f"- report_path: `{execution_gap_history_flat.get('execution_gap_history_report_path')}`",
        "",
        "## Execution State Comparison History",
        "",
        f"- entry_count: `{execution_state_comparison_flat.get('execution_state_comparison_entry_count')}`",
        f"- latest_status_match: `{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}`",
        f"- mismatching_count: `{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}`",
        f"- report_path: `{execution_state_comparison_flat.get('execution_state_comparison_report_path')}`",
        "",
        "## Execution Snapshot Drift History",
        "",
        f"- entry_count: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}`",
        f"- latest_execution_state_comparison_status_match: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}`",
        f"- mismatching_snapshot_count: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}`",
        f"- report_path: `{execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path')}`",
        "",
        "## Execution Drift Overview",
        "",
        f"- overall_status: `{execution_drift_flat.get('execution_drift_overview_status')}`",
        f"- diagnostics_alignment_match: `{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}`",
        f"- state_comparison_mismatching_count: `{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}`",
        f"- snapshot_drift_mismatching_snapshot_count: `{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}`",
        "",
        "## Immediate Next Work",
        "",
    ]
    if data.status == "running":
        lines.append(
            "- collection is still running; wait for terminal status before touching downstream artifacts"
        )
    elif data.status in {"failed", "failed_preflight", "failed_collection"}:
        lines.append(
            "- inspect the failure point in the log tail and fix the first blocking error before rerunning"
        )
    elif data.status == "partial_failed":
        lines.append(
            "- inspect the failed step and rerun after fixing the recorded blocker; raw data and diagnostics are already available"
        )
    elif data.status == "completed_with_retries":
        lines.append(
            "- review the retried steps and remove the underlying instability before the next live run"
        )
    elif data.next_actions:
        lines.extend(f"- {item}" for item in data.next_actions)
    else:
        lines.append("- no blocking follow-up was emitted by the report")
    lines.extend(
        [
            "",
            "## Log Tail",
            "",
            "```text",
            *data.log_tail,
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def default_html_output_path(log_path: Path) -> Path:
    stem = log_path.stem.replace("live_evidence_", "")
    return Path("docs/live_evidence_reports") / f"live_evidence_report_{stem}.html"


def default_followup_output_path(log_path: Path) -> Path:
    stem = log_path.stem.replace("live_evidence_", "")
    return Path("docs/live_evidence_reports") / f"live_evidence_followup_{stem}.md"
