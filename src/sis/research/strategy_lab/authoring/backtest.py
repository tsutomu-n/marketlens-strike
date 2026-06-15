from __future__ import annotations

import json
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any, Literal, cast

import polars as pl

from sis.backtest.bridge import run_backtest_bridge_for_signals
from sis.research.strategy_lab.authoring.compiler.artifacts import (
    strategy_signals_to_research_signals,
)
from sis.research.strategy_lab.authoring.compiler.build import build_authoring_signals
from sis.research.strategy_lab.authoring.contracts.base import (
    StrategyAuthoringValidationError,
    _stable_digest,
)
from sis.research.strategy_lab.authoring.contracts.spec import (
    StrategyAuthoringBundleSpec,
    StrategyAuthoringSpec,
)
from sis.research.strategy_lab.authoring.evaluation_window import (
    apply_evaluation_window,
    capital_metrics,
    evaluation_counts,
    evaluation_window,
)
from sis.research.strategy_lab.authoring.scorecard import (
    _increment_count,
    _metrics_json,
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


def _aggregate_bundle_multi_leg_group_metrics(
    members: list[dict[str, Any]],
) -> dict[str, float | int | None]:
    group_metrics = [
        (member, member["summary"].get("multi_leg_group_metrics"))
        for member in members
        if isinstance(member["summary"].get("multi_leg_group_metrics"), dict)
        and int(member["summary"]["multi_leg_group_metrics"].get("group_count") or 0) > 0
    ]
    if not group_metrics:
        return {
            "member_count": 0,
            "group_count": 0,
            "executed_group_count": 0,
            "complete_group_count": 0,
            "incomplete_group_count": 0,
            "expected_leg_count": 0,
            "executed_leg_count": 0,
            "weighted_total_return": 0.0,
            "weighted_cost_drag_bps": 0.0,
            "weighted_avg_group_return": None,
            "weighted_win_rate": None,
            "worst_group_return": None,
            "weighted_max_drawdown": None,
            "weighted_profit_factor": None,
            "weighted_avg_leg_return_imbalance": None,
            "total_notional_usd": 0.0,
            "weighted_notional_return": None,
        }

    weighted_total_return = 0.0
    weighted_cost_drag_bps = 0.0
    total_notional_usd = 0.0
    weighted_avg_group_return_values: list[float] = []
    weighted_win_rate_values: list[float] = []
    weighted_drawdowns: list[float] = []
    weighted_profit_factors: list[float] = []
    weighted_leg_return_imbalances: list[float] = []
    weighted_notional_returns: list[float] = []
    worst_group_returns: list[float] = []
    totals = {
        "member_count": len(group_metrics),
        "group_count": 0,
        "executed_group_count": 0,
        "complete_group_count": 0,
        "incomplete_group_count": 0,
        "expected_leg_count": 0,
        "executed_leg_count": 0,
    }
    for member, metrics in group_metrics:
        weight = float(member["effective_allocation_weight"])
        totals["group_count"] += int(metrics.get("group_count") or 0)
        totals["executed_group_count"] += int(metrics.get("executed_group_count") or 0)
        totals["complete_group_count"] += int(metrics.get("complete_group_count") or 0)
        totals["incomplete_group_count"] += int(metrics.get("incomplete_group_count") or 0)
        totals["expected_leg_count"] += int(metrics.get("expected_leg_count") or 0)
        totals["executed_leg_count"] += int(metrics.get("executed_leg_count") or 0)
        weighted_total_return += float(metrics.get("total_return") or 0.0) * weight
        weighted_cost_drag_bps += float(metrics.get("cost_drag_bps") or 0.0) * weight
        total_notional_usd += float(metrics.get("total_notional_usd") or 0.0)
        if metrics.get("avg_group_return") is not None:
            weighted_avg_group_return_values.append(float(metrics["avg_group_return"]) * weight)
        if metrics.get("win_rate") is not None:
            weighted_win_rate_values.append(float(metrics["win_rate"]) * weight)
        if metrics.get("worst_group_return") is not None:
            worst_group_returns.append(float(metrics["worst_group_return"]) * weight)
        if metrics.get("max_drawdown") is not None:
            weighted_drawdowns.append(float(metrics["max_drawdown"]) * weight)
        if metrics.get("profit_factor") is not None:
            weighted_profit_factors.append(float(metrics["profit_factor"]) * weight)
        if metrics.get("avg_leg_return_imbalance") is not None:
            weighted_leg_return_imbalances.append(
                float(metrics["avg_leg_return_imbalance"]) * weight
            )
        if metrics.get("notional_weighted_total_return") is not None:
            weighted_notional_returns.append(
                float(metrics["notional_weighted_total_return"]) * weight
            )

    return {
        **totals,
        "weighted_total_return": weighted_total_return,
        "weighted_cost_drag_bps": weighted_cost_drag_bps,
        "weighted_avg_group_return": (
            sum(weighted_avg_group_return_values) if weighted_avg_group_return_values else None
        ),
        "weighted_win_rate": sum(weighted_win_rate_values) if weighted_win_rate_values else None,
        "worst_group_return": min(worst_group_returns) if worst_group_returns else None,
        "weighted_max_drawdown": min(weighted_drawdowns) if weighted_drawdowns else None,
        "weighted_profit_factor": (
            sum(weighted_profit_factors) if weighted_profit_factors else None
        ),
        "weighted_avg_leg_return_imbalance": (
            sum(weighted_leg_return_imbalances) if weighted_leg_return_imbalances else None
        ),
        "total_notional_usd": total_notional_usd,
        "weighted_notional_return": (
            sum(weighted_notional_returns) if weighted_notional_returns else None
        ),
    }


def _aggregate_bundle_metrics(members: list[dict[str, Any]]) -> dict[str, Any]:
    if not members:
        return {
            "member_count": 0,
            "trade_count": 0,
            "weighted_total_return": 0.0,
            "max_drawdown": None,
            "cost_drag_bps": 0.0,
            "multi_leg_group_metrics": _aggregate_bundle_multi_leg_group_metrics([]),
        }
    weighted_total_return = 0.0
    max_drawdowns: list[float] = []
    trade_count = 0
    cost_drag_bps = 0.0
    for member in members:
        weight = float(member["effective_allocation_weight"])
        metrics = member["summary"]["aggregate_metrics"]
        weighted_total_return += float(metrics.get("total_return") or 0.0) * weight
        if metrics.get("max_drawdown") is not None:
            max_drawdowns.append(float(metrics["max_drawdown"]) * weight)
        trade_count += int(metrics.get("trade_count") or 0)
        cost_drag_bps += float(metrics.get("cost_drag_bps") or 0.0) * weight
    return {
        "member_count": len(members),
        "trade_count": trade_count,
        "weighted_total_return": weighted_total_return,
        "max_drawdown": min(max_drawdowns) if max_drawdowns else None,
        "cost_drag_bps": cost_drag_bps,
        "multi_leg_group_metrics": _aggregate_bundle_multi_leg_group_metrics(members),
    }


def _cap_bundle_weights(
    raw_weights: dict[int, float], max_total_allocation_weight: float | None
) -> dict[int, float]:
    total = sum(raw_weights.values())
    if total <= 0:
        return {index: 0.0 for index in raw_weights}
    scale = (
        min(1.0, max_total_allocation_weight / total)
        if max_total_allocation_weight is not None
        else 1.0
    )
    return {index: weight * scale for index, weight in raw_weights.items()}


def _risk_parity_risk_value(member: dict[str, Any]) -> float:
    metrics = member["summary"]["aggregate_metrics"]
    drawdown = metrics.get("max_drawdown")
    if drawdown is None:
        return 1.0
    return max(abs(float(drawdown)), 0.0001)


def _bundle_effective_weights(
    bundle: StrategyAuthoringBundleSpec, member_results: list[dict[str, Any]]
) -> dict[int, float]:
    if not member_results:
        return {}
    if bundle.portfolio.allocation_method == "equal_weight":
        raw = {int(member["member_index"]): 1.0 / len(member_results) for member in member_results}
    elif bundle.portfolio.allocation_method == "risk_parity":
        inverse_risk = {
            int(member["member_index"]): 1.0 / _risk_parity_risk_value(member)
            for member in member_results
        }
        total_inverse = sum(inverse_risk.values())
        raw = {
            index: (weight / total_inverse if total_inverse > 0 else 0.0)
            for index, weight in inverse_risk.items()
        }
    else:
        raw = {
            index: member.allocation_weight
            for index, member in enumerate(bundle.members)
            if member.enabled
        }
    return _cap_bundle_weights(raw, bundle.portfolio.max_total_allocation_weight)


def _threshold_actual(summary: dict[str, Any], metric_name: str) -> float | int | None:
    aggregate_metrics = summary.get("aggregate_metrics")
    if isinstance(aggregate_metrics, dict) and metric_name in aggregate_metrics:
        value = aggregate_metrics.get(metric_name)
    else:
        current: Any = summary
        for part in metric_name.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        value = current
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        return value
    return None


def _threshold_passes(metric_name: str, actual: float | int | None, threshold: float) -> bool:
    if actual is None:
        return False
    if _metric_lower_is_better(metric_name):
        return float(actual) <= threshold
    return float(actual) >= threshold


def _metric_lower_is_better(metric_name: str) -> bool:
    lower_is_better = {
        "cost_drag_bps",
        "stale_rejected_count",
        "halt_rejected_count",
        "blocked_count",
        "no_signal_count",
        "entry_order_unfilled_count",
        "multi_leg_group_metrics.incomplete_group_count",
        "multi_leg_group_metrics.cost_drag_bps",
    }
    if metric_name in lower_is_better:
        return True
    leaf = metric_name.rsplit(".", maxsplit=1)[-1]
    lower_leaf_suffixes = (
        "_cost_bps",
        "_drag_bps",
        "_imbalance",
        "_imbalance_bps",
        "_rejected_count",
        "_blocked_count",
        "_unfilled_count",
    )
    return leaf.endswith(lower_leaf_suffixes) or leaf.startswith(("incomplete_", "rejected_"))


def _resolve_selection_direction(
    direction: str, metric_name: str
) -> Literal["maximize", "minimize"]:
    if direction == "auto":
        return "minimize" if _metric_lower_is_better(metric_name) else "maximize"
    if direction in {"maximize", "minimize"}:
        return cast(Literal["maximize", "minimize"], direction)
    raise StrategyAuthoringValidationError(f"unsupported selection_direction: {direction}")


def _evaluate_pass_thresholds(
    spec: StrategyAuthoringSpec, summary: dict[str, Any]
) -> dict[str, dict[str, float | int | bool | None]]:
    results: dict[str, dict[str, float | int | bool | None]] = {}
    for metric_name, threshold in spec.backtest.pass_thresholds.items():
        actual = _threshold_actual(summary, metric_name)
        results[metric_name] = {
            "actual": actual,
            "threshold": threshold,
            "passed": _threshold_passes(metric_name, actual, threshold),
        }
    return results


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
                "multi_leg_group_metrics": summary["multi_leg_group_metrics"],
                "executed_count": summary.get("executed_count", 0),
            }
        )
    return eras


