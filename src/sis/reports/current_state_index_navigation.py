from __future__ import annotations

from pathlib import Path
from typing import Mapping


def remediation_fields_from_sources(*sources: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for source in sources
        if isinstance(source, dict)
        for key, value in source.items()
        if isinstance(key, str) and key.startswith("timeline_latest_remediation_")
    }


def report_path_for_summary(path: Path | None, report_name: str) -> str | None:
    if path is None:
        return None
    base = path.parent.parent if path.parent.name == "ops" else path.parent
    return str(base / "reports" / report_name)


def live_evidence_report_path(
    summary_path: Path | None,
    live_evidence_summary: dict[str, object] | None = None,
) -> str | None:
    run_id = None
    if isinstance(live_evidence_summary, dict):
        run_id = live_evidence_summary.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        if summary_path is None:
            return None
        stem = summary_path.stem
        prefix = "live_evidence_summary_"
        if not stem.startswith(prefix):
            return None
        run_id = stem[len(prefix) :]
    return str(Path("docs/live_evidence_reports") / f"live_evidence_report_{run_id}.md")


def related_reports(
    restart_pointers: Mapping[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    ordered_items = (
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        (
            "remediation_session_checkpoint_report",
            restart_pointers.get("remediation_session_checkpoint_report"),
        ),
        ("remediation_session_report", restart_pointers.get("remediation_session_report")),
        (
            "remediation_execution_plan_report",
            restart_pointers.get("remediation_execution_plan_report"),
        ),
        ("remediation_planner_report", restart_pointers.get("remediation_planner_report")),
        ("remediation_evaluator_report", restart_pointers.get("remediation_evaluator_report")),
        ("remediation_evidence_report", restart_pointers.get("remediation_evidence_report")),
        (
            "remediation_command_results_report",
            restart_pointers.get("remediation_command_results_report"),
        ),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return _string_items(ordered_items)


def quick_navigation(
    restart_pointers: Mapping[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    items = (
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return _string_items(items)


def _string_items(items: tuple[tuple[str, object], ...]) -> dict[str, str]:
    return {key: value for key, value in items if isinstance(value, str) and value}
