from __future__ import annotations

from pathlib import Path

import yaml

from sis.models import QuoteLog

DEFAULT_MARK_INDEX_DIVERGENCE_BPS = 25.0


def load_halt_policy(path: Path = Path("configs/halt_policy.yaml")) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def summarize_halt_policy(policy: dict) -> list[str]:
    halt = policy.get("halt_policy", policy)
    stale = halt.get("stale_price", {})
    session = halt.get("session", {})
    spread = halt.get("spread", {}).get("max_spread_p90_bps", {})
    return [
        f"gtrade_max_age_ms={stale.get('gtrade_max_age_ms')}",
        f"ostium_max_age_ms={stale.get('ostium_max_age_ms')}",
        f"block_before_close_minutes={session.get('block_before_close_minutes')}",
        f"block_after_open_minutes={session.get('block_after_open_minutes')}",
        f"spread_limits={spread}",
    ]


def _halt(policy: dict) -> dict:
    return policy.get("halt_policy", policy)


def stale_reason(quote: QuoteLog, policy: dict) -> str | None:
    if quote.oracle_ts_ms is None:
        return None
    import time

    stale = _halt(policy).get("stale_price", {})
    max_age = stale.get(f"{quote.venue.value}_max_age_ms")
    if not isinstance(max_age, int | float):
        return None
    if int(time.time() * 1000) - quote.oracle_ts_ms > max_age:
        return "BLOCK_PRICE_STALE"
    return None


def spread_reason(quote: QuoteLog, policy: dict) -> str | None:
    if quote.spread_bps is None:
        return None
    limits = _halt(policy).get("spread", {}).get("max_spread_p90_bps", {})
    limit = limits.get(quote.canonical_symbol)
    if isinstance(limit, int | float) and quote.spread_bps > limit:
        return "BLOCK_SPREAD_TOO_WIDE"
    return None


def mark_index_divergence_reason(
    quote: QuoteLog,
    max_divergence_bps: float = DEFAULT_MARK_INDEX_DIVERGENCE_BPS,
) -> str | None:
    if quote.mark_price is None or quote.index_price is None or quote.index_price == 0:
        return None
    divergence = abs(quote.mark_price - quote.index_price) / quote.index_price * 10_000
    if divergence > max_divergence_bps:
        return "BLOCK_MARK_INDEX_DIVERGENCE"
    return None


def evaluate_halt_reasons(quote: QuoteLog, policy: dict) -> list[str]:
    reasons: list[str] = []
    if quote.market_status.value != "open" or not quote.is_tradable:
        reasons.append("BLOCK_MARKET_CLOSED")
    for reason in (
        stale_reason(quote, policy),
        spread_reason(quote, policy),
        mark_index_divergence_reason(quote),
    ):
        if reason:
            reasons.append(reason)
    return reasons
