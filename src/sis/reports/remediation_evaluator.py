from __future__ import annotations

import re
from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import read_jsonl, write_json


_IN_SET_RE = re.compile(r"^(?P<field>[A-Za-z0-9_]+)\s+in\s+\{(?P<values>.+)\}$")
_EQ_RE = re.compile(r"^(?P<field>[A-Za-z0-9_]+)\s*==\s*(?P<value>.+)$")
_EMPTY_RE = re.compile(r"^(?P<field>[A-Za-z0-9_ ]+)\s+is\s+empty$")
_NON_NULL_RE = re.compile(r"^(?P<field>[A-Za-z0-9_ ]+)\s+are\s+non-null$")
_EXIT_CODE_RE = re.compile(r"^(?P<label>.+)\s+exits\s+(?P<code>-?\d+)$")
_REPORTS_ISSUES_RE = re.compile(r"^(?P<label>.+)\s+reports\s+issues=(?P<issues>-?\d+)$")
_REPORTS_CURRENT_ISSUE_COUNT_RE = re.compile(r"^(?P<label>.+)\s+reports\s+the current issue count$")
_REPORTS_CHECKED_FILES_GTE_RE = re.compile(
    r"^(?P<label>.+)\s+reports\s+checked_files\s+>=\s+(?P<count>\d+)$"
)
_INCLUDES_CHECKED_FILES_RE = re.compile(r"^(?P<label>.+)\s+includes\s+checked_files$")
_KV_INT_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>-?\d+)")
_KV_ANY_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>[A-Za-z0-9_.-]+)")
_PRINTS_FIELD_RE = re.compile(r"^(?P<label>.+)\s+prints\s+(?P<field>[A-Za-z0-9_]+)$")
_PRINTS_PER_SYMBOL_ROWS_RE = re.compile(r"^(?P<label>.+)\s+prints\s+per-symbol diagnostics rows$")


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evaluator_report": str(out_path),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_session_checkpoint_report": str(reports_dir / "remediation_session_checkpoint.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "remediation_evaluator_report": str(out_path),
        "remediation_planner_report": str(reports_dir / "remediation_planner.md"),
        "remediation_execution_plan_report": str(reports_dir / "remediation_execution_plan.md"),
        "remediation_session_report": str(reports_dir / "remediation_session.md"),
        "remediation_session_checkpoint_report": str(reports_dir / "remediation_session_checkpoint.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
        "remediation_evidence_report": str(reports_dir / "remediation_evidence.md"),
        "remediation_command_results_report": str(reports_dir / "remediation_command_results.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _coerce_value(raw: str) -> object:
    value = raw.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        value = value[1:-1].strip()
    if value == "True":
        return True
    if value == "False":
        return False
    if value == "None":
        return None
    try:
        return int(value)
    except ValueError:
        return value


def _planner_summary_from_checkpoint(checkpoint: dict) -> dict:
    session_path = checkpoint.get("remediation_session_summary_path")
    session = safe_read_json_dict(Path(session_path) if isinstance(session_path, str) else None)
    execution_plan_path = session.get("remediation_execution_plan_summary_path")
    execution_plan = safe_read_json_dict(
        Path(execution_plan_path) if isinstance(execution_plan_path, str) else None
    )
    planner_summary_path = execution_plan.get("remediation_planner_summary_path")
    return safe_read_json_dict(Path(planner_summary_path) if isinstance(planner_summary_path, str) else None)


def _issue_preview_values(value: object) -> list[str]:
    previews: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                path = item.get("path")
                message = item.get("message")
                if path is not None and message is not None:
                    previews.append(f"{path}: {message}")
                elif path is not None:
                    previews.append(str(path))
                elif message is not None:
                    previews.append(str(message))
            elif isinstance(item, str):
                previews.append(item)
    return previews


def _source_summaries(planner: dict) -> dict[str, dict]:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    return {
        "phase_gate_review": safe_read_json_dict(Path(phase_gate_path) if isinstance(phase_gate_path, str) else None),
        "paper_operations_runbook": safe_read_json_dict(
            Path(runbook_path) if isinstance(runbook_path, str) else None
        ),
    }


def _report_path_from_summary_path(summary_path: Path | None) -> Path | None:
    if summary_path is None:
        return None
    if summary_path.parent.name == "ops" and summary_path.name.endswith("_summary.json"):
        stem = summary_path.name.removesuffix("_summary.json")
        report_name = f"{stem}.md"
        if stem == "ops_review":
            report_name = "ops_review_report.md"
        return summary_path.parent.parent / "reports" / report_name
    return None


def _report_paths(planner: dict, source_summaries: dict[str, dict]) -> dict[str, Path | None]:
    phase_gate_summary_path = planner.get("phase_gate_summary_path")
    runbook_summary_path = planner.get("runbook_summary_path")
    phase_gate_summary = source_summaries.get("phase_gate_review", {})
    runbook_summary = source_summaries.get("paper_operations_runbook", {})
    phase_gate_report_path = phase_gate_summary.get("phase_gate_review_report_path")
    runbook_report_path = runbook_summary.get("paper_operations_runbook_report_path")
    return {
        "phase_gate_review": (
            Path(phase_gate_report_path)
            if isinstance(phase_gate_report_path, str)
            else _report_path_from_summary_path(
                Path(phase_gate_summary_path) if isinstance(phase_gate_summary_path, str) else None
            )
        ),
        "paper_operations_runbook": (
            Path(runbook_report_path)
            if isinstance(runbook_report_path, str)
            else _report_path_from_summary_path(
                Path(runbook_summary_path) if isinstance(runbook_summary_path, str) else None
            )
        ),
    }


def _timeline_summary_paths(planner: dict) -> dict[str, Path | None]:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    bases = [
        Path(raw).parent
        for raw in (phase_gate_path, runbook_path)
        if isinstance(raw, str)
    ]
    base_dir = bases[0] if bases else None
    return {
        "operations_timeline": (base_dir / "operations_timeline_summary.json") if base_dir else None,
        "audit_timeline": (base_dir / "audit_timeline_summary.json") if base_dir else None,
    }


def _dashboard_bundle_summary_paths(planner: dict) -> dict[str, Path | None]:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    bases = [
        Path(raw).parent
        for raw in (phase_gate_path, runbook_path)
        if isinstance(raw, str)
    ]
    base_dir = bases[0] if bases else None
    return {
        "operations_dashboard": (base_dir / "operations_dashboard_summary.json") if base_dir else None,
        "audit_dashboard": (base_dir / "audit_dashboard_summary.json") if base_dir else None,
        "operations_bundle": (base_dir / "operations_bundle_manifest.json") if base_dir else None,
        "operations_audit_pack": (base_dir / "operations_audit_pack.json") if base_dir else None,
        "audit_bundle": (base_dir / "audit_bundle_manifest.json") if base_dir else None,
    }


def _ops_review_paths(planner: dict) -> dict[str, Path | None]:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    bases = [
        Path(raw).parent
        for raw in (phase_gate_path, runbook_path)
        if isinstance(raw, str)
    ]
    base_dir = bases[0] if bases else None
    summary_path = (base_dir / "ops_review_summary.json") if base_dir else None
    return {
        "ops_review_summary": summary_path,
        "ops_review_report": _report_path_from_summary_path(summary_path),
    }


def _current_state_index_paths(planner: dict) -> dict[str, Path | None]:
    phase_gate_path = planner.get("phase_gate_summary_path")
    runbook_path = planner.get("runbook_summary_path")
    bases = [
        Path(raw).parent
        for raw in (phase_gate_path, runbook_path)
        if isinstance(raw, str)
    ]
    base_dir = bases[0] if bases else None
    summary_path = (base_dir / "current_state_index.json") if base_dir else None
    report_path = None
    if base_dir is not None:
        report_path = base_dir.parent / "reports" / "current_state_index.md"
    return {
        "current_state_index_summary": summary_path,
        "current_state_index_report": report_path,
    }


def _live_evidence_paths(planner: dict) -> dict[str, Path | None]:
    current_state_summary = safe_read_json_dict(
        _current_state_index_paths(planner)["current_state_index_summary"]
    )
    artifacts = current_state_summary.get("artifacts")
    live_evidence_summary_path: Path | None = None
    if isinstance(artifacts, dict):
        raw = artifacts.get("live_evidence_summary")
        if isinstance(raw, str) and raw:
            live_evidence_summary_path = Path(raw)
    if live_evidence_summary_path is None:
        return {"live_evidence_summary": None, "live_evidence_report": None}
    report_path: Path | None = None
    if live_evidence_summary_path.name.startswith("live_evidence_summary_"):
        stem = live_evidence_summary_path.name.removesuffix(".json").replace(
            "live_evidence_summary_",
            "",
        )
        if live_evidence_summary_path.is_absolute() and len(live_evidence_summary_path.parents) >= 4:
            report_root = live_evidence_summary_path.parents[3]
            report_path = report_root / "docs/live_evidence_reports" / f"live_evidence_report_{stem}.md"
        else:
            report_path = Path("docs/live_evidence_reports") / f"live_evidence_report_{stem}.md"
    return {
        "live_evidence_summary": live_evidence_summary_path,
        "live_evidence_report": report_path,
    }


def _apply_aliases(
    observed_fields: dict[str, object], observed_counts: dict[str, int]
) -> tuple[dict[str, object], dict[str, int]]:
    alias_map = {
        "phase_gate_checked_files": "checked_files",
        "phase_gate_strict_validation_issue_count": "issues",
        "phase_gate_decision": "decision",
        "phase_gate_reason": "phase2_entry_reason",
    }
    for source_key, target_key in alias_map.items():
        if source_key in observed_fields and target_key not in observed_fields:
            observed_fields[target_key] = observed_fields[source_key]
        if source_key in observed_counts and target_key not in observed_counts:
            observed_counts[target_key] = observed_counts[source_key]
    return observed_fields, observed_counts


def _merge_observation_sources(
    sources: list[tuple[str, dict[str, object], dict[str, int]]]
) -> tuple[dict[str, object], dict[str, int], dict[str, str], dict[str, str]]:
    merged_fields: dict[str, object] = {}
    merged_counts: dict[str, int] = {}
    field_sources: dict[str, str] = {}
    count_sources: dict[str, str] = {}
    for source_name, fields, counts in sources:
        for key, value in fields.items():
            if key in merged_fields:
                continue
            merged_fields[key] = value
            field_sources[key] = source_name
        for key, value in counts.items():
            if key in merged_counts:
                continue
            merged_counts[key] = value
            count_sources[key] = source_name
    return merged_fields, merged_counts, field_sources, count_sources


def _dashboard_bundle_summary_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    field_map = {
        "execution_diagnostics_status": "execution_diagnostics_status",
        "execution_balance_gap_detected": "execution_balance_gap_detected",
        "execution_fills_gap_detected": "execution_fills_gap_detected",
        "execution_drift_overview_status": "execution_drift_overview_status",
        "execution_drift_overview_diagnostics_alignment_match": (
            "execution_drift_overview_diagnostics_alignment_match"
        ),
        "execution_drift_overview_state_comparison_mismatching_count": (
            "execution_drift_overview_state_comparison_mismatching_count"
        ),
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        ),
        "execution_gap_history_latest_status": "execution_gap_history_latest_status",
        "execution_gap_history_latest_diagnostics_status": (
            "execution_gap_history_latest_diagnostics_status"
        ),
        "execution_state_comparison_latest_status_match": (
            "execution_state_comparison_latest_status_match"
        ),
        "execution_state_comparison_mismatching_count": (
            "execution_state_comparison_mismatching_count"
        ),
        "readiness_execution_ready": "readiness_execution_ready",
        "readiness_next_phase_candidate": "readiness_next_phase_candidate",
        "phase2_entry_allowed": "phase2_entry_allowed",
        "phase_gate_phase2_entry_allowed": "phase2_entry_allowed",
        "phase_gate_reason": "phase_gate_reason",
        "phase_gate_decision": "phase_gate_decision",
        "phase_gate_checked_files": "phase_gate_checked_files",
        "phase_gate_strict_validation_passed": "phase_gate_strict_validation_passed",
        "phase_gate_strict_validation_issue_count": (
            "phase_gate_strict_validation_issue_count"
        ),
        "phase_gate_review_report_path": "phase_gate_review_report_path",
        "phase_gate_strict_validation_issues": "phase_gate_strict_validation_issues",
    }
    for path in _dashboard_bundle_summary_paths(planner).values():
        summary = safe_read_json_dict(path)
        for source_key, target_key in field_map.items():
            if target_key in observed_fields or source_key not in summary:
                continue
            value = summary.get(source_key)
            if value is None:
                continue
            if source_key == "phase_gate_strict_validation_issues":
                previews = _issue_preview_values(value)
                if previews:
                    observed_fields["phase_gate_issue_previews"] = previews
                    observed_fields[target_key] = value
                continue
            normalized = value if isinstance(value, (bool, int)) else _coerce_value(str(value))
            observed_fields[target_key] = normalized
            if isinstance(normalized, int):
                observed_counts[target_key] = normalized
    return _apply_aliases(observed_fields, observed_counts)


def _ops_review_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    summary = safe_read_json_dict(_ops_review_paths(planner)["ops_review_summary"])
    field_map = {
        "monitoring_status": "monitoring_status",
        "daemon_dry_run_status": "daemon_dry_run_status",
        "execution_overall_status": "execution_overall_status",
        "execution_venue_count": "execution_venue_count",
        "execution_balance_gap_detected": "execution_balance_gap_detected",
        "execution_fills_gap_detected": "execution_fills_gap_detected",
        "execution_diagnostics_status": "execution_diagnostics_status",
        "execution_drift_overview_status": "execution_drift_overview_status",
        "execution_drift_overview_diagnostics_alignment_match": (
            "execution_drift_overview_diagnostics_alignment_match"
        ),
        "execution_drift_overview_state_comparison_mismatching_count": (
            "execution_drift_overview_state_comparison_mismatching_count"
        ),
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        ),
        "readiness_next_phase_candidate": "readiness_next_phase_candidate",
        "readiness_execution_ready": "readiness_execution_ready",
        "phase_gate_decision": "phase_gate_decision",
        "phase2_entry_allowed": "phase2_entry_allowed",
        "phase_gate_reason": "phase_gate_reason",
        "phase_gate_strict_validation_passed": "phase_gate_strict_validation_passed",
        "phase_gate_strict_validation_issue_count": "phase_gate_strict_validation_issue_count",
        "phase_gate_checked_files": "phase_gate_checked_files",
        "phase_gate_review_report_path": "phase_gate_review_report_path",
    }
    for source_key, target_key in field_map.items():
        if source_key not in summary:
            continue
        value = summary.get(source_key)
        if value is None:
            continue
        normalized = value if isinstance(value, (bool, int)) else _coerce_value(str(value))
        observed_fields[target_key] = normalized
        if isinstance(normalized, int):
            observed_counts[target_key] = normalized
    issue_previews = _issue_preview_values(summary.get("phase_gate_strict_validation_issues"))
    if issue_previews:
        observed_fields["phase_gate_issue_previews"] = issue_previews
    return _apply_aliases(observed_fields, observed_counts)


def _current_state_index_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    summary = safe_read_json_dict(_current_state_index_paths(planner)["current_state_index_summary"])
    field_map = {
        "overall_status": "overall_status",
        "phase_gate_decision": "phase_gate_decision",
        "phase2_entry_allowed": "phase2_entry_allowed",
        "phase_gate_reason": "phase_gate_reason",
        "phase_gate_strict_validation_passed": "phase_gate_strict_validation_passed",
        "phase_gate_strict_validation_issue_count": "phase_gate_strict_validation_issue_count",
        "phase_gate_checked_files": "phase_gate_checked_files",
        "phase_gate_review_report_path": "phase_gate_review_report_path",
        "execution_overall_status": "execution_overall_status",
        "execution_venue_count": "execution_venue_count",
        "execution_comparison_ready": "execution_comparison_all_registries_present",
        "execution_diagnostics_status": "execution_diagnostics_status",
        "execution_balance_gap_detected": "execution_balance_gap_detected",
        "execution_fills_gap_detected": "execution_fills_gap_detected",
        "execution_gap_history_latest_status": "execution_gap_history_latest_status",
        "execution_gap_history_latest_diagnostics_status": (
            "execution_gap_history_latest_diagnostics_status"
        ),
        "execution_state_comparison_latest_status_match": (
            "execution_state_comparison_latest_status_match"
        ),
        "execution_state_comparison_mismatching_count": (
            "execution_state_comparison_mismatching_count"
        ),
        "execution_snapshot_drift_latest_status_match": (
            "execution_snapshot_drift_latest_status_match"
        ),
        "execution_snapshot_drift_mismatching_snapshot_count": (
            "execution_snapshot_drift_mismatching_snapshot_count"
        ),
        "execution_drift_overview_status": "execution_drift_overview_status",
        "execution_drift_overview_diagnostics_alignment_match": (
            "execution_drift_overview_diagnostics_alignment_match"
        ),
        "execution_drift_overview_state_comparison_mismatching_count": (
            "execution_drift_overview_state_comparison_mismatching_count"
        ),
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        ),
        "live_evidence_status": "live_evidence_status",
        "live_evidence_decision": "live_evidence_decision",
        "live_evidence_run_id": "live_evidence_run_id",
    }
    for source_key, target_key in field_map.items():
        if source_key not in summary:
            continue
        value = summary.get(source_key)
        if value is None:
            continue
        normalized = value if isinstance(value, (bool, int)) else _coerce_value(str(value))
        observed_fields[target_key] = normalized
        if isinstance(normalized, int):
            observed_counts[target_key] = normalized
    issue_previews = _issue_preview_values(summary.get("phase_gate_strict_validation_issues"))
    if issue_previews:
        observed_fields["phase_gate_issue_previews"] = issue_previews
    return _apply_aliases(observed_fields, observed_counts)


