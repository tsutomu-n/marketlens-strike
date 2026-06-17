from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Protocol, cast

import httpx

from sis.venues.trade_xyz.client import TradeXyzApiError, TradeXyzClient

EXECUTION_STATE_USER_ADDRESS_ENV = "SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS"
ACCOUNT_FEE_USER_ADDRESS_ENV = "SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS"
COLLECTOR_ENABLED_ENV = "SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED"
COLLECTOR_ROOT_SOURCE = "execution_read_only_surfaces_summary.venues[].collector_status"
RATE_LIMIT_WEIGHT_ASSUMPTION = "unknown_info_endpoint_weight"


class TradeXyzExecutionStateClient(Protocol):
    def clearinghouse_state(self, user: str) -> dict[str, Any]: ...

    def open_orders(self, user: str) -> list[dict[str, Any]]: ...

    def user_fills(self, user: str) -> list[dict[str, Any]]: ...

    def close(self) -> None: ...


def _base_surface(settings_data_dir: Path) -> dict[str, object]:
    registry_path = settings_data_dir / "registry/trade_xyz_instrument_registry.json"
    return {
        "venue": "trade_xyz",
        "registry_exists": registry_path.exists(),
        "balance_snapshot_exists": False,
        "positions_snapshot_exists": False,
        "fills_snapshot_exists": False,
        "order_status_snapshot_exists": False,
        "positions_count": None,
        "fills_count": None,
        "order_status_count": None,
        "collector_status": "not_connected",
        "collector_reason": None,
        "collector_root_source": COLLECTOR_ROOT_SOURCE,
        "read_only_endpoint_scope": "info_endpoint_only",
        "external_api_used": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
    }


def _configured_user_address() -> tuple[str | None, str | None]:
    execution_state_address = os.environ.get(EXECUTION_STATE_USER_ADDRESS_ENV, "").strip()
    if execution_state_address:
        return execution_state_address, EXECUTION_STATE_USER_ADDRESS_ENV
    account_fee_address = os.environ.get(ACCOUNT_FEE_USER_ADDRESS_ENV, "").strip()
    if account_fee_address:
        return account_fee_address, ACCOUNT_FEE_USER_ADDRESS_ENV
    return None, None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.lower().encode("utf-8")).hexdigest()


