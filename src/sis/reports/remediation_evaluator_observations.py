from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.reports.remediation_evaluator_observation_fields import (
    collect_mapped_observations,
)
from sis.reports import remediation_evaluator_observation_core as _observation_core
from sis.reports import remediation_evaluator_paths as _evaluator_paths
from sis.reports.remediation_evaluator_report_observations import (
    markdown_report_observations,
)
from sis.reports import remediation_signal_evaluator as _signal_evaluator
from sis.storage.jsonl_store import read_jsonl

_coerce_value = _signal_evaluator.coerce_value
_issue_preview_values = _signal_evaluator.issue_preview_values
apply_aliases = _observation_core.apply_aliases
merge_observation_sources = _observation_core.merge_observation_sources

__all__ = [
    "apply_aliases",
    "current_state_index_observations",
    "dashboard_bundle_summary_observations",
    "live_evidence_paths",
    "live_evidence_summary_observations",
    "manifest_note_observations",
    "markdown_report_observations",
    "merge_observation_sources",
    "ops_review_observations",
    "timeline_summary_observations",
]


def live_evidence_paths(planner: dict) -> dict[str, Path | None]:
    current_state_summary = safe_read_json_dict(
        _evaluator_paths.current_state_index_paths(planner)["current_state_index_summary"]
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
        if (
            live_evidence_summary_path.is_absolute()
            and len(live_evidence_summary_path.parents) >= 4
        ):
            report_root = live_evidence_summary_path.parents[3]
            report_path = (
                report_root / "docs/live_evidence_reports" / f"live_evidence_report_{stem}.md"
            )
        else:
            report_path = Path("docs/live_evidence_reports") / f"live_evidence_report_{stem}.md"
    return {
        "live_evidence_summary": live_evidence_summary_path,
        "live_evidence_report": report_path,
    }


def dashboard_bundle_summary_observations(
    planner: dict,
) -> tuple[dict[str, object], dict[str, int]]:
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
        "phase_gate_strict_validation_issue_count": ("phase_gate_strict_validation_issue_count"),
        "phase_gate_review_report_path": "phase_gate_review_report_path",
        "phase_gate_strict_validation_issues": "phase_gate_strict_validation_issues",
    }
    for path in _evaluator_paths.dashboard_bundle_summary_paths(planner).values():
        summary = safe_read_json_dict(path)
        observed_fields, observed_counts = collect_mapped_observations(
            summary,
            field_map,
            observed_fields=observed_fields,
            observed_counts=observed_counts,
            issue_preview_source_keys={"phase_gate_strict_validation_issues"},
        )
    return apply_aliases(observed_fields, observed_counts)


def ops_review_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    summary = safe_read_json_dict(_evaluator_paths.ops_review_paths(planner)["ops_review_summary"])
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
    observed_fields, observed_counts = collect_mapped_observations(
        summary,
        field_map,
        observed_fields=observed_fields,
        observed_counts=observed_counts,
    )
    issue_previews = _issue_preview_values(summary.get("phase_gate_strict_validation_issues"))
    if issue_previews:
        observed_fields["phase_gate_issue_previews"] = issue_previews
    return apply_aliases(observed_fields, observed_counts)


def current_state_index_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    summary = safe_read_json_dict(
        _evaluator_paths.current_state_index_paths(planner)["current_state_index_summary"]
    )
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
    observed_fields, observed_counts = collect_mapped_observations(
        summary,
        field_map,
        observed_fields=observed_fields,
        observed_counts=observed_counts,
    )
    issue_previews = _issue_preview_values(summary.get("phase_gate_strict_validation_issues"))
    if issue_previews:
        observed_fields["phase_gate_issue_previews"] = issue_previews
    return apply_aliases(observed_fields, observed_counts)


def live_evidence_summary_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    summary = safe_read_json_dict(live_evidence_paths(planner)["live_evidence_summary"])
    top_level_field_map = {
        "status": "live_evidence_status",
        "decision": "live_evidence_decision",
        "run_id": "live_evidence_run_id",
        "phase2_entry_allowed": "phase2_entry_allowed",
        "phase_gate_reason": "phase_gate_reason",
        "phase_gate_checked_files": "phase_gate_checked_files",
    }
    observed_fields, observed_counts = collect_mapped_observations(
        summary,
        top_level_field_map,
        observed_fields=observed_fields,
        observed_counts=observed_counts,
    )
    blockers = summary.get("blockers")
    if isinstance(blockers, list) and blockers:
        observed_fields["blockers"] = [str(item) for item in blockers]
    next_actions = summary.get("next_actions")
    if isinstance(next_actions, list) and next_actions:
        observed_fields["next_actions"] = [str(item) for item in next_actions]
    phase_gate_summary = summary.get("phase_gate_summary")
    if isinstance(phase_gate_summary, dict):
        observed_fields, observed_counts = collect_mapped_observations(
            phase_gate_summary,
            {
                "decision": "phase_gate_decision",
                "phase2_entry_allowed": "phase2_entry_allowed",
                "phase_gate_reason": "phase_gate_reason",
                "strict_validation_passed": "phase_gate_strict_validation_passed",
                "strict_validation_issue_count": "phase_gate_strict_validation_issue_count",
                "checked_files": "phase_gate_checked_files",
            },
            observed_fields=observed_fields,
            observed_counts=observed_counts,
        )
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
    return apply_aliases(observed_fields, observed_counts)


def timeline_summary_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
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
    for path in _evaluator_paths.timeline_summary_paths(planner).values():
        timeline_summary = safe_read_json_dict(path)
        observed_fields, observed_counts = collect_mapped_observations(
            timeline_summary,
            field_map,
            observed_fields=observed_fields,
            observed_counts=observed_counts,
            issue_preview_source_keys={"latest_phase_gate_issue_previews"},
        )
    return apply_aliases(observed_fields, observed_counts)


def manifest_note_observations(planner: dict) -> tuple[dict[str, object], dict[str, int]]:
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
    return apply_aliases(observed_fields, observed_counts)
