from __future__ import annotations

from pathlib import Path


def quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evaluator_report": str(out_path),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
    }


def related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evaluator_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def report_path_from_summary_path(summary_path: Path | None) -> Path | None:
    if summary_path is None:
        return None
    if summary_path.parent.name == "ops" and summary_path.name.endswith("_summary.json"):
        stem = summary_path.name.removesuffix("_summary.json")
        report_name = f"{stem}.md"
        if stem == "ops_review":
            report_name = "ops_review_report.md"
        return summary_path.parent.parent / "reports" / report_name
    return None


def report_paths(
    planner: dict,
    source_summaries: dict[str, dict],
) -> dict[str, Path | None]:
    phase_gate_summary_path = planner.get("phase_gate_summary_path")
    runbook_summary_path = planner.get("runbook_summary_path")
    phase_gate_summary = source_summaries.get("phase_gate_review", {})
    runbook_summary = source_summaries.get("paper_operations_runbook", {})
    phase_gate_report_path = phase_gate_summary.get("phase_gate_review_report_path")
    runbook_report_path = runbook_summary.get("paper_operations_runbook_report_path")
    return {
        "phase_gate_review": (
            Path(phase_gate_report_path)
            if isinstance(phase_gate_report_path, str)
            else report_path_from_summary_path(
                Path(phase_gate_summary_path) if isinstance(phase_gate_summary_path, str) else None
            )
        ),
        "paper_operations_runbook": (
            Path(runbook_report_path)
            if isinstance(runbook_report_path, str)
            else report_path_from_summary_path(
                Path(runbook_summary_path) if isinstance(runbook_summary_path, str) else None
            )
        ),
    }


def timeline_summary_paths(planner: dict) -> dict[str, Path | None]:
    base_dir = _first_planner_base_dir(planner)
    return {
        "operations_timeline": (base_dir / "operations_timeline_summary.json")
        if base_dir
        else None,
        "audit_timeline": (base_dir / "audit_timeline_summary.json") if base_dir else None,
    }


def dashboard_bundle_summary_paths(planner: dict) -> dict[str, Path | None]:
    base_dir = _first_planner_base_dir(planner)
    return {
        "operations_dashboard": (base_dir / "operations_dashboard_summary.json")
        if base_dir
        else None,
        "audit_dashboard": (base_dir / "audit_dashboard_summary.json") if base_dir else None,
        "operations_bundle": (base_dir / "operations_bundle_manifest.json") if base_dir else None,
        "operations_audit_pack": (base_dir / "operations_audit_pack.json") if base_dir else None,
        "audit_bundle": (base_dir / "audit_bundle_manifest.json") if base_dir else None,
    }


def ops_review_paths(planner: dict) -> dict[str, Path | None]:
    base_dir = _first_planner_base_dir(planner)
    summary_path = (base_dir / "ops_review_summary.json") if base_dir else None
    return {
        "ops_review_summary": summary_path,
        "ops_review_report": report_path_from_summary_path(summary_path),
    }


def current_state_index_paths(planner: dict) -> dict[str, Path | None]:
    base_dir = _first_planner_base_dir(planner)
    summary_path = (base_dir / "current_state_index.json") if base_dir else None
    report_path = None
    if base_dir is not None:
        report_path = base_dir.parent / "reports" / "current_state_index.md"
    return {
        "current_state_index_summary": summary_path,
        "current_state_index_report": report_path,
    }


def _first_planner_base_dir(planner: dict) -> Path | None:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    bases = [Path(raw).parent for raw in (phase_gate_path, runbook_path) if isinstance(raw, str)]
    return bases[0] if bases else None
