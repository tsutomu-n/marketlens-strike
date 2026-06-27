from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.edge_rules import rank_directional_actions, select_action
from sis.crypto_perp.features import CryptoPerpFeaturePack
from sis.crypto_perp.models import (
    CryptoPerpAction,
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)
from sis.crypto_perp.source_availability import CryptoPerpSourceAvailability


EDGE_SCORE_SCHEMA_VERSION = "crypto_perp_edge_score.v1"


class EdgeActionScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal["REVERSAL_SHORT", "CONTINUATION_LONG", "NO_TRADE", "UNKNOWN"]
    score: DecimalValue
    rank: int = Field(ge=1)
    reasons: list[str]
    missing_evidence: list[str]

    @field_serializer("score")
    def serialize_decimal(self, value: Decimal) -> str:
        return decimal_to_json_string(value)


class CryptoPerpEdgeScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_edge_score.v1"] = EDGE_SCORE_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    edge_score_id: str
    event_id: str
    information_cutoff_at: datetime
    selected_action: Literal["REVERSAL_SHORT", "CONTINUATION_LONG", "NO_TRADE", "UNKNOWN"]
    action_scores: list[EdgeActionScore]
    why_no_trade: list[str]
    known_gaps: list[str]
    summary: dict[str, object]

    @field_validator("created_at", "information_cutoff_at", mode="before")
    @classmethod
    def validate_utc(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("timestamp", value)

    @field_serializer("created_at", "information_cutoff_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _decimal(value: str, *, field_name: str) -> Decimal:
    try:
        return Decimal(value)
    except Exception as exc:
        raise ValueError(f"{field_name} must be a decimal string") from exc


def _ranked_score_rows(
    scores: dict[CryptoPerpAction, Decimal],
    *,
    missing_evidence: list[str],
) -> list[EdgeActionScore]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        EdgeActionScore(
            action=action.value,
            score=score,
            rank=index + 1,
            reasons=[f"deterministic_rule_score_bps={decimal_to_json_string(score)}"],
            missing_evidence=missing_evidence,
        )
        for index, (action, score) in enumerate(ordered)
    ]


def build_edge_score(
    *,
    feature_pack: CryptoPerpFeaturePack,
    source_availability: CryptoPerpSourceAvailability,
    created_at: datetime | str,
    min_abs_event_return_bps: Decimal = Decimal("30"),
    producer_command: str = "crypto-perp-edge-score",
) -> CryptoPerpEdgeScore:
    if feature_pack.event_id != source_availability.event_id:
        raise ValueError("feature pack and source availability event_id must match")
    created = ensure_utc_aware("created_at", created_at)
    known_gaps = list(dict.fromkeys([*source_availability.known_gaps, *feature_pack.known_gaps]))
    missing_evidence = [
        gap
        for gap in known_gaps
        if gap.endswith("_SOURCE_MISSING") or gap.endswith("_NOT_PROVIDED")
    ]
    why_no_trade: list[str] = []
    if not source_availability.can_compute_cost_adjusted_estimate:
        selected = CryptoPerpAction.UNKNOWN
        scores = {CryptoPerpAction.UNKNOWN: Decimal("0")}
        why_no_trade.append("COST_ADJUSTED_INPUTS_MISSING")
        known_gaps.append("EDGE_SCORE_UNKNOWN_COST_ADJUSTED_INPUTS_MISSING")
    else:
        event_return = _decimal(feature_pack.event_return, field_name="event_return")
        spread_bps = _decimal(feature_pack.spread_bps, field_name="spread_bps")
        funding_rate = _decimal(feature_pack.funding_rate, field_name="funding_rate")
        scores = rank_directional_actions(
            event_return=event_return,
            spread_bps=spread_bps,
            funding_rate=funding_rate,
            min_abs_event_return_bps=min_abs_event_return_bps,
        )
        selected = select_action(scores)
        if selected == CryptoPerpAction.NO_TRADE:
            why_no_trade.append("NO_ACTION_SCORE_ABOVE_ZERO_AFTER_FRICTION")
    known_gaps = list(dict.fromkeys(known_gaps))
    action_scores = _ranked_score_rows(scores, missing_evidence=missing_evidence)
    edge_score_id = stable_hash(
        [
            "crypto-perp-edge-score",
            feature_pack.feature_pack_id,
            source_availability.artifact_id,
            min_abs_event_return_bps,
            selected.value,
            [row.model_dump(mode="json") for row in action_scores],
            known_gaps,
        ]
    )
    summary = {
        "event_id": feature_pack.event_id,
        "selected_action": selected.value,
        "known_gap_count": len(known_gaps),
        "why_no_trade_count": len(why_no_trade),
        "deterministic_rule": True,
    }
    return CryptoPerpEdgeScore(
        artifact_id=stable_hash(["crypto-perp-edge-score-artifact", edge_score_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=producer_command),
        source_refs=[
            *feature_pack.source_refs,
            *source_availability.source_refs,
        ],
        edge_score_id=edge_score_id,
        event_id=feature_pack.event_id,
        information_cutoff_at=feature_pack.information_cutoff_at,
        selected_action=selected.value,
        action_scores=action_scores,
        why_no_trade=why_no_trade,
        known_gaps=known_gaps,
        summary=summary,
    )
