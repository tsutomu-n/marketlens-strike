from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bias_guards import CryptoPerpBiasGuard, build_bias_guard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.edge_scorer import CryptoPerpEdgeScore, build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import CryptoPerpFeaturePack, build_feature_pack
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.source_availability import (
    CryptoPerpSourceAvailability,
    SourceAvailabilityStatus,
    build_source_availability,
)
from sis.crypto_perp.tournament_rows import (
    CostAwareTournamentRow,
    CryptoPerpTournamentRowsV2,
    build_cost_aware_tournament_rows,
)


BACKTEST_CANDIDATE_PACK_SCHEMA_VERSION = "crypto_perp_backtest_candidate_pack.v1"
BACKTEST_CANDIDATE_PACK_PRODUCER = "crypto-perp-backtest-candidate-pack"
BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES = (
    "signal_rows.jsonl",
    "data_availability_ledger.json",
    "execution_assumptions.json",
    "no_lookahead_report.json",
    "backtest_result.json",
    "stress_result.json",
    "regime_split_result.json",
    "rolling_stability_result.json",
    "decision.json",
    "decision.md",
)
BacktestCandidateDecisionName = Literal[
    "BACKTEST_REJECT",
    "BACKTEST_REVISE",
    "BACKTEST_COLLECT_MORE_DATA",
    "BACKTEST_CANDIDATE_HOLD",
]
JsonModelT = TypeVar("JsonModelT", bound=BaseModel)


class CryptoPerpBacktestCandidatePackDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_backtest_candidate_pack.v1"] = (
        BACKTEST_CANDIDATE_PACK_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    pack_id: str
    decision: BacktestCandidateDecisionName
    reason_codes: list[str]
    event_count: int = Field(ge=0)
    outcome_count: int = Field(ge=0)
    artifact_paths: dict[str, str]
    summary: dict[str, Any]
    non_goal_flags: dict[str, bool]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class BacktestCandidatePackResult:
    paths: dict[str, Path]
    decision: CryptoPerpBacktestCandidatePackDecision


@dataclass(frozen=True)
class _EventOutcomePair:
    event_path: Path
    event: CryptoPerpEvent
    outcome_path: Path
    outcome: CryptoPerpOutcome


@dataclass(frozen=True)
class _ArtifactOrigin:
    origin: Literal["existing", "recomputed_minimal"]
    path: str | None
    note: str


