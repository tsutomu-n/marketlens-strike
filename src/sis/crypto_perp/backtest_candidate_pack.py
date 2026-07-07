from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any, TypeVar, cast

from pydantic import BaseModel

from sis.crypto_perp.backtest_candidate_pack_models import (
    BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES,
    BACKTEST_CANDIDATE_PACK_PRODUCER,
    BACKTEST_CANDIDATE_PACK_SCHEMA_VERSION,
    BacktestCandidatePackResult,
    CryptoPerpBacktestCandidatePackDecision,
    _ArtifactOrigin,
    _EventOutcomePair,
    _PerEventArtifacts,
)
from sis.crypto_perp.backtest_candidate_pack_reports import (
    build_availability_ledger,
    build_backtest_result,
    build_execution_assumptions,
    build_no_lookahead_report,
    build_regime_split_result,
    build_rolling_stability_result,
    build_signal_rows,
    build_stress_result,
    decide_backtest_candidate,
    decision_markdown,
    non_goal_flags,
    validate_backtest_assumptions,
)
from sis.crypto_perp.bias_guards import CryptoPerpBiasGuard, build_bias_guard
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.cost_model import (
    CRYPTO_PERP_PROJECT_FUNDING_RATE,
    CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
    CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
)
from sis.crypto_perp.edge_scorer import CryptoPerpEdgeScore, build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import CryptoPerpFeaturePack, build_feature_pack
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.source_availability import (
    CryptoPerpSourceAvailability,
    build_source_availability,
)
from sis.crypto_perp.tournament_rows import (
    CryptoPerpTournamentRowsV2,
    build_cost_aware_tournament_rows,
)


__all__ = [
    "BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES",
    "BACKTEST_CANDIDATE_PACK_PRODUCER",
    "BACKTEST_CANDIDATE_PACK_SCHEMA_VERSION",
    "BacktestCandidatePackResult",
    "CryptoPerpBacktestCandidatePackDecision",
    "build_crypto_perp_backtest_candidate_pack",
]

