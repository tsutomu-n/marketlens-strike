from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal
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
from sis.crypto_perp.edge_scorer import build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent, validate_event_identity
from sis.crypto_perp.features import build_feature_pack
from sis.crypto_perp.io import file_artifact_ref, write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpProducer, stable_hash
from sis.crypto_perp.outcomes import CryptoPerpOutcome, validate_outcome_identity
from sis.crypto_perp.real_market_artifact_validation import (
    validate_public_market_pair,
    validate_public_source_availability,
    validate_selection_manifest,
)
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
    critical_missing_reasons: Counter[str] = Counter()
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
                if source_type in {"event", "bars", "ticker", "funding"}:
                    missing_reason = str(raw_row.get("missing_reason") or "")
                    if missing_reason:
                        critical_missing_reasons[missing_reason] += 1

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
        known_limits.extend(sorted(critical_missing_reasons))
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


def _select_pairs(
    data_dir: Path,
    *,
    expected_horizon_minutes: int | None = None,
    require_selection_manifest: bool = False,
) -> tuple[list[_EventOutcomePair], list[str]]:
    event_records = _load_schema_artifacts(data_dir, "crypto_perp_event.v1", CryptoPerpEvent)
    outcome_records = _load_schema_artifacts(data_dir, "crypto_perp_outcome.v1", CryptoPerpOutcome)
    events: dict[str, tuple[Path, CryptoPerpEvent]] = {}
    outcomes_by_event: dict[str, list[tuple[Path, CryptoPerpOutcome]]] = {}
    gaps: list[str] = []
    for path, event in event_records:
        validate_event_identity(event)
        if event.event_id in events:
            raise ValueError(f"MULTIPLE_EVENTS_WITH_SAME_ID: {event.event_id}")
        events[event.event_id] = (path, event)
    for path, outcome in outcome_records:
        validate_outcome_identity(outcome)
        matured = [horizon for horizon in outcome.horizons if horizon.matured]
        if not matured:
            continue
        if len(matured) != 1:
            raise ValueError(f"MATURED_HORIZON_COUNT_NOT_ONE: {outcome.event_id}")
        if (
            expected_horizon_minutes is not None
            and matured[0].horizon_minutes != expected_horizon_minutes
        ):
            raise ValueError(
                "MATURED_HORIZON_HOLDING_MISMATCH: "
                f"max_holding_minutes={expected_horizon_minutes} does not match "
                f"actual outcome horizon={matured[0].horizon_minutes} "
                f"event={outcome.event_id}"
            )
        outcomes_by_event.setdefault(outcome.event_id, []).append((path, outcome))
    pairs: list[_EventOutcomePair] = []
    for event_id, (event_path, event) in sorted(events.items()):
        outcomes = sorted(outcomes_by_event.get(event_id, []), key=lambda item: item[0].as_posix())
        if not outcomes:
            gaps.append("EVENT_WITHOUT_MATURED_OUTCOME")
            continue
        if len(outcomes) > 1:
            raise ValueError(f"MULTIPLE_MATURED_OUTCOMES_FOR_EVENT: {event_id}")
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
    execution_windows: dict[str, tuple[str, str, int]] = {}
    for pair in pairs:
        window = validate_public_market_pair(
            event=pair.event,
            outcome=pair.outcome,
            data_dir=data_dir,
        )
        if window is not None:
            execution_windows[pair.event.event_id] = window
    if require_selection_manifest:
        validate_selection_manifest(
            data_dir=data_dir,
            pairs=pairs,
            execution_windows=execution_windows,
        )
    return pairs, list(dict.fromkeys(gaps))


def _existing_by_event(
    data_dir: Path,
    schema_version: str,
    model_type: type[JsonModelT],
) -> dict[str, tuple[Path, JsonModelT]]:
    selected: dict[str, tuple[Path, JsonModelT]] = {}
    for path, artifact in _load_schema_artifacts(data_dir, schema_version, model_type):
        event_id = getattr(artifact, "event_id", None)
        if not isinstance(event_id, str) or not event_id:
            continue
        if event_id in selected:
            raise ValueError(
                f"MULTIPLE_{schema_version.upper().replace('.', '_')}_FOR_EVENT: {event_id}"
            )
        selected[event_id] = (path, artifact)
    return selected


