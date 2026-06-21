from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)


TOURNAMENT_SCHEMA_VERSION = "crypto_perp_tournament_report.v1"
TournamentAction = Literal["REVERSAL_SHORT", "CONTINUATION_LONG", "NO_TRADE"]
TOURNAMENT_ACTIONS: tuple[TournamentAction, ...] = (
    "REVERSAL_SHORT",
    "CONTINUATION_LONG",
    "NO_TRADE",
)


class TournamentEventResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    action: TournamentAction
    actual_cash_result_usd: DecimalValue
    market_adjusted_return: DecimalValue
    operator_time_minutes: DecimalValue
    near_miss: bool = False

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_validator("operator_time_minutes")
    @classmethod
    def validate_operator_time(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("operator_time_minutes must be non-negative")
        return value

    @field_serializer("actual_cash_result_usd", "market_adjusted_return", "operator_time_minutes")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class TournamentScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: TournamentAction
    event_count: int = Field(ge=0)
    actual_cash_result_usd: DecimalValue
    largest_loss_usd: DecimalValue
    profit_concentration: DecimalValue
    market_adjusted_return: DecimalValue
    near_miss_count: int = Field(ge=0)
    operator_time_minutes: DecimalValue

    @field_serializer(
        "actual_cash_result_usd",
        "largest_loss_usd",
        "profit_concentration",
        "market_adjusted_return",
        "operator_time_minutes",
    )
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CryptoPerpTournamentReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_tournament_report.v1"] = TOURNAMENT_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    report_id: str
    generated_at: datetime
    primary_metric: Literal["actual_cash_result_usd"] = "actual_cash_result_usd"
    tournament_status: Literal["COMPLETE", "INCONCLUSIVE_DATA"]
    leader_action: TournamentAction | None
    event_set: list[str]
    event_count: int = Field(ge=0)
    scores: list[TournamentScore]
    rows: list[TournamentEventResult]
    inconclusive_reasons: list[str]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", "generated_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_validator("artifact_id", "report_id")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_serializer("created_at", "generated_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


_ZERO = Decimal("0")


def _rows_for_action(
    rows: Sequence[TournamentEventResult], action: TournamentAction
) -> list[TournamentEventResult]:
    return [row for row in rows if row.action == action]


def _event_set(rows: Sequence[TournamentEventResult]) -> list[str]:
    return sorted({row.event_id for row in rows})


def _validate_same_event_set(rows: Sequence[TournamentEventResult]) -> list[str]:
    if not rows:
        raise ValueError("rows must not be empty")
    expected: list[str] | None = None
    for action in TOURNAMENT_ACTIONS:
        action_rows = _rows_for_action(rows, action)
        if not action_rows:
            raise ValueError("reversal, continuation, and no-trade must use the same event set")
        event_ids = _event_set(action_rows)
        if len(event_ids) != len(action_rows):
            raise ValueError("each action must contain one row per event")
        if expected is None:
            expected = event_ids
        elif event_ids != expected:
            raise ValueError("reversal, continuation, and no-trade must use the same event set")
    return expected or []


def _profit_concentration(values: Sequence[Decimal]) -> Decimal:
    positive_values = [value for value in values if value > 0]
    positive_total = sum(positive_values, _ZERO)
    if positive_total == 0:
        return _ZERO
    return max(positive_values) / positive_total


def _score(rows: Sequence[TournamentEventResult], action: TournamentAction) -> TournamentScore:
    action_rows = _rows_for_action(rows, action)
    cash_values = [row.actual_cash_result_usd for row in action_rows]
    largest_loss = min(cash_values) if cash_values else _ZERO
    return TournamentScore(
        action=action,
        event_count=len(action_rows),
        actual_cash_result_usd=sum(cash_values, _ZERO),
        largest_loss_usd=largest_loss,
        profit_concentration=_profit_concentration(cash_values),
        market_adjusted_return=sum((row.market_adjusted_return for row in action_rows), _ZERO),
        near_miss_count=sum(1 for row in action_rows if row.near_miss),
        operator_time_minutes=sum((row.operator_time_minutes for row in action_rows), _ZERO),
    )


def _leader(scores: Sequence[TournamentScore]) -> TournamentAction | None:
    ordered = sorted(scores, key=lambda score: score.actual_cash_result_usd, reverse=True)
    if len(ordered) < 2:
        return None
    if ordered[0].actual_cash_result_usd == ordered[1].actual_cash_result_usd:
        return None
    return ordered[0].action


def _summary(
    *,
    report_id: str,
    tournament_status: Literal["COMPLETE", "INCONCLUSIVE_DATA"],
    leader_action: TournamentAction | None,
    event_count: int,
    scores: Sequence[TournamentScore],
) -> dict[str, Any]:
    leader_score = next((score for score in scores if score.action == leader_action), None)
    return {
        "report_id": report_id,
        "tournament_status": tournament_status,
        "leader_action": leader_action,
        "primary_metric": "actual_cash_result_usd",
        "event_count": event_count,
        "leader_actual_cash_result_usd": (
            leader_score.actual_cash_result_usd if leader_score is not None else None
        ),
    }


def build_tournament_report(
    *,
    report_id: str,
    generated_at: datetime | str,
    rows: Sequence[TournamentEventResult],
    min_events: int,
    source_refs: Sequence[dict[str, str]] | None = None,
    known_gaps: Sequence[str] | None = None,
    producer_command: str = "crypto-perp-tournament-report",
) -> CryptoPerpTournamentReport:
    generated = ensure_utc_aware("generated_at", generated_at)
    row_list = list(rows)
    event_set = _validate_same_event_set(row_list)
    scores = [_score(row_list, action) for action in TOURNAMENT_ACTIONS]
    inconclusive_reasons: list[str] = []
    leader_action = _leader(scores)
    if len(event_set) < min_events:
        inconclusive_reasons.append("INSUFFICIENT_EVENT_COUNT")
    if leader_action is None:
        inconclusive_reasons.append("TIE_ON_ACTUAL_CASH")
    tournament_status: Literal["COMPLETE", "INCONCLUSIVE_DATA"] = (
        "INCONCLUSIVE_DATA" if inconclusive_reasons else "COMPLETE"
    )
    if tournament_status == "INCONCLUSIVE_DATA":
        leader_action = None
    computed_gaps = list(known_gaps or [])
    if tournament_status == "INCONCLUSIVE_DATA":
        computed_gaps.append("INCONCLUSIVE_DATA")
    computed_gaps = list(dict.fromkeys(computed_gaps))
    report_summary = _summary(
        report_id=report_id,
        tournament_status=tournament_status,
        leader_action=leader_action,
        event_count=len(event_set),
        scores=scores,
    )
    return CryptoPerpTournamentReport(
        artifact_id=stable_hash(
            ["crypto-perp-tournament-report-artifact", report_id, serialize_utc_z(generated)]
        ),
        created_at=generated,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=list(source_refs or []),
        report_id=report_id,
        generated_at=generated,
        tournament_status=tournament_status,
        leader_action=leader_action,
        event_set=event_set,
        event_count=len(event_set),
        scores=scores,
        rows=row_list,
        inconclusive_reasons=list(dict.fromkeys(inconclusive_reasons)),
        known_gaps=computed_gaps,
        summary=report_summary,
    )
