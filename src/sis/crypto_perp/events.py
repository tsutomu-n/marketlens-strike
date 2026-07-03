from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
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
EventFamily = Literal["slow_pump_74h_v1", "fast_pump_1h_v1", "near_miss_v1", "market_window_v1"]


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


def _decimal_to_string(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


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


def _read_strategy_input_csv(
    *,
    input_csv: Path,
    symbol: str,
    information_cutoff_at: datetime,
) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    reason_codes: list[str] = []
    with input_csv.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = {"ts", "available_at", "symbol", "open", "high", "low", "close", "quote_vol"}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError("input_csv missing columns: " + ",".join(missing))
        for row in reader:
            if row["symbol"] != symbol:
                continue
            available = ensure_utc_aware("available_at", row["available_at"])
            if available <= information_cutoff_at:
                rows.append(row)
    rows.sort(key=lambda item: ensure_utc_aware("ts", item["ts"]))
    if len(rows) < 2:
        raise ValueError("input_csv has fewer than two rows at information cutoff")
    return rows, reason_codes


def _minutes_between(first: str, second: str) -> int:
    left = ensure_utc_aware("ts", first)
    right = ensure_utc_aware("ts", second)
    return int((right - left).total_seconds() // 60)


def _period_return(closes: Sequence[Decimal], periods: int) -> Decimal:
    if periods <= 0 or len(closes) <= periods:
        return Decimal("0")
    reference = closes[-periods - 1]
    if reference == 0:
        return Decimal("0")
    return closes[-1] / reference - Decimal("1")


def build_market_window_event(
    *,
    input_csv: Path,
    symbol: str,
    information_cutoff_at: datetime | str,
    lookback_minutes: int = 60,
    source_refs: Sequence[dict[str, str]] | None = None,
    producer_command: str = "crypto-perp-event-record",
) -> CryptoPerpEvent:
    cutoff = ensure_utc_aware("information_cutoff_at", information_cutoff_at)
    rows, reason_codes = _read_strategy_input_csv(
        input_csv=input_csv,
        symbol=symbol,
        information_cutoff_at=cutoff,
    )
    interval_minutes = _minutes_between(rows[-2]["ts"], rows[-1]["ts"])
    if interval_minutes <= 0:
        raise ValueError("input_csv timestamps must be strictly increasing")

    closes = [_decimal(row["close"]) for row in rows]
    turnovers = [_decimal(row["quote_vol"]) for row in rows]
    periods_15m = max(1, 15 // interval_minutes)
    periods_60m = max(1, lookback_minutes // interval_minutes)
    periods_74h = max(1, (74 * 60) // interval_minutes)
    if len(closes) <= periods_74h:
        reason_codes.append("RETURN_74H_UNAVAILABLE_SOURCE_WINDOW_TOO_SHORT")
    if len(closes) <= periods_60m:
        reason_codes.append("LOOKBACK_RETURN_UNAVAILABLE_SOURCE_WINDOW_TOO_SHORT")
    recent_turnover = (
        sum(turnovers[-periods_60m:], Decimal("0"))
        if len(turnovers) >= periods_60m
        else Decimal("0")
    )
    previous_turnover = (
        sum(turnovers[-periods_60m * 2 : -periods_60m], Decimal("0"))
        if len(turnovers) >= periods_60m * 2
        else Decimal("0")
    )
    turnover_impulse = (
        recent_turnover / previous_turnover - Decimal("1")
        if previous_turnover != 0
        else Decimal("0")
    )
    if previous_turnover == 0:
        reason_codes.append("PREVIOUS_TURNOVER_WINDOW_UNAVAILABLE")
    reason_codes.append("MARKET_WINDOW_EVENT_NOT_DETECTOR_TRIGGER")
    reason_codes.append("TICKER_CONTEXT_NOT_INCLUDED_IN_CSV")

    event_id = stable_hash(
        [
            "crypto-perp-market-window-event",
            symbol,
            serialize_utc_z(cutoff),
            stable_hash([input_csv.as_posix(), input_csv.read_text(encoding="utf-8")]),
        ]
    )
    return CryptoPerpEvent(
        artifact_id=stable_hash(["crypto-perp-market-window-event-artifact", event_id]),
        created_at=cutoff,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=_source_refs(source_refs),
        event_id=event_id,
        event_family="market_window_v1",
        provider_id="bitget",
        native_symbol=symbol,
        canonical_symbol=symbol,
        first_detected_at=cutoff,
        information_cutoff_at=cutoff,
        universe_snapshot_id=stable_hash(
            ["market-window-universe", symbol, serialize_utc_z(cutoff)]
        ),
        market_snapshot_id=stable_hash(["market-window-market", symbol, serialize_utc_z(cutoff)]),
        detector_version="market_window_csv.v1",
        detector_config_hash=stable_hash(["market-window-csv", lookback_minutes, interval_minutes]),
        features_at_detection=EventFeatures(
            return_15m=_decimal_to_string(_period_return(closes, periods_15m)),
            return_60m=_decimal_to_string(_period_return(closes, periods_60m)),
            return_74h=_decimal_to_string(_period_return(closes, periods_74h)),
            recent_turnover=_decimal_to_string(recent_turnover),
            previous_turnover=_decimal_to_string(previous_turnover),
            turnover_impulse=_decimal_to_string(turnover_impulse),
            robust_return_z="0",
            turnover_percentile="0",
            spread_bps="0",
            mark_index_basis_bps="0",
            funding_rate="0",
            open_interest_raw="0",
        ),
        market_context=MarketContext(),
        data_quality=EventDataQuality(
            status="PASS", reason_codes=list(dict.fromkeys(reason_codes))
        ),
        capture_request=EventCaptureRequest(
            requested=False,
            channels=[],
            duration_minutes=max(1, lookback_minutes),
        ),
        status="CAPTURE_COMPLETE",
    )


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
