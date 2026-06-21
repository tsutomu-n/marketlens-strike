from __future__ import annotations

import re
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
    CryptoPerpAction,
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)


DECISION_SCHEMA_VERSION = "crypto_perp_decision.v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DecisionSourceRef(BaseModel):
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


class CryptoPerpDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_decision.v1"] = DECISION_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[DecisionSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    decision_id: str
    event_id: str
    decision_version: str
    actor_type: Literal["system", "human"]
    actor_id: str
    decision_at: datetime
    information_cutoff_at: datetime
    action: CryptoPerpAction
    size_cap_usd: DecimalValue
    reason_codes: list[str]
    notes: str
    review_seconds: int = Field(ge=0)
    source_event_path: str
    source_event_sha256: str
    replacement_of: str | None = None

    @field_validator("created_at", "decision_at", "information_cutoff_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_validator(
        "artifact_id",
        "decision_id",
        "event_id",
        "decision_version",
        "actor_id",
        "source_event_path",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("source_event_sha256")
    @classmethod
    def validate_source_event_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("source_event_sha256 must be a lowercase hex SHA-256 digest")
        return value

    @field_validator("size_cap_usd")
    @classmethod
    def validate_size_cap(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("size_cap_usd must be non-negative")
        return value

    @model_validator(mode="after")
    def validate_pre_outcome_cutoff(self) -> Self:
        if self.decision_at < self.information_cutoff_at:
            raise ValueError("decision_at must be after or equal to information_cutoff_at")
        return self

    @field_serializer("created_at", "decision_at", "information_cutoff_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer("size_cap_usd")
    def serialize_size_cap_usd(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


def _decision_id(
    *,
    event_id: str,
    decision_version: str,
    actor_type: Literal["system", "human"],
    actor_id: str,
    decision_at: datetime,
    information_cutoff_at: datetime,
    action: CryptoPerpAction,
    size_cap_usd: Decimal,
    source_event_sha256: str,
    replacement_of: str | None,
) -> str:
    return stable_hash(
        [
            "crypto-perp-decision",
            event_id,
            decision_version,
            actor_type,
            actor_id,
            serialize_utc_z(decision_at),
            serialize_utc_z(information_cutoff_at),
            action.value,
            decimal_to_json_string(size_cap_usd),
            source_event_sha256,
            replacement_of,
        ]
    )


def build_decision(
    *,
    event_id: str,
    action: CryptoPerpAction | str,
    actor_type: Literal["system", "human"],
    actor_id: str,
    decision_at: datetime | str,
    information_cutoff_at: datetime | str,
    size_cap_usd: Decimal | str | int,
    reason_codes: list[str],
    notes: str,
    review_seconds: int,
    source_event_path: str,
    source_event_sha256: str,
    decision_version: str = "mvp-b.v1",
    replacement_of: str | None = None,
    producer_command: str = "crypto-perp-watchdeck",
) -> CryptoPerpDecision:
    parsed_decision_at = ensure_utc_aware("decision_at", decision_at)
    parsed_cutoff = ensure_utc_aware("information_cutoff_at", information_cutoff_at)
    parsed_action = CryptoPerpAction(action)
    parsed_size = Decimal(str(size_cap_usd))
    decision_id = _decision_id(
        event_id=event_id,
        decision_version=decision_version,
        actor_type=actor_type,
        actor_id=actor_id,
        decision_at=parsed_decision_at,
        information_cutoff_at=parsed_cutoff,
        action=parsed_action,
        size_cap_usd=parsed_size,
        source_event_sha256=source_event_sha256,
        replacement_of=replacement_of,
    )
    return CryptoPerpDecision(
        artifact_id=stable_hash(["crypto-perp-decision-artifact", decision_id]),
        created_at=parsed_decision_at,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=[
            DecisionSourceRef(
                path=source_event_path,
                sha256=source_event_sha256,
                schema_version="crypto_perp_event.v1",
            )
        ],
        decision_id=decision_id,
        event_id=event_id,
        decision_version=decision_version,
        actor_type=actor_type,
        actor_id=actor_id,
        decision_at=parsed_decision_at,
        information_cutoff_at=parsed_cutoff,
        action=parsed_action,
        size_cap_usd=parsed_size,
        reason_codes=reason_codes,
        notes=notes,
        review_seconds=review_seconds,
        source_event_path=source_event_path,
        source_event_sha256=source_event_sha256,
        replacement_of=replacement_of,
    )
