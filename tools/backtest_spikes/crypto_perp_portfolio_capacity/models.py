from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator


ActionPolicy = Literal[
    "CURRENT_SELECTOR",
    "ALWAYS_CONTINUATION",
    "ALWAYS_REVERSAL",
    "NO_TRADE",
]
MetricScenario = Literal["BASE", "STRESS"]
TimestampCashPolicy = Literal["NO_SAME_TIMESTAMP_REUSE", "EXIT_THEN_ENTRY"]
DECIMAL_ZERO = Decimal("0")


class DecimalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_serializer("*", when_used="json")
    def serialize_decimals(self, value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        return value


class PortfolioCapacityPolicy(DecimalModel):
    initial_cash_usd: Decimal = Field(ge=DECIMAL_ZERO)
    max_open_positions: int | None = Field(default=None, ge=1)
    max_open_positions_per_symbol: int = Field(default=1, ge=1)
    action_policy: ActionPolicy
    metric_scenario: MetricScenario
    same_timestamp_cash_policy: TimestampCashPolicy
    reserve_policy: Literal["NOTIONAL_PLUS_ESTIMATED_TRADING_COSTS"] = (
        "NOTIONAL_PLUS_ESTIMATED_TRADING_COSTS"
    )
    priority_policy: Literal["FIRST_OBSERVED"] = "FIRST_OBSERVED"


class PortfolioTradeIntent(DecimalModel):
    event_id: str
    outcome_id: str
    symbol: str
    action: Literal["REVERSAL_SHORT", "CONTINUATION_LONG"]
    side: Literal["LONG", "SHORT"]
    information_cutoff_at: datetime
    entry_at: datetime
    exit_at: datetime
    source_row_index: int = Field(ge=0)
    signal_score: Decimal | None
    notional_usd: Decimal = Field(gt=DECIMAL_ZERO)
    entry_price_proxy: Decimal = Field(gt=DECIMAL_ZERO)
    exit_price_proxy: Decimal = Field(ge=DECIMAL_ZERO)
    before_cost_proxy_usd: Decimal
    fee_estimate_usd: Decimal = Field(ge=DECIMAL_ZERO)
    funding_estimate_usd: Decimal = Field(ge=DECIMAL_ZERO)
    slippage_estimate_usd: Decimal = Field(ge=DECIMAL_ZERO)
    operator_time_cost_usd: Decimal = Field(ge=DECIMAL_ZERO)
    stress_slippage_estimate_usd: Decimal = Field(ge=DECIMAL_ZERO)
    account_delta_base_usd: Decimal
    account_delta_stress_usd: Decimal
    economic_delta_base_usd: Decimal
    economic_delta_stress_usd: Decimal
    reserve_base_usd: Decimal = Field(gt=DECIMAL_ZERO)
    reserve_stress_usd: Decimal = Field(gt=DECIMAL_ZERO)
    known_gaps: list[str]

    @model_validator(mode="after")
    def validate_window(self) -> PortfolioTradeIntent:
        if not self.information_cutoff_at < self.entry_at < self.exit_at:
            raise ValueError("information_cutoff_at < entry_at < exit_at is required")
        expected_side = "LONG" if self.action == "CONTINUATION_LONG" else "SHORT"
        if self.side != expected_side:
            raise ValueError("action and side are inconsistent")
        return self

    def reserve(self, scenario: MetricScenario) -> Decimal:
        return self.reserve_base_usd if scenario == "BASE" else self.reserve_stress_usd

    def account_delta(self, scenario: MetricScenario) -> Decimal:
        return self.account_delta_base_usd if scenario == "BASE" else self.account_delta_stress_usd

    def economic_delta(self, scenario: MetricScenario) -> Decimal:
        return (
            self.economic_delta_base_usd if scenario == "BASE" else self.economic_delta_stress_usd
        )


class PortfolioSkip(DecimalModel):
    event_id: str
    symbol: str
    action: Literal["NO_TRADE", "UNKNOWN"]
    entry_at: datetime
    reason_code: Literal["NO_TRADE_SKIPPED", "UNKNOWN_SKIPPED"]


class PortfolioCapacityCase(DecimalModel):
    case_id: str
    pack_id: str
    row_set_id: str
    policy: PortfolioCapacityPolicy
    intents: list[PortfolioTradeIntent]
    skips: list[PortfolioSkip] = Field(default_factory=list)


class PortfolioPosition(DecimalModel):
    event_id: str
    symbol: str
    action: str
    entry_at: datetime
    exit_at: datetime
    reserve_usd: Decimal
    account_delta_usd: Decimal
    economic_delta_usd: Decimal
    intent: PortfolioTradeIntent


class PortfolioTimelineRow(DecimalModel):
    timestamp: datetime
    event_kind: Literal[
        "ENTRY_ACCEPTED",
        "ENTRY_REJECTED",
        "EXIT_SETTLED",
        "NO_TRADE_SKIPPED",
        "UNKNOWN_SKIPPED",
    ]
    event_id: str
    symbol: str
    action: str
    available_cash_before_usd: Decimal
    available_cash_after_usd: Decimal
    reserved_cash_before_usd: Decimal
    reserved_cash_after_usd: Decimal
    open_position_count_before: int
    open_position_count_after: int
    account_delta_usd: Decimal
    economic_delta_usd: Decimal
    reason_code: str | None


class PortfolioCapacityResult(DecimalModel):
    schema_version: Literal["crypto_perp_portfolio_capacity_result.v1"] = (
        "crypto_perp_portfolio_capacity_result.v1"
    )
    result_id: str
    case_id: str
    pack_id: str
    row_set_id: str
    engine_id: Literal["decimal_reference"] = "decimal_reference"
    evidence_basis: Literal["BAR_PROXY"] = "BAR_PROXY"
    metric_scenario: MetricScenario
    same_timestamp_cash_policy: TimestampCashPolicy
    initial_cash_usd: Decimal
    final_available_cash_usd: Decimal
    final_reserved_cash_usd: Decimal
    simulated_account_pnl_estimate_usd: Decimal
    economic_result_estimate_usd: Decimal
    accepted_trade_count: int
    rejected_trade_count: int
    skipped_trade_count: int
    peak_open_positions: int
    peak_reserved_cash_usd: Decimal
    peak_capital_utilization: Decimal
    settled_cash_drawdown_estimate_usd: Decimal
    accepted_action_counts: dict[str, int]
    rejected_reason_counts: dict[str, int]
    rejected_counterfactual_estimate_usd: Decimal
    run_status: Literal["COMPLETE", "INCONCLUSIVE", "INVALID_INPUT"]
    known_limits: list[str]
    timeline: list[PortfolioTimelineRow]
    accepted_intents: list[PortfolioTradeIntent]
    actual_cash_used: Literal[False] = False
    profit_proven: Literal[False] = False
    mark_to_market_modeled: Literal[False] = False
    liquidation_modeled: Literal[False] = False


class RuntimeInventory(DecimalModel):
    pack_id: str
    row_set_id: str
    event_count: int
    unique_symbol_count: int
    time_range: dict[str, str | None]
    selected_action_counts: dict[str, int]
    notional_usd: Decimal
    fee_rate: Decimal
    funding_rate: Decimal
    slippage_bps: Decimal
    operator_cost_non_zero_count: int
    execution_window_peak_overlap: int
    same_timestamp_entry_exit_count: int
    source_coverage_counts: dict[str, int]
    known_gaps: list[str]


class VectorbtDifferentialResult(DecimalModel):
    vectorbt_version: str
    reference_result_id: str
    reference_trade_count: int
    vectorbt_order_count: int
    reference_gross_pnl_usd: Decimal
    vectorbt_gross_pnl_usd: Decimal
    reference_fixed_trading_cost_usd: Decimal
    vectorbt_fixed_trading_cost_usd: Decimal
    reference_final_delta_usd: Decimal
    vectorbt_final_delta_usd: Decimal
    absolute_difference_usd: Decimal
    validated_components: list[str]
    unvalidated_components: list[str]
    decision: Literal["MATCH", "MISMATCH", "VECTORBT_NOT_APPLICABLE"]
