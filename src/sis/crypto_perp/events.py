from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bars import CandleBar
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.features import (
    EventDetectorConfig,
    EventFeatures,
    MarketContext,
    compute_event_features,
)
from sis.crypto_perp.heartbeat import MarketTickerSnapshot
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.quality import CandleQualityReport


EVENT_SCHEMA_VERSION = "crypto_perp_event.v1"
EventFamily = Literal["slow_pump_74h_v1", "fast_pump_1h_v1", "near_miss_v1"]


class EventSourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    schema_version: str


class EventDataQuality(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["PASS", "REJECTED_DATA_QUALITY"]
    reason_codes: list[str]


class EventCaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested: bool
    channels: list[str]
    duration_minutes: int


class CryptoPerpEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_event.v1"] = EVENT_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[EventSourceRef]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    event_id: str
    event_family: EventFamily
    provider_id: Literal["bitget"]
    native_symbol: str
    canonical_symbol: str
    first_detected_at: datetime
    information_cutoff_at: datetime
    universe_snapshot_id: str
    market_snapshot_id: str
    detector_version: str
    detector_config_hash: str
    features_at_detection: EventFeatures
    market_context: MarketContext
    data_quality: EventDataQuality
    capture_request: EventCaptureRequest
    status: Literal[
        "CAPTURE_REQUESTED",
        "CAPTURE_ACTIVE",
        "CAPTURE_COMPLETE",
        "INCONCLUSIVE_DATA",
        "REJECTED_DATA_QUALITY",
    ]

    @field_validator("created_at", "first_detected_at", "information_cutoff_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "first_detected_at", "information_cutoff_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _decimal(value: str) -> Decimal:
    return Decimal(value)


def _family(features: EventFeatures, config: EventDetectorConfig) -> EventFamily | None:
    slow = (
        _decimal(features.return_74h) >= config.slow_return_threshold
        and _decimal(features.turnover_impulse) >= config.slow_turnover_impulse_threshold
    )
    fast = (
        abs(_decimal(features.return_60m)) >= config.fast_abs_return_floor
        and _decimal(features.robust_return_z) >= config.fast_robust_z_threshold
        and _decimal(features.turnover_percentile) >= config.fast_turnover_percentile_threshold
    )
    near_slow = (
        _decimal(features.return_74h) >= config.slow_return_threshold * config.near_miss_ratio
        and _decimal(features.turnover_impulse)
        >= config.slow_turnover_impulse_threshold * config.near_miss_ratio
    )
    near_fast = (
        abs(_decimal(features.return_60m)) >= config.fast_abs_return_floor * config.near_miss_ratio
        and _decimal(features.robust_return_z)
        >= config.fast_robust_z_threshold * config.near_miss_ratio
        and _decimal(features.turnover_percentile)
        >= config.fast_turnover_percentile_threshold * config.near_miss_ratio
    )
    if slow:
        return "slow_pump_74h_v1"
    if fast:
        return "fast_pump_1h_v1"
    if near_slow or near_fast:
        return "near_miss_v1"
    return None


def _event_id(
    *,
    provider_id: str,
    native_symbol: str,
    detector_version: str,
    first_detected_at: datetime,
) -> str:
    return stable_hash(
        [
            "crypto-perp-event",
            provider_id,
            native_symbol,
            detector_version,
            serialize_utc_z(first_detected_at),
        ]
    )


def _detector_config_hash(config: EventDetectorConfig) -> str:
    return stable_hash(["crypto-perp-detector-config", config.model_dump(mode="json")])


def _source_refs(source_refs: Sequence[dict[str, Any]] | None) -> list[EventSourceRef]:
    return [EventSourceRef.model_validate(item) for item in source_refs or []]


def detect_event(
    *,
    provider_id: Literal["bitget"],
    native_symbol: str,
    canonical_symbol: str,
    bars: Sequence[CandleBar],
    ticker: MarketTickerSnapshot,
    quality_report: CandleQualityReport,
    universe_snapshot_id: str,
    market_snapshot_id: str,
    detector_config: EventDetectorConfig,
    information_cutoff_at: datetime | str | None = None,
    source_refs: Sequence[dict[str, Any]] | None = None,
) -> CryptoPerpEvent | None:
    if not bars:
        return None
    cutoff = ensure_utc_aware(
        "information_cutoff_at",
        information_cutoff_at or max(item.ts_available for item in bars),
    )
    available_bars = [item for item in bars if item.ts_available <= cutoff]
    if not quality_report.event_generation_allowed or not available_bars:
        return None

    features = compute_event_features(
        bars=available_bars,
        ticker=ticker,
        detector_config=detector_config,
    )
    family = _family(features, detector_config)
    if family is None:
        return None

    event_id = _event_id(
        provider_id=provider_id,
        native_symbol=native_symbol,
        detector_version=detector_config.detector_version,
        first_detected_at=cutoff,
    )
    return CryptoPerpEvent(
        artifact_id=stable_hash(["crypto-perp-event-artifact", event_id]),
        created_at=cutoff,
        producer=CryptoPerpProducer(command="crypto-perp-refresh"),
        source_refs=_source_refs(source_refs),
        event_id=event_id,
        event_family=family,
        provider_id=provider_id,
        native_symbol=native_symbol,
        canonical_symbol=canonical_symbol,
        first_detected_at=cutoff,
        information_cutoff_at=cutoff,
        universe_snapshot_id=universe_snapshot_id,
        market_snapshot_id=market_snapshot_id,
        detector_version=detector_config.detector_version,
        detector_config_hash=_detector_config_hash(detector_config),
        features_at_detection=features,
        market_context=MarketContext(),
        data_quality=EventDataQuality(status="PASS", reason_codes=[]),
        capture_request=EventCaptureRequest(
            requested=True,
            channels=list(detector_config.capture_channels),
            duration_minutes=detector_config.capture_duration_minutes,
        ),
        status="CAPTURE_REQUESTED",
    )
