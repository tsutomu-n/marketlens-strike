from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from sis.paper.fills import PaperFill
from sis.paper.orders import PaperOrder
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview

__all__ = ["paper_observation_payload", "quote_age_ms", "write_observation"]


def write_observation(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def quote_age_ms(now: datetime, quote_ts: datetime | None) -> int | None:
    if quote_ts is None:
        return None
    return int((now - quote_ts).total_seconds() * 1000)


def paper_observation_payload(
    *,
    intent: PaperIntentPreview,
    status: str,
    now: datetime,
    block_reasons: list[str],
    quote: dict[str, Any] | None = None,
    quote_ts: datetime | None = None,
    order: PaperOrder | None = None,
    fill: PaperFill | None = None,
) -> dict[str, Any]:
    quantity = float(intent.quantity or 1.0)
    notional = intent.notional_usd
    if notional is None and fill is not None:
        notional = float(fill.price) * quantity
    return {
        "created_at": now.isoformat(),
        "intent_id": intent.intent_id,
        "candidate_id": intent.candidate_id,
        "venue": intent.execution_venue,
        "execution_symbol": intent.execution_symbol,
        "real_market_symbol": intent.real_market_symbol,
        "status": status,
        "block_reasons": block_reasons,
        "quote_ts": quote_ts.isoformat() if quote_ts is not None else None,
        "quote_age_ms": quote_age_ms(now, quote_ts),
        "market_status": str(quote.get("market_status", "unknown")) if quote else None,
        "is_tradable": bool(quote.get("is_tradable")) if quote else None,
        "spread_bps": float(quote["spread_bps"])
        if quote and quote.get("spread_bps") is not None
        else None,
        "source_confidence": float(quote["source_confidence"])
        if quote and quote.get("source_confidence") is not None
        else None,
        "venue_quality_score": float(quote["venue_quality_score"])
        if quote and quote.get("venue_quality_score") is not None
        else None,
        "notional_usd": notional,
        "quantity": quantity,
        "order_id": order.order_id if order else None,
        "fill_id": fill.fill_id if fill else None,
        "source_operator_promotion_path": intent.operator_promotion_path,
        "source_operator_promotion_hash": intent.operator_promotion_hash,
        "live_order_submitted": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "venue_write_used": False,
    }
