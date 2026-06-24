from __future__ import annotations

from pathlib import Path
from typing import Mapping


REMEDIATION_FIELD_KEYS = (
    "timeline_latest_remediation_planner_status",
    "timeline_latest_remediation_planner_next_best_command",
    "timeline_latest_remediation_planner_feedback_priority_reason",
    "timeline_latest_remediation_execution_plan_status",
    "timeline_latest_remediation_execution_plan_next_action_command",
    "timeline_latest_remediation_execution_plan_feedback_priority_reason",
    "timeline_latest_remediation_session_status",
    "timeline_latest_remediation_session_next_pending_command",
    "timeline_latest_remediation_session_feedback_priority_reason",
    "timeline_latest_remediation_checkpoint_status",
    "timeline_latest_remediation_checkpoint_next_action_command",
    "timeline_latest_remediation_checkpoint_feedback_priority_reason",
    "timeline_latest_remediation_scoreboard_status",
    "timeline_latest_remediation_scoreboard_next_action_command",
    "timeline_latest_remediation_scoreboard_feedback_priority_reason",
)


def remediation_fields_from_sources(
    current_state: dict[str, object],
    operations: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    for key in REMEDIATION_FIELD_KEYS:
        if current_state.get(key) is not None:
            merged[key] = current_state.get(key)
        elif operations.get(key) is not None:
            merged[key] = operations.get(key)
    return merged


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
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
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
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return _string_items(ordered_items)


def quick_navigation(
    restart_pointers: Mapping[str, object],
    phase_gate_review_report_path: object,
) -> dict[str, str]:
    items = (
        ("readiness_snapshot_report", restart_pointers.get("readiness_snapshot_report")),
        ("current_state_index_report", restart_pointers.get("current_state_index_report")),
        ("phase_gate_review_report", phase_gate_review_report_path),
        ("remediation_scoreboard_report", restart_pointers.get("remediation_scoreboard_report")),
        ("live_evidence_report", restart_pointers.get("live_evidence_report")),
    )
    return _string_items(items)


def _string_items(items: tuple[tuple[str, object], ...]) -> dict[str, str]:
    return {key: value for key, value in items if isinstance(value, str) and value}
