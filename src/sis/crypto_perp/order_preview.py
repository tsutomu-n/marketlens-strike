from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_FLOOR
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bitget.account import (
    CryptoPerpAccountSnapshot,
    measurement_readiness_blockers,
)
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.idempotency import build_client_oid
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)


ORDER_PREVIEW_SCHEMA_VERSION = "crypto_perp_order_preview.v1"


class InstrumentOrderConstraints(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    product_type: Literal["USDT-FUTURES"]
    price_multiplier: DecimalValue
    size_multiplier: DecimalValue
    min_order_amount: DecimalValue
    min_order_qty: DecimalValue
    max_market_order_qty: DecimalValue

    @field_validator(
        "price_multiplier",
        "size_multiplier",
        "min_order_amount",
        "min_order_qty",
        "max_market_order_qty",
    )
    @classmethod
    def validate_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("order constraint decimals must be positive")
        return value


class OrderPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    decision_id: str
    symbol: str
    product_type: Literal["USDT-FUTURES"]
    side: Literal["buy", "sell"]
    position_side: Literal["one_way", "long", "short"]
    order_type: Literal["limit", "market"]
    margin_mode: Literal["isolated", "crossed"]
    margin_coin: Literal["USDT"]
    requested_notional_usd: DecimalValue
    reference_price: DecimalValue
    limit_price: DecimalValue | None = None
    leverage: int = Field(gt=0)

    @field_validator("requested_notional_usd", "reference_price")
    @classmethod
    def validate_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("requested_notional_usd and reference_price must be positive")
        return value


class CryptoPerpOrderPreview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_order_preview.v1"] = ORDER_PREVIEW_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    preview_id: str
    event_id: str
    decision_id: str
    account_snapshot_id: str
    symbol: str
    product_type: Literal["USDT-FUTURES"]
    side: Literal["buy", "sell"]
    position_side: Literal["one_way", "long", "short"]
    order_type: Literal["limit", "market"]
    margin_mode: Literal["isolated", "crossed"]
    margin_coin: Literal["USDT"]
    leverage: int
    requested_notional_usd: DecimalValue
    reference_price: DecimalValue
    normalized_limit_price: DecimalValue | None
    normalized_qty: DecimalValue
    normalized_notional_usd: DecimalValue
    client_oid: str
    preview_status: Literal["READY", "BLOCKED"]
    reason_codes: list[str]
    would_submit_order: Literal[False] = False

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "requested_notional_usd",
        "reference_price",
        "normalized_limit_price",
        "normalized_qty",
        "normalized_notional_usd",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


def round_down_to_step(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        raise ValueError("step must be positive")
    if value < 0:
        raise ValueError("value must be non-negative")
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step


def _order_price(request: OrderPreviewRequest, constraints: InstrumentOrderConstraints) -> Decimal:
    raw_price = request.limit_price if request.order_type == "limit" else request.reference_price
    if raw_price is None:
        raw_price = request.reference_price
    return round_down_to_step(raw_price, constraints.price_multiplier)


def _reason_codes(
    *,
    request: OrderPreviewRequest,
    constraints: InstrumentOrderConstraints,
    account_snapshot: CryptoPerpAccountSnapshot,
    normalized_qty: Decimal,
    normalized_notional: Decimal,
) -> list[str]:
    reasons = measurement_readiness_blockers(account_snapshot)
    if request.margin_mode != "isolated":
        reasons.append("REQUEST_MARGIN_MODE_NOT_ISOLATED")
    if normalized_qty < constraints.min_order_qty:
        reasons.append("QTY_BELOW_MIN_ORDER_QTY")
    if normalized_notional < constraints.min_order_amount:
        reasons.append("NOTIONAL_BELOW_MIN_ORDER_AMOUNT")
    if request.order_type == "market" and normalized_qty > constraints.max_market_order_qty:
        reasons.append("QTY_ABOVE_MAX_MARKET_ORDER_QTY")
    return list(dict.fromkeys(reasons))


def build_order_preview(
    *,
    request: OrderPreviewRequest,
    constraints: InstrumentOrderConstraints,
    account_snapshot: CryptoPerpAccountSnapshot,
    created_at: datetime | str,
    producer_command: str = "crypto-perp-order-preview",
) -> CryptoPerpOrderPreview:
    created = ensure_utc_aware("created_at", created_at)
    normalized_price = _order_price(request, constraints)
    raw_qty = request.requested_notional_usd / normalized_price
    normalized_qty = round_down_to_step(raw_qty, constraints.size_multiplier)
    normalized_notional = normalized_qty * normalized_price
    reason_codes = _reason_codes(
        request=request,
        constraints=constraints,
        account_snapshot=account_snapshot,
        normalized_qty=normalized_qty,
        normalized_notional=normalized_notional,
    )
    client_oid = build_client_oid(
        event_id=request.event_id,
        decision_id=request.decision_id,
        symbol=request.symbol,
        side=request.side,
        position_side=request.position_side,
    )
    preview_id = stable_hash(
        [
            "crypto-perp-order-preview",
            request.model_dump(mode="json"),
            account_snapshot.account_snapshot_id,
            client_oid,
        ]
    )
    return CryptoPerpOrderPreview(
        artifact_id=stable_hash(["crypto-perp-order-preview-artifact", preview_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=[],
        preview_id=preview_id,
        event_id=request.event_id,
        decision_id=request.decision_id,
        account_snapshot_id=account_snapshot.account_snapshot_id,
        symbol=request.symbol,
        product_type=request.product_type,
        side=request.side,
        position_side=request.position_side,
        order_type=request.order_type,
        margin_mode=request.margin_mode,
        margin_coin=request.margin_coin,
        leverage=request.leverage,
        requested_notional_usd=request.requested_notional_usd,
        reference_price=request.reference_price,
        normalized_limit_price=normalized_price if request.order_type == "limit" else None,
        normalized_qty=normalized_qty,
        normalized_notional_usd=normalized_notional,
        client_oid=client_oid,
        preview_status="BLOCKED" if reason_codes else "READY",
        reason_codes=reason_codes,
    )
