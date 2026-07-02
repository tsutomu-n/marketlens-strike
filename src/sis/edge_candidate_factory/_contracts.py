from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from sis.strategy_review.manifest import REVIEW_ID_PATTERN, SHA256_PATTERN
from sis.strategy_review.provenance import normalize_repo_relative_posix_path


SMART_CANDIDATE_PRIOR_REPORT_SCHEMA_VERSION = "smart_candidate_prior_report.v1"
EDGE_CANDIDATE_SEARCH_LEDGER_SCHEMA_VERSION = "edge_candidate_search_ledger.v1"
TRIAL_MULTIPLICITY_ACCOUNT_SCHEMA_VERSION = "trial_multiplicity_account.v1"
BACKTEST_KILL_GATE_SCHEMA_VERSION = "backtest_kill_gate.v1"
VIRTUAL_EXECUTION_GATE_SCHEMA_VERSION = "virtual_execution_gate.v1"
RISK_ACTUAL_CASH_HANDOFF_SCHEMA_VERSION = "edge_candidate_risk_actual_cash_handoff.v1"
LLM_ADVERSARIAL_EVIDENCE_REVIEW_SCHEMA_VERSION = "llm_adversarial_evidence_review.v1"

BACKTEST_KILL_GATE_REQUIRED_CONDITION_IDS = frozenset(
    {
        "source_available",
        "bridge_technical_ready",
        "candidate_scoped_backtest_exists",
        "no_trade_comparison_available",
        "event_count_meets_family_threshold",
        "closed_trade_count_meets_threshold",
        "after_cost_edge_positive",
        "stress_edge_positive",
        "largest_loss_within_limit",
        "profit_concentration_within_limit",
        "multiplicity_account_available",
        "unexecutable_reason_count_zero",
        "sealed_test_not_used_for_selection",
        "execution_precheck_passed",
    }
)

VIRTUAL_EXECUTION_GATE_REQUIRED_CONDITION_IDS = frozenset(
    {
        "order_preview_ready",
        "order_accepted_or_rejected_with_reason",
        "client_oid_unique",
        "partial_fill_handled",
        "cancel_handled",
        "reduce_only_close_checked",
        "flat_reconciliation_passed",
        "fee_like_fields_captured",
        "funding_like_fields_captured",
        "duplicate_order_prevented",
        "production_exchange_write_not_used",
    }
)


class CausePrior(StrEnum):
    FORCED_FLOW = "FORCED_FLOW"
    INVENTORY_RISK_TRANSFER = "INVENTORY_RISK_TRANSFER"
    SLOW_INFORMATION = "SLOW_INFORMATION"
    CONSTRAINED_ARBITRAGE = "CONSTRAINED_ARBITRAGE"
    CROWDED_POSITIONING = "CROWDED_POSITIONING"
    BEHAVIORAL_ATTENTION = "BEHAVIORAL_ATTENTION"
    ADVERSE_SELECTION = "ADVERSE_SELECTION"
    EXECUTION_FRICTION = "EXECUTION_FRICTION"
    DATA_OBSERVABILITY = "DATA_OBSERVABILITY"


class Observable(StrEnum):
    FUNDING_RATE = "funding_rate"
    FUNDING_WINDOW = "funding_window"
    LIQUIDATION_NOTIONAL = "liquidation_notional"
    LIQUIDATION_SIDE = "liquidation_side"
    MARK_PRICE = "mark_price"
    INDEX_PRICE = "index_price"
    MARK_INDEX_BASIS_BPS = "mark_index_basis_bps"
    SPOT_PERP_BASIS_BPS = "spot_perp_basis_bps"
    OPEN_INTEREST = "open_interest"
    OPEN_INTEREST_CHANGE = "open_interest_change"
    SPREAD_BPS = "spread_bps"
    BID_PRICE = "bid_price"
    ASK_PRICE = "ask_price"
    BOOK_DEPTH = "book_depth"
    ORDER_FLOW_IMBALANCE = "order_flow_imbalance"
    AGGRESSIVE_TRADE_IMBALANCE = "aggressive_trade_imbalance"
    VOLUME = "volume"
    TURNOVER = "turnover"
    REALIZED_VOLATILITY = "realized_volatility"
    VOLATILITY_COMPRESSION = "volatility_compression"
    SESSION_TIME = "session_time"
    WEEKDAY = "weekday"
    QUOTE_AGE = "quote_age"
    FEE_RATE = "fee_rate"
    MIN_NOTIONAL = "min_notional"
    TICK_SIZE = "tick_size"
    LOT_SIZE = "lot_size"
    SOURCE_QUALITY = "source_quality"
    AVAILABLE_AT = "available_at"


