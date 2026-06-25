from __future__ import annotations

from sis.reports.audit_timeline_markdown import render_audit_timeline_markdown


def _summary() -> dict[str, object]:
    return {
        "audit_entry_count": 3,
        "recent_count": 3,
        "latest_operation": "audit_bundle_snapshot",
        "latest_status": "ok",
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
            "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"
        ],
        "quick_navigation": {
            "audit_timeline_report": "data/reports/audit_timeline_report.md",
            "audit_dashboard_report": "data/reports/audit_dashboard.md",
        },
        "related_reports": {
            "audit_timeline_report": "data/reports/audit_timeline_report.md",
            "operations_audit_pack_report": "data/reports/operations_audit_pack.md",
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
        "operation_counts": {
            "audit_bundle_snapshot": 1,
            "operations_audit_snapshot": 1,
            "operations_snapshot": 1,
        },
        "diagnostics_status_counts": {"degraded": 2, "ok": 1},
        "drift_overview_status_counts": {"degraded": 2, "ok": 1},
        "drift_overview_diagnostics_alignment_counts": {"False": 2, "True": 1},
        "drift_overview_state_comparison_mismatching_count_values": {"1": 2, "0": 1},
        "drift_overview_snapshot_drift_mismatching_snapshot_count_values": {"1": 2, "0": 1},
        "gap_history_status_counts": {"ok": 3},
        "gap_history_diagnostics_status_counts": {"degraded": 2, "ok": 1},
        "state_comparison_status_match_counts": {"False": 2, "True": 1},
        "state_comparison_mismatching_count_values": {"1": 2, "0": 1},
        "readiness_next_phase_counts": {"Phase 1": 2, "Phase 2": 1},
        "readiness_execution_ready_counts": {"False": 2, "True": 1},
        "phase_gate_decision_counts": {"CONDITIONAL_GO_NEEDS_LIVE_WINDOW": 2, "GO": 1},
        "phase2_entry_allowed_counts": {"False": 2, "True": 1},
        "phase_gate_reason_counts": {"remain_in_phase1_until_live_evidence_gate_clears": 2},
        "phase_gate_strict_validation_passed_counts": {"False": 2, "True": 1},
        "phase_gate_strict_validation_issue_count_values": {"2": 2, "0": 1},
        "phase_gate_checked_files_values": {"7": 3},
    }


def test_render_audit_timeline_markdown_includes_core_sections() -> None:
    text = render_audit_timeline_markdown(
        summary=_summary(),
        recent=[
            {
                "created_at": "2026-05-24T01:00:00+00:00",
                "operation": "operations_snapshot",
                "status": "ok",
                "notes": ["execution_diagnostics_status=ok"],
            },
            {
                "created_at": "2026-05-24T03:00:00+00:00",
                "operation": "audit_bundle_snapshot",
                "status": "ok",
                "notes": ["execution_diagnostics_status=degraded"],
            },
        ],
    )

    assert text.startswith("# Audit Timeline Report\n")
    assert "## Summary" in text
    assert "- audit_entry_count: 3" in text
    assert "- latest_execution_overall_status: ok" in text
    assert "## Quick Navigation" in text
    assert "- audit_timeline_report: data/reports/audit_timeline_report.md" in text
    assert "## Related Reports" in text
    assert "- operations_audit_pack_report: data/reports/operations_audit_pack.md" in text
    assert "## Remediation State" in text
    assert "- latest_remediation_planner_status: stalled" in text
    assert "## Audit Entry Counts" in text
    assert "## Latest Phase Gate Issue Preview" in text
    assert text.index("## Audit Entry Counts") < text.index("## Latest Phase Gate Issue Preview")
    assert text.index("## Latest Phase Gate Issue Preview") < text.index(
        "- audit_bundle_snapshot: 1"
    )
    assert "- operations_snapshot: 1" in text
    assert "## Readiness Execution Ready Counts" in text
    assert "- False: 2" in text
    assert "## Recent Audit Timeline" in text
    assert (
        "- 2026-05-24T03:00:00+00:00 | op=audit_bundle_snapshot | "
        "status=ok | notes=execution_diagnostics_status=degraded"
    ) in text


def test_render_audit_timeline_markdown_handles_empty_counts_and_recent() -> None:
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
        "readiness_execution_ready_counts",
        "phase_gate_decision_counts",
        "phase2_entry_allowed_counts",
        "phase_gate_reason_counts",
        "phase_gate_strict_validation_passed_counts",
        "phase_gate_strict_validation_issue_count_values",
        "phase_gate_checked_files_values",
    ]:
        summary[key] = {}
    summary["latest_phase_gate_issue_previews"] = []

    text = render_audit_timeline_markdown(summary=summary, recent=[])

    assert "- no audit snapshot entries were available" in text
    assert "- no execution diagnostics notes were available" in text
    assert "- no readiness execution-ready notes were available" in text
    assert "- no audit timeline entries available" in text
