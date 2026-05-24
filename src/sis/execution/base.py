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


class ExecutionAdapter(Protocol):
    adapter_name: str

    def read_balance(self) -> dict: ...

    def read_positions(self) -> list[AdapterPositionSnapshot]: ...

    def estimate_order(self, intent: OrderIntent) -> AdapterOrderEstimate: ...

    def healthcheck(self) -> dict: ...
