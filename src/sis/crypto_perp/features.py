from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from sis.crypto_perp.bars import CandleBar
from sis.crypto_perp.heartbeat import MarketTickerSnapshot
from sis.crypto_perp.models import DecimalValue, decimal_to_json_string


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
