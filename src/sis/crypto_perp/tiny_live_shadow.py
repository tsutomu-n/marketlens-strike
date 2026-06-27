from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

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


TINY_LIVE_SHADOW_SCHEMA_VERSION = "crypto_perp_tiny_live_shadow.v1"


class TinyLiveShadowCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    check_id: str
    passed: bool
    observed: str
    required: str


class CryptoPerpTinyLiveShadow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_tiny_live_shadow.v1"] = TINY_LIVE_SHADOW_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    shadow_id: str
    event_id: str
    decision_id: str
    order_preview_id: str
    account_snapshot_id: str
    preflight_status: Literal["PASS", "BLOCKED"]
    blockers: list[str]
    checks: list[TinyLiveShadowCheck]
    requested_notional_usd: DecimalValue
    max_notional_usd: DecimalValue
    exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False
    permits_live_order: Literal[False] = False
    credential_values_redacted: Literal[True] = True
    known_gaps: list[str]
    summary: dict[str, Any]

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


def _check(check_id: str, passed: bool, observed: object, required: object) -> TinyLiveShadowCheck:
    return TinyLiveShadowCheck(
        check_id=check_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
    )


def _source_refs(
    *,
    account_snapshot: CryptoPerpAccountSnapshot,
    order_preview: CryptoPerpOrderPreview,
    extra_refs: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    refs.extend(ref.model_dump(mode="json") for ref in account_snapshot.source_refs)
    refs.extend(order_preview.source_refs)
    refs.extend(extra_refs or [])
    return refs


def build_tiny_live_shadow(
    *,
    account_snapshot: CryptoPerpAccountSnapshot,
    order_preview: CryptoPerpOrderPreview,
    created_at: datetime | str,
    max_notional_usd: Decimal = Decimal("25"),
    source_refs: list[dict[str, str]] | None = None,
    producer_command: str = "crypto-perp-tiny-live-shadow",
) -> CryptoPerpTinyLiveShadow:
    if order_preview.account_snapshot_id != account_snapshot.account_snapshot_id:
        raise ValueError("order preview account_snapshot_id must match account snapshot")
    if max_notional_usd <= 0:
        raise ValueError("max_notional_usd must be positive")
    created = ensure_utc_aware("created_at", created_at)
    checks = [
        _check(
            "requested_notional_within_shadow_cap",
            order_preview.requested_notional_usd <= max_notional_usd,
            order_preview.requested_notional_usd,
            f"<= {max_notional_usd}",
        ),
        _check(
            "account_margin_isolated",
            account_snapshot.margin_mode == "isolated",
            account_snapshot.margin_mode,
            "isolated",
        ),
        _check(
            "order_margin_isolated",
            order_preview.margin_mode == "isolated",
            order_preview.margin_mode,
            "isolated",
        ),
        _check(
            "flat_precheck_positions",
            all(position.total == 0 for position in account_snapshot.positions),
            len(account_snapshot.positions),
            "all position total == 0",
        ),
        _check(
            "flat_precheck_open_orders",
            not account_snapshot.open_orders,
            len(account_snapshot.open_orders),
            "0",
        ),
        _check(
            "order_preview_ready",
            order_preview.preview_status == "READY",
            order_preview.preview_status,
            "READY",
        ),
        _check("credential_values_redacted", True, True, True),
    ]
    blockers = [f"TINY_LIVE_SHADOW_FAILED_{check.check_id}" for check in checks if not check.passed]
    known_gaps = ["SHADOW_MEASUREMENT_NOT_LIVE_ORDER"]
    if account_snapshot.credential_scope_attestation.trade_enabled:
        known_gaps.append("TRADE_ENABLED_ATTESTED_BUT_NOT_USED_BY_SHADOW")
    shadow_id = stable_hash(
        [
            "crypto-perp-tiny-live-shadow",
            account_snapshot.account_snapshot_id,
            order_preview.preview_id,
            serialize_utc_z(created),
            max_notional_usd,
            [check.model_dump(mode="json") for check in checks],
        ]
    )
    preflight_status: Literal["PASS", "BLOCKED"] = "BLOCKED" if blockers else "PASS"
    summary = {
        "shadow_id": shadow_id,
        "preflight_status": preflight_status,
        "blocker_count": len(blockers),
        "requested_notional_usd": order_preview.requested_notional_usd,
        "max_notional_usd": max_notional_usd,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "permits_live_order": False,
    }
    return CryptoPerpTinyLiveShadow(
        artifact_id=stable_hash(["crypto-perp-tiny-live-shadow-artifact", shadow_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=_source_refs(
            account_snapshot=account_snapshot,
            order_preview=order_preview,
            extra_refs=source_refs,
        ),
        shadow_id=shadow_id,
        event_id=order_preview.event_id,
        decision_id=order_preview.decision_id,
        order_preview_id=order_preview.preview_id,
        account_snapshot_id=account_snapshot.account_snapshot_id,
        preflight_status=preflight_status,
        blockers=blockers,
        checks=checks,
        requested_notional_usd=order_preview.requested_notional_usd,
        max_notional_usd=max_notional_usd,
        known_gaps=known_gaps,
        summary=summary,
    )
