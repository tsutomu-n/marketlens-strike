from __future__ import annotations

from sis.reports import remediation_evaluator_paths as _evaluator_paths
from sis.reports import remediation_signal_evaluator as _signal_evaluator

_coerce_value = _signal_evaluator.coerce_value


def markdown_report_observations(
    planner: dict, source_summaries: dict[str, dict]
) -> tuple[dict[str, object], dict[str, int]]:
    from sis.reports.remediation_evaluator_observations import (
        apply_aliases,
        live_evidence_paths,
    )

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
