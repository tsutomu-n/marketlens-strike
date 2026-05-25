from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    latest_execution_lineage_from_notes,
    phase_gate_issue_note_previews,
)
from sis.storage.jsonl_store import read_jsonl, write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "paper_cycle_history_report": str(out_path),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
    }


def _related_reports(out_path: Path | None, latest_phase_gate_review_report_path: str | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    related = {
        "paper_cycle_history_report": str(out_path),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(reports_dir / "execution_state_comparison_history.md"),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": latest_phase_gate_review_report_path or str(reports_dir / "phase_gate_review.md"),
    }
    return related


def _note_value(notes: list[object], prefix: str) -> str | None:
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            return text.removeprefix(prefix)
    return None


def _note_counts(items: list[dict[str, object]], prefix: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        notes = item.get("notes", [])
        if not isinstance(notes, list):
            continue
        value = _note_value(notes, prefix)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _note_values(notes: list[object], prefix: str) -> list[str]:
    values: list[str] = []
    for item in notes:
        text = str(item)
        if text.startswith(prefix):
            values.append(text.removeprefix(prefix))
    return values


def build_paper_cycle_history_report(
    *,
    operation_chain_path: Path | None = None,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    operations = list(read_jsonl(operation_chain_path)) if operation_chain_path and operation_chain_path.exists() else []
    cycles = [item for item in operations if str(item.get("operation")) == "paper_operations_cycle"]

    completed_count = sum(1 for item in cycles if str(item.get("status")) == "completed")
    latest = cycles[-1] if cycles else {}
    latest_notes = latest.get("notes", []) if isinstance(latest, dict) else []
    latest_execution_diagnostics_status = (
        _note_value(latest_notes, "execution_diagnostics_status=") if isinstance(latest_notes, list) else None
    )
    latest_execution_drift_overview_status = (
        _note_value(latest_notes, "execution_drift_overview_status=") if isinstance(latest_notes, list) else None
    )
    latest_execution_drift_overview_diagnostics_alignment_match = (
        _note_value(latest_notes, "execution_drift_overview_diagnostics_alignment_match=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_execution_drift_overview_state_comparison_mismatching_count = (
        _note_value(latest_notes, "execution_drift_overview_state_comparison_mismatching_count=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count = (
        _note_value(
            latest_notes,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=",
        )
        if isinstance(latest_notes, list)
        else None
    )
    latest_readiness_next_phase = (
        _note_value(latest_notes, "readiness_next_phase=") if isinstance(latest_notes, list) else None
    )
    latest_readiness_execution_ready = (
        _note_value(latest_notes, "readiness_execution_ready=") if isinstance(latest_notes, list) else None
    )
    latest_phase_gate_decision = (
        _note_value(latest_notes, "phase_gate_decision=") if isinstance(latest_notes, list) else None
    )
    latest_phase2_entry_allowed = (
        _note_value(latest_notes, "phase2_entry_allowed=") if isinstance(latest_notes, list) else None
    )
    latest_phase_gate_reason = (
        _note_value(latest_notes, "phase_gate_reason=") if isinstance(latest_notes, list) else None
    )
    latest_phase_gate_strict_validation_passed = (
        _note_value(latest_notes, "phase_gate_strict_validation_passed=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_phase_gate_strict_validation_issue_count = (
        _note_value(latest_notes, "phase_gate_strict_validation_issue_count=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_phase_gate_checked_files = (
        _note_value(latest_notes, "phase_gate_checked_files=") if isinstance(latest_notes, list) else None
    )
    latest_phase_gate_review_report_path = (
        _note_value(latest_notes, "phase_gate_review_report_path=")
        if isinstance(latest_notes, list)
        else None
    )
    latest_phase_gate_issue_previews = (
        phase_gate_issue_note_previews(latest_notes) if isinstance(latest_notes, list) else []
    )

    total_orders = 0
    total_fills = 0
    for item in cycles:
        notes = item.get("notes", [])
        if isinstance(notes, list):
            orders = _note_value(notes, "orders=")
            fills = _note_value(notes, "fills=")
            total_orders += int(orders) if orders is not None else 0
            total_fills += int(fills) if fills is not None else 0

    diagnostics_status_counts = _note_counts(cycles, "execution_diagnostics_status=")
    drift_overview_status_counts = _note_counts(cycles, "execution_drift_overview_status=")
    drift_overview_diagnostics_alignment_counts = _note_counts(
        cycles, "execution_drift_overview_diagnostics_alignment_match="
    )
    drift_overview_state_comparison_mismatching_count_values = _note_counts(
        cycles, "execution_drift_overview_state_comparison_mismatching_count="
    )
    drift_overview_snapshot_drift_mismatching_snapshot_count_values = _note_counts(
        cycles, "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
    )
    readiness_next_phase_counts = _note_counts(cycles, "readiness_next_phase=")
    phase_gate_decision_counts = _note_counts(cycles, "phase_gate_decision=")
    phase2_entry_allowed_counts = _note_counts(cycles, "phase2_entry_allowed=")
    phase_gate_reason_counts = _note_counts(cycles, "phase_gate_reason=")
    phase_gate_strict_validation_passed_counts = _note_counts(
        cycles, "phase_gate_strict_validation_passed="
    )
    phase_gate_strict_validation_issue_count_values = _note_counts(
        cycles, "phase_gate_strict_validation_issue_count="
    )
    phase_gate_checked_files_values = _note_counts(cycles, "phase_gate_checked_files=")

    latest_execution_lineage = latest_execution_lineage_from_notes(latest_notes)

    summary = {
        "cycle_count": len(cycles),
        "completed_count": completed_count,
        "latest_status": latest.get("status"),
        "latest_run_id": latest.get("run_id"),
        "latest_created_at": latest.get("created_at"),
        "total_orders": total_orders,
        "total_fills": total_fills,
        **latest_execution_lineage,
        "latest_execution_diagnostics_summary": {
            "execution_diagnostics_status": latest_execution_diagnostics_status,
        },
        "latest_execution_drift_overview_summary": {
            "execution_drift_overview_status": latest_execution_drift_overview_status,
            "execution_drift_overview_diagnostics_alignment_match": (
                latest_execution_drift_overview_diagnostics_alignment_match
            ),
            "execution_drift_overview_state_comparison_mismatching_count": (
                latest_execution_drift_overview_state_comparison_mismatching_count
            ),
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
                latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count
            ),
        },
        "latest_readiness_summary": {
            "readiness_next_phase_candidate": latest_readiness_next_phase,
            "readiness_execution_ready": latest_readiness_execution_ready,
        },
        "latest_phase_gate_summary": {
            "phase_gate_decision": latest_phase_gate_decision,
            "phase2_entry_allowed": latest_phase2_entry_allowed,
            "phase_gate_reason": latest_phase_gate_reason,
            "phase_gate_strict_validation_passed": latest_phase_gate_strict_validation_passed,
            "phase_gate_strict_validation_issue_count": latest_phase_gate_strict_validation_issue_count,
            "phase_gate_checked_files": latest_phase_gate_checked_files,
            "phase_gate_review_report_path": latest_phase_gate_review_report_path,
            "phase_gate_strict_validation_issues": latest_phase_gate_issue_previews,
        },
        "latest_execution_diagnostics_status": latest_execution_diagnostics_status,
        "latest_execution_drift_overview_status": latest_execution_drift_overview_status,
        "latest_execution_drift_overview_diagnostics_alignment_match": (
            latest_execution_drift_overview_diagnostics_alignment_match
        ),
        "latest_execution_drift_overview_state_comparison_mismatching_count": (
            latest_execution_drift_overview_state_comparison_mismatching_count
        ),
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count": (
            latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count
        ),
        "latest_readiness_next_phase": latest_readiness_next_phase,
        "latest_readiness_execution_ready": latest_readiness_execution_ready,
        "latest_phase_gate_decision": latest_phase_gate_decision,
        "latest_phase2_entry_allowed": latest_phase2_entry_allowed,
        "latest_phase_gate_reason": latest_phase_gate_reason,
        "latest_phase_gate_strict_validation_passed": latest_phase_gate_strict_validation_passed,
        "latest_phase_gate_strict_validation_issue_count": latest_phase_gate_strict_validation_issue_count,
        "latest_phase_gate_checked_files": latest_phase_gate_checked_files,
        "latest_phase_gate_review_report_path": latest_phase_gate_review_report_path,
        "latest_phase_gate_issue_previews": latest_phase_gate_issue_previews,
        "diagnostics_status_counts": diagnostics_status_counts,
        "drift_overview_status_counts": drift_overview_status_counts,
        "drift_overview_diagnostics_alignment_counts": drift_overview_diagnostics_alignment_counts,
        "drift_overview_state_comparison_mismatching_count_values": (
            drift_overview_state_comparison_mismatching_count_values
        ),
        "drift_overview_snapshot_drift_mismatching_snapshot_count_values": (
            drift_overview_snapshot_drift_mismatching_snapshot_count_values
        ),
        "readiness_next_phase_counts": readiness_next_phase_counts,
        "phase_gate_decision_counts": phase_gate_decision_counts,
        "phase2_entry_allowed_counts": phase2_entry_allowed_counts,
        "phase_gate_reason_counts": phase_gate_reason_counts,
        "phase_gate_strict_validation_passed_counts": phase_gate_strict_validation_passed_counts,
        "phase_gate_strict_validation_issue_count_values": phase_gate_strict_validation_issue_count_values,
        "phase_gate_checked_files_values": phase_gate_checked_files_values,
        "paper_cycle_history_report_path": str(out_path) if out_path is not None else None,
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path, latest_phase_gate_review_report_path),
    }
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path, latest_phase_gate_review_report_path)
    latest_phase_gate_issue_previews = (
        summary["latest_phase_gate_issue_previews"]
        if isinstance(summary.get("latest_phase_gate_issue_previews"), list)
        else []
    )
    summary["quick_navigation"] = quick_navigation
    summary["related_reports"] = related_reports

    lines = ["# Paper Cycle History Report", ""]
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
            "## Summary",
            "",
            f"- cycle_count: {summary['cycle_count']}",
            f"- completed_count: {summary['completed_count']}",
            f"- latest_status: {summary['latest_status']}",
            f"- latest_run_id: {summary['latest_run_id']}",
            f"- latest_created_at: {summary['latest_created_at']}",
            f"- total_orders: {summary['total_orders']}",
            f"- total_fills: {summary['total_fills']}",
            f"- latest_execution_overall_status: {summary['latest_execution_overall_status']}",
            f"- latest_execution_venue_count: {summary['latest_execution_venue_count']}",
            (
                "- latest_execution_comparison_all_registries_present: "
                f"{summary['latest_execution_comparison_all_registries_present']}"
            ),
            f"- latest_execution_diagnostics_status: {summary['latest_execution_diagnostics_status']}",
            f"- latest_execution_drift_overview_status: {summary['latest_execution_drift_overview_status']}",
            (
                "- latest_execution_drift_overview_diagnostics_alignment_match: "
                f"{summary['latest_execution_drift_overview_diagnostics_alignment_match']}"
            ),
            (
                "- latest_execution_drift_overview_state_comparison_mismatching_count: "
                f"{summary['latest_execution_drift_overview_state_comparison_mismatching_count']}"
            ),
            (
                "- latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: "
                f"{summary['latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count']}"
            ),
            f"- latest_readiness_next_phase: {summary['latest_readiness_next_phase']}",
            f"- latest_readiness_execution_ready: {summary['latest_readiness_execution_ready']}",
            f"- latest_phase_gate_decision: {summary['latest_phase_gate_decision']}",
            f"- latest_phase2_entry_allowed: {summary['latest_phase2_entry_allowed']}",
            f"- latest_phase_gate_reason: {summary['latest_phase_gate_reason']}",
            f"- latest_phase_gate_strict_validation_passed: {summary['latest_phase_gate_strict_validation_passed']}",
            (
                "- latest_phase_gate_strict_validation_issue_count: "
                f"{summary['latest_phase_gate_strict_validation_issue_count']}"
            ),
            f"- latest_phase_gate_checked_files: {summary['latest_phase_gate_checked_files']}",
            f"- latest_phase_gate_review_report_path: {summary['latest_phase_gate_review_report_path']}",
            "",
        ]
    )
    if latest_phase_gate_issue_previews:
        lines.extend(["## Latest Phase Gate Issue Preview", ""])
        lines.extend(f"- {item}" for item in latest_phase_gate_issue_previews)
        lines.append("")

    lines.extend(["## Diagnostics Status Counts", ""])
    if diagnostics_status_counts:
        for key in sorted(diagnostics_status_counts):
            lines.append(f"- {key}: {diagnostics_status_counts[key]}")
    else:
        lines.append("- no execution diagnostics notes were available")
    lines.append("")

    lines.extend(["## Drift Overview Status Counts", ""])
    if drift_overview_status_counts:
        for key in sorted(drift_overview_status_counts):
            lines.append(f"- {key}: {drift_overview_status_counts[key]}")
    else:
        lines.append("- no execution drift overview notes were available")
    lines.append("")

    lines.extend(["## Drift Overview Diagnostics Alignment Counts", ""])
    if drift_overview_diagnostics_alignment_counts:
        for key in sorted(drift_overview_diagnostics_alignment_counts):
            lines.append(f"- {key}: {drift_overview_diagnostics_alignment_counts[key]}")
    else:
        lines.append("- no execution drift overview alignment notes were available")
    lines.append("")

    lines.extend(["## Drift Overview State Comparison Mismatching Count Values", ""])
    if drift_overview_state_comparison_mismatching_count_values:
        for key in sorted(drift_overview_state_comparison_mismatching_count_values):
            lines.append(f"- {key}: {drift_overview_state_comparison_mismatching_count_values[key]}")
    else:
        lines.append("- no execution drift overview state comparison mismatch notes were available")
    lines.append("")

    lines.extend(["## Drift Overview Snapshot Drift Mismatching Count Values", ""])
    if drift_overview_snapshot_drift_mismatching_snapshot_count_values:
        for key in sorted(drift_overview_snapshot_drift_mismatching_snapshot_count_values):
            lines.append(f"- {key}: {drift_overview_snapshot_drift_mismatching_snapshot_count_values[key]}")
    else:
        lines.append("- no execution drift overview snapshot drift mismatch notes were available")
    lines.append("")

    lines.extend(["## Readiness Next Phase Counts", ""])
    if readiness_next_phase_counts:
        for key in sorted(readiness_next_phase_counts):
            lines.append(f"- {key}: {readiness_next_phase_counts[key]}")
    else:
        lines.append("- no readiness notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Decision Counts", ""])
    if phase_gate_decision_counts:
        for key in sorted(phase_gate_decision_counts):
            lines.append(f"- {key}: {phase_gate_decision_counts[key]}")
    else:
        lines.append("- no phase gate decision notes were available")
    lines.append("")

    lines.extend(["## Phase 2 Entry Allowed Counts", ""])
    if phase2_entry_allowed_counts:
        for key in sorted(phase2_entry_allowed_counts):
            lines.append(f"- {key}: {phase2_entry_allowed_counts[key]}")
    else:
        lines.append("- no phase2 entry notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Reason Counts", ""])
    if phase_gate_reason_counts:
        for key in sorted(phase_gate_reason_counts):
            lines.append(f"- {key}: {phase_gate_reason_counts[key]}")
    else:
        lines.append("- no phase gate reason notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Strict Validation Counts", ""])
    if phase_gate_strict_validation_passed_counts:
        for key in sorted(phase_gate_strict_validation_passed_counts):
            lines.append(f"- {key}: {phase_gate_strict_validation_passed_counts[key]}")
    else:
        lines.append("- no phase gate strict validation notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Strict Validation Issue Count Values", ""])
    if phase_gate_strict_validation_issue_count_values:
        for key in sorted(phase_gate_strict_validation_issue_count_values):
            lines.append(f"- {key}: {phase_gate_strict_validation_issue_count_values[key]}")
    else:
        lines.append("- no phase gate strict validation issue count notes were available")
    lines.append("")

    lines.extend(["## Phase Gate Checked Files Values", ""])
    if phase_gate_checked_files_values:
        for key in sorted(phase_gate_checked_files_values):
            lines.append(f"- {key}: {phase_gate_checked_files_values[key]}")
    else:
        lines.append("- no phase gate checked files notes were available")
    lines.append("")

    if cycles:
        lines.extend(
            [
                "## Recent Cycles",
                "",
            ]
        )
        for item in cycles[-5:]:
            notes = item.get("notes", [])
            notes_text = ", ".join(str(x) for x in notes) if isinstance(notes, list) else ""
            lines.append(
                f"- {item.get('created_at')} | status={item.get('status')} | run_id={item.get('run_id')} | {notes_text}"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "## No Cycles",
                "",
                "- no paper_operations_cycle entries were available in the operation chain",
                "",
            ]
        )

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
