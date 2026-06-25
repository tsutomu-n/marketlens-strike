from __future__ import annotations

from typing import Any, Iterable

from sis.research.strategy_lab.authoring.compiler.common import _position_weight_value


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
