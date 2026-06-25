from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.bridge import run_backtest_bridge_for_signals
from sis.research.strategy_lab.authoring.compiler.artifacts import (
    strategy_signals_to_research_signals,
)
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.backtest_optimizer import (
    _evaluate_pass_thresholds,
    _nested_get,
    _optimizer_sort_value,
    _optimizer_variants,
    _resolve_selection_direction,
)
from sis.research.strategy_lab.authoring.backtest_outputs import (
    write_authoring_backtest_outputs as write_authoring_backtest_outputs,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.evaluation_window import (
    apply_evaluation_window,
    capital_metrics,
    evaluation_counts,
    evaluation_window,
)
from sis.research.strategy_lab.authoring.scorecard import (
    _increment_count,
    _strategy_scorecard,
)
from sis.research.strategy_lab.authoring.validation import _resolve_path


def _equity_max_drawdown(equity: list[float]) -> float:
    peak = 1.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1.0)
    return worst


def _profit_factor(returns: list[float]) -> float | None:
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    if losses:
        return sum(wins) / abs(sum(losses))
    return None


def _multi_leg_group_backtest_metrics(
    frame: pl.DataFrame, summary: dict[str, Any]
) -> dict[str, Any]:
    if frame.is_empty() or "multi_leg_group_id" not in frame.columns:
        return {
            "group_count": 0,
            "executed_group_count": 0,
            "complete_group_count": 0,
            "incomplete_group_count": 0,
            "expected_leg_count": 0,
            "executed_leg_count": 0,
            "total_return": 0.0,
            "avg_group_return": None,
            "win_rate": None,
            "worst_group_return": None,
            "max_drawdown": None,
            "profit_factor": None,
            "avg_leg_return_imbalance": None,
            "total_notional_usd": 0.0,
            "notional_weighted_total_return": None,
            "cost_drag_bps": 0.0,
            "groups": [],
        }

    expected_by_group: dict[str, list[dict[str, Any]]] = {}
    for row in frame.to_dicts():
        group_id = str(row.get("multi_leg_group_id") or "").strip()
        if not group_id:
            continue
        if str(row.get("side") or "").lower() not in {"long", "short"}:
            continue
        expected_by_group.setdefault(group_id, []).append(row)

    executed_by_group: dict[str, list[dict[str, Any]]] = {}
    for result in summary.get("executed_signal_results") or []:
        if not isinstance(result, dict):
            continue
        group_id = str(result.get("multi_leg_group_id") or "").strip()
        if not group_id:
            continue
        executed_by_group.setdefault(group_id, []).append(result)

    groups: list[dict[str, Any]] = []
    total_expected_legs = 0
    total_executed_legs = 0
    total_return = 0.0
    total_cost_drag_bps = 0.0
    total_notional_usd = 0.0
    total_notional_weighted_return = 0.0
    complete_count = 0
    executed_group_count = 0
    executed_group_returns: list[float] = []
    leg_return_imbalances: list[float] = []

    for group_id in sorted(expected_by_group):
        expected_rows = expected_by_group[group_id]
        executed_rows = executed_by_group.get(group_id, [])
        expected_counts = [
            int(value)
            for value in (row.get("multi_leg_leg_count") for row in expected_rows)
            if isinstance(value, int | float) and int(value) > 0
        ]
        expected_leg_count = max(expected_counts, default=len(expected_rows))
        executed_leg_count = len(executed_rows)
        leg_returns = [float(row.get("signal_return") or 0.0) for row in executed_rows]
        group_return = sum(leg_returns)
        leg_return_imbalance = (
            max(leg_returns) - min(leg_returns) if len(leg_returns) >= 2 else None
        )
        leg_notional_pairs = [
            (float(row.get("signal_return") or 0.0), float(row.get("notional_usd") or 0.0))
            for row in executed_rows
            if isinstance(row.get("notional_usd"), int | float)
            and float(row.get("notional_usd") or 0.0) > 0
        ]
        group_notional_usd = sum(notional for _signal_return, notional in leg_notional_pairs)
        group_notional_weighted_return = (
            sum(signal_return * notional for signal_return, notional in leg_notional_pairs)
            / group_notional_usd
            if group_notional_usd > 0
            else None
        )
        group_cost_drag_bps = sum(float(row.get("cost_drag_bps") or 0.0) for row in executed_rows)
        exit_reason_counts: dict[str, int] = {}
        for executed in executed_rows:
            _increment_count(exit_reason_counts, executed.get("exit_reason"))
        complete = executed_leg_count >= expected_leg_count
        if complete:
            complete_count += 1
        if executed_leg_count > 0:
            executed_group_count += 1
        total_expected_legs += expected_leg_count
        total_executed_legs += executed_leg_count
        total_return += group_return
        total_cost_drag_bps += group_cost_drag_bps
        total_notional_usd += group_notional_usd
        if group_notional_weighted_return is not None:
            total_notional_weighted_return += group_notional_weighted_return * group_notional_usd
        if executed_leg_count > 0:
            executed_group_returns.append(group_return)
        if leg_return_imbalance is not None:
            leg_return_imbalances.append(leg_return_imbalance)
        anchor = next(
            (
                str(row.get("multi_leg_anchor_real_market_symbol") or "").strip()
                for row in expected_rows
                if str(row.get("multi_leg_anchor_real_market_symbol") or "").strip()
            ),
            None,
        )
        groups.append(
            {
                "multi_leg_group_id": group_id,
                "anchor_real_market_symbol": anchor,
                "leg_count": len(expected_rows),
                "expected_leg_count": expected_leg_count,
                "executed_leg_count": executed_leg_count,
                "complete": complete,
                "total_return": group_return,
                "total_notional_usd": group_notional_usd,
                "notional_weighted_return": group_notional_weighted_return,
                "avg_leg_return": group_return / executed_leg_count if executed_leg_count else None,
                "leg_return_imbalance": leg_return_imbalance,
                "win": group_return > 0 if executed_leg_count else None,
                "cost_drag_bps": group_cost_drag_bps,
                "exit_reason_counts": dict(sorted(exit_reason_counts.items())),
            }
        )

    group_count = len(groups)
    equity = [1.0]
    for group_return in executed_group_returns:
        equity.append(equity[-1] * (1.0 + group_return))
    return {
        "group_count": group_count,
        "executed_group_count": executed_group_count,
        "complete_group_count": complete_count,
        "incomplete_group_count": group_count - complete_count,
        "expected_leg_count": total_expected_legs,
        "executed_leg_count": total_executed_legs,
        "total_return": total_return,
        "avg_group_return": (
            sum(executed_group_returns) / len(executed_group_returns)
            if executed_group_returns
            else None
        ),
        "win_rate": (
            sum(1 for group_return in executed_group_returns if group_return > 0)
            / len(executed_group_returns)
            if executed_group_returns
            else None
        ),
        "worst_group_return": min(executed_group_returns) if executed_group_returns else None,
        "max_drawdown": _equity_max_drawdown(equity) if executed_group_returns else None,
        "profit_factor": _profit_factor(executed_group_returns),
        "avg_leg_return_imbalance": (
            sum(leg_return_imbalances) / len(leg_return_imbalances)
            if leg_return_imbalances
            else None
        ),
        "total_notional_usd": total_notional_usd,
        "notional_weighted_total_return": (
            total_notional_weighted_return / total_notional_usd if total_notional_usd > 0 else None
        ),
        "cost_drag_bps": total_cost_drag_bps,
        "groups": groups,
    }


