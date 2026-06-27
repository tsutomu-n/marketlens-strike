from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import (
    CandidateDecision,
    CandidateExportManifest,
    CandidateExportedIdea,
    CandidateSetStatus,
    StrategyIdeaCandidateSet,
)
from sis.strategy_inputs.io import write_json_artifact
from sis.strategy_inputs.models import (
    AuthoringIntent,
    BaselineSpec,
    ExecutionAssumptions,
    ProducerInfo,
    RiskSpec,
    StrategyIdea,
    StrategyInputBoundary,
)
from sis.strategy_review.provenance import repo_relative_path


@dataclass(frozen=True)
class StrategyIdeaCandidateExportResult:
    manifest: CandidateExportManifest
    manifest_path: Path
    idea_paths: list[Path]
    manifest_sha256: str


class StrategyIdeaCandidateExportError(ValueError):
    pass


class StrategyIdeaCandidateExportOutputExistsError(StrategyIdeaCandidateExportError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return _utc_now()
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _strategy_idea_from_candidate(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    idea_candidate_id: str,
    created_at: datetime,
) -> StrategyIdea:
    candidate = next(
        item for item in candidate_set.candidate_inventory if item.idea_candidate_id == idea_candidate_id
    )
    return StrategyIdea(
        idea_id=candidate.idea_candidate_id,
        created_at=created_at,
        title=f"UNVERIFIED_CANDIDATE: {candidate.title}",
        hypothesis=candidate.hypothesis_template,
        mechanism=f"{candidate.family}: {candidate.signal_expression}",
        timeframe=candidate.timeframe,
        instruments=candidate.instruments,
        required_input_contract_ids=[
            ref.contract_id for ref in candidate_set.input_contract_validation_refs
        ],
        baseline=BaselineSpec(name="cash_or_no_trade", expected_to_beat=True),
        invalidation=[
            "Reject if guarded validation fails to beat cash_or_no_trade after leakage checks.",
            "Reject if source evidence or available-at policy cannot be reproduced.",
        ],
        risk=RiskSpec(
            max_position_notional_usd=1.0,
            max_daily_loss_usd=1.0,
            kill_conditions=[
                "Do not trade; draft requires human risk specification before paper or live use."
            ],
        ),
        execution_assumptions=ExecutionAssumptions(
            order_type="not_for_execution_research_draft",
            slippage_model="not_modeled_candidate_export",
        ),
        authoring_intent=AuthoringIntent(
            target="strategy_authoring_draft",
            auto_generate_spec=False,
        ),
        boundary=StrategyInputBoundary(),
    )


def export_shortlisted_strategy_ideas(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    candidate_set_path: Path,
    out_dir: Path,
    replace_existing: bool = False,
    created_at: datetime | str | None = None,
) -> StrategyIdeaCandidateExportResult:
    if candidate_set.candidate_set_status is not CandidateSetStatus.BUILT:
        raise StrategyIdeaCandidateExportError("only BUILT candidate sets can be exported")
    shortlisted_ids = [
        candidate.idea_candidate_id
        for candidate in candidate_set.candidate_inventory
        if candidate.decision is CandidateDecision.SHORTLISTED
    ]
    if not shortlisted_ids:
        raise StrategyIdeaCandidateExportError("no shortlisted candidates to export")

    manifest_path = out_dir / "strategy_idea_candidate_export_manifest.json"
    idea_paths = [out_dir / f"{candidate_id}.strategy_idea.json" for candidate_id in shortlisted_ids]
    if not replace_existing and (
        manifest_path.exists() or any(path.exists() for path in idea_paths)
    ):
        raise StrategyIdeaCandidateExportOutputExistsError(f"output already exists: {out_dir}")

    timestamp = _coerce_datetime(created_at)
    exported: list[CandidateExportedIdea] = []
    for idea_path, candidate_id in zip(idea_paths, shortlisted_ids, strict=True):
        idea = _strategy_idea_from_candidate(
            candidate_set=candidate_set,
            idea_candidate_id=candidate_id,
            created_at=timestamp,
        )
        write_json_artifact(idea_path, idea.model_dump(mode="json", exclude_none=True))
        exported.append(
            CandidateExportedIdea(
                idea_candidate_id=candidate_id,
                strategy_idea_path=repo_relative_path(idea_path),
                strategy_idea_sha256=sha256_file(idea_path),
                export_decision=CandidateDecision.SHORTLISTED.value,
            )
        )

    manifest = CandidateExportManifest(
        manifest_id=f"{candidate_set.candidate_set_id}-export",
        created_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidate-export"),
        candidate_set_id=candidate_set.candidate_set_id,
        candidate_set_path=repo_relative_path(candidate_set_path),
        candidate_set_sha256=sha256_file(candidate_set_path),
        exported_ideas=exported,
    )
    write_json_artifact(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
    return StrategyIdeaCandidateExportResult(
        manifest=manifest,
        manifest_path=manifest_path,
        idea_paths=idea_paths,
        manifest_sha256=sha256_file(manifest_path),
    )
