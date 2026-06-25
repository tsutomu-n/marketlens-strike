from __future__ import annotations

from typing import Any, cast

from sis.reports.remediation_planner_entries import as_int, entry_key


def planner_status_rank(status: object) -> int:
    ranks = {
        "matched": 0,
        "no_actions": 0,
        "improving": 1,
        "planned": 1,
        "stalled": 2,
        "regressed": 3,
    }
    return ranks.get(str(status), 99)


def note_map(notes: object) -> dict[str, str]:
    if not isinstance(notes, list):
        return {}
    mapped: dict[str, str] = {}
    for note in notes:
        if not isinstance(note, str) or "=" not in note:
            continue
        key, value = note.split("=", 1)
        mapped[key] = value
    return mapped


def planner_entry_diffs(
    previous_entries: object, current_entries: list[dict[str, Any]]
) -> dict[str, dict[str, object]]:
    previous_list = previous_entries if isinstance(previous_entries, list) else []
    previous = {
        entry_key(cast(dict[str, Any], item)): cast(dict[str, Any], item)
        for item in previous_list
        if isinstance(item, dict) and entry_key(cast(dict[str, Any], item))
    }
    current = {entry_key(item): item for item in current_entries if entry_key(item)}
    diffs: dict[str, dict[str, object]] = {}
    for key in sorted(set(previous) | set(current)):
        previous_entry = previous.get(key, {})
        current_entry = current.get(key, {})
        previous_status = previous_entry.get("status")
        current_status = current_entry.get("status")
        previous_commands_value = previous_entry.get("commands")
        previous_commands = (
            cast(list[object], previous_commands_value)
            if isinstance(previous_commands_value, list)
            else []
        )
        current_commands_value = current_entry.get("commands")
        current_commands = (
            cast(list[object], current_commands_value)
            if isinstance(current_commands_value, list)
            else []
        )
        if not previous_entry:
            trend = "new"
        elif not current_entry:
            trend = "removed"
        elif previous_status == current_status and previous_commands == current_commands:
            trend = "unchanged"
        elif planner_status_rank(current_status) < planner_status_rank(previous_status):
            trend = "improved"
        elif planner_status_rank(current_status) > planner_status_rank(previous_status):
            trend = "regressed"
        else:
            trend = "changed"
        diffs[key] = {
            "source": current_entry.get("source") or previous_entry.get("source"),
            "reason": current_entry.get("reason") or previous_entry.get("reason"),
            "previous_status": previous_status,
            "current_status": current_status,
            "previous_commands": previous_commands,
            "current_commands": current_commands,
            "trend": trend,
            "active": bool(current_entry),
        }
    return diffs


def command_chain_diff(previous_chain: object, current_chain: list[str]) -> dict[str, object]:
    previous = (
        [item for item in previous_chain if isinstance(item, str)]
        if isinstance(previous_chain, list)
        else []
    )
    added = [item for item in current_chain if item not in previous]
    removed = [item for item in previous if item not in current_chain]
    unchanged = [item for item in current_chain if item in previous]
    if not previous:
        trend = "first_run"
    elif not added and not removed:
        trend = "unchanged"
    elif removed and not added:
        trend = "narrowed"
    elif added and not removed:
        trend = "expanded"
    else:
        trend = "changed"
    return {
        "previous": previous,
        "current": current_chain,
        "added": added,
        "removed": removed,
        "unchanged": unchanged,
        "trend": trend,
    }


def planner_rerun_diff(
    previous_summary: dict,
    previous_manifest: dict,
    *,
    planner_status: str,
    planned_step_count: int,
    next_best_command: str | None,
    recommended_command_chain: list[str],
) -> dict[str, object]:
    previous_notes = note_map(previous_manifest.get("notes"))
    previous_status = previous_summary.get("planner_status") or previous_manifest.get("status")
    previous_next_best_command = previous_summary.get("next_best_command") or previous_notes.get(
        "next_best_command"
    )
    previous_planned_step_count_raw = previous_summary.get(
        "planned_step_count"
    ) or previous_notes.get("planned_step_count")
    previous_planned_step_count = as_int(previous_planned_step_count_raw)
    if not previous_summary and not previous_manifest:
        trend = "first_run"
    elif (
        previous_status == planner_status
        and previous_next_best_command == next_best_command
        and previous_planned_step_count == planned_step_count
    ):
        trend = "unchanged"
    elif planner_status_rank(planner_status) < planner_status_rank(previous_status):
        trend = "improved"
    elif planner_status_rank(planner_status) > planner_status_rank(previous_status):
        trend = "regressed"
    elif (
        previous_planned_step_count is not None and planned_step_count < previous_planned_step_count
    ):
        trend = "improved"
    elif (
        previous_planned_step_count is not None and planned_step_count > previous_planned_step_count
    ):
        trend = "regressed"
    else:
        trend = "changed"
    return {
        "previous_summary_path": previous_summary.get("remediation_planner_report_path"),
        "previous_manifest_run_id": previous_manifest.get("run_id"),
        "previous_summary_status": previous_summary.get("planner_status"),
        "previous_manifest_status": previous_manifest.get("status"),
        "current_status": planner_status,
        "previous_next_best_command": previous_next_best_command,
        "current_next_best_command": next_best_command,
        "previous_planned_step_count": previous_planned_step_count,
        "current_planned_step_count": planned_step_count,
        "trend": trend,
        "command_chain_diff": command_chain_diff(
            previous_summary.get("recommended_command_chain"),
            recommended_command_chain,
        ),
    }