@dataclass(frozen=True)
class _PerEventArtifacts:
    source_availability: CryptoPerpSourceAvailability
    source_origin: _ArtifactOrigin
    feature_pack: CryptoPerpFeaturePack
    feature_origin: _ArtifactOrigin
    edge_score: CryptoPerpEdgeScore
    edge_origin: _ArtifactOrigin


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _json_ready(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _artifact_ref(path: Path, schema_version: str | None = None) -> dict[str, str]:
    ref = {"path": path.as_posix(), "sha256": _sha256_file(path)}
    if schema_version:
        ref["schema_version"] = schema_version
    return ref


def _load_schema_artifacts(
    data_dir: Path,
    schema_version: str,
    model_type: type[JsonModelT],
) -> list[tuple[Path, JsonModelT]]:
    artifacts: list[tuple[Path, JsonModelT]] = []
    if not data_dir.exists():
        return artifacts
    for path in sorted(data_dir.rglob("*.json")):
        try:
            payload = _read_json_object(path)
        except Exception:
            continue
        if payload.get("schema_version") != schema_version:
            continue
        artifacts.append((path, model_type.model_validate(payload)))
    return artifacts


def _select_pairs(data_dir: Path) -> tuple[list[_EventOutcomePair], list[str]]:
    event_records = _load_schema_artifacts(data_dir, "crypto_perp_event.v1", CryptoPerpEvent)
    outcome_records = _load_schema_artifacts(data_dir, "crypto_perp_outcome.v1", CryptoPerpOutcome)
    events: dict[str, tuple[Path, CryptoPerpEvent]] = {}
    outcomes_by_event: dict[str, list[tuple[Path, CryptoPerpOutcome]]] = {}
    gaps: list[str] = []
    for path, event in event_records:
        events.setdefault(event.event_id, (path, event))
    for path, outcome in outcome_records:
        if not any(horizon.matured for horizon in outcome.horizons):
            continue
        outcomes_by_event.setdefault(outcome.event_id, []).append((path, outcome))
    pairs: list[_EventOutcomePair] = []
    for event_id, (event_path, event) in sorted(events.items()):
        outcomes = sorted(outcomes_by_event.get(event_id, []), key=lambda item: item[0].as_posix())
        if not outcomes:
            gaps.append("EVENT_WITHOUT_MATURED_OUTCOME")
            continue
        if len(outcomes) > 1:
            gaps.append("MULTIPLE_MATURED_OUTCOMES_FOR_EVENT_COLLAPSED_TO_FIRST")
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
        if event_id not in events:
            gaps.append("MATURED_OUTCOME_WITHOUT_EVENT")
    pairs.sort(key=lambda pair: (pair.event.information_cutoff_at, pair.event.event_id))
    return pairs, list(dict.fromkeys(gaps))


def _existing_by_event(
    data_dir: Path,
    schema_version: str,
    model_type: type[JsonModelT],
) -> dict[str, tuple[Path, JsonModelT]]:
    selected: dict[str, tuple[Path, JsonModelT]] = {}
    for path, artifact in _load_schema_artifacts(data_dir, schema_version, model_type):
        event_id = getattr(artifact, "event_id", None)
        if isinstance(event_id, str) and event_id and event_id not in selected:
            selected[event_id] = (path, artifact)
    return selected


def _existing_rows(
    data_dir: Path,
    event_ids: Sequence[str],
) -> tuple[Path, CryptoPerpTournamentRowsV2] | None:
    expected = sorted(set(event_ids))
    for path, rows in _load_schema_artifacts(
        data_dir, "crypto_perp_tournament_rows.v2", CryptoPerpTournamentRowsV2
    ):
        if sorted(rows.event_set) == expected:
            return path, rows
    return None


def _existing_bias_guard(
    data_dir: Path,
    event_count: int,
) -> tuple[Path, CryptoPerpBiasGuard] | None:
    for path, guard in _load_schema_artifacts(
        data_dir, "crypto_perp_bias_guard.v1", CryptoPerpBiasGuard
    ):
        if guard.event_count == event_count:
            return path, guard
    return None


def _build_per_event_artifacts(
    *,
    data_dir: Path,
    pairs: Sequence[_EventOutcomePair],
    created: datetime,
) -> list[_PerEventArtifacts]:
    sources = _existing_by_event(
        data_dir, "crypto_perp_source_availability.v1", CryptoPerpSourceAvailability
    )
    features = _existing_by_event(data_dir, "crypto_perp_feature_pack.v1", CryptoPerpFeaturePack)
    edges = _existing_by_event(data_dir, "crypto_perp_edge_score.v1", CryptoPerpEdgeScore)
    artifacts: list[_PerEventArtifacts] = []
    for pair in pairs:
        source_record = sources.get(pair.event.event_id)
        if source_record is None:
            source = build_source_availability(
                event=pair.event,
                created_at=created,
                available_sources={"outcome": True},
                row_counts={"outcome": 1},
                source_refs=[_artifact_ref(pair.outcome_path, pair.outcome.schema_version)],
                producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
            )
            source_origin = _ArtifactOrigin(
                origin="recomputed_minimal",
                path=None,
                note="source availability missing; recomputed from event and outcome only",
            )
        else:
            source_path, source = source_record
            source_origin = _ArtifactOrigin("existing", source_path.as_posix(), "matched_event_id")

        feature_record = features.get(pair.event.event_id)
        if feature_record is None:
            feature = build_feature_pack(
                event=pair.event,
                source_availability=source,
                created_at=created,
                producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
            )
            feature_origin = _ArtifactOrigin(
                "recomputed_minimal",
                None,
                "feature pack missing; recomputed from event and source availability",
            )
        else:
            feature_path, feature = feature_record
            feature_origin = _ArtifactOrigin(
                "existing", feature_path.as_posix(), "matched_event_id"
            )

        edge_record = edges.get(pair.event.event_id)
        if edge_record is None:
            edge = build_edge_score(
                feature_pack=feature,
                source_availability=source,
                created_at=created,
                producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
            )
            edge_origin = _ArtifactOrigin(
                "recomputed_minimal",
                None,
                "edge score missing; recomputed from feature pack and source availability",
            )
        else:
            edge_path, edge = edge_record
            edge_origin = _ArtifactOrigin("existing", edge_path.as_posix(), "matched_event_id")
        artifacts.append(
            _PerEventArtifacts(
                source_availability=source,
                source_origin=source_origin,
                feature_pack=feature,
                feature_origin=feature_origin,
                edge_score=edge,
                edge_origin=edge_origin,
            )
        )
    return artifacts


def _build_rows_and_guard(
    *,
    data_dir: Path,
    pairs: Sequence[_EventOutcomePair],
    created: datetime,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    min_events_for_stability: int,
    fold_count: int,
    known_gaps: Sequence[str],
) -> tuple[
    CryptoPerpTournamentRowsV2 | None, _ArtifactOrigin, CryptoPerpBiasGuard | None, _ArtifactOrigin
]:
    if not pairs:
        return (
            None,
            _ArtifactOrigin("recomputed_minimal", None, "no event/outcome pairs"),
            None,
            _ArtifactOrigin("recomputed_minimal", None, "no event/outcome pairs"),
        )
    event_ids = [pair.event.event_id for pair in pairs]
    row_record = _existing_rows(data_dir, event_ids)
    if row_record is None:
        rows = build_cost_aware_tournament_rows(
            outcomes=[pair.outcome for pair in pairs],
            created_at=created,
            notional_usd=notional_usd,
            fee_rate=fee_rate,
            funding_rate=funding_rate,
            slippage_bps=slippage_bps,
            source_refs=[
                _artifact_ref(pair.outcome_path, pair.outcome.schema_version) for pair in pairs
            ],
            known_gaps=known_gaps,
            producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
        )
        rows_origin = _ArtifactOrigin(
            "recomputed_minimal",
            None,
            "matching tournament rows missing; recomputed from matured outcomes",
        )
    else:
        rows_path, rows = row_record
        rows_origin = _ArtifactOrigin("existing", rows_path.as_posix(), "matched_event_set")

    guard_record = _existing_bias_guard(data_dir, len(set(event_ids)))
    if guard_record is None:
        guard = build_bias_guard(
            rows=rows.rows,
            created_at=created,
            min_events_for_pbo=min_events_for_stability,
            fold_count=fold_count,
            source_refs=[
                {
                    "path": rows_origin.path or "backtest_candidate_pack:tournament_rows_v2",
                    "sha256": rows.artifact_id,
                    "schema_version": rows.schema_version,
                }
            ],
            known_gaps=rows.known_gaps,
            producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
        )
        guard_origin = _ArtifactOrigin(
            "recomputed_minimal",
            None,
            "matching bias guard missing; recomputed from tournament rows",
        )
    else:
        guard_path, guard = guard_record
        guard_origin = _ArtifactOrigin("existing", guard_path.as_posix(), "matched_event_count")
    return rows, rows_origin, guard, guard_origin


def _score(edge: CryptoPerpEdgeScore) -> str:
    first = sorted(edge.action_scores, key=lambda row: row.rank)[0] if edge.action_scores else None
    return str(first.score) if first is not None else "0"


def _signal_rows(
    *,
    pairs: Sequence[_EventOutcomePair],
    artifacts: Sequence[_PerEventArtifacts],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pair, artifact in zip(pairs, artifacts, strict=True):
        edge = artifact.edge_score
        selected = edge.selected_action
        no_trade_reason = list(edge.why_no_trade)
        if selected == "UNKNOWN":
            no_trade_reason.append("SELECTED_ACTION_UNKNOWN")
        if selected == "NO_TRADE":
            no_trade_reason.append("NO_TRADE_SELECTED")
        rows.append(
            {
                "timestamp": serialize_utc_z(pair.event.information_cutoff_at),
                "symbol": pair.event.canonical_symbol,
                "event_id": pair.event.event_id,
                "outcome_id": pair.outcome.outcome_id,
                "information_cutoff_at": serialize_utc_z(pair.event.information_cutoff_at),
                "source_availability_id": artifact.source_availability.artifact_id,
                "feature_pack_id": artifact.feature_pack.feature_pack_id,
                "edge_score_id": edge.edge_score_id,
                "selected_action": selected,
                "signal_score": _score(edge),
                "entry_allowed": selected not in {"UNKNOWN", "NO_TRADE"},
                "no_trade_reason": list(dict.fromkeys(no_trade_reason)),
                "artifact_origin": {
                    "source_availability": artifact.source_origin.__dict__,
                    "feature_pack": artifact.feature_origin.__dict__,
                    "edge_score": artifact.edge_origin.__dict__,
                },
            }
        )
    return rows


def _metadata_available_at(
    status: SourceAvailabilityStatus,
    fallback: datetime,
) -> tuple[datetime | None, str]:
    raw_ms = status.metadata.get("coverage_end_ms")
    if isinstance(raw_ms, int | float) and not isinstance(raw_ms, bool):
        return datetime.fromtimestamp(raw_ms / 1000, tz=UTC), "metadata.coverage_end_ms"
    return fallback if status.available else None, "information_cutoff_fallback"


def _source_status_by_id(
    source: CryptoPerpSourceAvailability,
) -> dict[str, SourceAvailabilityStatus]:
    return {status.source_id: status for status in source.source_statuses}


def _availability_ledger(
    *,
    pairs: Sequence[_EventOutcomePair],
    artifacts: Sequence[_PerEventArtifacts],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    critical_sources = {"event", "bars", "ticker", "funding"}
    signal_sources = {"event", "bars", "ticker", "funding", "trades", "books", "replay"}
    future_signal_source_count = 0
    critical_missing_count = 0
    for pair, artifact in zip(pairs, artifacts, strict=True):
        cutoff = pair.event.information_cutoff_at
        statuses = _source_status_by_id(artifact.source_availability)
        for source_type, status in sorted(statuses.items()):
            usage_role = "evaluation_label" if source_type == "outcome" else "signal_input"
            if source_type == "outcome":
                is_available = True
                available_at = pair.outcome.settled_at
                used_at = pair.outcome.settled_at
                missing_reason = None
                row_count = 1
                available_at_policy = "outcome.settled_at"
            else:
                is_available = status.available
                available_at, available_at_policy = _metadata_available_at(status, cutoff)
                used_at = cutoff
                missing_reason = None if is_available else status.reason
                row_count = status.row_count
            if source_type in critical_sources and not is_available:
                critical_missing_count += 1
            future_signal_source = (
                source_type in signal_sources
                and is_available
                and available_at is not None
                and available_at > cutoff
            )
            future_signal_source_count += int(future_signal_source)
            staleness_seconds = (
                int((used_at - available_at).total_seconds())
                if available_at is not None and used_at >= available_at
                else None
            )
            rows.append(
                {
                    "timestamp": serialize_utc_z(cutoff),
                    "symbol": pair.event.canonical_symbol,
                    "event_id": pair.event.event_id,
                    "source_type": source_type,
                    "source_artifact_id": artifact.source_availability.artifact_id,
                    "available_at": serialize_utc_z(available_at) if available_at else None,
                    "used_at": serialize_utc_z(used_at),
                    "usage_role": usage_role,
                    "is_available": is_available,
                    "missing_reason": missing_reason,
                    "staleness_seconds": staleness_seconds,
                    "row_count": row_count,
                    "source_ref_count": len(status.source_refs),
                    "available_at_policy": available_at_policy,
                    "metadata": _json_ready(status.metadata),
                }
            )
    return {
        "schema_version": "crypto_perp_backtest_data_availability_ledger.v1",
        "summary": {
            "event_count": len(pairs),
            "row_count": len(rows),
            "critical_missing_count": critical_missing_count,
            "future_signal_source_count": future_signal_source_count,
            "network_used": False,
            "external_api_called": False,
        },
        "rows": rows,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _execution_assumptions(
    *,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    max_holding_minutes: int,
) -> dict[str, Any]:
    return {
        "schema_version": "crypto_perp_backtest_execution_assumptions.v1",
        "entry_price_rule": "next_5m_open_proxy_after_signal",
        "exit_price_rule": "matured_outcome_first_horizon_close_proxy",
        "fee_rate": str(fee_rate),
        "slippage_bps": str(slippage_bps),
        "funding_rate_assumption": str(funding_rate),
        "max_holding_minutes": max_holding_minutes,
        "position_size_usd": str(notional_usd),
        "no_fill_policy": "UNKNOWN blocks entry; NO_TRADE records zero exposure baseline",
        "zero_cost_forbidden": True,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _check_row(
    check_id: str, status: str, message: str, event_id: str | None = None
) -> dict[str, Any]:
    return {"check_id": check_id, "status": status, "message": message, "event_id": event_id}


def _no_lookahead_report(
    *,
    pairs: Sequence[_EventOutcomePair],
    artifacts: Sequence[_PerEventArtifacts],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    ledger_rows = cast(list[dict[str, Any]], ledger.get("rows", []))
    for pair, artifact in zip(pairs, artifacts, strict=True):
        cutoff = pair.event.information_cutoff_at
        entry_at = cutoff + timedelta(minutes=5)
        checks.append(
            _check_row(
                "signal_timestamp_before_entry_timestamp",
                "pass" if cutoff < entry_at else "fail",
                "signal timestamp must be before simulated entry timestamp",
                pair.event.event_id,
            )
        )
        checks.append(
            _check_row(
                "feature_used_at_not_after_signal",
                "pass" if artifact.feature_pack.information_cutoff_at <= cutoff else "fail",
                "feature pack cutoff must not be after signal timestamp",
                pair.event.event_id,
            )
        )
        checks.append(
            _check_row(
                "outcome_not_used_for_signal",
                "pass",
                "outcome is only used for backtest evaluation after signal generation",
                pair.event.event_id,
            )
        )
    for row in ledger_rows:
        if row.get("usage_role") != "signal_input" or not row.get("is_available"):
            continue
        available_at = ensure_utc_aware("available_at", row["available_at"])
        used_at = ensure_utc_aware("used_at", row["used_at"])
        checks.append(
            _check_row(
                "source_available_at_not_after_used_at",
                "pass" if available_at <= used_at else "fail",
                f"{row['source_type']} available_at must be <= used_at",
                cast(str, row.get("event_id")),
            )
        )
    critical_missing = int(cast(Mapping[str, Any], ledger["summary"])["critical_missing_count"])
    if critical_missing:
        checks.append(
            _check_row(
                "critical_signal_sources_available",
                "unverified",
                "one or more critical signal sources are missing; backtest must collect more data",
            )
        )
    checks.append(
        _check_row(
            "train_test_split_time_ordered",
            "pass",
            "no train/test optimization is performed in this deterministic candidate pack",
        )
    )
    counts = Counter(str(check["status"]) for check in checks)
    status = "fail" if counts.get("fail", 0) else "pass"
    return {
        "schema_version": "crypto_perp_backtest_no_lookahead_report.v1",
        "status": status,
        "summary": {
            "check_count": len(checks),
            "failed_count": counts.get("fail", 0),
            "unverified_count": counts.get("unverified", 0),
            "coverage_status": "unverified" if counts.get("unverified", 0) else "covered",
            "outcome_used_for_signal": False,
        },
        "checks": checks,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _row_by_event_action(
    rows: CryptoPerpTournamentRowsV2 | None,
) -> dict[tuple[str, str], CostAwareTournamentRow]:
    if rows is None:
        return {}
    return {(row.event_id, row.action): row for row in rows.rows}


def _drawdown(values: Sequence[Decimal]) -> Decimal:
    peak = Decimal("0")
    cumulative = Decimal("0")
    worst = Decimal("0")
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        worst = min(worst, cumulative - peak)
    return worst


def _simulation_results(
    *,
    signal_rows: Sequence[Mapping[str, Any]],
    rows: CryptoPerpTournamentRowsV2 | None,
    metric: Literal["cost_adjusted_cash_estimate_usd", "stress_cash_estimate_usd"],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    row_map = _row_by_event_action(rows)
    results: list[dict[str, Any]] = []
    returns: list[Decimal] = []
    for signal in signal_rows:
        event_id = str(signal["event_id"])
        selected = str(signal["selected_action"])
        source_row = row_map.get((event_id, selected))
        if selected == "UNKNOWN":
            result = Decimal("0")
            fill_status = "blocked_unknown_signal"
        elif selected == "NO_TRADE":
            result = Decimal("0")
            fill_status = "no_trade_baseline"
        elif source_row is None:
            result = Decimal("0")
            fill_status = "blocked_missing_action_row"
        else:
            result = getattr(source_row, metric)
            fill_status = "simulated"
        returns.append(result)
        results.append(
            {
                "event_id": event_id,
                "outcome_id": signal["outcome_id"],
                "selected_action": selected,
                "fill_status": fill_status,
                "result_usd": str(result),
                "metric": metric,
            }
        )
    executed = [row for row in results if row["fill_status"] == "simulated"]
    total = sum(returns, Decimal("0"))
    wins = sum(1 for row in executed if Decimal(str(row["result_usd"])) > 0)
    summary = {
        "event_count": len(signal_rows),
        "executed_trade_count": len(executed),
        "no_trade_count": sum(1 for row in results if row["fill_status"] == "no_trade_baseline"),
        "unknown_count": sum(
            1 for row in results if row["fill_status"] == "blocked_unknown_signal"
        ),
        "blocked_missing_action_row_count": sum(
            1 for row in results if row["fill_status"] == "blocked_missing_action_row"
        ),
        "total_result_usd": str(total),
        "average_result_usd": str(total / Decimal(len(results))) if results else "0",
        "win_rate": str(Decimal(wins) / Decimal(len(executed))) if executed else None,
        "max_drawdown_usd": str(_drawdown(returns)),
        "beats_no_trade": total > 0,
    }
    return results, summary


def _backtest_result(
    signal_rows: Sequence[Mapping[str, Any]],
    rows: CryptoPerpTournamentRowsV2 | None,
) -> dict[str, Any]:
    results, summary = _simulation_results(
        signal_rows=signal_rows,
        rows=rows,
        metric="cost_adjusted_cash_estimate_usd",
    )
    return {
        "schema_version": "crypto_perp_backtest_result.v1",
        "status": "complete",
        "summary": summary,
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _stress_result(
    signal_rows: Sequence[Mapping[str, Any]],
    rows: CryptoPerpTournamentRowsV2 | None,
) -> dict[str, Any]:
    results, summary = _simulation_results(
        signal_rows=signal_rows,
        rows=rows,
        metric="stress_cash_estimate_usd",
    )
    return {
        "schema_version": "crypto_perp_backtest_stress_result.v1",
        "status": "complete",
        "stress_kind": "row_level_conservative_cost_slippage",
        "summary": summary,
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _regime_split_result(
    *,
    pairs: Sequence[_EventOutcomePair],
    backtest_results: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    families = {pair.event.event_id: pair.event.event_family for pair in pairs}
    buckets: dict[str, list[Decimal]] = {}
    for result in backtest_results:
        family = families.get(str(result["event_id"]), "unknown")
        buckets.setdefault(family, []).append(Decimal(str(result["result_usd"])))
    regimes = [
        {
            "regime": regime,
            "event_count": len(values),
            "total_result_usd": str(sum(values, Decimal("0"))),
            "average_result_usd": str(sum(values, Decimal("0")) / Decimal(len(values)))
            if values
            else "0",
        }
        for regime, values in sorted(buckets.items())
    ]
    return {
        "schema_version": "crypto_perp_backtest_regime_split_result.v1",
        "status": "complete" if regimes else "sample_insufficient",
        "summary": {"regime_count": len(regimes), "event_count": len(pairs)},
        "regimes": regimes,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _rolling_stability_result(
    backtest_results: Sequence[Mapping[str, Any]],
    min_events_for_stability: int,
) -> dict[str, Any]:
    cumulative = Decimal("0")
    points: list[dict[str, Any]] = []
    for index, result in enumerate(backtest_results, start=1):
        cumulative += Decimal(str(result["result_usd"]))
        points.append(
            {
                "index": index,
                "event_id": result["event_id"],
                "cumulative_result_usd": str(cumulative),
            }
        )
    status = (
        "complete" if len(backtest_results) >= min_events_for_stability else "sample_insufficient"
    )
    return {
        "schema_version": "crypto_perp_backtest_rolling_stability_result.v1",
        "status": status,
        "summary": {
            "event_count": len(backtest_results),
            "min_events_for_stability": min_events_for_stability,
            "final_cumulative_result_usd": str(cumulative),
            "min_cumulative_result_usd": min(
                (Decimal(str(point["cumulative_result_usd"])) for point in points),
                default=Decimal("0"),
            ),
            "max_cumulative_result_usd": max(
                (Decimal(str(point["cumulative_result_usd"])) for point in points),
                default=Decimal("0"),
            ),
        },
        "points": points,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


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
        "backtest_promote_to_live_available": False,
        "ml_or_llm_trade_decision_used": False,
    }


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _decide(
    *,
    event_count: int,
    outcome_count: int,
    min_events: int,
    ledger: Mapping[str, Any],
    no_lookahead: Mapping[str, Any],
    backtest: Mapping[str, Any],
    stress: Mapping[str, Any],
    rolling: Mapping[str, Any],
    guard: CryptoPerpBiasGuard | None,
) -> tuple[BacktestCandidateDecisionName, list[str]]:
    reasons: list[str] = []
    if event_count == 0 or outcome_count == 0:
        return "BACKTEST_COLLECT_MORE_DATA", ["NO_EVENT_OUTCOME_PAIRS"]
    if event_count < min_events or outcome_count < min_events:
        reasons.append("MIN_EVENT_OUTCOME_SAMPLE_NOT_MET")
    if int(cast(Mapping[str, Any], ledger["summary"])["critical_missing_count"]) > 0:
        reasons.append("CRITICAL_SIGNAL_SOURCE_MISSING")
    nl_summary = cast(Mapping[str, Any], no_lookahead["summary"])
    if int(nl_summary["failed_count"]) > 0:
        reasons.append("NO_LOOKAHEAD_FAILED")
        return "BACKTEST_REJECT", _unique(reasons)
    if int(nl_summary["unverified_count"]) > 0:
        reasons.append("NO_LOOKAHEAD_UNVERIFIED")
    bt_summary = cast(Mapping[str, Any], backtest["summary"])
    stress_summary = cast(Mapping[str, Any], stress["summary"])
    if int(bt_summary["unknown_count"]) > 0 and "CRITICAL_SIGNAL_SOURCE_MISSING" in reasons:
        reasons.append("SELECTED_ACTION_UNKNOWN_DUE_TO_MISSING_SOURCE")
    elif int(bt_summary["unknown_count"]) > 0:
        reasons.append("SELECTED_ACTION_UNKNOWN")
    if guard is None:
        reasons.append("BIAS_GUARD_NOT_RUN")
    elif guard.pbo_status == "NOT_ESTIMABLE":
        reasons.append("PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT")
    if rolling["status"] == "sample_insufficient":
        reasons.append("ROLLING_STABILITY_SAMPLE_INSUFFICIENT")
    collection_reasons = {
        "MIN_EVENT_OUTCOME_SAMPLE_NOT_MET",
        "CRITICAL_SIGNAL_SOURCE_MISSING",
        "NO_LOOKAHEAD_UNVERIFIED",
        "SELECTED_ACTION_UNKNOWN_DUE_TO_MISSING_SOURCE",
        "PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT",
        "ROLLING_STABILITY_SAMPLE_INSUFFICIENT",
    }
    if collection_reasons.intersection(reasons):
        return "BACKTEST_COLLECT_MORE_DATA", _unique(reasons)
    if int(bt_summary["executed_trade_count"]) == 0 or int(bt_summary["unknown_count"]) > 0:
        reasons.append("NO_EXECUTABLE_SIGNAL_ROWS")
        return "BACKTEST_REVISE", _unique(reasons)
    total = Decimal(str(bt_summary["total_result_usd"]))
    stress_total = Decimal(str(stress_summary["total_result_usd"]))
    if total <= 0:
        reasons.append("NO_TRADE_NOT_BEATEN_AFTER_COST")
    if stress_total <= 0:
        reasons.append("STRESS_RESULT_NOT_POSITIVE")
    if Decimal(str(bt_summary["max_drawdown_usd"])) < total * Decimal("-1"):
        reasons.append("DRAWDOWN_TOO_LARGE_FOR_TOTAL_RESULT")
    if reasons:
        return "BACKTEST_REJECT", _unique(reasons)
    reasons.append("SIMULATION_CANDIDATE_REMAINS_AFTER_LOCAL_BACKTEST")
    reasons.append("ACTUAL_CASH_PAPER_TINY_LIVE_NOT_IN_SCOPE")
    return "BACKTEST_CANDIDATE_HOLD", reasons


def _decision_markdown(artifact: CryptoPerpBacktestCandidatePackDecision) -> str:
    return "\n".join(
        [
            "# Crypto Perp Backtest Candidate Pack Decision",
            "",
            f"- created_at: `{serialize_utc_z(artifact.created_at)}`",
            f"- pack_id: `{artifact.pack_id}`",
            f"- event_count: `{artifact.event_count}`",
            f"- outcome_count: `{artifact.outcome_count}`",
            f"- decision: `{artifact.decision}`",
            f"- reason_codes: `{', '.join(artifact.reason_codes)}`",
            "- actual_cash_used: `false`",
            "- profit_proven: `false`",
            "- permits_live_order: `false`",
            "- live_trading_readiness_claimed: `false`",
            "",
            "This pack is timestamp-safe simulation evidence only. It does not prove profit, actual-cash readiness, tiny-live readiness, or live trading readiness.",
        ]
    )


def _validate_assumptions(
    *,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    min_events: int,
    min_events_for_stability: int,
    fold_count: int,
    max_holding_minutes: int,
) -> None:
    if notional_usd <= 0:
        raise ValueError("notional_usd must be positive")
    if fee_rate <= 0:
        raise ValueError("fee_rate must be positive; zero-cost backtest is forbidden")
    if funding_rate < 0:
        raise ValueError("funding_rate must be non-negative")
    if slippage_bps <= 0:
        raise ValueError("slippage_bps must be positive; zero-cost backtest is forbidden")
    if min_events <= 0:
        raise ValueError("min_events must be positive")
    if min_events_for_stability <= 0:
        raise ValueError("min_events_for_stability must be positive")
    if fold_count < 0:
        raise ValueError("fold_count must be non-negative")
    if max_holding_minutes <= 0:
        raise ValueError("max_holding_minutes must be positive")


def build_crypto_perp_backtest_candidate_pack(
    *,
    data_dir: Path,
    out_dir: Path,
    created_at: datetime | str,
    notional_usd: Decimal,
    min_events: int = 10,
    min_events_for_stability: int = 30,
    fold_count: int = 0,
    fee_rate: Decimal = Decimal("0.0006"),
    funding_rate: Decimal = Decimal("0.0001"),
    slippage_bps: Decimal = Decimal("2"),
    max_holding_minutes: int = 60,
) -> BacktestCandidatePackResult:
    _validate_assumptions(
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        min_events=min_events,
        min_events_for_stability=min_events_for_stability,
        fold_count=fold_count,
        max_holding_minutes=max_holding_minutes,
    )
    created = ensure_utc_aware("created_at", created_at)
    pairs, selection_gaps = _select_pairs(data_dir)
    per_event = _build_per_event_artifacts(data_dir=data_dir, pairs=pairs, created=created)
    rows, rows_origin, guard, guard_origin = _build_rows_and_guard(
        data_dir=data_dir,
        pairs=pairs,
        created=created,
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        min_events_for_stability=min_events_for_stability,
        fold_count=fold_count,
        known_gaps=selection_gaps,
    )
    signals = _signal_rows(pairs=pairs, artifacts=per_event)
    ledger = _availability_ledger(pairs=pairs, artifacts=per_event)
    assumptions = _execution_assumptions(
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        max_holding_minutes=max_holding_minutes,
    )
    no_lookahead = _no_lookahead_report(pairs=pairs, artifacts=per_event, ledger=ledger)
    backtest = _backtest_result(signals, rows)
    stress = _stress_result(signals, rows)
    regime = _regime_split_result(
        pairs=pairs,
        backtest_results=cast(list[dict[str, Any]], backtest["results"]),
    )
    rolling = _rolling_stability_result(
        cast(list[dict[str, Any]], backtest["results"]),
        min_events_for_stability,
    )
    decision, reason_codes = _decide(
        event_count=len(pairs),
        outcome_count=len(pairs),
        min_events=min_events,
        ledger=ledger,
        no_lookahead=no_lookahead,
        backtest=backtest,
        stress=stress,
        rolling=rolling,
        guard=guard,
    )
    artifact_paths = {
        name: (out_dir / name).as_posix() for name in BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES
    }
    source_refs = [_artifact_ref(pair.event_path, pair.event.schema_version) for pair in pairs] + [
        _artifact_ref(pair.outcome_path, pair.outcome.schema_version) for pair in pairs
    ]
    summary = {
        "signal_row_count": len(signals),
        "selected_action_counts": dict(Counter(str(row["selected_action"]) for row in signals)),
        "data_availability": ledger["summary"],
        "no_lookahead": no_lookahead["summary"],
        "backtest": backtest["summary"],
        "stress": stress["summary"],
        "regime_split": regime["summary"],
        "rolling_stability": rolling["summary"],
        "selection_gaps": selection_gaps,
        "tournament_rows_origin": rows_origin.__dict__,
        "bias_guard_origin": guard_origin.__dict__,
        "bias_guard_status": guard.guard_status if guard else "NOT_RUN",
        "pbo_status": guard.pbo_status if guard else "NOT_RUN",
    }
    pack_id = stable_hash(
        [
            "crypto-perp-backtest-candidate-pack",
            serialize_utc_z(created),
            summary,
            decision,
            reason_codes,
        ]
    )
    decision_artifact = CryptoPerpBacktestCandidatePackDecision(
        artifact_id=stable_hash(["crypto-perp-backtest-candidate-pack-decision", pack_id]),
        created_at=created,
        producer=CryptoPerpProducer(command=BACKTEST_CANDIDATE_PACK_PRODUCER),
        source_refs=source_refs,
        pack_id=pack_id,
        decision=decision,
        reason_codes=reason_codes,
        event_count=len(pairs),
        outcome_count=len(pairs),
        artifact_paths=artifact_paths,
        summary=_json_ready(summary),
        non_goal_flags=_non_goal_flags(),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    signal_path = out_dir / "signal_rows.jsonl"
    signal_path.write_text(
        "".join(json.dumps(_json_ready(row), ensure_ascii=False) + "\n" for row in signals),
        encoding="utf-8",
    )
    paths["signal_rows.jsonl"] = signal_path
    payloads = {
        "data_availability_ledger.json": ledger,
        "execution_assumptions.json": assumptions,
        "no_lookahead_report.json": no_lookahead,
        "backtest_result.json": backtest,
        "stress_result.json": stress,
        "regime_split_result.json": regime,
        "rolling_stability_result.json": rolling,
        "decision.json": decision_artifact.model_dump(mode="json"),
    }
    for name, payload in payloads.items():
        path = out_dir / name
        write_json_artifact(path, _json_ready(payload))
        paths[name] = path
    decision_md_path = out_dir / "decision.md"
    write_text_artifact(decision_md_path, _decision_markdown(decision_artifact))
    paths["decision.md"] = decision_md_path
    return BacktestCandidatePackResult(paths=paths, decision=decision_artifact)
