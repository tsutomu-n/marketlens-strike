from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.compiler.trade_blocking import _block_trade_row


def _apply_stop_target_width_gate(
    row: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, Any]:
    stop_loss_bps = row.get("stop_loss_bps")
    take_profit_bps = row.get("take_profit_bps")
    min_stop = row.get("min_stop_loss_bps")
    max_stop = row.get("max_stop_loss_bps")
    min_take = row.get("min_take_profit_bps")
    max_take = row.get("max_take_profit_bps")

    if row.get("side") not in {"long", "short"}:
        return row

    if min_stop is not None and max_stop is not None and float(max_stop) < float(min_stop):
        raise StrategyAuthoringValidationError(
            "rules.exit.max_stop_loss_bps must be >= min_stop_loss_bps"
        )
    if min_take is not None and max_take is not None and float(max_take) < float(min_take):
        raise StrategyAuthoringValidationError(
            "rules.exit.max_take_profit_bps must be >= min_take_profit_bps"
        )

    if min_stop is not None or max_stop is not None:
        if stop_loss_bps is None:
            return _block_trade_row(row, spec=spec, block_reason="stop_loss_bps_missing")
        stop = float(stop_loss_bps)
        if min_stop is not None and stop < float(min_stop):
            return _block_trade_row(row, spec=spec, block_reason="stop_loss_bps_too_low")
        if max_stop is not None and stop > float(max_stop):
            return _block_trade_row(row, spec=spec, block_reason="stop_loss_bps_too_high")

    if min_take is not None or max_take is not None:
        if take_profit_bps is None:
            return _block_trade_row(row, spec=spec, block_reason="take_profit_bps_missing")
        take = float(take_profit_bps)
        if min_take is not None and take < float(min_take):
            return _block_trade_row(row, spec=spec, block_reason="take_profit_bps_too_low")
        if max_take is not None and take > float(max_take):
            return _block_trade_row(row, spec=spec, block_reason="take_profit_bps_too_high")

    return row
