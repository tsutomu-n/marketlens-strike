from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)


ACCOUNT_SNAPSHOT_SCHEMA_VERSION = "crypto_perp_account_snapshot.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class AccountSnapshotSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    schema_version: str

    @field_validator("path", "schema_version")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("sha256 must be a lowercase hex SHA-256 digest")
        return value


class CredentialScopeAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    read_enabled: bool
    trade_enabled: bool
    withdrawal_disabled_confirmed: bool
    ip_restriction_confirmed: bool
    attested_by: str
    attested_at: datetime

    @field_validator("attested_by")
    @classmethod
    def validate_attested_by(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("attested_by must not be empty")
        return stripped

    @field_validator("attested_at", mode="before")
    @classmethod
    def validate_attested_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("attested_at", value)

    @field_serializer("attested_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class CryptoPerpPosition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    hold_side: str
    total: DecimalValue
    available: DecimalValue
    margin_mode: str

    @field_serializer("total", "available")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CryptoPerpOpenOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    order_id: str | None
    client_oid: str | None
    side: str
    size: DecimalValue
    reduce_only: bool

    @field_serializer("size")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class FeeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    maker_fee_rate: DecimalValue | None = None
    taker_fee_rate: DecimalValue | None = None
    source: Literal["account_payload", "not_provided"] = "not_provided"

    @field_serializer("maker_fee_rate", "taker_fee_rate")
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


class CryptoPerpAccountSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_account_snapshot.v1"] = ACCOUNT_SNAPSHOT_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[AccountSnapshotSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    account_snapshot_id: str
    observed_at: datetime
    account_equity_usd: DecimalValue
    available_usd: DecimalValue
    unrealized_pnl_usd: DecimalValue
    margin_mode: Literal["isolated", "crossed", "unknown"]
    position_mode: str
    positions: list[CryptoPerpPosition]
    open_orders: list[CryptoPerpOpenOrder]
    fee_snapshot: FeeSnapshot
    credential_scope_attestation: CredentialScopeAttestation

    @field_validator("created_at", "observed_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "observed_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("account_equity_usd", "available_usd", "unrealized_pnl_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


def _first_row(payload: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    if isinstance(payload, Mapping):
        return cast(Mapping[str, Any], payload)
    rows = list(payload)
    if not rows:
        raise ValueError("payload must not be empty")
    return rows[0]


def _decimal_from(row: Mapping[str, Any], *keys: str, default: str = "0") -> Decimal:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return Decimal(str(value))
    return Decimal(default)


def _text_from(row: Mapping[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value)
    return default


def _bool_from(row: Mapping[str, Any], *keys: str) -> bool:
    value = _text_from(row, *keys, default="false").lower()
    return value in {"true", "yes", "1"}


def _positions(rows: Sequence[Mapping[str, Any]]) -> list[CryptoPerpPosition]:
    return [
        CryptoPerpPosition(
            symbol=_text_from(row, "symbol"),
            hold_side=_text_from(row, "holdSide", "hold_side", default="unknown"),
            total=_decimal_from(row, "total", "size", "positionSize"),
            available=_decimal_from(row, "available", "availableSize", "total"),
            margin_mode=_text_from(row, "marginMode", "margin_mode", default="unknown"),
        )
        for row in rows
    ]


def _open_orders(rows: Sequence[Mapping[str, Any]]) -> list[CryptoPerpOpenOrder]:
    return [
        CryptoPerpOpenOrder(
            symbol=_text_from(row, "symbol"),
            order_id=_text_from(row, "orderId", "order_id", default="") or None,
            client_oid=_text_from(row, "clientOid", "client_oid", default="") or None,
            side=_text_from(row, "side", default="unknown"),
            size=_decimal_from(row, "size", "qty", "baseVolume"),
            reduce_only=_bool_from(row, "reduceOnly", "reduce_only"),
        )
        for row in rows
    ]


def _fee_snapshot(row: Mapping[str, Any]) -> FeeSnapshot:
    maker = row.get("makerFeeRate")
    taker = row.get("takerFeeRate")
    if maker is None and taker is None:
        return FeeSnapshot()
    return FeeSnapshot(
        maker_fee_rate=Decimal(str(maker)) if maker is not None else None,
        taker_fee_rate=Decimal(str(taker)) if taker is not None else None,
        source="account_payload",
    )


def build_account_snapshot(
    *,
    observed_at: datetime | str,
    account_payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    positions_payload: Sequence[Mapping[str, Any]],
    open_orders_payload: Sequence[Mapping[str, Any]],
    credential_scope_attestation: CredentialScopeAttestation,
    source_refs: Sequence[Mapping[str, str]] | None = None,
    producer_command: str = "crypto-perp-account-probe",
) -> CryptoPerpAccountSnapshot:
    observed = ensure_utc_aware("observed_at", observed_at)
    account = _first_row(account_payload)
    positions = _positions(positions_payload)
    open_orders = _open_orders(open_orders_payload)
    margin_mode = _text_from(account, "marginMode", "margin_mode", default="unknown")
    parsed_margin_mode: Literal["isolated", "crossed", "unknown"] = "unknown"
    if margin_mode == "isolated":
        parsed_margin_mode = "isolated"
    elif margin_mode == "crossed":
        parsed_margin_mode = "crossed"
    snapshot_id = stable_hash(
        [
            "crypto-perp-account-snapshot",
            serialize_utc_z(observed),
            _text_from(account, "marginCoin", default="USDT"),
            margin_mode,
            _decimal_from(account, "accountEquity", "equity"),
            _decimal_from(account, "available"),
            [item.model_dump(mode="json") for item in positions],
            [item.model_dump(mode="json") for item in open_orders],
        ]
    )
    return CryptoPerpAccountSnapshot(
        artifact_id=stable_hash(["crypto-perp-account-snapshot-artifact", snapshot_id]),
        created_at=observed,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=[AccountSnapshotSourceRef.model_validate(item) for item in source_refs or []],
        account_snapshot_id=snapshot_id,
        observed_at=observed,
        account_equity_usd=_decimal_from(account, "accountEquity", "equity"),
        available_usd=_decimal_from(account, "available"),
        unrealized_pnl_usd=_decimal_from(account, "unrealizedPL", "unrealizedPnl"),
        margin_mode=parsed_margin_mode,
        position_mode=_text_from(account, "posMode", "positionMode", default="unknown"),
        positions=positions,
        open_orders=open_orders,
        fee_snapshot=_fee_snapshot(account),
        credential_scope_attestation=credential_scope_attestation,
    )


def _object_decimal(value: object, name: str) -> Decimal:
    if isinstance(value, Mapping):
        mapping = cast(Mapping[str, object], value)
        return Decimal(str(mapping[name]))
    return Decimal(str(getattr(value, name)))


def measurement_readiness_blockers(snapshot: CryptoPerpAccountSnapshot) -> list[str]:
    blockers: list[str] = []
    if snapshot.margin_mode != "isolated":
        blockers.append("MARGIN_MODE_NOT_ISOLATED")
    if snapshot.credential_scope_attestation.trade_enabled:
        blockers.append("CREDENTIAL_NOT_READ_ONLY")
    if not snapshot.credential_scope_attestation.withdrawal_disabled_confirmed:
        blockers.append("WITHDRAWAL_DISABLED_NOT_CONFIRMED")
    if not snapshot.credential_scope_attestation.ip_restriction_confirmed:
        blockers.append("IP_RESTRICTION_NOT_CONFIRMED")
    if any(_object_decimal(position, "total") != 0 for position in snapshot.positions):
        blockers.append("EXISTING_POSITION")
    if snapshot.open_orders:
        blockers.append("EXISTING_OPEN_ORDER")
    return blockers
