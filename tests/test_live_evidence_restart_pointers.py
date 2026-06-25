from __future__ import annotations

from pathlib import Path

from sis.live_evidence_restart_pointers import build_live_evidence_restart_pointers


def test_build_live_evidence_restart_pointers_preserves_summary_paths() -> None:
    pointers = build_live_evidence_restart_pointers(
        data_dir=Path("data"),
        run_id="20260522_2308",
    )

    assert pointers == {
        "readiness_snapshot_summary": "data/ops/readiness_snapshot.json",
        "readiness_snapshot_report": "data/reports/readiness_snapshot.md",
        "current_state_index_summary": "data/ops/current_state_index.json",
        "current_state_index_report": "data/reports/current_state_index.md",
        "remediation_planner_summary": "data/ops/remediation_planner_summary.json",
        "remediation_planner_report": "data/reports/remediation_planner.md",
        "remediation_execution_plan_summary": ("data/ops/remediation_execution_plan_summary.json"),
        "remediation_execution_plan_report": ("data/reports/remediation_execution_plan.md"),
        "remediation_session_summary": "data/ops/remediation_session_summary.json",
        "remediation_session_report": "data/reports/remediation_session.md",
        "remediation_session_checkpoint_summary": (
            "data/ops/remediation_session_checkpoint_summary.json"
        ),
        "remediation_session_checkpoint_report": ("data/reports/remediation_session_checkpoint.md"),
        "remediation_scoreboard_summary": "data/ops/remediation_scoreboard_summary.json",
        "remediation_scoreboard_report": "data/reports/remediation_scoreboard.md",
        "remediation_evaluator_summary": "data/ops/remediation_evaluator_summary.json",
        "remediation_evaluator_report": "data/reports/remediation_evaluator.md",
        "remediation_evidence_summary": "data/ops/remediation_evidence_summary.json",
        "remediation_evidence_report": "data/reports/remediation_evidence.md",
        "remediation_command_results_summary": (
            "data/ops/remediation_command_results_summary.json"
        ),
        "remediation_command_results_report": ("data/reports/remediation_command_results.md"),
        "live_evidence_report": (
            "docs/live_evidence_reports/live_evidence_report_20260522_2308.md"
        ),
        "live_evidence_report_html": (
            "docs/live_evidence_reports/live_evidence_report_20260522_2308.html"
        ),
        "live_evidence_followup_report": (
            "docs/live_evidence_reports/live_evidence_followup_20260522_2308.md"
        ),
    }
