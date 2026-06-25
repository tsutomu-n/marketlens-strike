from __future__ import annotations

from pathlib import Path


def build_live_evidence_restart_pointers(*, data_dir: Path, run_id: str) -> dict[str, str]:
    remediation_report_root = data_dir / "reports"
    remediation_summary_root = data_dir / "ops"
    live_report_root = Path("docs/live_evidence_reports")
    return {
        "readiness_snapshot_summary": str(remediation_summary_root / "readiness_snapshot.json"),
        "readiness_snapshot_report": str(remediation_report_root / "readiness_snapshot.md"),
        "current_state_index_summary": str(remediation_summary_root / "current_state_index.json"),
        "current_state_index_report": str(remediation_report_root / "current_state_index.md"),
        "remediation_planner_summary": str(
            remediation_summary_root / "remediation_planner_summary.json"
        ),
        "remediation_planner_report": str(remediation_report_root / "remediation_planner.md"),
        "remediation_execution_plan_summary": str(
            remediation_summary_root / "remediation_execution_plan_summary.json"
        ),
        "remediation_execution_plan_report": str(
            remediation_report_root / "remediation_execution_plan.md"
        ),
        "remediation_session_summary": str(
            remediation_summary_root / "remediation_session_summary.json"
        ),
        "remediation_session_report": str(remediation_report_root / "remediation_session.md"),
        "remediation_session_checkpoint_summary": str(
            remediation_summary_root / "remediation_session_checkpoint_summary.json"
        ),
        "remediation_session_checkpoint_report": str(
            remediation_report_root / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_summary": str(
            remediation_summary_root / "remediation_scoreboard_summary.json"
        ),
        "remediation_scoreboard_report": str(remediation_report_root / "remediation_scoreboard.md"),
        "remediation_evaluator_summary": str(
            remediation_summary_root / "remediation_evaluator_summary.json"
        ),
        "remediation_evaluator_report": str(remediation_report_root / "remediation_evaluator.md"),
        "remediation_evidence_summary": str(
            remediation_summary_root / "remediation_evidence_summary.json"
        ),
        "remediation_evidence_report": str(remediation_report_root / "remediation_evidence.md"),
        "remediation_command_results_summary": str(
            remediation_summary_root / "remediation_command_results_summary.json"
        ),
        "remediation_command_results_report": str(
            remediation_report_root / "remediation_command_results.md"
        ),
        "live_evidence_report": str(live_report_root / f"live_evidence_report_{run_id}.md"),
        "live_evidence_report_html": str(live_report_root / f"live_evidence_report_{run_id}.html"),
        "live_evidence_followup_report": str(
            live_report_root / f"live_evidence_followup_{run_id}.md"
        ),
    }
