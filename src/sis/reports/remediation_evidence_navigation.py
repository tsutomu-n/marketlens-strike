from __future__ import annotations

from pathlib import Path


def quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evidence_report": str(out_path),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
    }


def related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evidence_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }
