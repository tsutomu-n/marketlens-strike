from __future__ import annotations

from sis.reports.operations_timeline_markdown import render_operations_timeline_markdown


def _summary() -> dict[str, object]:
    return {
        "operation_count": 2,
        "recent_count": 2,
        "latest_operation": "remediation_scoreboard",
        "latest_status": "retrying",
        "latest_execution_overall_status": "ok",
        "latest_execution_venue_count": 2,
        "latest_execution_comparison_all_registries_present": True,
        "latest_execution_diagnostics_status": "degraded",
        "latest_execution_drift_overview_status": "degraded",
        "latest_execution_drift_overview_diagnostics_alignment_match": "False",
        "latest_execution_drift_overview_state_comparison_mismatching_count": "1",
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": "1",
        "latest_execution_gap_history_status": "ok",
        "latest_execution_gap_history_diagnostics_status": "degraded",
        "latest_execution_state_comparison_status_match": "False",
        "latest_execution_state_comparison_mismatching_count": "1",
        "latest_readiness_next_phase": "Phase 1",
        "latest_readiness_execution_ready": "False",
        "latest_phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "latest_phase2_entry_allowed": "False",
        "latest_phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "latest_phase_gate_strict_validation_passed": "False",
        "latest_phase_gate_strict_validation_issue_count": "2",
        "latest_phase_gate_checked_files": "7",
        "latest_phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "latest_phase_gate_issue_previews": [
            "data/research/backtest_metrics_summary.json: missing field"
        ],
        "quick_navigation": {
            "operations_timeline_report": "data/reports/operations_timeline_report.md",
            "operations_dashboard_report": "data/reports/operations_dashboard.md",
        },
        "related_reports": {
            "operations_timeline_report": "data/reports/operations_timeline_report.md",
            "audit_dashboard_report": "data/reports/audit_dashboard.md",
        },
        "latest_remediation_planner_status": "stalled",
        "latest_remediation_planner_next_best_command": "uv run sis validate-artifacts --strict",
        "latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
        "latest_remediation_execution_plan_status": "stalled",
        "latest_remediation_execution_plan_next_action_command": "uv run sis diagnose-quotes",
        "latest_remediation_execution_plan_feedback_priority_reason": "evaluation_failed",
        "latest_remediation_session_status": "ready_for_dry_run",
        "latest_remediation_session_next_pending_command": "uv run sis monitoring-status",
        "latest_remediation_session_feedback_priority_reason": "evaluation_failed",
        "latest_remediation_checkpoint_status": "retry_pending",
        "latest_remediation_checkpoint_next_action_command": "uv run sis phase-gate-review",
        "latest_remediation_checkpoint_feedback_priority_reason": "evaluation_failed",
        "latest_remediation_scoreboard_status": "retrying",
        "latest_remediation_scoreboard_next_action_command": "uv run sis phase-gate-review",
        "latest_remediation_scoreboard_feedback_priority_reason": "evaluation_failed",
        "operation_counts": {"daemon_dry_run": 1, "remediation_scoreboard": 1},
        "diagnostics_status_counts": {"degraded": 1},
        "drift_overview_status_counts": {"degraded": 1},
        "drift_overview_diagnostics_alignment_counts": {"False": 1},
        "drift_overview_state_comparison_mismatching_count_values": {"1": 1},
        "drift_overview_snapshot_drift_mismatching_snapshot_count_values": {"1": 1},
        "gap_history_status_counts": {"ok": 1},
        "gap_history_diagnostics_status_counts": {"degraded": 1},
        "state_comparison_status_match_counts": {"False": 1},
        "state_comparison_mismatching_count_values": {"1": 1},
        "readiness_next_phase_counts": {"Phase 1": 1},
        "phase_gate_decision_counts": {"CONDITIONAL_GO_NEEDS_LIVE_WINDOW": 1},
        "phase2_entry_allowed_counts": {"False": 1},
        "phase_gate_reason_counts": {"remain_in_phase1_until_live_evidence_gate_clears": 1},
        "phase_gate_strict_validation_passed_counts": {"False": 1},
        "phase_gate_strict_validation_issue_count_values": {"2": 1},
        "phase_gate_checked_files_values": {"7": 1},
    }


def test_render_operations_timeline_markdown_includes_core_sections() -> None:
    text = render_operations_timeline_markdown(
        summary=_summary(),
        recent=[
            {
                "created_at": "2026-05-24T00:00:00+00:00",
                "operation": "daemon_dry_run",
                "status": "planned",
                "mode": "paper",
                "notes": ["dry_run"],
            },
            {
                "created_at": "2026-05-24T07:00:00+00:00",
                "operation": "remediation_scoreboard",
                "status": "retrying",
                "mode": "ops",
                "notes": ["scoreboard_status=retrying"],
            },
        ],
    )

    assert text.startswith("# Operations Timeline Report\n")
    assert "## Summary" in text
    assert "- operation_count: 2" in text
    assert "- latest_execution_overall_status: ok" in text
    assert "## Quick Navigation" in text
    assert "- operations_timeline_report: data/reports/operations_timeline_report.md" in text
    assert "## Related Reports" in text
    assert "- audit_dashboard_report: data/reports/audit_dashboard.md" in text
    assert "## Remediation State" in text
    assert "- latest_remediation_planner_status: stalled" in text
    assert "## Latest Phase Gate Issue Preview" in text
    assert "- data/research/backtest_metrics_summary.json: missing field" in text
    assert "## Operation Counts" in text
    assert text.index("## Operation Counts") < text.index("## Latest Phase Gate Issue Preview")
    assert text.index("## Latest Phase Gate Issue Preview") < text.index("- daemon_dry_run: 1")
    assert "- daemon_dry_run: 1" in text
    assert "## Diagnostics Status Counts" in text
    assert "- degraded: 1" in text
    assert "## Recent Timeline" in text
    assert (
        "- 2026-05-24T07:00:00+00:00 | op=remediation_scoreboard | "
        "status=retrying | mode=ops | notes=scoreboard_status=retrying"
    ) in text


def test_render_operations_timeline_markdown_handles_empty_counts_and_recent() -> None:
    summary = _summary()
    for key in [
        "operation_counts",
        "diagnostics_status_counts",
        "drift_overview_status_counts",
        "drift_overview_diagnostics_alignment_counts",
        "drift_overview_state_comparison_mismatching_count_values",
        "drift_overview_snapshot_drift_mismatching_snapshot_count_values",
        "gap_history_status_counts",
        "gap_history_diagnostics_status_counts",
        "state_comparison_status_match_counts",
        "state_comparison_mismatching_count_values",
        "readiness_next_phase_counts",
        "phase_gate_decision_counts",
        "phase2_entry_allowed_counts",
        "phase_gate_reason_counts",
        "phase_gate_strict_validation_passed_counts",
        "phase_gate_strict_validation_issue_count_values",
        "phase_gate_checked_files_values",
    ]:
        summary[key] = {}
    summary["latest_phase_gate_issue_previews"] = []

    text = render_operations_timeline_markdown(summary=summary, recent=[])

    assert "- no operations were available" in text
    assert "- no execution diagnostics notes were available" in text
    assert "- no execution drift overview notes were available" in text
    assert "- no timeline entries available" in text
