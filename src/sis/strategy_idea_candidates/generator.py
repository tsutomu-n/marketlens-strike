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
from sis.strategy_idea_candidates.service import (
    build_blocked_candidate_set_from_input_evidence,
)
from sis.strategy_inputs.models import (
    InputValidationStatus,
    ProducerInfo,
    SourceValidationStatus,
    StrategyInputContract,
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


class StrategyIdeaCandidateGeneratorError(ValueError):
    pass


class StrategyIdeaCandidateGeneratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_set_id: str
    generator_version: str = GENERATOR_VERSION
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
    }


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
                "selection-adjusted metrics are NOT_IMPLEMENTED",
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
        raw_validation_metrics={},
        selection_adjusted_metrics_status=SelectionAdjustedMetricsStatus.NOT_IMPLEMENTED,
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
    }[family]


def _feature_columns(family: CandidateFamilyId) -> list[str]:
    return {
        CandidateFamilyId.TREND_MOMENTUM: ["close", "realized_volatility"],
        CandidateFamilyId.VOLATILITY_REGIME: ["close", "realized_volatility"],
        CandidateFamilyId.LIQUIDITY_SPREAD: ["bid", "ask", "spread_bps"],
        CandidateFamilyId.CROSS_SECTIONAL_RANK: ["close", "universe_member_id"],
        CandidateFamilyId.MEAN_REVERSION: ["close", "zscore"],
    }[family]


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
