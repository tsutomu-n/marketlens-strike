from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

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
CashMetricBasis = Literal["actual_cash", "before_cost_proxy", "cost_adjusted_estimate", "mixed"]
TOURNAMENT_ACTIONS: tuple[TournamentAction, ...] = (
    "REVERSAL_SHORT",
    "CONTINUATION_LONG",
    "NO_TRADE",
)
NON_ACTUAL_CASH_KNOWN_GAPS = {
    "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH",
    "ESTIMATE_NOT_ACTUAL_CASH",
}
PRIMARY_METRIC_DISPLAY_NAMES: dict[CashMetricBasis, str] = {
    "actual_cash": "actual_cash_result_usd",
    "before_cost_proxy": "before_cost_proxy_usd",
    "cost_adjusted_estimate": "cost_adjusted_cash_estimate_usd",
    "mixed": "mixed_cash_metric_basis",
}


class TournamentEventResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    action: TournamentAction
    cash_metric_value_usd: DecimalValue
    actual_cash_result_usd: DecimalValue | None = None
    cash_metric_basis: Literal["actual_cash", "before_cost_proxy", "cost_adjusted_estimate"] = (
        "actual_cash"
    )
    market_adjusted_return: DecimalValue
    operator_time_minutes: DecimalValue
    near_miss: bool = False

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_cash_metric(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        migrated = dict(data)
        if "cash_metric_value_usd" not in migrated and "actual_cash_result_usd" in migrated:
            migrated["cash_metric_value_usd"] = migrated["actual_cash_result_usd"]
        basis = migrated.get("cash_metric_basis", "actual_cash")
        if basis == "actual_cash" and migrated.get("actual_cash_result_usd") is None:
            migrated["actual_cash_result_usd"] = migrated.get("cash_metric_value_usd")
        if basis != "actual_cash":
            migrated["actual_cash_result_usd"] = None
        return migrated

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

    @field_serializer("cash_metric_value_usd", "market_adjusted_return", "operator_time_minutes")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)

    @field_serializer("actual_cash_result_usd")
    def serialize_optional_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


class TournamentScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: TournamentAction
    event_count: int = Field(ge=0)
    cash_metric_value_usd: DecimalValue
    actual_cash_result_usd: DecimalValue | None = None
    largest_loss_usd: DecimalValue
    profit_concentration: DecimalValue
    market_adjusted_return: DecimalValue
    near_miss_count: int = Field(ge=0)
    operator_time_minutes: DecimalValue

    @field_serializer(
        "actual_cash_result_usd",
        "cash_metric_value_usd",
        "largest_loss_usd",
        "profit_concentration",
        "market_adjusted_return",
        "operator_time_minutes",
    )
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
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
    primary_metric_display_name: str = "actual_cash_result_usd"
    cash_metric_basis: CashMetricBasis = "actual_cash"
    actual_cash: bool = True
    tournament_status: Literal["COMPLETE", "INCONCLUSIVE_DATA"]
    leader_action: TournamentAction | None
    leader_cash_metric_value_usd: DecimalValue | None = None
    leader_actual_cash_result_usd: DecimalValue | None = None
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

    @field_serializer("leader_cash_metric_value_usd", "leader_actual_cash_result_usd")
    def serialize_optional_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return decimal_to_json_string(value)


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
    cash_values = [row.cash_metric_value_usd for row in action_rows]
    actual_cash_basis = all(row.cash_metric_basis == "actual_cash" for row in action_rows)
    largest_loss = min(cash_values) if cash_values else _ZERO
    return TournamentScore(
        action=action,
        event_count=len(action_rows),
        cash_metric_value_usd=sum(cash_values, _ZERO),
        actual_cash_result_usd=sum(cash_values, _ZERO) if actual_cash_basis else None,
        largest_loss_usd=largest_loss,
        profit_concentration=_profit_concentration(cash_values),
        market_adjusted_return=sum((row.market_adjusted_return for row in action_rows), _ZERO),
        near_miss_count=sum(1 for row in action_rows if row.near_miss),
        operator_time_minutes=sum((row.operator_time_minutes for row in action_rows), _ZERO),
    )


def _leader(scores: Sequence[TournamentScore]) -> TournamentAction | None:
    ordered = sorted(scores, key=lambda score: score.cash_metric_value_usd, reverse=True)
    if len(ordered) < 2:
        return None
    if ordered[0].cash_metric_value_usd == ordered[1].cash_metric_value_usd:
        return None
    return ordered[0].action


