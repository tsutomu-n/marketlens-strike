from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import (
    CandidateDecision,
    CandidateSetStatus,
    CandidateSourceArtifact,
    InputContractValidationRef,
    LeakagePolicy,
    SearchLedgerSummary,
    SelectionAdjustedMetricsStatus,
    SelectionPolicy,
    SplitPolicy,
    StrategyIdeaCandidate,
    StrategyIdeaCandidateSet,
    TimeWindow,
)
from sis.strategy_idea_candidates.perp_costs import perp_cost_estimate_from_parameter_set
from sis.strategy_idea_candidates.service import (
    build_blocked_candidate_set_from_input_evidence,
)
from sis.strategy_inputs.models import (
    InputValidationStatus,
    ProducerInfo,
    SourceValidationResult,
    SourceValidationStatus,
    StrategyInputContract,
    StrategyInputSource,
    StrategyInputContractValidation,
)
from sis.strategy_review.provenance import repo_relative_path


GENERATOR_VERSION = "deterministic-candidate-generator-v0"


class CandidateFamilyId(StrEnum):
    TREND_MOMENTUM = "trend_momentum"
    VOLATILITY_REGIME = "volatility_regime"
    LIQUIDITY_SPREAD = "liquidity_spread"
    CROSS_SECTIONAL_RANK = "cross_sectional_rank"
    MEAN_REVERSION = "mean_reversion"
    REGIME_FILTER = "regime_filter"
    PERP_MOMENTUM_CONTINUATION = "perp_momentum_continuation"
    PERP_REVERSAL_AFTER_LIQUIDATION_MOVE = "perp_reversal_after_liquidation_move"
    PERP_FUNDING_RATE_CARRY_FILTER = "perp_funding_rate_carry_filter"
    PERP_BASIS_MARK_INDEX_SPREAD = "perp_basis_mark_index_spread"
    PERP_VOLATILITY_BREAKOUT_COMPRESSION = "perp_volatility_breakout_compression"
    PERP_LIQUIDITY_SPREAD_FILTER = "perp_liquidity_spread_filter"
    PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE = "perp_open_interest_liquidation_pressure"


class StrategyIdeaCandidateProfile(StrEnum):
    DEFAULT = "default"
    CRYPTO_PERP_RISK_TAKER = "crypto-perp-risk-taker"


class StrategyIdeaCandidateGeneratorError(ValueError):
    pass


class StrategyIdeaCandidateGeneratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_set_id: str
    generator_version: str = GENERATOR_VERSION
    profile: StrategyIdeaCandidateProfile = StrategyIdeaCandidateProfile.DEFAULT
    family_ids: list[CandidateFamilyId] = Field(
        default_factory=lambda: [
            CandidateFamilyId.TREND_MOMENTUM,
            CandidateFamilyId.VOLATILITY_REGIME,
            CandidateFamilyId.LIQUIDITY_SPREAD,
            CandidateFamilyId.CROSS_SECTIONAL_RANK,
            CandidateFamilyId.MEAN_REVERSION,
        ],
        min_length=1,
    )
    parameter_grids: dict[str, list[dict[str, Any]]] | None = None
    candidate_cap: int = Field(ge=1, default=25)
    shortlist_count: int = Field(ge=1, default=1)
    target_definition: str = "next_window_return"
    prediction_horizon: str = "5_sessions"
    timeframe: str | None = None
    label_window: TimeWindow
    feature_observation_window: TimeWindow
    train_window: TimeWindow
    validation_window: TimeWindow
    sealed_test_window: TimeWindow | None = None
    generated_at: datetime | None = None
    available_at_policy: str = "features must be available at or before decision timestamp"
    purge_policy: str = "policy_record_only:not_implemented"
    embargo_policy: str = "policy_record_only:not_implemented"
    dependency_versions: dict[str, str] = Field(default_factory=lambda: {"sis": "local"})

    @field_validator("family_ids")
    @classmethod
    def validate_family_ids(cls, value: list[CandidateFamilyId]) -> list[CandidateFamilyId]:
        if CandidateFamilyId.REGIME_FILTER in value:
            raise ValueError("regime_filter is filter metadata and not a standalone C4 family")
        if len(value) != len(set(value)):
            raise ValueError("family_ids must not contain duplicates")
        return value

    @field_validator(
        "candidate_set_id",
        "generator_version",
        "target_definition",
        "prediction_horizon",
        "available_at_policy",
        "purge_policy",
        "embargo_policy",
    )
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return _serialize_datetime(value)


