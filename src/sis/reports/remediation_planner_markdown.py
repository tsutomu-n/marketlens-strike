from __future__ import annotations

from typing import Any, Mapping, cast


def _mapping(value: object) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], value) if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return cast(list[Any], value) if isinstance(value, list) else []


def render_remediation_planner_markdown(summary: dict[str, object]) -> str:
    quick_navigation = _mapping(summary.get("quick_navigation"))
    related_reports = _mapping(summary.get("related_reports"))
    planner_rerun_diff = _mapping(summary.get("planner_rerun_diff"))
    command_chain_diff = _mapping(planner_rerun_diff.get("command_chain_diff"))
    planner_entry_diffs = _mapping(summary.get("planner_entry_diffs"))
    entries = _list(summary.get("entries"))
    recommended_command_chain = _list(summary.get("recommended_command_chain"))

    chain_trend = command_chain_diff.get("trend")
    chain_added = command_chain_diff.get("added")
    chain_removed = command_chain_diff.get("removed")
    chain_unchanged = command_chain_diff.get("unchanged")

    lines = ["# Remediation Planner Dry Run", ""]
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
            "## Planner Summary",
            "",
            f"- planner_status: {summary['planner_status']}",
            f"- planned_step_count: {summary['planned_step_count']}",
            f"- next_best_command: {summary['next_best_command']}",
            f"- phase_gate_summary_path: {summary['phase_gate_summary_path']}",
            f"- runbook_summary_path: {summary['runbook_summary_path']}",
            f"- remediation_evaluator_summary_path: {summary['remediation_evaluator_summary_path']}",
            f"- remediation_command_results_summary_path: {summary['remediation_command_results_summary_path']}",
            f"- operation_chain_path: {summary['operation_chain_path']}",
            "",
            "## Recommended Command Chain",
            "",
        ]
    )
    if recommended_command_chain:
        lines.extend(f"- `{command}`" for command in recommended_command_chain)
    else:
        lines.append("- recommended_command_chain: none")

    lines.extend(
        [
            "",
            "## Planner Rerun Diff",
            "",
            f"- trend: {planner_rerun_diff['trend']}",
            f"- previous_summary_status: {planner_rerun_diff['previous_summary_status']}",
            f"- previous_manifest_status: {planner_rerun_diff['previous_manifest_status']}",
            f"- current_status: {planner_rerun_diff['current_status']}",
            f"- previous_next_best_command: {planner_rerun_diff['previous_next_best_command']}",
            f"- current_next_best_command: {planner_rerun_diff['current_next_best_command']}",
            f"- previous_planned_step_count: {planner_rerun_diff['previous_planned_step_count']}",
            f"- current_planned_step_count: {planner_rerun_diff['current_planned_step_count']}",
            f"- previous_manifest_run_id: {planner_rerun_diff['previous_manifest_run_id']}",
            "",
            "## Recommended Command Chain Diff",
            "",
            f"- trend: {chain_trend}",
            f"- added: {chain_added}",
            f"- removed: {chain_removed}",
            f"- unchanged: {chain_unchanged}",
            "",
            "## Planner Entry Diffs",
            "",
        ]
    )
    if planner_entry_diffs:
        for key, diff_value in planner_entry_diffs.items():
            diff = _mapping(diff_value)
            lines.append(f"- {key}: {diff['trend']}")
            lines.append(f"  - previous_status: {diff['previous_status']}")
            lines.append(f"  - current_status: {diff['current_status']}")
            lines.append(f"  - previous_commands: {diff['previous_commands']}")
            lines.append(f"  - current_commands: {diff['current_commands']}")
            lines.append(f"  - active: {diff['active']}")
    else:
        lines.append("- planner_entry_diffs: none")

    lines.extend(["", "## Planned Steps", ""])
    if entries:
        for entry_value in entries:
            entry = _mapping(entry_value)
            lines.append(f"- priority_{entry['priority']}_{entry['source']}: {entry['reason']}")
            lines.append(f"  - status: {entry['status']}")
            lines.append(f"  - why: {entry['why']}")
            lines.append(f"  - effective_priority: {entry['effective_priority']}")
            lines.append(f"  - observed_sources: {entry['observed_sources']}")
            lines.append(f"  - source_confidence: {entry['source_confidence']}")
            lines.append(f"  - source_policy: {entry['source_policy']}")
            lines.append(f"  - feedback_priority_reason: {entry['feedback_priority_reason']}")
            lines.append(f"  - supporting_action_keys: {entry['supporting_action_keys']}")
            for command in _list(entry.get("commands")):
                lines.append(f"  - next: `{command}`")
    else:
        lines.append("- planned_steps: none")

    return "\n".join(lines).rstrip() + "\n"
