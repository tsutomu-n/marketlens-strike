"""Smart edge candidate factory contract models."""

from sis.edge_candidate_factory.models import (
    BacktestKillGate,
    CandidateExecutionPrecheck,
    CandidateMechanismCard,
    CandidatePriorScore,
    CandidateSourceRequirement,
    EdgeCandidateBoundary,
    EdgeCandidateSearchLedger,
    EdgeCandidateSearchLedgerRow,
    LLMAdversarialEvidenceReview,
    RiskActualCashHandoff,
    SmartCandidateCard,
    SmartCandidatePriorReport,
    TrialMultiplicityAccount,
    VirtualExecutionGate,
)
from sis.edge_candidate_factory.generator import (
    EdgeCandidateFactoryConfig,
    EdgeCandidateFactoryRun,
    EdgeCandidateFactoryWriteResult,
    build_edge_candidate_factory_run,
    write_edge_candidate_factory_run,
)
from sis.edge_candidate_factory.multiplicity import (
    MultiplicityAccountError,
    build_trial_multiplicity_account,
)
from sis.edge_candidate_factory.backtest_inputs import (
    BacktestMetricInputs,
    extract_backtest_metrics,
)
from sis.edge_candidate_factory.backtest_kill_gate import (
    build_backtest_kill_gate,
    family_event_threshold,
)
from sis.edge_candidate_factory.virtual_execution_gate import build_virtual_execution_gate
from sis.edge_candidate_factory.smart_priors import (
    DEFAULT_SMART_PRIOR_CAUSE_IDS,
    DEFAULT_SMART_PRIOR_FAMILY_IDS,
    SmartPriorDefinition,
    SmartPriorFamily,
    build_default_candidate_card,
    default_smart_prior_families,
    default_smart_prior_family_ids,
    smart_prior_family_by_id,
)

__all__ = [
    "BacktestKillGate",
    "BacktestMetricInputs",
    "CandidateExecutionPrecheck",
    "CandidateMechanismCard",
    "CandidatePriorScore",
    "CandidateSourceRequirement",
    "EdgeCandidateBoundary",
    "EdgeCandidateFactoryConfig",
    "EdgeCandidateFactoryRun",
    "EdgeCandidateFactoryWriteResult",
    "EdgeCandidateSearchLedger",
    "EdgeCandidateSearchLedgerRow",
    "LLMAdversarialEvidenceReview",
    "RiskActualCashHandoff",
    "SmartCandidateCard",
    "SmartCandidatePriorReport",
    "SmartPriorDefinition",
    "SmartPriorFamily",
    "TrialMultiplicityAccount",
    "VirtualExecutionGate",
    "DEFAULT_SMART_PRIOR_CAUSE_IDS",
    "DEFAULT_SMART_PRIOR_FAMILY_IDS",
    "build_default_candidate_card",
    "build_edge_candidate_factory_run",
    "build_backtest_kill_gate",
    "build_trial_multiplicity_account",
    "build_virtual_execution_gate",
    "default_smart_prior_families",
    "default_smart_prior_family_ids",
    "extract_backtest_metrics",
    "family_event_threshold",
    "smart_prior_family_by_id",
    "write_edge_candidate_factory_run",
    "MultiplicityAccountError",
]
