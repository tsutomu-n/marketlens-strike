from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_serializer, field_validator, model_validator

from sis.crypto_perp.clock import serialize_utc_z
from sis.strategy_review.provenance import normalize_repo_relative_posix_path
from sis.edge_candidate_factory._contracts import (
    BACKTEST_KILL_GATE_REQUIRED_CONDITION_IDS,
    BACKTEST_KILL_GATE_SCHEMA_VERSION,
    EDGE_CANDIDATE_SEARCH_LEDGER_SCHEMA_VERSION,
    LLM_ADVERSARIAL_EVIDENCE_REVIEW_SCHEMA_VERSION,
    RISK_ACTUAL_CASH_HANDOFF_SCHEMA_VERSION,
    SMART_CANDIDATE_PRIOR_REPORT_SCHEMA_VERSION,
    TRIAL_MULTIPLICITY_ACCOUNT_SCHEMA_VERSION,
    VIRTUAL_EXECUTION_GATE_REQUIRED_CONDITION_IDS,
    VIRTUAL_EXECUTION_GATE_SCHEMA_VERSION,
    AdjustmentStatus,
    ArtifactModel,
    ArtifactRef,
    BacktestKillGateStatus,
    CandidateDecision,
    CandidateGateStatus,
    CandidateRowKind,
    CausePrior,
    ConditionStatus,
    EdgeCandidateBoundary,
    ExecutionEnvironment,
    LLMAdversarialReviewStatus,
    LLMFindingSeverity,
    LLMFindingType,
    Observable,
    ProducerInfo,
    RiskActualCashHandoffStatus,
    VirtualExecutionGateStatus,
    _validate_id,
    _validate_non_empty,
    _validate_sha256,
    _validate_text_list,
    _validate_unique,
)


