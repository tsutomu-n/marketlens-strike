from __future__ import annotations

import html
from typing import Any, Mapping

from sis.reports.summary_normalizers import latest_execution_lineage_fields_from_payload


def latest_execution_lineage_flat_values(
    data: Any,
) -> dict[str, Any]:
    return latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=data.timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(
            data.timeline_latest_execution_comparison_summary
        ),
        bundle_history_latest_execution_summary=(data.bundle_history_latest_execution_summary),
        bundle_history_latest_execution_comparison_summary=(
            data.bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=(data.cycle_history_latest_execution_summary),
        cycle_history_latest_execution_comparison_summary=(
            data.cycle_history_latest_execution_comparison_summary
        ),
    )


def latest_execution_lineage_markdown_lines(
    latest_execution_flat: Mapping[str, Any],
) -> list[str]:
    return [
        (
            "- timeline_latest_execution_overall_status: "
            f"`{latest_execution_flat.get('timeline_latest_execution_overall_status')}`"
        ),
        (
            "- timeline_latest_execution_venue_count: "
            f"`{latest_execution_flat.get('timeline_latest_execution_venue_count')}`"
        ),
        (
            "- timeline_latest_execution_comparison_all_registries_present: "
            f"`{latest_execution_flat.get('timeline_latest_execution_comparison_all_registries_present')}`"
        ),
        (
            "- bundle_history_latest_execution_overall_status: "
            f"`{latest_execution_flat.get('bundle_history_latest_execution_overall_status')}`"
        ),
        (
            "- bundle_history_latest_execution_venue_count: "
            f"`{latest_execution_flat.get('bundle_history_latest_execution_venue_count')}`"
        ),
        (
            "- bundle_history_latest_execution_comparison_all_registries_present: "
            f"`{latest_execution_flat.get('bundle_history_latest_execution_comparison_all_registries_present')}`"
        ),
        (
            "- cycle_history_latest_execution_overall_status: "
            f"`{latest_execution_flat.get('cycle_history_latest_execution_overall_status')}`"
        ),
        (
            "- cycle_history_latest_execution_venue_count: "
            f"`{latest_execution_flat.get('cycle_history_latest_execution_venue_count')}`"
        ),
        (
            "- cycle_history_latest_execution_comparison_all_registries_present: "
            f"`{latest_execution_flat.get('cycle_history_latest_execution_comparison_all_registries_present')}`"
        ),
    ]


def latest_execution_lineage_html_metrics(
    latest_execution_flat: Mapping[str, Any],
) -> str:
    metrics = [
        (
            "Timeline Overall Status",
            latest_execution_flat.get("timeline_latest_execution_overall_status"),
        ),
        (
            "Timeline Venue Count",
            latest_execution_flat.get("timeline_latest_execution_venue_count"),
        ),
        (
            "Timeline Comparison",
            latest_execution_flat.get(
                "timeline_latest_execution_comparison_all_registries_present"
            ),
        ),
        (
            "Bundle History Overall Status",
            latest_execution_flat.get("bundle_history_latest_execution_overall_status"),
        ),
        (
            "Bundle History Venue Count",
            latest_execution_flat.get("bundle_history_latest_execution_venue_count"),
        ),
        (
            "Bundle History Comparison",
            latest_execution_flat.get(
                "bundle_history_latest_execution_comparison_all_registries_present"
            ),
        ),
        (
            "Cycle History Overall Status",
            latest_execution_flat.get("cycle_history_latest_execution_overall_status"),
        ),
        (
            "Cycle History Venue Count",
            latest_execution_flat.get("cycle_history_latest_execution_venue_count"),
        ),
        (
            "Cycle History Comparison",
            latest_execution_flat.get(
                "cycle_history_latest_execution_comparison_all_registries_present"
            ),
        ),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
    )


