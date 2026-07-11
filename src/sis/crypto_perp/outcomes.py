from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)


OUTCOME_SCHEMA_VERSION = "crypto_perp_outcome.v1"
HighLowOrdering = Literal["HIGH_FIRST", "LOW_FIRST", "AMBIGUOUS", "UNKNOWN"]
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class OutcomeSourceRef(BaseModel):
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


class OutcomePriceWindow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    horizon_minutes: int = Field(gt=0)
    matured: bool
    reference_price: DecimalValue
    close_price: DecimalValue
    high_price: DecimalValue
    low_price: DecimalValue
    market_return: DecimalValue = Decimal("0")
    observed_high_low_order: Literal["HIGH_FIRST", "LOW_FIRST"] | None = None

    @model_validator(mode="after")
    def validate_prices(self) -> Self:
        if self.reference_price <= 0:
            raise ValueError("reference_price must be positive")
        if self.close_price < 0 or self.high_price < 0 or self.low_price < 0:
            raise ValueError("prices must be non-negative")
        if self.high_price < self.low_price:
            raise ValueError("high_price must be greater than or equal to low_price")
        return self


class OutcomeHorizon(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    horizon_minutes: int = Field(gt=0)
    matured: bool
    reference_price: DecimalValue
    close_price: DecimalValue
    raw_return: DecimalValue
    short_return_before_cost: DecimalValue
    long_return_before_cost: DecimalValue
    mfe_long: DecimalValue
    mae_long: DecimalValue
    mfe_short: DecimalValue
    mae_short: DecimalValue
    high_first_low_first: HighLowOrdering
    market_adjusted_return: DecimalValue

    @field_serializer(
        "reference_price",
        "close_price",
        "raw_return",
        "short_return_before_cost",
        "long_return_before_cost",
        "mfe_long",
        "mae_long",
        "mfe_short",
        "mae_short",
        "market_adjusted_return",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CryptoPerpOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_outcome.v1"] = OUTCOME_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[OutcomeSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    outcome_id: str
    event_id: str
    settled_at: datetime
    horizons: list[OutcomeHorizon]
    near_miss_refs: list[str]
    known_gaps: list[str]

    @field_validator("created_at", "settled_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_validator("artifact_id", "outcome_id", "event_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("horizons")
    @classmethod
    def validate_horizons(cls, value: list[OutcomeHorizon]) -> list[OutcomeHorizon]:
        if not value:
            raise ValueError("horizons must not be empty")
        return value

    @field_serializer("created_at", "settled_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _ordering(window: OutcomePriceWindow) -> HighLowOrdering:
    if not window.matured:
        return "UNKNOWN"
    return window.observed_high_low_order or "AMBIGUOUS"


def _horizon(window: OutcomePriceWindow) -> OutcomeHorizon:
    reference = window.reference_price
    raw_return = (window.close_price - reference) / reference
    long_return = raw_return
    short_return = -raw_return
    mfe_long = (window.high_price - reference) / reference
    mae_long = (window.low_price - reference) / reference
    mfe_short = (reference - window.low_price) / reference
    mae_short = (reference - window.high_price) / reference
    return OutcomeHorizon(
        horizon_minutes=window.horizon_minutes,
        matured=window.matured,
        reference_price=reference,
        close_price=window.close_price,
        raw_return=raw_return,
        short_return_before_cost=short_return,
        long_return_before_cost=long_return,
        mfe_long=mfe_long,
        mae_long=mae_long,
        mfe_short=mfe_short,
        mae_short=mae_short,
        high_first_low_first=_ordering(window),
        market_adjusted_return=raw_return - window.market_return,
    )


def _outcome_id(event_id: str, settled_at: datetime, horizons: Sequence[OutcomeHorizon]) -> str:
    return stable_hash(
        [
            "crypto-perp-outcome",
            event_id,
            serialize_utc_z(settled_at),
            [item.model_dump(mode="json") for item in horizons],
        ]
    )


def validate_outcome_identity(outcome: CryptoPerpOutcome) -> None:
    """Reject an outcome whose persisted identity no longer matches its content."""
    expected_outcome_id = _outcome_id(outcome.event_id, outcome.settled_at, outcome.horizons)
    if outcome.outcome_id != expected_outcome_id:
        raise ValueError(f"OUTCOME_IDENTITY_MISMATCH: {outcome.event_id}")
    expected_artifact_id = stable_hash(["crypto-perp-outcome-artifact", expected_outcome_id])
    if outcome.artifact_id != expected_artifact_id:
        raise ValueError(f"OUTCOME_ARTIFACT_IDENTITY_MISMATCH: {outcome.event_id}")
    for horizon in outcome.horizons:
        expected_raw_return = (horizon.close_price - horizon.reference_price) / (
            horizon.reference_price
        )
        if horizon.raw_return != expected_raw_return:
            raise ValueError(f"OUTCOME_RETURN_MISMATCH: {outcome.event_id}")
        if horizon.long_return_before_cost != expected_raw_return:
            raise ValueError(f"OUTCOME_LONG_RETURN_MISMATCH: {outcome.event_id}")
        if horizon.short_return_before_cost != -expected_raw_return:
            raise ValueError(f"OUTCOME_SHORT_RETURN_MISMATCH: {outcome.event_id}")
        if horizon.mfe_short != -horizon.mae_long:
            raise ValueError(f"OUTCOME_MFE_SHORT_MISMATCH: {outcome.event_id}")
        if horizon.mae_short != -horizon.mfe_long:
            raise ValueError(f"OUTCOME_MAE_SHORT_MISMATCH: {outcome.event_id}")


def _source_refs(source_refs: Sequence[dict[str, str]] | None) -> list[OutcomeSourceRef]:
    return [OutcomeSourceRef.model_validate(item) for item in source_refs or []]


def build_outcome(
    *,
    event_id: str,
    settled_at: datetime | str,
    horizons: Sequence[OutcomePriceWindow],
    near_miss_refs: Sequence[str] | None = None,
    known_gaps: Sequence[str] | None = None,
    source_refs: Sequence[dict[str, str]] | None = None,
    producer_command: str = "crypto-perp-watchdeck",
) -> CryptoPerpOutcome:
    parsed_settled_at = ensure_utc_aware("settled_at", settled_at)
    computed_horizons = [_horizon(window) for window in horizons]
    outcome_id = _outcome_id(event_id, parsed_settled_at, computed_horizons)
    return CryptoPerpOutcome(
        artifact_id=stable_hash(["crypto-perp-outcome-artifact", outcome_id]),
        created_at=parsed_settled_at,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=_source_refs(source_refs),
        outcome_id=outcome_id,
        event_id=event_id,
        settled_at=parsed_settled_at,
        horizons=computed_horizons,
        near_miss_refs=list(near_miss_refs or []),
        known_gaps=list(known_gaps or []),
    )
