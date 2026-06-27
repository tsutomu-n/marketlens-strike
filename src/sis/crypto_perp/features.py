from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bars import CandleBar
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.heartbeat import MarketTickerSnapshot
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)


if TYPE_CHECKING:
    from sis.crypto_perp.events import CryptoPerpEvent
    from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability


FEATURE_PACK_SCHEMA_VERSION = "crypto_perp_feature_pack.v1"


class EventDetectorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detector_version: str = "crypto_perp_event_detector.v1"
    slow_return_threshold: DecimalValue = Field(default=Decimal("0.04"))
    slow_turnover_impulse_threshold: DecimalValue = Field(default=Decimal("0.15"))
    fast_abs_return_floor: DecimalValue = Field(default=Decimal("0.03"))
    fast_robust_z_threshold: DecimalValue = Field(default=Decimal("3.0"))
    fast_turnover_percentile_threshold: DecimalValue = Field(default=Decimal("0.95"))
    near_miss_ratio: DecimalValue = Field(default=Decimal("0.80"))
    capture_duration_minutes: int = 360
    capture_channels: tuple[str, ...] = ("trades", "books1", "books15")


class EventFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    return_15m: str
    return_60m: str
    return_74h: str
    recent_turnover: str
    previous_turnover: str
    turnover_impulse: str
    robust_return_z: str
    turnover_percentile: str
    spread_bps: str
    mark_index_basis_bps: str
    funding_rate: str
    open_interest_raw: str


class MarketContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    btc_return: str = "0"
    eth_return: str = "0"
    cross_section_median_return: str = "0"
    breadth: str = "0"
    market_adjusted_return: str = "0"


