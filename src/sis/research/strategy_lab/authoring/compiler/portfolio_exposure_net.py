from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _position_weight_value,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


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
