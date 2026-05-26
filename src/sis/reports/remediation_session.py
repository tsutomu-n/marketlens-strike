from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_session_report": str(out_path),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_session_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_checkpoint_report": str(
            reports_dir / "remediation_session_checkpoint.md"
        ),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evaluator_report": str(reports_dir / "remediation_evaluator.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _action_key(item: dict) -> str:
    return (
        f"priority_{item.get('priority')}_{item.get('source')}_{item.get('reason')}_"
        f"{item.get('stage')}_{item.get('sequence')}"
    )


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


def _action_sort_key(item: dict) -> tuple[int, int, int, int, int, int, str, str]:
    return (
        _feedback_priority_rank(item.get("feedback_priority_reason")),
        int(item.get("effective_priority") or item.get("priority") or 999),
        int(item.get("priority") or 999),
        _stage_rank(item.get("stage")),
        _confidence_rank(item.get("stage_signal_confidence")),
        int(item.get("sequence") or 0),
        str(item.get("source") or ""),
        str(item.get("reason") or ""),
    )


def _feedback_maps(
    command_results_summary: dict, evaluator_summary: dict
) -> tuple[dict[str, str], dict[str, str]]:
    entries = (
        command_results_summary.get("entries")
        if isinstance(command_results_summary.get("entries"), list)
        else []
    )
    observation_status_by_action: dict[str, str] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        action_key = item.get("action_key")
        observation_status = item.get("observation_status")
        if isinstance(action_key, str) and isinstance(observation_status, str):
            observation_status_by_action[action_key] = observation_status
    actions = (
        evaluator_summary.get("actions")
        if isinstance(evaluator_summary.get("actions"), list)
        else []
    )
    evaluation_result_by_action: dict[str, str] = {}
    for item in actions:
        if not isinstance(item, dict):
            continue
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
    if observation_value and observation_value != "observed":
        return "missing_command_observation"
    if evaluation_value == "pass":
        return "verification_passed"
    return "no_feedback"


def _feedback_priority_rank(reason: object) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(reason or "no_feedback"), 5)


def _session_status(actions: list[dict]) -> str:
    if not actions:
        return "no_actions"
    return "ready_for_dry_run"