class CandidateMechanismCard(ArtifactModel):
    mechanism_id: str
    mechanism_summary: str
    who_is_forced_or_constrained: str
    why_flow_may_be_unfavorable: str
    expected_time_horizon: str
    failure_modes: list[str] = Field(min_length=1)
    counter_hypothesis: str

    @field_validator(
        "mechanism_id",
        "mechanism_summary",
        "who_is_forced_or_constrained",
        "why_flow_may_be_unfavorable",
        "expected_time_horizon",
        "counter_hypothesis",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("failure_modes")
    @classmethod
    def validate_failure_modes(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="failure_modes")


class CandidateSourceRequirement(ArtifactModel):
    source_id: str
    source_type: str
    required: bool
    expected_schema: str
    available_at_policy: str
    status: CandidateGateStatus
    known_gaps: list[str] = Field(default_factory=list)

    @field_validator("source_id")
    @classmethod
    def validate_source_id(cls, value: str) -> str:
        return _validate_id(value, label="source_id")

    @field_validator("source_type", "expected_schema", "available_at_policy")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("known_gaps")
    @classmethod
    def validate_known_gaps(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="known_gaps")


class CandidateExecutionPrecheck(ArtifactModel):
    venue_id: str
    product_type: str
    symbol: str
    min_notional_ok: bool
    tick_size_ok: bool
    lot_size_ok: bool
    max_spread_bps: float = Field(ge=0)
    observed_spread_bps: float | None = Field(default=None, ge=0)
    min_depth_usd: float = Field(ge=0)
    observed_depth_usd: float | None = Field(default=None, ge=0)
    fee_rate_available: bool
    funding_available: bool
    estimated_operator_time_minutes: int = Field(ge=0)
    estimated_capital_tied_up_minutes: int = Field(ge=0)
    unexecutable_reasons: list[str] = Field(default_factory=list)
    execution_precheck_status: CandidateGateStatus

    @field_validator("venue_id", "product_type", "symbol")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("unexecutable_reasons")
    @classmethod
    def validate_unexecutable_reasons(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="unexecutable_reasons")

    @model_validator(mode="after")
    def validate_precheck_shape(self) -> CandidateExecutionPrecheck:
        if self.execution_precheck_status is CandidateGateStatus.PASS and self.unexecutable_reasons:
            raise ValueError("PASS execution_precheck_status must not include unexecutable_reasons")
        return self


class CandidatePriorScore(ArtifactModel):
    mechanism_score: float = Field(ge=0, le=1)
    source_availability_score: float = Field(ge=0, le=1)
    execution_feasibility_score: float = Field(ge=0, le=1)
    testability_score: float = Field(ge=0, le=1)
    diversity_score: float = Field(ge=0, le=1)
    information_gain_score: float = Field(ge=0, le=1)
    operator_cost_penalty: float = Field(ge=0, le=1)
    unexecutable_penalty: float = Field(ge=0, le=1)
    overfit_surface_penalty: float = Field(ge=0, le=1)
    total_score: float = Field(ge=0, le=1)
    score_basis: Literal["prior_not_profit_proof"] = "prior_not_profit_proof"


class SmartCandidateCard(ArtifactModel):
    candidate_id: str
    candidate_status: Literal["UNVERIFIED_CANDIDATE"] = "UNVERIFIED_CANDIDATE"
    candidate_decision: CandidateDecision
    cause_priors: list[CausePrior] = Field(min_length=1)
    family: str
    mechanism_card: CandidateMechanismCard
    observables: list[Observable] = Field(min_length=1)
    required_sources: list[CandidateSourceRequirement] = Field(min_length=1)
    source_requirement_status: CandidateGateStatus
    execution_precheck: CandidateExecutionPrecheck
    candidate_prior_score: CandidatePriorScore
    parameter_set: dict[str, Any]
    action_set: list[str] = Field(min_length=1)
    entry_logic: str
    exit_logic: str
    kill_conditions: list[str] = Field(min_length=1)
    expected_information_gain: str
    test_cost_estimate: str
    operator_burden_estimate: str
    candidate_cluster_id: str
    similar_candidate_count: int = Field(ge=0)
    negative_control_refs: list[str] = Field(default_factory=list)
    proof_status: Literal["not_alpha_or_profit_proof"] = "not_alpha_or_profit_proof"
    rejection_reason: str | None = None
    shortlist_reason: str | None = None
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("candidate_id", "candidate_cluster_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="candidate_id")

    @field_validator(
        "family",
        "entry_logic",
        "exit_logic",
        "expected_information_gain",
        "test_cost_estimate",
        "operator_burden_estimate",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("action_set", "kill_conditions", "negative_control_refs")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values)

    @field_validator("rejection_reason", "shortlist_reason")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return _validate_non_empty(value) if value is not None else None

    @model_validator(mode="after")
    def validate_decision_shape(self) -> SmartCandidateCard:
        if self.candidate_decision is CandidateDecision.REJECTED:
            if self.rejection_reason is None:
                raise ValueError("REJECTED requires rejection_reason")
            if self.shortlist_reason is not None:
                raise ValueError("REJECTED must not include shortlist_reason")
        if (
            self.candidate_decision is CandidateDecision.GENERATED
            and self.rejection_reason is not None
        ):
            raise ValueError("GENERATED must not include rejection_reason")
        return self


class GeneratorConfig(ArtifactModel):
    profile: str
    symbols: list[str] = Field(min_length=1)
    product_type: str
    timeframe: str
    families: list[str] = Field(min_length=1)
    candidate_cap: int = Field(ge=1)
    parameter_grid_hash: str
    source_root: str
    sealed_test_policy: str
    network_attempted: Literal[False] = False
    credentials_used: Literal[False] = False
    production_exchange_write_used: Literal[False] = False

    @field_validator("profile", "product_type", "timeframe", "sealed_test_policy")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("symbols", "families")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values)

    @field_validator("parameter_grid_hash")
    @classmethod
    def validate_parameter_grid_hash(cls, value: str) -> str:
        return _validate_sha256(value, label="parameter_grid_hash")

    @field_validator("source_root")
    @classmethod
    def validate_source_root(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)


class SmartCandidatePriorReport(ArtifactModel):
    schema_version: Literal["smart_candidate_prior_report.v1"] = (
        SMART_CANDIDATE_PRIOR_REPORT_SCHEMA_VERSION
    )
    report_id: str
    generated_at: datetime
    producer: ProducerInfo
    source_refs: list[ArtifactRef] = Field(min_length=1)
    generator_config: GeneratorConfig
    candidate_cards: list[SmartCandidateCard] = Field(min_length=1)
    candidate_count_total: int = Field(ge=0)
    candidate_count_accepted: int = Field(ge=0)
    candidate_count_rejected: int = Field(ge=0)
    rejection_summary: dict[str, int] = Field(default_factory=dict)
    score_summary: dict[str, float] = Field(default_factory=dict)
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)
    known_gaps: list[str] = Field(default_factory=list)

    @field_validator("report_id")
    @classmethod
    def validate_report_id(cls, value: str) -> str:
        return _validate_id(value, label="report_id")

    @field_validator("known_gaps")
    @classmethod
    def validate_known_gaps(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="known_gaps")

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_counts(self) -> SmartCandidatePriorReport:
        candidate_ids = [card.candidate_id for card in self.candidate_cards]
        _validate_unique(candidate_ids, label="candidate_cards")
        generated_count = sum(
            1
            for card in self.candidate_cards
            if card.candidate_decision is CandidateDecision.GENERATED
        )
        rejected_count = sum(
            1
            for card in self.candidate_cards
            if card.candidate_decision is CandidateDecision.REJECTED
        )
        if self.candidate_count_total != len(self.candidate_cards):
            raise ValueError("candidate_count_total must match candidate_cards length")
        if self.candidate_count_accepted != generated_count:
            raise ValueError("candidate_count_accepted must match GENERATED cards")
        if self.candidate_count_rejected != rejected_count:
            raise ValueError("candidate_count_rejected must match REJECTED cards")
        return self


