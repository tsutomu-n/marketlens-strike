from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


SOURCE_AVAILABILITY_SCHEMA_VERSION = "crypto_perp_source_availability.v1"
SourceId = Literal[
    "event",
    "bars",
    "ticker",
    "funding",
    "trades",
    "books",
    "outcome",
    "replay",
    "cash_ledger",
    "live_measurement",
]


class SourceAvailabilityStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: SourceId
    available: bool
    row_count: int | None = Field(default=None, ge=0)
    reason: str
    source_refs: list[dict[str, str]] = Field(default_factory=list)


class CryptoPerpSourceAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_source_availability.v1"] = (
        SOURCE_AVAILABILITY_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    event_id: str
    information_cutoff_at: datetime
    source_statuses: list[SourceAvailabilityStatus]
    can_compute_ofi: bool
    can_compute_trade_sign_imbalance: bool
    can_compute_depth: bool
    can_compute_cost_adjusted_estimate: bool
    can_compute_actual_cash: bool
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", "information_cutoff_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "information_cutoff_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _source_refs_from_event(event: CryptoPerpEvent) -> list[dict[str, str]]:
    return [ref.model_dump(mode="json") for ref in event.source_refs]


def _source_ref_matches(ref: Mapping[str, str], needles: Sequence[str]) -> bool:
    path = str(ref.get("path", "")).lower()
    schema_version = str(ref.get("schema_version", "")).lower()
    haystack = f"{path} {schema_version}"
    return any(needle in haystack for needle in needles)


def _infer_available(
    source_id: SourceId,
    *,
    event: CryptoPerpEvent,
    provided: Mapping[str, bool],
) -> bool:
    if source_id == "event":
        return True
    if source_id in provided:
        return bool(provided[source_id])
    refs = _source_refs_from_event(event)
    if source_id == "bars":
        return any(_source_ref_matches(ref, ("candle", "candles", "bar")) for ref in refs)
    if source_id == "ticker":
        return any(_source_ref_matches(ref, ("ticker", "tickers", "market_snapshot")) for ref in refs)
    if source_id == "funding":
        return event.features_at_detection.funding_rate != ""
    return False


def _status(
    source_id: SourceId,
    *,
    event: CryptoPerpEvent,
    provided: Mapping[str, bool],
    row_counts: Mapping[str, int],
    source_refs: Sequence[dict[str, str]],
) -> SourceAvailabilityStatus:
    available = _infer_available(source_id, event=event, provided=provided)
    row_count = row_counts.get(source_id)
    refs = [
        dict(ref)
        for ref in source_refs
        if _source_ref_matches(ref, (source_id, source_id.replace("_", "-")))
    ]
    if source_id == "event":
        refs = _source_refs_from_event(event)
    reason = "available" if available else f"{source_id.upper()}_SOURCE_MISSING"
    if available and row_count == 0:
        available = False
        reason = f"{source_id.upper()}_ROW_COUNT_ZERO"
    return SourceAvailabilityStatus(
        source_id=source_id,
        available=available,
        row_count=row_count,
        reason=reason,
        source_refs=refs,
    )


def build_source_availability(
    *,
    event: CryptoPerpEvent,
    created_at: datetime | str,
    available_sources: Mapping[str, bool] | None = None,
    row_counts: Mapping[str, int] | None = None,
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-source-availability",
) -> CryptoPerpSourceAvailability:
    created = ensure_utc_aware("created_at", created_at)
    provided = dict(available_sources or {})
    counts = dict(row_counts or {})
    refs = [*_source_refs_from_event(event), *(dict(ref) for ref in source_refs or [])]
    statuses = [
        _status(
            source_id,
            event=event,
            provided=provided,
            row_counts=counts,
            source_refs=refs,
        )
        for source_id in (
            "event",
            "bars",
            "ticker",
            "funding",
            "trades",
            "books",
            "outcome",
            "replay",
            "cash_ledger",
            "live_measurement",
        )
    ]
    by_source = {status.source_id: status for status in statuses}
    can_compute_depth = bool(by_source["books"].available)
    can_compute_ofi = can_compute_depth
    can_compute_trade_sign_imbalance = bool(by_source["trades"].available)
    can_compute_cost_adjusted_estimate = all(
        by_source[source_id].available for source_id in ("event", "bars", "ticker", "funding")
    )
    can_compute_actual_cash = bool(
        by_source["cash_ledger"].available or by_source["live_measurement"].available
    )
    computed_gaps = list(known_gaps or [])
    for status in statuses:
        if not status.available and status.source_id in {
            "trades",
            "books",
            "outcome",
            "replay",
            "cash_ledger",
            "live_measurement",
        }:
            computed_gaps.append(status.reason)
    if not can_compute_actual_cash:
        computed_gaps.append("ACTUAL_CASH_SOURCE_MISSING")
    computed_gaps = list(dict.fromkeys(computed_gaps))
    summary = {
        "event_id": event.event_id,
        "available_source_count": sum(1 for status in statuses if status.available),
        "known_gap_count": len(computed_gaps),
        "can_compute_cost_adjusted_estimate": can_compute_cost_adjusted_estimate,
        "can_compute_actual_cash": can_compute_actual_cash,
        "can_compute_depth": can_compute_depth,
    }
    artifact_id = stable_hash(
        [
            "crypto-perp-source-availability",
            event.event_id,
            serialize_utc_z(created),
            [status.model_dump(mode="json") for status in statuses],
            computed_gaps,
        ]
    )
    return CryptoPerpSourceAvailability(
        artifact_id=artifact_id,
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=refs,
        event_id=event.event_id,
        information_cutoff_at=event.information_cutoff_at,
        source_statuses=statuses,
        can_compute_ofi=can_compute_ofi,
        can_compute_trade_sign_imbalance=can_compute_trade_sign_imbalance,
        can_compute_depth=can_compute_depth,
        can_compute_cost_adjusted_estimate=can_compute_cost_adjusted_estimate,
        can_compute_actual_cash=can_compute_actual_cash,
        known_gaps=computed_gaps,
        summary=summary,
    )
