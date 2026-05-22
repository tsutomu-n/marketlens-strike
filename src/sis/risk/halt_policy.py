from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from sis.models import AssetClass, QuoteLog

DEFAULT_MARK_INDEX_DIVERGENCE_BPS = 25.0
EASTERN = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class PositionContext:
    side: str
    liquidation_price: float | None = None
    leverage: float | None = None


@dataclass(frozen=True)
class CostContext:
    total_cost_bps: float | None = None
    max_cost_bps: float | None = None


@dataclass(frozen=True)
class EventWindow:
    starts_at: datetime
    ends_at: datetime
    label: str = "event"


def load_halt_policy(path: Path = Path("configs/halt_policy.yaml")) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def summarize_halt_policy(policy: dict) -> list[str]:
    halt = policy.get("halt_policy", policy)
    stale = halt.get("stale_price", {})
    session = halt.get("session", {})
    spread = halt.get("spread", {}).get("max_spread_p90_bps", {})
    liquidation = halt.get("liquidation", {})
    return [
        f"gtrade_max_age_ms={stale.get('gtrade_max_age_ms')}",
        f"ostium_max_age_ms={stale.get('ostium_max_age_ms')}",
        f"block_before_close_minutes={session.get('block_before_close_minutes')}",
        f"block_after_open_minutes={session.get('block_after_open_minutes')}",
        f"spread_limits={spread}",
        f"near_liquidation_bps={liquidation.get('near_liquidation_bps')}",
    ]


def _halt(policy: dict) -> dict:
    return policy.get("halt_policy", policy)


def stale_reason(quote: QuoteLog, policy: dict) -> str | None:
    if quote.oracle_ts_ms is None:
        return None

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


def _eastern_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo("UTC"))
    return value.astimezone(EASTERN)


def _asset_class_for_symbol(symbol: str) -> AssetClass:
    if symbol in {"SPY", "QQQ", "SPX_EQUIV", "NDX_EQUIV"}:
        return AssetClass.INDEX
    if symbol == "XAU":
        return AssetClass.COMMODITY
    return AssetClass.UNKNOWN


def _session_close_for_quote(quote: QuoteLog) -> datetime | None:
    local = _eastern_dt(quote.ts_client)
    asset_class = _asset_class_for_symbol(quote.canonical_symbol)
    weekday = local.weekday()
    if asset_class == AssetClass.INDEX:
        if weekday >= 5:
            return None
        return local.replace(hour=16, minute=0, second=0, microsecond=0)
    if asset_class == AssetClass.COMMODITY:
        if weekday == 4:
            return local.replace(hour=17, minute=0, second=0, microsecond=0)
        if weekday in {0, 1, 2, 3}:
            return local.replace(hour=17, minute=0, second=0, microsecond=0)
    return None


def session_end_reason(quote: QuoteLog, policy: dict) -> str | None:
    close = _session_close_for_quote(quote)
    if close is None:
        return "BLOCK_WEEKEND_HOLD" if quote.ts_client.astimezone(EASTERN).weekday() >= 5 else None
    local = _eastern_dt(quote.ts_client)
    if local > close:
        return None
    minutes = _halt(policy).get("session", {}).get("block_before_close_minutes", 30)
    if not isinstance(minutes, int | float):
        minutes = 30
    if close - local <= timedelta(minutes=float(minutes)):
        return "BLOCK_SESSION_END_NEAR"
    return None


def near_liquidation_reason(
    quote: QuoteLog,
    policy: dict,
    position: PositionContext | None,
) -> str | None:
    if position is None or position.liquidation_price is None:
        return None
    price = quote.mark_price or quote.mid_price or quote.oracle_price or quote.index_price
    if price is None or price <= 0:
        return "BLOCK_UNKNOWN_PRICE_REFERENCE"

    side = position.side.lower()
    if side == "long":
        distance_bps = (price - position.liquidation_price) / price * 10_000
    elif side == "short":
        distance_bps = (position.liquidation_price - price) / price * 10_000
    else:
        return "BLOCK_UNKNOWN_PRICE_REFERENCE"

    threshold = _halt(policy).get("liquidation", {}).get("near_liquidation_bps", 100)
    if not isinstance(threshold, int | float):
        threshold = 100
    if distance_bps <= threshold:
        return "BLOCK_NEAR_LIQUIDATION"
    return None


def leverage_reason(policy: dict, position: PositionContext | None) -> str | None:
    if position is None or position.leverage is None:
        return None
    prohibited_above = _halt(policy).get("leverage", {}).get("prohibited_above")
    if isinstance(prohibited_above, int | float) and position.leverage > prohibited_above:
        return "BLOCK_NEAR_LIQUIDATION"
    return None


def cost_reason(cost: CostContext | None) -> str | None:
    if cost is None or cost.total_cost_bps is None or cost.max_cost_bps is None:
        return None
    if cost.total_cost_bps > cost.max_cost_bps:
        return "BLOCK_COST_TOO_HIGH"
    return None


def event_window_reason(quote: QuoteLog, event_windows: list[EventWindow] | None) -> str | None:
    if not event_windows:
        return None
    ts = quote.ts_client
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    for window in event_windows:
        starts_at = window.starts_at
        ends_at = window.ends_at
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=ZoneInfo("UTC"))
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=ZoneInfo("UTC"))
        if starts_at <= ts <= ends_at:
            return "BLOCK_EVENT_WINDOW"
    return None


def evaluate_halt_reasons(
    quote: QuoteLog,
    policy: dict,
    position: PositionContext | None = None,
    cost: CostContext | None = None,
    registry_complete: bool = True,
    event_windows: list[EventWindow] | None = None,
) -> list[str]:
    reasons: list[str] = []
    if not registry_complete:
        reasons.append("BLOCK_REGISTRY_INCOMPLETE")
    if quote.market_status.value != "open" or not quote.is_tradable:
        reasons.append("BLOCK_MARKET_CLOSED")
    for reason in (
        stale_reason(quote, policy),
        session_end_reason(quote, policy),
        event_window_reason(quote, event_windows),
        spread_reason(quote, policy),
        mark_index_divergence_reason(quote),
        cost_reason(cost),
        near_liquidation_reason(quote, policy, position),
        leverage_reason(policy, position),
    ):
        if reason:
            reasons.append(reason)
    return reasons
