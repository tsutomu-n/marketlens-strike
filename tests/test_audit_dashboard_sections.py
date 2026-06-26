from __future__ import annotations

from sis.reports.audit_dashboard_sections import (
    audit_coverage_section_lines,
    artifact_summaries_section_lines,
    overall_section_lines,
    strict_validation_preview_section_lines,
)


def test_overall_section_lines_preserve_order_and_latest_execution_labels() -> None:
    summary = {
        "overall_status": "ok",
        "bundle_status": "ok",
        "audit_pack_status": "ok",
        "timeline_latest_operation": "audit_bundle_snapshot",
        "timeline_latest_status": "ok",
        "timeline_latest_execution_overall_status": "degraded",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": False,
    }

    assert overall_section_lines(summary) == [
        "## Overall",
        "",
        "- overall_status: ok",
        "- bundle_status: ok",
        "- audit_pack_status: ok",
        "- timeline_latest_operation: audit_bundle_snapshot",
        "- timeline_latest_status: ok",
        "- timeline_latest_execution_overall_status: degraded",
        "- timeline_latest_execution_venue_count: 2",
        "- timeline_latest_execution_comparison_all_registries_present: False",
        "",
    ]


def test_audit_coverage_section_lines_preserve_order_and_latest_execution_labels() -> None:
    summary = {
        "audit_entry_count": 4,
        "operations_snapshot_count": 3,
        "operations_audit_snapshot_count": 2,
        "audit_bundle_snapshot_count": 1,
        "cycle_count": 5,
        "completed_cycle_count": 4,
        "bundle_history_snapshot_count": 7,
        "bundle_history_ok_count": 6,
        "bundle_history_latest_execution_overall_status": "ok",
        "bundle_history_latest_execution_venue_count": 2,
        "bundle_history_latest_execution_comparison_all_registries_present": True,
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_all_registries_present": True,
        "execution_diagnostics_status": "ok",
        "execution_balance_gap_detected": False,
        "execution_fills_gap_detected": False,
        "execution_gap_history_entry_count": 8,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "ok",
        "execution_state_comparison_entry_count": 9,
        "execution_state_comparison_latest_status_match": True,
        "execution_state_comparison_mismatching_count": 0,
        "execution_snapshot_drift_entry_count": 10,
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_mismatching_snapshot_count": 0,
        "execution_drift_overview_status": "ok",
        "execution_drift_overview_diagnostics_alignment_match": True,
        "execution_drift_overview_state_comparison_mismatching_count": 0,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 0,
        "readiness_next_phase_candidate": "phase2",
        "readiness_execution_ready": False,
        "timeline_latest_remediation_planner_status": "ok",
        "timeline_latest_remediation_planner_next_best_command": "sis plan",
        "timeline_latest_remediation_execution_plan_status": "ok",
        "timeline_latest_remediation_execution_plan_next_action_command": "sis exec",
        "timeline_latest_remediation_session_status": "pending",
        "timeline_latest_remediation_session_next_pending_command": "sis session",
        "timeline_latest_remediation_checkpoint_status": "pending",
        "timeline_latest_remediation_checkpoint_next_action_command": "sis checkpoint",
        "timeline_latest_remediation_scoreboard_status": "ok",
        "timeline_latest_remediation_scoreboard_next_action_command": "sis scoreboard",
        "phase_gate_decision": "BLOCK",
        "phase2_entry_allowed": False,
        "phase_gate_reason": "strict validation failed",
        "phase_gate_strict_validation_passed": False,
        "phase_gate_strict_validation_issue_count": 2,
        "phase_gate_checked_files": 12,
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
    }

    assert audit_coverage_section_lines(summary) == [
        "## Audit Coverage",
        "",
        "- audit_entry_count: 4",
        "- operations_snapshot_count: 3",
        "- operations_audit_snapshot_count: 2",
        "- audit_bundle_snapshot_count: 1",
        "- cycle_count: 5",
        "- completed_cycle_count: 4",
        "- bundle_history_snapshot_count: 7",
        "- bundle_history_ok_count: 6",
        "- bundle_history_latest_execution_overall_status: ok",
        "- bundle_history_latest_execution_venue_count: 2",
        "- bundle_history_latest_execution_comparison_all_registries_present: True",
        "- execution_overall_status: ok",
        "- execution_venue_count: 2",
        "- execution_comparison_all_registries_present: True",
        "- execution_diagnostics_status: ok",
        "- execution_balance_gap_detected: False",
        "- execution_fills_gap_detected: False",
        "- execution_gap_history_entry_count: 8",
        "- execution_gap_history_latest_status: ok",
        "- execution_gap_history_latest_diagnostics_status: ok",
        "- execution_state_comparison_entry_count: 9",
        "- execution_state_comparison_latest_status_match: True",
        "- execution_state_comparison_mismatching_count: 0",
        "- execution_snapshot_drift_entry_count: 10",
        "- execution_snapshot_drift_latest_status_match: True",
        "- execution_snapshot_drift_mismatching_snapshot_count: 0",
        "- execution_drift_overview_status: ok",
        "- execution_drift_overview_diagnostics_alignment_match: True",
        "- execution_drift_overview_state_comparison_mismatching_count: 0",
        "- execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 0",
        "- readiness_next_phase_candidate: phase2",
        "- readiness_execution_ready: False",
        "- timeline_latest_remediation_planner_status: ok",
        "- timeline_latest_remediation_planner_next_best_command: sis plan",
        "- timeline_latest_remediation_execution_plan_status: ok",
        "- timeline_latest_remediation_execution_plan_next_action_command: sis exec",
        "- timeline_latest_remediation_session_status: pending",
        "- timeline_latest_remediation_session_next_pending_command: sis session",
        "- timeline_latest_remediation_checkpoint_status: pending",
        "- timeline_latest_remediation_checkpoint_next_action_command: sis checkpoint",
        "- timeline_latest_remediation_scoreboard_status: ok",
        "- timeline_latest_remediation_scoreboard_next_action_command: sis scoreboard",
        "- phase_gate_decision: BLOCK",
        "- phase2_entry_allowed: False",
        "- phase_gate_reason: strict validation failed",
        "- phase_gate_strict_validation_passed: False",
        "- phase_gate_strict_validation_issue_count: 2",
        "- phase_gate_checked_files: 12",
        "- phase_gate_review_report_path: data/reports/phase_gate_review.md",
        "",
    ]


def test_strict_validation_preview_section_lines_renders_issue_previews() -> None:
    summary = {
        "phase_gate_strict_validation_issues": [
            {
                "path": "configs/a.json",
                "message": "missing field",
            },
            {
                "path": "configs/b.json",
                "message": "invalid value",
            },
        ],
    }

    assert strict_validation_preview_section_lines(summary) == [
        "## Strict Validation Preview",
        "",
        "- configs/a.json: missing field",
        "- configs/b.json: invalid value",
        "",
    ]


def test_strict_validation_preview_section_lines_renders_none_fallback() -> None:
    assert strict_validation_preview_section_lines({}) == [
        "## Strict Validation Preview",
        "",
        "- issues: none",
        "",
    ]


def test_artifact_summaries_section_lines_preserves_order_and_none_values() -> None:
    artifacts = {
        "bundle_manifest": "data/ops/bundle.json",
        "audit_pack": None,
        "phase_gate_summary": "data/ops/phase_gate.json",
    }

    assert artifact_summaries_section_lines(artifacts) == [
        "## Artifact Summaries",
        "",
        "- bundle_manifest: data/ops/bundle.json",
        "- audit_pack: None",
        "- phase_gate_summary: data/ops/phase_gate.json",
        "",
    ]
