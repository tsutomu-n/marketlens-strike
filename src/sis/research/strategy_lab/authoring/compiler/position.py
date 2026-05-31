from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _compiled_signal_id,
    _position_weight_value,
    _signal_timestamp,
)
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _apply_position_state_limits(
    rows: list[dict[str, Any]], spec: StrategyAuthoringSpec
) -> list[dict[str, Any]]:
    position = spec.rules.position
    if (
        not position.enabled
        and not spec.rules.order.reduce_only
        and spec.rules.order.reduce_only_column is None
    ):
        return rows

    horizon_minutes = position.holding_horizon_minutes or spec.backtest.label_horizon_minutes
    active_by_symbol: dict[str, list[tuple[datetime, str, float]]] = {}
    selected: list[dict[str, Any]] = []

    def compact_active(
        active: list[tuple[datetime, str, float]], weight: float
    ) -> list[tuple[datetime, str, float]]:
        if weight <= 0:
            return []
        end_at = max(
            (item_end_at for item_end_at, _item_side, _item_weight in active), default=None
        )
        if end_at is None:
            return []
        sides = [item_side for _item_end_at, item_side, item_weight in active if item_weight > 0]
        side = sides[0] if sides else "long"
        return [(end_at, side, weight)]

    def reduce_active_side(
        active: list[tuple[datetime, str, float]], side: str, fraction: float
    ) -> list[tuple[datetime, str, float]]:
        total = sum(weight for _end_at, active_side, weight in active if active_side == side)
        to_reduce = total * min(max(fraction, 0.0), 1.0)
        updated: list[tuple[datetime, str, float]] = []
        for end_at, active_side, weight in active:
            if active_side != side or to_reduce <= 0:
                updated.append((end_at, active_side, weight))
                continue
            reduced = min(weight, to_reduce)
            remaining = weight - reduced
            to_reduce -= reduced
            if remaining > 0:
                updated.append((end_at, active_side, remaining))
        return updated

    for row in sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"])):
        if row.get("side") == "none":
            selected.append(row)
            continue

        ts_signal = _signal_timestamp(row)
        symbol = str(row["execution_symbol"])
        active = [
            (end_at, active_side, weight)
            for end_at, active_side, weight in active_by_symbol.get(symbol, [])
            if end_at > ts_signal
        ]
        active_by_symbol[symbol] = active
        open_weight = sum(weight for _end_at, _active_side, weight in active)
        side = str(row.get("side") or "")

        if side in {"close", "reduce", "add", "rebalance"}:
            if position.require_open_position_for_markers and open_weight <= 0:
                selected.append(
                    _block_trade_row(row, spec=spec, block_reason="position_marker_without_open")
                )
                continue
            if side == "close":
                active_by_symbol[symbol] = []
            elif side == "reduce" and open_weight > 0:
                reduce_fraction = row.get("reduce_fraction")
                fraction = (
                    min(max(float(reduce_fraction), 0.0), 1.0)
                    if isinstance(reduce_fraction, int | float)
                    else 1.0
                )
                active_by_symbol[symbol] = compact_active(active, open_weight * (1.0 - fraction))
            elif side == "add" and open_weight > 0:
                add_fraction = row.get("add_fraction")
                added_weight = (
                    max(float(add_fraction), 0.0) if isinstance(add_fraction, int | float) else 1.0
                )
                if (
                    position.max_open_position_weight_per_symbol is not None
                    and open_weight + added_weight > position.max_open_position_weight_per_symbol
                ):
                    selected.append(
                        _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
                    )
                    continue
                active_by_symbol[symbol] = compact_active(active, open_weight + added_weight)
            elif side == "rebalance" and open_weight > 0:
                target_fraction = row.get("rebalance_target_fraction")
                target_weight = (
                    max(float(target_fraction), 0.0)
                    if isinstance(target_fraction, int | float)
                    else open_weight
                )
                if (
                    position.max_open_position_weight_per_symbol is not None
                    and target_weight > position.max_open_position_weight_per_symbol
                ):
                    selected.append(
                        _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
                    )
                    continue
                active_by_symbol[symbol] = compact_active(active, target_weight)
            selected.append(row)
            continue

        weight = abs(_position_weight_value(row))
        if row.get("entry_reduce_only") and side in {"long", "short"}:
            opposing_side = "short" if side == "long" else "long"
            opposing_weight = sum(
                active_weight
                for _end_at, active_side, active_weight in active
                if active_side == opposing_side
            )
            if opposing_weight <= 0:
                selected.append(
                    _block_trade_row(
                        row, spec=spec, block_reason="position_reduce_only_without_opposing_open"
                    )
                )
                continue
            reduce_fraction = row.get("reduce_fraction")
            fraction = (
                min(max(float(reduce_fraction), 0.0), 1.0)
                if isinstance(reduce_fraction, int | float)
                else 1.0
            )
            active_by_symbol[symbol] = reduce_active_side(active, opposing_side, fraction)
            reduce_row = dict(row)
            reduce_row["side"] = "reduce"
            reduce_row["signal_id"] = _compiled_signal_id(spec, reduce_row, side="reduce")
            reduce_row["position_weight"] = 0.0
            reduce_row["notional_usd"] = None
            reduce_row["reason_codes"] = [*list(row.get("reason_codes") or []), "reduce_only"]
            selected.append(reduce_row)
            continue
        if not position.allow_opposing_open_positions and side in {"long", "short"}:
            opposing_side = "short" if side == "long" else "long"
            opposing_weight = sum(
                active_weight
                for _end_at, active_side, active_weight in active
                if active_side == opposing_side
            )
            if opposing_weight > 0:
                selected.append(
                    _block_trade_row(row, spec=spec, block_reason="position_opposing_open_position")
                )
                continue
        if not position.allow_pyramiding and side in {"long", "short"}:
            same_side_weight = sum(
                active_weight
                for _end_at, active_side, active_weight in active
                if active_side == side
            )
            if same_side_weight > 0:
                selected.append(
                    _block_trade_row(row, spec=spec, block_reason="position_pyramiding_not_allowed")
                )
                continue

        if (
            position.max_open_signals_per_symbol is not None
            and len(active) >= position.max_open_signals_per_symbol
        ):
            selected.append(
                _block_trade_row(row, spec=spec, block_reason="position_open_signal_limit")
            )
            continue
        if (
            position.max_open_position_weight_per_symbol is not None
            and open_weight + weight > position.max_open_position_weight_per_symbol
        ):
            selected.append(
                _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
            )
            continue

        active.append((ts_signal + timedelta(minutes=horizon_minutes), side, weight))
        active_by_symbol[symbol] = active
        selected.append(row)
    return selected
