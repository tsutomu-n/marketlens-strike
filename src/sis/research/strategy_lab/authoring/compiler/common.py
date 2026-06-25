from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.signal_ids import _compiled_signal_id
from sis.research.strategy_lab.authoring.compiler.signal_selection import _entry_passes
from sis.research.strategy_lab.authoring.compiler.trade_block_neutral_fields import (
    _blocked_trade_neutral_fields,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.multi_leg import RegimeOverride
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _matching_regime_override(
    row: dict[str, Any], spec: StrategyAuthoringSpec
) -> RegimeOverride | None:
    for regime in spec.rules.regime_overrides:
        if _entry_passes(row, regime.when):
            return regime
    return None


def _regime_value(
    regime: RegimeOverride | None, field_name: str, default: float | None
) -> float | None:
    if regime is None:
        return default
    value = getattr(regime, field_name)
    return value if value is not None else default


def _exit_override(
    overrides: dict[str, float | None] | None, field_name: str, default: float | None
) -> float | None:
    if overrides is None:
        return default
    value = overrides.get(field_name)
    return value if value is not None else default


def _exit_override_column(
    overrides: dict[str, float | None] | None, field_name: str, default: str | None
) -> str | None:
    if overrides is not None and field_name in overrides:
        return None
    return default


def _override_value(overrides: dict[str, Any] | None, field_name: str, default: Any) -> Any:
    if overrides is None:
        return default
    value = overrides.get(field_name)
    return value if value is not None else default


def _override_column(
    overrides: dict[str, Any] | None, field_name: str, default: str | None
) -> str | None:
    if overrides is not None and field_name in overrides:
        return None
    return default


def _block_trade_row(
    row: dict[str, Any],
    *,
    spec: StrategyAuthoringSpec,
    block_reason: str,
) -> dict[str, Any]:
    blocked = dict(row)
    blocked["side"] = "none"
    blocked["signal_id"] = _compiled_signal_id(spec, blocked, side="none")
    blocked["confidence"] = 0.0
    blocked.update(_blocked_trade_neutral_fields(row))
    blocked["reason_codes"] = [spec.rules.hold_reason_code]
    blocked["block_reasons"] = [*list(row.get("block_reasons") or []), block_reason]
    return blocked


def _signal_timestamp(row: dict[str, Any]) -> datetime:
    value = row["ts_signal"]
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise StrategyAuthoringValidationError(f"Unsupported ts_signal value: {value!r}")


def _resolve_leg_side(base_side: str, leg_side: str) -> Literal["long", "short"]:
    if leg_side == "long":
        return "long"
    if leg_side == "short":
        return "short"
    if leg_side == "same":
        return "short" if base_side == "short" else "long"
    return "long" if base_side == "short" else "short"


def _position_weight_value(row: dict[str, Any]) -> float:
    value = row.get("position_weight")
    return float(value) if isinstance(value, int | float) else 1.0


def _portfolio_turnover_weight_value(row: dict[str, Any]) -> float:
    value = row.get("_portfolio_turnover_weight")
    if isinstance(value, int | float):
        return abs(float(value))
    return abs(_position_weight_value(row))
