from __future__ import annotations

from decimal import Decimal

from sis.crypto_perp.models import CryptoPerpAction


def rank_directional_actions(
    *,
    event_return: Decimal,
    spread_bps: Decimal,
    funding_rate: Decimal,
    min_abs_event_return_bps: Decimal,
) -> dict[CryptoPerpAction, Decimal]:
    event_return_bps = event_return * Decimal("10000")
    funding_bps = abs(funding_rate * Decimal("10000"))
    friction_bps = abs(spread_bps) + funding_bps
    reversal_score = -event_return_bps - friction_bps
    continuation_score = event_return_bps - friction_bps
    no_trade_score = Decimal("0")
    if abs(event_return_bps) < min_abs_event_return_bps:
        reversal_score -= min_abs_event_return_bps
        continuation_score -= min_abs_event_return_bps
    return {
        CryptoPerpAction.REVERSAL_SHORT: reversal_score,
        CryptoPerpAction.CONTINUATION_LONG: continuation_score,
        CryptoPerpAction.NO_TRADE: no_trade_score,
    }


def select_action(scores: dict[CryptoPerpAction, Decimal]) -> CryptoPerpAction:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered:
        return CryptoPerpAction.UNKNOWN
    if len(ordered) > 1 and ordered[0][1] == ordered[1][1]:
        return CryptoPerpAction.NO_TRADE
    selected, score = ordered[0]
    if score <= 0:
        return CryptoPerpAction.NO_TRADE
    return selected
