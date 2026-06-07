from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import polars as pl
from sis.reports.loaders import safe_read_json_dict, safe_read_json_dict_list
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    latest_execution_flat_sections,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_snapshot_summary,
    normalize_execution_state_comparison_summary,
    normalize_phase_gate_summary,
    normalize_readiness_summary,
    phase_gate_flat_fields,
    readiness_flat_fields,
)


def _dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _quick_navigation(
    out_path: Path | None,
    phase_gate_report_path: str | None,
) -> dict[str, str]:
    if out_path is None:
        return {}
    items = (
        ("paper_vs_backtest_comparison_report", str(out_path)),
        ("phase_gate_review_report", phase_gate_report_path),
        ("current_state_index_report", str(out_path.parent / "current_state_index.md")),
        ("readiness_snapshot_report", str(out_path.parent / "readiness_snapshot.md")),
        ("paper_operations_runbook_report", str(out_path.parent / "paper_operations_runbook.md")),
    )
    return {key: value for key, value in items if isinstance(value, str) and value}


def _related_reports(
    out_path: Path | None,
    row: dict[str, object],
) -> dict[str, str]:
    if out_path is None:
        return {}
    phase_gate = row.get("phase_gate")
    phase_gate_report_path = None
    if isinstance(phase_gate, dict):
        phase_gate_report_path = phase_gate_flat_fields(
            normalize_phase_gate_summary(_dict_or_empty(phase_gate))
        ).get("phase_gate_review_report_path")
    items = (
        ("paper_vs_backtest_comparison_report", str(out_path)),
        ("phase_gate_review_report", phase_gate_report_path),
        ("current_state_index_report", str(out_path.parent / "current_state_index.md")),
        ("readiness_snapshot_report", str(out_path.parent / "readiness_snapshot.md")),
        ("operations_dashboard_report", str(out_path.parent / "operations_dashboard.md")),
        ("paper_operations_runbook_report", str(out_path.parent / "paper_operations_runbook.md")),
    )
    execution_summary = row.get("execution_summary")
    if isinstance(execution_summary, dict):
        items += (
            (
                "execution_snapshot_report",
                execution_snapshot_flat_fields(
                    normalize_execution_snapshot_summary(_dict_or_empty(execution_summary))
                ).get("execution_report_path"),
            ),
        )
    execution_comparison = row.get("execution_comparison_summary")
    if isinstance(execution_comparison, dict):
        items += (
            (
                "execution_venue_comparison_report",
                execution_comparison_flat_fields(
                    normalize_execution_comparison_summary(_dict_or_empty(execution_comparison))
                ).get("execution_comparison_report_path"),
            ),
        )
    execution_diagnostics = row.get("execution_diagnostics_summary")
    if isinstance(execution_diagnostics, dict):
        items += (
            (
                "execution_venue_diagnostics_report",
                execution_diagnostics_flat_fields(
                    normalize_execution_diagnostics_summary(_dict_or_empty(execution_diagnostics))
                ).get("execution_diagnostics_report_path"),
            ),
        )
    execution_gap_history = row.get("execution_gap_history_summary")
    if isinstance(execution_gap_history, dict):
        items += (
            (
                "execution_gap_history_report",
                execution_gap_history_flat_fields(
                    normalize_execution_gap_history_summary(_dict_or_empty(execution_gap_history))
                ).get("execution_gap_history_report_path"),
            ),
        )
    execution_state_comparison = row.get("execution_state_comparison_summary")
    if isinstance(execution_state_comparison, dict):
        items += (
            (
                "execution_state_comparison_report",
                execution_state_comparison_flat_fields(
                    normalize_execution_state_comparison_summary(
                        _dict_or_empty(execution_state_comparison)
                    )
                ).get("execution_state_comparison_report_path"),
            ),
        )
    execution_snapshot_drift = row.get("execution_snapshot_drift_summary")
    if isinstance(execution_snapshot_drift, dict):
        items += (
            (
                "execution_snapshot_drift_report",
                execution_snapshot_drift_flat_fields(
                    normalize_execution_snapshot_drift_summary(
                        _dict_or_empty(execution_snapshot_drift)
                    )
                ).get("execution_snapshot_drift_report_path"),
            ),
        )
    execution_drift_overview = row.get("execution_drift_overview_summary")
    if isinstance(execution_drift_overview, dict):
        items += (
            (
                "execution_drift_overview_report",
                execution_drift_overview_flat_fields(
                    normalize_execution_drift_overview_summary(
                        _dict_or_empty(execution_drift_overview)
                    )
                ).get("execution_drift_overview_report_path"),
            ),
        )
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_paper_live_comparison_report(
    *,
    paper_pnl_path: Path | None = None,
    backtest_metrics_path: Path | None = None,
    paper_last_run_path: Path | None = None,
    out_path: Path | None = None,
) -> str:
    lines = [
        "# Paper vs Backtest Comparison",
        "",
    ]

    paper_total = None
    if paper_pnl_path and paper_pnl_path.exists():
        pnl = pl.read_parquet(paper_pnl_path)
        lines.extend(
            [
                "## Paper Summary",
                "",
                f"- rows: {pnl.height}",
            ]
        )
        if pnl.height and "realized_pnl" in pnl.columns:
            paper_total = float(pnl["realized_pnl"].sum())
            lines.append(f"- total_realized_pnl: {paper_total:.4f}")
        lines.append("")

    backtest_avg = None
    if backtest_metrics_path and backtest_metrics_path.exists():
        metrics_rows = safe_read_json_dict_list(backtest_metrics_path)
        lines.extend(
            [
                "## Backtest Summary",
                "",
                f"- rows: {len(metrics_rows)}",
            ]
        )
        if metrics_rows:
            values = [
                float(value)
                for row in metrics_rows
                for value in [row.get("avg_trade_return")]
                if value is not None
            ]
            if values:
                backtest_avg = sum(values) / len(values)
                lines.append(f"- avg_trade_return_mean: {backtest_avg:.6f}")
        lines.append("")

    lines.extend(
        [
            "## Comparison",
            "",
            f"- paper_total_realized_pnl: {paper_total}",
            f"- backtest_avg_trade_return_mean: {backtest_avg}",
        ]
    )
    if paper_total is None or backtest_avg is None:
        lines.append("- interpretation: insufficient_inputs")
    else:
        lines.append("- interpretation: manual_review_required")
    lines.append("")

    row = safe_read_json_dict(paper_last_run_path)
    phase_gate_report_path = None
    if row:
        phase_gate = row.get("phase_gate")
        if isinstance(phase_gate, dict):
            phase_gate_report_path = phase_gate_flat_fields(
                normalize_phase_gate_summary(phase_gate)
            ).get("phase_gate_review_report_path")
    quick_navigation = _quick_navigation(out_path, phase_gate_report_path)
    related_reports = _related_reports(out_path, row)
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    if row:
        audit = row.get("audit")
        if isinstance(audit, dict):
            audit_summary_flat = audit_summary_fields(audit, audit)
            lines.extend(
                [
                    "## Paper Last Run Audit",
                    "",
                    f"- overall_status: {audit_summary_flat.get('overall_status') or ''}",
                    f"- latest_operation: {audit_summary_flat.get('latest_operation') or ''}",
                    f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count') or ''}",
                    "",
                ]
            )
        phase_gate = row.get("phase_gate")
        if isinstance(phase_gate, dict):
            phase_gate = normalize_phase_gate_summary(phase_gate)
            phase_gate_flat = phase_gate_flat_fields(phase_gate)
            lines.extend(
                [
                    "## Paper Last Run Phase Gate",
                    "",
                    f"- decision: {phase_gate_flat.get('phase_gate_decision') or ''}",
                    f"- phase2_entry_allowed: {phase_gate_flat.get('phase2_entry_allowed')}",
                    f"- phase_gate_reason: {phase_gate_flat.get('phase_gate_reason') or ''}",
                    f"- strict_validation_passed: {phase_gate_flat.get('strict_validation_passed')}",
                    (
                        "- phase_gate_strict_validation_issue_count: "
                        f"{phase_gate_flat.get('phase_gate_strict_validation_issue_count')}"
                    ),
                    f"- phase_gate_checked_files: {phase_gate_flat.get('phase_gate_checked_files')}",
                    "",
                ]
            )
        readiness = row.get("readiness_summary")
        if isinstance(readiness, dict):
            readiness = normalize_readiness_summary(readiness)
            readiness_flat = readiness_flat_fields(readiness)
            lines.extend(
                [
                    "## Paper Last Run Readiness",
                    "",
                    (
                        "- next_phase_candidate: "
                        f"{readiness_flat.get('readiness_next_phase_candidate') or ''}"
                    ),
                    f"- execution_ready: {readiness_flat.get('readiness_execution_ready')}",
                    "",
                ]
            )
        execution_summary = row.get("execution_summary")
        if isinstance(execution_summary, dict):
            execution_summary = normalize_execution_snapshot_summary(execution_summary)
            execution_summary_flat = execution_snapshot_flat_fields(execution_summary)
            lines.extend(
                [
                    "## Paper Last Run Execution Snapshot",
                    "",
                    f"- overall_status: {execution_summary_flat.get('execution_overall_status') or ''}",
                    f"- venue_count: {execution_summary_flat.get('execution_venue_count')}",
                    f"- report_path: {execution_summary_flat.get('execution_report_path') or ''}",
                    "",
                ]
            )
        execution_comparison = row.get("execution_comparison_summary")
        if isinstance(execution_comparison, dict):
            execution_comparison = normalize_execution_comparison_summary(execution_comparison)
            execution_comparison_flat = execution_comparison_flat_fields(execution_comparison)
            lines.extend(
                [
                    "## Paper Last Run Execution Venue Comparison",
                    "",
                    (
                        "- all_registries_present: "
                        f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
                    ),
                    f"- report_path: {execution_comparison_flat.get('execution_comparison_report_path') or ''}",
                    "",
                ]
            )
        execution_diagnostics = row.get("execution_diagnostics_summary")
        if isinstance(execution_diagnostics, dict):
            execution_diagnostics = normalize_execution_diagnostics_summary(execution_diagnostics)
            execution_diagnostics_flat = execution_diagnostics_flat_fields(execution_diagnostics)
            lines.extend(
                [
                    "## Paper Last Run Execution Venue Diagnostics",
                    "",
                    f"- overall_status: {execution_diagnostics_flat.get('execution_diagnostics_status') or ''}",
                    f"- balance_gap_detected: {execution_diagnostics_flat.get('execution_balance_gap_detected')}",
                    f"- fills_gap_detected: {execution_diagnostics_flat.get('execution_fills_gap_detected')}",
                    f"- report_path: {execution_diagnostics_flat.get('execution_diagnostics_report_path') or ''}",
                    "",
                ]
            )
        execution_gap_history = row.get("execution_gap_history_summary")
        if isinstance(execution_gap_history, dict):
            execution_gap_history = normalize_execution_gap_history_summary(execution_gap_history)
            execution_gap_history_flat = execution_gap_history_flat_fields(execution_gap_history)
            lines.extend(
                [
                    "## Paper Last Run Execution Gap History",
                    "",
                    f"- entry_count: {execution_gap_history_flat.get('execution_gap_history_entry_count')}",
                    f"- latest_status: {execution_gap_history_flat.get('execution_gap_history_latest_status') or ''}",
                    (
                        "- latest_execution_diagnostics_status: "
                        f"{execution_gap_history_flat.get('execution_gap_history_latest_diagnostics_status') or ''}"
                    ),
                    f"- report_path: {execution_gap_history_flat.get('execution_gap_history_report_path') or ''}",
                    "",
                ]
            )
        execution_state_comparison = row.get("execution_state_comparison_summary")
        if isinstance(execution_state_comparison, dict):
            execution_state_comparison = normalize_execution_state_comparison_summary(
                execution_state_comparison
            )
            execution_state_comparison_flat = execution_state_comparison_flat_fields(
                execution_state_comparison
            )
            lines.extend(
                [
                    "## Paper Last Run Execution State Comparison History",
                    "",
                    f"- entry_count: {execution_state_comparison_flat.get('execution_state_comparison_entry_count')}",
                    (
                        "- latest_status_match: "
                        f"{execution_state_comparison_flat.get('execution_state_comparison_latest_status_match')}"
                    ),
                    (
                        "- mismatching_count: "
                        f"{execution_state_comparison_flat.get('execution_state_comparison_mismatching_count')}"
                    ),
                    f"- report_path: {execution_state_comparison_flat.get('execution_state_comparison_report_path') or ''}",
                    "",
                ]
            )
        execution_snapshot_drift = row.get("execution_snapshot_drift_summary")
        if isinstance(execution_snapshot_drift, dict):
            execution_snapshot_drift = normalize_execution_snapshot_drift_summary(
                execution_snapshot_drift
            )
            execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
                execution_snapshot_drift
            )
            lines.extend(
                [
                    "## Paper Last Run Execution Snapshot Drift History",
                    "",
                    f"- entry_count: {execution_snapshot_drift_flat.get('execution_snapshot_drift_entry_count')}",
                    (
                        "- latest_status_match: "
                        f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_latest_status_match')}"
                    ),
                    (
                        "- mismatching_snapshot_count: "
                        f"{execution_snapshot_drift_flat.get('execution_snapshot_drift_mismatching_snapshot_count')}"
                    ),
                    f"- report_path: {execution_snapshot_drift_flat.get('execution_snapshot_drift_report_path') or ''}",
                    "",
                ]
            )
        execution_drift_overview = row.get("execution_drift_overview_summary")
        if isinstance(execution_drift_overview, dict):
            execution_drift_overview = normalize_execution_drift_overview_summary(
                execution_drift_overview
            )
            execution_drift_flat = execution_drift_overview_flat_fields(execution_drift_overview)
            lines.extend(
                [
                    "## Paper Last Run Execution Drift Overview",
                    "",
                    f"- overall_status: {execution_drift_flat.get('execution_drift_overview_status') or ''}",
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
                    f"- report_path: {execution_drift_flat.get('execution_drift_overview_report_path') or ''}",
                    "",
                ]
            )
        lines.extend(
            latest_execution_flat_sections(
                [
                    (
                        "## Paper Last Run Audit Timeline Latest Execution",
                        row.get("timeline_latest_execution_overall_status"),
                        row.get("timeline_latest_execution_venue_count"),
                        row.get("timeline_latest_execution_comparison_all_registries_present"),
                    ),
                    (
                        "## Paper Last Run Audit Bundle History Latest Execution",
                        row.get("bundle_history_latest_execution_overall_status"),
                        row.get("bundle_history_latest_execution_venue_count"),
                        row.get(
                            "bundle_history_latest_execution_comparison_all_registries_present"
                        ),
                    ),
                    (
                        "## Paper Last Run Cycle History Latest Execution",
                        row.get("cycle_history_latest_execution_overall_status"),
                        row.get("cycle_history_latest_execution_venue_count"),
                        row.get("cycle_history_latest_execution_comparison_all_registries_present"),
                    ),
                ]
            )
        )

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    return text