class CryptoPerpFeaturePack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_feature_pack.v1"] = FEATURE_PACK_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    feature_pack_id: str
    event_id: str
    information_cutoff_at: datetime
    event_return: str
    turnover_impulse: str
    spread_bps: str
    mark_index_basis_bps: str
    funding_rate: str
    trade_sign_imbalance: str | None = None
    ofi: str | None = None
    depth_10bps: str | None = None
    available_optional_features: list[str]
    known_gaps: list[str]
    summary: dict[str, object]

    @field_validator("created_at", "information_cutoff_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "information_cutoff_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _decimals(values: Sequence[str]) -> list[Decimal]:
    return [Decimal(value) for value in values]


def _return(closes: Sequence[Decimal], periods: int) -> Decimal:
    if len(closes) <= periods or closes[-periods - 1] == 0:
        return Decimal("0")
    return closes[-1] / closes[-periods - 1] - Decimal("1")


def _median(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / Decimal("2")


def _robust_return_z(closes: Sequence[Decimal], periods: int) -> Decimal:
    current = abs(_return(closes, periods))
    samples = [
        abs(closes[index] / closes[index - periods] - Decimal("1"))
        for index in range(periods, len(closes) - 1)
        if closes[index - periods] != 0
    ]
    median = _median(samples)
    deviations = [abs(item - median) for item in samples]
    mad = _median(deviations)
    if mad == 0:
        return Decimal("999") if current > median else Decimal("0")
    return abs(current - median) / (mad * Decimal("1.4826"))


def _turnover_percentile(turnovers: Sequence[Decimal], periods: int) -> Decimal:
    if len(turnovers) < periods:
        return Decimal("0")
    current = sum(turnovers[-periods:])
    samples = [
        sum(turnovers[index - periods : index]) for index in range(periods, len(turnovers) + 1)
    ]
    if not samples:
        return Decimal("0")
    below_or_equal = sum(1 for item in samples if item <= current)
    return Decimal(below_or_equal) / Decimal(len(samples))


def _mark_index_basis_bps(ticker: MarketTickerSnapshot) -> str:
    index_price = Decimal(ticker.index_price)
    if index_price == 0:
        return "0"
    basis = (Decimal(ticker.mark_price) - index_price) / index_price * Decimal("10000")
    return decimal_to_json_string(basis)


def compute_event_features(
    *,
    bars: Sequence[CandleBar],
    ticker: MarketTickerSnapshot,
    detector_config: EventDetectorConfig,
) -> EventFeatures:
    sorted_bars = sorted(bars, key=lambda item: item.ts_open)
    closes = _decimals([item.close for item in sorted_bars])
    turnovers = _decimals([item.quote_turnover for item in sorted_bars])
    recent_turnover = sum(turnovers[-296:], Decimal("0")) if len(turnovers) >= 296 else Decimal("0")
    previous_turnover = (
        sum(turnovers[-592:-296], Decimal("0")) if len(turnovers) >= 592 else Decimal("0")
    )
    turnover_impulse = (
        recent_turnover / previous_turnover - Decimal("1")
        if previous_turnover != 0
        else Decimal("0")
    )

    return EventFeatures(
        return_15m=decimal_to_json_string(_return(closes, 1)),
        return_60m=decimal_to_json_string(_return(closes, 4)),
        return_74h=decimal_to_json_string(_return(closes, 296)),
        recent_turnover=decimal_to_json_string(recent_turnover),
        previous_turnover=decimal_to_json_string(previous_turnover),
        turnover_impulse=decimal_to_json_string(turnover_impulse),
        robust_return_z=decimal_to_json_string(_robust_return_z(closes, 4)),
        turnover_percentile=decimal_to_json_string(_turnover_percentile(turnovers, 4)),
        spread_bps=ticker.spread_bps,
        mark_index_basis_bps=_mark_index_basis_bps(ticker),
        funding_rate=ticker.funding_rate,
        open_interest_raw=ticker.open_interest_raw,
    )


def _event_return(features: EventFeatures, event_family: str) -> str:
    if event_family == "slow_pump_74h_v1":
        return features.return_74h
    if event_family == "fast_pump_1h_v1":
        return features.return_60m
    return features.return_60m


def _event_source_refs(event: CryptoPerpEvent) -> list[dict[str, str]]:
    return [ref.model_dump(mode="json") for ref in event.source_refs]


def _optional_feature_gap(
    *,
    name: str,
    value: Decimal | None,
    source_available: bool,
) -> str | None:
    if value is not None:
        return None
    if not source_available:
        return f"{name.upper()}_SOURCE_MISSING"
    return f"{name.upper()}_NOT_PROVIDED"


def build_feature_pack(
    *,
    event: CryptoPerpEvent,
    source_availability: CryptoPerpSourceAvailability,
    created_at: datetime | str,
    trade_sign_imbalance: Decimal | None = None,
    ofi: Decimal | None = None,
    depth_10bps: Decimal | None = None,
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-feature-pack",
) -> CryptoPerpFeaturePack:
    if source_availability.event_id != event.event_id:
        raise ValueError("source availability event_id must match event")
    created = ensure_utc_aware("created_at", created_at)
    features = event.features_at_detection
    optional_features: list[str] = []
    if trade_sign_imbalance is not None:
        optional_features.append("trade_sign_imbalance")
    if ofi is not None:
        optional_features.append("ofi")
    if depth_10bps is not None:
        optional_features.append("depth_10bps")
    computed_gaps = [
        *source_availability.known_gaps,
        *(known_gaps or []),
    ]
    optional_gaps = [
        _optional_feature_gap(
            name="trade_sign_imbalance",
            value=trade_sign_imbalance,
            source_available=source_availability.can_compute_trade_sign_imbalance,
        ),
        _optional_feature_gap(
            name="ofi",
            value=ofi,
            source_available=source_availability.can_compute_ofi,
        ),
        _optional_feature_gap(
            name="depth_10bps",
            value=depth_10bps,
            source_available=source_availability.can_compute_depth,
        ),
    ]
    computed_gaps.extend(gap for gap in optional_gaps if gap is not None)
    computed_gaps = list(dict.fromkeys(computed_gaps))
    refs = [
        *_event_source_refs(event),
        *source_availability.source_refs,
        *(dict(ref) for ref in source_refs or []),
    ]
    feature_pack_id = stable_hash(
        [
            "crypto-perp-feature-pack",
            event.event_id,
            serialize_utc_z(event.information_cutoff_at),
            features.model_dump(mode="json"),
            decimal_to_json_string(trade_sign_imbalance) if trade_sign_imbalance is not None else None,
            decimal_to_json_string(ofi) if ofi is not None else None,
            decimal_to_json_string(depth_10bps) if depth_10bps is not None else None,
            computed_gaps,
        ]
    )
    summary = {
        "event_id": event.event_id,
        "optional_feature_count": len(optional_features),
        "known_gap_count": len(computed_gaps),
        "sets_entry_action": False,
    }
    return CryptoPerpFeaturePack(
        artifact_id=stable_hash(["crypto-perp-feature-pack-artifact", feature_pack_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=refs,
        feature_pack_id=feature_pack_id,
        event_id=event.event_id,
        information_cutoff_at=event.information_cutoff_at,
        event_return=_event_return(features, event.event_family),
        turnover_impulse=features.turnover_impulse,
        spread_bps=features.spread_bps,
        mark_index_basis_bps=features.mark_index_basis_bps,
        funding_rate=features.funding_rate,
        trade_sign_imbalance=(
            decimal_to_json_string(trade_sign_imbalance)
            if trade_sign_imbalance is not None
            else None
        ),
        ofi=decimal_to_json_string(ofi) if ofi is not None else None,
        depth_10bps=decimal_to_json_string(depth_10bps) if depth_10bps is not None else None,
        available_optional_features=optional_features,
        known_gaps=computed_gaps,
        summary=summary,
    )