def _live_evidence_summary_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    summary = safe_read_json_dict(_live_evidence_paths(planner)["live_evidence_summary"])
    top_level_field_map = {
        "status": "live_evidence_status",
        "decision": "live_evidence_decision",
        "run_id": "live_evidence_run_id",
        "phase2_entry_allowed": "phase2_entry_allowed",
        "phase_gate_reason": "phase_gate_reason",
        "phase_gate_checked_files": "phase_gate_checked_files",
    }
    for source_key, target_key in top_level_field_map.items():
        if source_key not in summary:
            continue
        value = summary.get(source_key)
        if value is None:
            continue
        normalized = value if isinstance(value, (bool, int)) else _coerce_value(str(value))
        observed_fields[target_key] = normalized
        if isinstance(normalized, int):
            observed_counts[target_key] = normalized
    blockers = summary.get("blockers")
    if isinstance(blockers, list) and blockers:
        observed_fields["blockers"] = [str(item) for item in blockers]
    next_actions = summary.get("next_actions")
    if isinstance(next_actions, list) and next_actions:
        observed_fields["next_actions"] = [str(item) for item in next_actions]
    phase_gate_summary = summary.get("phase_gate_summary")
    if isinstance(phase_gate_summary, dict):
        for source_key, target_key in {
            "decision": "phase_gate_decision",
            "phase2_entry_allowed": "phase2_entry_allowed",
            "phase_gate_reason": "phase_gate_reason",
            "strict_validation_passed": "phase_gate_strict_validation_passed",
            "strict_validation_issue_count": "phase_gate_strict_validation_issue_count",
            "checked_files": "phase_gate_checked_files",
        }.items():
            if source_key not in phase_gate_summary:
                continue
            value = phase_gate_summary.get(source_key)
            if value is None:
                continue
            normalized = value if isinstance(value, (bool, int)) else _coerce_value(str(value))
            observed_fields[target_key] = normalized
            if isinstance(normalized, int):
                observed_counts[target_key] = normalized
    readiness_summary = summary.get("readiness_summary")
    if isinstance(readiness_summary, dict):
        for source_key, target_key in {
            "next_phase_candidate": "readiness_next_phase_candidate",
            "execution_ready": "readiness_execution_ready",
        }.items():
            if source_key not in readiness_summary:
                continue
            value = readiness_summary.get(source_key)
            if value is None:
                continue
            observed_fields[target_key] = (
                value if isinstance(value, (bool, int)) else _coerce_value(str(value))
            )
    execution_diagnostics = summary.get("execution_diagnostics_summary")
    if isinstance(execution_diagnostics, dict):
        for source_key, target_key in {
            "overall_status": "execution_diagnostics_status",
            "balance_gap_detected": "execution_balance_gap_detected",
            "fills_gap_detected": "execution_fills_gap_detected",
        }.items():
            if source_key not in execution_diagnostics:
                continue
            value = execution_diagnostics.get(source_key)
            if value is None:
                continue
            observed_fields[target_key] = (
                value if isinstance(value, (bool, int)) else _coerce_value(str(value))
            )
    return _apply_aliases(observed_fields, observed_counts)


