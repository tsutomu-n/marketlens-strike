from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
    _position_weight_value,
    _signal_timestamp,
)
from sis.research.strategy_lab.authoring.compiler.position_state import (
    _clamped_position_fraction,
    _compact_active_positions,
    _non_negative_position_value,
    _reduce_active_side,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
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
                fraction = _clamped_position_fraction(row.get("reduce_fraction"))
                active_by_symbol[symbol] = _compact_active_positions(
                    active, open_weight * (1.0 - fraction)
                )
            elif side == "add" and open_weight > 0:
                added_weight = _non_negative_position_value(row.get("add_fraction"), default=1.0)
                if (
                    position.max_open_position_weight_per_symbol is not None
                    and open_weight + added_weight > position.max_open_position_weight_per_symbol
                ):
                    selected.append(
                        _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
                    )
                    continue
                active_by_symbol[symbol] = _compact_active_positions(
                    active, open_weight + added_weight
                )
            elif side == "rebalance" and open_weight > 0:
                target_weight = _non_negative_position_value(
                    row.get("rebalance_target_fraction"), default=open_weight
                )
                if (
                    position.max_open_position_weight_per_symbol is not None
                    and target_weight > position.max_open_position_weight_per_symbol
                ):
                    selected.append(
                        _block_trade_row(row, spec=spec, block_reason="position_open_weight_limit")
                    )
                    continue
                active_by_symbol[symbol] = _compact_active_positions(active, target_weight)
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
            fraction = _clamped_position_fraction(row.get("reduce_fraction"))
            active_by_symbol[symbol] = _reduce_active_side(active, opposing_side, fraction)
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