class EdgeCandidateSearchLedgerRow(ArtifactModel):
    schema_version: Literal["edge_candidate_search_ledger.v1"] = (
        EDGE_CANDIDATE_SEARCH_LEDGER_SCHEMA_VERSION
    )
    run_id: str
    candidate_id: str
    row_kind: CandidateRowKind
    family: str
    cause_priors: list[CausePrior] = Field(min_length=1)
    parameter_hash: str
    parameter_set: dict[str, Any]
    candidate_cluster_id: str
    similar_candidate_count: int = Field(ge=0)
    candidate_prior_score: CandidatePriorScore
    candidate_decision: CandidateDecision
    rejection_reason: str | None = None
    source_requirement_status: CandidateGateStatus
    execution_precheck_status: CandidateGateStatus
    validation_peek_count_at_generation: int = Field(ge=0)
    sealed_test_used_for_selection: Literal[False] = False
    proof_status: Literal["not_alpha_or_profit_proof"] = "not_alpha_or_profit_proof"
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("run_id", "candidate_id", "candidate_cluster_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("family")
    @classmethod
    def validate_family(cls, value: str) -> str:
        return _validate_non_empty(value, label="family")

    @field_validator("parameter_hash")
    @classmethod
    def validate_parameter_hash(cls, value: str) -> str:
        return _validate_sha256(value, label="parameter_hash")

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, value: str | None) -> str | None:
        return _validate_non_empty(value, label="rejection_reason") if value is not None else None

    @model_validator(mode="after")
    def validate_ledger_decision(self) -> EdgeCandidateSearchLedgerRow:
        if self.candidate_decision is CandidateDecision.REJECTED and self.rejection_reason is None:
            raise ValueError("REJECTED ledger rows require rejection_reason")
        if (
            self.candidate_decision is CandidateDecision.GENERATED
            and self.rejection_reason is not None
        ):
            raise ValueError("GENERATED ledger rows must not include rejection_reason")
        return self


class EdgeCandidateSearchLedger(ArtifactModel):
    schema_version: Literal["edge_candidate_search_ledger.v1"] = (
        EDGE_CANDIDATE_SEARCH_LEDGER_SCHEMA_VERSION
    )
    run_id: str
    rows: list[EdgeCandidateSearchLedgerRow] = Field(min_length=1)
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        return _validate_id(value, label="run_id")

    @model_validator(mode="after")
    def validate_rows(self) -> EdgeCandidateSearchLedger:
        for row in self.rows:
            if row.run_id != self.run_id:
                raise ValueError("ledger row run_id must match ledger run_id")
        return self


