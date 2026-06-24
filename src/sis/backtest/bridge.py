from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl

from sis.backtest.costs import CostProfile, load_cost_profiles, round_trip_cost_bps
from sis.backtest.decision_summaries import (
    enrich_backtest_decision_summary as _enrich_backtest_decision_summary,
    executed_signal_summary as _executed_signal_summary,
    write_decision_records as _write_decision_records,
    write_decision_summary as _write_decision_summary,
)
from sis.backtest.exits import resolve_signal_exit as _resolve_signal_exit
from sis.backtest.fills import (
    effective_fill_fraction as _effective_fill_fraction,
    entry_fill_index as _entry_fill_index,
    microstructure_fill_fraction as _microstructure_fill_fraction,
)
from sis.backtest.metrics import (
    BacktestMetrics,
    dominant_cost_source as _dominant_cost_source,
    metrics_for_group as _metrics_for_group,
    metrics_from_returns as _metrics_from_returns,
)
from sis.backtest.prices import (
    execution_price as _execution_price,
)
from sis.backtest.report_writers import (
    write_backtest_metrics_json as write_backtest_metrics_json,
    write_backtest_metrics_summary_json as write_backtest_metrics_summary_json,
    write_backtest_report as write_backtest_report,
)
from sis.backtest.signal_returns import scaled_signal_return as _scaled_signal_return
from sis.backtest.signals import ResearchSignal, load_research_signals
from sis.core.context import DecisionContext
from sis.core.decision import DecisionRecord
from sis.core.execution_plan import build_execution_plan
from sis.core.strategy import SignalPassthroughStrategy
from sis.risk.risk_gate import evaluate_risk_gate


