from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.loaders import safe_read_json_dict
from sis.reports import remediation_session_checkpoint_actions
from sis.reports import remediation_session_checkpoint_navigation
from sis.storage.jsonl_store import write_json

VALID_RESULTS = remediation_session_checkpoint_actions.VALID_RESULTS
_action_observed_sources = remediation_session_checkpoint_actions.action_observed_sources
_confidence_rank = remediation_session_checkpoint_actions.confidence_rank
_stage_rank = remediation_session_checkpoint_actions.stage_rank
_action_priority_key = remediation_session_checkpoint_actions.action_priority_key
_as_int = remediation_session_checkpoint_actions.as_int
_observed_source_counts = remediation_session_checkpoint_actions.observed_source_counts
_feedback_priority_reason = remediation_session_checkpoint_actions.feedback_priority_reason
_feedback_priority_rank = remediation_session_checkpoint_actions.feedback_priority_rank
_enrich_actions_with_feedback = remediation_session_checkpoint_actions.enrich_actions_with_feedback
_next_action = remediation_session_checkpoint_actions.next_action
_merge_actions = remediation_session_checkpoint_actions.merge_actions
_checkpoint_summary_status = remediation_session_checkpoint_actions.checkpoint_summary_status
_quick_navigation = remediation_session_checkpoint_navigation.quick_navigation
_related_reports = remediation_session_checkpoint_navigation.related_reports


def _feedback_summary_maps(
    remediation_command_results_summary_path: Path | None,
    remediation_evaluator_summary_path: Path | None,
) -> tuple[dict[str, str], dict[str, str]]:
    command_results = safe_read_json_dict(remediation_command_results_summary_path)
    evaluator = safe_read_json_dict(remediation_evaluator_summary_path)
    observation_status_by_action: dict[str, str] = {}
    entries = cast(list[object], command_results.get("entries", []))
    if not isinstance(entries, list):
        entries = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        action_key = item.get("action_key")
        observation_status = item.get("observation_status")
        if isinstance(action_key, str) and isinstance(observation_status, str):
            observation_status_by_action[action_key] = observation_status
    evaluation_result_by_action: dict[str, str] = {}
    actions = cast(list[object], evaluator.get("actions", []))
    if not isinstance(actions, list):
        actions = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        action_key = item.get("action_key")
        evaluation_result = item.get("evaluation_result")
        if isinstance(action_key, str) and isinstance(evaluation_result, str):
            evaluation_result_by_action[action_key] = evaluation_result
    return observation_status_by_action, evaluation_result_by_action


