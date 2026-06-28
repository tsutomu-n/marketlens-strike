from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows
from sis.strategy_idea_candidates.models import (
    CandidateBoundary,
    CandidateDecision,
    StrategyIdeaCandidateSet,
)
from sis.strategy_idea_candidates.perp_costs import (
    is_perp_candidate,
    perp_cost_estimate_from_candidate,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo
from sis.strategy_review.provenance import repo_relative_path


PERP_ESTIMATE_BRIDGE_SCHEMA_VERSION = "strategy_idea_candidate_perp_estimate_bridge.v1"


class StrategyIdeaCandidatePerpEstimateRowSetRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    side_bias: str
    row_set_path: str
    row_set_sha256: str
    row_set_id: str
    evidence_level: Literal["cost_adjusted_estimate"] = "cost_adjusted_estimate"
    actual_cash_result_available: Literal[False] = False


class StrategyIdeaCandidatePerpEstimateBridgeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_perp_estimate_bridge.v1"] = (
        PERP_ESTIMATE_BRIDGE_SCHEMA_VERSION
    )
    manifest_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    candidate_set_path: str
    candidate_set_sha256: str
    outcome_paths: list[str]
    row_sets: list[StrategyIdeaCandidatePerpEstimateRowSetRef]
    summary: dict[str, Any]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _serialize_datetime(value)

    @field_validator("manifest_id", "candidate_set_id")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("id fields must not be empty")
        return stripped


@dataclass(frozen=True)
class StrategyIdeaCandidatePerpEstimateBridgeWriteResult:
    manifest: StrategyIdeaCandidatePerpEstimateBridgeManifest
    manifest_path: Path
    manifest_sha256: str
    row_set_paths: list[Path]


class StrategyIdeaCandidatePerpEstimateBridgeOutputExistsError(ValueError):
    pass


def build_and_write_candidate_perp_estimate_bridge(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    candidate_set_path: Path,
    outcome_paths: list[Path],
    out_dir: Path,
    replace_existing: bool = False,
    created_at: datetime | str | None = None,
) -> StrategyIdeaCandidatePerpEstimateBridgeWriteResult:
    manifest_path = out_dir / "perp_estimate_bridge_manifest.json"
    if manifest_path.exists() and not replace_existing:
        raise StrategyIdeaCandidatePerpEstimateBridgeOutputExistsError(
            f"output already exists: {manifest_path}"
        )
    outcomes = [_read_outcome(path) for path in outcome_paths]
    created = _coerce_datetime(created_at)
    row_set_refs: list[StrategyIdeaCandidatePerpEstimateRowSetRef] = []
    row_set_paths: list[Path] = []
    candidates = [
        candidate
        for candidate in candidate_set.candidate_inventory
        if candidate.decision is CandidateDecision.SHORTLISTED and is_perp_candidate(candidate)
    ]
    for candidate in candidates:
        estimate = perp_cost_estimate_from_candidate(candidate)
        row_set = build_cost_aware_tournament_rows(
            outcomes=outcomes,
            created_at=created,
            notional_usd=Decimal(str(estimate.notional_usd)),
            fee_rate=Decimal(str(estimate.fee_rate)),
            funding_rate=Decimal(str(estimate.funding_rate_bps_per_8h)) / Decimal("10000"),
            slippage_bps=Decimal(str(estimate.slippage_bps)),
            source_refs=[
                {
                    "path": repo_relative_path(candidate_set_path),
                    "sha256": sha256_file(candidate_set_path),
                    "schema_version": candidate_set.schema_version,
                },
                {
                    "path": repo_relative_path(candidate_set_path),
                    "sha256": candidate.source_artifact_sha256,
                    "schema_version": "strategy_idea_candidate",
                },
            ],
            known_gaps=[
                "CANDIDATE_PERP_ESTIMATE_NOT_ACTUAL_CASH",
                "ACTUAL_CASH_RESULT_NOT_AVAILABLE",
            ],
            producer_command="strategy-idea-candidates-perp-estimate",
        )
        candidate_dir = out_dir / candidate.idea_candidate_id
        row_set_path = candidate_dir / "crypto_perp_tournament_rows_v2.json"
        if row_set_path.exists() and not replace_existing:
            raise StrategyIdeaCandidatePerpEstimateBridgeOutputExistsError(
                f"output already exists: {row_set_path}"
            )
        write_json_artifact(row_set_path, row_set.model_dump(mode="json"))
        row_set_paths.append(row_set_path)
        row_set_refs.append(
            StrategyIdeaCandidatePerpEstimateRowSetRef(
                candidate_id=candidate.idea_candidate_id,
                side_bias=str(candidate.parameter_set.get("side_bias") or ""),
                row_set_path=repo_relative_path(row_set_path),
                row_set_sha256=sha256_file(row_set_path),
                row_set_id=row_set.row_set_id,
            )
        )
    manifest = StrategyIdeaCandidatePerpEstimateBridgeManifest(
        manifest_id=f"{candidate_set.candidate_set_id}-perp-estimate-bridge",
        created_at=created,
        producer=ProducerInfo(command="strategy-idea-candidates-perp-estimate"),
        candidate_set_id=candidate_set.candidate_set_id,
        candidate_set_path=repo_relative_path(candidate_set_path),
        candidate_set_sha256=sha256_file(candidate_set_path),
        outcome_paths=[repo_relative_path(path) for path in outcome_paths],
        row_sets=row_set_refs,
        summary={
            "shortlisted_perp_candidate_count": len(candidates),
            "outcome_count": len(outcomes),
            "row_set_count": len(row_set_refs),
            "actual_cash_result_available": False,
        },
        known_gaps=[
            "CANDIDATE_PERP_ESTIMATE_NOT_ACTUAL_CASH",
            "ACTUAL_CASH_RESULT_NOT_AVAILABLE",
            "DO_NOT_FEED_TO_CRYPTO_PERP_TOURNAMENT_REPORT_AS_ACTUAL_CASH",
        ],
    )
    write_json_artifact(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
    write_text_artifact(
        out_dir / "perp_estimate_bridge_manifest.md",
        render_perp_estimate_bridge_manifest_markdown(manifest),
    )
    return StrategyIdeaCandidatePerpEstimateBridgeWriteResult(
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        row_set_paths=row_set_paths,
    )


def render_perp_estimate_bridge_manifest_markdown(
    manifest: StrategyIdeaCandidatePerpEstimateBridgeManifest,
) -> str:
    lines = [
        f"# Perp Estimate Bridge: {manifest.candidate_set_id}",
        "",
        "- evidence_level: `cost_adjusted_estimate`",
        "- actual_cash_result_available: `false`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Row Sets",
        "",
        "| candidate_id | side_bias | row_set_path |",
        "|---|---|---|",
    ]
    for ref in manifest.row_sets:
        lines.append(
            "| "
            f"`{ref.candidate_id}` | "
            f"`{ref.side_bias}` | "
            f"`{ref.row_set_path}` |"
        )
    if manifest.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in manifest.known_gaps)
    return "\n".join(lines) + "\n"


def _read_outcome(path: Path) -> CryptoPerpOutcome:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CryptoPerpOutcome.model_validate(payload)


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