def _timeline_summary_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    field_map = {
        "latest_execution_diagnostics_status": "execution_diagnostics_status",
        "latest_execution_drift_overview_status": "execution_drift_overview_status",
        "latest_execution_drift_overview_diagnostics_alignment_match": (
            "execution_drift_overview_diagnostics_alignment_match"
        ),
        "latest_execution_drift_overview_state_comparison_mismatching_count": (
            "execution_drift_overview_state_comparison_mismatching_count"
        ),
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
        ),
        "latest_execution_gap_history_status": "execution_gap_history_latest_status",
        "latest_execution_gap_history_diagnostics_status": (
            "execution_gap_history_latest_diagnostics_status"
        ),
        "latest_execution_state_comparison_status_match": (
            "execution_state_comparison_latest_status_match"
        ),
        "latest_execution_state_comparison_mismatching_count": (
            "execution_state_comparison_mismatching_count"
        ),
        "latest_readiness_next_phase": "readiness_next_phase",
        "latest_readiness_execution_ready": "readiness_execution_ready",
        "latest_phase_gate_decision": "phase_gate_decision",
        "latest_phase2_entry_allowed": "phase2_entry_allowed",
        "latest_phase_gate_reason": "phase_gate_reason",
        "latest_phase_gate_strict_validation_passed": "phase_gate_strict_validation_passed",
        "latest_phase_gate_strict_validation_issue_count": (
            "phase_gate_strict_validation_issue_count"
        ),
        "latest_phase_gate_checked_files": "phase_gate_checked_files",
        "latest_phase_gate_review_report_path": "phase_gate_review_report_path",
        "latest_phase_gate_issue_previews": "phase_gate_issue_previews",
    }
    for path in _timeline_summary_paths(planner).values():
        timeline_summary = safe_read_json_dict(path)
        for source_key, target_key in field_map.items():
            if target_key in observed_fields or source_key not in timeline_summary:
                continue
            value = timeline_summary.get(source_key)
            if value is None:
                continue
            if source_key == "latest_phase_gate_issue_previews":
                previews = _issue_preview_values(value)
                if previews:
                    observed_fields[target_key] = previews
                continue
            normalized = _coerce_value(str(value))
            observed_fields[target_key] = normalized
            if isinstance(normalized, int):
                observed_counts[target_key] = normalized
    return _apply_aliases(observed_fields, observed_counts)


