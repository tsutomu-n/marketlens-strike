from __future__ import annotations

from datetime import datetime, timezone

from sis.real_market.models import RealMarketBar


def estimate_source_confidence(
    bar: RealMarketBar,
    *,
    now: datetime | None = None,
    max_delay_seconds: float = 300.0,
    has_secondary_agreement: bool = False,
    market_session_resolved: bool = True,
) -> float:
    now = now or datetime.now(timezone.utc)
    ts_end = (
        bar.ts_end if bar.ts_end.tzinfo is not None else bar.ts_end.replace(tzinfo=timezone.utc)
    )
    delay = max((now - ts_end).total_seconds(), 0.0)

    score = 0.0
    if bar.close > 0:
        score += 0.25
    if bar.volume is not None and bar.volume >= 0:
        score += 0.20
    if delay <= max_delay_seconds:
        score += 0.20
    if market_session_resolved:
        score += 0.20
    if has_secondary_agreement:
        score += 0.15
    return min(score, 1.0)


def source_confidence_reasons(score: float, threshold: float = 0.70) -> list[str]:
    return [] if score >= threshold else ["BLOCK_LOW_SOURCE_CONFIDENCE"]


def live_suitability_reasons(
    *,
    source_confidence: float,
    providers: list[str],
    threshold: float = 0.70,
) -> list[str]:
    reasons = source_confidence_reasons(source_confidence, threshold=threshold)
    normalized = {item.strip().lower() for item in providers}
    if normalized == {"yfinance"}:
        reasons.append("BLOCK_YFINANCE_ONLY_LIVE")
    return list(dict.fromkeys(reasons))
