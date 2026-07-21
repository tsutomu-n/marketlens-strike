from __future__ import annotations

from dataclasses import dataclass

from sis.edge_candidate_factory._contracts import (
    CandidateDecision,
    CandidateGateStatus,
    CausePrior,
    Observable,
)
from sis.edge_candidate_factory.models import (
    CandidateExecutionPrecheck,
    CandidateMechanismCard,
    CandidatePriorScore,
    CandidateSourceRequirement,
    SmartCandidateCard,
)


@dataclass(frozen=True)
class ExecutionPrecheckTemplate:
    max_spread_bps: float = 12.0
    min_depth_usd: float = 10_000.0
    estimated_operator_time_minutes: int = 15
    estimated_capital_tied_up_minutes: int = 60
    fee_rate_required: bool = True
    funding_required: bool = True

    def to_precheck(
        self,
        *,
        venue_id: str,
        product_type: str,
        symbol: str,
    ) -> CandidateExecutionPrecheck:
        return CandidateExecutionPrecheck(
            venue_id=venue_id,
            product_type=product_type,
            symbol=symbol,
            min_notional_ok=False,
            tick_size_ok=False,
            lot_size_ok=False,
            max_spread_bps=self.max_spread_bps,
            observed_spread_bps=None,
            min_depth_usd=self.min_depth_usd,
            observed_depth_usd=None,
            fee_rate_available=False,
            funding_available=not self.funding_required,
            estimated_operator_time_minutes=self.estimated_operator_time_minutes,
            estimated_capital_tied_up_minutes=self.estimated_capital_tied_up_minutes,
            unexecutable_reasons=["runtime_execution_precheck_not_run"],
            execution_precheck_status=CandidateGateStatus.NOT_ESTIMABLE,
        )


@dataclass(frozen=True)
class SourceRequirementTemplate:
    source_id: str
    source_type: str
    expected_schema: str
    available_at_policy: str = "must be available before candidate evaluation timestamp"
    required: bool = True

    def to_requirement(self) -> CandidateSourceRequirement:
        return CandidateSourceRequirement(
            source_id=self.source_id,
            source_type=self.source_type,
            required=self.required,
            expected_schema=self.expected_schema,
            available_at_policy=self.available_at_policy,
            status=CandidateGateStatus.NOT_ESTIMABLE,
            known_gaps=[],
        )


@dataclass(frozen=True)
class MechanismTemplate:
    mechanism_id: str
    mechanism_summary: str
    who_is_forced_or_constrained: str
    why_flow_may_be_unfavorable: str
    expected_time_horizon: str
    failure_modes: tuple[str, ...]
    counter_hypothesis: str

    def to_card(self) -> CandidateMechanismCard:
        return CandidateMechanismCard(
            mechanism_id=self.mechanism_id,
            mechanism_summary=self.mechanism_summary,
            who_is_forced_or_constrained=self.who_is_forced_or_constrained,
            why_flow_may_be_unfavorable=self.why_flow_may_be_unfavorable,
            expected_time_horizon=self.expected_time_horizon,
            failure_modes=list(self.failure_modes),
            counter_hypothesis=self.counter_hypothesis,
        )


@dataclass(frozen=True)
class SmartPriorDefinition:
    cause_prior: str
    mechanism_template: str
    allowed_observables: tuple[str, ...]
    default_action_set: tuple[str, ...]
    required_sources: tuple[str, ...]
    default_execution_precheck: ExecutionPrecheckTemplate
    default_kill_conditions: tuple[str, ...]
    expected_information_gain_template: str


@dataclass(frozen=True)
class SmartPriorFamily:
    family_id: str
    cause_priors: tuple[str, ...]
    mechanism: MechanismTemplate
    allowed_observables: tuple[str, ...]
    default_action_set: tuple[str, ...]
    required_sources: tuple[SourceRequirementTemplate, ...]
    default_execution_precheck: ExecutionPrecheckTemplate
    default_kill_conditions: tuple[str, ...]
    expected_information_gain_template: str
    entry_logic: str
    exit_logic: str
    family_role: str = "candidate_signal"
    structural_cause_role: str = "structural_cause"
    negative_control_refs: tuple[str, ...] = ("no_trade",)
    test_cost_estimate: str = "low"
    operator_burden_estimate: str = "low"


