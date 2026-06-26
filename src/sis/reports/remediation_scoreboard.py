from __future__ import annotations

from pathlib import Path
from typing import cast

from sis.reports.loaders import safe_read_json_dict
from sis.reports import remediation_scoreboard_actions, remediation_scoreboard_navigation
from sis.storage.jsonl_store import write_json


_quick_navigation = remediation_scoreboard_navigation.quick_navigation
_related_reports = remediation_scoreboard_navigation.related_reports
_action_observed_sources = remediation_scoreboard_actions.action_observed_sources
_action_priority_key = remediation_scoreboard_actions.action_priority_key
_as_int = remediation_scoreboard_actions.as_int
_enrich_actions_with_feedback = remediation_scoreboard_actions.enrich_actions_with_feedback
_next_action = remediation_scoreboard_actions.next_action
_observed_source_counts = remediation_scoreboard_actions.observed_source_counts
_scoreboard_status = remediation_scoreboard_actions.scoreboard_status


def _feedback_summary_maps(
    remediation_command_results_summary_path: Path | None,
    remediation_evaluator_summary_path: Path | None,
) -> tuple[dict[str, str], dict[str, str]]:
    command_results = safe_read_json_dict(remediation_command_results_summary_path)
    evaluator = safe_read_json_dict(remediation_evaluator_summary_path)
    observation_status_by_action: dict[str, str] = {}
    entries = (
        cast(list[object], command_results.get("entries"))
        if isinstance(command_results.get("entries"), list)
        else []
    )
    for item in entries:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, object], item)
        action_key = item.get("action_key")
        observation_status = item.get("observation_status")
        if isinstance(action_key, str) and isinstance(observation_status, str):
            observation_status_by_action[action_key] = observation_status
    evaluation_result_by_action: dict[str, str] = {}
    actions = (
        cast(list[object], evaluator.get("actions"))
        if isinstance(evaluator.get("actions"), list)
        else []
    )
    for item in actions:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, object], item)
        action_key = item.get("action_key")
        evaluation_result = item.get("evaluation_result")
        if isinstance(action_key, str) and isinstance(evaluation_result, str):
            evaluation_result_by_action[action_key] = evaluation_result
    return observation_status_by_action, evaluation_result_by_action