def _parse_quote_ts(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError(f"Unsupported quote timestamp: {value!r}")


def _metrics_for_signals(
    quotes: pl.DataFrame,
    signals: list[ResearchSignal],
    cost_profiles: dict[tuple[str, str], CostProfile] | None = None,
    *,
    exit_model: str = "next_row",
    holding_horizon_minutes: int | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if exit_model not in {"next_row", "fixed_horizon"}:
        raise ValueError(f"Unsupported exit_model: {exit_model}")
    if exit_model == "fixed_horizon" and (
        holding_horizon_minutes is None or holding_horizon_minutes <= 0
    ):
        raise ValueError("holding_horizon_minutes must be positive for fixed_horizon")
    rows_by_key: dict[tuple[str, str], list[dict]] = {}
    for row in quotes.sort("ts_client").to_dicts():
        key = (str(row["venue"]), str(row["canonical_symbol"]).upper())
        rows_by_key.setdefault(key, []).append(row)

    signals_by_symbol: dict[str, list[ResearchSignal]] = {}
    for signal in signals:
        signals_by_symbol.setdefault(signal.canonical_symbol, []).append(signal)
    signals_by_symbol = {
        symbol: sorted(symbol_signals, key=lambda item: item.ts_signal)
        for symbol, symbol_signals in signals_by_symbol.items()
    }

    metrics: list[BacktestMetrics] = []
    decision_records: list[DecisionRecord] = []
    blocked_reason_counts: dict[str, int] = {}
    exit_reason_counts: dict[str, int] = {}
    entry_order_type_counts: dict[str, int] = {}
    executed_signal_results: list[dict[str, object]] = []
    entry_order_unfilled = 0
    executed = 0
    blocked = 0
    strategy = SignalPassthroughStrategy()
    for (venue, symbol), rows in rows_by_key.items():
        symbol_signals = signals_by_symbol.get(symbol, [])
        if not symbol_signals:
            continue

        returns: list[float] = []
        equity = [1.0]
        cost_drag_bps = 0.0
        cost_sources: list[str] = []
        stale_rejected = 0
        halt_rejected = 0
        quote_times = [_parse_quote_ts(row["ts_client"]) for row in rows]

        for signal in symbol_signals:
            if signal.side in {"close", "reduce", "add", "rebalance"}:
                continue
            reference_index = next(
                (
                    index
                    for index, quote_time in enumerate(quote_times)
                    if quote_time >= signal.ts_signal
                ),
                None,
            )
            if reference_index is None:
                stale_rejected += 1
                continue
            entry_index, entry_block_reason = _entry_fill_index(
                rows=rows,
                quote_times=quote_times,
                reference_index=reference_index,
                signal=signal,
            )
            if entry_index is None:
                entry_order_unfilled += 1
                reason = entry_block_reason or "entry_order_unfilled"
                blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
                continue
            entry_order_type_counts[signal.entry_order_type] = (
                entry_order_type_counts.get(signal.entry_order_type, 0) + 1
            )
            exit_resolution = _resolve_signal_exit(
                signal=signal,
                symbol_signals=symbol_signals,
                quote_times=quote_times,
                entry_index=entry_index,
                exit_model=exit_model,
                holding_horizon_minutes=holding_horizon_minutes,
            )
            if exit_resolution is None:
                stale_rejected += 1
                continue
            exit_index = exit_resolution.exit_index
            final_exit_reason = exit_resolution.final_exit_reason
            min_exit_index = exit_resolution.min_exit_index
            reduce_events = exit_resolution.reduce_events
            add_events = exit_resolution.add_events
            rebalance_events = exit_resolution.rebalance_events

            entry = rows[entry_index]
            context = DecisionContext(
                decision_ts=signal.ts_signal,
                venue=venue,
                canonical_symbol=symbol,
                timeframe=signal.timeframe,
                quote_ts=_parse_quote_ts(entry["ts_client"]),
                signal_ts=signal.ts_signal,
                signal_side=signal.side,
                signal_strength=signal.signal_strength,
                strategy_name="signal_passthrough_strategy",
                market_status=str(entry.get("market_status", "unknown")),
                is_tradable=bool(entry.get("is_tradable")),
            )
            strategy_decision = strategy.evaluate(context)
            risk_decision = evaluate_risk_gate(context, entry)
            execution_plan = build_execution_plan(context, strategy_decision, risk_decision)
            decision_records.append(
                DecisionRecord(
                    context=context,
                    strategy_decision=strategy_decision,
                    risk_decision=risk_decision,
                    execution_plan=execution_plan.model_dump(mode="json"),
                )
            )
            if not risk_decision.allowed:
                blocked += 1
                for reason in risk_decision.blocked_reasons:
                    blocked_reason_counts[reason] = blocked_reason_counts.get(reason, 0) + 1
                if risk_decision.stale_rejected:
                    stale_rejected += 1
                if risk_decision.halt_rejected:
                    halt_rejected += 1
                continue

            entry_price = _execution_price(entry, signal.side)
            if entry_price is None:
                stale_rejected += 1
                continue
            microstructure_fill_fraction, microstructure_block_reason = (
                _microstructure_fill_fraction(signal, entry)
            )
            if microstructure_block_reason is not None:
                blocked += 1
                blocked_reason_counts[microstructure_block_reason] = (
                    blocked_reason_counts.get(microstructure_block_reason, 0) + 1
                )
                continue
            effective_fill_fraction = _effective_fill_fraction(
                signal, microstructure_fill_fraction or 1.0
            )
            if (
                signal.min_fill_fraction is not None
                and effective_fill_fraction < signal.min_fill_fraction
            ):
                blocked += 1
                blocked_reason_counts["execution_fill_fraction_too_low"] = (
                    blocked_reason_counts.get("execution_fill_fraction_too_low", 0) + 1
                )
                continue
            spread_raw = entry.get("spread_bps")
            spread = float(spread_raw) if isinstance(spread_raw, int | float) else None
            cost_bps, cost_source = round_trip_cost_bps(
                venue=venue,
                symbol=symbol,
                holding_horizon=signal.timeframe,
                quote_spread_bps=spread,
                cost_profiles=cost_profiles or {},
            )
            signal_return, exit_reason = _scaled_signal_return(
                rows=rows,
                quote_times=quote_times,
                entry_index=entry_index,
                horizon_exit_index=exit_index,
                entry_price=entry_price,
                side=signal.side,
                cost_bps=cost_bps,
                signal=signal,
                final_exit_reason=final_exit_reason,
                min_exit_index=min_exit_index,
                microstructure_fill_fraction=microstructure_fill_fraction or 1.0,
                reduce_events=reduce_events,
                add_events=add_events,
                rebalance_events=rebalance_events,
            )
            if exit_reason == "missing_exit_price":
                stale_rejected += 1
                continue
            returns.append(signal_return)
            exit_reason_counts[exit_reason] = exit_reason_counts.get(exit_reason, 0) + 1
            cost_drag_bps += cost_bps + signal.slippage_bps
            cost_sources.append(cost_source)
            equity.append(equity[-1] * (1.0 + returns[-1]))
            executed += 1
            executed_signal_results.append(
                {
                    "signal_id": signal.signal_id,
                    "ts_signal": signal.ts_signal,
                    "venue": venue,
                    "canonical_symbol": symbol,
                    "side": signal.side,
                    "timeframe": signal.timeframe,
                    "signal_return": signal_return,
                    "exit_reason": exit_reason,
                    "cost_drag_bps": cost_bps + signal.slippage_bps,
                    "position_weight": signal.position_weight,
                    "notional_usd": signal.notional_usd,
                    "multi_leg_group_id": signal.multi_leg_group_id,
                    "multi_leg_leg_index": signal.multi_leg_leg_index,
                    "multi_leg_leg_count": signal.multi_leg_leg_count,
                    "multi_leg_anchor_real_market_symbol": (
                        signal.multi_leg_anchor_real_market_symbol
                    ),
                }
            )

        metrics.append(
            _metrics_from_returns(
                venue=venue,
                symbol=symbol,
                returns=returns,
                equity=equity,
                cost_drag_bps=cost_drag_bps,
                cost_source=_dominant_cost_source(cost_sources),
                stale_rejected=stale_rejected,
                halt_rejected=halt_rejected,
                candidate_count=len(symbol_signals),
            )
        )
    summary: dict[str, object] = {
        "mode": "signal_driven",
        "exit_model": exit_model,
        "holding_horizon_minutes": holding_horizon_minutes,
        "signals_considered": len(signals),
        "executed_count": executed,
        "blocked_count": blocked,
        "blocked_reason_counts": blocked_reason_counts,
        "exit_reason_counts": exit_reason_counts,
        "entry_order_type_counts": entry_order_type_counts,
        "entry_order_unfilled_count": entry_order_unfilled,
        "executed_signal_results": executed_signal_results,
        "executed_signal_summary": _executed_signal_summary(executed_signal_results),
        "records_written": len(decision_records),
    }
    return metrics, decision_records, summary


def run_backtest_bridge_with_decisions(
    quotes_path: Path,
    signals_path: Path | None = None,
    cost_matrix_path: Path | None = None,
    exit_model: str = "next_row",
    holding_horizon_minutes: int | None = None,
    decision_log_path: Path | None = None,
    decision_summary_path: Path | None = None,
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
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Normalized quote parquet not found: {quotes_path}")
    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        raise ValueError(f"Normalized quote parquet is empty: {quotes_path}")

    required = {"ts_client", "venue", "canonical_symbol", "market_status", "is_tradable"}
    missing = required.difference(quotes.columns)
    if missing:
        raise ValueError(f"Normalized quote parquet missing columns: {sorted(missing)}")

    cost_profiles = load_cost_profiles(cost_matrix_path)
    if signals_path is not None:
        signals = load_research_signals(signals_path)
        if signals:
            metrics, records, summary = _metrics_for_signals(
                quotes,
                signals,
                cost_profiles,
                exit_model=exit_model,
                holding_horizon_minutes=holding_horizon_minutes,
            )
            summary = _enrich_backtest_decision_summary(
                summary,
                audit_summary=audit_summary,
                phase_gate_summary=phase_gate_summary,
                readiness_summary=readiness_summary,
                execution_summary=execution_summary,
                execution_comparison_summary=execution_comparison_summary,
                execution_diagnostics_summary=execution_diagnostics_summary,
                execution_gap_history_summary=execution_gap_history_summary,
                execution_state_comparison_summary=execution_state_comparison_summary,
                execution_snapshot_drift_summary=execution_snapshot_drift_summary,
                execution_drift_overview_summary=execution_drift_overview_summary,
                timeline_latest_execution_summary=timeline_latest_execution_summary,
                timeline_latest_execution_comparison_summary=(
                    timeline_latest_execution_comparison_summary
                ),
                bundle_history_latest_execution_summary=(bundle_history_latest_execution_summary),
                bundle_history_latest_execution_comparison_summary=(
                    bundle_history_latest_execution_comparison_summary
                ),
                cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
                cycle_history_latest_execution_comparison_summary=(
                    cycle_history_latest_execution_comparison_summary
                ),
            )
            if decision_log_path is not None:
                _write_decision_records(records, decision_log_path)
            if decision_summary_path is not None:
                _write_decision_summary(summary, decision_summary_path)
            return metrics, records, summary

    metrics = [
        _metrics_for_group(group, cost_profiles)
        for (_key, group) in quotes.group_by(["venue", "canonical_symbol"], maintain_order=True)
    ]
    summary: dict[str, object] = {
        "mode": "quote_fallback",
        "exit_model": exit_model,
        "holding_horizon_minutes": holding_horizon_minutes,
        "signals_considered": 0,
        "executed_count": 0,
        "blocked_count": 0,
        "blocked_reason_counts": {},
        "records_written": 0,
    }
    summary = _enrich_backtest_decision_summary(
        summary,
        audit_summary=audit_summary,
        phase_gate_summary=phase_gate_summary,
        readiness_summary=readiness_summary,
        execution_summary=execution_summary,
        execution_comparison_summary=execution_comparison_summary,
        execution_diagnostics_summary=execution_diagnostics_summary,
        execution_gap_history_summary=execution_gap_history_summary,
        execution_state_comparison_summary=execution_state_comparison_summary,
        execution_snapshot_drift_summary=execution_snapshot_drift_summary,
        execution_drift_overview_summary=execution_drift_overview_summary,
        timeline_latest_execution_summary=timeline_latest_execution_summary,
        timeline_latest_execution_comparison_summary=(timeline_latest_execution_comparison_summary),
        bundle_history_latest_execution_summary=bundle_history_latest_execution_summary,
        bundle_history_latest_execution_comparison_summary=(
            bundle_history_latest_execution_comparison_summary
        ),
        cycle_history_latest_execution_summary=cycle_history_latest_execution_summary,
        cycle_history_latest_execution_comparison_summary=(
            cycle_history_latest_execution_comparison_summary
        ),
    )
    if decision_summary_path is not None:
        _write_decision_summary(summary, decision_summary_path)
    if decision_log_path is not None:
        _write_decision_records([], decision_log_path)
    return metrics, [], summary


def run_backtest_bridge_for_signals(
    quotes_path: Path,
    signals: list[ResearchSignal],
    cost_matrix_path: Path | None = None,
    exit_model: str = "next_row",
    holding_horizon_minutes: int | None = None,
) -> tuple[list[BacktestMetrics], list[DecisionRecord], dict]:
    if not quotes_path.exists():
        raise FileNotFoundError(f"Normalized quote parquet not found: {quotes_path}")
    quotes = pl.read_parquet(quotes_path)
    if quotes.is_empty():
        raise ValueError(f"Normalized quote parquet is empty: {quotes_path}")

    required = {"ts_client", "venue", "canonical_symbol", "market_status", "is_tradable"}
    missing = required.difference(quotes.columns)
    if missing:
        raise ValueError(f"Normalized quote parquet missing columns: {sorted(missing)}")

    return _metrics_for_signals(
        quotes,
        signals,
        load_cost_profiles(cost_matrix_path),
        exit_model=exit_model,
        holding_horizon_minutes=holding_horizon_minutes,
    )


def run_backtest_bridge(
    quotes_path: Path,
    signals_path: Path | None = None,
    cost_matrix_path: Path | None = None,
) -> list[BacktestMetrics]:
    metrics, _records, _summary = run_backtest_bridge_with_decisions(
        quotes_path,
        signals_path=signals_path,
        cost_matrix_path=cost_matrix_path,
    )
    return metrics