def _aggregate_backtest_metrics(metrics: list[Any]) -> dict[str, float | int | None]:
    if not metrics:
        return {
            "trade_count": 0,
            "total_return": 0.0,
            "max_drawdown": None,
            "cost_drag_bps": 0.0,
            "stale_rejected_count": 0,
            "halt_rejected_count": 0,
        }
    return {
        "trade_count": sum(item.trade_count for item in metrics),
        "total_return": sum(item.total_return for item in metrics),
        "max_drawdown": min(item.max_drawdown for item in metrics),
        "cost_drag_bps": sum(item.cost_drag_bps for item in metrics),
        "stale_rejected_count": sum(item.stale_rejected_count for item in metrics),
        "halt_rejected_count": sum(item.halt_rejected_count for item in metrics),
    }


def _era_key(value: object, era_unit: str) -> str:
    ts = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if era_unit == "month":
        return ts.strftime("%Y-%m")
    if era_unit == "week":
        year, week, _weekday = ts.isocalendar()
        return f"{year}-W{week:02d}"
    return ts.strftime("%Y-%m-%d")


def _walk_forward_eras(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> list[dict[str, Any]]:
    if frame.is_empty():
        return []
    eras: list[dict[str, Any]] = []
    for era in sorted(
        {_era_key(row["ts_signal"], spec.backtest.era_unit) for row in frame.to_dicts()}
    ):
        era_frame = frame.filter(
            pl.col("ts_signal").map_elements(
                lambda value: _era_key(value, spec.backtest.era_unit) == era,
                return_dtype=pl.Boolean,
            )
        )
        metrics, summary = _run_authoring_backtest_once(spec, era_frame, data_dir=data_dir)
        eras.append(
            {
                "era": era,
                "signal_count": era_frame.height,
                "aggregate_metrics": summary["aggregate_metrics"],
                "capital": summary["capital"],
                "multi_leg_group_metrics": summary["multi_leg_group_metrics"],
                "executed_count": summary.get("executed_count", 0),
            }
        )
    return eras


def _run_authoring_backtest_once(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> tuple[list[Any], dict[str, Any]]:
    quote_path = _resolve_path(spec.data.quote_data_path, data_dir)
    cost_path = _resolve_path(spec.data.cost_model_path, data_dir)
    signals = strategy_signals_to_research_signals(frame)
    metrics, _records, summary = run_backtest_bridge_for_signals(
        quote_path,
        signals,
        cost_matrix_path=cost_path if cost_path.exists() else None,
        exit_model="fixed_horizon",
        holding_horizon_minutes=spec.backtest.label_horizon_minutes,
    )
    aggregate_metrics = _aggregate_backtest_metrics(metrics)
    summary["authoring_split_method"] = spec.backtest.split_method
    summary["authoring_era_unit"] = spec.backtest.era_unit
    summary["min_trade_count"] = spec.backtest.min_trade_count
    summary["evaluation_window"] = evaluation_window(spec)
    summary["evaluation_signal_count"] = frame.height
    summary["aggregate_metrics"] = aggregate_metrics
    summary["capital"] = capital_metrics(spec, aggregate_metrics)
    summary["multi_leg_group_metrics"] = _multi_leg_group_backtest_metrics(frame, summary)
    threshold_results = _evaluate_pass_thresholds(spec, summary)
    pass_all_thresholds = all(bool(result["passed"]) for result in threshold_results.values())
    summary["pass_thresholds"] = threshold_results
    summary["pass_all_thresholds"] = pass_all_thresholds
    summary["pass_min_trade_count"] = (
        aggregate_metrics["trade_count"] or 0
    ) >= spec.backtest.min_trade_count
    summary["backtest_passed"] = summary["pass_min_trade_count"] and pass_all_thresholds
    return metrics, summary


def run_authoring_backtest(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> tuple[list[Any], dict[str, Any]]:
    source_frame = frame
    frame = apply_evaluation_window(spec, source_frame)
    metrics, summary = _run_authoring_backtest_once(spec, frame, data_dir=data_dir)
    summary.update(evaluation_counts(spec, source_frame, frame))
    if spec.backtest.split_method in {"walk_forward", "purged_walk_forward"}:
        summary["walk_forward_eras"] = _walk_forward_eras(spec, frame, data_dir=data_dir)
    variant_results = []
    for variant_id, variant in _optimizer_variants(spec):
        variant_frame, _manifest = build_authoring_signals(variant, data_dir=data_dir)
        variant_evaluation_frame = apply_evaluation_window(variant, variant_frame)
        _variant_metrics, variant_summary = _run_authoring_backtest_once(
            variant, variant_evaluation_frame, data_dir=data_dir
        )
        variant_results.append(
            {
                "variant_id": variant_id,
                "parameters": {
                    path: _nested_get(variant.model_dump(mode="json"), path)
                    for path in sorted(spec.optimizer.parameter_sweep)
                },
                **evaluation_counts(variant, variant_frame, variant_evaluation_frame),
                "aggregate_metrics": variant_summary["aggregate_metrics"],
                "capital": variant_summary["capital"],
                "multi_leg_group_metrics": variant_summary["multi_leg_group_metrics"],
                "backtest_passed": variant_summary["backtest_passed"],
            }
        )
    if variant_results:
        metric_name = spec.optimizer.selection_metric
        resolved_direction = _resolve_selection_direction(
            spec.optimizer.selection_direction, metric_name
        )
        reverse = resolved_direction == "maximize"
        ranked = sorted(
            variant_results,
            key=lambda item: _optimizer_sort_value(item, metric_name, maximize=reverse),
            reverse=reverse,
        )
        summary["optimizer"] = {
            "selection_metric": metric_name,
            "selection_direction": spec.optimizer.selection_direction,
            "resolved_selection_direction": resolved_direction,
            "variant_count": len(variant_results),
            "best_variant": ranked[0],
            "variants": ranked,
        }
    summary["strategy_scorecard"] = _strategy_scorecard(spec, frame, summary)
    return metrics, summary