def _build_per_event_artifacts(
    *,
    data_dir: Path,
    pairs: Sequence[_EventOutcomePair],
    created: datetime,
) -> list[_PerEventArtifacts]:
    sources = _existing_by_event(
        data_dir, "crypto_perp_source_availability.v1", CryptoPerpSourceAvailability
    )
    artifacts: list[_PerEventArtifacts] = []
    for pair in pairs:
        source_record = sources.get(pair.event.event_id)
        if source_record is None:
            source = build_source_availability(
                event=pair.event,
                created_at=created,
                available_sources={"outcome": True},
                row_counts={"outcome": 1},
                source_refs=[file_artifact_ref(pair.outcome_path, pair.outcome.schema_version)],
                producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
            )
            source_origin = _ArtifactOrigin(
                origin="recomputed_minimal",
                path=None,
                note="source availability missing; recomputed from event and outcome only",
            )
        else:
            source_path, source = source_record
            validate_public_source_availability(
                event=pair.event,
                source=source,
                data_dir=data_dir,
            )
            source_origin = _ArtifactOrigin("existing", source_path.as_posix(), "matched_event_id")

        feature = build_feature_pack(
            event=pair.event,
            source_availability=source,
            created_at=created,
            producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
        )
        feature_origin = _ArtifactOrigin(
            "recomputed_minimal",
            None,
            "recomputed by the current non-recursive feature pipeline",
        )
        edge = build_edge_score(
            feature_pack=feature,
            source_availability=source,
            created_at=created,
            producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
        )
        edge_origin = _ArtifactOrigin(
            "recomputed_minimal",
            None,
            "recomputed from the current feature pack and source availability",
        )
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
    pairs: Sequence[_EventOutcomePair],
    created: datetime,
    notional_usd: Decimal,
    fee_rate: Decimal,
    funding_rate: Decimal,
    slippage_bps: Decimal,
    min_events_for_stability: int,
    fold_count: int,
    lookahead_violation: bool,
    recursive_warmup_violation: bool,
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
    rows = build_cost_aware_tournament_rows(
        outcomes=[pair.outcome for pair in pairs],
        created_at=created,
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        source_refs=[
            file_artifact_ref(pair.outcome_path, pair.outcome.schema_version) for pair in pairs
        ],
        known_gaps=known_gaps,
        producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
    )
    rows_origin = _ArtifactOrigin(
        "recomputed_minimal",
        None,
        "always recomputed from matured outcomes; derived rows are not trusted inputs",
    )
    guard_source_ref = {
        "path": "backtest_candidate_pack:tournament_rows_v2",
        "sha256": rows.artifact_id,
        "schema_version": rows.schema_version,
    }
    guard = build_bias_guard(
        rows=rows.rows,
        created_at=created,
        min_events_for_pbo=min_events_for_stability,
        fold_count=fold_count,
        lookahead_violation=lookahead_violation,
        recursive_warmup_violation=recursive_warmup_violation,
        source_refs=[guard_source_ref],
        known_gaps=rows.known_gaps,
        producer_command=BACKTEST_CANDIDATE_PACK_PRODUCER,
    )
    guard_origin = _ArtifactOrigin(
        "recomputed_minimal",
        None,
        "recomputed with current guard policy from selected tournament rows",
    )
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
    pairs, selection_gaps = _select_pairs(
        data_dir,
        expected_horizon_minutes=max_holding_minutes,
        require_selection_manifest=True,
    )
    per_event = _build_per_event_artifacts(data_dir=data_dir, pairs=pairs, created=created)
    signals = build_signal_rows(pairs=pairs, artifacts=per_event)
    ledger = build_availability_ledger(pairs=pairs, artifacts=per_event)
    no_lookahead = build_no_lookahead_report(pairs=pairs, artifacts=per_event, ledger=ledger)
    no_lookahead_summary = cast(Mapping[str, Any], no_lookahead["summary"])
    no_lookahead_checks = cast(Sequence[Mapping[str, Any]], no_lookahead["checks"])
    recursive_warmup_checks = [
        check
        for check in no_lookahead_checks
        if check.get("check_id") == "recursive_feature_warmup_absent"
    ]
    recursive_warmup_violation = (
        len(recursive_warmup_checks) != 1 or recursive_warmup_checks[0].get("status") != "pass"
    )
    rows, rows_origin, guard, guard_origin = _build_rows_and_guard(
        pairs=pairs,
        created=created,
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        min_events_for_stability=min_events_for_stability,
        fold_count=fold_count,
        lookahead_violation=int(no_lookahead_summary["failed_count"]) > 0,
        recursive_warmup_violation=recursive_warmup_violation,
        known_gaps=selection_gaps,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_output_path: Path | None = None
    guard_output_path: Path | None = None
    if rows is not None:
        rows_output_path = out_dir / "tournament_rows_v2.json"
        write_json_artifact(rows_output_path, rows.model_dump(mode="json"))
    if guard is not None and rows is not None:
        assert rows_output_path is not None
        guard = guard.model_copy(
            update={"source_refs": [file_artifact_ref(rows_output_path, rows.schema_version)]}
        )
        guard_output_path = out_dir / "bias_guard.json"
        write_json_artifact(guard_output_path, guard.model_dump(mode="json"))
    assumptions = build_execution_assumptions(
        notional_usd=notional_usd,
        fee_rate=fee_rate,
        funding_rate=funding_rate,
        slippage_bps=slippage_bps,
        max_holding_minutes=max_holding_minutes,
    )
    backtest = build_backtest_result(
        signals, rows, holding_minutes=max_holding_minutes, notional_usd=notional_usd
    )
    stress = build_stress_result(
        signals, rows, holding_minutes=max_holding_minutes, notional_usd=notional_usd
    )
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
        fixture_only=any(
            pair.event.producer.command == "crypto-perp-no-cash-backtest-sample" for pair in pairs
        ),
        event_source_provenance_verified=all(
            pair.event.event_family == "market_window_v1" for pair in pairs
        ),
    )
    artifact_paths = {
        name: (out_dir / name).as_posix() for name in BACKTEST_CANDIDATE_PACK_ARTIFACT_NAMES
    }
    paths: dict[str, Path] = {}
    component_schema_versions: dict[str, str | None] = {}
    if rows is not None:
        assert rows_output_path is not None
        paths["tournament_rows_v2.json"] = rows_output_path
        component_schema_versions["tournament_rows_v2.json"] = rows.schema_version
    if guard is not None and rows is not None:
        assert guard_output_path is not None
        paths["bias_guard.json"] = guard_output_path
        component_schema_versions["bias_guard.json"] = guard.schema_version
    signal_path = out_dir / "signal_rows.jsonl"
    signal_path.write_text(
        "".join(json.dumps(_json_ready(row), ensure_ascii=False) + "\n" for row in signals),
        encoding="utf-8",
    )
    paths["signal_rows.jsonl"] = signal_path
    component_schema_versions["signal_rows.jsonl"] = None
    component_payloads = {
        "data_availability_ledger.json": ledger,
        "execution_assumptions.json": assumptions,
        "no_lookahead_report.json": no_lookahead,
        "backtest_result.json": backtest,
        "stress_result.json": stress,
        "regime_split_result.json": regime,
        "rolling_stability_result.json": rolling,
    }
    for name, payload in component_payloads.items():
        component_path = out_dir / name
        write_json_artifact(component_path, _json_ready(payload))
        paths[name] = component_path
        component_schema_versions[name] = str(payload["schema_version"])
    pack_component_refs = {
        name: file_artifact_ref(path, component_schema_versions[name])
        for name, path in sorted(paths.items())
    }
    source_refs = [
        file_artifact_ref(pair.event_path, pair.event.schema_version) for pair in pairs
    ] + [file_artifact_ref(pair.outcome_path, pair.outcome.schema_version) for pair in pairs]
    selection_manifest_path = data_dir / "selection_manifest.json"
    if selection_manifest_path.is_file():
        selection_manifest = json.loads(selection_manifest_path.read_text(encoding="utf-8"))
        manifest_schema_version = (
            str(selection_manifest.get("schema_version"))
            if isinstance(selection_manifest, Mapping)
            and selection_manifest.get("schema_version") is not None
            else None
        )
        source_refs.append(file_artifact_ref(selection_manifest_path, manifest_schema_version))
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
        "bias_guard_stop_reasons": list(guard.stop_reasons) if guard else [],
        "bias_guard_warning_codes": (
            [gap for gap in guard.known_gaps if gap.startswith("BIAS_GUARD_WARNING_")]
            if guard
            else []
        ),
        "pbo_status": guard.pbo_status if guard else "NOT_RUN",
        "pack_component_refs": pack_component_refs,
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
    decision_path = out_dir / "decision.json"
    write_json_artifact(decision_path, decision_artifact.model_dump(mode="json"))
    paths["decision.json"] = decision_path
    decision_md_path = out_dir / "decision.md"
    write_text_artifact(decision_md_path, decision_markdown(decision_artifact))
    paths["decision.md"] = decision_md_path
    return BacktestCandidatePackResult(paths=paths, decision=decision_artifact)