def _manifest_note_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    operation_chain_path = planner.get("operation_chain_path")
    path = Path(operation_chain_path) if isinstance(operation_chain_path, str) else None
    if path is None or not path.exists():
        return {}, {}
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    manifests = [item for item in read_jsonl(path) if isinstance(item, dict)]
    for item in reversed(manifests):
        notes = item.get("notes")
        if not isinstance(notes, list):
            continue
        issue_previews = observed_fields.get("phase_gate_issue_previews")
        normalized_issue_previews = issue_previews if isinstance(issue_previews, list) else []
        for note in notes:
            if not isinstance(note, str) or "=" not in note:
                continue
            key, raw_value = note.split("=", 1)
            if key.startswith("phase_gate_issue_"):
                normalized_issue_previews.append(raw_value)
                observed_fields["phase_gate_issue_previews"] = normalized_issue_previews
                continue
            if key in observed_fields:
                continue
            value = _coerce_value(raw_value)
            observed_fields[key] = value
            if isinstance(value, int):
                observed_counts[key] = value
    return _apply_aliases(observed_fields, observed_counts)


def _markdown_report_observations(
    planner: dict, source_summaries: dict[str, dict]
) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    report_paths = _report_paths(planner, source_summaries)
    ops_review_report_path = _ops_review_paths(planner).get("ops_review_report")
    if ops_review_report_path is not None:
        report_paths["ops_review"] = ops_review_report_path
    current_state_index_report_path = _current_state_index_paths(planner).get(
        "current_state_index_report"
    )
    if current_state_index_report_path is not None:
        report_paths["current_state_index"] = current_state_index_report_path
    live_evidence_report_path = _live_evidence_paths(planner).get("live_evidence_report")
    if live_evidence_report_path is not None:
        report_paths["live_evidence_report"] = live_evidence_report_path
    issue_previews: list[str] = []
    next_actions: list[str] = []
    blockers: list[str] = []
    for path in report_paths.values():
        if path is None or not path.exists():
            continue
        current_section = ""
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("## "):
                current_section = line[3:]
                continue
            if current_section == "Strict Validation" and line.startswith("| ") and not line.startswith("| ---"):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                if len(cells) == 2 and cells[0] != "path":
                    issue_previews.append(f"{cells[0]}: {cells[1]}")
                continue
            if not line.startswith("- "):
                continue
            bullet = line[2:]
            if current_section in {"Strict Validation", "Strict Validation Preview"}:
                if bullet == "issues: none":
                    issue_previews = []
                elif not bullet.startswith("missing_required_artifact_paths") and not bullet.startswith(
                    "checked_files: "
                ):
                    issue_previews.append(bullet)
            if current_section == "Next Actions":
                next_actions.append(bullet)
            if current_section == "Blockers":
                blockers.append(bullet)
            if current_section == "Executive Summary" and bullet.startswith("phase2_entry_reason: "):
                reason = bullet.split(": ", 1)[1].strip()
                if reason and reason != "None":
                    blockers.append(reason)
            if ": " not in bullet:
                continue
            key, raw_value = bullet.split(": ", 1)
            if key not in observed_fields:
                value = _coerce_value(raw_value)
                observed_fields[key] = value
                if isinstance(value, int):
                    observed_counts[key] = value
        if issue_previews and "phase_gate_issue_previews" not in observed_fields:
            observed_fields["phase_gate_issue_previews"] = issue_previews
        if next_actions and "next_actions" not in observed_fields:
            observed_fields["next_actions"] = next_actions
        if blockers and "blockers" not in observed_fields:
            observed_fields["blockers"] = blockers
    return _apply_aliases(observed_fields, observed_counts)