JsonModelT = TypeVar("JsonModelT", bound=BaseModel)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _json_ready(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _int_from_mapping(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key, 0)
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _evidence_grade_summary(
    *,
    per_event: Sequence[_PerEventArtifacts],
    ledger: Mapping[str, Any],
    backtest: Mapping[str, Any],
    rows_origin: _ArtifactOrigin,
    guard_origin: _ArtifactOrigin,
) -> dict[str, Any]:
    """Build a top-level reality marker for the evidence strength of the pack.

    This intentionally does not change candidate decisions. It exists so operators do not
    confuse generated artifacts, recomputed minimal artifacts, or local simulation rows
    with actual cash or live-readiness evidence.
    """
    origin_counts: Counter[str] = Counter()
    for artifact in per_event:
        origin_counts[f"source_availability:{artifact.source_origin.origin}"] += 1
        origin_counts[f"feature_pack:{artifact.feature_origin.origin}"] += 1
        origin_counts[f"edge_score:{artifact.edge_origin.origin}"] += 1
    origin_counts[f"tournament_rows:{rows_origin.origin}"] += 1
    origin_counts[f"bias_guard:{guard_origin.origin}"] += 1

    ledger_summary_raw = ledger.get("summary", {})
    ledger_summary = ledger_summary_raw if isinstance(ledger_summary_raw, Mapping) else {}
    critical_missing_count = _int_from_mapping(ledger_summary, "critical_missing_count")
    future_signal_source_count = _int_from_mapping(ledger_summary, "future_signal_source_count")

    source_available_counts: Counter[str] = Counter()
    source_missing_counts: Counter[str] = Counter()
    ledger_rows = ledger.get("rows", [])
    if isinstance(ledger_rows, list):
        for raw_row in ledger_rows:
            if not isinstance(raw_row, Mapping):
                continue
            source_type = str(raw_row.get("source_type") or "unknown")
            if raw_row.get("is_available") is True:
                source_available_counts[source_type] += 1
            else:
                source_missing_counts[source_type] += 1

    backtest_summary_raw = backtest.get("summary", {})
    backtest_summary = backtest_summary_raw if isinstance(backtest_summary_raw, Mapping) else {}
    simulated_trade_count = _int_from_mapping(backtest_summary, "executed_trade_count")

    recomputed_minimal_count = sum(
        count for key, count in origin_counts.items() if key.endswith(":recomputed_minimal")
    )
    known_limits = [
        "LOCAL_SIMULATION_ONLY",
        "NOT_ACTUAL_CASH",
        "NOT_LIVE_READINESS",
    ]
    if recomputed_minimal_count:
        known_limits.append("RECOMPUTED_MINIMAL_ARTIFACTS_PRESENT")
    if any(source_missing_counts.get(source_id, 0) for source_id in ("books", "trades", "replay")):
        known_limits.append("BOOKS_TRADES_REPLAY_MISSING")
    if critical_missing_count:
        known_limits.append("CRITICAL_SIGNAL_SOURCE_MISSING")
    if simulated_trade_count == 0:
        known_limits.append("NO_SIMULATED_TRADE_ROWS")
    for artifact in per_event:
        for gap in artifact.source_availability.known_gaps:
            if gap.endswith("_NOT_REAL_MARKET_EVIDENCE"):
                known_limits.append(gap)

    if critical_missing_count or simulated_trade_count == 0:
        overall_grade = "insufficient_source_for_local_simulation"
        strongest_evidence_level = "incomplete_local_artifact"
    elif recomputed_minimal_count:
        overall_grade = "local_simulation_with_recomputed_minimal_artifacts"
        strongest_evidence_level = "recomputed_minimal_simulated_estimate"
    else:
        overall_grade = "local_simulation_from_existing_artifacts"
        strongest_evidence_level = "local_simulated_estimate"

    return {
        "overall_grade": overall_grade,
        "strongest_evidence_level": strongest_evidence_level,
        "basis": "timestamp_safe_local_simulation",
        "actual_cash_used": False,
        "profit_proven": False,
        "permits_live_order": False,
        "event_count": len(per_event),
        "simulated_trade_count": simulated_trade_count,
        "critical_missing_count": critical_missing_count,
        "future_signal_source_count": future_signal_source_count,
        "artifact_origin_counts": dict(sorted(origin_counts.items())),
        "source_available_counts": dict(sorted(source_available_counts.items())),
        "source_missing_counts": dict(sorted(source_missing_counts.items())),
        "recomputed_minimal_artifact_count": recomputed_minimal_count,
        "existing_artifact_only": recomputed_minimal_count == 0,
        "known_limits": list(dict.fromkeys(known_limits)),
    }


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


def build_crypto_perp_backtest_candidate_pack(
    *,
    data_dir: Path,
    out_dir: Path,
    created_at: datetime | str,
    notional_usd: Decimal,
    min_events: int = 10,
    min_events_for_stability: int = 30,
    fold_count: int = 0,
    fee_rate: Decimal = CRYPTO_PERP_PROJECT_TAKER_FEE_RATE,
    funding_rate: Decimal = CRYPTO_PERP_PROJECT_FUNDING_RATE,
    slippage_bps: Decimal = CRYPTO_PERP_PROJECT_SLIPPAGE_BPS,
    max_holding_minutes: int = 60,
) -> BacktestCandidatePackResult:
    validate_backtest_assumptions(
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
    signals = build_signal_rows(pairs=pairs, artifacts=per_event)
    ledger = build_availability_ledger(pairs=pairs, artifacts=per_event)
    assumptions = build_execution_assumptions(
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        max_holding_minutes=max_holding_minutes,
    )
    no_lookahead = build_no_lookahead_report(pairs=pairs, artifacts=per_event, ledger=ledger)
    backtest = build_backtest_result(signals, rows)
    stress = build_stress_result(signals, rows)
    backtest_results = cast(list[dict[str, Any]], backtest["results"])
    regime = build_regime_split_result(pairs=pairs, backtest_results=backtest_results)
    rolling = build_rolling_stability_result(backtest_results, min_events_for_stability)
    decision, reason_codes = decide_backtest_candidate(
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
    evidence_grade_summary = _evidence_grade_summary(
        per_event=per_event,
        ledger=ledger,
        backtest=backtest,
        rows_origin=rows_origin,
        guard_origin=guard_origin,
    )
    pack_id = stable_hash(
        [
            "crypto-perp-backtest-candidate-pack",
            serialize_utc_z(created),
            summary,
            evidence_grade_summary,
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
        evidence_grade_summary=_json_ready(evidence_grade_summary),
        non_goal_flags=non_goal_flags(),
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
    write_text_artifact(decision_md_path, decision_markdown(decision_artifact))
    paths["decision.md"] = decision_md_path
    return BacktestCandidatePackResult(paths=paths, decision=decision_artifact)
