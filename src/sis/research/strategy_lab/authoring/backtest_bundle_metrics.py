from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringBundleSpec


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
