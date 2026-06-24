from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.reports.loaders import safe_read_json_dict
from sis.reports import remediation_evaluator_observations as _evaluator_observations
from sis.reports import remediation_evaluator_paths as _evaluator_paths
from sis.reports import remediation_signal_evaluator as _signal_evaluator
from sis.storage.jsonl_store import write_json

_action_result = _signal_evaluator.action_result
_coerce_value = _signal_evaluator.coerce_value
_evaluate_signal = _signal_evaluator.evaluate_signal
_evaluate_signal_with_observations = _signal_evaluator.evaluate_signal_with_observations
_evaluator_status = _signal_evaluator.evaluator_status
_issue_preview_values = _signal_evaluator.issue_preview_values

_quick_navigation = _evaluator_paths.quick_navigation
_related_reports = _evaluator_paths.related_reports
_report_path_from_summary_path = _evaluator_paths.report_path_from_summary_path
_report_paths = _evaluator_paths.report_paths
_timeline_summary_paths = _evaluator_paths.timeline_summary_paths
_dashboard_bundle_summary_paths = _evaluator_paths.dashboard_bundle_summary_paths
_ops_review_paths = _evaluator_paths.ops_review_paths
_current_state_index_paths = _evaluator_paths.current_state_index_paths
_live_evidence_paths = _evaluator_observations.live_evidence_paths
_apply_aliases = _evaluator_observations.apply_aliases
_merge_observation_sources = _evaluator_observations.merge_observation_sources
_dashboard_bundle_summary_observations = (
    _evaluator_observations.dashboard_bundle_summary_observations
)
_ops_review_observations = _evaluator_observations.ops_review_observations
_current_state_index_observations = _evaluator_observations.current_state_index_observations
_live_evidence_summary_observations = _evaluator_observations.live_evidence_summary_observations
_timeline_summary_observations = _evaluator_observations.timeline_summary_observations
_manifest_note_observations = _evaluator_observations.manifest_note_observations
_markdown_report_observations = _evaluator_observations.markdown_report_observations


def _planner_summary_from_checkpoint(checkpoint: dict) -> dict:
    session_path = checkpoint.get("remediation_session_summary_path")
    session = safe_read_json_dict(Path(session_path) if isinstance(session_path, str) else None)
    execution_plan_path = session.get("remediation_execution_plan_summary_path")
    execution_plan = safe_read_json_dict(
        Path(execution_plan_path) if isinstance(execution_plan_path, str) else None
    )
    planner_summary_path = execution_plan.get("remediation_planner_summary_path")
    return safe_read_json_dict(
        Path(planner_summary_path) if isinstance(planner_summary_path, str) else None
    )


def _source_summaries(planner: dict) -> dict[str, dict]:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    return {
        "phase_gate_review": safe_read_json_dict(
            Path(phase_gate_path) if isinstance(phase_gate_path, str) else None
        ),
        "paper_operations_runbook": safe_read_json_dict(
            Path(runbook_path) if isinstance(runbook_path, str) else None
        ),
    }


