from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bias_guards import CryptoPerpBiasGuard, build_bias_guard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.edge_scorer import CryptoPerpEdgeScore, build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import CryptoPerpFeaturePack, build_feature_pack
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.profit_readiness import (
    ProfitReadinessInventory,
    ProfitReadinessRunManifest,
    build_profit_readiness_inventory,
)
from sis.crypto_perp.replay import CryptoPerpReplaySlice, build_replay_slice
from sis.crypto_perp.source_availability import (
    CryptoPerpSourceAvailability,
    SourceId,
    build_source_availability,
)
from sis.crypto_perp.tournament_rows import (
    CryptoPerpTournamentRowsV2,
    build_cost_aware_tournament_rows,
)


PRE_ACTUAL_CASH_DECISION_SCHEMA_VERSION = "crypto_perp_pre_actual_cash_decision.v1"
PRE_ACTUAL_CASH_PACK_PRODUCER = "pre_actual_cash_evidence_pack_v1"
PRE_ACTUAL_CASH_SUMMARY_ARTIFACT_NAMES = (
    "events_summary",
    "outcomes_summary",
    "source_availability_matrix",
    "known_gaps_by_source",
    "replay_slice_summary",
    "feature_pack_summary",
    "edge_score_summary",
    "tournament_rows_v2_summary",
    "bias_guard_summary",
)
PreActualCashDecisionName = Literal[
    "KILL",
    "REVISE_EVENT_DEFINITION",
    "COLLECT_MORE_SOURCES",
    "HOLD_FOR_FUTURE_ACTUAL_CASH",
]
ModelT = TypeVar("ModelT", bound=BaseModel)


class PreActualCashDecisionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_pre_actual_cash_decision.v1"] = (
        PRE_ACTUAL_CASH_DECISION_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    decision: PreActualCashDecisionName
    reason_codes: list[str]
    event_count: int = Field(ge=0)
    outcome_count: int = Field(ge=0)
    source_gap_summary: dict[str, Any]
    edge_summary: dict[str, Any]
    tournament_summary: dict[str, Any]
    bias_guard_summary: dict[str, Any]
    non_goal_flags: dict[str, bool]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class _EventOutcomePair:
    event_path: Path
    event: CryptoPerpEvent
    outcome_path: Path
    outcome: CryptoPerpOutcome


@dataclass(frozen=True)
class _RunManifestRecord:
    path: Path
    manifest: ProfitReadinessRunManifest


@dataclass(frozen=True)
class _ArtifactOrigin:
    origin: Literal["existing", "recomputed_minimal", "not_run"]
    path: str | None
    gap_origin: str
    match_note: str


@dataclass(frozen=True)
class _ExistingArtifacts:
    source_availability: dict[str, tuple[Path, CryptoPerpSourceAvailability]]
    replay_slice: dict[str, tuple[Path, CryptoPerpReplaySlice]]
    feature_pack: dict[str, tuple[Path, CryptoPerpFeaturePack]]
    edge_score: dict[str, tuple[Path, CryptoPerpEdgeScore]]
    rows_v2: tuple[Path, CryptoPerpTournamentRowsV2] | None
    bias_guard: tuple[Path, CryptoPerpBiasGuard] | None
    known_gaps: list[str]


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _artifact_ref(path: Path, schema_version: str | None = None) -> dict[str, str]:
    ref = {"path": path.as_posix(), "sha256": "sha256:" + stable_hash([path.read_text("utf-8")])}
    if schema_version:
        ref["schema_version"] = schema_version
    return ref


