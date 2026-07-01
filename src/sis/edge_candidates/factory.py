from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import product
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import sha256_file
from sis.edge_candidates import EDGE_CANDIDATE_FACTORY_SUMMARY_SCHEMA_VERSION
from sis.edge_candidates.protocol import (
    CandidateGeneratorType,
    CandidateProtocolManifest,
    CandidateProtocolMode,
)
from sis.strategy_idea_candidates.generator import (
    CandidateFamilyId,
    StrategyIdeaCandidateGeneratorConfig,
    StrategyIdeaCandidateProfile,
    build_deterministic_candidate_set_from_input_evidence,
)
from sis.strategy_idea_candidates.ledger import (
    parameter_set_hash,
    write_strategy_idea_candidate_search_ledger,
)
from sis.strategy_idea_candidates.models import (
    CandidateDecision,
    StrategyIdeaCandidate,
    StrategyIdeaCandidateSet,
    TimeWindow,
)
from sis.strategy_idea_candidates.profit_core import (
    write_trial_multiplicity_account_from_candidate_set,
)
from sis.strategy_idea_candidates.service import (
    write_strategy_idea_candidate_set,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import (
    ProducerInfo,
    StrategyInputContract,
    StrategyInputContractValidation,
)


SUPPORTED_P4_GENERATOR_TYPES = {
    CandidateGeneratorType.CLASSICAL_RULE,
    CandidateGeneratorType.GRAMMAR_BASED,
}


@dataclass(frozen=True)
class EdgeCandidateFactoryResult:
    candidate_set: StrategyIdeaCandidateSet
    candidate_set_path: Path
    report_path: Path
    search_ledger_path: Path
    rejection_ledger_path: Path
    multiplicity_account_path: Path
    summary_path: Path
    summary: dict[str, Any]


class EdgeCandidateFactoryError(ValueError):
    pass


class EdgeCandidateFactoryOutputExistsError(EdgeCandidateFactoryError):
    pass


def run_edge_candidate_factory(
    *,
    protocol_path: Path,
    contract_path: Path,
    validation_path: Path,
    out_dir: Path,
    candidate_set_id: str | None = None,
    shortlist_count: int = 1,
    replace_existing: bool = False,
) -> EdgeCandidateFactoryResult:
    protocol = CandidateProtocolManifest.model_validate(read_mapping_file(protocol_path))
    contract = StrategyInputContract.model_validate(read_mapping_file(contract_path))
    validation = StrategyInputContractValidation.model_validate(read_mapping_file(validation_path))

    _validate_p4_protocol(protocol)
    family_ids = _family_ids_from_protocol(protocol)
    parameter_grids = _parameter_grids_from_protocol(protocol)
    _validate_parameter_grids_cover_families(
        family_ids=family_ids,
        parameter_grids=parameter_grids,
    )
    _ensure_outputs_can_be_written(out_dir=out_dir, replace_existing=replace_existing)

    config = _config_from_protocol(
        protocol=protocol,
        contract=contract,
        validation=validation,
        family_ids=family_ids,
        parameter_grids=parameter_grids,
        candidate_set_id=candidate_set_id,
        shortlist_count=shortlist_count,
    )
    candidate_set = build_deterministic_candidate_set_from_input_evidence(
        contract=contract,
        validation=validation,
        validation_path=validation_path,
        config=config,
    ).model_copy(update={"producer": ProducerInfo(command="edge-candidate-factory-run")})

    candidate_write = write_strategy_idea_candidate_set(
        candidate_set=candidate_set,
        out_dir=out_dir,
        replace_existing=replace_existing,
    )
    ledger_write = write_strategy_idea_candidate_search_ledger(
        candidate_set=candidate_set,
        out_dir=out_dir,
        source_kind="edge_candidate_factory",
        replace_existing=replace_existing,
    )
    rejection_ledger_path = write_rejection_ledger(
        candidate_set=candidate_set,
        out_dir=out_dir,
        replace_existing=replace_existing,
    )
    multiplicity = write_trial_multiplicity_account_from_candidate_set(
        candidate_set=candidate_set,
        ledger_path=ledger_write.ledger_path,
        protocol_manifest_path=protocol_path,
        out_dir=out_dir,
        replace_existing=replace_existing,
    )
    summary = build_edge_candidate_factory_summary(
        protocol=protocol,
        protocol_path=protocol_path,
        contract_path=contract_path,
        validation_path=validation_path,
        candidate_set=candidate_set,
        candidate_set_path=candidate_write.candidate_set_path,
        search_ledger_path=ledger_write.ledger_path,
        rejection_ledger_path=rejection_ledger_path,
        multiplicity_account_path=multiplicity.account_path,
    )
    summary_path = out_dir / "edge_candidate_factory_summary.json"
    write_json_artifact(summary_path, summary)
    return EdgeCandidateFactoryResult(
        candidate_set=candidate_set,
        candidate_set_path=candidate_write.candidate_set_path,
        report_path=candidate_write.report_path,
        search_ledger_path=ledger_write.ledger_path,
        rejection_ledger_path=rejection_ledger_path,
        multiplicity_account_path=multiplicity.account_path,
        summary_path=summary_path,
        summary=summary,
    )


def write_rejection_ledger(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    out_dir: Path,
    replace_existing: bool = False,
) -> Path:
    path = out_dir / "rejection_ledger.jsonl"
    if path.exists() and not replace_existing:
        raise EdgeCandidateFactoryOutputExistsError(f"output already exists: {path}")
    rows = [
        _rejection_ledger_row(candidate)
        for candidate in candidate_set.candidate_inventory
        if candidate.decision is CandidateDecision.REJECTED
    ]
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if rows:
        text += "\n"
    write_text_artifact(path, text)
    return path


def build_edge_candidate_factory_summary(
    *,
    protocol: CandidateProtocolManifest,
    protocol_path: Path,
    contract_path: Path,
    validation_path: Path,
    candidate_set: StrategyIdeaCandidateSet,
    candidate_set_path: Path,
    search_ledger_path: Path,
    rejection_ledger_path: Path,
    multiplicity_account_path: Path,
) -> dict[str, Any]:
    summary = candidate_set.search_ledger_summary
    rejection_rows = [
        _rejection_ledger_row(candidate)
        for candidate in candidate_set.candidate_inventory
        if candidate.decision is CandidateDecision.REJECTED
    ]
    unexecutable_reason_count = sum(1 for row in rejection_rows if row["unexecutable_reasons"])
    candidate_count_total = summary.candidate_count_total
    unexecutable_rate = (
        round(unexecutable_reason_count / candidate_count_total, 10)
        if candidate_count_total
        else 0.0
    )
    return {
        "schema_version": EDGE_CANDIDATE_FACTORY_SUMMARY_SCHEMA_VERSION,
        "protocol_ref": {
            "protocol_id": protocol.protocol_id,
            "mode": protocol.mode.value,
            "path": protocol_path.as_posix(),
            "sha256": sha256_file(protocol_path),
        },
        "input_evidence_refs": {
            "contract_path": contract_path.as_posix(),
            "contract_sha256": sha256_file(contract_path),
            "validation_path": validation_path.as_posix(),
            "validation_sha256": sha256_file(validation_path),
            "source_requirements": [
                requirement.model_dump(mode="json") for requirement in protocol.source_requirements
            ],
        },
        "artifact_refs": {
            "candidate_set_path": candidate_set_path.as_posix(),
            "candidate_set_sha256": sha256_file(candidate_set_path),
            "search_ledger_path": search_ledger_path.as_posix(),
            "search_ledger_sha256": sha256_file(search_ledger_path),
            "rejection_ledger_path": rejection_ledger_path.as_posix(),
            "rejection_ledger_sha256": sha256_file(rejection_ledger_path),
            "multiplicity_account_path": multiplicity_account_path.as_posix(),
            "multiplicity_account_sha256": sha256_file(multiplicity_account_path),
        },
        "family_ids": [family.family_id for family in protocol.families],
        "family_count": summary.family_count,
        "candidate_count_total": candidate_count_total,
        "candidate_count_shortlisted": summary.candidate_count_shortlisted,
        "candidate_count_rejected": summary.candidate_count_rejected,
        "trial_count_total": summary.trial_count_total,
        "best_only_report": False,
        "success_only_reporting": summary.success_only_reporting,
        "sealed_test_used_for_selection": summary.sealed_test_used_for_selection,
        "unexecutable_reason_count": unexecutable_reason_count,
        "unexecutable_rate": unexecutable_rate,
        "boundary": {
            "actual_cash": False,
            "permits_live_order": False,
            "live_order_submitted": False,
            "production_exchange_write_used": False,
        },
    }


def _validate_p4_protocol(protocol: CandidateProtocolManifest) -> None:
    if protocol.mode is CandidateProtocolMode.RISK_TAKER_SPRINT:
        raise EdgeCandidateFactoryError(
            "risk_taker_sprint factory is disabled in P4; use verification_throughput"
        )
    if protocol.mode is not CandidateProtocolMode.VERIFICATION_THROUGHPUT:
        raise EdgeCandidateFactoryError(f"unsupported protocol mode: {protocol.mode.value}")
    for family in protocol.families:
        if family.generator_type not in SUPPORTED_P4_GENERATOR_TYPES:
            raise EdgeCandidateFactoryError(
                "unsupported generator_type for P4 Edge Candidate Factory: "
                f"{family.family_id}={family.generator_type.value}"
            )


def _family_ids_from_protocol(protocol: CandidateProtocolManifest) -> list[CandidateFamilyId]:
    family_ids: list[CandidateFamilyId] = []
    seen: set[str] = set()
    for family in protocol.families:
        if family.family_id in seen:
            raise EdgeCandidateFactoryError(f"duplicate protocol family: {family.family_id}")
        seen.add(family.family_id)
        try:
            family_ids.append(CandidateFamilyId(family.family_id))
        except ValueError as exc:
            raise EdgeCandidateFactoryError(
                f"unsupported candidate family for local generator: {family.family_id}"
            ) from exc
    return family_ids


def _parameter_grids_from_protocol(
    protocol: CandidateProtocolManifest,
) -> dict[str, list[dict[str, Any]]]:
    family_ids = {family.family_id for family in protocol.families}
    extra_spaces = sorted(set(protocol.parameter_spaces) - family_ids)
    if extra_spaces:
        raise EdgeCandidateFactoryError(
            "parameter_spaces include families not declared in protocol: " + ", ".join(extra_spaces)
        )
    return {
        family_id: _expand_parameter_space(family_id, protocol.parameter_spaces[family_id])
        for family_id in sorted(family_ids)
    }


def _expand_parameter_space(
    family_id: str, parameter_space: dict[str, Any]
) -> list[dict[str, Any]]:
    if not parameter_space:
        raise EdgeCandidateFactoryError(f"empty parameter space: {family_id}")
    if "grid" in parameter_space:
        if set(parameter_space) != {"grid"}:
            raise EdgeCandidateFactoryError(
                f"parameter space with grid must not include additional keys: {family_id}"
            )
        raw_grid = parameter_space["grid"]
        if not isinstance(raw_grid, list) or not raw_grid:
            raise EdgeCandidateFactoryError(f"grid must be a non-empty list: {family_id}")
        if not all(isinstance(item, dict) and item for item in raw_grid):
            raise EdgeCandidateFactoryError(f"grid entries must be non-empty mappings: {family_id}")
        return [dict(item) for item in raw_grid]

    keys = sorted(parameter_space)
    values: list[list[Any]] = []
    for key in keys:
        raw_value = parameter_space[key]
        if isinstance(raw_value, list):
            if not raw_value:
                raise EdgeCandidateFactoryError(
                    f"parameter values must not be empty: {family_id}.{key}"
                )
            values.append(raw_value)
        else:
            values.append([raw_value])
    return [dict(zip(keys, combination, strict=True)) for combination in product(*values)]


def _validate_parameter_grids_cover_families(
    *,
    family_ids: list[CandidateFamilyId],
    parameter_grids: dict[str, list[dict[str, Any]]],
) -> None:
    expected = {family.value for family in family_ids}
    actual = set(parameter_grids)
    if expected != actual:
        raise EdgeCandidateFactoryError(
            "parameter grids must exactly match protocol families: "
            f"expected={sorted(expected)} actual={sorted(actual)}"
        )


def _config_from_protocol(
    *,
    protocol: CandidateProtocolManifest,
    contract: StrategyInputContract,
    validation: StrategyInputContractValidation,
    family_ids: list[CandidateFamilyId],
    parameter_grids: dict[str, list[dict[str, Any]]],
    candidate_set_id: str | None,
    shortlist_count: int,
) -> StrategyIdeaCandidateGeneratorConfig:
    max_observed = _max_observed_timestamp(validation)
    generated_at = validation.validated_at
    train_start = max_observed - timedelta(days=365)
    train_end = max_observed - timedelta(days=180)
    validation_start = train_end + timedelta(seconds=1)
    validation_end = max_observed
    sealed_start = protocol.sealed_holdout_definition.start
    if sealed_start <= validation_end:
        sealed_start = validation_end + timedelta(seconds=1)
    profile = _profile_for_families(family_ids=family_ids, protocol=protocol)
    candidate_cap = sum(len(grid) for grid in parameter_grids.values())
    return StrategyIdeaCandidateGeneratorConfig(
        candidate_set_id=candidate_set_id
        or f"{contract.contract_id}-{protocol.protocol_id}-edge-factory",
        profile=profile,
        family_ids=family_ids,
        parameter_grids=parameter_grids,
        candidate_cap=max(candidate_cap, 1),
        shortlist_count=shortlist_count,
        target_definition=str(
            protocol.objective.get("primary") or "next_window_cost_adjusted_return_estimate"
        ),
        prediction_horizon="protocol_bound_verification_window",
        timeframe=contract.strategy_scope.timeframe,
        label_window=TimeWindow(start=validation_end, end=validation_end),
        feature_observation_window=TimeWindow(start=train_start, end=validation_end),
        train_window=TimeWindow(start=train_start, end=train_end),
        validation_window=TimeWindow(start=validation_start, end=validation_end),
        sealed_test_window=TimeWindow(
            start=sealed_start,
            end=protocol.sealed_holdout_definition.end,
        ),
        generated_at=generated_at,
        available_at_policy=(
            "protocol-bound inputs and execution reality fields must be available before "
            "candidate selection"
        ),
        purge_policy="policy_record_only:not_implemented_for_p4_edge_candidate_factory",
        embargo_policy="policy_record_only:not_implemented_for_p4_edge_candidate_factory",
    )


def _profile_for_families(
    *,
    family_ids: list[CandidateFamilyId],
    protocol: CandidateProtocolManifest,
) -> StrategyIdeaCandidateProfile:
    if protocol.target_market == "crypto_perp" or any(
        family.value.startswith("perp_") for family in family_ids
    ):
        return StrategyIdeaCandidateProfile.CRYPTO_PERP_RISK_TAKER
    return StrategyIdeaCandidateProfile.DEFAULT


def _ensure_outputs_can_be_written(*, out_dir: Path, replace_existing: bool) -> None:
    if replace_existing:
        return
    paths = [
        out_dir / "strategy_idea_candidate_set.json",
        out_dir / "strategy_idea_candidate_set.md",
        out_dir / "search_ledger.jsonl",
        out_dir / "rejection_ledger.jsonl",
        out_dir / "trial_multiplicity_account.json",
        out_dir / "edge_candidate_factory_summary.json",
    ]
    existing = [path for path in paths if path.exists()]
    if existing:
        raise EdgeCandidateFactoryOutputExistsError(
            "output already exists: " + ", ".join(path.as_posix() for path in existing)
        )


def _rejection_ledger_row(candidate: StrategyIdeaCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.idea_candidate_id,
        "candidate_status": candidate.candidate_status,
        "family": candidate.family,
        "parameter_set_hash": parameter_set_hash(candidate.parameter_set),
        "decision": candidate.decision.value,
        "rejection_reason": candidate.rejection_reason,
        "unexecutable_reasons": _unexecutable_reasons(candidate),
    }


def _unexecutable_reasons(candidate: StrategyIdeaCandidate) -> list[str]:
    reason = candidate.rejection_reason or ""
    if reason.startswith("missing perp risk modeling fields"):
        return [reason]
    return []


def _max_observed_timestamp(validation: StrategyInputContractValidation) -> datetime:
    observed = [
        result.max_observed_timestamp
        for result in validation.source_results
        if result.max_observed_timestamp is not None
    ]
    if not observed:
        return validation.validated_at - timedelta(days=1)
    values = [
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        for value in observed
    ]
    latest = max(values)
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    return latest.astimezone(timezone.utc)


__all__ = [
    "EdgeCandidateFactoryError",
    "EdgeCandidateFactoryOutputExistsError",
    "EdgeCandidateFactoryResult",
    "build_edge_candidate_factory_summary",
    "run_edge_candidate_factory",
    "write_rejection_ledger",
]
