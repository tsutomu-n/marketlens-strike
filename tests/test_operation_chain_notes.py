from __future__ import annotations

from pathlib import Path

from sis.reports.operation_chain_notes import (
    latest_note_from_operation,
    latest_notes_with_prefix,
    latest_operation_entry,
    note_counts,
    note_value,
    note_values,
    remediation_state,
    reports_dir,
    timeline_latest_note_summary,
)


def test_note_value_and_values_preserve_prefix_order_and_string_coercion() -> None:
    notes: list[object] = [
        "status=old",
        "ignored=value",
        "status=new",
        42,
    ]

    assert note_value(notes, "status=") == "old"
    assert note_values(notes, "status=") == ["old", "new"]
    assert note_value(notes, "missing=") is None


def test_note_counts_skips_non_list_notes_and_counts_first_matching_value() -> None:
    items = [
        {"notes": ["status=ok", "status=ignored"]},
        {"notes": ["status=degraded"]},
        {"notes": "status=bad"},
        {"notes": ["other=value"]},
    ]

    assert note_counts(items, "status=") == {"ok": 1, "degraded": 1}


def test_latest_operation_helpers_read_latest_matching_entry_and_note() -> None:
    items = [
        {"operation": "audit", "notes": ["status=old"]},
        {"operation": "ops", "notes": ["status=ignored"]},
        {"operation": "audit", "notes": ["status=new", "other=value"]},
    ]

    assert latest_operation_entry(items, "audit") == {
        "operation": "audit",
        "notes": ["status=new", "other=value"],
    }
    assert latest_operation_entry(items, "missing") == {}
    assert latest_note_from_operation(items, "audit", "status=") == "new"
    assert latest_note_from_operation(items, "missing", "status=") is None


def test_latest_notes_with_prefix_returns_full_latest_notes_list() -> None:
    items = [
        {"operation": "old", "notes": ["status=old", "detail=keep-old"]},
        {"operation": "skip", "notes": ["other=value"]},
        {"operation": "new", "notes": ["status=new", "detail=keep-new"]},
    ]

    assert latest_notes_with_prefix(items, "status=") == ["status=new", "detail=keep-new"]
    assert latest_notes_with_prefix(items, "missing=") == []


def test_reports_dir_handles_ops_and_non_ops_operation_chain_paths() -> None:
    assert reports_dir(Path("data/ops/operation_chain.jsonl")) == Path("data/reports")
    assert reports_dir(Path("data/operation_chain.jsonl")) == Path("data/reports")
    assert reports_dir(None) is None


def test_remediation_state_extracts_latest_values_from_all_operations() -> None:
    items = [
        {
            "operation": "remediation_planner_dry_run",
            "notes": ["planner_status=old", "next_best_command=old"],
        },
        {
            "operation": "remediation_execution_plan_dry_run",
            "notes": [
                "execution_plan_status=stalled",
                "next_action_command=uv run sis diagnose-quotes",
                "next_action_feedback_priority_reason=evaluation_failed",
            ],
        },
        {
            "operation": "remediation_session_dry_run",
            "notes": [
                "session_status=ready_for_dry_run",
                "next_pending_command=uv run sis monitoring-status",
                "next_pending_feedback_priority_reason=manual_review_pending",
            ],
        },
        {
            "operation": "remediation_session_checkpoint",
            "notes": [
                "checkpoint_status=retry_pending",
                "next_action_command=uv run sis phase-gate-review",
                "next_action_feedback_priority_reason=partial_verification",
            ],
        },
        {
            "operation": "remediation_scoreboard",
            "notes": [
                "scoreboard_status=retrying",
                "next_action_command=uv run sis refresh-scoreboard",
                "next_action_feedback_priority_reason=evaluation_failed",
            ],
        },
        {
            "operation": "remediation_planner_dry_run",
            "notes": [
                "planner_status=stalled",
                "next_best_command=uv run sis validate-artifacts --strict",
                "next_feedback_priority_reason=evaluation_failed",
            ],
        },
    ]

    state = remediation_state(items)

    assert state["latest_remediation_planner_status"] == "stalled"
    assert (
        state["latest_remediation_planner_next_best_command"]
        == "uv run sis validate-artifacts --strict"
    )
    assert state["latest_remediation_planner_feedback_priority_reason"] == "evaluation_failed"
    assert state["latest_remediation_execution_plan_status"] == "stalled"
    assert (
        state["latest_remediation_execution_plan_next_action_command"]
        == "uv run sis diagnose-quotes"
    )
    assert (
        state["latest_remediation_execution_plan_feedback_priority_reason"] == "evaluation_failed"
    )
    assert state["latest_remediation_session_status"] == "ready_for_dry_run"
    assert (
        state["latest_remediation_session_next_pending_command"] == "uv run sis monitoring-status"
    )
    assert state["latest_remediation_session_feedback_priority_reason"] == "manual_review_pending"
    assert state["latest_remediation_checkpoint_status"] == "retry_pending"
    assert (
        state["latest_remediation_checkpoint_next_action_command"] == "uv run sis phase-gate-review"
    )
    assert state["latest_remediation_checkpoint_feedback_priority_reason"] == "partial_verification"
    assert state["latest_remediation_scoreboard_status"] == "retrying"
    assert (
        state["latest_remediation_scoreboard_next_action_command"]
        == "uv run sis refresh-scoreboard"
    )
    assert state["latest_remediation_scoreboard_feedback_priority_reason"] == "evaluation_failed"


