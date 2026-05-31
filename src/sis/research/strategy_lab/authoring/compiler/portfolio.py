from __future__ import annotations

import math
from typing import Any, Iterable

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _portfolio_turnover_weight_value,
    _position_weight_value,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import PortfolioRules
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_portfolio_allocation(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.allocation_method == "none":
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        target = _portfolio_target_total_position_weight(timestamp_rows, portfolio)
        if target is None:
            selected.extend(timestamp_rows)
            continue
        if portfolio.allocation_method in {
            "dollar_neutral",
            "beta_neutral",
            "group_neutral",
        }:
            selected.extend(
                _neutral_allocated_rows(
                    timestamp_rows,
                    target=target,
                    method=portfolio.allocation_method,
                )
            )
            continue
        raw_weights = _allocation_raw_weights(timestamp_rows, portfolio)
        total_raw = sum(raw_weights)
        for row, raw_weight in zip(timestamp_rows, raw_weights, strict=True):
            allocated = 0.0 if total_raw == 0.0 else target * raw_weight / total_raw
            updated = dict(row)
            updated["position_weight"] = allocated
            selected.append(updated)
    return selected


def _portfolio_target_total_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    column = portfolio.target_total_position_weight_column
    if column is None:
        return portfolio.target_total_position_weight
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.target_total_position_weight,
        value_key="_portfolio_target_total_position_weight",
        field_name="rules.portfolio.target_total_position_weight_column",
    )


def _portfolio_timestamp_limit(
    rows: list[dict[str, Any]],
    *,
    fixed: float | None,
    value_key: str,
    field_name: str,
) -> float | None:
    resolved: list[float] = []
    for row in rows:
        raw_value = row.get(value_key)
        value = float(raw_value) if isinstance(raw_value, int | float) else None
        if value is None:
            continue
        if value < 0:
            raise StrategyAuthoringValidationError(f"{field_name} must be >= 0")
        resolved.append(value)
    if not resolved:
        return fixed
    first = resolved[0]
    if any(not math.isclose(value, first, rel_tol=0.0, abs_tol=1e-12) for value in resolved[1:]):
        raise StrategyAuthoringValidationError(
            f"{field_name} must resolve to one value per timestamp"
        )
    return first


def _allocation_raw_weights(rows: list[dict[str, Any]], portfolio: PortfolioRules) -> list[float]:
    if portfolio.allocation_method == "equal_weight":
        return [1.0 for _row in rows]
    if portfolio.allocation_method == "score_proportional":
        raw_weights = [
            max(0.0, float(row["raw_score"]))
            if isinstance(row.get("raw_score"), int | float)
            else 0.0
            for row in rows
        ]
        return (
            raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]
        )
    raw_weights = [
        1.0 / float(row["_allocation_volatility"])
        if isinstance(row.get("_allocation_volatility"), int | float)
        and float(row["_allocation_volatility"]) > 0.0
        else 0.0
        for row in rows
    ]
    return raw_weights if any(weight > 0.0 for weight in raw_weights) else [1.0 for _row in rows]


def _neutral_allocated_rows(
    rows: list[dict[str, Any]], *, target: float, method: str
) -> list[dict[str, Any]]:
    if method == "group_neutral":
        group_rows: dict[str, list[dict[str, Any]]] = {}
        ungrouped: list[dict[str, Any]] = []
        for row in rows:
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append(row)
            else:
                ungrouped.append(row)
        group_target = target / len(group_rows) if group_rows else 0.0
        allocated: list[dict[str, Any]] = []
        for grouped_rows in group_rows.values():
            allocated.extend(
                _side_neutral_allocated_rows(
                    grouped_rows,
                    long_target=group_target / 2.0,
                    short_target=group_target / 2.0,
                )
            )
        allocated.extend(_side_neutral_allocated_rows(ungrouped, long_target=0.0, short_target=0.0))
        return allocated

    long_target = target / 2.0
    short_target = target / 2.0
    if method == "beta_neutral":
        long_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "long")
        short_beta = _weighted_average_abs_beta(row for row in rows if row.get("side") == "short")
        if long_beta > 0.0 and short_beta > 0.0:
            long_target = target * short_beta / (long_beta + short_beta)
            short_target = target * long_beta / (long_beta + short_beta)
    return _side_neutral_allocated_rows(rows, long_target=long_target, short_target=short_target)


def _weighted_average_abs_beta(rows: Iterable[dict[str, Any]]) -> float:
    weighted_beta = 0.0
    total_weight = 0.0
    for row in rows:
        beta = row.get("_allocation_beta")
        if not isinstance(beta, int | float):
            continue
        weight = abs(_position_weight_value(row))
        weighted_beta += abs(float(beta)) * weight
        total_weight += weight
    return 0.0 if total_weight == 0.0 else weighted_beta / total_weight