class CandidateDecision(StrEnum):
    GENERATED = "GENERATED"
    REJECTED = "REJECTED"


class CandidateRowKind(StrEnum):
    CANDIDATE = "candidate"
    REJECTION = "rejection"
    DUPLICATE = "duplicate"
    CAP_REJECTION = "cap_rejection"
    SOURCE_BLOCKER = "source_blocker"


class CandidateGateStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NOT_ESTIMABLE = "NOT_ESTIMABLE"


class ConditionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_ESTIMABLE = "NOT_ESTIMABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AdjustmentStatus(StrEnum):
    NOT_ESTIMABLE = "NOT_ESTIMABLE"
    AVAILABLE = "AVAILABLE"


class BacktestKillGateStatus(StrEnum):
    KILL = "KILL"
    INCONCLUSIVE_DATA = "INCONCLUSIVE_DATA"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    SHORTLIST_FOR_VIRTUAL = "SHORTLIST_FOR_VIRTUAL"


class VirtualExecutionGateStatus(StrEnum):
    VIRTUAL_NOT_RUN = "VIRTUAL_NOT_RUN"
    VIRTUAL_BLOCKED_SOURCE = "VIRTUAL_BLOCKED_SOURCE"
    VIRTUAL_BLOCKED_EXECUTION_PRECHECK = "VIRTUAL_BLOCKED_EXECUTION_PRECHECK"
    VIRTUAL_FAILED_ORDER_LIFECYCLE = "VIRTUAL_FAILED_ORDER_LIFECYCLE"
    VIRTUAL_FAILED_RECONCILIATION = "VIRTUAL_FAILED_RECONCILIATION"
    VIRTUAL_PASSED_EXECUTION_LIFECYCLE = "VIRTUAL_PASSED_EXECUTION_LIFECYCLE"


class ExecutionEnvironment(StrEnum):
    FIXTURE = "fixture"
    DEMO = "demo"
    TESTNET = "testnet"


class RiskActualCashHandoffStatus(StrEnum):
    BLOCKED_NEEDS_ACTUAL_CASH_ROWS = "BLOCKED_NEEDS_ACTUAL_CASH_ROWS"
    READY_WITH_ACTUAL_CASH_ROWS = "READY_WITH_ACTUAL_CASH_ROWS"


class LLMAdversarialReviewStatus(StrEnum):
    NO_BLOCKING_FINDING = "NO_BLOCKING_FINDING"
    ADVERSARIAL_FINDING = "ADVERSARIAL_FINDING"
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    CONTRADICTION = "CONTRADICTION"
    OVERCLAIM_FLAG = "OVERCLAIM_FLAG"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class LLMFindingType(StrEnum):
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    CONTRADICTION = "CONTRADICTION"
    OVERCLAIM_FLAG = "OVERCLAIM_FLAG"
    LEAKAGE_RISK = "LEAKAGE_RISK"
    UNSAFE_BOUNDARY = "UNSAFE_BOUNDARY"


class LLMFindingSeverity(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class ArtifactModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_id(value: str, *, label: str) -> str:
    if not REVIEW_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must match ^[A-Za-z0-9][A-Za-z0-9._-]{{0,127}}$")
    return value


def _validate_sha256(value: str, *, label: str = "sha256") -> str:
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must match sha256:<64 lowercase hex>")
    return value


def _validate_non_empty(value: str, *, label: str = "value") -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{label} must not be empty")
    return stripped


def _validate_text_list(values: list[str], *, label: str = "list") -> list[str]:
    cleaned = [_validate_non_empty(item, label=label) for item in values]
    return cleaned


def _validate_unique(values: list[str], *, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicate values")


class EdgeCandidateBoundary(ArtifactModel):
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    permits_live_order: Literal[False] = False
    live_conversion_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    production_exchange_write_allowed: Literal[False] = False
    production_exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False
    auto_promote: Literal[False] = False


class ProducerInfo(ArtifactModel):
    tool: Literal["sis"] = "sis"
    command: str

    @field_validator("command")
    @classmethod
    def validate_command(cls, value: str) -> str:
        return _validate_non_empty(value, label="command")


class ArtifactRef(ArtifactModel):
    ref_id: str
    schema_version: str
    path: str
    sha256: str

    @field_validator("ref_id")
    @classmethod
    def validate_ref_id(cls, value: str) -> str:
        return _validate_id(value, label="ref_id")

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        return _validate_non_empty(value, label="schema_version")

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return normalize_repo_relative_posix_path(value)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        return _validate_sha256(value)