def remediation_markdown_lines(readiness_summary: Mapping[str, Any]) -> list[str]:
    return [
        (
            "- planner_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_planner_status')}`"
        ),
        (
            "- planner_next_best_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_planner_next_best_command')}`"
        ),
        (
            "- planner_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_planner_feedback_priority_reason')}`"
        ),
        (
            "- execution_plan_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_execution_plan_status')}`"
        ),
        (
            "- execution_plan_next_action_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_execution_plan_next_action_command')}`"
        ),
        (
            "- execution_plan_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_execution_plan_feedback_priority_reason')}`"
        ),
        (
            "- session_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_session_status')}`"
        ),
        (
            "- session_next_pending_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_session_next_pending_command')}`"
        ),
        (
            "- session_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_session_feedback_priority_reason')}`"
        ),
        (
            "- checkpoint_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_checkpoint_status')}`"
        ),
        (
            "- checkpoint_next_action_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_checkpoint_next_action_command')}`"
        ),
        (
            "- checkpoint_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_checkpoint_feedback_priority_reason')}`"
        ),
        (
            "- scoreboard_status: "
            f"`{readiness_summary.get('timeline_latest_remediation_scoreboard_status')}`"
        ),
        (
            "- scoreboard_next_action_command: "
            f"`{readiness_summary.get('timeline_latest_remediation_scoreboard_next_action_command')}`"
        ),
        (
            "- scoreboard_feedback_priority_reason: "
            f"`{readiness_summary.get('timeline_latest_remediation_scoreboard_feedback_priority_reason')}`"
        ),
    ]


def remediation_html_metrics(readiness_summary: Mapping[str, Any]) -> str:
    metrics = [
        ("Planner Status", readiness_summary.get("timeline_latest_remediation_planner_status")),
        (
            "Planner Next Best Command",
            readiness_summary.get("timeline_latest_remediation_planner_next_best_command"),
        ),
        (
            "Planner Feedback Reason",
            readiness_summary.get("timeline_latest_remediation_planner_feedback_priority_reason"),
        ),
        (
            "Execution Plan Status",
            readiness_summary.get("timeline_latest_remediation_execution_plan_status"),
        ),
        (
            "Execution Plan Next Action",
            readiness_summary.get("timeline_latest_remediation_execution_plan_next_action_command"),
        ),
        (
            "Execution Plan Feedback Reason",
            readiness_summary.get(
                "timeline_latest_remediation_execution_plan_feedback_priority_reason"
            ),
        ),
        ("Session Status", readiness_summary.get("timeline_latest_remediation_session_status")),
        (
            "Session Next Pending Command",
            readiness_summary.get("timeline_latest_remediation_session_next_pending_command"),
        ),
        (
            "Session Feedback Reason",
            readiness_summary.get("timeline_latest_remediation_session_feedback_priority_reason"),
        ),
        (
            "Checkpoint Status",
            readiness_summary.get("timeline_latest_remediation_checkpoint_status"),
        ),
        (
            "Checkpoint Next Action",
            readiness_summary.get("timeline_latest_remediation_checkpoint_next_action_command"),
        ),
        (
            "Checkpoint Feedback Reason",
            readiness_summary.get(
                "timeline_latest_remediation_checkpoint_feedback_priority_reason"
            ),
        ),
        (
            "Scoreboard Status",
            readiness_summary.get("timeline_latest_remediation_scoreboard_status"),
        ),
        (
            "Scoreboard Next Action",
            readiness_summary.get("timeline_latest_remediation_scoreboard_next_action_command"),
        ),
        (
            "Scoreboard Feedback Reason",
            readiness_summary.get(
                "timeline_latest_remediation_scoreboard_feedback_priority_reason"
            ),
        ),
    ]
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
    )


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
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )


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
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )


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
    return "\n".join(
        (
            f'        <div class="metric"><div class="label">{label}</div>'
            f'<div class="value">{html.escape(str(value))}</div></div>'
        )
        for label, value in metrics
        if value is not None
    )
