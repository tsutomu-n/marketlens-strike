from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from sis.backtest.metrics import BacktestMetrics
from sis.reports.summary_normalizers import (
    audit_summary_fields,
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_lineage_fields_from_payload,
    latest_execution_sections,
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


def write_backtest_report(
    metrics: list[BacktestMetrics],
    out_path: Path,
    signals_path: Path | None = None,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    readiness_summary = normalize_readiness_summary(readiness_summary)
    execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    source = (
        f"This report uses research signals from `{signals_path}` for virtual venue execution."
        if signals_path is not None and signals_path.exists()
        else "This report uses venue quote logs for virtual execution. It is not a trading signal generator."
    )
    rows = "\n".join(
        "| {venue} | {symbol} | {trades} | {total:.6f} | {drawdown:.6f} | {win_rate} | {cost:.2f} | {cost_source} | {stale} | {halt} |".format(
            venue=item.venue,
            symbol=item.canonical_symbol,
            trades=item.trade_count,
            total=item.total_return,
            drawdown=item.max_drawdown,
            win_rate="" if item.win_rate is None else f"{item.win_rate:.4f}",
            cost=item.cost_drag_bps,
            cost_source=item.cost_source or "",
            stale=item.stale_rejected_count,
            halt=item.halt_rejected_count,
        )
        for item in metrics
    )
    lines = [
        "# Backtest Bridge Report",
        "",
        source,
        "",
        "| Venue | Symbol | Trades | Total Return | Max Drawdown | Win Rate | Cost Drag bps | Cost Source | Stale Rejects | Halt Rejects |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|---:|",
        rows,
        "",
    ]
    if isinstance(audit_summary, dict) and any(audit_summary.values()):
        audit_summary_flat = audit_summary_fields(audit_summary, audit_summary)
        lines.extend(
            [
                "## Audit Summary",
                "",
                f"- overall_status: {audit_summary_flat.get('overall_status') or ''}",
                f"- latest_operation: {audit_summary_flat.get('latest_operation') or ''}",
                f"- bundle_history_snapshot_count: {audit_summary_flat.get('bundle_history_snapshot_count') or ''}",
                "",
            ]
        )
    if isinstance(phase_gate_summary, dict) and any(phase_gate_summary.values()):
        phase_gate_flat = phase_gate_flat_fields(phase_gate_summary)
        lines.extend(
            [
                "## Phase Gate Summary",
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
    if isinstance(readiness_summary, dict) and any(readiness_summary.values()):
        readiness_flat = readiness_flat_fields(readiness_summary)
        lines.extend(
            [
                "## Readiness Summary",
                "",
                f"- next_phase_candidate: {readiness_flat.get('readiness_next_phase_candidate') or ''}",
                f"- execution_ready: {readiness_flat.get('readiness_execution_ready')}",
                f"- phase_gate_decision: {readiness_flat.get('phase_gate_decision') or ''}",
                f"- phase2_entry_allowed: {readiness_flat.get('phase2_entry_allowed')}",
                "",
            ]
        )
    if isinstance(execution_summary, dict) and any(execution_summary.values()):
        execution_summary_flat = execution_snapshot_flat_fields(execution_summary)
        lines.extend(
            [
                "## Execution Snapshot",
                "",
                f"- overall_status: {execution_summary_flat.get('execution_overall_status') or ''}",
                f"- venue_count: {execution_summary_flat.get('execution_venue_count')}",
                f"- report_path: {execution_summary_flat.get('execution_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_comparison_summary, dict) and any(
        execution_comparison_summary.values()
    ):
        execution_comparison_flat = execution_comparison_flat_fields(execution_comparison_summary)
        lines.extend(
            [
                "## Execution Venue Comparison",
                "",
                (
                    "- all_registries_present: "
                    f"{execution_comparison_flat.get('execution_comparison_all_registries_present')}"
                ),
                f"- report_path: {execution_comparison_flat.get('execution_comparison_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_diagnostics_summary, dict) and any(
        execution_diagnostics_summary.values()
    ):
        execution_diagnostics_flat = execution_diagnostics_flat_fields(
            execution_diagnostics_summary
        )
        lines.extend(
            [
                "## Execution Venue Diagnostics",
                "",
                f"- overall_status: {execution_diagnostics_flat.get('execution_diagnostics_status') or ''}",
                f"- balance_gap_detected: {execution_diagnostics_flat.get('execution_balance_gap_detected')}",
                f"- fills_gap_detected: {execution_diagnostics_flat.get('execution_fills_gap_detected')}",
                f"- report_path: {execution_diagnostics_flat.get('execution_diagnostics_report_path') or ''}",
                "",
            ]
        )
    if isinstance(execution_gap_history_summary, dict) and any(
        execution_gap_history_summary.values()
    ):
        execution_gap_history_flat = execution_gap_history_flat_fields(
            execution_gap_history_summary
        )
        lines.extend(
            [
                "## Execution Gap History",
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
    if isinstance(execution_state_comparison_summary, dict) and any(
        execution_state_comparison_summary.values()
    ):
        execution_state_comparison_flat = execution_state_comparison_flat_fields(
            execution_state_comparison_summary
        )
        lines.extend(
            [
                "## Execution State Comparison History",
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
    if isinstance(execution_snapshot_drift_summary, dict) and any(
        execution_snapshot_drift_summary.values()
    ):
        execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
            execution_snapshot_drift_summary
        )
        lines.extend(
            [
                "## Execution Snapshot Drift History",
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
    if isinstance(execution_drift_overview_summary, dict) and any(
        execution_drift_overview_summary.values()
    ):
        execution_drift_flat = execution_drift_overview_flat_fields(
            execution_drift_overview_summary
        )
        lines.extend(
            [
                "## Execution Drift Overview",
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
        latest_execution_sections(
            [
                (
                    "## Audit Timeline Latest Execution",
                    timeline_latest_execution_summary,
                    timeline_latest_execution_comparison_summary,
                ),
                (
                    "## Audit Bundle History Latest Execution",
                    bundle_history_latest_execution_summary,
                    bundle_history_latest_execution_comparison_summary,
                ),
                (
                    "## Cycle History Latest Execution",
                    cycle_history_latest_execution_summary,
                    cycle_history_latest_execution_comparison_summary,
                ),
            ]
        )
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_backtest_metrics_json(metrics: list[BacktestMetrics], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps([asdict(item) for item in metrics], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_backtest_metrics_summary_json(
    metrics: list[BacktestMetrics],
    out_path: Path,
    *,
    audit_summary: dict | None = None,
    phase_gate_summary: dict | None = None,
    readiness_summary: dict | None = None,
    execution_summary: dict | None = None,
    execution_comparison_summary: dict | None = None,
    execution_diagnostics_summary: dict | None = None,
    execution_gap_history_summary: dict | None = None,
    execution_state_comparison_summary: dict | None = None,
    execution_snapshot_drift_summary: dict | None = None,
    execution_drift_overview_summary: dict | None = None,
    timeline_latest_execution_summary: dict | None = None,
    timeline_latest_execution_comparison_summary: dict | None = None,
    bundle_history_latest_execution_summary: dict | None = None,
    bundle_history_latest_execution_comparison_summary: dict | None = None,
    cycle_history_latest_execution_summary: dict | None = None,
    cycle_history_latest_execution_comparison_summary: dict | None = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    trade_counts = [item.trade_count for item in metrics]
    avg_trade_returns = [
        item.avg_trade_return for item in metrics if item.avg_trade_return is not None
    ]
    normalized_phase_gate_summary = normalize_phase_gate_summary(phase_gate_summary)
    normalized_readiness_summary = normalize_readiness_summary(readiness_summary)
    normalized_execution_summary = normalize_execution_snapshot_summary(execution_summary)
    normalized_execution_comparison_summary = normalize_execution_comparison_summary(
        execution_comparison_summary
    )
    normalized_execution_diagnostics_summary = normalize_execution_diagnostics_summary(
        execution_diagnostics_summary
    )
    normalized_execution_gap_history_summary = normalize_execution_gap_history_summary(
        execution_gap_history_summary
    )
    normalized_execution_state_comparison_summary = normalize_execution_state_comparison_summary(
        execution_state_comparison_summary
    )
    normalized_execution_snapshot_drift_summary = normalize_execution_snapshot_drift_summary(
        execution_snapshot_drift_summary
    )
    normalized_execution_drift_overview_summary = normalize_execution_drift_overview_summary(
        execution_drift_overview_summary
    )
    latest_execution_lineage = latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary=timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(timeline_latest_execution_comparison_summary),
        bundle_history_latest_execution_summary=(bundle_history_latest_execution_summary),
        bundle_history_latest_execution_comparison_summary=(
            bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
        cycle_history_latest_execution_comparison_summary=(
            cycle_history_latest_execution_comparison_summary
        ),
    )
    phase_gate_flat = phase_gate_flat_fields(normalized_phase_gate_summary)
    readiness_flat = readiness_flat_fields(normalized_readiness_summary)
    execution_flat = execution_snapshot_flat_fields(normalized_execution_summary)
    execution_comparison_flat = execution_comparison_flat_fields(
        normalized_execution_comparison_summary
    )
    execution_diagnostics_flat = execution_diagnostics_flat_fields(
        normalized_execution_diagnostics_summary
    )
    execution_gap_history_flat = execution_gap_history_flat_fields(
        normalized_execution_gap_history_summary
    )
    execution_state_comparison_flat = execution_state_comparison_flat_fields(
        normalized_execution_state_comparison_summary
    )
    execution_snapshot_drift_flat = execution_snapshot_drift_flat_fields(
        normalized_execution_snapshot_drift_summary
    )
    execution_drift_flat = execution_drift_overview_flat_fields(
        normalized_execution_drift_overview_summary
    )
    payload = {
        "row_count": len(metrics),
        "venues": sorted({item.venue for item in metrics}),
        "symbols": sorted({item.canonical_symbol for item in metrics}),
        "total_trade_count": sum(trade_counts),
        "max_trade_count": max(trade_counts, default=0),
        "avg_trade_return_mean": (sum(avg_trade_returns) / len(avg_trade_returns))
        if avg_trade_returns
        else None,
        "max_drawdown_worst": min((item.max_drawdown for item in metrics), default=None),
        "cost_drag_bps_total": sum(item.cost_drag_bps for item in metrics),
        "stale_rejected_total": sum(item.stale_rejected_count for item in metrics),
        "halt_rejected_total": sum(item.halt_rejected_count for item in metrics),
        "audit": audit_summary if isinstance(audit_summary, dict) else {},
        "phase_gate": normalized_phase_gate_summary,
        **phase_gate_flat,
        "readiness_summary": normalized_readiness_summary,
        **readiness_flat,
        "execution": normalized_execution_summary,
        **execution_flat,
        "execution_comparison": normalized_execution_comparison_summary,
        **execution_comparison_flat,
        "execution_diagnostics": normalized_execution_diagnostics_summary,
        **execution_diagnostics_flat,
        "execution_gap_history_summary": normalized_execution_gap_history_summary,
        **execution_gap_history_flat,
        "execution_state_comparison_summary": normalized_execution_state_comparison_summary,
        **execution_state_comparison_flat,
        "execution_snapshot_drift_summary": normalized_execution_snapshot_drift_summary,
        **execution_snapshot_drift_flat,
        "execution_drift_overview_summary": normalized_execution_drift_overview_summary,
        **execution_drift_flat,
        **latest_execution_lineage,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
