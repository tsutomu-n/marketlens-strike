from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sis.execution.base import AdapterActionResult, AdapterOrderStatus


class TradeXyzExchange(Protocol):
    def read_account_state(self, master_address: str, subaccount_address: str | None = None) -> dict[str, Any]: ...

    def schedule_cancel(self, deadline_ts_ms: int) -> dict[str, Any]: ...

    def place_limit_order(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def order_status_by_cloid(self, cloid: str) -> dict[str, Any]: ...

    def cancel_by_cloid(self, cloid: str) -> dict[str, Any]: ...

    def close_position_reduce_only(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class TradeXyzOrderIntent:
    canonical_symbol: str
    side: str
    quantity: float
    limit_price: float
    cloid: str
    notional_usd: float
    leverage: float
    post_only: bool = True
    reduce_only: bool = False
    tif: str = "Alo"


def _success(payload: dict[str, Any]) -> bool:
    status = str(payload.get("status", "")).lower()
    if status in {"ok", "success", "scheduled", "accepted", "filled", "open", "working", "canceled"}:
        return True
    return bool(payload.get("ok", False))


class TradeXyzSafetyAdapter:
    adapter_name = "trade_xyz"

    def __init__(self, exchange: TradeXyzExchange) -> None:
        self._exchange = exchange

    def read_account_state(
        self,
        *,
        master_address: str,
        subaccount_address: str | None = None,
    ) -> dict[str, Any]:
        payload = self._exchange.read_account_state(master_address, subaccount_address)
        return payload if isinstance(payload, dict) else {}

    def schedule_cancel(self, *, deadline_ts_ms: int) -> AdapterActionResult:
        payload = self._exchange.schedule_cancel(deadline_ts_ms)
        success = _success(payload) if isinstance(payload, dict) else False
        return AdapterActionResult(
            venue=self.adapter_name,
            action="schedule_cancel",
            target=str(deadline_ts_ms),
            success=success,
            status="scheduled" if success else "schedule_cancel_failed",
            notes=["micro_live", f"payload={payload!r}"] if isinstance(payload, dict) else ["micro_live"],
        )

    def place_limit_order(self, intent: TradeXyzOrderIntent) -> AdapterActionResult:
        if not intent.post_only or intent.tif.lower() == "market":
            return AdapterActionResult(
                venue=self.adapter_name,
                action="place_limit_order",
                target=intent.cloid,
                success=False,
                status="blocked_market_order",
                notes=["micro_live", "post_only_required"],
            )
        payload = self._exchange.place_limit_order(
            {
                "symbol": intent.canonical_symbol.upper(),
                "side": intent.side.lower(),
                "quantity": intent.quantity,
                "limit_price": intent.limit_price,
                "cloid": intent.cloid,
                "reduce_only": intent.reduce_only,
                "post_only": intent.post_only,
                "tif": intent.tif,
                "notional_usd": intent.notional_usd,
                "leverage": intent.leverage,
            }
        )
        success = _success(payload) if isinstance(payload, dict) else False
        return AdapterActionResult(
            venue=self.adapter_name,
            action="place_limit_order",
            target=intent.cloid,
            success=success,
            status="accepted" if success else "order_rejected",
            notes=["micro_live", f"payload={payload!r}"] if isinstance(payload, dict) else ["micro_live"],
        )

    def order_status_by_cloid(self, cloid: str) -> AdapterOrderStatus:
        payload = self._exchange.order_status_by_cloid(cloid)
        if not isinstance(payload, dict):
            payload = {}
        quantity = payload.get("quantity")
        return AdapterOrderStatus(
            venue=self.adapter_name,
            order_id=str(payload.get("order_id") or cloid),
            canonical_symbol=(str(payload["symbol"]) if payload.get("symbol") is not None else None),
            side=(str(payload["side"]) if payload.get("side") is not None else None),
            quantity=float(quantity) if isinstance(quantity, int | float) else None,
            status=str(payload.get("status", "unknown")),
            notes=["micro_live", f"payload={payload!r}"],
        )

    def cancel_by_cloid(self, cloid: str) -> AdapterActionResult:
        payload = self._exchange.cancel_by_cloid(cloid)
        success = _success(payload) if isinstance(payload, dict) else False
        return AdapterActionResult(
            venue=self.adapter_name,
            action="cancel_by_cloid",
            target=cloid,
            success=success,
            status="canceled" if success else "cancel_failed",
            notes=["micro_live", f"payload={payload!r}"] if isinstance(payload, dict) else ["micro_live"],
        )

    def close_position_reduce_only(
        self,
        *,
        canonical_symbol: str,
        side: str,
        quantity: float,
        limit_price: float,
        cloid: str,
        reduce_only: bool = True,
    ) -> AdapterActionResult:
        if not reduce_only:
            return AdapterActionResult(
                venue=self.adapter_name,
                action="close_position_reduce_only",
                target=cloid,
                success=False,
                status="blocked_non_reduce_only_close",
                notes=["micro_live", "reduce_only_required"],
            )
        payload = self._exchange.close_position_reduce_only(
            {
                "symbol": canonical_symbol.upper(),
                "side": side.lower(),
                "quantity": quantity,
                "limit_price": limit_price,
                "cloid": cloid,
                "reduce_only": True,
                "post_only": True,
                "tif": "Alo",
            }
        )
        success = _success(payload) if isinstance(payload, dict) else False
        return AdapterActionResult(
            venue=self.adapter_name,
            action="close_position_reduce_only",
            target=cloid,
            success=success,
            status="close_submitted" if success else "close_failed",
            notes=["micro_live", f"payload={payload!r}"] if isinstance(payload, dict) else ["micro_live"],
        )

