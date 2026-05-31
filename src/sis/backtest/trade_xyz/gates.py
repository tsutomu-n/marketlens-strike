from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any

from sis.backtest.engine.config import GateConfig
from sis.backtest.trade_xyz.cost_model import FeeResolution


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reasons: list[str]


def _as_bool(value: object) -> bool:
    return value if isinstance(value, bool) else False


def _as_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _block_reasons(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None and str(item)]
    if value in {None, ""}:
        return []
    return [str(value)]


def execution_value(row: Mapping[str, Any], field: str) -> Any:
    fill_value = row.get(f"fill_{field}")
    return fill_value if fill_value is not None else row.get(field)


def evaluate_entry_gate(
    row: dict[str, Any], *, gates: GateConfig, fee: FeeResolution
) -> GateResult:
    reasons: list[str] = []
    if not gates.allow_entry_when_is_tradable_false and not _as_bool(row.get("is_tradable")):
        reasons.append("is_tradable_false")
    if not gates.allow_entry_when_block_reasons_non_empty and _block_reasons(
        row.get("block_reasons")
    ):
        reasons.append("block_reasons_non_empty")
    if not fee.resolved:
        reasons.append("fee_unresolved")
    market_status = str(row.get("market_status") or "open").lower()
    if market_status != "open":
        reasons.append("market_status_not_open")

    spread_bps = _as_float(row.get("spread_bps"))
    if (
        gates.max_spread_bps is not None
        and spread_bps is not None
        and spread_bps > gates.max_spread_bps
    ):
        reasons.append("spread_bps_above_max")

    depth = _as_float(row.get("min_side_depth_10bps_usd"))
    if (
        gates.min_depth_10bps_usd is not None
        and depth is not None
        and depth < gates.min_depth_10bps_usd
    ):
        reasons.append("min_depth_10bps_usd_below_min")

    bound_distance = _as_float(row.get("bound_distance"))
    if (
        gates.max_bound_distance is not None
        and bound_distance is not None
        and bound_distance > gates.max_bound_distance
    ):
        reasons.append("bound_distance_above_max")

    oi_cap_usage = _as_float(row.get("oi_cap_usage"))
    if (
        gates.max_oi_cap_usage is not None
        and oi_cap_usage is not None
        and oi_cap_usage > gates.max_oi_cap_usage
    ):
        reasons.append("oi_cap_usage_above_max")
    return GateResult(allowed=not reasons, reasons=reasons)


def evaluate_open_fill_gate(
    row: Mapping[str, Any],
    *,
    gates: GateConfig,
    fee: FeeResolution,
    fill_price_resolved: bool,
) -> GateResult:
    reasons: list[str] = []
    if not fill_price_resolved:
        reasons.append("fill_price_unresolved")
    if not fee.resolved:
        reasons.append("fill_fee_unresolved")
    if not _as_bool(execution_value(row, "is_tradable")):
        reasons.append("fill_row_is_tradable_false")
    if _block_reasons(execution_value(row, "block_reasons")):
        reasons.append("fill_row_block_reasons_non_empty")
    market_status = str(execution_value(row, "market_status") or "open").lower()
    if market_status != "open":
        reasons.append("fill_row_market_status_not_open")

    spread_bps = _as_float(execution_value(row, "spread_bps"))
    if (
        gates.max_spread_bps is not None
        and spread_bps is not None
        and spread_bps > gates.max_spread_bps
    ):
        reasons.append("fill_row_spread_bps_above_max")

    depth = _as_float(execution_value(row, "min_side_depth_10bps_usd"))
    if (
        gates.min_depth_10bps_usd is not None
        and depth is not None
        and depth < gates.min_depth_10bps_usd
    ):
        reasons.append("fill_row_min_depth_10bps_usd_below_min")

    bound_distance = _as_float(execution_value(row, "bound_distance"))
    if (
        gates.max_bound_distance is not None
        and bound_distance is not None
        and bound_distance > gates.max_bound_distance
    ):
        reasons.append("fill_row_bound_distance_above_max")

    oi_cap_usage = _as_float(execution_value(row, "oi_cap_usage"))
    if (
        gates.max_oi_cap_usage is not None
        and oi_cap_usage is not None
        and oi_cap_usage > gates.max_oi_cap_usage
    ):
        reasons.append("fill_row_oi_cap_usage_above_max")
    return GateResult(allowed=not reasons, reasons=reasons)


def evaluate_close_fill_gate(
    row: Mapping[str, Any],
    *,
    fee: FeeResolution,
    fill_price_resolved: bool,
) -> GateResult:
    reasons: list[str] = []
    if not fill_price_resolved:
        reasons.append("fill_price_unresolved")
    if not fee.resolved:
        reasons.append("fill_fee_unresolved")
    market_status = str(execution_value(row, "market_status") or "open").lower()
    if market_status not in {"open", "close_only", "unknown_if_fixture"}:
        reasons.append("fill_row_market_status_exit_not_allowed")
    return GateResult(allowed=not reasons, reasons=reasons)


def evaluate_exit_gate(
    row: dict[str, Any],
    *,
    position_is_open: bool,
    exit_signal_exists: bool,
    fee: FeeResolution,
    exit_price_resolved: bool = True,
) -> GateResult:
    reasons: list[str] = []
    if not position_is_open:
        reasons.append("position_not_open")
    if not exit_signal_exists:
        reasons.append("exit_signal_missing")
    if not exit_price_resolved:
        reasons.append("exit_price_unresolved")
    if not fee.resolved:
        reasons.append("fee_unresolved")
    market_status = str(row.get("market_status") or "open").lower()
    if market_status not in {"open", "close_only", "unknown_if_fixture"}:
        reasons.append("market_status_exit_not_allowed")
    return GateResult(allowed=not reasons, reasons=reasons)
