from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import write_json


VALID_RESULTS = {"pending", "pass", "fail", "retry"}


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_session_checkpoint_report": str(out_path),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_session_checkpoint_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _action_observed_sources(item: dict[str, Any]) -> list[str]:
    values = item.get("observed_sources")
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if isinstance(value, str)]


def _confidence_rank(value: object) -> int:
    return {
        "unknown": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
    }.get(str(value or "unknown"), 0)


def _stage_rank(value: object) -> int:
    return {
        "preflight": 0,
        "execute": 1,
        "post_check": 2,
    }.get(str(value or ""), 99)


def _action_priority_key(item: dict[str, Any]) -> tuple[int, int, int, int, int, str, str]:
    effective_priority = _as_int(item.get("effective_priority"))
    priority = _as_int(item.get("priority"))
    sequence = _as_int(item.get("sequence")) or 0
    return (
        effective_priority
        if effective_priority is not None
        else (priority if priority is not None else 999),
        priority if priority is not None else 999,
        _stage_rank(item.get("stage")),
        _confidence_rank(item.get("stage_signal_confidence")),
        sequence,
        str(item.get("source") or ""),
        str(item.get("reason") or ""),
    )


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _observed_source_counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
        for source in _action_observed_sources(item):
            counts[source] = counts.get(source, 0) + 1
    return counts


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


def _feedback_priority_reason(evaluation_result: object, observation_status: object) -> str:
    evaluation_value = str(evaluation_result or "")
    observation_value = str(observation_status or "")
    if evaluation_value == "fail":
        return "evaluation_failed"
    if evaluation_value == "manual_review":
        return "manual_review_pending"
    if evaluation_value == "partial":
        return "partial_verification"
    if observation_value != "observed":
        return "missing_command_observation"
    if evaluation_value == "pass":
        return "verification_passed"
    return "no_feedback"


def _feedback_priority_rank(item: dict[str, Any]) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(item.get("feedback_priority_reason") or "no_feedback"), 5)


def _enrich_actions_with_feedback(
    actions: list[dict[str, Any]],
    observation_status_by_action: dict[str, str],
    evaluation_result_by_action: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        action_key = str(item.get("action_key") or "")
        observation_status = observation_status_by_action.get(action_key)
        evaluation_result = evaluation_result_by_action.get(action_key)
        feedback_priority_reason = _feedback_priority_reason(
            evaluation_result,
            observation_status,
        )
        enriched.append(
            {
                **item,
                "feedback_observation_status": observation_status,
                "feedback_evaluation_result": evaluation_result,
                "feedback_priority_reason": feedback_priority_reason,
            }
        )
    return enriched


def _next_action(actions: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        item
        for item in actions
        if isinstance(item, dict) and item.get("checkpoint_status") in {"retry", "pending"}
    ]
    if not candidates:
        return None
    status_rank = {"retry": 0, "pending": 1}
    return min(
        candidates,
        key=lambda item: (
            status_rank.get(str(item.get("checkpoint_status") or ""), 99),
            _feedback_priority_rank(item),
            *_action_priority_key(item),
        ),
    )


def _merge_actions(
    session_actions: object,
    previous_actions: object,
    *,
    action_key: str | None = None,
    result: str | None = None,
    note: str | None = None,
    evidence_path: str | None = None,
    observed_signal: str | None = None,
    stdout_summary: str | None = None,
    stderr_summary: str | None = None,
    exit_code: int | None = None,
) -> list[dict[str, Any]]:
    current = session_actions if isinstance(session_actions, list) else []
    previous_list = previous_actions if isinstance(previous_actions, list) else []
    previous = {
        str(cast(dict[str, Any], item).get("action_key")): cast(dict[str, Any], item)
        for item in previous_list
        if isinstance(item, dict) and cast(dict[str, Any], item).get("action_key")
    }
    merged: list[dict[str, Any]] = []
    for item in current:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        key = str(item.get("action_key") or "")
        previous_item = previous.get(key, {})
        checkpoint_status = previous_item.get("checkpoint_status") or "pending"
        if key == action_key and result in VALID_RESULTS:
            checkpoint_status = result
        evidence_status = (
            previous_item.get("evidence_status")
            or item.get("evidence_status")
            or "evidence_missing"
        )
        if checkpoint_status == "pass":
            evidence_status = "evidence_recorded"
        elif checkpoint_status in {"fail", "retry"}:
            evidence_status = "needs_review"
        operator_notes_value = previous_item.get("operator_notes")
        operator_notes: list[object] = (
            cast(list[object], operator_notes_value)
            if isinstance(operator_notes_value, list)
            else []
        )
        if key == action_key and note:
            operator_notes = [*operator_notes, note]
        evidence_paths_value = previous_item.get("evidence_paths")
        evidence_paths: list[object] = (
            cast(list[object], evidence_paths_value)
            if isinstance(evidence_paths_value, list)
            else []
        )
        if key == action_key and evidence_path:
            evidence_paths = [*evidence_paths, evidence_path]
        observed_signals_value = previous_item.get("observed_signals")
        observed_signals: list[object] = (
            cast(list[object], observed_signals_value)
            if isinstance(observed_signals_value, list)
            else []
        )
        if key == action_key and observed_signal:
            observed_signals = [*observed_signals, observed_signal]
        command_result_records_value = previous_item.get("command_result_records")
        command_result_records: list[object] = (
            cast(list[object], command_result_records_value)
            if isinstance(command_result_records_value, list)
            else []
        )
        latest_exit_code = previous_item.get("latest_exit_code")
        latest_stdout_summary = previous_item.get("latest_stdout_summary")
        latest_stderr_summary = previous_item.get("latest_stderr_summary")
        if key == action_key and any(
            value is not None
            for value in (evidence_path, observed_signal, stdout_summary, stderr_summary, exit_code)
        ):
            record: dict[str, object] = {}
            if evidence_path:
                record["evidence_path"] = evidence_path
            if observed_signal:
                record["observed_signal"] = observed_signal
            if stdout_summary:
                record["stdout_summary"] = stdout_summary
            if stderr_summary:
                record["stderr_summary"] = stderr_summary
            if exit_code is not None:
                record["exit_code"] = exit_code
            if result:
                record["checkpoint_result"] = result
            command_result_records = [*command_result_records, record]
            if exit_code is not None:
                latest_exit_code = exit_code
            if stdout_summary:
                latest_stdout_summary = stdout_summary
            if stderr_summary:
                latest_stderr_summary = stderr_summary
        merged.append(
            {
                **item,
                "checkpoint_status": checkpoint_status,
                "evidence_status": evidence_status,
                "operator_notes": operator_notes,
                "evidence_paths": list(
                    dict.fromkeys(str(value) for value in evidence_paths if isinstance(value, str))
                ),
                "observed_signals": list(
                    dict.fromkeys(
                        str(value) for value in observed_signals if isinstance(value, str)
                    )
                ),
                "latest_exit_code": latest_exit_code,
                "latest_stdout_summary": latest_stdout_summary,
                "latest_stderr_summary": latest_stderr_summary,
                "command_result_records": command_result_records,
            }
        )
    return merged


def _checkpoint_summary_status(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "no_actions"
    statuses = [str(item.get("checkpoint_status")) for item in actions]
    if any(status == "fail" for status in statuses):
        return "attention_required"
    if any(status == "retry" for status in statuses):
        return "retry_pending"
    if all(status == "pass" for status in statuses):
        return "completed"
    return "in_progress"


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
