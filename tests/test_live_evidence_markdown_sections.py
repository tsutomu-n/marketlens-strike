from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sis.reports.live_evidence_markdown_sections import summary_markdown_lines


def test_summary_markdown_lines_render_status_and_summary_sections() -> None:
    data = SimpleNamespace(
        status="completed",
        started_at_utc="2026-05-22T14:08:00Z",
        finished_at_utc="2026-05-22T16:08:30Z",
        decision="GO",
        log_path=Path("logs/live_evidence/live_evidence_20260522_2308.log"),
        manifest_path=Path("logs/live_evidence/manifests/live_evidence_20260522_2308.json"),
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
            "checked_files": ["data/research/go_no_go_report.md"],
        },
        readiness_summary={
            "next_phase_candidate": "Stay Phase 1",
            "execution_ready": False,
            "timeline_latest_remediation_planner_status": "stalled",
            "timeline_latest_remediation_planner_next_best_command": "uv run sis validate-artifacts",
            "timeline_latest_remediation_planner_feedback_priority_reason": "evaluation_failed",
            "live_evidence_report": "docs/live_evidence_reports/report.md",
            "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        },
        timeline_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        timeline_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": True,
        },
        bundle_history_latest_execution_summary={
            "execution_overall_status": "warn",
            "execution_venue_count": 1,
        },
        bundle_history_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": False,
        },
        cycle_history_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        cycle_history_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": True,
        },
        execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
            "report_path": "data/reports/execution_snapshot.md",
        },
        execution_comparison_summary={
            "all_registries_present": True,
            "report_path": "data/reports/execution_venue_comparison.md",
        },
        execution_diagnostics_summary={
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
            "report_path": "data/reports/execution_venue_diagnostics.md",
        },
        execution_gap_history_summary={
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "report_path": "data/reports/execution_gap_history.md",
        },
        execution_state_comparison_summary={
            "entry_count": 5,
            "latest_status_match": False,
            "mismatching_count": 2,
            "report_path": "data/reports/execution_state_comparison.md",
        },
        execution_snapshot_drift_summary={
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_snapshot_drift_history.md",
        },
        execution_drift_overview_summary={
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 2,
            "snapshot_drift_mismatching_snapshot_count": 1,
        },
    )

    lines = summary_markdown_lines(data)

    assert lines[:15] == [
        "# Live Evidence Detailed Report",
        "",
        "## Status",
        "",
        "- run_status: `completed`",
        "- started_at_utc: `2026-05-22T14:08:00Z`",
        "- finished_at_utc: `2026-05-22T16:08:30Z`",
        "- decision: `GO`",
        "- log_path: `logs/live_evidence/live_evidence_20260522_2308.log`",
        "- manifest_path: `logs/live_evidence/manifests/live_evidence_20260522_2308.json`",
        "",
        "## Audit Summary",
        "",
        "- overall_status: `ok`",
        "- latest_operation: `audit_bundle_snapshot`",
    ]
    assert "## Current Remediation Queue" in lines
    assert "- planner_status: `stalled`" in lines
    assert "## Latest Execution Lineage" in lines
    assert "- bundle_history_latest_execution_comparison_all_registries_present: `False`" in lines
    assert "## Execution State Comparison History" in lines
    assert "- mismatching_count: `2`" in lines
    assert lines[-5:] == [
        "- overall_status: `degraded`",
        "- diagnostics_alignment_match: `False`",
        "- state_comparison_mismatching_count: `2`",
        "- snapshot_drift_mismatching_snapshot_count: `1`",
        "",
    ]