def _evaluate_signal(signal: str, summary: dict) -> dict[str, object]:
    stripped = signal.strip()
    match = _EQ_RE.match(stripped)
    if match:
        field = match.group("field")
        expected = _coerce_value(match.group("value"))
        observed = summary.get(field)
        return {
            "signal": signal,
            "status": "pass" if observed == expected else "fail",
            "field": field,
            "expected": expected,
            "observed": observed,
        }
    match = _IN_SET_RE.match(stripped)
    if match:
        field = match.group("field")
        values = [_coerce_value(item) for item in match.group("values").split(",")]
        observed = summary.get(field)
        return {
            "signal": signal,
            "status": "pass" if observed in values else "fail",
            "field": field,
            "expected": values,
            "observed": observed,
        }
    match = _EMPTY_RE.match(stripped)
    if match:
        field = match.group("field").replace(" ", "_")
        observed = summary.get(field)
        return {
            "signal": signal,
            "status": "pass" if observed in ([], {}, None, "") else "fail",
            "field": field,
            "expected": "empty",
            "observed": observed,
        }
    match = _NON_NULL_RE.match(stripped)
    if match:
        field = match.group("field").replace(" ", "_")
        observed = summary.get(field)
        status = "pass" if isinstance(observed, dict) and all(value is not None for value in observed.values()) else "unsupported"
        return {
            "signal": signal,
            "status": status,
            "field": field,
            "expected": "non-null",
            "observed": observed,
        }
    return {
        "signal": signal,
        "status": "unsupported",
        "field": None,
        "expected": None,
        "observed": None,
    }


