from __future__ import annotations

from typing import Any

from sis.core.decision import DecisionRecord
from sis.core.execution_plan import ExecutionPlan
from sis.paper.fills import PaperFill


def _price_for_action(action: str, row: dict[str, Any]) -> tuple[float | None, str | None]:
    if action == "enter_long":
        for key in ("best_ask", "ask_price", "mid_price", "mark_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value), key
        return None, None
    if action == "enter_short":
        for key in ("best_bid", "bid_price", "mid_price", "mark_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value), key
        return None, None
    if action == "exit_long":
        for key in ("best_bid", "bid_price", "mid_price", "mark_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value), key
        return None, None
    if action == "exit_short":
        for key in ("best_ask", "ask_price", "mid_price", "mark_price"):
            value = row.get(key)
            if isinstance(value, int | float) and value > 0:
                return float(value), key
        return None, None
    return None, None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _round_trip_cost_bps(
    *,
    quote_row: dict[str, Any],
    fee_model: dict[str, Any],
) -> tuple[str | None, float | None]:
    mode = quote_row.get("fee_mode")
    fee_mode = mode if isinstance(mode, str) else None
    venue = str(quote_row.get("venue") or "trade_xyz").strip().lower()
    trade_cfg = fee_model.get("fee_model", {}).get(venue, {}) if isinstance(fee_model, dict) else {}
    fallback = trade_cfg.get("fallback", {}) if isinstance(trade_cfg, dict) else {}
    fallback_cfg = fallback.get(fee_mode or "standard", fallback.get("standard", {}))
    taker = _as_float(quote_row.get("taker_fee_bps"))
    maker = _as_float(quote_row.get("maker_fee_bps"))
    entry_fee = taker if taker is not None else _as_float(fallback_cfg.get("taker_bps"))
    exit_fee = maker if maker is not None else _as_float(fallback_cfg.get("maker_bps"))
    if entry_fee is None:
        entry_fee = 0.0
    if exit_fee is None:
        exit_fee = 0.0
    spread = _as_float(quote_row.get("spread_bps")) or 0.0
    estimated_slippage_bps = spread / 2
    funding_rate = _as_float(quote_row.get("funding_rate"))
    funding_bps = abs(funding_rate * 10_000) if funding_rate is not None else 0.0
    return fee_mode, entry_fee + exit_fee + estimated_slippage_bps + funding_bps


def _gate_reasons(
    *,
    quote_row: dict[str, Any],
    min_source_confidence: float,
    min_venue_quality_score: float,
    max_spread_bps: float,
    min_depth_10bps_usd: float,
    max_abs_funding_bps: float,
) -> list[str]:
    reasons: list[str] = []
    if quote_row.get("trade_allowed") is False:
        reasons.append("BLOCK_TRACKING_DISALLOWS_TRADE")
    source_confidence = _as_float(quote_row.get("source_confidence"))
    if source_confidence is not None and source_confidence < min_source_confidence:
        reasons.append("BLOCK_LOW_SOURCE_CONFIDENCE")
    venue_quality_score = _as_float(quote_row.get("venue_quality_score"))
    if venue_quality_score is not None and venue_quality_score < min_venue_quality_score:
        reasons.append("BLOCK_LOW_VENUE_QUALITY")
    if str(quote_row.get("market_status", "")).lower() != "open":
        reasons.append("BLOCK_MARKET_CLOSED")
    if quote_row.get("is_tradable") is False:
        reasons.append("BLOCK_VENUE_NOT_TRADABLE")
    spread_bps = _as_float(quote_row.get("spread_bps"))
    if spread_bps is not None and spread_bps > max_spread_bps:
        reasons.append("BLOCK_SPREAD_TOO_WIDE")
    depth = _as_float(quote_row.get("depth_10bps_usd"))
    if depth is not None and depth < min_depth_10bps_usd:
        reasons.append("BLOCK_DEPTH_TOO_THIN")
    funding_rate = _as_float(quote_row.get("funding_rate"))
    if funding_rate is not None:
        funding_bps = abs(funding_rate * 10_000)
        if funding_bps > max_abs_funding_bps:
            reasons.append("BLOCK_FUNDING_TOO_HIGH")
    return list(dict.fromkeys(reasons))


class PaperBroker:
    def __init__(
        self,
        *,
        halt_policy: dict | None = None,
        fee_model: dict | None = None,
    ) -> None:
        halt = halt_policy.get("halt_policy", halt_policy) if isinstance(halt_policy, dict) else {}
        tracking = halt.get("tracking", {}) if isinstance(halt, dict) else {}
        spread = halt.get("spread", {}).get("max_spread_bps", {}) if isinstance(halt, dict) else {}
        funding = halt.get("funding", {}) if isinstance(halt, dict) else {}
        self.min_source_confidence = float(tracking.get("min_source_confidence", 0.70))
        self.min_venue_quality_score = float(tracking.get("min_venue_quality_score", 0.70))
        self.max_spread_bps = float(spread.get("default_equity", 25))
        self.min_depth_10bps_usd = float(tracking.get("min_depth_10bps_usd", 1000))
        self.max_abs_funding_bps = float(funding.get("max_abs_funding_rate_hourly_bps", 5))
        self.fee_model = fee_model if isinstance(fee_model, dict) else {}

    def create_fill(
        self,
        execution_plan: ExecutionPlan,
        decision_record: DecisionRecord,
        quote_row: dict[str, Any],
        *,
        quantity: float = 1.0,
    ) -> PaperFill | None:
        if execution_plan.action == "skip":
            return None
        reasons = _gate_reasons(
            quote_row=quote_row,
            min_source_confidence=self.min_source_confidence,
            min_venue_quality_score=self.min_venue_quality_score,
            max_spread_bps=self.max_spread_bps,
            min_depth_10bps_usd=self.min_depth_10bps_usd,
            max_abs_funding_bps=self.max_abs_funding_bps,
        )
        if reasons:
            return None
        price, price_source = _price_for_action(execution_plan.action, quote_row)
        if price is None:
            return None
        fee_mode, round_trip_cost_bps = _round_trip_cost_bps(
            quote_row=quote_row, fee_model=self.fee_model
        )
        return PaperFill(
            ts_fill=decision_record.context.quote_ts,
            venue=execution_plan.venue,
            canonical_symbol=execution_plan.canonical_symbol,
            side=decision_record.strategy_decision.side,
            action=execution_plan.action,
            quantity=quantity,
            price=price,
            strategy_name=decision_record.strategy_decision.strategy_name,
            source_confidence=_as_float(quote_row.get("source_confidence")),
            venue_quality_score=_as_float(quote_row.get("venue_quality_score")),
            block_reasons=reasons,
            fee_mode=fee_mode,
            estimated_round_trip_cost_bps=round_trip_cost_bps,
            fill_price_source=price_source,
            notes=execution_plan.notes[:],
        )