def _json_ready(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _load_events(inventory: ProfitReadinessInventory) -> dict[str, tuple[Path, CryptoPerpEvent]]:
    events: dict[str, tuple[Path, CryptoPerpEvent]] = {}
    for item in inventory.items:
        if item.category != "event":
            continue
        path = Path(item.path)
        event = CryptoPerpEvent.model_validate(_load_json_object(path))
        events.setdefault(event.event_id, (path, event))
    return events


def _load_matured_outcomes(
    inventory: ProfitReadinessInventory,
) -> dict[str, list[tuple[Path, CryptoPerpOutcome]]]:
    outcomes_by_event: dict[str, list[tuple[Path, CryptoPerpOutcome]]] = {}
    for item in inventory.items:
        if item.category != "outcome" or not item.matured_outcome:
            continue
        path = Path(item.path)
        outcome = CryptoPerpOutcome.model_validate(_load_json_object(path))
        outcomes_by_event.setdefault(outcome.event_id, []).append((path, outcome))
    for outcomes in outcomes_by_event.values():
        outcomes.sort(key=lambda pair: pair[0].as_posix())
    return outcomes_by_event


def _load_run_manifests(data_dir: Path) -> list[_RunManifestRecord]:
    records: list[_RunManifestRecord] = []
    for path in sorted(data_dir.rglob("*.json")) if data_dir.exists() else []:
        try:
            payload = _load_json_object(path)
        except Exception:
            continue
        if payload.get("schema_version") != "crypto_perp_profit_readiness_run.v1":
            continue
        records.append(
            _RunManifestRecord(
                path=path,
                manifest=ProfitReadinessRunManifest.model_validate(payload),
            )
        )
    return records


def _existing_origin(path: Path, match_note: str) -> _ArtifactOrigin:
    return _ArtifactOrigin(
        origin="existing",
        path=path.as_posix(),
        gap_origin="existing artifact payload",
        match_note=match_note,
    )


def _recomputed_origin(reason: str) -> _ArtifactOrigin:
    return _ArtifactOrigin(
        origin="recomputed_minimal",
        path=None,
        gap_origin="minimal recomputed from event/outcome only",
        match_note=reason,
    )


def _not_run_origin(reason: str) -> _ArtifactOrigin:
    return _ArtifactOrigin(
        origin="not_run",
        path=None,
        gap_origin="not run",
        match_note=reason,
    )


def _origin_payload(origin: _ArtifactOrigin) -> dict[str, str | None]:
    return {
        "artifact_origin": origin.origin,
        "artifact_path": origin.path,
        "artifact_gap_origin": origin.gap_origin,
        "artifact_match_note": origin.match_note,
    }


def _origin_counts(origins: Sequence[_ArtifactOrigin]) -> dict[str, int]:
    return dict(sorted(Counter(origin.origin for origin in origins).items()))


def _origin_for_event(
    origins: Mapping[str, _ArtifactOrigin] | None,
    event_id: str,
) -> dict[str, str | None]:
    if origins is None or event_id not in origins:
        return {}
    return _origin_payload(origins[event_id])


def _load_existing_per_event_artifacts(
    *,
    inventory: ProfitReadinessInventory,
    category: str,
    model_type: type[ModelT],
) -> tuple[dict[str, tuple[Path, ModelT]], list[str]]:
    candidates: dict[str, list[tuple[Path, ModelT]]] = {}
    known_gaps: list[str] = []
    category_token = category.upper()
    for item in inventory.items:
        if item.category != category:
            continue
        path = Path(item.path)
        try:
            artifact = model_type.model_validate(_load_json_object(path))
        except Exception:
            known_gaps.append(f"EXISTING_{category_token}_INVALID")
            continue
        event_id = getattr(artifact, "event_id", None)
        if not isinstance(event_id, str) or not event_id:
            known_gaps.append(f"EXISTING_{category_token}_MISSING_EVENT_ID")
            continue
        candidates.setdefault(event_id, []).append((path, artifact))

    selected: dict[str, tuple[Path, ModelT]] = {}
    for event_id, artifacts in sorted(candidates.items()):
        artifacts.sort(key=lambda pair: pair[0].as_posix())
        if len(artifacts) > 1:
            known_gaps.append(f"MULTIPLE_EXISTING_{category_token}_FOR_EVENT_COLLAPSED_TO_FIRST")
        selected[event_id] = artifacts[0]
    return selected, _unique(known_gaps)


def _load_existing_rows_v2(
    *,
    inventory: ProfitReadinessInventory,
    event_ids: Sequence[str],
) -> tuple[tuple[Path, CryptoPerpTournamentRowsV2] | None, list[str]]:
    expected_event_set = sorted(set(event_ids))
    known_gaps: list[str] = []
    candidates: list[tuple[Path, CryptoPerpTournamentRowsV2]] = []
    mismatch_count = 0
    for item in inventory.items:
        if item.category != "rows_v2":
            continue
        path = Path(item.path)
        try:
            rows = CryptoPerpTournamentRowsV2.model_validate(_load_json_object(path))
        except Exception:
            known_gaps.append("EXISTING_ROWS_V2_INVALID")
            continue
        if sorted(rows.event_set) == expected_event_set:
            candidates.append((path, rows))
        else:
            mismatch_count += 1
    if mismatch_count:
        known_gaps.append("EXISTING_ROWS_V2_EVENT_SET_MISMATCH")
    if not candidates:
        return None, _unique(known_gaps)
    candidates.sort(key=lambda pair: pair[0].as_posix())
    if len(candidates) > 1:
        known_gaps.append("MULTIPLE_EXISTING_ROWS_V2_FOR_EVENT_SET_COLLAPSED_TO_FIRST")
    return candidates[0], _unique(known_gaps)


def _load_existing_bias_guard(
    *,
    inventory: ProfitReadinessInventory,
    event_count: int,
) -> tuple[tuple[Path, CryptoPerpBiasGuard] | None, list[str]]:
    if event_count <= 0:
        return None, []
    known_gaps: list[str] = []
    candidates: list[tuple[Path, CryptoPerpBiasGuard]] = []
    mismatch_count = 0
    for item in inventory.items:
        if item.category != "bias_guard":
            continue
        path = Path(item.path)
        try:
            guard = CryptoPerpBiasGuard.model_validate(_load_json_object(path))
        except Exception:
            known_gaps.append("EXISTING_BIAS_GUARD_INVALID")
            continue
        if guard.event_count == event_count:
            candidates.append((path, guard))
        else:
            mismatch_count += 1
    if mismatch_count:
        known_gaps.append("EXISTING_BIAS_GUARD_EVENT_COUNT_MISMATCH")
    if not candidates:
        return None, _unique(known_gaps)
    candidates.sort(key=lambda pair: pair[0].as_posix())
    if len(candidates) > 1:
        known_gaps.append("MULTIPLE_EXISTING_BIAS_GUARD_FOR_EVENT_COUNT_COLLAPSED_TO_FIRST")
    return candidates[0], _unique(known_gaps)


def _load_existing_artifacts(
    *,
    inventory: ProfitReadinessInventory,
    pairs: Sequence[_EventOutcomePair],
) -> _ExistingArtifacts:
    source_artifacts, source_gaps = _load_existing_per_event_artifacts(
        inventory=inventory,
        category="source_availability",
        model_type=CryptoPerpSourceAvailability,
    )
    replay_artifacts, replay_gaps = _load_existing_per_event_artifacts(
        inventory=inventory,
        category="replay_slice",
        model_type=CryptoPerpReplaySlice,
    )
    feature_artifacts, feature_gaps = _load_existing_per_event_artifacts(
        inventory=inventory,
        category="feature_pack",
        model_type=CryptoPerpFeaturePack,
    )
    edge_artifacts, edge_gaps = _load_existing_per_event_artifacts(
        inventory=inventory,
        category="edge_score",
        model_type=CryptoPerpEdgeScore,
    )
    event_ids = [pair.event.event_id for pair in pairs]
    rows, rows_gaps = _load_existing_rows_v2(inventory=inventory, event_ids=event_ids)
    guard, guard_gaps = _load_existing_bias_guard(
        inventory=inventory,
        event_count=len(set(event_ids)),
    )
    return _ExistingArtifacts(
        source_availability=source_artifacts,
        replay_slice=replay_artifacts,
        feature_pack=feature_artifacts,
        edge_score=edge_artifacts,
        rows_v2=rows,
        bias_guard=guard,
        known_gaps=_unique(
            [
                *source_gaps,
                *replay_gaps,
                *feature_gaps,
                *edge_gaps,
                *rows_gaps,
                *guard_gaps,
            ]
        ),
    )


def _select_pairs(
    *,
    events_by_id: dict[str, tuple[Path, CryptoPerpEvent]],
    outcomes_by_event: dict[str, list[tuple[Path, CryptoPerpOutcome]]],
) -> tuple[list[_EventOutcomePair], list[str]]:
    known_gaps: list[str] = []
    pairs: list[_EventOutcomePair] = []
    for event_id in sorted(events_by_id):
        event_path, event = events_by_id[event_id]
        outcomes = outcomes_by_event.get(event_id, [])
        if not outcomes:
            known_gaps.append("EVENT_WITHOUT_MATURED_OUTCOME")
            continue
        if len(outcomes) > 1:
            known_gaps.append("MULTIPLE_MATURED_OUTCOMES_FOR_EVENT_COLLAPSED_TO_FIRST")
        outcome_path, outcome = outcomes[0]
        pairs.append(
            _EventOutcomePair(
                event_path=event_path,
                event=event,
                outcome_path=outcome_path,
                outcome=outcome,
            )
        )
    for event_id in sorted(outcomes_by_event):
        if event_id not in events_by_id:
            known_gaps.append("MATURED_OUTCOME_WITHOUT_EVENT")
    return pairs, _unique(known_gaps)


def _build_per_event_artifacts(
    *,
    pairs: Sequence[_EventOutcomePair],
    created: datetime,
    existing_artifacts: _ExistingArtifacts,
) -> tuple[
    list[CryptoPerpSourceAvailability],
    list[CryptoPerpReplaySlice],
    list[CryptoPerpFeaturePack],
    list[CryptoPerpEdgeScore],
    dict[str, dict[str, _ArtifactOrigin]],
    list[str],
]:
    source_artifacts: list[CryptoPerpSourceAvailability] = []
    replay_artifacts: list[CryptoPerpReplaySlice] = []
    feature_artifacts: list[CryptoPerpFeaturePack] = []
    edge_artifacts: list[CryptoPerpEdgeScore] = []
    artifact_origins: dict[str, dict[str, _ArtifactOrigin]] = {
        "source_availability": {},
        "replay_slice": {},
        "feature_pack": {},
        "edge_score": {},
    }
    known_gaps: list[str] = []
    for pair in pairs:
        event_id = pair.event.event_id
        source_record = existing_artifacts.source_availability.get(event_id)
        if source_record is None:
            source = build_source_availability(
                event=pair.event,
                created_at=created,
                available_sources={"outcome": True},
                row_counts={"outcome": 1},
                source_refs=[_artifact_ref(pair.outcome_path, pair.outcome.schema_version)],
                producer_command=PRE_ACTUAL_CASH_PACK_PRODUCER,
            )
            artifact_origins["source_availability"][event_id] = _recomputed_origin(
                "source_availability artifact missing for event_id"
            )
        else:
            source_path, source = source_record
            artifact_origins["source_availability"][event_id] = _existing_origin(
                source_path,
                "matched_by_event_id",
            )

        replay_record = existing_artifacts.replay_slice.get(event_id)
        if replay_record is None:
            replay = build_replay_slice(
                event=pair.event,
                created_at=created,
                included_sources=["event", "outcome"],
                row_counts={"event": 1, "outcome": 1},
                source_refs=[_artifact_ref(pair.outcome_path, pair.outcome.schema_version)],
                producer_command=PRE_ACTUAL_CASH_PACK_PRODUCER,
            )
            artifact_origins["replay_slice"][event_id] = _recomputed_origin(
                "replay_slice artifact missing for event_id"
            )
        else:
            replay_path, replay = replay_record
            artifact_origins["replay_slice"][event_id] = _existing_origin(
                replay_path,
                "matched_by_event_id",
            )

        feature_record = existing_artifacts.feature_pack.get(event_id)
        if feature_record is None:
            feature = build_feature_pack(
                event=pair.event,
                source_availability=source,
                created_at=created,
                producer_command=PRE_ACTUAL_CASH_PACK_PRODUCER,
            )
            artifact_origins["feature_pack"][event_id] = _recomputed_origin(
                "feature_pack artifact missing for event_id"
            )
        else:
            feature_path, feature = feature_record
            artifact_origins["feature_pack"][event_id] = _existing_origin(
                feature_path,
                "matched_by_event_id",
            )

        edge_record = existing_artifacts.edge_score.get(event_id)
        if edge_record is None:
            edge = build_edge_score(
                feature_pack=feature,
                source_availability=source,
                created_at=created,
                producer_command=PRE_ACTUAL_CASH_PACK_PRODUCER,
            )
            artifact_origins["edge_score"][event_id] = _recomputed_origin(
                "edge_score artifact missing for event_id"
            )
        else:
            edge_path, edge = edge_record
            artifact_origins["edge_score"][event_id] = _existing_origin(
                edge_path,
                "matched_by_event_id",
            )
        source_artifacts.append(source)
        replay_artifacts.append(replay)
        feature_artifacts.append(feature)
        edge_artifacts.append(edge)
        known_gaps.extend(source.known_gaps)
        known_gaps.extend(replay.known_gaps)
        known_gaps.extend(feature.known_gaps)
        known_gaps.extend(edge.known_gaps)
    return (
        source_artifacts,
        replay_artifacts,
        feature_artifacts,
        edge_artifacts,
        artifact_origins,
        _unique(known_gaps),
    )


def _source_ids() -> tuple[SourceId, ...]:
    return (
        "event",
        "bars",
        "ticker",
        "funding",
        "trades",
        "books",
        "outcome",
        "replay",
        "cash_ledger",
        "live_measurement",
    )


def _source_availability_matrix(
    source_artifacts: Sequence[CryptoPerpSourceAvailability],
    origins: Mapping[str, _ArtifactOrigin] | None = None,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    can_compute_actual_cash_count = 0
    can_compute_cost_adjusted_count = 0
    can_compute_depth_count = 0
    public_candle_only_count = 0
    for artifact in source_artifacts:
        status_by_id = {status.source_id: status for status in artifact.source_statuses}
        sources = {
            source_id: {
                "available": status_by_id[source_id].available,
                "row_count": status_by_id[source_id].row_count,
                "reason": status_by_id[source_id].reason,
            }
            for source_id in _source_ids()
        }
        can_compute_actual_cash_count += int(artifact.can_compute_actual_cash)
        can_compute_cost_adjusted_count += int(artifact.can_compute_cost_adjusted_estimate)
        can_compute_depth_count += int(artifact.can_compute_depth)
        has_microstructure = sources["trades"]["available"] or sources["books"]["available"]
        if not has_microstructure and not artifact.can_compute_actual_cash:
            public_candle_only_count += 1
        events.append(
            {
                "event_id": artifact.event_id,
                "can_compute_actual_cash": artifact.can_compute_actual_cash,
                "can_compute_cost_adjusted_estimate": artifact.can_compute_cost_adjusted_estimate,
                "can_compute_depth": artifact.can_compute_depth,
                "known_gap_count": len(artifact.known_gaps),
                "sources": sources,
                **_origin_for_event(origins, artifact.event_id),
            }
        )
    return {
        "event_count": len(source_artifacts),
        "artifact_origin_counts": _origin_counts(list(origins.values())) if origins else {},
        "source_ids": list(_source_ids()),
        "can_compute_actual_cash_count": can_compute_actual_cash_count,
        "can_compute_cost_adjusted_estimate_count": can_compute_cost_adjusted_count,
        "can_compute_depth_count": can_compute_depth_count,
        "public_candle_only_or_no_microstructure_count": public_candle_only_count,
        "events": events,
    }


def _known_gaps_by_source(
    source_artifacts: Sequence[CryptoPerpSourceAvailability],
    extra_known_gaps: Sequence[str],
) -> dict[str, Any]:
    sources: dict[str, dict[str, Any]] = {
        source_id: {"missing_event_count": 0, "reason_codes": []} for source_id in _source_ids()
    }
    for artifact in source_artifacts:
        for status in artifact.source_statuses:
            if status.available:
                continue
            bucket = sources[status.source_id]
            bucket["missing_event_count"] += 1
            bucket["reason_codes"].append(status.reason)
    for bucket in sources.values():
        bucket["reason_codes"] = sorted(set(bucket["reason_codes"]))
    return {
        "sources": sources,
        "global_known_gaps": sorted(set(extra_known_gaps)),
    }


def _events_summary(
    *,
    pairs: Sequence[_EventOutcomePair],
    raw_event_count: int,
    min_events: int,
    selection_gaps: Sequence[str],
) -> dict[str, Any]:
    return {
        "event_count": len(pairs),
        "raw_event_count": raw_event_count,
        "minimum_required_event_count": min_events,
        "known_gaps": list(selection_gaps),
        "events": [
            {
                "event_id": pair.event.event_id,
                "path": pair.event_path.as_posix(),
                "event_family": pair.event.event_family,
                "canonical_symbol": pair.event.canonical_symbol,
                "information_cutoff_at": serialize_utc_z(pair.event.information_cutoff_at),
                "status": pair.event.status,
            }
            for pair in pairs
        ],
    }


def _outcomes_summary(
    *,
    pairs: Sequence[_EventOutcomePair],
    raw_matured_outcome_count: int,
    min_events: int,
    selection_gaps: Sequence[str],
) -> dict[str, Any]:
    return {
        "outcome_count": len(pairs),
        "raw_matured_outcome_count": raw_matured_outcome_count,
        "minimum_required_outcome_count": min_events,
        "known_gaps": list(selection_gaps),
        "outcomes": [
            {
                "event_id": pair.outcome.event_id,
                "outcome_id": pair.outcome.outcome_id,
                "path": pair.outcome_path.as_posix(),
                "settled_at": serialize_utc_z(pair.outcome.settled_at),
                "matured_horizon_count": sum(
                    1 for horizon in pair.outcome.horizons if horizon.matured
                ),
                "known_gap_count": len(pair.outcome.known_gaps),
            }
            for pair in pairs
        ],
    }


def _feature_pack_summary(
    features: Sequence[CryptoPerpFeaturePack],
    origins: Mapping[str, _ArtifactOrigin] | None = None,
) -> dict[str, Any]:
    optional_counts = [len(feature.available_optional_features) for feature in features]
    return {
        "event_count": len(features),
        "artifact_origin_counts": _origin_counts(list(origins.values())) if origins else {},
        "optional_feature_count_min": min(optional_counts, default=0),
        "optional_feature_count_max": max(optional_counts, default=0),
        "optional_feature_count_total": sum(optional_counts),
        "optional_feature_zero_event_count": sum(1 for count in optional_counts if count == 0),
        "sets_entry_action": False,
        "sets_entry_action_count": 0,
        "events": [
            {
                "event_id": feature.event_id,
                "feature_pack_id": feature.feature_pack_id,
                "optional_feature_count": len(feature.available_optional_features),
                "available_optional_features": list(feature.available_optional_features),
                "sets_entry_action": False,
                "known_gap_count": len(feature.known_gaps),
                **_origin_for_event(origins, feature.event_id),
            }
            for feature in features
        ],
    }


def _summary_int(summary: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = summary.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float | str):
        return int(value)
    return default


def _replay_slice_summary(
    replays: Sequence[CryptoPerpReplaySlice],
    origins: Mapping[str, _ArtifactOrigin] | None = None,
) -> dict[str, Any]:
    return {
        "event_count": len(replays),
        "artifact_origin_counts": _origin_counts(list(origins.values())) if origins else {},
        "future_data_included": any(
            bool(replay.summary.get("future_data_included")) for replay in replays
        ),
        "row_count_total": sum(
            _summary_int(replay.summary, "row_count_total") for replay in replays
        ),
        "known_gap_count": sum(len(replay.known_gaps) for replay in replays),
        "events": [
            {
                "event_id": replay.event_id,
                "included_sources": list(replay.included_sources),
                "row_counts": dict(replay.row_counts),
                "future_data_included": bool(replay.summary.get("future_data_included")),
                "known_gap_count": len(replay.known_gaps),
                **_origin_for_event(origins, replay.event_id),
            }
            for replay in replays
        ],
    }


def _edge_score_summary(
    edges: Sequence[CryptoPerpEdgeScore],
    origins: Mapping[str, _ArtifactOrigin] | None = None,
) -> dict[str, Any]:
    selected_counts = Counter(edge.selected_action for edge in edges)
    return {
        "event_count": len(edges),
        "artifact_origin_counts": _origin_counts(list(origins.values())) if origins else {},
        "selected_action_counts": dict(sorted(selected_counts.items())),
        "unknown_selected_action_count": selected_counts.get("UNKNOWN", 0),
        "no_trade_selected_action_count": selected_counts.get("NO_TRADE", 0),
        "known_gap_count": sum(len(edge.known_gaps) for edge in edges),
        "events": [
            {
                "event_id": edge.event_id,
                "selected_action": edge.selected_action,
                "why_no_trade": list(edge.why_no_trade),
                "known_gap_count": len(edge.known_gaps),
                **_origin_for_event(origins, edge.event_id),
            }
            for edge in edges
        ],
    }


def _tournament_summary(
    rows: CryptoPerpTournamentRowsV2 | None,
    origin: _ArtifactOrigin,
) -> dict[str, Any]:
    if rows is None:
        return {
            "event_count": 0,
            "row_count": 0,
            "leader_action": None,
            "leader_beats_no_trade": False,
            "known_gap_count": 0,
            "status": "NOT_RUN",
            **_origin_payload(origin),
        }
    action_totals: dict[str, Decimal] = {}
    for row in rows.rows:
        action_totals[row.action] = action_totals.get(row.action, Decimal("0")) + (
            row.cost_adjusted_cash_estimate_usd
        )
    return {
        **_json_ready(rows.summary),
        "status": "BUILT",
        "primary_metric": rows.primary_metric,
        "action_totals_cost_adjusted_cash_estimate_usd": {
            action: str(value) for action, value in sorted(action_totals.items())
        },
        "actual_cash_result_null_count": sum(
            1 for row in rows.rows if row.actual_cash_result_usd is None
        ),
        **_origin_payload(origin),
    }


def _bias_guard_summary(
    guard: CryptoPerpBiasGuard | None,
    origin: _ArtifactOrigin,
) -> dict[str, Any]:
    if guard is None:
        return {
            "guard_status": "NOT_RUN",
            "pbo_status": "NOT_ESTIMABLE",
            "event_count": 0,
            "known_gaps": ["BIAS_GUARD_NOT_RUN_NO_ROWS"],
            "stop_reasons": ["BIAS_GUARD_NOT_RUN_NO_ROWS"],
            **_origin_payload(origin),
        }
    return {
        "guard_status": guard.guard_status,
        "pbo_status": guard.pbo_status,
        "event_count": guard.event_count,
        "min_events_for_pbo": guard.min_events_for_pbo,
        "fold_count": guard.fold_count,
        "stop_reasons": list(guard.stop_reasons),
        "known_gaps": list(guard.known_gaps),
        "summary": _json_ready(guard.summary),
        **_origin_payload(origin),
    }


def _run_manifest_summary(
    *,
    pairs: Sequence[_EventOutcomePair],
    records: Sequence[_RunManifestRecord],
    computed_known_gaps: Sequence[str],
    reason_codes: Sequence[str],
) -> dict[str, Any]:
    by_pair = {(record.manifest.event_id, record.manifest.outcome_id): record for record in records}
    matched: list[_RunManifestRecord] = []
    missing_pair_count = 0
    for pair in pairs:
        record = by_pair.get((pair.event.event_id, pair.outcome.outcome_id))
        if record is None:
            missing_pair_count += 1
            continue
        matched.append(record)
    status_counts = Counter(record.manifest.status for record in matched)
    existing_known_gaps = _unique([gap for record in matched for gap in record.manifest.known_gaps])
    if matched:
        status = "blocked" if status_counts.get("blocked", 0) else "complete"
    else:
        status = "missing"
    merged_known_gaps = _unique([*existing_known_gaps, *computed_known_gaps, *reason_codes])
    return {
        "status": status,
        "known_gap_count": len(merged_known_gaps),
        "existing_manifest_count": len(records),
        "matched_manifest_count": len(matched),
        "missing_pair_count": missing_pair_count,
        "status_counts": dict(sorted(status_counts.items())),
        "existing_manifest_known_gap_count": len(existing_known_gaps),
        "computed_reason_code_count": len(reason_codes),
        "manifests": [
            {
                "path": record.path.as_posix(),
                "run_id": record.manifest.run_id,
                "event_id": record.manifest.event_id,
                "outcome_id": record.manifest.outcome_id,
                "status": record.manifest.status,
                "known_gap_count": len(record.manifest.known_gaps),
            }
            for record in matched
        ],
    }


def _decide(
    *,
    event_count: int,
    outcome_count: int,
    min_events: int,
    source_matrix: dict[str, Any],
    feature_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    tournament_summary: dict[str, Any],
    bias_guard_summary: dict[str, Any],
) -> tuple[PreActualCashDecisionName, list[str]]:
    reasons: list[str] = []
    if event_count < min_events or outcome_count < min_events:
        reasons.append("MIN_EVENT_OUTCOME_SAMPLE_NOT_MET")
    if source_matrix["can_compute_cost_adjusted_estimate_count"] < event_count:
        reasons.append("COST_ADJUSTED_INPUTS_MISSING")
    if source_matrix["can_compute_depth_count"] < event_count:
        reasons.append("DEPTH_SOURCE_MISSING")
    if int(feature_summary["optional_feature_zero_event_count"]) > 0:
        reasons.append("OPTIONAL_FEATURES_MISSING")
    if int(edge_summary["unknown_selected_action_count"]) > 0:
        reasons.append("EDGE_SELECTED_ACTION_UNKNOWN")
    if tournament_summary.get("status") != "BUILT":
        reasons.append("TOURNAMENT_ROWS_NOT_BUILT")
    if tournament_summary.get("leader_action") == "NO_TRADE":
        reasons.append("TOURNAMENT_LEADER_NO_TRADE")
    if tournament_summary.get("leader_beats_no_trade") is False:
        reasons.append("LEADER_DOES_NOT_BEAT_NO_TRADE")
    if bias_guard_summary.get("pbo_status") == "NOT_ESTIMABLE":
        reasons.append("BIAS_GUARD_SAMPLE_INSUFFICIENT_OR_NOT_ESTIMABLE")
    if bias_guard_summary.get("guard_status") in {"BLOCKED", "NOT_RUN"}:
        reasons.append("BIAS_GUARD_NOT_PASSING")

    collection_reasons = {
        "MIN_EVENT_OUTCOME_SAMPLE_NOT_MET",
        "COST_ADJUSTED_INPUTS_MISSING",
        "DEPTH_SOURCE_MISSING",
        "OPTIONAL_FEATURES_MISSING",
        "EDGE_SELECTED_ACTION_UNKNOWN",
        "TOURNAMENT_ROWS_NOT_BUILT",
        "BIAS_GUARD_SAMPLE_INSUFFICIENT_OR_NOT_ESTIMABLE",
    }
    if collection_reasons.intersection(reasons):
        return "COLLECT_MORE_SOURCES", _unique(reasons)
    if "TOURNAMENT_LEADER_NO_TRADE" in reasons or "LEADER_DOES_NOT_BEAT_NO_TRADE" in reasons:
        return "KILL", _unique(reasons)
    selected_counts = edge_summary.get("selected_action_counts", {})
    if not selected_counts or set(selected_counts) <= {"UNKNOWN", "NO_TRADE"}:
        reasons.append("NO_ACTION_DEFINITION_SURVIVES_PRE_ACTUAL_CASH_GATE")
        return "REVISE_EVENT_DEFINITION", _unique(reasons)
    reasons.append("PRE_ACTUAL_CASH_CANNOT_DECIDE_EXECUTION_QUALITY")
    reasons.append("ACTUAL_CASH_DEFERRED_BY_SCOPE")
    return "HOLD_FOR_FUTURE_ACTUAL_CASH", _unique(reasons)


def _non_goal_flags() -> dict[str, bool]:
    return {
        "actual_cash_used": False,
        "profit_proven": False,
        "actual_cash_readiness_claimed": False,
        "tiny_live_readiness_claimed": False,
        "live_trading_readiness_claimed": False,
        "wallet_or_signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "public_candle_outcome_is_profit_evidence": False,
        "cost_adjusted_estimate_is_actual_cash": False,
        "bias_guard_sample_insufficient_is_robustness_pass": False,
        "llm_trade_decision_used": False,
    }


def _decision_artifact(
    *,
    created: datetime,
    pairs: Sequence[_EventOutcomePair],
    decision: PreActualCashDecisionName,
    reason_codes: Sequence[str],
    source_gap_summary: dict[str, Any],
    edge_summary: dict[str, Any],
    tournament_summary: dict[str, Any],
    bias_guard_summary: dict[str, Any],
) -> PreActualCashDecisionArtifact:
    source_refs = [_artifact_ref(pair.event_path, pair.event.schema_version) for pair in pairs] + [
        _artifact_ref(pair.outcome_path, pair.outcome.schema_version) for pair in pairs
    ]
    payload = {
        "decision": decision,
        "reason_codes": list(reason_codes),
        "event_count": len(pairs),
        "outcome_count": len(pairs),
        "source_gap_summary": source_gap_summary,
        "edge_summary": edge_summary,
        "tournament_summary": tournament_summary,
        "bias_guard_summary": bias_guard_summary,
        "non_goal_flags": _non_goal_flags(),
    }
    return PreActualCashDecisionArtifact(
        artifact_id=stable_hash(
            ["crypto-perp-pre-actual-cash-decision", serialize_utc_z(created), payload]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command=PRE_ACTUAL_CASH_PACK_PRODUCER),
        source_refs=source_refs,
        decision=decision,
        reason_codes=list(reason_codes),
        event_count=len(pairs),
        outcome_count=len(pairs),
        source_gap_summary=source_gap_summary,
        edge_summary=edge_summary,
        tournament_summary=tournament_summary,
        bias_guard_summary=bias_guard_summary,
        non_goal_flags=_non_goal_flags(),
    )


def build_pre_actual_cash_evidence_pack(
    *,
    data_dir: Path,
    created_at: datetime | str,
    notional_usd: Decimal,
    min_events: int = 10,
    min_events_for_pbo: int = 30,
    fold_count: int = 0,
    fee_rate: Decimal = Decimal("0.0006"),
    funding_rate: Decimal = Decimal("0"),
    slippage_bps: Decimal = Decimal("0"),
    operator_time_minutes: Decimal = Decimal("0"),
    operator_hourly_cost_usd: Decimal = Decimal("0"),
) -> tuple[dict[str, dict[str, Any]], PreActualCashDecisionArtifact, str]:
    if min_events <= 0:
        raise ValueError("min_events must be positive")
    created = ensure_utc_aware("created_at", created_at)
    inventory = build_profit_readiness_inventory(data_dir=data_dir, created_at=created)
    events_by_id = _load_events(inventory)
    outcomes_by_event = _load_matured_outcomes(inventory)
    run_manifest_records = _load_run_manifests(data_dir)
    pairs, selection_gaps = _select_pairs(
        events_by_id=events_by_id, outcomes_by_event=outcomes_by_event
    )
    source_artifacts, replay_artifacts, feature_artifacts, edge_artifacts, per_event_gaps = (
        _build_per_event_artifacts(
            pairs=pairs,
            created=created,
        )
    )
    rows: CryptoPerpTournamentRowsV2 | None = None
    guard: CryptoPerpBiasGuard | None = None
    if pairs:
        rows = build_cost_aware_tournament_rows(
            outcomes=[pair.outcome for pair in pairs],
            created_at=created,
            notional_usd=notional_usd,
            fee_rate=fee_rate,
            funding_rate=funding_rate,
            slippage_bps=slippage_bps,
            operator_time_minutes=operator_time_minutes,
            operator_hourly_cost_usd=operator_hourly_cost_usd,
            source_refs=[
                _artifact_ref(pair.outcome_path, pair.outcome.schema_version) for pair in pairs
            ],
            known_gaps=selection_gaps,
            producer_command=PRE_ACTUAL_CASH_PACK_PRODUCER,
        )
        guard = build_bias_guard(
            rows=rows.rows,
            created_at=created,
            min_events_for_pbo=min_events_for_pbo,
            fold_count=fold_count,
            source_refs=[
                {
                    "path": "tournament_rows_v2_summary.json",
                    "sha256": rows.artifact_id,
                    "schema_version": rows.schema_version,
                }
            ],
            known_gaps=rows.known_gaps,
            producer_command=PRE_ACTUAL_CASH_PACK_PRODUCER,
        )
    source_matrix = _source_availability_matrix(source_artifacts)
    known_gaps = _unique([*inventory.known_gaps, *selection_gaps, *per_event_gaps])
    known_gaps_by_source = _known_gaps_by_source(source_artifacts, known_gaps)
    replay_summary = _replay_slice_summary(replay_artifacts)
    feature_summary = _feature_pack_summary(feature_artifacts)
    edge_summary = _edge_score_summary(edge_artifacts)
    tournament_summary = _tournament_summary(rows)
    bias_summary = _bias_guard_summary(guard)
    summaries = {
        "events_summary": _events_summary(
            pairs=pairs,
            raw_event_count=len(events_by_id),
            min_events=min_events,
            selection_gaps=selection_gaps,
        ),
        "outcomes_summary": _outcomes_summary(
            pairs=pairs,
            raw_matured_outcome_count=sum(len(items) for items in outcomes_by_event.values()),
            min_events=min_events,
            selection_gaps=selection_gaps,
        ),
        "source_availability_matrix": source_matrix,
        "known_gaps_by_source": known_gaps_by_source,
        "replay_slice_summary": replay_summary,
        "feature_pack_summary": feature_summary,
        "edge_score_summary": edge_summary,
        "tournament_rows_v2_summary": tournament_summary,
        "bias_guard_summary": bias_summary,
    }
    decision, reason_codes = _decide(
        event_count=len(pairs),
        outcome_count=len(pairs),
        min_events=min_events,
        source_matrix=source_matrix,
        feature_summary=feature_summary,
        edge_summary=edge_summary,
        tournament_summary=tournament_summary,
        bias_guard_summary=bias_summary,
    )
    run_manifest_summary = _run_manifest_summary(
        pairs=pairs,
        records=run_manifest_records,
        computed_known_gaps=known_gaps,
        reason_codes=reason_codes,
    )
    run_manifest_summary["artifact_count"] = len(summaries) + 2
    summaries["events_summary"]["run_manifest"] = run_manifest_summary
    summaries["known_gaps_by_source"]["run_manifest"] = run_manifest_summary
    artifact = _decision_artifact(
        created=created,
        pairs=pairs,
        decision=decision,
        reason_codes=reason_codes,
        source_gap_summary=known_gaps_by_source,
        edge_summary=edge_summary,
        tournament_summary=tournament_summary,
        bias_guard_summary=bias_summary,
    )
    return summaries, artifact, render_pre_actual_cash_decision_markdown(artifact)


def write_pre_actual_cash_evidence_pack(
    *,
    data_dir: Path,
    out_dir: Path,
    created_at: datetime | str,
    notional_usd: Decimal,
    min_events: int = 10,
    min_events_for_pbo: int = 30,
    fold_count: int = 0,
    fee_rate: Decimal = Decimal("0.0006"),
    funding_rate: Decimal = Decimal("0"),
    slippage_bps: Decimal = Decimal("0"),
    operator_time_minutes: Decimal = Decimal("0"),
    operator_hourly_cost_usd: Decimal = Decimal("0"),
) -> dict[str, Path]:
    summaries, decision, decision_md = build_pre_actual_cash_evidence_pack(
        data_dir=data_dir,
        created_at=created_at,
        notional_usd=notional_usd,
        min_events=min_events,
        min_events_for_pbo=min_events_for_pbo,
        fold_count=fold_count,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        operator_time_minutes=operator_time_minutes,
        operator_hourly_cost_usd=operator_hourly_cost_usd,
    )
    paths: dict[str, Path] = {}
    for name in PRE_ACTUAL_CASH_SUMMARY_ARTIFACT_NAMES:
        path = out_dir / f"{name}.json"
        write_json_artifact(path, summaries[name])
        paths[f"{name}.json"] = path
    decision_json = out_dir / "decision.json"
    write_json_artifact(decision_json, decision.model_dump(mode="json"))
    paths["decision.json"] = decision_json
    decision_markdown = out_dir / "decision.md"
    write_text_artifact(decision_markdown, decision_md)
    paths["decision.md"] = decision_markdown
    return paths


def _next_action(decision: PreActualCashDecisionName) -> str:
    if decision == "KILL":
        return "同じ event definition では actual cash へ進めず、候補を棄却する。"
    if decision == "REVISE_EVENT_DEFINITION":
        return "event id、cutoff、feature baseline、outcome window、比較 action set を見直す。"
    if decision == "COLLECT_MORE_SOURCES":
        return (
            "trades、books、ticker、funding、replay、cost inputs など不足 source を追加収集する。"
        )
    return "今は actual cash を実装せず、将来の actual cash evidence loop まで候補を保留する。"


def render_pre_actual_cash_decision_markdown(
    artifact: PreActualCashDecisionArtifact,
) -> str:
    source_gap_sources = artifact.source_gap_summary.get("sources", {})
    main_source_gaps = [
        f"{source}:{payload.get('missing_event_count', 0)}"
        for source, payload in sorted(source_gap_sources.items())
        if int(payload.get("missing_event_count", 0)) > 0
    ]
    selected_counts = artifact.edge_summary.get("selected_action_counts", {})
    return "\n".join(
        [
            "# Pre Actual Cash Evidence Decision",
            "",
            f"- created_at: `{serialize_utc_z(artifact.created_at)}`",
            f"- event_count: `{artifact.event_count}`",
            f"- outcome_count: `{artifact.outcome_count}`",
            f"- main_source_gaps: `{', '.join(main_source_gaps) if main_source_gaps else 'none'}`",
            f"- selected_action_counts: `{selected_counts}`",
            f"- leader_action: `{artifact.tournament_summary.get('leader_action')}`",
            f"- leader_beats_no_trade: `{artifact.tournament_summary.get('leader_beats_no_trade')}`",
            f"- bias_guard_status: `{artifact.bias_guard_summary.get('guard_status')}`",
            f"- pbo_status: `{artifact.bias_guard_summary.get('pbo_status')}`",
            "- actual_cash_used: `false`",
            "- profit_proven: `false`",
            "- actual_cash_readiness_claimed: `false`",
            "- tiny_live_readiness_claimed: `false`",
            "- live_trading_readiness_claimed: `false`",
            f"- decision: `{artifact.decision}`",
            f"- reason_codes: `{', '.join(artifact.reason_codes)}`",
            f"- next_action: {_next_action(artifact.decision)}",
            "",
            "This pack is a pre-actual-cash candidate handling gate only. It does not prove profit, actual cash readiness, tiny-live readiness, or live trading readiness.",
        ]
    )
