from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OrderIntent:
    venue: str
    canonical_symbol: str
    side: str
    quantity: float
    timeframe: str


@dataclass(frozen=True)
class AdapterPositionSnapshot:
    venue: str
    canonical_symbol: str
    side: str
    quantity: float
    entry_price: float | None = None
    liquidation_price: float | None = None


@dataclass(frozen=True)
class AdapterOrderEstimate:
    venue: str
    canonical_symbol: str
    side: str
    estimated_entry_price: float | None
    estimated_cost_bps: float | None
    price_reference: str
    notes: list[str]


@dataclass(frozen=True)
class AdapterOrderStatus:
    venue: str
    order_id: str
    canonical_symbol: str | None
    side: str | None
    quantity: float | None
    status: str
    notes: list[str]


@dataclass(frozen=True)
class AdapterFillSnapshot:
    venue: str
    fill_id: str
    order_id: str | None
    canonical_symbol: str | None
    side: str | None
    quantity: float | None
    price: float | None
    status: str
    ts_fill: str | None
    notes: list[str]


@dataclass(frozen=True)
class AdapterActionResult:
    venue: str
    action: str
    target: str
    success: bool
    status: str
    notes: list[str]


class ExecutionAdapter(Protocol):
    adapter_name: str

    def read_balance(self) -> dict: ...

    def read_positions(self) -> list[AdapterPositionSnapshot]: ...

    def estimate_order(self, intent: OrderIntent) -> AdapterOrderEstimate: ...

    def read_order_status(self, order_id: str) -> AdapterOrderStatus: ...

    def read_order_statuses(self, limit: int | None = None) -> list[AdapterOrderStatus]: ...

    def read_fills(self, limit: int | None = None) -> list[AdapterFillSnapshot]: ...

    def cancel_order(self, order_id: str) -> AdapterActionResult: ...

    def close_position(
        self, canonical_symbol: str, side: str | None = None
    ) -> AdapterActionResult: ...

    def healthcheck(self) -> dict: ...
