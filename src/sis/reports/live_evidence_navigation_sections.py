from __future__ import annotations

import html
from typing import Any, Mapping


def restart_pointer_lines(readiness_summary: Mapping[str, Any]) -> list[str]:
    keys = (
        "readiness_snapshot_report",
        "current_state_index_report",
        "remediation_scoreboard_report",
        "remediation_session_checkpoint_report",
        "remediation_session_report",
        "remediation_execution_plan_report",
        "remediation_planner_report",
        "live_evidence_report",
    )
    return [
        f"- {key}: `{readiness_summary.get(key)}`"
        for key in keys
        if readiness_summary.get(key) is not None
    ]


def restart_pointer_html_metrics(readiness_summary: Mapping[str, Any]) -> str:
    metrics = [
        ("Readiness Snapshot Report", readiness_summary.get("readiness_snapshot_report")),
        ("Current State Index Report", readiness_summary.get("current_state_index_report")),
        ("Remediation Scoreboard Report", readiness_summary.get("remediation_scoreboard_report")),
        (
            "Remediation Session Checkpoint Report",
            readiness_summary.get("remediation_session_checkpoint_report"),
        ),
        ("Remediation Session Report", readiness_summary.get("remediation_session_report")),
        (
            "Remediation Execution Plan Report",
            readiness_summary.get("remediation_execution_plan_report"),
        ),
        ("Remediation Planner Report", readiness_summary.get("remediation_planner_report")),
        ("Live Evidence Report", readiness_summary.get("live_evidence_report")),
    ]
    return _html_metrics(metrics)


def related_report_lines(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> list[str]:
    items = (
        ("phase_gate_review_report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("readiness_snapshot_report", readiness_summary.get("readiness_snapshot_report")),
        ("current_state_index_report", readiness_summary.get("current_state_index_report")),
        ("remediation_scoreboard_report", readiness_summary.get("remediation_scoreboard_report")),
        (
            "remediation_session_checkpoint_report",
            readiness_summary.get("remediation_session_checkpoint_report"),
        ),
        ("remediation_session_report", readiness_summary.get("remediation_session_report")),
        (
            "remediation_execution_plan_report",
            readiness_summary.get("remediation_execution_plan_report"),
        ),
        ("remediation_planner_report", readiness_summary.get("remediation_planner_report")),
        ("live_evidence_report", readiness_summary.get("live_evidence_report")),
    )
    return [f"- {key}: `{value}`" for key, value in items if value is not None]


def related_report_html_metrics(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> str:
    metrics = [
        ("Phase Gate Review Report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("Readiness Snapshot Report", readiness_summary.get("readiness_snapshot_report")),
        ("Current State Index Report", readiness_summary.get("current_state_index_report")),
        ("Remediation Scoreboard Report", readiness_summary.get("remediation_scoreboard_report")),
        (
            "Remediation Session Checkpoint Report",
            readiness_summary.get("remediation_session_checkpoint_report"),
        ),
        ("Remediation Session Report", readiness_summary.get("remediation_session_report")),
        (
            "Remediation Execution Plan Report",
            readiness_summary.get("remediation_execution_plan_report"),
        ),
        ("Remediation Planner Report", readiness_summary.get("remediation_planner_report")),
        ("Live Evidence Report", readiness_summary.get("live_evidence_report")),
    ]
    return _html_metrics(metrics)


def quick_navigation_lines(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> list[str]:
    items = (
        ("current_state_index_report", readiness_summary.get("current_state_index_report")),
        ("readiness_snapshot_report", readiness_summary.get("readiness_snapshot_report")),
        ("phase_gate_review_report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("remediation_scoreboard_report", readiness_summary.get("remediation_scoreboard_report")),
        ("live_evidence_report", readiness_summary.get("live_evidence_report")),
    )
    return [f"- {key}: `{value}`" for key, value in items if value is not None]


def quick_navigation_html_metrics(
    readiness_summary: Mapping[str, Any],
    phase_gate_summary: Mapping[str, Any],
) -> str:
    metrics = [
        ("Current State Index Report", readiness_summary.get("current_state_index_report")),
        ("Readiness Snapshot Report", readiness_summary.get("readiness_snapshot_report")),
        ("Phase Gate Review Report", phase_gate_summary.get("phase_gate_review_report_path")),
        ("Remediation Scoreboard Report", readiness_summary.get("remediation_scoreboard_report")),
        ("Live Evidence Report", readiness_summary.get("live_evidence_report")),
    ]
    return _html_metrics(metrics)


def _html_metrics(metrics: list[tuple[str, object]]) -> str:
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )
