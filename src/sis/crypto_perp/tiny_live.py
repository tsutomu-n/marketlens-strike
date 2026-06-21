from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bitget.account import CryptoPerpAccountSnapshot
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)
from sis.crypto_perp.order_preview import CryptoPerpOrderPreview
from sis.crypto_perp.reconciliation import (
    FlatReconciliation,
    LivePosition,
    ReduceOnlyCloseOrder,
    build_reduce_only_close_order,
    reconcile_flat,
)


LIVE_MEASUREMENT_SCHEMA_VERSION = "crypto_perp_live_measurement.v1"
TINY_LIVE_CONFIRMATION_PHRASE = "MEASURE TINY LIVE RISK"


class OrderState(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    UNKNOWN_AFTER_TIMEOUT = "UNKNOWN_AFTER_TIMEOUT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    CLOSE_PENDING = "CLOSE_PENDING"
    FLAT = "FLAT"
    BLOCKED_RECONCILIATION = "BLOCKED_RECONCILIATION"


_ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.CREATED: {OrderState.SUBMITTED, OrderState.REJECTED},
    OrderState.SUBMITTED: {
        OrderState.UNKNOWN_AFTER_TIMEOUT,
        OrderState.ACKNOWLEDGED,
        OrderState.REJECTED,
    },
    OrderState.UNKNOWN_AFTER_TIMEOUT: {OrderState.ACKNOWLEDGED, OrderState.REJECTED},
    OrderState.ACKNOWLEDGED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.REJECTED,
    },
    OrderState.PARTIALLY_FILLED: {
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.CLOSE_PENDING,
    },
    OrderState.FILLED: {OrderState.CLOSE_PENDING},
    OrderState.CANCEL_PENDING: {OrderState.CANCELED, OrderState.CLOSE_PENDING},
    OrderState.CANCELED: {OrderState.FLAT, OrderState.BLOCKED_RECONCILIATION},
    OrderState.CLOSE_PENDING: {OrderState.FLAT, OrderState.BLOCKED_RECONCILIATION},
    OrderState.REJECTED: set(),
    OrderState.FLAT: set(),
    OrderState.BLOCKED_RECONCILIATION: set(),
}


def transition_order_state(current: OrderState, target: OrderState) -> OrderState:
    if target in _ALLOWED_TRANSITIONS[current]:
        return target
    return current


class OrderCreateTimeout(RuntimeError):
    def __init__(self, client_oid: str) -> None:
        super().__init__(f"order create timed out: {client_oid}")
        self.client_oid = client_oid


class TinyLiveOrderClient(Protocol):
    def create_order(self, client_oid: str) -> Mapping[str, Any]: ...

    def query_order(self, client_oid: str) -> Mapping[str, Any] | None: ...


class TinyLiveOrderStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    client_oid: str
    status: Literal["ACKNOWLEDGED", "ACKNOWLEDGED_AFTER_QUERY", "BLOCKED_QUERY_BEFORE_RESUBMIT"]
    submit_attempts: int
    query_attempts: int
    query_before_resubmit: bool
    resubmitted: Literal[False] = False


class CryptoPerpLiveMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_live_measurement.v1"] = LIVE_MEASUREMENT_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    measurement_id: str
    event_id: str
    decision_id: str
    order_preview_id: str
    account_snapshot_id: str
    execution_mode: Literal["mock"]
    preflight_status: Literal["PASS", "BLOCKED"]
    blockers: list[str]
    requested_notional_usd: DecimalValue
    max_notional_usd: DecimalValue
    entry_step: TinyLiveOrderStep | None
    close_order: ReduceOnlyCloseOrder | None
    flat_reconciliation: FlatReconciliation
    auto_trading_enabled: Literal[False] = False
    live_order_submitted: Literal[False] = False

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("requested_notional_usd", "max_notional_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


def tiny_live_preflight_blockers(
    *,
    env: Mapping[str, str],
    confirm_live: bool,
    confirmation_phrase: str,
    account_snapshot: CryptoPerpAccountSnapshot,
    order_preview: CryptoPerpOrderPreview,
) -> list[str]:
    blockers: list[str] = []
    if env.get("SIS_ENABLE_TINY_LIVE_MEASUREMENT") != "1":
        blockers.append("TINY_LIVE_ENV_NOT_ENABLED")
    if not confirm_live:
        blockers.append("CONFIRM_LIVE_FLAG_MISSING")
    if confirmation_phrase != TINY_LIVE_CONFIRMATION_PHRASE:
        blockers.append("CONFIRMATION_PHRASE_MISMATCH")
    if order_preview.requested_notional_usd < Decimal("5"):
        blockers.append("NOTIONAL_BELOW_5_USD")
    if order_preview.requested_notional_usd > Decimal("25"):
        blockers.append("NOTIONAL_ABOVE_25_USD")
    if account_snapshot.margin_mode != "isolated" or order_preview.margin_mode != "isolated":
        blockers.append("MARGIN_MODE_NOT_ISOLATED")
    if not account_snapshot.credential_scope_attestation.trade_enabled:
        blockers.append("TRADE_PERMISSION_NOT_ATTESTED")
    if not account_snapshot.credential_scope_attestation.withdrawal_disabled_confirmed:
        blockers.append("WITHDRAWAL_DISABLED_NOT_CONFIRMED")
    if not account_snapshot.credential_scope_attestation.ip_restriction_confirmed:
        blockers.append("IP_RESTRICTION_NOT_CONFIRMED")
    if any(position.total != 0 for position in account_snapshot.positions):
        blockers.append("EXISTING_POSITION")
    if account_snapshot.open_orders:
        blockers.append("EXISTING_OPEN_ORDER")
    if order_preview.preview_status != "READY":
        blockers.append("ORDER_PREVIEW_NOT_READY")
    return list(dict.fromkeys(blockers))


def submit_entry_with_query_before_resubmit(
    *,
    client: TinyLiveOrderClient,
    order_preview: CryptoPerpOrderPreview,
) -> TinyLiveOrderStep:
    try:
        client.create_order(order_preview.client_oid)
    except OrderCreateTimeout:
        queried = client.query_order(order_preview.client_oid)
        if queried is None:
            return TinyLiveOrderStep(
                client_oid=order_preview.client_oid,
                status="BLOCKED_QUERY_BEFORE_RESUBMIT",
                submit_attempts=1,
                query_attempts=1,
                query_before_resubmit=True,
            )
        return TinyLiveOrderStep(
            client_oid=order_preview.client_oid,
            status="ACKNOWLEDGED_AFTER_QUERY",
            submit_attempts=1,
            query_attempts=1,
            query_before_resubmit=True,
        )
    return TinyLiveOrderStep(
        client_oid=order_preview.client_oid,
        status="ACKNOWLEDGED",
        submit_attempts=1,
        query_attempts=0,
        query_before_resubmit=False,
    )


def _mock_entry_step(order_preview: CryptoPerpOrderPreview) -> TinyLiveOrderStep:
    return TinyLiveOrderStep(
        client_oid=order_preview.client_oid,
        status="ACKNOWLEDGED",
        submit_attempts=0,
        query_attempts=0,
        query_before_resubmit=False,
    )


def _mock_close_order(order_preview: CryptoPerpOrderPreview) -> ReduceOnlyCloseOrder:
    hold_side = "long" if order_preview.side == "buy" else "short"
    return build_reduce_only_close_order(
        LivePosition(
            symbol=order_preview.symbol,
            hold_side=hold_side,
            total=order_preview.normalized_qty,
        )
    )


def build_mock_tiny_live_measurement(
    *,
    env: Mapping[str, str],
    confirm_live: bool,
    confirmation_phrase: str,
    account_snapshot: CryptoPerpAccountSnapshot,
    order_preview: CryptoPerpOrderPreview,
    measured_at: datetime | str,
) -> CryptoPerpLiveMeasurement:
    measured = ensure_utc_aware("measured_at", measured_at)
    blockers = tiny_live_preflight_blockers(
        env=env,
        confirm_live=confirm_live,
        confirmation_phrase=confirmation_phrase,
        account_snapshot=account_snapshot,
        order_preview=order_preview,
    )
    close_order = None if blockers else _mock_close_order(order_preview)
    flat_reconciliation = reconcile_flat(positions=[], open_orders=[])
    measurement_id = stable_hash(
        [
            "crypto-perp-live-measurement",
            "mock",
            order_preview.preview_id,
            account_snapshot.account_snapshot_id,
            serialize_utc_z(measured),
            blockers,
        ]
    )
    return CryptoPerpLiveMeasurement(
        artifact_id=stable_hash(["crypto-perp-live-measurement-artifact", measurement_id]),
        created_at=measured,
        producer=CryptoPerpProducer(command="crypto-perp-tiny-live-measurement"),
        source_refs=[],
        measurement_id=measurement_id,
        event_id=order_preview.event_id,
        decision_id=order_preview.decision_id,
        order_preview_id=order_preview.preview_id,
        account_snapshot_id=account_snapshot.account_snapshot_id,
        execution_mode="mock",
        preflight_status="BLOCKED" if blockers else "PASS",
        blockers=blockers,
        requested_notional_usd=order_preview.requested_notional_usd,
        max_notional_usd=Decimal("25"),
        entry_step=None if blockers else _mock_entry_step(order_preview),
        close_order=close_order,
        flat_reconciliation=flat_reconciliation,
    )
