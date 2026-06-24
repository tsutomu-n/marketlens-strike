from __future__ import annotations

from pathlib import Path

from sis.reports.loaders import safe_read_json_dict
from sis.reports import remediation_evaluator_paths as _evaluator_paths
from sis.reports import remediation_signal_evaluator as _signal_evaluator
from sis.storage.jsonl_store import read_jsonl

_coerce_value = _signal_evaluator.coerce_value
_issue_preview_values = _signal_evaluator.issue_preview_values


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


def apply_aliases(
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


def merge_observation_sources(
    sources: list[tuple[str, dict[str, object], dict[str, int]]],
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


def markdown_report_observations(
    planner: dict, source_summaries: dict[str, dict]
) -> tuple[dict[str, object], dict[str, int]]:
    observed_fields: dict[str, object] = {}
    observed_counts: dict[str, int] = {}
    report_paths = _evaluator_paths.report_paths(planner, source_summaries)
    ops_review_report_path = _evaluator_paths.ops_review_paths(planner).get("ops_review_report")
    if ops_review_report_path is not None:
        report_paths["ops_review"] = ops_review_report_path
    current_state_index_report_path = _evaluator_paths.current_state_index_paths(planner).get(
        "current_state_index_report"
    )
    if current_state_index_report_path is not None:
        report_paths["current_state_index"] = current_state_index_report_path
    live_evidence_report_path = live_evidence_paths(planner).get("live_evidence_report")
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
            if (
                current_section == "Strict Validation"
                and line.startswith("| ")
                and not line.startswith("| ---")
            ):
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
                elif not bullet.startswith(
                    "missing_required_artifact_paths"
                ) and not bullet.startswith("checked_files: "):
                    issue_previews.append(bullet)
            if current_section == "Next Actions":
                next_actions.append(bullet)
            if current_section == "Blockers":
                blockers.append(bullet)
            if current_section == "Executive Summary" and bullet.startswith(
                "phase2_entry_reason: "
            ):
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
    return apply_aliases(observed_fields, observed_counts)
