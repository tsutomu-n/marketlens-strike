from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.core.context import DecisionContext
from sis.core.decision import RiskDecision
from sis.models import MarketStatus, QuoteLog, Venue
from sis.risk.halt_policy import evaluate_halt_reasons, load_halt_policy
from sis.risk.scalping_policy import check_timeframe


def _quote_from_row(row: dict[str, Any]) -> QuoteLog:
    payload = {
        "ts_client": row["ts_client"],
        "venue": Venue(str(row["venue"]).lower()),
        "canonical_symbol": str(row["canonical_symbol"]).upper(),
        "venue_symbol": str(row.get("venue_symbol") or f"{row['canonical_symbol']}/USD"),
        "pair_index": row.get("pair_index"),
        "pair_id": row.get("pair_id"),
        "chain": row.get("chain"),
        "mark_price": row.get("mark_price"),
        "index_price": row.get("index_price"),
        "oracle_price": row.get("oracle_price"),
        "bid_price": row.get("bid_price"),
        "ask_price": row.get("ask_price"),
        "mid_price": row.get("mid_price"),
        "exec_buy_price": row.get("exec_buy_price"),
        "exec_sell_price": row.get("exec_sell_price"),
        "spread_bps": row.get("spread_bps"),
        "oracle_ts_ms": row.get("oracle_ts_ms"),
        "market_status": MarketStatus(str(row.get("market_status", "unknown")).lower()),
        "is_tradable": bool(row.get("is_tradable")),
        "source": str(row.get("source") or "backtest"),
        "raw_payload_sha256": str(row.get("raw_payload_sha256") or "backtest"),
        "raw_payload_ref": row.get("raw_payload_ref"),
        "raw_payload": row.get("raw_payload"),
    }
    if isinstance(payload["ts_client"], str):
        payload["ts_client"] = datetime.fromisoformat(payload["ts_client"].replace("Z", "+00:00"))
    return QuoteLog(**payload)


def evaluate_risk_gate(
    context: DecisionContext,
    row: dict[str, Any],
    *,
    policy: dict | None = None,
    enforce_live_stale: bool = False,
) -> RiskDecision:
    decision = check_timeframe(context.timeframe)
    reasons: list[str] = []
    if not decision.allowed:
        reasons.append(decision.reason)

    quote = _quote_from_row(row)
    if quote.oracle_ts_ms is None:
        reasons.append("BLOCK_ORACLE_TIMESTAMP_MISSING")

    halt_reasons = evaluate_halt_reasons(quote, policy or load_halt_policy())
    if not enforce_live_stale:
        halt_reasons = [reason for reason in halt_reasons if reason != "BLOCK_PRICE_STALE"]
    reasons.extend(halt_reasons)
    deduped = list(dict.fromkeys(reasons))
    stale_rejected = any(reason in {"BLOCK_PRICE_STALE", "BLOCK_ORACLE_TIMESTAMP_MISSING"} for reason in deduped)
    halt_rejected = any(reason not in {"BLOCK_PRICE_STALE", "BLOCK_ORACLE_TIMESTAMP_MISSING"} for reason in deduped)
    return RiskDecision(
        allowed=not deduped,
        blocked_reasons=deduped,
        stale_rejected=stale_rejected,
        halt_rejected=halt_rejected,
    )