def build_remediation_session(
    *,
    remediation_execution_plan_summary_path: Path | None = None,
    remediation_command_results_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    execution_plan = safe_read_json_dict(remediation_execution_plan_summary_path)
    command_results_summary = safe_read_json_dict(remediation_command_results_summary_path)
    evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    observation_status_by_action, evaluation_result_by_action = _feedback_maps(
        command_results_summary,
        evaluator_summary,
    )
    actions = (
        execution_plan.get("actions") if isinstance(execution_plan.get("actions"), list) else []
    )
    entries = (
        execution_plan.get("entries") if isinstance(execution_plan.get("entries"), list) else []
    )

    session_actions: list[dict] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        verification = (
            item.get("verification") if isinstance(item.get("verification"), list) else []
        )
        stage = str(item.get("stage") or "")
        recommendation_status = str(item.get("recommendation_status") or "")
        suggested_result = "pass"
        if recommendation_status in {"regressed", "stalled"} and stage in {"preflight", "execute"}:
            suggested_result = "needs_attention"
        action_key = _action_key(item)
        feedback_observation_status = observation_status_by_action.get(action_key)
        feedback_evaluation_result = evaluation_result_by_action.get(action_key)
        feedback_priority_reason = _feedback_priority_reason(
            feedback_evaluation_result,
            feedback_observation_status,
        )
        session_actions.append(
            {
                "action_key": action_key,
                "source": item.get("source"),
                "priority": item.get("priority"),
                "effective_priority": item.get("effective_priority"),
                "reason": item.get("reason"),
                "stage": stage,
                "sequence": item.get("sequence"),
                "command": item.get("command"),
                "recommendation_status": recommendation_status,
                "entry_trend": item.get("entry_trend"),
                "source_confidence": item.get("source_confidence"),
                "source_policy": item.get("source_policy"),
                "observed_sources": (
                    item.get("observed_sources")
                    if isinstance(item.get("observed_sources"), list)
                    else []
                ),
                "signal_observed_sources": (
                    item.get("signal_observed_sources")
                    if isinstance(item.get("signal_observed_sources"), dict)
                    else {}
                ),
                "stage_signal_confidence": item.get("stage_signal_confidence") or "unknown",
                "feedback_observation_status": feedback_observation_status,
                "feedback_evaluation_result": feedback_evaluation_result,
                "feedback_priority_reason": feedback_priority_reason,
                "session_status": "pending",
                "evidence_status": "evidence_missing",
                "suggested_result": suggested_result,
                "verification": verification,
                "operator_notes": [],
            }
        )
    session_actions.sort(key=_action_sort_key)

    next_pending_action = session_actions[0] if session_actions else None

    session_summary = {
        "session_status": _session_status(session_actions),
        "planned_reason_count": len(entries),
        "planned_action_count": len(session_actions),
        "pending_action_count": len(session_actions),
        "next_pending_command": next_pending_action["command"]
        if isinstance(next_pending_action, dict)
        else None,
        "next_pending_stage_signal_confidence": (
            next_pending_action.get("stage_signal_confidence")
            if isinstance(next_pending_action, dict)
            else None
        ),
        "next_pending_feedback_priority_reason": (
            next_pending_action.get("feedback_priority_reason")
            if isinstance(next_pending_action, dict)
            else None
        ),
        "remediation_execution_plan_summary_path": (
            str(remediation_execution_plan_summary_path)
            if remediation_execution_plan_summary_path is not None
            else None
        ),
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
        "execution_plan_status": execution_plan.get("execution_plan_status"),
        "planner_status": execution_plan.get("planner_status"),
        "planner_rerun_trend": execution_plan.get("planner_rerun_trend"),
        "entries": entries,
        "actions": session_actions,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "remediation_session_report_path": str(out_path) if out_path is not None else None,
    }

    lines = ["# Remediation Session Dry Run", ""]
    if session_summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(
            f"- {key}: {value}" for key, value in session_summary["quick_navigation"].items()
        )
        lines.append("")
    if session_summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(
            f"- {key}: {value}" for key, value in session_summary["related_reports"].items()
        )
        lines.append("")
    lines.extend(
        [
            "## Session Summary",
            "",
            f"- session_status: {session_summary['session_status']}",
            f"- planned_reason_count: {session_summary['planned_reason_count']}",
            f"- planned_action_count: {session_summary['planned_action_count']}",
            f"- pending_action_count: {session_summary['pending_action_count']}",
            f"- next_pending_command: {session_summary['next_pending_command']}",
            f"- next_pending_stage_signal_confidence: {session_summary['next_pending_stage_signal_confidence']}",
            f"- next_pending_feedback_priority_reason: {session_summary['next_pending_feedback_priority_reason']}",
            f"- execution_plan_status: {session_summary['execution_plan_status']}",
            f"- planner_status: {session_summary['planner_status']}",
            f"- planner_rerun_trend: {session_summary['planner_rerun_trend']}",
            f"- remediation_execution_plan_summary_path: {session_summary['remediation_execution_plan_summary_path']}",
            f"- remediation_command_results_summary_path: {session_summary['remediation_command_results_summary_path']}",
            f"- remediation_evaluator_summary_path: {session_summary['remediation_evaluator_summary_path']}",
            "",
            "## Pending Actions",
            "",
        ]
    )
    if session_actions:
        for action in session_actions:
            lines.append(f"- {action['action_key']}: `{action['command']}`")
            lines.append(f"  - session_status: {action['session_status']}")
            lines.append(f"  - evidence_status: {action['evidence_status']}")
            lines.append(f"  - suggested_result: {action['suggested_result']}")
            lines.append(f"  - recommendation_status: {action['recommendation_status']}")
            lines.append(f"  - entry_trend: {action['entry_trend']}")
            lines.append(f"  - effective_priority: {action['effective_priority']}")
            lines.append(f"  - source_confidence: {action['source_confidence']}")
            lines.append(f"  - source_policy: {action['source_policy']}")
            lines.append(f"  - observed_sources: {action['observed_sources']}")
            lines.append(f"  - stage_signal_confidence: {action['stage_signal_confidence']}")
            lines.append(
                f"  - feedback_observation_status: {action['feedback_observation_status']}"
            )
            lines.append(f"  - feedback_evaluation_result: {action['feedback_evaluation_result']}")
            lines.append(f"  - feedback_priority_reason: {action['feedback_priority_reason']}")
            lines.append("  - verification:")
            for value in action["verification"]:
                lines.append(f"    - {value}")
    else:
        lines.append("- pending_actions: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, session_summary)
    return text