def test_remediation_state_preserves_missing_keys_with_none_values() -> None:
    state = remediation_state([])

    assert set(state) == {
        "latest_remediation_planner_status",
        "latest_remediation_planner_next_best_command",
        "latest_remediation_planner_feedback_priority_reason",
        "latest_remediation_execution_plan_status",
        "latest_remediation_execution_plan_next_action_command",
        "latest_remediation_execution_plan_feedback_priority_reason",
        "latest_remediation_session_status",
        "latest_remediation_session_next_pending_command",
        "latest_remediation_session_feedback_priority_reason",
        "latest_remediation_checkpoint_status",
        "latest_remediation_checkpoint_next_action_command",
        "latest_remediation_checkpoint_feedback_priority_reason",
        "latest_remediation_scoreboard_status",
        "latest_remediation_scoreboard_next_action_command",
        "latest_remediation_scoreboard_feedback_priority_reason",
    }
    assert all(value is None for value in state.values())


def test_timeline_latest_note_summary_maps_nested_and_flat_fields() -> None:
    execution_notes = [
        "execution_diagnostics_status=degraded",
        "execution_drift_overview_status=warn",
        "execution_drift_overview_diagnostics_alignment_match=False",
        "execution_drift_overview_state_comparison_mismatching_count=2",
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=3",
        "execution_gap_history_latest_status=ok",
        "execution_gap_history_latest_diagnostics_status=warn",
        "execution_state_comparison_latest_status_match=False",
        "execution_state_comparison_mismatching_count=4",
    ]
    readiness_notes = [
        "readiness_next_phase=Phase 2",
        "readiness_execution_ready=True",
    ]
    phase_gate_notes = [
        "phase_gate_decision=CONDITIONAL_GO",
        "phase2_entry_allowed=False",
        "phase_gate_reason=needs_more_evidence",
        "phase_gate_strict_validation_passed=False",
        "phase_gate_strict_validation_issue_count=1",
        "phase_gate_checked_files=7",
        "phase_gate_review_report_path=data/reports/phase_gate_review.md",
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field",
    ]

    summary = timeline_latest_note_summary(
        execution_notes=execution_notes,
        readiness_notes=readiness_notes,
        phase_gate_notes=phase_gate_notes,
    )

    assert summary["latest_execution_diagnostics_summary"] == {
        "execution_diagnostics_status": "degraded"
    }
    assert summary["latest_execution_drift_overview_summary"] == {
        "execution_drift_overview_status": "warn",
        "execution_drift_overview_diagnostics_alignment_match": "False",
        "execution_drift_overview_state_comparison_mismatching_count": "2",
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": "3",
    }
    assert summary["latest_execution_gap_history_summary"] == {
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "warn",
    }
    assert summary["latest_execution_state_comparison_summary"] == {
        "execution_state_comparison_latest_status_match": "False",
        "execution_state_comparison_mismatching_count": "4",
    }
    assert summary["latest_readiness_summary"] == {
        "readiness_next_phase_candidate": "Phase 2",
        "readiness_execution_ready": "True",
    }
    assert summary["latest_phase_gate_summary"] == {
        "phase_gate_decision": "CONDITIONAL_GO",
        "phase2_entry_allowed": "False",
        "phase_gate_reason": "needs_more_evidence",
        "phase_gate_strict_validation_passed": "False",
        "phase_gate_strict_validation_issue_count": "1",
        "phase_gate_checked_files": "7",
        "phase_gate_review_report_path": "data/reports/phase_gate_review.md",
        "phase_gate_strict_validation_issues": [
            "data/research/backtest_metrics_summary.json: missing field"
        ],
    }
    assert summary["latest_execution_diagnostics_status"] == "degraded"
    assert summary["latest_readiness_next_phase"] == "Phase 2"
    assert summary["latest_phase_gate_decision"] == "CONDITIONAL_GO"
    assert summary["latest_phase_gate_issue_previews"] == [
        "data/research/backtest_metrics_summary.json: missing field"
    ]


def test_timeline_latest_note_summary_preserves_missing_values() -> None:
    summary = timeline_latest_note_summary(
        execution_notes=[],
        readiness_notes=[],
        phase_gate_notes=[],
    )

    assert summary["latest_execution_diagnostics_summary"] == {"execution_diagnostics_status": None}
    assert summary["latest_readiness_summary"] == {
        "readiness_next_phase_candidate": None,
        "readiness_execution_ready": None,
    }
    assert summary["latest_phase_gate_summary"]["phase_gate_strict_validation_issues"] == []
    assert summary["latest_phase_gate_issue_previews"] == []
    assert summary["latest_phase_gate_review_report_path"] is None
