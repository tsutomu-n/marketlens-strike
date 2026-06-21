from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from sis.crypto_perp.models import DecimalValue, decimal_to_json_string


class LivePosition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    hold_side: Literal["long", "short"]
    total: DecimalValue

    @field_validator("total")
    @classmethod
    def validate_total(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("position total must be non-negative")
        return value

    @field_serializer("total")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class LiveOpenOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    order_id: str
    client_oid: str


class ReduceOnlyCloseOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    side: Literal["buy", "sell"]
    size: DecimalValue
    reduce_only: Literal[True] = True

    @field_serializer("size")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class FlatReconciliation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["FLAT", "BLOCKED_RECONCILIATION"]
    blockers: list[str]


def reconcile_flat(
    *,
    positions: list[LivePosition],
    open_orders: list[LiveOpenOrder],
) -> FlatReconciliation:
    blockers: list[str] = []
    if any(position.total != 0 for position in positions):
        blockers.append("EXISTING_POSITION")
    if open_orders:
        blockers.append("EXISTING_OPEN_ORDER")
    return FlatReconciliation(
        status="BLOCKED_RECONCILIATION" if blockers else "FLAT",
        blockers=blockers,
    )


def build_reduce_only_close_order(position: LivePosition) -> ReduceOnlyCloseOrder:
    return ReduceOnlyCloseOrder(
        symbol=position.symbol,
        side="sell" if position.hold_side == "long" else "buy",
        size=position.total,
    )
