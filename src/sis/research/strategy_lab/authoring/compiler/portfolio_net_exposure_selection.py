from __future__ import annotations

from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.portfolio_weight_values import (
    _position_weight_value,
)


def _net_position_weight(rows: list[dict[str, Any]]) -> float:
    long_weight = sum(abs(_position_weight_value(row)) for row in rows if row.get("side") == "long")
    short_weight = sum(
        abs(_position_weight_value(row)) for row in rows if row.get("side") == "short"
    )
    return long_weight - short_weight


def _overweight_side(net_weight: float) -> Literal["long", "short"]:
    return "long" if net_weight > 0 else "short"


def _lowest_rank_overweight_candidate(
    rows: list[dict[str, Any]],
    *,
    side: str,
    group: str | None = None,
) -> tuple[int, dict[str, Any]] | None:
    candidates = [
        (index, row)
        for index, row in enumerate(rows)
        if row.get("side") == side
        and (group is None or str(row.get("_portfolio_group") or "").strip() == group)
    ]
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            item[1].get("rank_score") if item[1].get("rank_score") is not None else -1.0,
            item[0],
        ),
    )


def _first_over_limit_group_net_weight(
    rows: list[dict[str, Any]], max_group_abs_net_position_weight: float
) -> tuple[str, float] | None:
    group_rows: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        group = str(row.get("_portfolio_group") or "").strip()
        if group:
            group_rows.setdefault(group, []).append(row)

    for group, indexed_rows in group_rows.items():
        net_weight = _net_position_weight(indexed_rows)
        if abs(net_weight) > max_group_abs_net_position_weight:
            return group, net_weight
    return None
