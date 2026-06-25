from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.reports.remediation_planner_diffs import planner_entry_diffs, planner_rerun_diff
from sis.reports.remediation_planner_entries import (
    as_int,
    entry_key,
    evaluator_provenance_map,
    feedback_maps,
    feedback_priority_rank,
    planner_status as derive_planner_status,
    planner_entries,
    recommended_command_chain as derive_recommended_command_chain,
)
from sis.reports.remediation_planner_manifest import latest_planner_manifest
from sis.reports.remediation_planner_markdown import render_remediation_planner_markdown
from sis.reports.remediation_planner_navigation import (
    quick_navigation,
    related_reports,
)
from sis.storage.jsonl_store import write_json


def build_remediation_planner(
    *,
    phase_gate_summary_path: Path | None = None,
    runbook_summary_path: Path | None = None,
    remediation_evaluator_summary_path: Path | None = None,
    remediation_command_results_summary_path: Path | None = None,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    previous_summary = safe_read_json_dict(summary_path)
    previous_manifest = latest_planner_manifest(operation_chain_path)
    phase_gate_summary = safe_read_json_dict(phase_gate_summary_path)
    runbook_summary = safe_read_json_dict(runbook_summary_path)
    evaluator_summary = safe_read_json_dict(remediation_evaluator_summary_path)
    command_results_summary = safe_read_json_dict(remediation_command_results_summary_path)
    evaluator_provenance = evaluator_provenance_map(evaluator_summary)
    observation_status_by_action, evaluation_result_by_action = feedback_maps(
        {
            "entries": command_results_summary.get("entries"),
            "actions": evaluator_summary.get("actions"),
        }
    )
    entries = [
        *planner_entries(
            phase_gate_summary,
            source="phase_gate_review",
            provenance_map=evaluator_provenance,
            observation_status_by_action=observation_status_by_action,
            evaluation_result_by_action=evaluation_result_by_action,
        ),
        *planner_entries(
            runbook_summary,
            source="paper_operations_runbook",
            provenance_map=evaluator_provenance,
            observation_status_by_action=observation_status_by_action,
            evaluation_result_by_action=evaluation_result_by_action,
        ),
    ]
    entries.sort(
        key=lambda item: (
            feedback_priority_rank(item.get("feedback_priority_reason")),
            as_int(item.get("effective_priority")) or 999,
            as_int(item.get("priority")) or 999,
            str(item.get("source")),
            str(item.get("reason")),
        )
    )

    recommended_command_chain = derive_recommended_command_chain(entries)
    next_best_command = recommended_command_chain[0] if recommended_command_chain else None
    planner_status = derive_planner_status(entries)

    rerun_diff = planner_rerun_diff(
        previous_summary,
        previous_manifest,
        planner_status=planner_status,
        planned_step_count=len(entries),
        next_best_command=next_best_command,
        recommended_command_chain=recommended_command_chain,
    )
    entry_diffs = planner_entry_diffs(previous_summary.get("entries"), entries)
    planner_quick_navigation = quick_navigation(out_path)
    planner_related_reports = related_reports(out_path)

    summary = {
        "planner_status": planner_status,
        "planned_step_count": len(entries),
        "next_best_command": next_best_command,
        "source_policy_summary": {
            entry_key(item): {
                "source_confidence": item.get("source_confidence"),
                "source_policy": item.get("source_policy"),
                "effective_priority": item.get("effective_priority"),
            }
            for item in entries
        },
        "recommended_command_chain": recommended_command_chain,
        "phase_gate_summary_path": str(phase_gate_summary_path)
        if phase_gate_summary_path is not None
        else None,
        "runbook_summary_path": str(runbook_summary_path)
        if runbook_summary_path is not None
        else None,
        "remediation_evaluator_summary_path": (
            str(remediation_evaluator_summary_path)
            if remediation_evaluator_summary_path is not None
            else None
        ),
        "remediation_command_results_summary_path": (
            str(remediation_command_results_summary_path)
            if remediation_command_results_summary_path is not None
            else None
        ),
        "operation_chain_path": str(operation_chain_path)
        if operation_chain_path is not None
        else None,
        "previous_planner_status": previous_summary.get("planner_status")
        or previous_manifest.get("status"),
        "previous_planner_manifest_run_id": previous_manifest.get("run_id"),
        "planner_rerun_diff": rerun_diff,
        "planner_entry_diffs": entry_diffs,
        "entries": entries,
        "quick_navigation": planner_quick_navigation,
        "related_reports": planner_related_reports,
        "remediation_planner_report_path": str(out_path) if out_path is not None else None,
    }
    text = render_remediation_planner_markdown(summary)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
