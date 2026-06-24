from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from sis.core.decision import DecisionRecord
from sis.reports.summary_normalizers import (
    execution_comparison_flat_fields,
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_snapshot_flat_fields,
    execution_state_comparison_flat_fields,
    latest_execution_lineage_fields_from_payload,
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


def _float_from_summary_value(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return 0.0


def executed_signal_summary(results: list[dict[str, object]]) -> dict[str, object]:
    if not results:
        return {
            "result_count": 0,
            "first_ts_signal": None,
            "last_ts_signal": None,
            "side_counts": {},
            "symbol_counts": {},
            "timeframe_counts": {},
            "exit_reason_counts": {},
            "total_signal_return": 0.0,
            "avg_signal_return": None,
            "win_rate": None,
            "total_cost_drag_bps": 0.0,
            "total_notional_usd": 0.0,
            "notional_weighted_signal_return": None,
        }

    signal_returns = [
        _float_from_summary_value(item.get("signal_return") or 0.0) for item in results
    ]
    notionals = [_float_from_summary_value(item.get("notional_usd") or 0.0) for item in results]
    total_notional = sum(notionals)
    total_signal_return = sum(signal_returns)
    ts_values = [str(item.get("ts_signal")) for item in results if item.get("ts_signal")]
    return {
        "result_count": len(results),
        "first_ts_signal": min(ts_values) if ts_values else None,
        "last_ts_signal": max(ts_values) if ts_values else None,
        "side_counts": dict(Counter(str(item.get("side")) for item in results)),
        "symbol_counts": dict(Counter(str(item.get("canonical_symbol")) for item in results)),
        "timeframe_counts": dict(Counter(str(item.get("timeframe")) for item in results)),
        "exit_reason_counts": dict(Counter(str(item.get("exit_reason")) for item in results)),
        "total_signal_return": total_signal_return,
        "avg_signal_return": total_signal_return / len(signal_returns),
        "win_rate": sum(1 for value in signal_returns if value > 0) / len(signal_returns),
        "total_cost_drag_bps": sum(
            _float_from_summary_value(item.get("cost_drag_bps") or 0.0) for item in results
        ),
        "total_notional_usd": total_notional,
        "notional_weighted_signal_return": (
            sum(
                signal_return * notional
                for signal_return, notional in zip(signal_returns, notionals, strict=True)
            )
            / total_notional
            if total_notional > 0
            else None
        ),
    }


def enrich_backtest_decision_summary(
    summary: dict[str, object],
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
) -> dict[str, object]:
    enriched = dict(summary)
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

    if isinstance(audit_summary, dict) and any(audit_summary.values()):
        enriched["audit"] = audit_summary
    if normalized_phase_gate_summary and any(normalized_phase_gate_summary.values()):
        enriched["phase_gate"] = normalized_phase_gate_summary
        enriched.update(phase_gate_flat_fields(normalized_phase_gate_summary))
    if normalized_readiness_summary and any(normalized_readiness_summary.values()):
        enriched["readiness_summary"] = normalized_readiness_summary
        enriched.update(readiness_flat_fields(normalized_readiness_summary))
    if normalized_execution_summary and any(normalized_execution_summary.values()):
        enriched["execution_summary"] = normalized_execution_summary
        enriched.update(execution_snapshot_flat_fields(normalized_execution_summary))
    if normalized_execution_comparison_summary and any(
        normalized_execution_comparison_summary.values()
    ):
        enriched["execution_comparison_summary"] = normalized_execution_comparison_summary
        enriched.update(execution_comparison_flat_fields(normalized_execution_comparison_summary))
    if normalized_execution_diagnostics_summary and any(
        normalized_execution_diagnostics_summary.values()
    ):
        enriched["execution_diagnostics_summary"] = normalized_execution_diagnostics_summary
        enriched.update(execution_diagnostics_flat_fields(normalized_execution_diagnostics_summary))
    if normalized_execution_gap_history_summary and any(
        normalized_execution_gap_history_summary.values()
    ):
        enriched["execution_gap_history_summary"] = normalized_execution_gap_history_summary
        enriched.update(execution_gap_history_flat_fields(normalized_execution_gap_history_summary))
    if normalized_execution_state_comparison_summary and any(
        normalized_execution_state_comparison_summary.values()
    ):
        enriched["execution_state_comparison_summary"] = (
            normalized_execution_state_comparison_summary
        )
        enriched.update(
            execution_state_comparison_flat_fields(normalized_execution_state_comparison_summary)
        )
    if normalized_execution_snapshot_drift_summary and any(
        normalized_execution_snapshot_drift_summary.values()
    ):
        enriched["execution_snapshot_drift_summary"] = normalized_execution_snapshot_drift_summary
        enriched.update(
            execution_snapshot_drift_flat_fields(normalized_execution_snapshot_drift_summary)
        )
    if normalized_execution_drift_overview_summary and any(
        normalized_execution_drift_overview_summary.values()
    ):
        enriched["execution_drift_overview_summary"] = normalized_execution_drift_overview_summary
        enriched.update(
            execution_drift_overview_flat_fields(normalized_execution_drift_overview_summary)
        )
    enriched.update(latest_execution_lineage)
    return enriched


def write_decision_records(records: list[DecisionRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.model_dump_json() + "\n")


def write_decision_summary(summary: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
