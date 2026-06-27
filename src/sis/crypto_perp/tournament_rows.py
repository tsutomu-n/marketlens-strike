from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.tournament import TOURNAMENT_ACTIONS, TournamentAction, TournamentEventResult


TOURNAMENT_ROWS_V2_SCHEMA_VERSION = "crypto_perp_tournament_rows.v2"


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


class CostAwareTournamentRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    action: TournamentAction
    before_cost_proxy_usd: Decimal
    fee_estimate_usd: Decimal
    funding_estimate_usd: Decimal
    slippage_estimate_usd: Decimal
    operator_time_cost_usd: Decimal
    cost_adjusted_cash_estimate_usd: Decimal
    stress_cash_estimate_usd: Decimal
    evidence_level: Literal["cost_adjusted_estimate", "actual_cash"]
    actual_cash_result_usd: Decimal | None = None
    market_adjusted_return: Decimal
    operator_time_minutes: Decimal
    known_gaps: list[str]
    near_miss: bool = False

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_validator(
        "fee_estimate_usd",
        "funding_estimate_usd",
        "slippage_estimate_usd",
        "operator_time_cost_usd",
        "operator_time_minutes",
    )
    @classmethod
    def validate_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("cost and time estimates must be non-negative")
        return value

    @field_serializer(
        "before_cost_proxy_usd",
        "fee_estimate_usd",
        "funding_estimate_usd",
        "slippage_estimate_usd",
        "operator_time_cost_usd",
        "cost_adjusted_cash_estimate_usd",
        "stress_cash_estimate_usd",
        "actual_cash_result_usd",
        "market_adjusted_return",
        "operator_time_minutes",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return str(value.normalize()) if value != value.to_integral() else str(value.quantize(Decimal("1")))


class CryptoPerpTournamentRowsV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_tournament_rows.v2"] = TOURNAMENT_ROWS_V2_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    row_set_id: str
    primary_metric: Literal["cost_adjusted_cash_estimate_usd"] = (
        "cost_adjusted_cash_estimate_usd"
    )
    event_set: list[str]
    rows: list[CostAwareTournamentRow]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _matured_horizon(outcome: CryptoPerpOutcome):
    matured_horizons = [horizon for horizon in outcome.horizons if horizon.matured]
    if not matured_horizons:
        raise ValueError("outcome must contain at least one matured horizon")
    return matured_horizons[0]


def _source_refs_for_outcomes(outcomes: Sequence[CryptoPerpOutcome]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for outcome in outcomes:
        refs.extend(ref.model_dump(mode="json") for ref in outcome.source_refs)
    return refs


def _actual_cash(
    actual_cash_by_event_action: Mapping[tuple[str, TournamentAction], Decimal] | None,
    *,
    event_id: str,
    action: TournamentAction,
) -> Decimal | None:
    if actual_cash_by_event_action is None:
        return None
    return actual_cash_by_event_action.get((event_id, action))


def _cost_aware_row(
    *,
    event_id: str,
    action: TournamentAction,
    before_cost_proxy_usd: Decimal,
    market_adjusted_return: Decimal,
    notional_usd: Decimal,
    horizon_minutes: int,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    operator_time_minutes: Decimal,
    operator_hourly_cost_usd: Decimal,
    stress_slippage_multiplier: Decimal,
    actual_cash_result_usd: Decimal | None,
    extra_known_gaps: Sequence[str],
    near_miss: bool,
) -> CostAwareTournamentRow:
    is_trade = action != "NO_TRADE"
    fee = notional_usd * fee_rate * Decimal("2") if is_trade else Decimal("0")
    holding_fraction = Decimal(horizon_minutes) / Decimal("480")
    funding = abs(notional_usd * funding_rate * holding_fraction) if is_trade else Decimal("0")
    slippage = notional_usd * abs(slippage_bps) / Decimal("10000") if is_trade else Decimal("0")
    operator_cost = (
        operator_time_minutes * operator_hourly_cost_usd / Decimal("60")
        if is_trade
        else Decimal("0")
    )
    cost_adjusted = before_cost_proxy_usd - fee - funding - slippage - operator_cost
    stress = before_cost_proxy_usd - fee - funding - (
        slippage * stress_slippage_multiplier
    ) - operator_cost
    known_gaps = list(extra_known_gaps)
    if actual_cash_result_usd is None and is_trade:
        known_gaps.append("ACTUAL_CASH_RESULT_NOT_AVAILABLE")
        known_gaps.append("ESTIMATE_NOT_ACTUAL_CASH")
    return CostAwareTournamentRow(
        event_id=event_id,
        action=action,
        before_cost_proxy_usd=before_cost_proxy_usd,
        fee_estimate_usd=fee,
        funding_estimate_usd=funding,
        slippage_estimate_usd=slippage,
        operator_time_cost_usd=operator_cost,
        cost_adjusted_cash_estimate_usd=cost_adjusted,
        stress_cash_estimate_usd=stress,
        evidence_level="actual_cash" if actual_cash_result_usd is not None else "cost_adjusted_estimate",
        actual_cash_result_usd=actual_cash_result_usd,
        market_adjusted_return=market_adjusted_return,
        operator_time_minutes=operator_time_minutes if is_trade else Decimal("0"),
        known_gaps=list(dict.fromkeys(known_gaps)),
        near_miss=near_miss,
    )


def _rows_for_outcome(
    *,
    outcome: CryptoPerpOutcome,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    operator_time_minutes: Decimal,
    operator_hourly_cost_usd: Decimal,
    stress_slippage_multiplier: Decimal,
    actual_cash_by_event_action: Mapping[tuple[str, TournamentAction], Decimal] | None,
) -> list[CostAwareTournamentRow]:
    horizon = _matured_horizon(outcome)
    event_id = outcome.event_id
    extra_known_gaps = list(outcome.known_gaps)
    if horizon.high_first_low_first == "AMBIGUOUS":
        extra_known_gaps.append("AMBIGUOUS_HIGH_LOW_ORDERING")
    action_inputs: dict[TournamentAction, tuple[Decimal, Decimal]] = {
        "REVERSAL_SHORT": (
            horizon.short_return_before_cost * notional_usd,
            -horizon.market_adjusted_return,
        ),
        "CONTINUATION_LONG": (
            horizon.long_return_before_cost * notional_usd,
            horizon.market_adjusted_return,
        ),
        "NO_TRADE": (Decimal("0"), Decimal("0")),
    }
    return [
        _cost_aware_row(
            event_id=event_id,
            action=action,
            before_cost_proxy_usd=action_inputs[action][0],
            market_adjusted_return=action_inputs[action][1],
            notional_usd=notional_usd,
            horizon_minutes=horizon.horizon_minutes,
            fee_rate=fee_rate,
            funding_rate=funding_rate,
            slippage_bps=slippage_bps,
            operator_time_minutes=operator_time_minutes,
            operator_hourly_cost_usd=operator_hourly_cost_usd,
            stress_slippage_multiplier=stress_slippage_multiplier,
            actual_cash_result_usd=_actual_cash(
                actual_cash_by_event_action,
                event_id=event_id,
                action=action,
            ),
            extra_known_gaps=extra_known_gaps,
            near_miss=bool(outcome.near_miss_refs),
        )
        for action in TOURNAMENT_ACTIONS
    ]


def _leader_action(rows: Sequence[CostAwareTournamentRow]) -> TournamentAction | None:
    by_action: dict[TournamentAction, Decimal] = {
        action: sum(
            (
                row.cost_adjusted_cash_estimate_usd
                for row in rows
                if row.action == action
            ),
            Decimal("0"),
        )
        for action in TOURNAMENT_ACTIONS
    }
    ordered = sorted(by_action.items(), key=lambda item: item[1], reverse=True)
    if len(ordered) < 2 or ordered[0][1] == ordered[1][1]:
        return None
    return ordered[0][0]


def build_cost_aware_tournament_rows(
    *,
    outcomes: Sequence[CryptoPerpOutcome],
    created_at: datetime | str,
    notional_usd: Decimal,
    fee_rate: Decimal = Decimal("0.0006"),
    funding_rate: Decimal = Decimal("0"),
    slippage_bps: Decimal = Decimal("0"),
    operator_time_minutes: Decimal = Decimal("0"),
    operator_hourly_cost_usd: Decimal = Decimal("0"),
    stress_slippage_multiplier: Decimal = Decimal("2"),
    actual_cash_by_event_action: Mapping[tuple[str, TournamentAction], Decimal] | None = None,
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-tournament-rows-v2",
) -> CryptoPerpTournamentRowsV2:
    if not outcomes:
        raise ValueError("outcomes must not be empty")
    if notional_usd <= 0:
        raise ValueError("notional_usd must be positive")
    for value_name, value in {
        "fee_rate": fee_rate,
        "slippage_bps": slippage_bps,
        "operator_time_minutes": operator_time_minutes,
        "operator_hourly_cost_usd": operator_hourly_cost_usd,
        "stress_slippage_multiplier": stress_slippage_multiplier,
    }.items():
        if value < 0:
            raise ValueError(f"{value_name} must be non-negative")
    if stress_slippage_multiplier < 1:
        raise ValueError("stress_slippage_multiplier must be greater than or equal to 1")
    created = ensure_utc_aware("created_at", created_at)
    rows: list[CostAwareTournamentRow] = []
    for outcome in outcomes:
        rows.extend(
            _rows_for_outcome(
                outcome=outcome,
                notional_usd=notional_usd,
                fee_rate=fee_rate,
                funding_rate=funding_rate,
                slippage_bps=slippage_bps,
                operator_time_minutes=operator_time_minutes,
                operator_hourly_cost_usd=operator_hourly_cost_usd,
                stress_slippage_multiplier=stress_slippage_multiplier,
                actual_cash_by_event_action=actual_cash_by_event_action,
            )
        )
    event_set = sorted({row.event_id for row in rows})
    known_gap_list = list(known_gaps or [])
    for row in rows:
        known_gap_list.extend(row.known_gaps)
    known_gap_list = list(dict.fromkeys(known_gap_list))
    leader = _leader_action(rows)
    no_trade_total = sum(
        (row.cost_adjusted_cash_estimate_usd for row in rows if row.action == "NO_TRADE"),
        Decimal("0"),
    )
    leader_total = (
        sum(
            (
                row.cost_adjusted_cash_estimate_usd
                for row in rows
                if row.action == leader
            ),
            Decimal("0"),
        )
        if leader is not None
        else None
    )
    row_set_id = stable_hash(
        [
            "crypto-perp-tournament-rows-v2",
            [outcome.outcome_id for outcome in outcomes],
            serialize_utc_z(created),
            notional_usd,
            fee_rate,
            funding_rate,
            slippage_bps,
            operator_time_minutes,
            operator_hourly_cost_usd,
            [row.model_dump(mode="json") for row in rows],
        ]
    )
    summary = {
        "row_set_id": row_set_id,
        "event_count": len(event_set),
        "row_count": len(rows),
        "leader_action": leader,
        "leader_cost_adjusted_cash_estimate_usd": leader_total,
        "no_trade_cost_adjusted_cash_estimate_usd": no_trade_total,
        "leader_beats_no_trade": leader_total is not None and leader_total > no_trade_total,
        "known_gap_count": len(known_gap_list),
    }
    refs = [*_source_refs_for_outcomes(outcomes), *(dict(ref) for ref in source_refs or [])]
    return CryptoPerpTournamentRowsV2(
        artifact_id=stable_hash(["crypto-perp-tournament-rows-v2-artifact", row_set_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=refs,
        row_set_id=row_set_id,
        event_set=event_set,
        rows=rows,
        known_gaps=known_gap_list,
        summary=summary,
    )
