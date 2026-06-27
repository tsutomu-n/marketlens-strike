from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import (
    CandidateSetStatus,
    CandidateSourceArtifact,
    InputContractValidationRef,
    LeakagePolicy,
    SearchLedgerSummary,
    SelectionPolicy,
    SplitPolicy,
    StrategyIdeaCandidateSet,
    TimeWindow,
)
from sis.strategy_idea_candidates.rendering import render_strategy_idea_candidate_set_markdown
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import (
    InputValidationStatus,
    ProducerInfo,
    SourceValidationStatus,
    StrategyInputContract,
    StrategyInputContractValidation,
)
from sis.strategy_review.provenance import repo_relative_path


ZERO_HASH = "sha256:" + "0" * 64


@dataclass(frozen=True)
class StrategyIdeaCandidateSetWriteResult:
    candidate_set: StrategyIdeaCandidateSet
    candidate_set_path: Path
    report_path: Path
    candidate_set_sha256: str


class StrategyIdeaCandidateSetError(ValueError):
    pass


class StrategyIdeaCandidateSetOutputExistsError(StrategyIdeaCandidateSetError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _same_time_window(value: datetime) -> TimeWindow:
    return TimeWindow(start=value, end=value)


def _coerce_optional_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def write_strategy_idea_candidate_set(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateSetWriteResult:
    candidate_set_path = out_dir / "strategy_idea_candidate_set.json"
    report_path = out_dir / "strategy_idea_candidate_set.md"
    if not replace_existing and (candidate_set_path.exists() or report_path.exists()):
        raise StrategyIdeaCandidateSetOutputExistsError(f"output already exists: {out_dir}")

    write_json_artifact(
        candidate_set_path,
        candidate_set.model_dump(mode="json", exclude_none=True),
    )
    write_text_artifact(report_path, render_strategy_idea_candidate_set_markdown(candidate_set))
    return StrategyIdeaCandidateSetWriteResult(
        candidate_set=candidate_set,
        candidate_set_path=candidate_set_path,
        report_path=report_path,
        candidate_set_sha256=sha256_file(candidate_set_path),
    )


def build_blocked_candidate_set_from_input_evidence(
    *,
    candidate_set_id: str,
    contract: StrategyInputContract,
    validation: StrategyInputContractValidation,
    validation_path: Path,
    generator_version: str,
    generated_at: datetime | str | None = None,
    dependency_versions: dict[str, str] | None = None,
) -> StrategyIdeaCandidateSet:
    if validation.validation_status is InputValidationStatus.PASS:
        raise StrategyIdeaCandidateSetError("blocked candidate set requires non-PASS validation")
    validation_by_source = {result.source_id: result for result in validation.source_results}
    source_artifacts: list[CandidateSourceArtifact] = []
    for source in contract.sources:
        result = validation_by_source.get(source.source_id)
        source_artifacts.append(
            CandidateSourceArtifact(
                source_id=source.source_id,
                path=source.path,
                sha256=(
                    (result.actual_sha256 if result is not None else None)
                    or source.declared_sha256
                    or ZERO_HASH
                ),
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

    timestamp = generated_at or _utc_now()
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return StrategyIdeaCandidateSet(
        candidate_set_id=candidate_set_id,
        generated_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidates-build"),
        generator_version=generator_version,
        candidate_set_status=CandidateSetStatus.BLOCKED_INPUT_EVIDENCE,
        input_contract_validation_refs=[
            InputContractValidationRef(
                contract_id=validation.contract_id,
                validation_path=repo_relative_path(validation_path),
                validation_sha256=sha256_file(validation_path),
                validation_status=validation.validation_status,
            )
        ],
        source_artifacts=source_artifacts,
        candidate_inventory=[],
        search_ledger_summary=SearchLedgerSummary(
            family_count=0,
            candidate_count_total=0,
            candidate_count_shortlisted=0,
            candidate_count_rejected=0,
            trial_count_total=0,
            parameter_grid_hash=ZERO_HASH,
            validation_peek_count=0,
            rerank_count=0,
            duplicate_rejection_count=0,
        ),
        selection_policy=SelectionPolicy(
            policy_id="blocked-input-evidence",
            description="Candidate generation blocked because input validation did not PASS.",
            shortlisted_candidate_ids=[],
            rejected_candidate_ids=[],
            known_gaps=[f"input validation status: {validation.validation_status.value}"],
        ),
        split_policy=SplitPolicy(
            split_method="blocked_input_evidence_no_split",
            train_window=_same_time_window(validation.validated_at),
            validation_window=_same_time_window(validation.validated_at),
            sealed_test_window=None,
            uses_sealed_test_for_selection=False,
        ),
        leakage_policy=LeakagePolicy(
            feature_available_at_policy="not evaluated because input evidence did not PASS",
            purge_policy="not_evaluated:blocked_input_evidence",
            embargo_policy="not_evaluated:blocked_input_evidence",
            uses_sealed_test_for_selection=False,
        ),
        dependency_versions=dependency_versions or {"sis": "local"},
    )