def _source(
    source_id: str,
    source_type: str,
    expected_schema: str,
) -> SourceRequirementTemplate:
    return SourceRequirementTemplate(
        source_id=source_id,
        source_type=source_type,
        expected_schema=expected_schema,
    )


def _precheck(
    *,
    max_spread_bps: float = 12.0,
    min_depth_usd: float = 10_000.0,
    funding_required: bool = True,
) -> ExecutionPrecheckTemplate:
    return ExecutionPrecheckTemplate(
        max_spread_bps=max_spread_bps,
        min_depth_usd=min_depth_usd,
        funding_required=funding_required,
    )


def _mechanism(
    mechanism_id: str,
    summary: str,
    forced: str,
    unfavorable: str,
    counter: str,
    failures: tuple[str, ...],
    horizon: str = "5m_to_60m",
) -> MechanismTemplate:
    return MechanismTemplate(
        mechanism_id=mechanism_id,
        mechanism_summary=summary,
        who_is_forced_or_constrained=forced,
        why_flow_may_be_unfavorable=unfavorable,
        expected_time_horizon=horizon,
        failure_modes=failures,
        counter_hypothesis=counter,
    )


DEFAULT_SMART_PRIOR_DEFINITIONS: tuple[SmartPriorDefinition, ...] = (
    SmartPriorDefinition(
        cause_prior=CausePrior.FORCED_FLOW.value,
        mechanism_template="forced participants trade because of margin, stop, or funding pressure",
        allowed_observables=("liquidation_notional", "liquidation_side", "funding_rate"),
        default_action_set=("reversal_long", "reversal_short", "no_trade"),
        required_sources=("liquidation_events", "funding_history", "market_snapshot"),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("forced_flow_not_observed", "spread_widens"),
        expected_information_gain_template="tests whether forced flow exhaustion changes outcome",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.INVENTORY_RISK_TRANSFER.value,
        mechanism_template="liquidity providers transfer inventory risk after adverse flow",
        allowed_observables=("book_depth", "spread_bps", "order_flow_imbalance"),
        default_action_set=("no_trade", "fade_inventory_dislocation"),
        required_sources=("order_book", "aggressive_trades"),
        default_execution_precheck=_precheck(max_spread_bps=8.0),
        default_kill_conditions=("depth_missing", "adverse_selection_worsens"),
        expected_information_gain_template="tests whether inventory transfer predicts short horizon flow",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.SLOW_INFORMATION.value,
        mechanism_template="information arrives unevenly across venues or reference markets",
        allowed_observables=("mark_price", "index_price", "spot_perp_basis_bps"),
        default_action_set=("basis_reversion", "no_trade"),
        required_sources=("mark_index", "spot_reference"),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("reference_stale", "basis_not_observed"),
        expected_information_gain_template="tests whether slow reference adjustment remains tradable",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.CONSTRAINED_ARBITRAGE.value,
        mechanism_template="basis persists when arbitrage capacity or venue access is constrained",
        allowed_observables=("mark_index_basis_bps", "spot_perp_basis_bps", "fee_rate"),
        default_action_set=("basis_reversion", "no_trade"),
        required_sources=("basis_snapshot", "fee_snapshot"),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("basis_after_cost_negative", "borrow_or_fee_missing"),
        expected_information_gain_template="tests whether constrained basis survives costs",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.CROWDED_POSITIONING.value,
        mechanism_template="position crowding increases forced unwind or continuation risk",
        allowed_observables=("open_interest", "open_interest_change", "funding_rate"),
        default_action_set=("continuation", "reversal", "no_trade"),
        required_sources=("open_interest", "funding_history"),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("oi_impulse_absent", "crowding_proxy_stale"),
        expected_information_gain_template="tests whether crowding proxy improves over no trade",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.BEHAVIORAL_ATTENTION.value,
        mechanism_template="attention shock can overextend near-term flow before mean reversion",
        allowed_observables=("volume", "turnover", "realized_volatility"),
        default_action_set=("volume_shock_reversal", "no_trade"),
        required_sources=("trade_bars", "volume_snapshot"),
        default_execution_precheck=_precheck(funding_required=False),
        default_kill_conditions=("volume_shock_absent", "reversal_after_cost_negative"),
        expected_information_gain_template="tests whether attention shock adds reversal information",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.ADVERSE_SELECTION.value,
        mechanism_template="thin or stale liquidity raises the chance of being picked off",
        allowed_observables=("spread_bps", "book_depth", "quote_age"),
        default_action_set=("no_trade",),
        required_sources=("order_book", "quote_age"),
        default_execution_precheck=_precheck(max_spread_bps=6.0, funding_required=False),
        default_kill_conditions=("spread_widens", "quote_stale"),
        expected_information_gain_template="tests whether filtering bad liquidity improves outcomes",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.EXECUTION_FRICTION.value,
        mechanism_template="fees, funding, spread, and lot constraints can erase gross edge",
        allowed_observables=("fee_rate", "funding_rate", "spread_bps", "min_notional"),
        default_action_set=("no_trade", "cost_filtered_signal"),
        required_sources=("fee_snapshot", "funding_history", "instrument_constraints"),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("after_cost_edge_negative", "instrument_constraint_missing"),
        expected_information_gain_template="tests whether execution costs dominate the idea",
    ),
    SmartPriorDefinition(
        cause_prior=CausePrior.DATA_OBSERVABILITY.value,
        mechanism_template="missing or stale sources can create false candidate evidence",
        allowed_observables=("source_quality", "available_at", "quote_age"),
        default_action_set=("no_trade",),
        required_sources=("source_manifest", "available_at_index"),
        default_execution_precheck=_precheck(funding_required=False),
        default_kill_conditions=("source_quality_low", "available_at_missing"),
        expected_information_gain_template="tests whether the candidate is observable without leakage",
    ),
)

