from __future__ import annotations

from pathlib import Path
from typing import cast

from sis.reports.loaders import safe_read_json_dict
from sis.reports import remediation_execution_plan_navigation
from sis.reports.summary_normalizers import source_confidence_for_observed_sources
from sis.storage.jsonl_store import write_json


_quick_navigation = remediation_execution_plan_navigation.quick_navigation
_related_reports = remediation_execution_plan_navigation.related_reports


def _source_summaries(planner_summary: dict[str, object]) -> dict[str, dict[str, object]]:
    path_map = {
        "phase_gate_review": planner_summary.get("phase_gate_summary_path"),
        "paper_operations_runbook": planner_summary.get("runbook_summary_path"),
    }
    summaries: dict[str, dict[str, object]] = {}
    for source, raw_path in path_map.items():
        if isinstance(raw_path, str):
            summaries[source] = safe_read_json_dict(Path(raw_path))
        else:
            summaries[source] = {}
    return summaries


def _reason_values(source_summary: dict[str, object], field: str, reason: str) -> list[object]:
    values_by_reason = source_summary.get(field)
    if not isinstance(values_by_reason, dict):
        return []
    values = cast(dict[str, object], values_by_reason).get(reason)
    return cast(list[object], values) if isinstance(values, list) else []


def _flatten_observed_sources(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        flattened: list[str] = []
        for nested in value.values():
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    if isinstance(value, list):
        flattened: list[str] = []
        for nested in value:
            flattened.extend(_flatten_observed_sources(nested))
        return flattened
    return []


def _verification_confidence(signal_observed_sources: object, verification: list[str]) -> str:
    if not isinstance(signal_observed_sources, dict) or not verification:
        return "unknown"
    signal_sources = cast(dict[str, object], signal_observed_sources)
    flattened: list[str] = []
    for signal in verification:
        if not isinstance(signal, str):
            continue
        flattened.extend(_flatten_observed_sources(signal_sources.get(signal)))
    values = [str(source) for source in flattened if isinstance(source, str)]
    if not values:
        return "unknown"
    rank_map = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
    reverse_rank_map = {0: "high", 1: "medium", 2: "low", 3: "unknown"}
    normalized = [
        source_confidence_for_observed_sources([source]) or "unknown" for source in values
    ]
    return reverse_rank_map[max(rank_map.get(value, 3) for value in normalized)]


def _ordered_verification(signal_observed_sources: object, verification: list[str]) -> list[str]:
    if not isinstance(signal_observed_sources, dict):
        return verification
    rank_map = {"unknown": 0, "low": 1, "medium": 2, "high": 3}

    def _sort_key(signal: str) -> tuple[int, str]:
        confidence = _verification_confidence(signal_observed_sources, [signal])
        return (rank_map.get(confidence, 0), signal)

    return sorted([value for value in verification if isinstance(value, str)], key=_sort_key)


def _stage_order(
    status: object,
    trend: object,
    source_confidence: object,
    *,
    feedback_priority_reason: object,
    execute_signal_confidence: str,
    postcheck_signal_confidence: str,
) -> list[str]:
    status_value = str(status or "")
    trend_value = str(trend or "")
    confidence_value = str(source_confidence or "unknown")
    feedback_value = str(feedback_priority_reason or "no_feedback")
    if status_value == "matched":
        return ["post_check"]
    if feedback_value in {"evaluation_failed", "manual_review_pending", "partial_verification"}:
        return ["preflight", "execute", "post_check"]
    if execute_signal_confidence in {"low", "unknown"} or postcheck_signal_confidence in {
        "low",
        "unknown",
    }:
        return ["preflight", "execute", "post_check"]
    if confidence_value in {"low", "unknown"}:
        return ["preflight", "execute", "post_check"]
    if status_value in {"regressed", "stalled"} or trend_value in {"regressed", "new"}:
        return ["preflight", "execute", "post_check"]
    if status_value == "improving":
        return ["execute", "post_check"]
    return ["execute", "post_check"]


def _execution_plan_status(entries: list[dict]) -> str:
    statuses = [str(item.get("recommendation_status")) for item in entries]
    if not entries:
        return "no_actions"
    if any(status == "regressed" for status in statuses):
        return "regressed"
    if any(status == "stalled" for status in statuses):
        return "stalled"
    if any(status == "improving" for status in statuses):
        return "in_progress"
    if all(status == "matched" for status in statuses):
        return "postcheck_only"
    return "planned"


def _feedback_priority_rank(reason: object) -> int:
    return {
        "evaluation_failed": 0,
        "manual_review_pending": 1,
        "partial_verification": 2,
        "missing_command_observation": 3,
        "verification_passed": 4,
        "no_feedback": 5,
    }.get(str(reason or "no_feedback"), 5)


def build_remediation_execution_plan(
    *,
    remediation_planner_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    planner_summary = safe_read_json_dict(remediation_planner_summary_path)
    source_summaries = _source_summaries(planner_summary)
    planner_entries = (
        cast(list[object], planner_summary.get("entries"))
        if isinstance(planner_summary.get("entries"), list)
        else []
    )
    planner_entry_diffs = (
        planner_summary.get("planner_entry_diffs")
        if isinstance(planner_summary.get("planner_entry_diffs"), dict)
        else {}
    )

    planned_entries: list[dict] = []
    planned_actions: list[dict] = []
    for item in planner_entries:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, object], item)
        source = str(item.get("source") or "")
        reason = str(item.get("reason") or "")
        if not source or not reason:
            continue
        source_summary = source_summaries.get(source, {})
        preflight_commands = _reason_values(
            source_summary, "remediation_preflight_commands", reason
        )
        execute_commands = (
            cast(list[object], item.get("commands"))
            if isinstance(item.get("commands"), list)
            else []
        )
        postcheck_commands = _reason_values(
            source_summary, "remediation_postcheck_commands", reason
        )
        preflight_expected_outputs = _reason_values(
            source_summary, "remediation_preflight_expected_outputs", reason
        )
        execute_expected_outputs = _reason_values(
            source_summary, "remediation_execute_expected_outputs", reason
        )
        postcheck_pass_signals = _reason_values(
            source_summary, "remediation_postcheck_pass_signals", reason
        )
        diff_key = f"{source}:{reason}"
        entry_diff = (
            cast(dict[str, object], planner_entry_diffs).get(diff_key, {})
            if isinstance(planner_entry_diffs, dict)
            else {}
        )
        entry_diff = cast(dict[str, object], entry_diff) if isinstance(entry_diff, dict) else {}
        recommendation_status = item.get("status")
        entry_trend = entry_diff.get("trend")
        source_confidence = item.get("source_confidence")
        feedback_priority_reason = item.get("feedback_priority_reason")
        signal_observed_sources = (
            cast(dict[str, object], item.get("signal_observed_sources"))
            if isinstance(item.get("signal_observed_sources"), dict)
            else {}
        )
        ordered_preflight_verification = _ordered_verification(
            signal_observed_sources,
            [value for value in preflight_expected_outputs if isinstance(value, str)],
        )
        ordered_execute_verification = _ordered_verification(
            signal_observed_sources,
            [value for value in execute_expected_outputs if isinstance(value, str)],
        )
        ordered_postcheck_verification = _ordered_verification(
            signal_observed_sources,
            [value for value in postcheck_pass_signals if isinstance(value, str)],
        )
        execute_signal_confidence = _verification_confidence(
            signal_observed_sources,
            ordered_execute_verification,
        )
        postcheck_signal_confidence = _verification_confidence(
            signal_observed_sources,
            ordered_postcheck_verification,
        )
        stages = _stage_order(
            recommendation_status,
            entry_trend,
            source_confidence,
            feedback_priority_reason=feedback_priority_reason,
            execute_signal_confidence=execute_signal_confidence,
            postcheck_signal_confidence=postcheck_signal_confidence,
        )
        stage_map = {
            "preflight": {
                "commands": [command for command in preflight_commands if isinstance(command, str)],
                "verification": ordered_preflight_verification,
            },
            "execute": {
                "commands": [command for command in execute_commands if isinstance(command, str)],
                "verification": ordered_execute_verification,
            },
            "post_check": {
                "commands": [command for command in postcheck_commands if isinstance(command, str)],
                "verification": ordered_postcheck_verification,
            },
        }
        planned_entries.append(
            {
                "source": source,
                "priority": item.get("priority"),
                "reason": reason,
                "base_priority": item.get("priority"),
                "effective_priority": item.get("effective_priority"),
                "recommendation_status": recommendation_status,
                "recommendation_why": item.get("why"),
                "entry_trend": entry_trend,
                "observed_sources": (
                    item.get("observed_sources")
                    if isinstance(item.get("observed_sources"), list)
                    else []
                ),
                "source_confidence": source_confidence,
                "source_policy": item.get("source_policy"),
                "feedback_priority_reason": feedback_priority_reason,
                "signal_observed_sources": signal_observed_sources,
                "preflight_signal_confidence": _verification_confidence(
                    signal_observed_sources,
                    ordered_preflight_verification,
                ),
                "execute_signal_confidence": execute_signal_confidence,
                "postcheck_signal_confidence": postcheck_signal_confidence,
                "supporting_action_keys": (
                    item.get("supporting_action_keys")
                    if isinstance(item.get("supporting_action_keys"), list)
                    else []
                ),
                "stage_order": stages,
                "preflight_commands": stage_map["preflight"]["commands"],
                "execute_commands": stage_map["execute"]["commands"],
                "postcheck_commands": stage_map["post_check"]["commands"],
                "preflight_expected_outputs": stage_map["preflight"]["verification"],
                "execute_expected_outputs": stage_map["execute"]["verification"],
                "postcheck_pass_signals": stage_map["post_check"]["verification"],
            }
        )
        for stage in stages:
            stage_entry = stage_map.get(stage, {})
            commands = stage_entry.get("commands", [])
            verification = stage_entry.get("verification", [])
            for index, command in enumerate(commands, start=1):
                planned_actions.append(
                    {
                        "source": source,
                        "priority": item.get("priority"),
                        "effective_priority": item.get("effective_priority"),
                        "reason": reason,
                        "stage": stage,
                        "sequence": index,
                        "command": command,
                        "recommendation_status": recommendation_status,
                        "entry_trend": entry_trend,
                        "observed_sources": (
                            item.get("observed_sources")
                            if isinstance(item.get("observed_sources"), list)
                            else []
                        ),
                        "source_confidence": source_confidence,
                        "source_policy": item.get("source_policy"),
                        "feedback_priority_reason": feedback_priority_reason,
                        "signal_observed_sources": signal_observed_sources,
                        "stage_signal_confidence": {
                            "preflight": _verification_confidence(
                                signal_observed_sources,
                                ordered_preflight_verification,
                            ),
                            "execute": execute_signal_confidence,
                            "post_check": postcheck_signal_confidence,
                        }.get(stage, "unknown"),
                        "verification": verification,
                    }
                )

    planned_actions.sort(
        key=lambda item: (
            _feedback_priority_rank(item.get("feedback_priority_reason")),
            int(item.get("effective_priority") or 999),
            int(item.get("priority") or 999),
            str(item.get("source")),
            str(item.get("reason")),
            ["preflight", "execute", "post_check"].index(str(item.get("stage"))),
            int(item.get("sequence") or 0),
        )
    )
    recommended_execution_chain: list[str] = []
    for action in planned_actions:
        command = action.get("command")
        if isinstance(command, str) and command not in recommended_execution_chain:
            recommended_execution_chain.append(command)
    next_action_command = recommended_execution_chain[0] if recommended_execution_chain else None
    execution_plan_status = _execution_plan_status(planned_entries)
    summary = {
        "execution_plan_status": execution_plan_status,
        "planned_reason_count": len(planned_entries),
        "planned_action_count": len(planned_actions),
        "next_action_command": next_action_command,
        "recommended_execution_chain": recommended_execution_chain,
        "remediation_planner_summary_path": str(remediation_planner_summary_path)
        if remediation_planner_summary_path is not None
        else None,
        "planner_status": planner_summary.get("planner_status"),
        "planner_rerun_trend": (
            planner_summary.get("planner_rerun_diff", {}).get("trend")
            if isinstance(planner_summary.get("planner_rerun_diff"), dict)
            else None
        ),
        "entries": planned_entries,
        "actions": planned_actions,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "remediation_execution_plan_report_path": str(out_path) if out_path is not None else None,
    }

    lines = ["# Remediation Execution Plan Dry Run", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(
        [
            "## Execution Plan Summary",
            "",
            f"- execution_plan_status: {summary['execution_plan_status']}",
            f"- planned_reason_count: {summary['planned_reason_count']}",
            f"- planned_action_count: {summary['planned_action_count']}",
            f"- next_action_command: {summary['next_action_command']}",
            f"- planner_status: {summary['planner_status']}",
            f"- planner_rerun_trend: {summary['planner_rerun_trend']}",
            f"- remediation_planner_summary_path: {summary['remediation_planner_summary_path']}",
            "",
            "## Recommended Execution Chain",
            "",
        ]
    )
    if recommended_execution_chain:
        lines.extend(f"- `{command}`" for command in recommended_execution_chain)
    else:
        lines.append("- recommended_execution_chain: none")

    lines.extend(["", "## Planned Reasons", ""])
    if planned_entries:
        for entry in planned_entries:
            lines.append(f"- priority_{entry['priority']}_{entry['source']}: {entry['reason']}")
            lines.append(f"  - recommendation_status: {entry['recommendation_status']}")
            lines.append(f"  - recommendation_why: {entry['recommendation_why']}")
            lines.append(f"  - entry_trend: {entry['entry_trend']}")
            lines.append(f"  - effective_priority: {entry['effective_priority']}")
            lines.append(f"  - observed_sources: {entry['observed_sources']}")
            lines.append(f"  - source_confidence: {entry['source_confidence']}")
            lines.append(f"  - source_policy: {entry['source_policy']}")
            lines.append(f"  - feedback_priority_reason: {entry['feedback_priority_reason']}")
            lines.append(f"  - execute_signal_confidence: {entry['execute_signal_confidence']}")
            lines.append(f"  - postcheck_signal_confidence: {entry['postcheck_signal_confidence']}")
            lines.append(f"  - stage_order: {entry['stage_order']}")
    else:
        lines.append("- planned_reasons: none")

    lines.extend(["", "## Planned Actions", ""])
    if planned_actions:
        for action in planned_actions:
            lines.append(
                f"- priority_{action['priority']}_{action['source']}_{action['reason']}_{action['stage']}_{action['sequence']}: `{action['command']}`"
            )
            lines.append(f"  - recommendation_status: {action['recommendation_status']}")
            lines.append(f"  - entry_trend: {action['entry_trend']}")
            lines.append(f"  - effective_priority: {action['effective_priority']}")
            lines.append(f"  - observed_sources: {action['observed_sources']}")
            lines.append(f"  - source_confidence: {action['source_confidence']}")
            lines.append(f"  - source_policy: {action['source_policy']}")
            lines.append(f"  - feedback_priority_reason: {action['feedback_priority_reason']}")
            lines.append(f"  - stage_signal_confidence: {action['stage_signal_confidence']}")
            lines.append("  - verification:")
            for value in action["verification"]:
                lines.append(f"    - {value}")
    else:
        lines.append("- planned_actions: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