class AdjustmentMethods(ArtifactModel):
    benjamini_hochberg_fdr: AdjustmentStatus
    benjamini_yekutieli_fdr: AdjustmentStatus
    pbo: AdjustmentStatus
    white_reality_check: AdjustmentStatus
    deflated_sharpe_ratio: AdjustmentStatus


class TrialMultiplicityAccount(ArtifactModel):
    schema_version: Literal["trial_multiplicity_account.v1"] = (
        TRIAL_MULTIPLICITY_ACCOUNT_SCHEMA_VERSION
    )
    account_id: str
    created_at: datetime
    producer: ProducerInfo
    source_refs: list[ArtifactRef] = Field(min_length=1)
    candidate_run_id: str
    candidate_count_total: int = Field(ge=0)
    candidate_count_shortlisted: int = Field(ge=0)
    candidate_count_rejected: int = Field(ge=0)
    family_count: int = Field(ge=0)
    family_trial_counts: dict[str, int] = Field(default_factory=dict)
    parameter_grid_hashes: list[str] = Field(min_length=1)
    candidate_cluster_count: int = Field(ge=0)
    effective_trial_count_status: AdjustmentStatus
    effective_trial_count: int | None = Field(default=None, ge=0)
    validation_peek_count: int = Field(ge=0)
    rerank_count: int = Field(ge=0)
    sealed_test_used_for_selection: Literal[False] = False
    success_only_reporting: Literal[False] = False
    adjustment_methods: AdjustmentMethods
    known_gaps: list[str] = Field(default_factory=list)
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("account_id", "candidate_run_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("parameter_grid_hashes")
    @classmethod
    def validate_parameter_grid_hashes(cls, values: list[str]) -> list[str]:
        cleaned = [_validate_sha256(value, label="parameter_grid_hash") for value in values]
        _validate_unique(cleaned, label="parameter_grid_hashes")
        return cleaned

    @field_validator("family_trial_counts")
    @classmethod
    def validate_family_trial_counts(cls, value: dict[str, int]) -> dict[str, int]:
        cleaned: dict[str, int] = {}
        for raw_key, raw_count in value.items():
            key = _validate_non_empty(raw_key, label="family_trial_counts key")
            if raw_count < 0:
                raise ValueError("family_trial_counts values must be >= 0")
            cleaned[key] = raw_count
        return cleaned

    @field_validator("known_gaps")
    @classmethod
    def validate_known_gaps(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="known_gaps")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_counts(self) -> TrialMultiplicityAccount:
        if self.candidate_count_shortlisted + self.candidate_count_rejected != (
            self.candidate_count_total
        ):
            raise ValueError("candidate shortlisted and rejected counts must add up to total")
        if self.family_count != len(self.family_trial_counts):
            raise ValueError("family_count must match family_trial_counts length")
        if self.effective_trial_count_status is AdjustmentStatus.AVAILABLE:
            if self.effective_trial_count is None:
                raise ValueError(
                    "AVAILABLE effective_trial_count_status requires effective_trial_count"
                )
        elif self.effective_trial_count is not None:
            raise ValueError("NOT_ESTIMABLE effective_trial_count_status requires null count")
        return self


class GateCondition(ArtifactModel):
    condition_id: str
    condition_status: ConditionStatus
    observed: str | int | float | bool | None
    required: str | int | float | bool | None
    source_ref: str

    @field_validator("condition_id")
    @classmethod
    def validate_condition_id(cls, value: str) -> str:
        return _validate_id(value, label="condition_id")

    @field_validator("source_ref")
    @classmethod
    def validate_source_ref(cls, value: str) -> str:
        return _validate_non_empty(value, label="source_ref")


class BacktestMetrics(ArtifactModel):
    event_count: int | None = Field(default=None, ge=0)
    closed_trade_count: int | None = Field(default=None, ge=0)
    after_cost_edge_over_no_trade_usd: float | None = None
    stress_edge_over_no_trade_usd: float | None = None
    largest_loss_usd: float | None = None
    profit_concentration: float | None = Field(default=None, ge=0)
    source_gap_count: int = Field(ge=0)
    unexecutable_reason_count: int = Field(ge=0)
    validation_peek_count: int = Field(ge=0)
    candidate_cluster_count: int = Field(ge=0)
    effective_trial_count: int | None = Field(default=None, ge=0)


class BacktestKillGate(ArtifactModel):
    schema_version: Literal["backtest_kill_gate.v1"] = BACKTEST_KILL_GATE_SCHEMA_VERSION
    gate_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_id: str
    candidate_source_refs: list[ArtifactRef] = Field(min_length=1)
    bridge_refs: list[ArtifactRef] = Field(default_factory=list)
    multiplicity_account_ref: ArtifactRef
    backtest_refs: list[ArtifactRef] = Field(default_factory=list)
    gate_status: BacktestKillGateStatus
    recommended_action: str
    metric_extraction_status: ConditionStatus
    metric_source_refs: list[ArtifactRef] = Field(default_factory=list)
    metric_not_estimable_reasons: list[str] = Field(default_factory=list)
    conditions: list[GateCondition] = Field(min_length=1)
    metrics: BacktestMetrics
    known_gaps: list[str] = Field(default_factory=list)
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("gate_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("recommended_action")
    @classmethod
    def validate_recommended_action(cls, value: str) -> str:
        return _validate_non_empty(value, label="recommended_action")

    @field_validator("metric_not_estimable_reasons", "known_gaps")
    @classmethod
    def validate_text_lists(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_condition_set(self) -> BacktestKillGate:
        condition_ids = [condition.condition_id for condition in self.conditions]
        _validate_unique(condition_ids, label="conditions")
        missing = BACKTEST_KILL_GATE_REQUIRED_CONDITION_IDS - set(condition_ids)
        if missing:
            raise ValueError(f"missing required backtest kill gate conditions: {sorted(missing)}")
        return self


class VirtualExecutionGate(ArtifactModel):
    schema_version: Literal["virtual_execution_gate.v1"] = VIRTUAL_EXECUTION_GATE_SCHEMA_VERSION
    gate_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_id: str
    execution_environment: ExecutionEnvironment
    venue_id: str
    source_refs: list[ArtifactRef] = Field(default_factory=list)
    order_lifecycle_summary: dict[str, Any]
    fill_ledger_summary: dict[str, Any]
    reconciliation_summary: dict[str, Any]
    gate_status: VirtualExecutionGateStatus
    recommended_action: str
    actual_cash: Literal[False] = False
    cash_metric_basis: Literal["virtual_exchange"] = "virtual_exchange"
    exchange_write_used: bool = False
    production_exchange_write_used: Literal[False] = False
    permits_live_order: Literal[False] = False
    conditions: list[GateCondition] = Field(min_length=1)
    known_gaps: list[str] = Field(default_factory=list)
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("gate_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("venue_id", "recommended_action")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)

    @field_validator("known_gaps")
    @classmethod
    def validate_known_gaps(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="known_gaps")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_virtual_gate(self) -> VirtualExecutionGate:
        condition_ids = [condition.condition_id for condition in self.conditions]
        _validate_unique(condition_ids, label="conditions")
        missing = VIRTUAL_EXECUTION_GATE_REQUIRED_CONDITION_IDS - set(condition_ids)
        if missing:
            raise ValueError(f"missing required virtual execution conditions: {sorted(missing)}")
        if self.exchange_write_used and self.execution_environment is ExecutionEnvironment.FIXTURE:
            raise ValueError(
                "exchange_write_used is only allowed for demo or testnet virtual gates"
            )
        return self


class RiskActualCashHandoff(ArtifactModel):
    schema_version: Literal["edge_candidate_risk_actual_cash_handoff.v1"] = (
        RISK_ACTUAL_CASH_HANDOFF_SCHEMA_VERSION
    )
    handoff_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_id: str
    candidate_report_ref: ArtifactRef
    search_ledger_ref: ArtifactRef
    multiplicity_account_ref: ArtifactRef
    backtest_kill_gate_ref: ArtifactRef
    virtual_execution_gate_ref: ArtifactRef
    risk_taker_review_input_status: RiskActualCashHandoffStatus
    actual_cash_report_gate_input_status: RiskActualCashHandoffStatus
    actual_cash_rows_required: Literal[True] = True
    actual_cash_rows_ref: ArtifactRef | None = None
    virtual_or_backtest_used_as_actual_cash: Literal[False] = False
    known_gaps: list[str] = Field(default_factory=list)
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("handoff_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        return _validate_id(value, label="id")

    @field_validator("known_gaps")
    @classmethod
    def validate_known_gaps(cls, values: list[str]) -> list[str]:
        return _validate_text_list(values, label="known_gaps")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_handoff_status(self) -> RiskActualCashHandoff:
        statuses = {
            self.risk_taker_review_input_status,
            self.actual_cash_report_gate_input_status,
        }
        if RiskActualCashHandoffStatus.READY_WITH_ACTUAL_CASH_ROWS in statuses:
            if self.actual_cash_rows_ref is None:
                raise ValueError("READY_WITH_ACTUAL_CASH_ROWS requires actual_cash_rows_ref")
        return self


class LLMAdversarialFinding(ArtifactModel):
    finding_id: str
    finding_type: LLMFindingType
    severity: LLMFindingSeverity
    source_ref: str
    claim_text: str
    problem: str
    required_fix: str
    machine_checkable: bool
    hard_blocker: bool

    @field_validator("finding_id")
    @classmethod
    def validate_finding_id(cls, value: str) -> str:
        return _validate_id(value, label="finding_id")

    @field_validator("source_ref", "claim_text", "problem", "required_fix")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return _validate_non_empty(value)


class LLMAdversarialEvidenceReview(ArtifactModel):
    schema_version: Literal["llm_adversarial_evidence_review.v1"] = (
        LLM_ADVERSARIAL_EVIDENCE_REVIEW_SCHEMA_VERSION
    )
    review_id: str
    created_at: datetime
    producer: ProducerInfo
    source_refs: list[ArtifactRef] = Field(min_length=1)
    packet_hash: str
    review_status: LLMAdversarialReviewStatus
    findings: list[LLMAdversarialFinding] = Field(default_factory=list)
    hard_blocker_count: int = Field(ge=0)
    soft_warning_count: int = Field(ge=0)
    llm_approval_ignored: Literal[True] = True
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    actual_cash_decision_allowed: Literal[False] = False
    gate_override_allowed: Literal[False] = False
    boundary: EdgeCandidateBoundary = Field(default_factory=EdgeCandidateBoundary)

    @field_validator("review_id")
    @classmethod
    def validate_review_id(cls, value: str) -> str:
        return _validate_id(value, label="review_id")

    @field_validator("packet_hash")
    @classmethod
    def validate_packet_hash(cls, value: str) -> str:
        return _validate_sha256(value, label="packet_hash")

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)

    @model_validator(mode="after")
    def validate_finding_counts(self) -> LLMAdversarialEvidenceReview:
        hard_count = sum(1 for finding in self.findings if finding.hard_blocker)
        soft_count = len(self.findings) - hard_count
        if self.hard_blocker_count != hard_count:
            raise ValueError("hard_blocker_count must match findings")
        if self.soft_warning_count != soft_count:
            raise ValueError("soft_warning_count must match findings")
        return self


SCHEMA_MODEL_BY_FILENAME = {
    "smart_candidate_prior_report.v1.schema.json": SmartCandidatePriorReport,
    "edge_candidate_search_ledger.v1.schema.json": EdgeCandidateSearchLedgerRow,
    "trial_multiplicity_account.v1.schema.json": TrialMultiplicityAccount,
    "backtest_kill_gate.v1.schema.json": BacktestKillGate,
    "virtual_execution_gate.v1.schema.json": VirtualExecutionGate,
    "edge_candidate_risk_actual_cash_handoff.v1.schema.json": RiskActualCashHandoff,
    "llm_adversarial_evidence_review.v1.schema.json": LLMAdversarialEvidenceReview,
}
