from __future__ import annotations

from pathlib import Path

import polars as pl
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_drift_overview_flat_fields,
    normalize_execution_drift_overview_summary,
    normalize_phase_gate_summary,
    phase_gate_flat_fields,
)


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
        metrics = pl.read_json(backtest_metrics_path)
        lines.extend(
            [
                "## Backtest Summary",
                "",
                f"- rows: {metrics.height}",
            ]
        )
        if metrics.height and "avg_trade_return" in metrics.columns:
            values = [float(v) for v in metrics["avg_trade_return"].to_list() if v is not None]
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

    if paper_last_run_path and paper_last_run_path.exists():
        paper_last_run = pl.read_json(paper_last_run_path)
        if paper_last_run.height:
            row = paper_last_run.to_dicts()[0]
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

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    return text