DEFAULT_SMART_PRIOR_CAUSE_IDS = tuple(
    definition.cause_prior for definition in DEFAULT_SMART_PRIOR_DEFINITIONS
)

DEFAULT_SMART_PRIOR_FAMILIES: tuple[SmartPriorFamily, ...] = (
    SmartPriorFamily(
        family_id="funding_pressure_reversion",
        cause_priors=("FORCED_FLOW", "CROWDED_POSITIONING", "EXECUTION_FRICTION"),
        mechanism=_mechanism(
            "funding_pressure_reversion",
            "Extreme funding pressure may force crowded holders to rebalance before reversion.",
            "Crowded perpetual holders paying or receiving extreme funding.",
            "Funding-constrained participants accept worse prices to reduce exposure.",
            "Funding pressure marks persistent trend instead of reversion.",
            ("funding_extreme_not_observed", "trend_continues", "after_cost_edge_negative"),
        ),
        allowed_observables=("funding_rate", "funding_window", "open_interest", "spread_bps"),
        default_action_set=("funding_pressure_reversion", "no_trade"),
        required_sources=(
            _source("funding_history", "funding", "funding_history_event.v1"),
            _source("market_snapshot", "market", "crypto_perp_market_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("funding_extreme_not_observed", "after_cost_edge_negative"),
        expected_information_gain_template="does funding pressure add reversal signal after costs?",
        entry_logic="evaluate reversal only after funding pressure is observable before decision time",
        exit_logic="exit when funding pressure normalizes or spread widens",
    ),
    SmartPriorFamily(
        family_id="mark_index_basis_reversion",
        cause_priors=("CONSTRAINED_ARBITRAGE", "SLOW_INFORMATION", "DATA_OBSERVABILITY"),
        mechanism=_mechanism(
            "mark_index_basis_reversion",
            "Mark-index dislocation can revert when reference pricing catches up.",
            "Arbitrageurs constrained by fees, latency, or inventory.",
            "Basis traders may accept weaker prices while the constraint is binding.",
            "Basis reflects correct risk premium and does not revert.",
            ("basis_not_observed", "reference_stale", "spread_widens"),
        ),
        allowed_observables=("mark_price", "index_price", "mark_index_basis_bps", "spread_bps"),
        default_action_set=("basis_reversion", "no_trade"),
        required_sources=(
            _source("mark_index_snapshot", "basis", "crypto_perp_market_snapshot.v1"),
            _source("fee_snapshot", "fee", "fee_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(max_spread_bps=10.0),
        default_kill_conditions=("basis_after_cost_negative", "reference_stale"),
        expected_information_gain_template="does mark-index basis revert more than no trade after costs?",
        entry_logic="enter only when mark-index basis is observable and reference is fresh",
        exit_logic="exit on basis normalization or stale reference",
    ),
    SmartPriorFamily(
        family_id="liquidation_exhaustion_reversal",
        cause_priors=("FORCED_FLOW", "CROWDED_POSITIONING"),
        mechanism=_mechanism(
            "liquidation_exhaustion_reversal",
            "Large forced liquidation can exhaust one-sided pressure and create reversion.",
            "Leveraged holders forced to liquidate.",
            "Forced sellers or buyers accept poor prices during thin liquidity.",
            "Cascade continuation dominates exhaustion.",
            ("cascade_continues", "liquidity_does_not_recover", "spread_widens"),
        ),
        allowed_observables=(
            "liquidation_notional",
            "liquidation_side",
            "spread_bps",
            "book_depth",
        ),
        default_action_set=("liquidation_exhaustion_reversal", "no_trade"),
        required_sources=(
            _source("liquidation_events", "liquidation", "crypto_perp_event.v1"),
            _source("order_book", "book", "quote_log_v2.schema.json"),
        ),
        default_execution_precheck=_precheck(max_spread_bps=8.0),
        default_kill_conditions=("liquidation_notional_missing", "spread_widens"),
        expected_information_gain_template="does liquidation exhaustion improve over no trade?",
        entry_logic="consider reversal only after forced flow slows and liquidity starts to recover",
        exit_logic="exit when cascade resumes or depth fails to recover",
    ),
    SmartPriorFamily(
        family_id="liquidation_cascade_continuation",
        cause_priors=("FORCED_FLOW", "CROWDED_POSITIONING"),
        mechanism=_mechanism(
            "liquidation_cascade_continuation",
            "Liquidation clusters can continue while margin pressure remains unresolved.",
            "Leveraged holders near liquidation thresholds.",
            "Participants liquidate into worsening prices as margin pressure propagates.",
            "Cascade exhausts quickly and reverses.",
            ("liquidation_cluster_absent", "depth_recovers", "continuation_after_cost_negative"),
        ),
        allowed_observables=("liquidation_notional", "liquidation_side", "open_interest_change"),
        default_action_set=("liquidation_cascade_continuation", "no_trade"),
        required_sources=(
            _source("liquidation_events", "liquidation", "crypto_perp_event.v1"),
            _source("open_interest", "positioning", "crypto_perp_market_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(max_spread_bps=10.0),
        default_kill_conditions=("cascade_signal_absent", "largest_loss_exceeds_limit"),
        expected_information_gain_template="does cascade continuation beat reversal and no trade?",
        entry_logic="enter continuation only while liquidation clustering and OI stress persist",
        exit_logic="exit when liquidation flow decays or adverse spread expands",
    ),
    SmartPriorFamily(
        family_id="oi_impulse_continuation",
        cause_priors=("CROWDED_POSITIONING", "SLOW_INFORMATION"),
        mechanism=_mechanism(
            "oi_impulse_continuation",
            "Open-interest impulse can indicate new positioning that continues briefly.",
            "Late entrants adding exposure after a directional move.",
            "Positioning flow may chase price before information is fully absorbed.",
            "OI impulse is hedging noise or immediate exhaustion.",
            ("oi_impulse_absent", "volume_confirmation_missing", "trend_fails"),
        ),
        allowed_observables=("open_interest", "open_interest_change", "volume", "turnover"),
        default_action_set=("oi_impulse_continuation", "no_trade"),
        required_sources=(
            _source("open_interest", "positioning", "crypto_perp_market_snapshot.v1"),
            _source("trade_bars", "trades", "crypto_perp_tournament_rows.v2"),
        ),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("oi_impulse_absent", "stress_edge_negative"),
        expected_information_gain_template="does OI impulse add continuation information?",
        entry_logic="enter continuation only with fresh OI impulse and volume confirmation",
        exit_logic="exit when OI impulse mean-reverts or no-trade catches up",
    ),
    SmartPriorFamily(
        family_id="volume_shock_reversal",
        cause_priors=("BEHAVIORAL_ATTENTION", "ADVERSE_SELECTION"),
        mechanism=_mechanism(
            "volume_shock_reversal",
            "Attention-driven volume shocks can overextend price and then mean revert.",
            "Attention-led flow and liquidity takers chasing a move.",
            "Late attention flow may accept worse prices after the easy move is gone.",
            "Volume shock reflects real information and continues.",
            ("volume_shock_absent", "information_continues", "spread_widens"),
        ),
        allowed_observables=("volume", "turnover", "realized_volatility", "spread_bps"),
        default_action_set=("volume_shock_reversal", "no_trade"),
        required_sources=(
            _source("trade_bars", "trades", "crypto_perp_tournament_rows.v2"),
            _source("market_snapshot", "market", "crypto_perp_market_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(funding_required=False),
        default_kill_conditions=("volume_shock_absent", "reversal_after_cost_negative"),
        expected_information_gain_template="does volume shock reversal survive costs and spread?",
        entry_logic="enter reversal only after volume shock has peaked and spread is controlled",
        exit_logic="exit when realized volatility expands against the reversal",
    ),
    SmartPriorFamily(
        family_id="volatility_compression_breakout",
        cause_priors=("CROWDED_POSITIONING", "DATA_OBSERVABILITY"),
        mechanism=_mechanism(
            "volatility_compression_breakout",
            "Volatility compression is a regime state that can precede breakout tests.",
            "Crowded or inactive participants waiting for new information.",
            "When compression breaks, late participants may cross spread to reposition.",
            "Compression persists or breakout fails after costs.",
            ("compression_not_observed", "breakout_fails", "source_quality_low"),
            horizon="15m_to_240m",
        ),
        allowed_observables=(
            "volatility_compression",
            "realized_volatility",
            "volume",
            "spread_bps",
        ),
        default_action_set=("volatility_compression_breakout", "no_trade"),
        required_sources=(
            _source("bar_features", "bars", "crypto_perp_feature_pack.v1"),
            _source("source_quality", "quality", "crypto_perp_source_availability.v1"),
        ),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("compression_not_observed", "breakout_after_cost_negative"),
        expected_information_gain_template="does compression regime improve breakout selection?",
        entry_logic="enter breakout only after compression state and fresh volume confirmation",
        exit_logic="exit when breakout fails or spread expands",
        structural_cause_role="regime_state",
    ),
    SmartPriorFamily(
        family_id="spread_widening_no_trade",
        cause_priors=("ADVERSE_SELECTION", "EXECUTION_FRICTION"),
        mechanism=_mechanism(
            "spread_widening_no_trade",
            "Spread widening is a no-trade filter for adverse selection and execution friction.",
            "Liquidity takers facing stale or thin quotes.",
            "Crossing a wide spread pays too much for uncertain information.",
            "Spread widening is temporary and harmless for the candidate.",
            ("spread_not_wide", "depth_recovers", "missed_trade_opportunity"),
        ),
        allowed_observables=("spread_bps", "book_depth", "quote_age", "fee_rate"),
        default_action_set=("no_trade",),
        required_sources=(
            _source("order_book", "book", "quote_log_v2.schema.json"),
            _source("fee_snapshot", "fee", "fee_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(max_spread_bps=6.0, funding_required=False),
        default_kill_conditions=("spread_not_wide", "filter_does_not_reduce_loss"),
        expected_information_gain_template="does no-trade filtering improve after-cost outcomes?",
        entry_logic="avoid entries when spread and depth conditions are unfavorable",
        exit_logic="release filter when spread and depth normalize",
        family_role="filter_no_trade",
        negative_control_refs=("always_trade",),
    ),
    SmartPriorFamily(
        family_id="funding_window_avoidance",
        cause_priors=("EXECUTION_FRICTION", "CROWDED_POSITIONING"),
        mechanism=_mechanism(
            "funding_window_avoidance",
            "Funding windows can turn a gross edge into an avoidable after-cost loss.",
            "Participants holding through funding despite unfavorable carry.",
            "Funding cost forces position changes near settlement windows.",
            "Funding window is already priced and does not affect after-cost edge.",
            ("funding_window_missing", "after_cost_edge_positive_through_window"),
        ),
        allowed_observables=("funding_window", "funding_rate", "fee_rate", "session_time"),
        default_action_set=("no_trade", "avoid_funding_window"),
        required_sources=(
            _source("funding_history", "funding", "funding_history_event.v1"),
            _source("fee_snapshot", "fee", "fee_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("funding_window_missing", "avoidance_not_better_than_no_trade"),
        expected_information_gain_template="does avoiding funding windows improve after-cost edge?",
        entry_logic="suppress entries that would hold through unfavorable funding windows",
        exit_logic="release avoidance after funding window passes",
        family_role="filter_no_trade",
    ),
    SmartPriorFamily(
        family_id="cross_market_basis_dislocation",
        cause_priors=("CONSTRAINED_ARBITRAGE", "SLOW_INFORMATION", "DATA_OBSERVABILITY"),
        mechanism=_mechanism(
            "cross_market_basis_dislocation",
            "Cross-market basis can persist when arbitrage is delayed or constrained.",
            "Arbitrageurs and hedgers with constrained venue access or stale references.",
            "Delayed arbitrage can leave one venue temporarily mispriced.",
            "Basis reflects real risk premium or stale source artifact.",
            ("basis_source_stale", "basis_after_cost_negative", "reference_missing"),
            horizon="15m_to_240m",
        ),
        allowed_observables=("spot_perp_basis_bps", "mark_index_basis_bps", "available_at"),
        default_action_set=("cross_market_basis_reversion", "no_trade"),
        required_sources=(
            _source("spot_reference", "reference", "crypto_perp_market_snapshot.v1"),
            _source("perp_reference", "perp", "crypto_perp_market_snapshot.v1"),
        ),
        default_execution_precheck=_precheck(),
        default_kill_conditions=("basis_source_stale", "after_cost_edge_negative"),
        expected_information_gain_template="does cross-market basis survive freshness and costs?",
        entry_logic="enter only when both market references are fresh and basis is observable",
        exit_logic="exit on basis normalization or source staleness",
    ),
)

DEFAULT_SMART_PRIOR_FAMILY_IDS = tuple(family.family_id for family in DEFAULT_SMART_PRIOR_FAMILIES)


def default_smart_prior_families() -> tuple[SmartPriorFamily, ...]:
    return DEFAULT_SMART_PRIOR_FAMILIES


def default_smart_prior_family_ids() -> tuple[str, ...]:
    return DEFAULT_SMART_PRIOR_FAMILY_IDS


def smart_prior_family_by_id(family_id: str) -> SmartPriorFamily:
    normalized = family_id.strip()
    for family in DEFAULT_SMART_PRIOR_FAMILIES:
        if family.family_id == normalized:
            return family
    raise KeyError(f"Unknown smart prior family: {normalized}")


def _default_prior_score(family: SmartPriorFamily) -> CandidatePriorScore:
    is_filter = family.family_role == "filter_no_trade"
    return CandidatePriorScore(
        mechanism_score=0.55,
        source_availability_score=0.5,
        execution_feasibility_score=0.45 if not is_filter else 0.7,
        testability_score=0.65,
        diversity_score=0.6,
        information_gain_score=0.6,
        operator_cost_penalty=0.2,
        unexecutable_penalty=0.35 if not is_filter else 0.05,
        overfit_surface_penalty=0.25,
        total_score=0.55 if not is_filter else 0.6,
        score_basis="prior_not_profit_proof",
    )


def build_default_candidate_card(
    family_id: str,
    *,
    candidate_id: str,
    venue_id: str,
    product_type: str,
    symbol: str,
) -> SmartCandidateCard:
    family = smart_prior_family_by_id(family_id)
    return SmartCandidateCard(
        candidate_id=candidate_id,
        candidate_status="UNVERIFIED_CANDIDATE",
        candidate_decision=CandidateDecision.GENERATED,
        cause_priors=[CausePrior(cause_prior) for cause_prior in family.cause_priors],
        family=family.family_id,
        mechanism_card=family.mechanism.to_card(),
        observables=[Observable(observable) for observable in family.allowed_observables],
        required_sources=[source.to_requirement() for source in family.required_sources],
        source_requirement_status=CandidateGateStatus.NOT_ESTIMABLE,
        execution_precheck=family.default_execution_precheck.to_precheck(
            venue_id=venue_id,
            product_type=product_type,
            symbol=symbol,
        ),
        candidate_prior_score=_default_prior_score(family),
        parameter_set={"family_id": family.family_id, "profile": "core_default"},
        action_set=list(family.default_action_set),
        entry_logic=family.entry_logic,
        exit_logic=family.exit_logic,
        kill_conditions=list(family.default_kill_conditions),
        expected_information_gain=family.expected_information_gain_template,
        test_cost_estimate=family.test_cost_estimate,
        operator_burden_estimate=family.operator_burden_estimate,
        candidate_cluster_id=family.family_id,
        similar_candidate_count=0,
        negative_control_refs=list(family.negative_control_refs),
        proof_status="not_alpha_or_profit_proof",
        rejection_reason=None,
        shortlist_reason="default smart prior catalog entry; not selected for paper or live",
    )
