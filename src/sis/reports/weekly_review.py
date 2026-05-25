from __future__ import annotations

from pathlib import Path

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


def _quick_navigation(
    out_path: Path | None,
    row: dict[str, object],
) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    items: list[tuple[str, str | None]] = [
        ("weekly_review_report", str(out_path)),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("phase_gate_review_report", str(reports_dir / "phase_gate_review.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("strategy_lifecycle_report", str(reports_dir / "strategy_lifecycle_report.md")),
        (
            "live_evidence_report",
            row.get("live_evidence_report_path") if isinstance(row.get("live_evidence_report_path"), str) else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def _nested_report_path(row: dict[str, object], section: str, flat_key: str) -> str | None:
    value = row.get(flat_key)
    if isinstance(value, str) and value:
        return value
    nested = row.get(section)
    if isinstance(nested, dict):
        nested_value = nested.get("report_path")
        if isinstance(nested_value, str) and nested_value:
            return nested_value
    return None


def _related_reports(out_path: Path | None, row: dict[str, object]) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    items: list[tuple[str, str | None]] = [
        ("weekly_review_report", str(out_path)),
        ("operations_dashboard_report", str(reports_dir / "operations_dashboard.md")),
        ("ops_review_report", str(reports_dir / "ops_review.md")),
        ("current_state_index_report", str(reports_dir / "current_state_index.md")),
        ("readiness_snapshot_report", str(reports_dir / "readiness_snapshot.md")),
        ("phase_gate_review_report", str(reports_dir / "phase_gate_review.md")),
        ("go_no_go_report", str(out_path.parent.parent / "research/go_no_go_report.md")),
        ("paper_operations_runbook_report", str(reports_dir / "paper_operations_runbook.md")),
        ("strategy_lifecycle_report", str(reports_dir / "strategy_lifecycle_report.md")),
        ("paper_vs_backtest_comparison_report", str(reports_dir / "paper_vs_backtest_comparison.md")),
        (
            "execution_snapshot_report",
            _nested_report_path(row, "execution_summary", "execution_report_path"),
        ),
        (
            "execution_venue_comparison_report",
            _nested_report_path(
                row,
                "execution_comparison_summary",
                "execution_comparison_report_path",
            ),
        ),
        (
            "execution_venue_diagnostics_report",
            _nested_report_path(
                row,
                "execution_diagnostics_summary",
                "execution_diagnostics_report_path",
            ),
        ),
        (
            "execution_gap_history_report",
            _nested_report_path(
                row,
                "execution_gap_history_summary",
                "execution_gap_history_report_path",
            ),
        ),
        (
            "execution_state_comparison_report",
            _nested_report_path(
                row,
                "execution_state_comparison_summary",
                "execution_state_comparison_report_path",
            ),
        ),
        (
            "execution_snapshot_drift_report",
            _nested_report_path(
                row,
                "execution_snapshot_drift_summary",
                "execution_snapshot_drift_report_path",
            ),
        ),
        (
            "execution_drift_overview_report",
            _nested_report_path(
                row,
                "execution_drift_overview_summary",
                "execution_drift_overview_report_path",
            ),
        ),
        (
            "live_evidence_report",
            row.get("live_evidence_report_path") if isinstance(row.get("live_evidence_report_path"), str) else None,
        ),
    ]
    return {key: value for key, value in items if isinstance(value, str) and value}


def build_weekly_review_report(
    *,
    backtest_metrics_path: Path | None = None,
    daily_pnl_path: Path | None = None,
    paper_last_run_path: Path | None = None,
    out_path: Path | None = None,
) -> str:
    lines = [
        "# Weekly Strategy Review",
        "",
    ]

    if backtest_metrics_path and backtest_metrics_path.exists():
        metrics_rows = safe_read_json_dict_list(backtest_metrics_path)
        lines.extend(
            [
                "## Backtest Metrics Snapshot",
                "",
                f"- rows: {len(metrics_rows)}",
            ]
        )
        if metrics_rows:
            symbols = sorted(
                {
                    str(symbol)
                    for row in metrics_rows
                    for symbol in [row.get("canonical_symbol")]
                    if isinstance(symbol, str) and symbol
                }
            )
            lines.append(f"- symbols: {', '.join(symbols)}")
        lines.append("")

    if daily_pnl_path and daily_pnl_path.exists():
        pnl = pl.read_parquet(daily_pnl_path)
        lines.extend(
            [
                "## Paper PnL Snapshot",
                "",
                f"- rows: {pnl.height}",
            ]
        )
        if pnl.height and "realized_pnl" in pnl.columns:
            lines.append(f"- total_realized_pnl: {float(pnl['realized_pnl'].sum()):.4f}")
        lines.append("")

    row = safe_read_json_dict(paper_last_run_path)
    quick_navigation = _quick_navigation(out_path, row)
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
                execution_comparison = normalize_execution_comparison_summary(
                    execution_comparison
                )
                execution_comparison_flat = execution_comparison_flat_fields(
                    execution_comparison
                )
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
                execution_diagnostics = normalize_execution_diagnostics_summary(
                    execution_diagnostics
                )
                execution_diagnostics_flat = execution_diagnostics_flat_fields(
                    execution_diagnostics
                )
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
                execution_gap_history = normalize_execution_gap_history_summary(
                    execution_gap_history
                )
                execution_gap_history_flat = execution_gap_history_flat_fields(
                    execution_gap_history
                )
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
                            row.get(
                                "timeline_latest_execution_comparison_all_registries_present"
                            ),
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
                            row.get(
                                "cycle_history_latest_execution_comparison_all_registries_present"
                            ),
                        ),
                    ]
                )
            )

    if len(lines) == 2:
        lines.extend(
            [
                "## No Inputs",
                "",
                "- no backtest metrics or paper pnl artifacts were available",
                "",
            ]
        )

    text = "\n".join(lines).rstrip() + "\n"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    return text