def build_remediation_evaluator(
    *,
    remediation_session_checkpoint_summary_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    checkpoint = safe_read_json_dict(remediation_session_checkpoint_summary_path)
    planner = _planner_summary_from_checkpoint(checkpoint)
    source_summaries = _source_summaries(planner)
    report_paths = _report_paths(planner, source_summaries)
    ops_review_paths = _ops_review_paths(planner)
    current_state_index_paths = _current_state_index_paths(planner)
    live_evidence_paths = _live_evidence_paths(planner)
    ops_review_fields, ops_review_counts = _ops_review_observations(planner)
    current_state_index_fields, current_state_index_counts = _current_state_index_observations(
        planner
    )
    live_evidence_fields, live_evidence_counts = _live_evidence_summary_observations(planner)
    dashboard_bundle_fields, dashboard_bundle_counts = _dashboard_bundle_summary_observations(
        planner
    )
    timeline_fields, timeline_counts = _timeline_summary_observations(planner)
    manifest_fields, manifest_counts = _manifest_note_observations(planner)
    report_fields, report_counts = _markdown_report_observations(planner, source_summaries)
    fallback_fields, fallback_counts, fallback_field_sources, fallback_count_sources = (
        _merge_observation_sources(
            [
                ("live_evidence_summary", live_evidence_fields, live_evidence_counts),
                ("current_state_index", current_state_index_fields, current_state_index_counts),
                ("ops_review", ops_review_fields, ops_review_counts),
                ("dashboard_bundle", dashboard_bundle_fields, dashboard_bundle_counts),
                ("timeline_summary", timeline_fields, timeline_counts),
                ("manifest_notes", manifest_fields, manifest_counts),
                ("markdown_reports", report_fields, report_counts),
            ]
        )
    )
    dashboard_bundle_paths = _dashboard_bundle_summary_paths(planner)
    timeline_paths = _timeline_summary_paths(planner)
    actions_value = checkpoint.get("actions")
    actions = cast(list[object], actions_value) if isinstance(actions_value, list) else []
    evaluated_actions: list[dict[str, object]] = []
    action_results: list[str] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        item = cast(dict[str, Any], item)
        source = str(item.get("source") or "")
        summary = source_summaries.get(source, {})
        verification_value = item.get("verification")
        verification = (
            cast(list[object], verification_value) if isinstance(verification_value, list) else []
        )
        observed_signals_value = item.get("observed_signals")
        observed_signals = (
            cast(list[object], observed_signals_value)
            if isinstance(observed_signals_value, list)
            else []
        )
        normalized_observed_signals = [
            value for value in observed_signals if isinstance(value, str)
        ]
        latest_exit_code = item.get("latest_exit_code")
        normalized_exit_code = latest_exit_code if isinstance(latest_exit_code, int) else None
        stdout_summary = item.get("latest_stdout_summary")
        normalized_stdout_summary = stdout_summary if isinstance(stdout_summary, str) else None
        stderr_summary = item.get("latest_stderr_summary")
        normalized_stderr_summary = stderr_summary if isinstance(stderr_summary, str) else None
        evaluations = [
            _evaluate_signal_with_observations(
                signal,
                summary,
                normalized_observed_signals,
                normalized_exit_code,
                normalized_stdout_summary,
                normalized_stderr_summary,
                fallback_fields,
                fallback_counts,
                fallback_field_sources,
                fallback_count_sources,
            )
            for signal in verification
            if isinstance(signal, str)
        ]
        result = _action_result(evaluations)
        action_results.append(result)
        evaluated_actions.append(
            {**item, "evaluation_result": result, "signal_evaluations": evaluations}
        )

    auto_pass_count = sum(
        1 for item in evaluated_actions if item.get("evaluation_result") == "pass"
    )
    auto_fail_count = sum(
        1 for item in evaluated_actions if item.get("evaluation_result") == "fail"
    )
    manual_review_count = sum(
        1 for item in evaluated_actions if item.get("evaluation_result") == "manual_review"
    )
    partial_count = sum(
        1 for item in evaluated_actions if item.get("evaluation_result") == "partial"
    )
    evaluator_status = _evaluator_status(action_results)
    next_action_key = next(
        (
            item.get("action_key")
            for item in evaluated_actions
            if item.get("evaluation_result") in {"fail", "manual_review", "partial"}
        ),
        None,
    )
    summary = {
        "evaluator_status": evaluator_status,
        "planned_action_count": len(evaluated_actions),
        "auto_pass_count": auto_pass_count,
        "auto_fail_count": auto_fail_count,
        "manual_review_count": manual_review_count,
        "partial_count": partial_count,
        "next_action_key": next_action_key,
        "fallback_field_sources": fallback_field_sources,
        "fallback_count_sources": fallback_count_sources,
        "operation_chain_path": planner.get("operation_chain_path"),
        "operations_dashboard_summary_path": str(dashboard_bundle_paths["operations_dashboard"])
        if dashboard_bundle_paths["operations_dashboard"] is not None
        else None,
        "live_evidence_summary_path": str(live_evidence_paths["live_evidence_summary"])
        if live_evidence_paths["live_evidence_summary"] is not None
        else None,
        "live_evidence_report_path": str(live_evidence_paths["live_evidence_report"])
        if live_evidence_paths["live_evidence_report"] is not None
        else None,
        "current_state_index_summary_path": str(
            current_state_index_paths["current_state_index_summary"]
        )
        if current_state_index_paths["current_state_index_summary"] is not None
        else None,
        "current_state_index_report_path": str(
            current_state_index_paths["current_state_index_report"]
        )
        if current_state_index_paths["current_state_index_report"] is not None
        else None,
        "ops_review_summary_path": str(ops_review_paths["ops_review_summary"])
        if ops_review_paths["ops_review_summary"] is not None
        else None,
        "ops_review_report_path": str(ops_review_paths["ops_review_report"])
        if ops_review_paths["ops_review_report"] is not None
        else None,
        "audit_dashboard_summary_path": str(dashboard_bundle_paths["audit_dashboard"])
        if dashboard_bundle_paths["audit_dashboard"] is not None
        else None,
        "operations_bundle_manifest_path": str(dashboard_bundle_paths["operations_bundle"])
        if dashboard_bundle_paths["operations_bundle"] is not None
        else None,
        "operations_audit_pack_path": str(dashboard_bundle_paths["operations_audit_pack"])
        if dashboard_bundle_paths["operations_audit_pack"] is not None
        else None,
        "audit_bundle_manifest_path": str(dashboard_bundle_paths["audit_bundle"])
        if dashboard_bundle_paths["audit_bundle"] is not None
        else None,
        "operations_timeline_summary_path": str(timeline_paths["operations_timeline"])
        if timeline_paths["operations_timeline"] is not None
        else None,
        "audit_timeline_summary_path": str(timeline_paths["audit_timeline"])
        if timeline_paths["audit_timeline"] is not None
        else None,
        "phase_gate_review_report_path": str(report_paths["phase_gate_review"])
        if report_paths["phase_gate_review"] is not None
        else None,
        "paper_operations_runbook_report_path": str(report_paths["paper_operations_runbook"])
        if report_paths["paper_operations_runbook"] is not None
        else None,
        "remediation_session_checkpoint_summary_path": (
            str(remediation_session_checkpoint_summary_path)
            if remediation_session_checkpoint_summary_path is not None
            else None
        ),
        "actions": evaluated_actions,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
        "remediation_evaluator_report_path": str(out_path) if out_path is not None else None,
    }
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)

    lines = ["# Remediation Evaluator", ""]
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
            "## Evaluator Summary",
            "",
            f"- evaluator_status: {summary['evaluator_status']}",
            f"- planned_action_count: {summary['planned_action_count']}",
            f"- auto_pass_count: {summary['auto_pass_count']}",
            f"- auto_fail_count: {summary['auto_fail_count']}",
            f"- manual_review_count: {summary['manual_review_count']}",
            f"- partial_count: {summary['partial_count']}",
            f"- next_action_key: {summary['next_action_key']}",
            f"- fallback_field_source_count: {len(fallback_field_sources)}",
            f"- fallback_count_source_count: {len(fallback_count_sources)}",
            f"- operation_chain_path: {summary['operation_chain_path']}",
            f"- operations_dashboard_summary_path: {summary['operations_dashboard_summary_path']}",
            f"- live_evidence_summary_path: {summary['live_evidence_summary_path']}",
            f"- live_evidence_report_path: {summary['live_evidence_report_path']}",
            f"- current_state_index_summary_path: {summary['current_state_index_summary_path']}",
            f"- current_state_index_report_path: {summary['current_state_index_report_path']}",
            f"- ops_review_summary_path: {summary['ops_review_summary_path']}",
            f"- ops_review_report_path: {summary['ops_review_report_path']}",
            f"- audit_dashboard_summary_path: {summary['audit_dashboard_summary_path']}",
            f"- operations_bundle_manifest_path: {summary['operations_bundle_manifest_path']}",
            f"- operations_audit_pack_path: {summary['operations_audit_pack_path']}",
            f"- audit_bundle_manifest_path: {summary['audit_bundle_manifest_path']}",
            f"- operations_timeline_summary_path: {summary['operations_timeline_summary_path']}",
            f"- audit_timeline_summary_path: {summary['audit_timeline_summary_path']}",
            f"- phase_gate_review_report_path: {summary['phase_gate_review_report_path']}",
            f"- paper_operations_runbook_report_path: {summary['paper_operations_runbook_report_path']}",
            f"- remediation_session_checkpoint_summary_path: {summary['remediation_session_checkpoint_summary_path']}",
            "",
            "## Fallback Field Sources",
            "",
        ]
    )
    if fallback_field_sources:
        for key in sorted(fallback_field_sources):
            lines.append(f"- {key}: {fallback_field_sources[key]}")
    else:
        lines.append("- fallback_field_sources: none")
    lines.extend(
        [
            "",
            "## Fallback Count Sources",
            "",
        ]
    )
    if fallback_count_sources:
        for key in sorted(fallback_count_sources):
            lines.append(f"- {key}: {fallback_count_sources[key]}")
    else:
        lines.append("- fallback_count_sources: none")
    lines.extend(
        [
            "",
            "## Action Evaluations",
            "",
        ]
    )
    if evaluated_actions:
        for item in evaluated_actions:
            lines.append(f"- {item['action_key']}: `{item['command']}`")
            lines.append(f"  - evaluation_result: {item['evaluation_result']}")
            lines.append("  - signal_evaluations:")
            signal_evaluations = (
                cast(list[object], item["signal_evaluations"])
                if isinstance(item.get("signal_evaluations"), list)
                else []
            )
            for signal in signal_evaluations:
                if not isinstance(signal, dict):
                    continue
                signal = cast(dict[str, Any], signal)
                lines.append(
                    "    - signal={signal} status={status} expected={expected} observed={observed} observed_source={observed_source}".format(
                        signal=signal.get("signal"),
                        status=signal.get("status"),
                        expected=signal.get("expected"),
                        observed=signal.get("observed"),
                        observed_source=signal.get("observed_source"),
                    )
                )
    else:
        lines.append("- action_evaluations: none")

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