def _set_path(payload: dict[str, Any], dotted_path: str, value: float | int | str) -> None:
    current: dict[str, Any] = payload
    parts = dotted_path.split(".")
    for part in parts[:-1]:
        next_item = current.setdefault(part, {})
        if not isinstance(next_item, dict):
            raise StrategyAuthoringValidationError(f"Cannot set optimizer path: {dotted_path}")
        current = next_item
    current[parts[-1]] = value


def _nested_get(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _optimizer_sort_value(item: dict[str, Any], metric_name: str, *, maximize: bool) -> float:
    value = _threshold_actual(item, metric_name)
    if value is None:
        return float("-inf") if maximize else float("inf")
    return float(value)


def _optimizer_variants(spec: StrategyAuthoringSpec) -> list[tuple[str, StrategyAuthoringSpec]]:
    sweep = spec.optimizer.parameter_sweep
    if not sweep:
        return []
    paths = sorted(sweep)
    combinations = list(product(*(sweep[path] for path in paths)))
    if len(combinations) > spec.optimizer.max_variants:
        raise StrategyAuthoringValidationError(
            f"optimizer variants exceed max_variants: {len(combinations)} > {spec.optimizer.max_variants}"
        )
    variants: list[tuple[str, StrategyAuthoringSpec]] = []
    base_payload = spec.model_dump(mode="json")
    for index, values in enumerate(combinations):
        payload = json.loads(json.dumps(base_payload))
        payload["optimizer"]["parameter_sweep"] = {}
        parameters = dict(zip(paths, values, strict=True))
        for path, value in parameters.items():
            _set_path(payload, path, value)
        variant = StrategyAuthoringSpec.model_validate(payload)
        variants.append((f"variant-{index:03d}-{_stable_digest(parameters)}", variant))
    return variants


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


def write_authoring_backtest_outputs(
    spec: StrategyAuthoringSpec, metrics: list[Any], summary: dict[str, Any], *, data_dir: Path
) -> dict[str, Path]:
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    report_path = data_dir / "reports/strategy_backtest_report.md"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _metrics_json(metrics, summary, spec)
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {item.venue} | {item.canonical_symbol} | {item.trade_count} | {item.total_return:.6f} | {item.max_drawdown:.6f} | {item.cost_drag_bps:.2f} |"
        for item in metrics
    )
    scorecard = summary.get("strategy_scorecard") or {}
    capital = summary.get("capital") or {}
    scorecard_lines = (
        "\n".join(
            f"- {name}: {count}"
            for name, count in (scorecard.get("derived_feature_ops") or {}).items()
        )
        or "- none"
    )
    block_reason_lines = (
        "\n".join(
            f"- {name}: {count}"
            for name, count in (scorecard.get("block_reason_counts") or {}).items()
        )
        or "- none"
    )
    report_path.write_text(
        "# Strategy Authoring Backtest Report\n\n"
        "paper_only: true\n\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- source_signal_count: {summary.get('source_signal_count')}\n"
        f"- evaluation_signal_count: {summary.get('evaluation_signal_count')}\n"
        f"- evaluation_start_at: {summary.get('evaluation_window', {}).get('evaluation_start_at')}\n"
        f"- evaluation_end_at: {summary.get('evaluation_window', {}).get('evaluation_end_at')}\n"
        f"- signals_considered: {summary.get('signals_considered')}\n"
        f"- executed_count: {summary.get('executed_count')}\n"
        f"- pass_min_trade_count: {summary.get('pass_min_trade_count')}\n\n"
        f"- pass_all_thresholds: {summary.get('pass_all_thresholds')}\n"
        f"- backtest_passed: {summary.get('backtest_passed')}\n\n"
        "## Capital\n\n"
        f"- initial_capital_usd: {capital.get('initial_capital_usd')}\n"
        f"- net_pnl_usd: {capital.get('net_pnl_usd')}\n"
        f"- ending_equity_usd: {capital.get('ending_equity_usd')}\n"
        f"- max_drawdown_loss_usd: {capital.get('max_drawdown_loss_usd')}\n\n"
        "## Strategy Scorecard\n\n"
        f"- derived_feature_count: {scorecard.get('derived_feature_count', 0)}\n"
        f"- failed_thresholds: {scorecard.get('failed_thresholds', [])}\n\n"
        "### Derived Feature Ops\n\n"
        f"{scorecard_lines}\n\n"
        "### Signal Block Reasons\n\n"
        f"{block_reason_lines}\n\n"
        "| Venue | Symbol | Trades | Total Return | Max Drawdown | Cost Drag bps |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"metrics": metrics_path, "report": report_path}