def build_remediation_scoreboard(
    *,
    remediation_session_checkpoint_summary_path: Path | None = None,
    remediation_command_results_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    checkpoint = safe_read_json_dict(remediation_session_checkpoint_summary_path)
    base_actions = (
        cast(list[object], checkpoint.get("actions"))
        if isinstance(checkpoint.get("actions"), list)
        else []
    )
    observation_status_by_action, evaluation_result_by_action = _feedback_summary_maps(
        remediation_command_results_summary_path,
        remediation_evaluator_summary_path,
    )
    actions = _enrich_actions_with_feedback(
        [item for item in base_actions if isinstance(item, dict)],
        observation_status_by_action,
        evaluation_result_by_action,
    )
    pass_count = _as_int(checkpoint.get("pass_action_count")) or 0
    fail_count = _as_int(checkpoint.get("fail_action_count")) or 0
    retry_count = _as_int(checkpoint.get("retry_action_count")) or 0
    pending_count = _as_int(checkpoint.get("pending_action_count")) or 0
    total_count = len(actions)
    completion_rate = 0.0 if total_count == 0 else round(pass_count / total_count, 4)
    blocking_action_items = sorted(
        [
            item
            for item in actions
            if isinstance(item, dict) and item.get("checkpoint_status") in {"fail", "retry"}
        ],
        key=_action_priority_key,
    )
    blocking_actions = [item["action_key"] for item in blocking_action_items]
    blocking_action_observed_sources = {
        item["action_key"]: _action_observed_sources(item) for item in blocking_action_items
    }
    blocking_action_stage_signal_confidence = {
        item["action_key"]: item.get("stage_signal_confidence") for item in blocking_action_items
    }
    next_action = _next_action(actions)
    scoreboard_status = _scoreboard_status(checkpoint, actions)
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)
    observed_source_counts = _observed_source_counts(actions)
    summary = {
        "scoreboard_status": scoreboard_status,
        "planned_action_count": total_count,
        "pass_action_count": pass_count,
        "fail_action_count": fail_count,
        "retry_action_count": retry_count,
        "pending_action_count": pending_count,
        "completion_rate": completion_rate,
        "next_action_command": next_action.get("command")
        if isinstance(next_action, dict)
        else checkpoint.get("next_action_command"),
        "next_action_observed_sources": _action_observed_sources(next_action)
        if isinstance(next_action, dict)
        else [],
        "next_action_stage_signal_confidence": (
            next_action.get("stage_signal_confidence") if isinstance(next_action, dict) else None
        ),
        "blocking_action_keys": blocking_actions,
        "blocking_action_observed_sources": blocking_action_observed_sources,
        "blocking_action_stage_signal_confidence": blocking_action_stage_signal_confidence,
        "observed_source_counts": observed_source_counts,
        "remediation_command_results_summary_path": (
            str(remediation_command_results_summary_path)
            if remediation_command_results_summary_path is not None
            else None
        ),
        "remediation_evaluator_summary_path": (
            str(remediation_evaluator_summary_path)
            if remediation_evaluator_summary_path is not None
            else None
        ),
        "remediation_session_checkpoint_summary_path": (
            str(remediation_session_checkpoint_summary_path)
            if remediation_session_checkpoint_summary_path is not None
            else None
        ),
        "checkpoint_status": checkpoint.get("checkpoint_status"),
        "actions": actions,
        "quick_navigation": quick_navigation,
        "related_reports": related_reports,
        "remediation_scoreboard_report_path": str(out_path) if out_path is not None else None,
    }

    lines = ["# Remediation Scoreboard", ""]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(
        [
            "## Scoreboard Summary",
            "",
            f"- scoreboard_status: {summary['scoreboard_status']}",
            f"- planned_action_count: {summary['planned_action_count']}",
            f"- pass_action_count: {summary['pass_action_count']}",
            f"- fail_action_count: {summary['fail_action_count']}",
            f"- retry_action_count: {summary['retry_action_count']}",
            f"- pending_action_count: {summary['pending_action_count']}",
            f"- completion_rate: {summary['completion_rate']}",
            f"- next_action_command: {summary['next_action_command']}",
            f"- next_action_observed_sources: {summary['next_action_observed_sources']}",
            f"- next_action_stage_signal_confidence: {summary['next_action_stage_signal_confidence']}",
            f"- checkpoint_status: {summary['checkpoint_status']}",
            f"- blocking_action_keys: {summary['blocking_action_keys']}",
            f"- remediation_command_results_summary_path: {summary['remediation_command_results_summary_path']}",
            f"- remediation_evaluator_summary_path: {summary['remediation_evaluator_summary_path']}",
            f"- remediation_session_checkpoint_summary_path: {summary['remediation_session_checkpoint_summary_path']}",
            "",
            "## Observed Source Counts",
            "",
        ]
    )
    if observed_source_counts:
        for key in sorted(observed_source_counts):
            lines.append(f"- {key}: {observed_source_counts[key]}")
    else:
        lines.append("- observed_source_counts: none")

    lines.extend(
        [
            "",
            "## Blocking Action Sources",
            "",
        ]
    )
    if blocking_action_observed_sources:
        for key in sorted(blocking_action_observed_sources):
            lines.append(f"- {key}: {blocking_action_observed_sources[key]}")
            lines.append(
                f"  - stage_signal_confidence: {blocking_action_stage_signal_confidence.get(key)}"
            )
    else:
        lines.append("- blocking_action_observed_sources: none")

    lines.extend(
        [
            "",
            "## Action Statuses",
            "",
        ]
    )
    if actions:
        for item in actions:
            if not isinstance(item, dict):
                continue
            lines.append(f"- {item['action_key']}: `{item['command']}`")
            lines.append(f"  - checkpoint_status: {item.get('checkpoint_status')}")
            lines.append(f"  - evidence_status: {item.get('evidence_status')}")
            lines.append(f"  - observed_sources: {item.get('observed_sources')}")
            lines.append(f"  - stage_signal_confidence: {item.get('stage_signal_confidence')}")
            lines.append(
                f"  - feedback_observation_status: {item.get('feedback_observation_status')}"
            )
            lines.append(
                f"  - feedback_evaluation_result: {item.get('feedback_evaluation_result')}"
            )
            lines.append(f"  - feedback_priority_reason: {item.get('feedback_priority_reason')}")
            lines.append(f"  - operator_notes: {item.get('operator_notes')}")
    else:
        lines.append("- action_statuses: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