def build_remediation_session_checkpoint(
    *,
    remediation_session_summary_path: Path | None = None,
    checkpoint_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
    action_key: str | None = None,
    result: str | None = None,
    note: str | None = None,
    evidence_path: str | None = None,
    observed_signal: str | None = None,
    stdout_summary: str | None = None,
    stderr_summary: str | None = None,
    exit_code: int | None = None,
    remediation_command_results_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
) -> str:
    session_summary = safe_read_json_dict(remediation_session_summary_path)
    previous_checkpoint = safe_read_json_dict(checkpoint_summary_path or summary_path)
    merged_actions = _merge_actions(
        session_summary.get("actions"),
        previous_checkpoint.get("actions"),
        action_key=action_key,
        result=result,
        note=note,
        evidence_path=evidence_path,
        observed_signal=observed_signal,
        stdout_summary=stdout_summary,
        stderr_summary=stderr_summary,
        exit_code=exit_code,
    )
    observation_status_by_action, evaluation_result_by_action = _feedback_summary_maps(
        remediation_command_results_summary_path,
        remediation_evaluator_summary_path,
    )
    merged_actions = _enrich_actions_with_feedback(
        merged_actions,
        observation_status_by_action,
        evaluation_result_by_action,
    )
    pending_count = sum(1 for item in merged_actions if item.get("checkpoint_status") == "pending")
    pass_count = sum(1 for item in merged_actions if item.get("checkpoint_status") == "pass")
    fail_count = sum(1 for item in merged_actions if item.get("checkpoint_status") == "fail")
    retry_count = sum(1 for item in merged_actions if item.get("checkpoint_status") == "retry")
    checkpoint_status = _checkpoint_summary_status(merged_actions)
    next_action = _next_action(merged_actions)
    next_action_command = next_action.get("command") if isinstance(next_action, dict) else None
    next_action_observed_sources = (
        _action_observed_sources(next_action) if isinstance(next_action, dict) else []
    )
    next_action_stage_signal_confidence = (
        next_action.get("stage_signal_confidence") if isinstance(next_action, dict) else None
    )
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)
    observed_source_counts = _observed_source_counts(merged_actions)
    summary = {
        "checkpoint_status": checkpoint_status,
        "planned_action_count": len(merged_actions),
        "pending_action_count": pending_count,
        "pass_action_count": pass_count,
        "fail_action_count": fail_count,
        "retry_action_count": retry_count,
        "next_action_command": next_action_command,
        "next_action_observed_sources": next_action_observed_sources,
        "next_action_stage_signal_confidence": next_action_stage_signal_confidence,
        "observed_source_counts": observed_source_counts,
        "remediation_session_summary_path": (
            str(remediation_session_summary_path)
            if remediation_session_summary_path is not None
            else None
        ),
        "updated_action_key": action_key,
        "updated_result": result,
        "updated_evidence_path": evidence_path,
        "updated_observed_signal": observed_signal,
        "updated_stdout_summary": stdout_summary,
        "updated_stderr_summary": stderr_summary,
        "updated_exit_code": exit_code,
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
        "actions": merged_actions,
        "quick_navigation": quick_navigation,
        "related_reports": related_reports,
        "remediation_session_checkpoint_report_path": str(out_path)
        if out_path is not None
        else None,
    }
    lines = ["# Remediation Session Checkpoint", ""]
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
            "## Checkpoint Summary",
            "",
            f"- checkpoint_status: {summary['checkpoint_status']}",
            f"- planned_action_count: {summary['planned_action_count']}",
            f"- pending_action_count: {summary['pending_action_count']}",
            f"- pass_action_count: {summary['pass_action_count']}",
            f"- fail_action_count: {summary['fail_action_count']}",
            f"- retry_action_count: {summary['retry_action_count']}",
            f"- next_action_command: {summary['next_action_command']}",
            f"- next_action_observed_sources: {summary['next_action_observed_sources']}",
            f"- next_action_stage_signal_confidence: {summary['next_action_stage_signal_confidence']}",
            f"- updated_action_key: {summary['updated_action_key']}",
            f"- updated_result: {summary['updated_result']}",
            f"- updated_evidence_path: {summary['updated_evidence_path']}",
            f"- updated_observed_signal: {summary['updated_observed_signal']}",
            f"- updated_stdout_summary: {summary['updated_stdout_summary']}",
            f"- updated_stderr_summary: {summary['updated_stderr_summary']}",
            f"- updated_exit_code: {summary['updated_exit_code']}",
            f"- remediation_command_results_summary_path: {summary['remediation_command_results_summary_path']}",
            f"- remediation_evaluator_summary_path: {summary['remediation_evaluator_summary_path']}",
            f"- remediation_session_summary_path: {summary['remediation_session_summary_path']}",
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
            "## Action Checkpoints",
            "",
        ]
    )
    if merged_actions:
        for item in merged_actions:
            lines.append(f"- {item['action_key']}: `{item['command']}`")
            lines.append(f"  - checkpoint_status: {item['checkpoint_status']}")
            lines.append(f"  - evidence_status: {item['evidence_status']}")
            lines.append(f"  - suggested_result: {item['suggested_result']}")
            lines.append(f"  - observed_sources: {item.get('observed_sources')}")
            lines.append(f"  - signal_observed_sources: {item.get('signal_observed_sources')}")
            lines.append(f"  - stage_signal_confidence: {item.get('stage_signal_confidence')}")
            lines.append(
                f"  - feedback_observation_status: {item.get('feedback_observation_status')}"
            )
            lines.append(
                f"  - feedback_evaluation_result: {item.get('feedback_evaluation_result')}"
            )
            lines.append(f"  - feedback_priority_reason: {item.get('feedback_priority_reason')}")
            lines.append(f"  - operator_notes: {item['operator_notes']}")
            lines.append(f"  - evidence_paths: {item['evidence_paths']}")
            lines.append(f"  - observed_signals: {item['observed_signals']}")
            lines.append(f"  - latest_exit_code: {item['latest_exit_code']}")
            lines.append(f"  - latest_stdout_summary: {item['latest_stdout_summary']}")
            lines.append(f"  - latest_stderr_summary: {item['latest_stderr_summary']}")
            lines.append(f"  - command_result_records: {item['command_result_records']}")
    else:
        lines.append("- action_checkpoints: none")
    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