def stable_parameter_grid_hash(parameter_grids: dict[str, list[dict[str, Any]]]) -> str:
    payload = json.dumps(parameter_grids, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def default_parameter_grids() -> dict[str, list[dict[str, Any]]]:
    return {
        CandidateFamilyId.TREND_MOMENTUM.value: [
            {"lookback": 20, "threshold_z": 1.0},
            {"lookback": 60, "threshold_z": 1.0},
        ],
        CandidateFamilyId.VOLATILITY_REGIME.value: [
            {"volatility_lookback": 20, "regime": "compression"},
            {"volatility_lookback": 20, "regime": "expansion"},
        ],
        CandidateFamilyId.LIQUIDITY_SPREAD.value: [
            {"spread_limit_bps": 5},
            {"spread_limit_bps": 10},
        ],
        CandidateFamilyId.CROSS_SECTIONAL_RANK.value: [
            {"rank_lookback": 20, "top_quantile": 0.2},
        ],
        CandidateFamilyId.MEAN_REVERSION.value: [
            {"lookback": 10, "z_entry": 1.5},
            {"lookback": 20, "z_entry": 1.5},
        ],
        CandidateFamilyId.PERP_MOMENTUM_CONTINUATION.value: [
            _perp_parameter_set(
                side_bias="long",
                lookback=12,
                breakout_z=1.0,
                liquidation_buffer_bps=2500,
            ),
            _perp_parameter_set(
                side_bias="short",
                lookback=24,
                breakout_z=1.2,
                liquidation_buffer_bps=3000,
            ),
        ],
        CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE.value: [
            _perp_parameter_set(
                side_bias="both",
                liquidation_move_bps=150,
                reversal_wait_bars=2,
                liquidation_buffer_bps=3000,
            ),
            _perp_parameter_set(
                side_bias="short",
                liquidation_move_bps=250,
                reversal_wait_bars=3,
                liquidation_buffer_bps=3500,
            ),
        ],
        CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER.value: [
            _perp_parameter_set(
                side_bias="long",
                funding_rate_threshold_bps=-2,
                holding_bars=8,
                liquidation_buffer_bps=2500,
            ),
            _perp_parameter_set(
                side_bias="short",
                funding_rate_threshold_bps=2,
                holding_bars=8,
                liquidation_buffer_bps=2500,
            ),
        ],
        CandidateFamilyId.PERP_BASIS_MARK_INDEX_SPREAD.value: [
            _perp_parameter_set(
                side_bias="both",
                mark_index_spread_bps=8,
                mean_revert_bars=4,
                liquidation_buffer_bps=3000,
            ),
        ],
        CandidateFamilyId.PERP_VOLATILITY_BREAKOUT_COMPRESSION.value: [
            _perp_parameter_set(
                side_bias="long",
                compression_lookback=48,
                expansion_z=1.5,
                liquidation_buffer_bps=2500,
            ),
            _perp_parameter_set(
                side_bias="short",
                compression_lookback=48,
                expansion_z=1.5,
                liquidation_buffer_bps=2500,
            ),
        ],
        CandidateFamilyId.PERP_LIQUIDITY_SPREAD_FILTER.value: [
            _perp_parameter_set(
                side_bias="no_trade",
                spread_limit_bps=12,
                depth_imbalance_limit=0.7,
                liquidation_buffer_bps=4000,
            ),
        ],
        CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE.value: [
            _perp_parameter_set(
                side_bias="both",
                oi_change_threshold_pct=3,
                liquidation_pressure_bps=100,
                liquidation_buffer_bps=3500,
            ),
        ],
    }


def default_family_ids_for_profile(
    profile: StrategyIdeaCandidateProfile,
) -> list[CandidateFamilyId]:
    if profile is StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER:
        return [
            CandidateFamilyId.PERP_MOMENTUM_CONTINUATION,
            CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE,
            CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER,
            CandidateFamilyId.PERP_BASIS_MARK_INDEX_SPREAD,
            CandidateFamilyId.PERP_VOLATILITY_BREAKOUT_COMPRESSION,
            CandidateFamilyId.PERP_LIQUIDITY_SPREAD_FILTER,
            CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE,
        ]
    return [
        CandidateFamilyId.TREND_MOMENTUM,
        CandidateFamilyId.VOLATILITY_REGIME,
        CandidateFamilyId.LIQUIDITY_SPREAD,
        CandidateFamilyId.CROSS_SECTIONAL_RANK,
        CandidateFamilyId.MEAN_REVERSION,
    ]


def build_deterministic_candidate_set_from_input_evidence(
    *,
    contract: StrategyInputContract,
    validation: StrategyInputContractValidation,
    validation_path: Path,
    config: StrategyIdeaCandidateGeneratorConfig,
) -> StrategyIdeaCandidateSet:
    if validation.validation_status is not InputValidationStatus.PASS:
        return build_blocked_candidate_set_from_input_evidence(
            candidate_set_id=config.candidate_set_id,
            contract=contract,
            validation=validation,
            validation_path=validation_path,
            generated_at=config.generated_at,
            generator_version=config.generator_version,
            dependency_versions=config.dependency_versions,
        )

    parameter_grids = _parameter_grids_for_config(config)
    parameter_grid_hash = stable_parameter_grid_hash(parameter_grids)
    source_artifacts = _source_artifacts_from_input_evidence(contract, validation)
    source_hash = _primary_source_hash(source_artifacts)
    timeframe = config.timeframe or contract.strategy_scope.timeframe
    generated_at = config.generated_at or validation.validated_at

    candidates: list[StrategyIdeaCandidate] = []
    seen_parameter_sets: set[str] = set()
    duplicate_rejection_count = 0
    cap_rejection_count = 0
    unique_candidate_count = 0
    shortlist_count = 0
    trial_index = 0

    for family in config.family_ids:
        grid = parameter_grids[family.value]
        for parameter_set in grid:
            trial_index += 1
            candidate_id = f"cand-{trial_index:03d}-{family.value}"
            duplicate_key = _canonical_json(
                {"family": family.value, "parameter_set": parameter_set}
            )
            signal_expression = _signal_expression(family, parameter_set)
            if duplicate_key in seen_parameter_sets:
                duplicate_rejection_count += 1
                candidates.append(
                    _candidate(
                        candidate_id=candidate_id,
                        decision=CandidateDecision.REJECTED,
                        family=family,
                        parameter_set=parameter_set,
                        parameter_grid_hash=parameter_grid_hash,
                        signal_expression=signal_expression,
                        contract=contract,
                        config=config,
                        timeframe=timeframe,
                        source_hash=source_hash,
                        trial_index=trial_index,
                        rejection_reason=(
                            "duplicate parameterization: same family and parameter_set"
                        ),
                    )
                )
                continue

            seen_parameter_sets.add(duplicate_key)
            unique_candidate_count += 1
            if unique_candidate_count > config.candidate_cap:
                cap_rejection_count += 1
                candidates.append(
                    _candidate(
                        candidate_id=candidate_id,
                        decision=CandidateDecision.REJECTED,
                        family=family,
                        parameter_set=parameter_set,
                        parameter_grid_hash=parameter_grid_hash,
                        signal_expression=signal_expression,
                        contract=contract,
                        config=config,
                        timeframe=timeframe,
                        source_hash=source_hash,
                        trial_index=trial_index,
                        rejection_reason="candidate cap exceeded before shortlist",
                    )
                )
                continue

            perp_shortlist_rejection = _perp_shortlist_rejection_reason(
                profile=config.profile,
                family=family,
                parameter_set=parameter_set,
            )
            if perp_shortlist_rejection is not None:
                candidates.append(
                    _candidate(
                        candidate_id=candidate_id,
                        decision=CandidateDecision.REJECTED,
                        family=family,
                        parameter_set=parameter_set,
                        parameter_grid_hash=parameter_grid_hash,
                        signal_expression=signal_expression,
                        contract=contract,
                        config=config,
                        timeframe=timeframe,
                        source_hash=source_hash,
                        trial_index=trial_index,
                        rejection_reason=perp_shortlist_rejection,
                    )
                )
                continue

            if shortlist_count < config.shortlist_count:
                shortlist_count += 1
                candidates.append(
                    _candidate(
                        candidate_id=candidate_id,
                        decision=CandidateDecision.SHORTLISTED,
                        family=family,
                        parameter_set=parameter_set,
                        parameter_grid_hash=parameter_grid_hash,
                        signal_expression=signal_expression,
                        contract=contract,
                        config=config,
                        timeframe=timeframe,
                        source_hash=source_hash,
                        trial_index=trial_index,
                        shortlist_reason=(
                            "first deterministic candidate within cap; not alpha proof"
                        ),
                    )
                )
                continue

            candidates.append(
                _candidate(
                    candidate_id=candidate_id,
                    decision=CandidateDecision.REJECTED,
                    family=family,
                    parameter_set=parameter_set,
                    parameter_grid_hash=parameter_grid_hash,
                    signal_expression=signal_expression,
                    contract=contract,
                    config=config,
                    timeframe=timeframe,
                    source_hash=source_hash,
                    trial_index=trial_index,
                    rejection_reason="not selected by deterministic shortlist policy",
                )
            )

    shortlisted_ids = [
        candidate.idea_candidate_id
        for candidate in candidates
        if candidate.decision is CandidateDecision.SHORTLISTED
    ]
    rejected_ids = [
        candidate.idea_candidate_id
        for candidate in candidates
        if candidate.decision is CandidateDecision.REJECTED
    ]
    return StrategyIdeaCandidateSet(
        candidate_set_id=config.candidate_set_id,
        generated_at=generated_at,
        producer=ProducerInfo(command="strategy-idea-candidates-deterministic-generator"),
        generator_version=config.generator_version,
        candidate_set_status=CandidateSetStatus.BUILT,
        input_contract_validation_refs=[
            InputContractValidationRef(
                contract_id=validation.contract_id,
                validation_path=repo_relative_path(validation_path),
                validation_sha256=sha256_file(validation_path),
                validation_status=validation.validation_status,
            )
        ],
        source_artifacts=source_artifacts,
        candidate_inventory=candidates,
        parameter_grids=parameter_grids,
        search_ledger_summary=SearchLedgerSummary(
            family_count=len(config.family_ids),
            candidate_count_total=len(candidates),
            candidate_count_shortlisted=len(shortlisted_ids),
            candidate_count_rejected=len(rejected_ids),
            trial_count_total=trial_index,
            parameter_grid_hash=parameter_grid_hash,
            candidate_cap=config.candidate_cap,
            cap_rejection_count=cap_rejection_count,
            validation_peek_count=0,
            rerank_count=0,
            duplicate_rejection_count=duplicate_rejection_count,
        ),
        selection_policy=SelectionPolicy(
            policy_id="deterministic-generator-v0",
            description=(
                "Shortlist by fixed family/grid order only; raw metrics are not proof and "
                "sealed test data is not used for selection."
            ),
            shortlisted_candidate_ids=shortlisted_ids,
            rejected_candidate_ids=rejected_ids,
            known_gaps=[
                "selection-adjusted metrics engine runs locally but may be NOT_ESTIMABLE "
                "without raw p-values, return distributions, or fold outcomes",
                "purge and embargo are policy records only",
                "candidate output is UNVERIFIED_CANDIDATE and not paper/live permission",
            ],
        ),
        split_policy=SplitPolicy(
            split_method="fixed_policy_record_only",
            train_window=config.train_window,
            validation_window=config.validation_window,
            sealed_test_window=config.sealed_test_window,
            uses_sealed_test_for_selection=False,
        ),
        leakage_policy=LeakagePolicy(
            feature_available_at_policy=config.available_at_policy,
            purge_policy=config.purge_policy,
            embargo_policy=config.embargo_policy,
            uses_sealed_test_for_selection=False,
        ),
        dependency_versions=config.dependency_versions,
    )


def _parameter_grids_for_config(
    config: StrategyIdeaCandidateGeneratorConfig,
) -> dict[str, list[dict[str, Any]]]:
    defaults = default_parameter_grids()
    configured = config.parameter_grids or {}
    grids: dict[str, list[dict[str, Any]]] = {}
    for family in config.family_ids:
        grid = configured.get(family.value, defaults.get(family.value))
        if not grid:
            raise StrategyIdeaCandidateGeneratorError(f"missing parameter grid: {family.value}")
        grids[family.value] = [_canonicalize_parameter_set(item) for item in grid]
    return grids


def _source_artifacts_from_input_evidence(
    contract: StrategyInputContract,
    validation: StrategyInputContractValidation,
) -> list[CandidateSourceArtifact]:
    validation_by_source = {result.source_id: result for result in validation.source_results}
    artifacts: list[CandidateSourceArtifact] = []
    for source in contract.sources:
        result = validation_by_source.get(source.source_id)
        _validate_pass_source_evidence(source, result)
        sha256 = (result.actual_sha256 if result is not None else None) or source.declared_sha256
        if sha256 is None:
            raise StrategyIdeaCandidateGeneratorError(
                f"PASS input evidence is missing source hash: {source.source_id}"
            )
        artifacts.append(
            CandidateSourceArtifact(
                source_id=source.source_id,
                path=source.path,
                sha256=sha256,
                required=source.required,
                source_validation_status=(
                    result.status if result is not None else SourceValidationStatus.BLOCKED
                ),
                available_at=source.available_at,
                max_observed_timestamp=_coerce_optional_datetime(
                    result.max_observed_timestamp if result is not None else None
                ),
            )
        )
    return artifacts


def _validate_pass_source_evidence(
    source: StrategyInputSource,
    result: SourceValidationResult | None,
) -> None:
    if result is None:
        raise StrategyIdeaCandidateGeneratorError(
            f"invalid source evidence for PASS validation: missing result for {source.source_id}"
        )
    failures: list[str] = []
    if result.status is not SourceValidationStatus.PRESENT:
        failures.append(f"status={result.status.value}")
    if result.hash_matches is False:
        failures.append("hash_matches=false")
    if not result.available_at_present:
        failures.append("available_at_present=false")
    if result.generated_before_available is False:
        failures.append("generated_before_available=false")
    if result.max_observed_timestamp is None:
        failures.append("max_observed_timestamp=missing")
    if source.required and result.actual_sha256 is None and source.declared_sha256 is None:
        failures.append("source_hash=missing")
    if failures:
        details = ", ".join(failures)
        raise StrategyIdeaCandidateGeneratorError(
            f"invalid source evidence for PASS validation: {source.source_id}: {details}"
        )


def _primary_source_hash(source_artifacts: list[CandidateSourceArtifact]) -> str:
    for source in source_artifacts:
        if source.required:
            return source.sha256
    return source_artifacts[0].sha256


def _candidate(
    *,
    candidate_id: str,
    decision: CandidateDecision,
    family: CandidateFamilyId,
    parameter_set: dict[str, Any],
    parameter_grid_hash: str,
    signal_expression: str,
    contract: StrategyInputContract,
    config: StrategyIdeaCandidateGeneratorConfig,
    timeframe: str,
    source_hash: str,
    trial_index: int,
    rejection_reason: str | None = None,
    shortlist_reason: str | None = None,
) -> StrategyIdeaCandidate:
    raw_metrics = _raw_validation_metrics(config=config, parameter_set=parameter_set)
    if config.profile is StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER:
        estimate = perp_cost_estimate_from_parameter_set(
            candidate_id=candidate_id,
            family=family.value,
            parameter_set=parameter_set,
        )
        raw_metrics["perp_cost_estimate"] = estimate.model_dump(mode="json")
        raw_metrics["estimated_round_trip_cost_usd"] = estimate.estimated_round_trip_cost_usd
        raw_metrics["stress_round_trip_cost_usd"] = estimate.stress_round_trip_cost_usd
    return StrategyIdeaCandidate(
        idea_candidate_id=candidate_id,
        decision=decision,
        family=family.value,
        title=_title(family, contract.strategy_scope.instruments),
        hypothesis_template=_hypothesis_template(family),
        mechanism_status="UNVERIFIED_TEMPLATE",
        signal_expression=signal_expression,
        parameter_set=parameter_set,
        parameter_grid_ref=f"grid:{family.value}:{parameter_grid_hash}",
        target_definition=config.target_definition,
        prediction_horizon=config.prediction_horizon,
        timeframe=timeframe,
        instruments=contract.strategy_scope.instruments,
        label_window=config.label_window,
        feature_observation_window=config.feature_observation_window,
        feature_columns_used=_feature_columns(family),
        available_at_policy=config.available_at_policy,
        source_artifact_sha256=source_hash,
        trial_count_refs=[f"trial-{trial_index:03d}"],
        baseline_refs=["cash_or_no_trade"],
        novelty_checks={
            "duplicate_rule": "same family and parameter_set",
            "duplicate_signal": rejection_reason is not None
            and rejection_reason.startswith("duplicate parameterization"),
        },
        raw_validation_metrics=raw_metrics,
        selection_adjusted_metrics_status=SelectionAdjustedMetricsStatus.NOT_ESTIMABLE,
        leakage_checks={
            "uses_sealed_test_for_selection": False,
            "available_at_policy_recorded": True,
            "purge_policy": config.purge_policy,
            "embargo_policy": config.embargo_policy,
        },
        rejection_reason=rejection_reason,
        shortlist_reason=shortlist_reason,
    )


def _signal_expression(family: CandidateFamilyId, parameter_set: dict[str, Any]) -> str:
    if family is CandidateFamilyId.TREND_MOMENTUM:
        return (
            f"close_return_{parameter_set['lookback']}d "
            f"> {parameter_set['threshold_z']} * realized_volatility"
        )
    if family is CandidateFamilyId.VOLATILITY_REGIME:
        return (
            f"volatility_regime({parameter_set['volatility_lookback']}d) "
            f"== {parameter_set['regime']}"
        )
    if family is CandidateFamilyId.LIQUIDITY_SPREAD:
        return f"spread_bps <= {parameter_set['spread_limit_bps']}"
    if family is CandidateFamilyId.CROSS_SECTIONAL_RANK:
        return (
            f"cross_sectional_rank(return_{parameter_set['rank_lookback']}d) "
            f"<= {parameter_set['top_quantile']}"
        )
    if family is CandidateFamilyId.MEAN_REVERSION:
        return f"zscore(close, {parameter_set['lookback']}) <= -{parameter_set['z_entry']}"
    if family is CandidateFamilyId.PERP_MOMENTUM_CONTINUATION:
        return (
            f"mark_return_{parameter_set['lookback']}bars "
            f"> {parameter_set['breakout_z']} * realized_volatility"
        )
    if family is CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE:
        return (
            f"abs(liquidation_move_bps) >= {parameter_set['liquidation_move_bps']} "
            f"and wait_bars >= {parameter_set['reversal_wait_bars']}"
        )
    if family is CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER:
        return (
            "funding_rate_bps crosses "
            f"{parameter_set['funding_rate_threshold_bps']} over holding_bars="
            f"{parameter_set['holding_bars']}"
        )
    if family is CandidateFamilyId.PERP_BASIS_MARK_INDEX_SPREAD:
        return (
            "abs(mark_index_spread_bps) >= "
            f"{parameter_set['mark_index_spread_bps']} for mean_revert_bars="
            f"{parameter_set['mean_revert_bars']}"
        )
    if family is CandidateFamilyId.PERP_VOLATILITY_BREAKOUT_COMPRESSION:
        return (
            f"compression_lookback={parameter_set['compression_lookback']} "
            f"and expansion_z >= {parameter_set['expansion_z']}"
        )
    if family is CandidateFamilyId.PERP_LIQUIDITY_SPREAD_FILTER:
        return (
            f"spread_bps <= {parameter_set['spread_limit_bps']} and "
            f"depth_imbalance <= {parameter_set['depth_imbalance_limit']}"
        )
    if family is CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE:
        return (
            f"open_interest_change_pct >= {parameter_set['oi_change_threshold_pct']} "
            f"and liquidation_pressure_bps >= {parameter_set['liquidation_pressure_bps']}"
        )
    raise StrategyIdeaCandidateGeneratorError(f"unsupported standalone family: {family.value}")


def _title(family: CandidateFamilyId, instruments: list[str]) -> str:
    instrument_label = ",".join(instruments)
    return {
        CandidateFamilyId.TREND_MOMENTUM: f"{instrument_label} trend momentum candidate",
        CandidateFamilyId.VOLATILITY_REGIME: f"{instrument_label} volatility regime candidate",
        CandidateFamilyId.LIQUIDITY_SPREAD: f"{instrument_label} liquidity spread candidate",
        CandidateFamilyId.CROSS_SECTIONAL_RANK: (
            f"{instrument_label} cross sectional rank candidate"
        ),
        CandidateFamilyId.MEAN_REVERSION: f"{instrument_label} mean reversion candidate",
        CandidateFamilyId.PERP_MOMENTUM_CONTINUATION: (
            f"{instrument_label} perp momentum continuation candidate"
        ),
        CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE: (
            f"{instrument_label} perp reversal after liquidation move candidate"
        ),
        CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER: (
            f"{instrument_label} perp funding-rate carry/filter candidate"
        ),
        CandidateFamilyId.PERP_BASIS_MARK_INDEX_SPREAD: (
            f"{instrument_label} perp basis mark-index spread candidate"
        ),
        CandidateFamilyId.PERP_VOLATILITY_BREAKOUT_COMPRESSION: (
            f"{instrument_label} perp volatility breakout/compression candidate"
        ),
        CandidateFamilyId.PERP_LIQUIDITY_SPREAD_FILTER: (
            f"{instrument_label} perp liquidity/spread filter candidate"
        ),
        CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE: (
            f"{instrument_label} perp open-interest liquidation-pressure placeholder"
        ),
    }[family]


def _hypothesis_template(family: CandidateFamilyId) -> str:
    return {
        CandidateFamilyId.TREND_MOMENTUM: (
            "Trend and momentum continuation may persist over the configured horizon."
        ),
        CandidateFamilyId.VOLATILITY_REGIME: (
            "Volatility regime state may condition next-window return distribution."
        ),
        CandidateFamilyId.LIQUIDITY_SPREAD: (
            "Liquidity and spread constraints may filter unreliable strategy windows."
        ),
        CandidateFamilyId.CROSS_SECTIONAL_RANK: (
            "Cross-sectional rank may identify relative continuation candidates."
        ),
        CandidateFamilyId.MEAN_REVERSION: (
            "Overextension may partially revert over the configured horizon."
        ),
        CandidateFamilyId.PERP_MOMENTUM_CONTINUATION: (
            "Perp momentum may continue when mark/index behavior confirms the move after costs."
        ),
        CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE: (
            "Large liquidation-driven moves may mean-revert after a fixed waiting period."
        ),
        CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER: (
            "Funding-rate state may filter or carry directional perp exposure after costs."
        ),
        CandidateFamilyId.PERP_BASIS_MARK_INDEX_SPREAD: (
            "Mark-index basis dislocation may identify short-horizon mean reversion candidates."
        ),
        CandidateFamilyId.PERP_VOLATILITY_BREAKOUT_COMPRESSION: (
            "Compression followed by expansion may support a short-horizon perp breakout."
        ),
        CandidateFamilyId.PERP_LIQUIDITY_SPREAD_FILTER: (
            "Spread and depth constraints may reject poor execution windows before selection."
        ),
        CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE: (
            "Open-interest and liquidation pressure may be a placeholder filter for perp stress."
        ),
    }[family]


def _feature_columns(family: CandidateFamilyId) -> list[str]:
    return {
        CandidateFamilyId.TREND_MOMENTUM: ["close", "realized_volatility"],
        CandidateFamilyId.VOLATILITY_REGIME: ["close", "realized_volatility"],
        CandidateFamilyId.LIQUIDITY_SPREAD: ["bid", "ask", "spread_bps"],
        CandidateFamilyId.CROSS_SECTIONAL_RANK: ["close", "universe_member_id"],
        CandidateFamilyId.MEAN_REVERSION: ["close", "zscore"],
        CandidateFamilyId.PERP_MOMENTUM_CONTINUATION: [
            "mark_price",
            "index_price",
            "realized_volatility",
        ],
        CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE: [
            "liquidation_notional",
            "mark_price",
            "index_price",
        ],
        CandidateFamilyId.PERP_FUNDING_RATE_CARRY_FILTER: [
            "funding_rate",
            "mark_price",
            "index_price",
        ],
        CandidateFamilyId.PERP_BASIS_MARK_INDEX_SPREAD: [
            "mark_price",
            "index_price",
            "basis_bps",
        ],
        CandidateFamilyId.PERP_VOLATILITY_BREAKOUT_COMPRESSION: [
            "mark_price",
            "realized_volatility",
            "spread_bps",
        ],
        CandidateFamilyId.PERP_LIQUIDITY_SPREAD_FILTER: [
            "spread_bps",
            "book_depth",
            "depth_imbalance",
        ],
        CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE: [
            "open_interest",
            "liquidation_notional",
            "funding_rate",
        ],
    }[family]


PERP_REQUIRED_PARAMETER_FIELDS = (
    "side_bias",
    "venue",
    "product_type",
    "margin_mode",
    "margin_coin",
    "leverage",
    "funding_assumption",
    "fee_model_ref",
    "slippage_model_ref",
    "liquidation_buffer_bps",
    "max_position_notional_usd",
    "max_daily_loss_usd",
    "kill_conditions",
)

PERP_C9_V0_SOURCE_BLOCKED_FAMILY_REASONS = {
    CandidateFamilyId.PERP_REVERSAL_AFTER_LIQUIDATION_MOVE: (
        "family requires liquidation_notional source not available in current C9 v0 public source"
    ),
    CandidateFamilyId.PERP_OPEN_INTEREST_LIQUIDATION_PRESSURE: (
        "family requires open_interest and liquidation_notional sources not available in "
        "current C9 v0 public source"
    ),
}


def _perp_parameter_set(side_bias: str, **overrides: Any) -> dict[str, Any]:
    parameter_set: dict[str, Any] = {
        "side_bias": side_bias,
        "venue": "bitget",
        "product_type": "USDT-FUTURES",
        "margin_mode": "isolated",
        "margin_coin": "USDT",
        "leverage": 3,
        "funding_assumption": "funding paid or received during hold is modeled",
        "fee_model_ref": "bitget_usdt_futures_taker_fee_estimate",
        "slippage_model_ref": "bps_stress_model",
        "liquidation_buffer_bps": 2500,
        "max_position_notional_usd": 100,
        "max_daily_loss_usd": 25,
        "kill_conditions": ["spread_bps_gt_15", "funding_missing", "source_gap"],
    }
    parameter_set.update(overrides)
    return parameter_set


def _perp_shortlist_rejection_reason(
    *,
    profile: StrategyIdeaCandidateProfile,
    family: CandidateFamilyId,
    parameter_set: dict[str, Any],
) -> str | None:
    if profile is not StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER:
        return None
    missing = [
        field
        for field in PERP_REQUIRED_PARAMETER_FIELDS
        if parameter_set.get(field) in (None, "", [])
    ]
    failures: list[str] = []
    source_gap = PERP_C9_V0_SOURCE_BLOCKED_FAMILY_REASONS.get(family)
    if source_gap is not None:
        failures.append(source_gap)
    if missing:
        failures.append("missing " + ", ".join(missing))
    side_bias = str(parameter_set.get("side_bias") or "").lower()
    if side_bias and side_bias not in {"long", "short"}:
        failures.append("side_bias must be long or short for C9 v0 directional authoring bridge")
    if parameter_set.get("venue") != "bitget":
        failures.append("venue must be bitget")
    if parameter_set.get("product_type") != "USDT-FUTURES":
        failures.append("product_type must be USDT-FUTURES")
    if parameter_set.get("margin_mode") != "isolated":
        failures.append("margin_mode must be isolated")
    if parameter_set.get("margin_coin") != "USDT":
        failures.append("margin_coin must be USDT")
    leverage = parameter_set.get("leverage")
    if not isinstance(leverage, int | float) or leverage <= 0 or leverage > 3:
        failures.append("leverage must be between 1 and 3")
    liquidation_buffer = parameter_set.get("liquidation_buffer_bps")
    if not isinstance(liquidation_buffer, int | float) or liquidation_buffer <= 0:
        failures.append("liquidation_buffer_bps must be positive")
    if failures:
        return "perp shortlist constraints failed: " + "; ".join(failures)
    return None


def _raw_validation_metrics(
    *,
    config: StrategyIdeaCandidateGeneratorConfig,
    parameter_set: dict[str, Any],
) -> dict[str, Any]:
    if config.profile is not StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER:
        return {}
    return {
        "metric_basis": "raw_only_not_profit_proof",
        "selection_adjusted_metrics": "NOT_ESTIMABLE",
        "fee_model_ref": parameter_set.get("fee_model_ref"),
        "funding_assumption": parameter_set.get("funding_assumption"),
        "slippage_model_ref": parameter_set.get("slippage_model_ref"),
        "liquidation_buffer_bps": parameter_set.get("liquidation_buffer_bps"),
        "leverage_modeling_cap": 3,
    }


def _canonicalize_parameter_set(parameter_set: dict[str, Any]) -> dict[str, Any]:
    return json.loads(_canonical_json(parameter_set))


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _coerce_optional_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
