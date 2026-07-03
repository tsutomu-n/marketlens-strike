from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z


PROFIT_CORE_REALITY_CHECK_SCHEMA_VERSION = "profit_core_reality_check.v1"

OverallStatus = Literal["COMPLETE", "BLOCKED", "PARTIAL"]
NextAction = Literal["FIX_BLOCKER", "COLLECT_INPUTS", "RUN_EXISTING_PIPELINE", "REVIEW_ONLY", "NO_ACTION"]
LineageStatus = Literal["COMPLETE", "PARTIAL", "BROKEN", "NOT_APPLICABLE"]


class ProfitCoreRealityCheckProducer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: Literal["sis"] = "sis"
    command: str

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("command must not be empty")
        return stripped


class ProfitCoreRealityCheckBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    wallet_allowed: Literal[False] = False
    signing_allowed: Literal[False] = False
    exchange_write_allowed: Literal[False] = False
    production_exchange_write_allowed: Literal[False] = False
    permits_live_order: Literal[False] = False
    auto_promote: Literal[False] = False


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str
    schema_version: str | None = None


class RealityCheckInputPaths(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_set_path: str
    search_ledger_path: str
    export_manifest_path: str | None = None
    authoring_bridge_path: str | None = None
    profit_readiness_inventory_path: str | None = None
    source_availability_path: str | None = None
    risk_review_path: str | None = None
    actual_cash_rows_summary_path: str | None = None
    actual_cash_report_gate_path: str | None = None


class RealityCheckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_status: OverallStatus
    next_action: NextAction
    candidate_count_total: int = Field(ge=0)
    candidate_count_shortlisted: int = Field(ge=0)
    candidate_count_rejected: int = Field(ge=0)
    bridge_blocked_count: int = Field(ge=0)
    bridge_bridged_count: int = Field(ge=0)
    actual_cash_available_count: int = Field(ge=0)
    known_gap_count: int = Field(ge=0)


class CandidateGenerationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_set_present: bool
    search_ledger_present: bool
    export_manifest_present: bool
    candidate_set_id: str | None = None
    candidate_count_total: int = Field(default=0, ge=0)
    candidate_count_shortlisted: int = Field(default=0, ge=0)
    candidate_count_rejected: int = Field(default=0, ge=0)
    trial_count_total: int = Field(default=0, ge=0)
    candidate_cap: int = Field(default=0, ge=0)
    cap_rejection_count: int = Field(default=0, ge=0)
    duplicate_rejection_count: int = Field(default=0, ge=0)
    validation_peek_count: int = Field(default=0, ge=0)
    rerank_count: int = Field(default=0, ge=0)
    sealed_test_used_for_selection: bool = False
    success_only_reporting_detected: bool = False
    shortlisted_family_counts: dict[str, int] = Field(default_factory=dict)
    rejected_family_counts: dict[str, int] = Field(default_factory=dict)
    selection_adjusted_metrics_status_counts: dict[str, int] = Field(default_factory=dict)


class BridgeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bridge_manifest_present: bool
    bridge_candidate_count: int = Field(default=0, ge=0)
    bridge_bridged_count: int = Field(default=0, ge=0)
    bridge_blocked_count: int = Field(default=0, ge=0)
    bridge_status_counts: dict[str, int] = Field(default_factory=dict)
    blocked_reason_counts: dict[str, int] = Field(default_factory=dict)
    blocked_by_family: dict[str, int] = Field(default_factory=dict)
    blocked_by_side_bias: dict[str, int] = Field(default_factory=dict)
    blocked_by_symbol: dict[str, int] = Field(default_factory=dict)
    technical_bridged_candidate_ids: list[str] = Field(default_factory=list)
    blocked_candidate_ids: list[str] = Field(default_factory=list)
    bridge_success_semantics: Literal["technical_only"] = "technical_only"
    economic_gate_status: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"
    actual_cash_result_available: Literal[False] = False


class ProfitReadinessSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    inventory_present: bool
    inventory_status: str | None = None
    real_event_count: int = Field(default=0, ge=0)
    matured_outcome_count: int = Field(default=0, ge=0)
    cash_ledger_count: int = Field(default=0, ge=0)
    live_measurement_count: int = Field(default=0, ge=0)
    source_availability_present: bool
    can_compute_cost_adjusted_estimate: bool = False
    can_compute_actual_cash: bool = False
    source_status_counts: dict[str, int] = Field(default_factory=dict)


class RiskReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_review_present: bool
    risk_review_status: str | None = None
    recommended_action: str | None = None
    leader_action: str | None = None
    after_cost_edge_over_no_trade_usd: str | None = None
    stress_edge_over_no_trade_usd: str | None = None
    dollars_per_hour: str | None = None
    largest_loss_usd: str | None = None
    profit_concentration: str | None = None
    actual_cash_available: bool = False
    failed_condition_count: int = Field(default=0, ge=0)
    condition_statuses: dict[str, bool] = Field(default_factory=dict)


class ActualCashSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    actual_cash_rows_summary_present: bool
    actual_cash_row_count: int = Field(default=0, ge=0)
    actual_cash_event_count: int = Field(default=0, ge=0)
    action_set: list[str] = Field(default_factory=list)
    actual_cash_report_gate_present: bool
    actual_cash_gate_status: str | None = None
    report_actual_cash: bool = False
    fields_missing_for_actual_cash_result_usd: list[str] = Field(default_factory=list)


class LineageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lineage_status: LineageStatus
    candidate_id_count: int = Field(default=0, ge=0)
    candidate_ids_missing_from_ledger: list[str] = Field(default_factory=list)
    shortlisted_ids_missing_from_export_manifest: list[str] = Field(default_factory=list)
    exported_ids_missing_from_bridge: list[str] = Field(default_factory=list)
    risk_review_candidate_link_status: str = "NOT_APPLICABLE"
    actual_cash_candidate_link_status: str = "NOT_APPLICABLE"
    lineage_gaps: list[str] = Field(default_factory=list)


class BlockerSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    blocker_counts: dict[str, int] = Field(default_factory=dict)
    blockers_by_stage: dict[str, list[str]] = Field(default_factory=dict)
    blockers_by_family: dict[str, int] = Field(default_factory=dict)
    top_blockers: list[str] = Field(default_factory=list)
    next_single_blocker_to_fix: str


class ProfitCoreRealityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["profit_core_reality_check.v1"] = (
        PROFIT_CORE_REALITY_CHECK_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: ProfitCoreRealityCheckProducer
    source_refs: list[SourceRef]
    input_paths: RealityCheckInputPaths
    summary: RealityCheckSummary
    candidate_generation: CandidateGenerationSummary
    bridge_summary: BridgeSummary
    profit_readiness_summary: ProfitReadinessSummary
    risk_review_summary: RiskReviewSummary
    actual_cash_summary: ActualCashSummary
    lineage_summary: LineageSummary
    blocker_summary: BlockerSummary
    next_single_blocker_to_fix: str
    known_gaps: list[str]
    boundary: ProfitCoreRealityCheckBoundary = Field(default_factory=ProfitCoreRealityCheckBoundary)

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)
