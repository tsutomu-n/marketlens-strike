from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

from sis.real_market.calendar import market_session
from sis.real_market.models import RealMarketBar, RealMarketFeature
from sis.real_market.quality import estimate_source_confidence, live_suitability_reasons


def _return(prev: float, curr: float) -> float | None:
    if prev <= 0:
        return None
    return curr / prev - 1.0


def _stddev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(max(variance, 0.0))


def _volume_zscore(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    std = _stddev(values)
    if std is None or std == 0:
        return None
    return (values[-1] - mean) / std


def build_feature_from_bars(
    bars: list[RealMarketBar],
    *,
    event_flags: list[str] | None = None,
    now: datetime | None = None,
    has_secondary_agreement: bool = False,
    providers: list[str] | None = None,
) -> RealMarketFeature:
    if not bars:
        raise ValueError("bars must not be empty")
    ordered = sorted(bars, key=lambda row: row.ts_end)
    latest = ordered[-1]
    prev = ordered[-2] if len(ordered) >= 2 else None

    returns = []
    for left, right in zip(ordered[:-1], ordered[1:], strict=False):
        if left.close > 0:
            returns.append(math.log(right.close / left.close))

    volumes = [row.volume for row in ordered[-5:] if isinstance(row.volume, (int, float))]

    current_session = market_session(latest.ts_end)
    score = estimate_source_confidence(
        latest,
        now=now or datetime.now(timezone.utc),
        has_secondary_agreement=has_secondary_agreement,
        market_session_resolved=current_session != "unknown",
    )
    block_reasons = live_suitability_reasons(
        source_confidence=score,
        providers=providers or [latest.source],
    )

    return RealMarketFeature(
        ts=latest.ts_end,
        symbol=latest.symbol,
        timeframe=latest.timeframe,
        close=latest.close,
        return_5m=None,
        return_15m=_return(prev.close, latest.close) if prev else None,
        realized_vol_15m=_stddev(returns),
        volume_zscore_15m=_volume_zscore([float(v) for v in volumes]),
        source_confidence=score,
        market_session=current_session,
        event_flags=event_flags or [],
        block_reasons=block_reasons,
    )


def write_real_market_quality_report(
    *,
    bars: list[RealMarketBar],
    out_path: Path,
) -> None:
    providers = sorted({row.source for row in bars})
    symbols = sorted({row.symbol for row in bars})
    volume_available = sum(1 for row in bars if row.volume is not None)
    missing_rate = 0.0 if bars else 1.0
    delay_estimate = max((row.delay_seconds or 0.0) for row in bars) if bars else None
    volume_ratio = volume_available / len(bars) if bars else 0.0
    live_suitability = "blocked" if providers == ["yfinance"] else "candidate"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(
            [
                "# Free Real Market Data Quality Report",
                "",
                "## provider coverage",
                f"- providers: {providers}",
                "",
                "## missing rate",
                f"- missing_rate: {missing_rate:.3f}",
                "",
                "## delay estimate",
                f"- delay_seconds_max: {delay_estimate}",
                "",
                "## volume availability",
                f"- volume_availability_ratio: {volume_ratio:.3f}",
                "",
                "## symbol coverage",
                f"- symbols: {symbols}",
                "",
                "## live suitability",
                f"- status: {live_suitability}",
                "",
            ]
        ),
        encoding="utf-8",
    )