def _observed_counts(stdout_summary: str | None, stderr_summary: str | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    combined = " ".join(
        value for value in (stdout_summary, stderr_summary) if isinstance(value, str) and value
    )
    for match in _KV_INT_RE.finditer(combined):
        counts[match.group("key")] = int(match.group("value"))
    return counts


def _observed_fields(stdout_summary: str | None, stderr_summary: str | None) -> dict[str, object]:
    fields: dict[str, object] = {}
    combined = " ".join(
        value for value in (stdout_summary, stderr_summary) if isinstance(value, str) and value
    )
    for match in _KV_ANY_RE.finditer(combined):
        fields[match.group("key")] = _coerce_value(match.group("value"))
    return fields


def _diagnostics_row_presence(stdout_summary: str | None, stderr_summary: str | None) -> dict[str, object]:
    combined = " ".join(
        value for value in (stdout_summary, stderr_summary) if isinstance(value, str) and value
    )
    return {
        "venue_present": "venue=" in combined,
        "symbol_present": "symbol=" in combined,
        "rows_present": "rows=" in combined,
        "tradable_rate_present": "tradable_rate=" in combined,
        "stale_rate_present": "stale_rate=" in combined,
    }


def _evaluate_signal_with_observations(
    signal: str,
    summary: dict,
    observed_signals: list[str],
    latest_exit_code: int | None,
    stdout_summary: str | None,
    stderr_summary: str | None,
    manifest_fields: dict[str, object],
    manifest_counts: dict[str, int],
    fallback_field_sources: dict[str, str],
    fallback_count_sources: dict[str, str],
) -> dict[str, object]:
    if signal in observed_signals:
        return {
            "signal": signal,
            "status": "pass",
            "field": None,
            "expected": "manually_observed",
            "observed": signal,
            "observed_source": "observed_signals",
        }
    match = _EXIT_CODE_RE.match(signal.strip())
    if match and latest_exit_code is not None:
        expected_code = int(match.group("code"))
        return {
            "signal": signal,
            "status": "pass" if latest_exit_code == expected_code else "fail",
            "field": "exit_code",
            "expected": expected_code,
            "observed": latest_exit_code,
            "observed_source": "exit_code",
        }
    observed_counts = {**manifest_counts, **_observed_counts(stdout_summary, stderr_summary)}
    match = _REPORTS_ISSUES_RE.match(signal.strip())
    if match:
        expected_issues = int(match.group("issues"))
        observed_issues = observed_counts.get("issues")
        observed_source = "stdout_stderr" if "issues" in _observed_counts(stdout_summary, stderr_summary) else fallback_count_sources.get("issues")
        return {
            "signal": signal,
            "status": "pass" if observed_issues == expected_issues else "fail",
            "field": "issues",
            "expected": expected_issues,
            "observed": observed_issues,
            "observed_source": observed_source,
        }
    if _REPORTS_CURRENT_ISSUE_COUNT_RE.match(signal.strip()):
        observed_issues = observed_counts.get("issues")
        observed_source = "stdout_stderr" if "issues" in _observed_counts(stdout_summary, stderr_summary) else fallback_count_sources.get("issues")
        return {
            "signal": signal,
            "status": "pass" if observed_issues is not None else "fail",
            "field": "issues",
            "expected": "present",
            "observed": observed_issues,
            "observed_source": observed_source,
        }
    match = _REPORTS_CHECKED_FILES_GTE_RE.match(signal.strip())
    if match:
        minimum = int(match.group("count"))
        observed_checked_files = observed_counts.get("checked_files")
        observed_source = (
            "stdout_stderr"
            if "checked_files" in _observed_counts(stdout_summary, stderr_summary)
            else fallback_count_sources.get("checked_files")
        )
        return {
            "signal": signal,
            "status": (
                "pass"
                if observed_checked_files is not None and observed_checked_files >= minimum
                else "fail"
            ),
            "field": "checked_files",
            "expected": f">={minimum}",
            "observed": observed_checked_files,
            "observed_source": observed_source,
        }
    if _INCLUDES_CHECKED_FILES_RE.match(signal.strip()):
        observed_checked_files = observed_counts.get("checked_files")
        observed_source = (
            "stdout_stderr"
            if "checked_files" in _observed_counts(stdout_summary, stderr_summary)
            else fallback_count_sources.get("checked_files")
        )
        return {
            "signal": signal,
            "status": "pass" if observed_checked_files is not None else "fail",
            "field": "checked_files",
            "expected": "present",
            "observed": observed_checked_files,
            "observed_source": observed_source,
        }
    stdout_stderr_fields = _observed_fields(stdout_summary, stderr_summary)
    observed_fields = {**manifest_fields, **stdout_stderr_fields}
    diagnostics_presence = _diagnostics_row_presence(stdout_summary, stderr_summary)
    match = _PRINTS_FIELD_RE.match(signal.strip())
    if match:
        field = match.group("field")
        observed_value = observed_fields.get(field)
        return {
            "signal": signal,
            "status": "pass" if field in observed_fields else "fail",
            "field": field,
            "expected": "present",
            "observed": observed_value,
            "observed_source": (
                "stdout_stderr"
                if field in stdout_stderr_fields
                else fallback_field_sources.get(field)
            ),
        }
    if _PRINTS_PER_SYMBOL_ROWS_RE.match(signal.strip()):
        return {
            "signal": signal,
            "status": (
                "pass"
                if diagnostics_presence["venue_present"]
                and diagnostics_presence["symbol_present"]
                and diagnostics_presence["rows_present"]
                else "fail"
            ),
            "field": "venue,symbol,rows",
            "expected": "present",
            "observed": diagnostics_presence,
            "observed_source": "stdout_stderr",
        }
    normalized_signal = signal.strip()
    if normalized_signal == "required symbols show quote diagnostics coverage":
        return {
            "signal": signal,
            "status": (
                "pass"
                if diagnostics_presence["tradable_rate_present"]
                and diagnostics_presence["stale_rate_present"]
                else "fail"
            ),
            "field": "tradable_rate,stale_rate",
            "expected": "present",
            "observed": diagnostics_presence,
            "observed_source": "stdout_stderr",
        }
    if normalized_signal == "strict validation preview lists current issues":
        issue_previews = _issue_preview_values(summary.get("phase_gate_strict_validation_issues"))
        fallback_previews = observed_fields.get("phase_gate_issue_previews")
        if not issue_previews and isinstance(fallback_previews, list):
            issue_previews = [str(item) for item in fallback_previews if isinstance(item, str)]
        return {
            "signal": signal,
            "status": "pass" if issue_previews else "fail",
            "field": "phase_gate_issue_previews",
            "expected": "non-empty",
            "observed": issue_previews,
            "observed_source": fallback_field_sources.get("phase_gate_issue_previews"),
        }
    if normalized_signal == "phase gate summary lists blockers":
        blockers = summary.get("blockers")
        normalized_blockers = blockers if isinstance(blockers, list) else []
        if not normalized_blockers:
            fallback_blockers = observed_fields.get("blockers")
            if isinstance(fallback_blockers, list):
                normalized_blockers = [str(item) for item in fallback_blockers]
        return {
            "signal": signal,
            "status": "pass" if normalized_blockers else "fail",
            "field": "blockers",
            "expected": "non-empty",
            "observed": normalized_blockers,
            "observed_source": fallback_field_sources.get("blockers"),
        }
    if normalized_signal == "phase gate summary lists next actions":
        next_actions = summary.get("next_actions")
        normalized_next_actions = next_actions if isinstance(next_actions, list) else []
        if not normalized_next_actions:
            fallback_next_actions = observed_fields.get("next_actions")
            if isinstance(fallback_next_actions, list):
                normalized_next_actions = [str(item) for item in fallback_next_actions]
        return {
            "signal": signal,
            "status": "pass" if normalized_next_actions else "fail",
            "field": "next_actions",
            "expected": "non-empty",
            "observed": normalized_next_actions,
            "observed_source": fallback_field_sources.get("next_actions"),
        }
    if normalized_signal == "monitoring output shows current balance/fills gap flags":
        balance = observed_fields.get("execution_balance_gap_detected")
        fills = observed_fields.get("execution_fills_gap_detected")
        return {
            "signal": signal,
            "status": "pass" if "execution_balance_gap_detected" in observed_fields and "execution_fills_gap_detected" in observed_fields else "fail",
            "field": "execution_balance_gap_detected,execution_fills_gap_detected",
            "expected": "present",
            "observed": {
                "execution_balance_gap_detected": balance,
                "execution_fills_gap_detected": fills,
            },
            "observed_source": {
                "execution_balance_gap_detected": fallback_field_sources.get(
                    "execution_balance_gap_detected"
                ),
                "execution_fills_gap_detected": fallback_field_sources.get(
                    "execution_fills_gap_detected"
                ),
            },
        }
    if normalized_signal == "monitoring output shows current mismatch counts":
        state_count = observed_fields.get("execution_drift_overview_state_comparison_mismatching_count")
        snapshot_count = observed_fields.get("execution_drift_overview_snapshot_drift_mismatching_snapshot_count")
        return {
            "signal": signal,
            "status": (
                "pass"
                if "execution_drift_overview_state_comparison_mismatching_count" in observed_fields
                and "execution_drift_overview_snapshot_drift_mismatching_snapshot_count" in observed_fields
                else "fail"
            ),
            "field": (
                "execution_drift_overview_state_comparison_mismatching_count,"
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
            ),
            "expected": "present",
            "observed": {
                "execution_drift_overview_state_comparison_mismatching_count": state_count,
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": snapshot_count,
            },
            "observed_source": {
                "execution_drift_overview_state_comparison_mismatching_count": fallback_field_sources.get(
                    "execution_drift_overview_state_comparison_mismatching_count"
                ),
                "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": fallback_field_sources.get(
                    "execution_drift_overview_snapshot_drift_mismatching_snapshot_count"
                ),
            },
        }
    if normalized_signal == "phase gate output shows current readiness blockers":
        reason = observed_fields.get("phase_gate_reason")
        decision = observed_fields.get("phase_gate_decision")
        return {
            "signal": signal,
            "status": "pass" if "phase_gate_reason" in observed_fields or "phase_gate_decision" in observed_fields else "fail",
            "field": "phase_gate_reason,phase_gate_decision",
            "expected": "present",
            "observed": {
                "phase_gate_reason": reason,
                "phase_gate_decision": decision,
            },
            "observed_source": {
                "phase_gate_reason": fallback_field_sources.get("phase_gate_reason"),
                "phase_gate_decision": fallback_field_sources.get("phase_gate_decision"),
            },
        }
    if normalized_signal == "check-go-no-go prints the current decision and blockers":
        decision = observed_fields.get("phase_gate_decision") or observed_fields.get("decision")
        reason = observed_fields.get("phase_gate_reason") or observed_fields.get("phase2_entry_reason")
        blockers = observed_fields.get("blockers") or observed_fields.get("blocker_count")
        return {
            "signal": signal,
            "status": "pass" if decision is not None and (reason is not None or blockers is not None) else "fail",
            "field": "decision,reason,blockers",
            "expected": "present",
            "observed": {"decision": decision, "reason": reason, "blockers": blockers},
            "observed_source": {
                "decision": fallback_field_sources.get("phase_gate_decision")
                or fallback_field_sources.get("decision"),
                "reason": fallback_field_sources.get("phase_gate_reason")
                or fallback_field_sources.get("phase2_entry_reason"),
                "blockers": fallback_field_sources.get("blockers")
                or fallback_field_sources.get("blocker_count"),
            },
        }
    if normalized_signal == "current gate decision is visible before regeneration":
        decision = observed_fields.get("phase_gate_decision") or observed_fields.get("decision")
        return {
            "signal": signal,
            "status": "pass" if decision is not None else "fail",
            "field": "decision",
            "expected": "present",
            "observed": decision,
            "observed_source": fallback_field_sources.get("phase_gate_decision")
            or fallback_field_sources.get("decision"),
        }
    result = _evaluate_signal(signal, summary)
    field = result.get("field")
    if isinstance(field, str):
        result["observed_source"] = fallback_field_sources.get(field) or fallback_count_sources.get(field)
    return result


def _action_result(evaluations: list[dict[str, object]]) -> str:
    statuses = [str(item.get("status")) for item in evaluations]
    if not evaluations:
        return "manual_review"
    if any(status == "fail" for status in statuses):
        return "fail"
    if all(status == "pass" for status in statuses):
        return "pass"
    if any(status == "pass" for status in statuses):
        return "partial"
    return "manual_review"


def _evaluator_status(action_results: list[str]) -> str:
    if not action_results:
        return "no_actions"
    if any(result == "fail" for result in action_results):
        return "needs_retry"
    if all(result == "pass" for result in action_results):
        return "auto_passed"
    if any(result == "partial" for result in action_results):
        return "partial"
    return "manual_review"


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
    actions = checkpoint.get("actions") if isinstance(checkpoint.get("actions"), list) else []
    evaluated_actions: list[dict[str, object]] = []
    action_results: list[str] = []
    for item in actions:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "")
        summary = source_summaries.get(source, {})
        verification = item.get("verification") if isinstance(item.get("verification"), list) else []
        observed_signals = (
            item.get("observed_signals") if isinstance(item.get("observed_signals"), list) else []
        )
        normalized_observed_signals = [value for value in observed_signals if isinstance(value, str)]
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
        evaluated_actions.append({**item, "evaluation_result": result, "signal_evaluations": evaluations})

    auto_pass_count = sum(1 for item in evaluated_actions if item.get("evaluation_result") == "pass")
    auto_fail_count = sum(1 for item in evaluated_actions if item.get("evaluation_result") == "fail")
    manual_review_count = sum(1 for item in evaluated_actions if item.get("evaluation_result") == "manual_review")
    partial_count = sum(1 for item in evaluated_actions if item.get("evaluation_result") == "partial")
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
        "current_state_index_summary_path": str(current_state_index_paths["current_state_index_summary"])
        if current_state_index_paths["current_state_index_summary"] is not None
        else None,
        "current_state_index_report_path": str(current_state_index_paths["current_state_index_report"])
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

    lines = ["# Remediation Evaluator", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend([
        "## Evaluator Summary",
        "",
        f"- evaluator_status: {summary['evaluator_status']}",
        f"- planned_action_count: {summary['planned_action_count']}",
        f"- auto_pass_count: {summary['auto_pass_count']}",
        f"- auto_fail_count: {summary['auto_fail_count']}",
        f"- manual_review_count: {summary['manual_review_count']}",
        f"- partial_count: {summary['partial_count']}",
        f"- next_action_key: {summary['next_action_key']}",
        f"- fallback_field_source_count: {len(summary['fallback_field_sources'])}",
        f"- fallback_count_source_count: {len(summary['fallback_count_sources'])}",
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
    ])
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
            for signal in item["signal_evaluations"]:
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