def _cash_metric_basis(
    rows: Sequence[TournamentEventResult], known_gaps: Sequence[str]
) -> CashMetricBasis:
    if any(gap in NON_ACTUAL_CASH_KNOWN_GAPS for gap in known_gaps):
        if "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH" in known_gaps:
            return "before_cost_proxy"
        return "cost_adjusted_estimate"
    row_bases = {row.cash_metric_basis for row in rows}
    if len(row_bases) == 1:
        return row_bases.pop()
    return "mixed"


def _summary(
    *,
    report_id: str,
    tournament_status: Literal["COMPLETE", "INCONCLUSIVE_DATA"],
    leader_action: TournamentAction | None,
    event_count: int,
    scores: Sequence[TournamentScore],
    cash_metric_basis: CashMetricBasis,
    actual_cash: bool,
) -> dict[str, Any]:
    leader_score = next((score for score in scores if score.action == leader_action), None)
    leader_value = leader_score.cash_metric_value_usd if leader_score is not None else None
    return {
        "report_id": report_id,
        "tournament_status": tournament_status,
        "leader_action": leader_action,
        "primary_metric": "actual_cash_result_usd",
        "primary_metric_display_name": PRIMARY_METRIC_DISPLAY_NAMES[cash_metric_basis],
        "cash_metric_basis": cash_metric_basis,
        "actual_cash": actual_cash,
        "event_count": event_count,
        "leader_cash_metric_value_usd": leader_value,
        "leader_actual_cash_result_usd": leader_value if actual_cash else None,
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
    if min_events <= 0:
        raise ValueError("min_events must be positive")
    generated = ensure_utc_aware("generated_at", generated_at)
    row_list = list(rows)
    event_set = _validate_same_event_set(row_list)
    computed_gaps = list(known_gaps or [])
    cash_metric_basis = _cash_metric_basis(row_list, computed_gaps)
    actual_cash = cash_metric_basis == "actual_cash"
    if not actual_cash:
        row_list = [row.model_copy(update={"actual_cash_result_usd": None}) for row in row_list]
    scores = [_score(row_list, action) for action in TOURNAMENT_ACTIONS]
    inconclusive_reasons: list[str] = []
    leader_action = _leader(scores)
    if len(event_set) < min_events:
        inconclusive_reasons.append("INSUFFICIENT_EVENT_COUNT")
    if leader_action is None:
        inconclusive_reasons.append("TIE_ON_ACTUAL_CASH")
    if cash_metric_basis == "mixed":
        inconclusive_reasons.append("MIXED_CASH_METRIC_BASIS")
    tournament_status: Literal["COMPLETE", "INCONCLUSIVE_DATA"] = (
        "INCONCLUSIVE_DATA" if inconclusive_reasons else "COMPLETE"
    )
    if tournament_status == "INCONCLUSIVE_DATA":
        leader_action = None
    if cash_metric_basis == "mixed":
        computed_gaps.append("MIXED_CASH_METRIC_BASIS")
    if tournament_status == "INCONCLUSIVE_DATA":
        computed_gaps.append("INCONCLUSIVE_DATA")
    computed_gaps = list(dict.fromkeys(computed_gaps))
    report_summary = _summary(
        report_id=report_id,
        tournament_status=tournament_status,
        leader_action=leader_action,
        event_count=len(event_set),
        scores=scores,
        cash_metric_basis=cash_metric_basis,
        actual_cash=actual_cash,
    )
    leader_score = next((score for score in scores if score.action == leader_action), None)
    leader_value = leader_score.cash_metric_value_usd if leader_score is not None else None
    return CryptoPerpTournamentReport(
        artifact_id=stable_hash(
            ["crypto-perp-tournament-report-artifact", report_id, serialize_utc_z(generated)]
        ),
        created_at=generated,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=list(source_refs or []),
        report_id=report_id,
        generated_at=generated,
        primary_metric_display_name=PRIMARY_METRIC_DISPLAY_NAMES[cash_metric_basis],
        cash_metric_basis=cash_metric_basis,
        actual_cash=actual_cash,
        tournament_status=tournament_status,
        leader_action=leader_action,
        leader_cash_metric_value_usd=leader_value,
        leader_actual_cash_result_usd=leader_value if actual_cash else None,
        event_set=event_set,
        event_count=len(event_set),
        scores=scores,
        rows=row_list,
        inconclusive_reasons=list(dict.fromkeys(inconclusive_reasons)),
        known_gaps=computed_gaps,
        summary=report_summary,
    )
