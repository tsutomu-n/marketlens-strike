from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import CandidateBoundary, StrategyIdeaCandidateSet
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo


SPLIT_MATERIALIZATION_SCHEMA_VERSION = "strategy_idea_candidate_split_materialization.v1"


class CandidateSplitMaterializationRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    decision: str
    family: str
    train_window: dict[str, Any]
    validation_window: dict[str, Any]
    sealed_test_window: dict[str, Any] | None
    label_window: dict[str, Any]
    feature_observation_window: dict[str, Any]
    uses_sealed_test_for_selection: Literal[False] = False
    purge_policy: str
    embargo_policy: str


class StrategyIdeaCandidateSplitMaterialization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_split_materialization.v1"] = (
        SPLIT_MATERIALIZATION_SCHEMA_VERSION
    )
    materialization_id: str
    generated_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    split_method: str
    uses_sealed_test_for_selection: Literal[False] = False
    rows: list[CandidateSplitMaterializationRow]
    summary: dict[str, Any]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return _serialize_datetime(value)


@dataclass(frozen=True)
class StrategyIdeaCandidateSplitMaterializationWriteResult:
    materialization: StrategyIdeaCandidateSplitMaterialization
    materialization_path: Path
    markdown_path: Path
    materialization_sha256: str


class StrategyIdeaCandidateSplitMaterializationOutputExistsError(ValueError):
    pass


def materialize_candidate_splits(
    candidate_set: StrategyIdeaCandidateSet,
    *,
    generated_at: datetime | str | None = None,
) -> StrategyIdeaCandidateSplitMaterialization:
    timestamp = _coerce_datetime(generated_at)
    split = candidate_set.split_policy
    leakage = candidate_set.leakage_policy
    rows = [
        CandidateSplitMaterializationRow(
            candidate_id=candidate.idea_candidate_id,
            decision=candidate.decision.value,
            family=candidate.family,
            train_window=split.train_window.model_dump(mode="json"),
            validation_window=split.validation_window.model_dump(mode="json"),
            sealed_test_window=split.sealed_test_window.model_dump(mode="json")
            if split.sealed_test_window is not None
            else None,
            label_window=candidate.label_window.model_dump(mode="json"),
            feature_observation_window=candidate.feature_observation_window.model_dump(
                mode="json"
            ),
            uses_sealed_test_for_selection=False,
            purge_policy=leakage.purge_policy,
            embargo_policy=leakage.embargo_policy,
        )
        for candidate in candidate_set.candidate_inventory
    ]
    known_gaps: list[str] = []
    if "policy_record_only" in leakage.purge_policy:
        known_gaps.append("PURGE_POLICY_RECORDED_NOT_EXECUTED")
    if "policy_record_only" in leakage.embargo_policy:
        known_gaps.append("EMBARGO_POLICY_RECORDED_NOT_EXECUTED")
    summary = {
        "candidate_count": len(rows),
        "split_method": split.split_method,
        "has_sealed_test_window": split.sealed_test_window is not None,
        "uses_sealed_test_for_selection": False,
        "known_gap_count": len(known_gaps),
    }
    return StrategyIdeaCandidateSplitMaterialization(
        materialization_id=f"{candidate_set.candidate_set_id}-split-materialization",
        generated_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidates-split-materialization"),
        candidate_set_id=candidate_set.candidate_set_id,
        split_method=split.split_method,
        uses_sealed_test_for_selection=False,
        rows=rows,
        summary=summary,
        known_gaps=known_gaps,
    )


def write_strategy_idea_candidate_split_materialization(
    *,
    materialization: StrategyIdeaCandidateSplitMaterialization,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateSplitMaterializationWriteResult:
    materialization_path = out_dir / "split_materialization.json"
    markdown_path = out_dir / "split_materialization.md"
    if not replace_existing and (materialization_path.exists() or markdown_path.exists()):
        raise StrategyIdeaCandidateSplitMaterializationOutputExistsError(
            f"output already exists: {out_dir}"
        )
    write_json_artifact(
        materialization_path,
        materialization.model_dump(mode="json", exclude_none=True),
    )
    write_text_artifact(markdown_path, render_split_materialization_markdown(materialization))
    return StrategyIdeaCandidateSplitMaterializationWriteResult(
        materialization=materialization,
        materialization_path=materialization_path,
        markdown_path=markdown_path,
        materialization_sha256=sha256_file(materialization_path),
    )


def render_split_materialization_markdown(
    materialization: StrategyIdeaCandidateSplitMaterialization,
) -> str:
    lines = [
        f"# Split Materialization: {materialization.candidate_set_id}",
        "",
        f"- split_method: `{materialization.split_method}`",
        "- uses_sealed_test_for_selection: `false`",
        "- permits_live_order: `false`",
        "",
        "## Rows",
        "",
        "| candidate_id | decision | family | purge_policy | embargo_policy |",
        "|---|---|---|---|---|",
    ]
    for row in materialization.rows:
        lines.append(
            "| "
            f"`{row.candidate_id}` | "
            f"`{row.decision}` | "
            f"`{row.family}` | "
            f"`{row.purge_policy}` | "
            f"`{row.embargo_policy}` |"
        )
    if materialization.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in materialization.known_gaps)
    return "\n".join(lines) + "\n"


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