def _enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _float_or_none(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _position_payloads(clearinghouse_state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = clearinghouse_state.get("assetPositions")
    if not isinstance(rows, list):
        return []
    positions: list[dict[str, Any]] = []
    for row in rows:
        item = _dict_or_empty(row)
        position = _dict_or_empty(item.get("position"))
        if position:
            positions.append(position)
    return positions


def _position_float(position: dict[str, Any], key: str) -> float | None:
    return _float_or_none(position.get(key))


def _position_leverage(position: dict[str, Any]) -> float | None:
    leverage = position.get("leverage")
    if isinstance(leverage, dict):
        return _float_or_none(leverage.get("value") or leverage.get("rawUsd"))
    return _float_or_none(leverage)


def _position_cumulative_rollover(position: dict[str, Any]) -> float | None:
    funding = position.get("cumFunding")
    if isinstance(funding, dict):
        return _float_or_none(
            funding.get("allTime") or funding.get("sinceOpen") or funding.get("sinceChange")
        )
    return _float_or_none(position.get("cumulativeRollover"))


def _sum_present(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) if present else None


def _avg_present(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def _max_present(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _request_metadata(request_type: str, row_count: int) -> dict[str, object]:
    return {
        "endpoint_type": "info",
        "request_type": request_type,
        "row_count": row_count,
        "rate_limit_weight_assumption": RATE_LIMIT_WEIGHT_ASSUMPTION,
    }


def _latest_order(open_orders: list[dict[str, Any]]) -> dict[str, Any]:
    return open_orders[-1] if open_orders else {}


def _latest_fill(fills: list[dict[str, Any]]) -> dict[str, Any]:
    return fills[-1] if fills else {}


def _order_id(order: dict[str, Any]) -> str | None:
    value = order.get("oid") or order.get("order_id") or order.get("cloid")
    return str(value) if value is not None else None


def _fill_id(fill: dict[str, Any]) -> str | None:
    value = fill.get("hash") or fill.get("fill_id") or fill.get("tid") or fill.get("oid")
    return str(value) if value is not None else None


def _row_count(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        payload = cast(dict[str, Any], value)
        positions = payload.get("assetPositions")
        return len(positions) if isinstance(positions, list) else 1
    return 0


def _classify_error(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, TimeoutError | httpx.TimeoutException):
        return "trade_xyz_execution_state_collector_timeout", "timeout"
    if isinstance(exc, httpx.TransportError):
        return "trade_xyz_execution_state_collector_transport_error", "transport_error"
    if isinstance(exc, TradeXyzApiError):
        text = str(exc)
        if "429" in text:
            return "trade_xyz_execution_state_collector_rate_limited", "rate_limited"
        if "401" in text or "403" in text:
            return "trade_xyz_execution_state_collector_permission_error", "permission_error"
        if "returned non-" in text or "unexpected payload" in text:
            return "trade_xyz_execution_state_collector_schema_mismatch", "schema_mismatch"
        return "trade_xyz_execution_state_collector_api_error", "api_error"
    return "trade_xyz_execution_state_collector_error", type(exc).__name__


def _collected_surface(
    surface: dict[str, object],
    *,
    clearinghouse_state: dict[str, Any],
    open_orders: list[dict[str, Any]],
    fills: list[dict[str, Any]],
) -> dict[str, object]:
    margin_summary = _dict_or_empty(clearinghouse_state.get("marginSummary"))
    positions = _position_payloads(clearinghouse_state)
    latest_order = _latest_order(open_orders)
    latest_fill = _latest_fill(fills)
    position_values = [_position_float(position, "positionValue") for position in positions]
    unrealized_values = [_position_float(position, "unrealizedPnl") for position in positions]
    collateral_values = [_position_float(position, "marginUsed") for position in positions]
    rollover_values = [_position_cumulative_rollover(position) for position in positions]
    leverage_values = [_position_leverage(position) for position in positions]
    return_values = [_position_float(position, "returnOnEquity") for position in positions]
    quantity_values = [_position_float(position, "szi") for position in positions]
    max_leverage_values = [_position_float(position, "maxLeverage") for position in positions]
    surface.update(
        {
            "balance_snapshot_exists": True,
            "positions_snapshot_exists": True,
            "fills_snapshot_exists": True,
            "order_status_snapshot_exists": True,
            "positions_count": len(positions),
            "fills_count": len(fills),
            "order_status_count": len(open_orders),
            "collector_status": "connected",
            "collector_reason": None,
            "next_action": "none",
            "external_api_used": True,
            "balance": {
                "currency": "USD",
                "equity": _float_or_none(margin_summary.get("accountValue")),
            },
            "equity": _float_or_none(margin_summary.get("accountValue")),
            "available_cash": _float_or_none(clearinghouse_state.get("withdrawable")),
            "margin_used": _float_or_none(margin_summary.get("totalMarginUsed")),
            "notional_usd": _float_or_none(margin_summary.get("totalNtlPos")),
            "unrealized_pnl": _sum_present(unrealized_values),
            "cumulative_rollover_usd": _sum_present(rollover_values),
            "latest_order_id": _order_id(latest_order),
            "latest_order_status_snapshot": latest_order,
            "latest_order_status": (latest_order.get("status") or "open" if latest_order else None),
            "latest_fill_id": _fill_id(latest_fill),
            "latest_fill_status": (latest_fill.get("status") or "filled" if latest_fill else None),
            "latest_fill": latest_fill,
            "positions_notional_usd_total": _sum_present(position_values),
            "positions_unrealized_pnl_usd_total": _sum_present(unrealized_values),
            "positions_collateral_used_usd_total": _sum_present(collateral_values),
            "positions_max_withdrawable_usd_total": _float_or_none(
                clearinghouse_state.get("withdrawable")
            ),
            "positions_cumulative_rollover_usd_total": _sum_present(rollover_values),
            "positions_with_liquidation_price_count": sum(
                1 for position in positions if position.get("liquidationPx") is not None
            ),
            "positions_with_take_profit_count": sum(
                1 for position in positions if position.get("takeProfitPx") is not None
            ),
            "positions_with_stop_loss_count": sum(
                1 for position in positions if position.get("stopLossPx") is not None
            ),
            "positions_day_trade_count": None,
            "positions_average_leverage": _avg_present(leverage_values),
            "positions_average_return_on_equity": _avg_present(return_values),
            "positions_max_leverage": _max_present(max_leverage_values),
            "positions_total_quantity": _sum_present(quantity_values),
            "positions_total_realized_pnl": None,
            "positions_server_time_ms": clearinghouse_state.get("time"),
            "request_metadata": [
                _request_metadata("clearinghouseState", _row_count(clearinghouse_state)),
                _request_metadata("openOrders", _row_count(open_orders)),
                _request_metadata("userFills", _row_count(fills)),
            ],
        }
    )
    return surface


def build_trade_xyz_execution_state_surface(
    settings_data_dir: Path,
    *,
    client: TradeXyzExecutionStateClient | None = None,
    user_address: str | None = None,
    collector_enabled: bool | None = None,
) -> dict[str, object]:
    surface = _base_surface(settings_data_dir)
    configured_user_address, env_source = (
        (user_address, "argument") if user_address else _configured_user_address()
    )
    if not configured_user_address:
        surface.update(
            {
                "collector_reason": "trade_xyz_execution_state_user_address_missing",
                "required_env": [EXECUTION_STATE_USER_ADDRESS_ENV, ACCOUNT_FEE_USER_ADDRESS_ENV],
                "user_address_configured": False,
                "next_action": "set_trade_xyz_execution_state_public_user_address",
            }
        )
        return surface

    surface.update(
        {
            "user_address_configured": True,
            "user_address_source": env_source,
            "user_address_sha256": _sha256_text(configured_user_address),
        }
    )
    enabled = (
        collector_enabled
        if collector_enabled is not None
        else _enabled(os.environ.get(COLLECTOR_ENABLED_ENV))
    )
    if not enabled:
        surface.update(
            {
                "collector_reason": "trade_xyz_execution_state_collector_opt_in_required",
                "required_env": [COLLECTOR_ENABLED_ENV],
                "next_action": "enable_trade_xyz_execution_state_read_only_collector",
            }
        )
        return surface

    own_client = client is None
    created_client = client or TradeXyzClient()
    surface["external_api_used"] = True
    try:
        clearinghouse_state = created_client.clearinghouse_state(configured_user_address)
        open_orders = created_client.open_orders(configured_user_address)
        fills = created_client.user_fills(configured_user_address)
        return _collected_surface(
            surface,
            clearinghouse_state=clearinghouse_state,
            open_orders=open_orders,
            fills=fills,
        )
    except Exception as exc:
        reason, error_class = _classify_error(exc)
        surface.update(
            {
                "collector_status": "unavailable",
                "collector_reason": reason,
                "error_class": error_class,
                "error_message": str(exc)[:500],
                "next_action": "inspect_trade_xyz_execution_state_collector_error",
            }
        )
        return surface
    finally:
        if own_client:
            created_client.close()
