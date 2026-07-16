from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
)

ActionPolicy = Literal[
    "CURRENT_SELECTOR",
    "ALWAYS_CONTINUATION",
    "ALWAYS_REVERSAL",
    "NO_TRADE",
]
MetricScenario = Literal["BASE", "STRESS"]
SameTimestampCashPolicy = Literal["NO_SAME_TIMESTAMP_REUSE", "EXIT_THEN_ENTRY"]
TradeAction = Literal["REVERSAL_SHORT", "CONTINUATION_LONG"]
TradeSide = Literal["LONG", "SHORT"]
RunStatus = Literal["COMPLETE", "INCONCLUSIVE", "INVALID_INPUT"]
TimelineEventKind = Literal[
    "ENTRY_ACCEPTED",
    "ENTRY_REJECTED",
    "EXIT_SETTLED",
    "EXIT_BLOCKED",
    "NO_TRADE_SKIPPED",
    "UNKNOWN_SKIPPED",
]


def _serialize_decimal(value: Decimal | None) -> str | None:
    return None if value is None else decimal_to_json_string(value)


class PortfolioCapacityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    initial_cash_usd: DecimalValue = Field(gt=0)
    max_open_positions: int | None = Field(default=None, ge=1)
    max_open_positions_per_symbol: int = Field(default=1, ge=1)
    action_policy: ActionPolicy = "CURRENT_SELECTOR"
    metric_scenario: MetricScenario = "STRESS"
    same_timestamp_cash_policy: SameTimestampCashPolicy = "NO_SAME_TIMESTAMP_REUSE"
    reserve_policy: Literal["NOTIONAL_PLUS_ESTIMATED_TRADING_COSTS"] = (
        "NOTIONAL_PLUS_ESTIMATED_TRADING_COSTS"
    )
    priority_policy: Literal["FIRST_OBSERVED"] = "FIRST_OBSERVED"

    @field_serializer("initial_cash_usd")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class PortfolioTradeIntent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    outcome_id: str
    symbol: str
    action: TradeAction
    side: TradeSide
    information_cutoff_at: datetime
    entry_at: datetime
    exit_at: datetime
    source_row_index: int = Field(ge=0)
    signal_score: DecimalValue | None = None
    notional_usd: DecimalValue = Field(gt=0)
    before_cost_proxy_usd: DecimalValue
    fee_estimate_usd: DecimalValue = Field(ge=0)
    funding_estimate_usd: DecimalValue = Field(ge=0)
    slippage_estimate_usd: DecimalValue = Field(ge=0)
    operator_time_cost_usd: DecimalValue = Field(ge=0)
    stress_slippage_estimate_usd: DecimalValue = Field(ge=0)
    account_delta_base_usd: DecimalValue
    account_delta_stress_usd: DecimalValue
    economic_delta_base_usd: DecimalValue
    economic_delta_stress_usd: DecimalValue
    reserve_base_usd: DecimalValue = Field(gt=0)
    reserve_stress_usd: DecimalValue = Field(gt=0)
    known_gaps: list[str] = Field(default_factory=list)

    @field_validator("event_id", "outcome_id")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("symbol must not be empty")
        return stripped

    @field_validator("information_cutoff_at", "entry_at", "exit_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @model_validator(mode="after")
    def validate_timeline_and_side(self) -> PortfolioTradeIntent:
        if not self.information_cutoff_at < self.entry_at < self.exit_at:
            raise ValueError("information_cutoff_at < entry_at < exit_at is required")
        expected_side = "LONG" if self.action == "CONTINUATION_LONG" else "SHORT"
        if self.side != expected_side:
            raise ValueError("trade side does not match action")
        if self.stress_slippage_estimate_usd < self.slippage_estimate_usd:
            raise ValueError("stress slippage must be >= base slippage")
        return self

    @field_serializer("information_cutoff_at", "entry_at", "exit_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "signal_score",
        "notional_usd",
        "before_cost_proxy_usd",
        "fee_estimate_usd",
        "funding_estimate_usd",
        "slippage_estimate_usd",
        "operator_time_cost_usd",
        "stress_slippage_estimate_usd",
        "account_delta_base_usd",
        "account_delta_stress_usd",
        "economic_delta_base_usd",
        "economic_delta_stress_usd",
        "reserve_base_usd",
        "reserve_stress_usd",
    )
    def serialize_decimals(self, value: Decimal | None) -> str | None:
        return _serialize_decimal(value)


class PortfolioSkippedSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    symbol: str
    selected_action: Literal["NO_TRADE", "UNKNOWN"]
    information_cutoff_at: datetime
    source_row_index: int = Field(ge=0)

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        stripped = value.strip().upper()
        if not stripped:
            raise ValueError("symbol must not be empty")
        return stripped

    @field_validator("information_cutoff_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("information_cutoff_at", value)

    @field_serializer("information_cutoff_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class PortfolioCapacityCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_portfolio_capacity_case.v1"] = (
        "crypto_perp_portfolio_capacity_case.v1"
    )
    case_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    pack_id: str
    row_set_id: str
    evidence_basis: Literal["BAR_PROXY"] = "BAR_PROXY"
    policy: PortfolioCapacityPolicy
    intents: list[PortfolioTradeIntent]
    skipped_signals: list[PortfolioSkippedSignal]
    known_limits: list[str]

    @field_validator("case_id", "pack_id", "row_set_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("identifier must not be empty")
        return stripped

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class PortfolioTimelineRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    timestamp: datetime
    event_kind: TimelineEventKind
    event_id: str
    symbol: str
    action: str
    available_cash_before_usd: DecimalValue
    available_cash_after_usd: DecimalValue
    reserved_cash_before_usd: DecimalValue
    reserved_cash_after_usd: DecimalValue
    open_position_count_before: int = Field(ge=0)
    open_position_count_after: int = Field(ge=0)
    account_delta_usd: DecimalValue = Decimal("0")
    economic_delta_usd: DecimalValue = Decimal("0")
    reason_code: str | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "available_cash_before_usd",
        "available_cash_after_usd",
        "reserved_cash_before_usd",
        "reserved_cash_after_usd",
        "account_delta_usd",
        "economic_delta_usd",
    )
    def serialize_decimals(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class PortfolioCapacityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_portfolio_capacity_result.v1"] = (
        "crypto_perp_portfolio_capacity_result.v1"
    )
    result_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    case_id: str
    pack_id: str
    row_set_id: str
    engine_id: Literal["decimal_reference"] = "decimal_reference"
    evidence_basis: Literal["BAR_PROXY"] = "BAR_PROXY"
    metric_scenario: MetricScenario
    same_timestamp_cash_policy: SameTimestampCashPolicy
    initial_cash_usd: DecimalValue
    final_available_cash_usd: DecimalValue
    final_reserved_cash_usd: DecimalValue
    simulated_account_pnl_estimate_usd: DecimalValue
    economic_result_estimate_usd: DecimalValue
    accepted_trade_count: int = Field(ge=0)
    rejected_trade_count: int = Field(ge=0)
    skipped_trade_count: int = Field(ge=0)
    peak_open_positions: int = Field(ge=0)
    peak_reserved_cash_usd: DecimalValue = Field(ge=0)
    peak_capital_utilization: DecimalValue = Field(ge=0)
    settled_cash_drawdown_estimate_usd: DecimalValue = Field(le=0)
    accepted_action_counts: dict[str, int]
    rejected_reason_counts: dict[str, int]
    rejected_counterfactual_estimate_usd: DecimalValue
    run_status: RunStatus
    known_limits: list[str]
    timeline: list[PortfolioTimelineRow]
    actual_cash_used: Literal[False] = False
    profit_proven: Literal[False] = False
    mark_to_market_modeled: Literal[False] = False
    liquidation_modeled: Literal[False] = False

    @model_validator(mode="after")
    def validate_complete_result(self) -> PortfolioCapacityResult:
        if self.run_status == "COMPLETE" and self.final_reserved_cash_usd != 0:
            raise ValueError("complete result must have zero reserved cash")
        return self

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "initial_cash_usd",
        "final_available_cash_usd",
        "final_reserved_cash_usd",
        "simulated_account_pnl_estimate_usd",
        "economic_result_estimate_usd",
        "peak_reserved_cash_usd",
        "peak_capital_utilization",
        "settled_cash_drawdown_estimate_usd",
        "rejected_counterfactual_estimate_usd",
    )
    def serialize_decimals(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class VectorbtDifferentialResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_portfolio_capacity_vectorbt_diff.v1"] = (
        "crypto_perp_portfolio_capacity_vectorbt_diff.v1"
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    case_id: str
    reference_result_id: str
    vectorbt_version: str | None
    run_status: Literal["COMPLETED", "SKIPPED", "FAILED"]
    decision: Literal["MATCH", "MISMATCH", "VECTORBT_NOT_AVAILABLE", "VECTORBT_NOT_APPLICABLE"]
    reference_trade_count: int = Field(ge=0)
    vectorbt_order_count: int | None = Field(default=None, ge=0)
    reference_gross_and_fixed_cost_usd: DecimalValue
    vectorbt_total_profit_usd: DecimalValue | None = None
    absolute_difference_usd: DecimalValue | None = None
    tolerance_usd: DecimalValue = Decimal("0.000001")
    validated_components: list[str]
    unvalidated_components: list[str]
    reason_codes: list[str]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @field_serializer(
        "reference_gross_and_fixed_cost_usd",
        "vectorbt_total_profit_usd",
        "absolute_difference_usd",
        "tolerance_usd",
    )
    def serialize_decimals(self, value: Decimal | None) -> str | None:
        return _serialize_decimal(value)
