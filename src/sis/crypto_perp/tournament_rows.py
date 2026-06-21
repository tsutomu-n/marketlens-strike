from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.tournament import TournamentEventResult


class CryptoPerpTournamentRowsPreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["crypto_perp_tournament_rows_preview.v1"] = (
        "crypto_perp_tournament_rows_preview.v1"
    )
    artifact_id: str
    producer: CryptoPerpProducer
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    event_id: str
    outcome_id: str
    primary_metric_source: Literal["outcome_before_cost_proxy"] = "outcome_before_cost_proxy"
    rows: list[TournamentEventResult]
    known_gaps: list[str]
    summary: dict[str, Any]


def build_tournament_rows_preview(
    *,
    outcome: CryptoPerpOutcome,
    notional_usd: Decimal,
    operator_time_minutes: Decimal = Decimal("0"),
) -> CryptoPerpTournamentRowsPreview:
    if notional_usd < 0:
        raise ValueError("notional_usd must be non-negative")
    matured_horizons = [horizon for horizon in outcome.horizons if horizon.matured]
    if not matured_horizons:
        raise ValueError("outcome must contain at least one matured horizon")
    horizon = matured_horizons[0]
    reversal_cash = horizon.short_return_before_cost * notional_usd
    continuation_cash = horizon.long_return_before_cost * notional_usd
    rows = [
        TournamentEventResult(
            event_id=outcome.event_id,
            action="REVERSAL_SHORT",
            actual_cash_result_usd=reversal_cash,
            market_adjusted_return=-horizon.market_adjusted_return,
            operator_time_minutes=operator_time_minutes,
        ),
        TournamentEventResult(
            event_id=outcome.event_id,
            action="CONTINUATION_LONG",
            actual_cash_result_usd=continuation_cash,
            market_adjusted_return=horizon.market_adjusted_return,
            operator_time_minutes=operator_time_minutes,
        ),
        TournamentEventResult(
            event_id=outcome.event_id,
            action="NO_TRADE",
            actual_cash_result_usd=Decimal("0"),
            market_adjusted_return=Decimal("0"),
            operator_time_minutes=Decimal("0"),
        ),
    ]
    known_gaps = list(outcome.known_gaps)
    known_gaps.append("OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH")
    known_gaps.append("FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED")
    if horizon.high_first_low_first == "AMBIGUOUS":
        known_gaps.append("AMBIGUOUS_HIGH_LOW_ORDERING")
    known_gaps = list(dict.fromkeys(known_gaps))
    summary = {
        "event_id": outcome.event_id,
        "outcome_id": outcome.outcome_id,
        "horizon_minutes": horizon.horizon_minutes,
        "notional_usd": str(notional_usd),
        "known_gap_count": len(known_gaps),
    }
    return CryptoPerpTournamentRowsPreview(
        artifact_id=stable_hash(["crypto-perp-tournament-rows-preview", summary]),
        producer=CryptoPerpProducer(command="crypto-perp-tournament-rows-preview"),
        event_id=outcome.event_id,
        outcome_id=outcome.outcome_id,
        rows=rows,
        known_gaps=known_gaps,
        summary=summary,
    )