def _side_neutral_allocated_rows(
    rows: list[dict[str, Any]], *, long_target: float, short_target: float
) -> list[dict[str, Any]]:
    by_side = {
        "long": [row for row in rows if row.get("side") == "long"],
        "short": [row for row in rows if row.get("side") == "short"],
    }
    allocated: list[dict[str, Any]] = []
    for side, side_rows in by_side.items():
        side_target = long_target if side == "long" else short_target
        total_raw = sum(abs(_position_weight_value(row)) for row in side_rows)
        for row in side_rows:
            updated = dict(row)
            updated["position_weight"] = (
                0.0
                if total_raw == 0.0
                else side_target * abs(_position_weight_value(row)) / total_raw
            )
            allocated.append(updated)
    return allocated


def _apply_portfolio_turnover_budget(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if portfolio.max_turnover_weight_per_timestamp is None:
        return rows

    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        used_turnover = 0.0
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            turnover_weight = _portfolio_turnover_weight_value(row)
            if used_turnover + turnover_weight > portfolio.max_turnover_weight_per_timestamp:
                blocked_rows.append(
                    _block_trade_row(row, spec=spec, block_reason="portfolio_turnover_budget_limit")
                )
                continue
            used_turnover += turnover_weight
            accepted_rows.append(row)
        selected.extend([*blocked_rows, *accepted_rows])
    return selected


def _portfolio_exposure_block_reason(
    row: dict[str, Any],
    *,
    portfolio: PortfolioRules,
    max_total_position_weight: float | None,
    max_long_position_weight: float | None,
    max_short_position_weight: float | None,
    max_symbol_position_weight: float | None,
    max_group_position_weight: float | None,
    total_weight: float,
    long_weight: float,
    short_weight: float,
    symbol_weights: dict[str, float],
    group_weights: dict[str, float],
) -> str | None:
    weight = abs(_position_weight_value(row))
    side = str(row.get("side") or "")
    symbol = str(row.get("execution_symbol") or "")
    group = str(row.get("_portfolio_group") or "").strip()
    if max_total_position_weight is not None and total_weight + weight > max_total_position_weight:
        return "portfolio_total_exposure_limit"
    if side == "long" and max_long_position_weight is not None:
        if long_weight + weight > max_long_position_weight:
            return "portfolio_long_exposure_limit"
    if side == "short" and max_short_position_weight is not None:
        if short_weight + weight > max_short_position_weight:
            return "portfolio_short_exposure_limit"
    if max_symbol_position_weight is not None:
        if symbol_weights.get(symbol, 0.0) + weight > max_symbol_position_weight:
            return "portfolio_symbol_exposure_limit"
    if (
        max_group_position_weight is not None
        or portfolio.max_group_abs_net_position_weight is not None
        or portfolio.max_group_abs_net_position_weight_column is not None
    ):
        if not group:
            return "portfolio_group_missing"
    if max_group_position_weight is not None:
        if group_weights.get(group, 0.0) + weight > max_group_position_weight:
            return "portfolio_group_exposure_limit"
    return None


def _portfolio_max_long_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_long_position_weight,
        value_key="_portfolio_max_long_position_weight",
        field_name="rules.portfolio.max_long_position_weight_column",
    )


def _portfolio_max_short_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_short_position_weight,
        value_key="_portfolio_max_short_position_weight",
        field_name="rules.portfolio.max_short_position_weight_column",
    )


def _portfolio_max_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_abs_net_position_weight,
        value_key="_portfolio_max_abs_net_position_weight",
        field_name="rules.portfolio.max_abs_net_position_weight_column",
    )


def _portfolio_max_symbol_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_symbol_position_weight,
        value_key="_portfolio_max_symbol_position_weight",
        field_name="rules.portfolio.max_symbol_position_weight_column",
    )


def _portfolio_max_group_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_group_position_weight,
        value_key="_portfolio_max_group_position_weight",
        field_name="rules.portfolio.max_group_position_weight_column",
    )


def _portfolio_max_group_abs_net_position_weight(
    rows: list[dict[str, Any]], portfolio: PortfolioRules
) -> float | None:
    return _portfolio_timestamp_limit(
        rows,
        fixed=portfolio.max_group_abs_net_position_weight,
        value_key="_portfolio_max_group_abs_net_position_weight",
        field_name="rules.portfolio.max_group_abs_net_position_weight_column",
    )


