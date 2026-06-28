from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import CandidateBoundary, StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.perp_costs import (
    StrategyIdeaCandidatePerpCostEstimateReport,
)
from sis.strategy_idea_candidates.policies import StrategyIdeaCandidatePolicyValidationResult
from sis.strategy_idea_candidates.selection_metrics import (
    StrategyIdeaCandidateSelectionMetricsReport,
)
from sis.strategy_idea_candidates.splits import StrategyIdeaCandidateSplitMaterialization
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo


REVIEW_PACKET_SCHEMA_VERSION = "strategy_idea_candidate_review_packet.v1"


class StrategyIdeaCandidateReviewPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_review_packet.v1"] = (
        REVIEW_PACKET_SCHEMA_VERSION
    )
    packet_id: str
    generated_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    summary: dict[str, Any]
    candidate_reviews: list[dict[str, Any]]
    rejection_reason_counts: dict[str, int]
    policy_validation: dict[str, Any]
    known_gaps: list[str]
    human_review_template: dict[str, Any]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return _serialize_datetime(value)


@dataclass(frozen=True)
class StrategyIdeaCandidateReviewPacketWriteResult:
    packet: StrategyIdeaCandidateReviewPacket
    packet_path: Path
    markdown_path: Path
    packet_sha256: str


class StrategyIdeaCandidateReviewPacketOutputExistsError(ValueError):
    pass


def build_strategy_idea_candidate_review_packet(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    selection_metrics: StrategyIdeaCandidateSelectionMetricsReport,
    perp_cost_estimates: StrategyIdeaCandidatePerpCostEstimateReport,
    split_materialization: StrategyIdeaCandidateSplitMaterialization,
    policy_validation: StrategyIdeaCandidatePolicyValidationResult | None,
    generated_at: datetime | str | None = None,
) -> StrategyIdeaCandidateReviewPacket:
    timestamp = _coerce_datetime(generated_at)
    costs_by_candidate_id = {
        estimate.candidate_id: estimate for estimate in perp_cost_estimates.estimates
    }
    metrics_by_candidate_id = {
        adjustment.candidate_id: adjustment for adjustment in selection_metrics.adjustments
    }
    candidate_reviews: list[dict[str, Any]] = []
    for candidate in candidate_set.candidate_inventory:
        estimate = costs_by_candidate_id.get(candidate.idea_candidate_id)
        adjustment = metrics_by_candidate_id.get(candidate.idea_candidate_id)
        candidate_reviews.append(
            {
                "candidate_id": candidate.idea_candidate_id,
                "decision": candidate.decision.value,
                "family": candidate.family,
                "title": candidate.title,
                "side_bias": candidate.parameter_set.get("side_bias"),
                "selection_adjusted_metrics_status": (
                    candidate.selection_adjusted_metrics_status.value
                ),
                "benjamini_hochberg_q_value": (
                    adjustment.benjamini_hochberg_q_value if adjustment else None
                ),
                "estimated_round_trip_cost_usd": (
                    estimate.estimated_round_trip_cost_usd if estimate else None
                ),
                "stress_round_trip_cost_usd": (
                    estimate.stress_round_trip_cost_usd if estimate else None
                ),
                "shortlist_reason": candidate.shortlist_reason,
                "rejection_reason": candidate.rejection_reason,
                "human_decision": "UNREVIEWED",
                "allowed_human_decisions": [
                    "KEEP_FOR_QUICK_VALIDATION",
                    "REJECT",
                    "REQUEST_MORE_EVIDENCE",
                ],
            }
        )
    rejection_counts = Counter(
        candidate.rejection_reason or ""
        for candidate in candidate_set.candidate_inventory
        if candidate.rejection_reason
    )
    policy_failures = policy_validation.failures if policy_validation is not None else []
    known_gaps = list(
        dict.fromkeys(
            [
                *candidate_set.selection_policy.known_gaps,
                *selection_metrics.known_gaps,
                *perp_cost_estimates.known_gaps,
                *split_materialization.known_gaps,
                "HUMAN_REVIEW_REQUIRED_BEFORE_SHORTLIST_PROMOTION",
                "REVIEW_PACKET_NOT_PAPER_OR_LIVE_PERMISSION",
            ]
        )
    )
    summary = {
        "candidate_count_total": candidate_set.search_ledger_summary.candidate_count_total,
        "candidate_count_shortlisted": candidate_set.search_ledger_summary.candidate_count_shortlisted,
        "candidate_count_rejected": candidate_set.search_ledger_summary.candidate_count_rejected,
        "selection_metric_status_counts": selection_metrics.status_counts,
        "perp_cost_estimate_count": len(perp_cost_estimates.estimates),
        "split_row_count": len(split_materialization.rows),
        "policy_validation_passed": policy_validation.passed if policy_validation else None,
        "known_gap_count": len(known_gaps),
    }
    return StrategyIdeaCandidateReviewPacket(
        packet_id=f"{candidate_set.candidate_set_id}-review-packet",
        generated_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidates-review-packet"),
        candidate_set_id=candidate_set.candidate_set_id,
        summary=summary,
        candidate_reviews=candidate_reviews,
        rejection_reason_counts=dict(sorted(rejection_counts.items())),
        policy_validation={
            "status": "PASS"
            if policy_validation is not None and policy_validation.passed
            else "FAIL"
            if policy_validation is not None
            else "NOT_RUN",
            "failures": policy_failures,
        },
        known_gaps=known_gaps,
        human_review_template={
            "reviewer": "",
            "reviewed_at": "",
            "decision": "UNREVIEWED",
            "notes": "",
            "paper_or_live_permission_granted": False,
        },
    )


def write_strategy_idea_candidate_review_packet(
    *,
    packet: StrategyIdeaCandidateReviewPacket,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateReviewPacketWriteResult:
    packet_path = out_dir / "strategy_idea_candidate_review_packet.json"
    markdown_path = out_dir / "strategy_idea_candidate_review_packet.md"
    if not replace_existing and (packet_path.exists() or markdown_path.exists()):
        raise StrategyIdeaCandidateReviewPacketOutputExistsError(
            f"output already exists: {out_dir}"
        )
    write_json_artifact(packet_path, packet.model_dump(mode="json", exclude_none=True))
    write_text_artifact(markdown_path, render_review_packet_markdown(packet))
    return StrategyIdeaCandidateReviewPacketWriteResult(
        packet=packet,
        packet_path=packet_path,
        markdown_path=markdown_path,
        packet_sha256=sha256_file(packet_path),
    )


def render_review_packet_markdown(packet: StrategyIdeaCandidateReviewPacket) -> str:
    lines = [
        f"# Review Packet: {packet.candidate_set_id}",
        "",
        f"- packet_id: `{packet.packet_id}`",
        f"- candidate_count_total: `{packet.summary['candidate_count_total']}`",
        f"- candidate_count_shortlisted: `{packet.summary['candidate_count_shortlisted']}`",
        "- paper_or_live_permission_granted: `false`",
        "",
        "## Candidate Reviews",
        "",
        "| candidate_id | decision | family | metrics_status | est_cost_usd | human_decision |",
        "|---|---|---|---|---:|---|",
    ]
    for review in packet.candidate_reviews:
        lines.append(
            "| "
            f"`{review['candidate_id']}` | "
            f"`{review['decision']}` | "
            f"`{review['family']}` | "
            f"`{review['selection_adjusted_metrics_status']}` | "
            f"`{review.get('estimated_round_trip_cost_usd')}` | "
            f"`{review['human_decision']}` |"
        )
    if packet.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in packet.known_gaps)
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
