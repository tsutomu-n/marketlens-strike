from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import (
    CandidateBoundary,
    CandidateExportManifest,
    StrategyIdeaCandidateSet,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo


AUTHORING_PREFLIGHT_SCHEMA_VERSION = "strategy_idea_candidate_authoring_preflight.v1"


class StrategyIdeaCandidateAuthoringPreflight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_authoring_preflight.v1"] = (
        AUTHORING_PREFLIGHT_SCHEMA_VERSION
    )
    preflight_id: str
    generated_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    candidate_results: list[dict[str, Any]]
    summary: dict[str, Any]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return _serialize_datetime(value)


@dataclass(frozen=True)
class StrategyIdeaCandidateAuthoringPreflightWriteResult:
    preflight: StrategyIdeaCandidateAuthoringPreflight
    preflight_path: Path
    markdown_path: Path
    preflight_sha256: str


class StrategyIdeaCandidateAuthoringPreflightOutputExistsError(ValueError):
    pass


def build_strategy_idea_candidate_authoring_preflight(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    export_manifest: CandidateExportManifest | None = None,
    generated_at: datetime | str | None = None,
) -> StrategyIdeaCandidateAuthoringPreflight:
    timestamp = _coerce_datetime(generated_at)
    export_by_candidate_id = {
        item.idea_candidate_id: item for item in (export_manifest.exported_ideas if export_manifest else [])
    }
    candidate_results: list[dict[str, Any]] = []
    for candidate in candidate_set.candidate_inventory:
        export = export_by_candidate_id.get(candidate.idea_candidate_id)
        shortlisted = candidate.decision.value == "SHORTLISTED"
        blockers = [
            "STRATEGY_AUTHORING_SPEC_NOT_GENERATED",
            "BACKTEST_FEATURE_MAPPING_NOT_VALIDATED",
            "PAPER_AND_LIVE_PERMISSION_NOT_GRANTED",
        ]
        if candidate.selection_adjusted_metrics_status.value != "AVAILABLE":
            blockers.append("SELECTION_ADJUSTED_METRICS_NOT_AVAILABLE")
        candidate_results.append(
            {
                "candidate_id": candidate.idea_candidate_id,
                "decision": candidate.decision.value,
                "strategy_idea_v1_export_possible": shortlisted,
                "strategy_idea_v1_export_written": export is not None,
                "strategy_idea_path": export.strategy_idea_path if export is not None else None,
                "strategy_authoring_spec_ready": False,
                "backtest_ready": False,
                "paper_ready": False,
                "live_ready": False,
                "blocking_gaps": blockers,
            }
        )
    summary = {
        "candidate_count_total": len(candidate_results),
        "strategy_idea_v1_export_written_count": sum(
            1 for item in candidate_results if item["strategy_idea_v1_export_written"]
        ),
        "strategy_authoring_spec_ready_count": 0,
        "backtest_ready_count": 0,
        "paper_ready_count": 0,
        "live_ready_count": 0,
    }
    known_gaps = [
        "STRATEGY_AUTHORING_SPEC_NOT_GENERATED",
        "BACKTEST_NOT_RUN",
        "PAPER_AND_LIVE_PERMISSION_NOT_GRANTED",
    ]
    return StrategyIdeaCandidateAuthoringPreflight(
        preflight_id=f"{candidate_set.candidate_set_id}-authoring-preflight",
        generated_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidates-authoring-preflight"),
        candidate_set_id=candidate_set.candidate_set_id,
        candidate_results=candidate_results,
        summary=summary,
        known_gaps=known_gaps,
    )


def write_strategy_idea_candidate_authoring_preflight(
    *,
    preflight: StrategyIdeaCandidateAuthoringPreflight,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateAuthoringPreflightWriteResult:
    preflight_path = out_dir / "authoring_preflight.json"
    markdown_path = out_dir / "authoring_preflight.md"
    if not replace_existing and (preflight_path.exists() or markdown_path.exists()):
        raise StrategyIdeaCandidateAuthoringPreflightOutputExistsError(
            f"output already exists: {out_dir}"
        )
    write_json_artifact(preflight_path, preflight.model_dump(mode="json", exclude_none=True))
    write_text_artifact(markdown_path, render_authoring_preflight_markdown(preflight))
    return StrategyIdeaCandidateAuthoringPreflightWriteResult(
        preflight=preflight,
        preflight_path=preflight_path,
        markdown_path=markdown_path,
        preflight_sha256=sha256_file(preflight_path),
    )


def render_authoring_preflight_markdown(
    preflight: StrategyIdeaCandidateAuthoringPreflight,
) -> str:
    lines = [
        f"# Authoring Preflight: {preflight.candidate_set_id}",
        "",
        "- strategy_authoring_spec_ready_count: `0`",
        "- backtest_ready_count: `0`",
        "- paper_ready_count: `0`",
        "- live_ready_count: `0`",
        "",
        "## Candidate Results",
        "",
        "| candidate_id | idea_export_written | authoring_ready | backtest_ready |",
        "|---|---:|---:|---:|",
    ]
    for item in preflight.candidate_results:
        lines.append(
            "| "
            f"`{item['candidate_id']}` | "
            f"`{str(item['strategy_idea_v1_export_written']).lower()}` | "
            f"`{str(item['strategy_authoring_spec_ready']).lower()}` | "
            f"`{str(item['backtest_ready']).lower()}` |"
        )
    if preflight.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in preflight.known_gaps)
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
