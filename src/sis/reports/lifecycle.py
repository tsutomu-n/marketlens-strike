from __future__ import annotations

from pathlib import Path

from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    phase_gate_flat_fields,
)
from sis.storage.jsonl_store import read_json


def build_strategy_lifecycle_report(
    *,
    decision_summary_path: Path | None = None,
    weekly_review_path: Path | None = None,
    paper_last_run_path: Path | None = None,
    out_path: Path | None = None,
) -> str:
    lines = [
        "# Strategy Lifecycle Report",
        "",
    ]

    if decision_summary_path and decision_summary_path.exists():
        payload = read_json(decision_summary_path)
        if isinstance(payload, dict):
            lines.extend(
                [
                    "## Decision Summary",
                    "",
                    f"- mode: {payload.get('mode')}",
                    f"- signals_considered: {payload.get('signals_considered')}",
                    f"- executed_count: {payload.get('executed_count')}",
                    f"- blocked_count: {payload.get('blocked_count')}",
                    "",
                ]
            )

    if weekly_review_path and weekly_review_path.exists():
        text = weekly_review_path.read_text(encoding="utf-8")
        lines.extend(
            [
                "## Weekly Review Reference",
                "",
                f"- source: {weekly_review_path}",
                "",
                "```md",
                text.strip(),
                "```",
                "",
            ]
        )

    if paper_last_run_path and paper_last_run_path.exists():
        payload = read_json(paper_last_run_path)
        if isinstance(payload, dict):
            audit = payload.get("audit")
            if isinstance(audit, dict):
                audit_summary_flat = audit_summary_fields(audit, audit)
                lines.extend(
                    [
                        "## Paper Last Run Audit",
                        "",
                        f"- overall_status: {audit_summary_flat.get('overall_status')}",
                        f"- latest_operation: {audit_summary_flat.get('latest_operation')}",
                        f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count')}",
                        "",
                    ]
                )
            phase_gate = payload.get("phase_gate")
            if isinstance(phase_gate, dict):
                phase_gate = normalize_phase_gate_summary(phase_gate)
                phase_gate_flat = phase_gate_flat_fields(phase_gate)
                lines.extend(
                    [
                        "## Paper Last Run Phase Gate",
                        "",
                        f"- decision: {phase_gate_flat.get('phase_gate_decision')}",
                        f"- phase2_entry_allowed: {phase_gate_flat.get('phase2_entry_allowed')}",
                        f"- phase_gate_reason: {phase_gate_flat.get('phase_gate_reason')}",
                        f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                        (
                            "- phase_gate_strict_validation_issue_count: "
                            f"{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}"
                        ),
                        f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
                        "",
                    ]
                )
            execution_drift_overview = payload.get("execution_drift_overview_summary")
            if isinstance(execution_drift_overview, dict):
                execution_drift_overview = normalize_execution_drift_overview_summary(
                    execution_drift_overview
                )
                execution_drift_flat = execution_drift_overview_flat_fields(execution_drift_overview)
                lines.extend(
                    [
                        "## Paper Last Run Execution Drift Overview",
                        "",
                        f"- overall_status: {execution_drift_flat.get('execution_drift_overview_status')}",
                        (
                            "- diagnostics_alignment_match: "
                            f"{execution_drift_flat.get('execution_drift_overview_diagnostics_alignment_match')}"
                        ),
                        (
                            "- state_comparison_mismatching_count: "
                            f"{execution_drift_flat.get('execution_drift_overview_state_comparison_mismatching_count')}"
                        ),
                        (
                            "- snapshot_drift_mismatching_snapshot_count: "
                            f"{execution_drift_flat.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
                        ),
                        f"- report_path: {execution_drift_flat.get('execution_drift_overview_report_path')}",
                        "",
                    ]
                )

    if len(lines) == 2:
        lines.extend(
            [
                "## No Inputs",
                "",
                "- no decision summary or weekly review artifacts were available",
                "",
            ]
        )

    report = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
    return report