def _apply_portfolio_exposure_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    portfolio = spec.rules.portfolio
    if not portfolio.exposure_limits_enabled:
        return rows
    grouped: dict[Any, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []
    for row in rows:
        if row.get("side") == "none":
            passthrough.append(row)
            continue
        grouped.setdefault(row["ts_signal"], []).append(row)

    selected: list[dict[str, Any]] = [*passthrough]
    for timestamp_rows in grouped.values():
        max_total_position_weight = _portfolio_timestamp_limit(
            timestamp_rows,
            fixed=portfolio.max_total_position_weight,
            value_key="_portfolio_max_total_position_weight",
            field_name="rules.portfolio.max_total_position_weight_column",
        )
        max_long_position_weight = _portfolio_max_long_position_weight(timestamp_rows, portfolio)
        max_short_position_weight = _portfolio_max_short_position_weight(timestamp_rows, portfolio)
        max_symbol_position_weight = _portfolio_max_symbol_position_weight(
            timestamp_rows, portfolio
        )
        max_group_position_weight = _portfolio_max_group_position_weight(timestamp_rows, portfolio)
        max_abs_net_position_weight = _portfolio_max_abs_net_position_weight(
            timestamp_rows, portfolio
        )
        max_group_abs_net_position_weight = _portfolio_max_group_abs_net_position_weight(
            timestamp_rows, portfolio
        )
        total_weight = 0.0
        long_weight = 0.0
        short_weight = 0.0
        symbol_weights: dict[str, float] = {}
        group_weights: dict[str, float] = {}
        accepted_rows: list[dict[str, Any]] = []
        blocked_rows: list[dict[str, Any]] = []
        for row in sorted(
            timestamp_rows,
            key=lambda item: item.get("rank_score") if item.get("rank_score") is not None else -1.0,
            reverse=True,
        ):
            reason = _portfolio_exposure_block_reason(
                row,
                portfolio=portfolio,
                max_total_position_weight=max_total_position_weight,
                max_long_position_weight=max_long_position_weight,
                max_short_position_weight=max_short_position_weight,
                max_symbol_position_weight=max_symbol_position_weight,
                max_group_position_weight=max_group_position_weight,
                total_weight=total_weight,
                long_weight=long_weight,
                short_weight=short_weight,
                symbol_weights=symbol_weights,
                group_weights=group_weights,
            )
            if reason is not None:
                blocked_rows.append(_block_trade_row(row, spec=spec, block_reason=reason))
                continue
            weight = abs(_position_weight_value(row))
            total_weight += weight
            if row.get("side") == "long":
                long_weight += weight
            elif row.get("side") == "short":
                short_weight += weight
            symbol = str(row.get("execution_symbol") or "")
            symbol_weights[symbol] = symbol_weights.get(symbol, 0.0) + weight
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_weights[group] = group_weights.get(group, 0.0) + weight
            accepted_rows.append(row)
        accepted_rows, net_blocked_rows = _apply_portfolio_net_exposure_limit(
            accepted_rows,
            max_abs_net_position_weight=max_abs_net_position_weight,
            spec=spec,
        )
        accepted_rows, group_net_blocked_rows = _apply_portfolio_group_net_exposure_limit(
            accepted_rows,
            max_group_abs_net_position_weight=max_group_abs_net_position_weight,
            spec=spec,
        )
        selected.extend([*blocked_rows, *net_blocked_rows, *group_net_blocked_rows, *accepted_rows])
    return selected


def _apply_portfolio_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        long_weight = sum(
            abs(_position_weight_value(row)) for row in accepted if row.get("side") == "long"
        )
        short_weight = sum(
            abs(_position_weight_value(row)) for row in accepted if row.get("side") == "short"
        )
        net_weight = long_weight - short_weight
        if abs(net_weight) <= max_abs_net_position_weight:
            return accepted, blocked

        overweight_side = "long" if net_weight > 0 else "short"
        candidates = [
            (index, row) for index, row in enumerate(accepted) if row.get("side") == overweight_side
        ]
        if not candidates:
            return accepted, blocked

        remove_index, row = min(
            candidates,
            key=lambda item: (
                item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
                item[0],
            ),
        )
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_net_exposure_limit")
        )
        accepted.pop(remove_index)


def _apply_portfolio_group_net_exposure_limit(
    rows: list[dict[str, Any]],
    *,
    max_group_abs_net_position_weight: float | None,
    spec: StrategyAuthoringSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if max_group_abs_net_position_weight is None:
        return rows, []

    accepted = [*rows]
    blocked: list[dict[str, Any]] = []
    while True:
        group_rows: dict[str, list[tuple[int, dict[str, Any]]]] = {}
        for index, row in enumerate(accepted):
            group = str(row.get("_portfolio_group") or "").strip()
            if group:
                group_rows.setdefault(group, []).append((index, row))

        over_limit: tuple[str, float] | None = None
        for group, indexed_rows in group_rows.items():
            long_weight = sum(
                abs(_position_weight_value(row))
                for _index, row in indexed_rows
                if row.get("side") == "long"
            )
            short_weight = sum(
                abs(_position_weight_value(row))
                for _index, row in indexed_rows
                if row.get("side") == "short"
            )
            net_weight = long_weight - short_weight
            if abs(net_weight) > max_group_abs_net_position_weight:
                over_limit = (group, net_weight)
                break
        if over_limit is None:
            return accepted, blocked

        group, net_weight = over_limit
        overweight_side = "long" if net_weight > 0 else "short"
        candidates = [
            (index, row)
            for index, row in enumerate(accepted)
            if row.get("side") == overweight_side
            and str(row.get("_portfolio_group") or "").strip() == group
        ]
        if not candidates:
            return accepted, blocked

        remove_index, row = min(
            candidates,
            key=lambda item: (
                item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
                item[0],
            ),
        )
        blocked.append(
            _block_trade_row(row, spec=spec, block_reason="portfolio_group_net_exposure_limit")
        )
        accepted.pop(remove_index)
