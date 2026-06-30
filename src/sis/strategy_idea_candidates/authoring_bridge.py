from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_serializer
import yaml

from sis.backtest.artifact_io import sha256_file
from sis.backtest.benchmark_relative import DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN
from sis.backtest.pack_runner import StrategyBacktestPackRunInputs, run_strategy_backtest_pack
from sis.edge_candidates.backtest_kill_gate import (
    BacktestKillGateDecision,
    BacktestKillGateInput,
    build_backtest_kill_gate,
)
from sis.edge_candidates.multiplicity import SelectionAdjustmentStatus, TrialMultiplicityAccount
from sis.edge_candidates.protocol import (
    CandidateProtocolManifest,
    CandidateProtocolMode,
    FamilyEventCountPolicy,
)
from sis.strategy_idea_candidates.models import (
    CandidateBoundary,
    CandidateDecision,
    CandidateExportManifest,
    StrategyIdeaCandidate,
    StrategyIdeaCandidateSet,
)
from sis.strategy_idea_candidates.perp_costs import perp_cost_estimate_from_candidate
from sis.strategy_idea_candidates.prep_watchdeck_source import (
    PrepWatchdeckBundle,
    PrepWatchdeckContract,
    PrepWatchdeckTicker,
    load_prep_watchdeck_source,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo


AUTHORING_BRIDGE_SCHEMA_VERSION = "strategy_idea_candidate_authoring_bridge.v1"
SUPPORTED_FAMILIES = {
    "perp_momentum_continuation",
    "perp_funding_rate_carry_filter",
}
SUPPORTED_PRODUCT_TYPE = "USDT-FUTURES"
AUTHORING_VENUE = "trade_xyz"

BridgeStatus = Literal[
    "BRIDGED_TECHNICAL_ONLY",
    "BLOCKED_UNSUPPORTED_FAMILY",
    "BLOCKED_MISSING_SOURCE",
    "BLOCKED_BACKTEST_PACK",
    "BLOCKED_ECONOMIC_GATE",
    "BLOCKED_MULTIPLICITY_ACCOUNT",
]


class ProfitCoreArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    path: str
    sha256: str
    artifact_id: str | None = None


class StrategyIdeaCandidateAuthoringBridgeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    family: str
    status: BridgeStatus
    symbols: list[str]
    blockers: list[str] = Field(default_factory=list)
    source_statuses: list[str] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    backtest_kill_gate_state: str | None = None
    profit_core_blocker_codes: list[str] = Field(default_factory=list)


class StrategyIdeaCandidateAuthoringBridgeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_authoring_bridge.v1"] = (
        AUTHORING_BRIDGE_SCHEMA_VERSION
    )
    manifest_id: str
    created_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    candidate_set_path: str
    candidate_set_sha256: str
    export_manifest_path: str
    export_manifest_sha256: str
    ledger_path: str
    ledger_sha256: str
    protocol_manifest_ref: ProfitCoreArtifactRef | None = None
    multiplicity_account_ref: ProfitCoreArtifactRef | None = None
    prep_watchdeck_root: str
    candidates: list[StrategyIdeaCandidateAuthoringBridgeCandidate]
    summary: dict[str, Any]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return _serialize_datetime(value)


@dataclass(frozen=True)
class StrategyIdeaCandidateAuthoringBridgeResult:
    manifest: StrategyIdeaCandidateAuthoringBridgeManifest
    manifest_path: Path
    manifest_sha256: str


class StrategyIdeaCandidateAuthoringBridgeOutputExistsError(ValueError):
    pass


def build_strategy_idea_candidate_authoring_bridge(
    *,
    candidate_set_path: Path,
    export_manifest_path: Path,
    ledger_path: Path,
    protocol_manifest_path: Path | None = None,
    multiplicity_account_path: Path | None = None,
    prep_watchdeck_root: Path,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateAuthoringBridgeResult:
    manifest_path = out_dir / "strategy_idea_candidate_authoring_bridge_manifest.json"
    if manifest_path.exists() and not replace_existing:
        raise StrategyIdeaCandidateAuthoringBridgeOutputExistsError(
            f"output already exists: {manifest_path}"
        )
    if not ledger_path.exists():
        raise FileNotFoundError(f"candidate ledger missing: {ledger_path}")

    candidate_set = StrategyIdeaCandidateSet.model_validate(read_mapping_file(candidate_set_path))
    export_manifest = CandidateExportManifest.model_validate(
        read_mapping_file(export_manifest_path)
    )
    if export_manifest.candidate_set_id != candidate_set.candidate_set_id:
        raise ValueError(
            "export_manifest candidate_set_id does not match candidate_set: "
            f"{export_manifest.candidate_set_id} != {candidate_set.candidate_set_id}"
        )
    protocol = _load_protocol_manifest(protocol_manifest_path)
    multiplicity_account = _load_multiplicity_account(multiplicity_account_path)
    _validate_multiplicity_account_matches_candidate_set(
        candidate_set=candidate_set,
        multiplicity_account=multiplicity_account,
    )

    shortlisted_export_ids = {item.idea_candidate_id for item in export_manifest.exported_ideas}
    shortlisted_candidates = [
        candidate
        for candidate in candidate_set.candidate_inventory
        if candidate.decision is CandidateDecision.SHORTLISTED
        and candidate.idea_candidate_id in shortlisted_export_ids
    ]
    source = load_prep_watchdeck_source(
        prep_watchdeck_root,
        symbols=_candidate_symbols(shortlisted_candidates),
    )

    candidate_results: list[StrategyIdeaCandidateAuthoringBridgeCandidate] = []
    for candidate in shortlisted_candidates:
        candidate_results.append(
            _process_candidate(
                candidate=candidate,
                source=source,
                out_dir=out_dir,
                protocol=protocol,
                multiplicity_account=multiplicity_account,
                replace_existing=replace_existing,
            )
        )

    status_counts = Counter(item.status for item in candidate_results)
    gate_state_counts = Counter(
        item.backtest_kill_gate_state
        for item in candidate_results
        if item.backtest_kill_gate_state is not None
    )
    refs_attached = protocol_manifest_path is not None and multiplicity_account_path is not None
    manifest = StrategyIdeaCandidateAuthoringBridgeManifest(
        manifest_id=f"{candidate_set.candidate_set_id}-authoring-bridge",
        created_at=datetime.now(timezone.utc).replace(microsecond=0),
        producer=ProducerInfo(command="strategy-idea-candidates-authoring-bridge"),
        candidate_set_id=candidate_set.candidate_set_id,
        candidate_set_path=candidate_set_path.as_posix(),
        candidate_set_sha256=sha256_file(candidate_set_path),
        export_manifest_path=export_manifest_path.as_posix(),
        export_manifest_sha256=sha256_file(export_manifest_path),
        ledger_path=ledger_path.as_posix(),
        ledger_sha256=sha256_file(ledger_path),
        protocol_manifest_ref=_artifact_ref(
            protocol_manifest_path,
            schema_version="candidate_protocol_manifest.v1",
            artifact_id=protocol.protocol_id if protocol is not None else None,
        ),
        multiplicity_account_ref=_artifact_ref(
            multiplicity_account_path,
            schema_version="trial_multiplicity_account.v1",
            artifact_id=(
                multiplicity_account.account_id if multiplicity_account is not None else None
            ),
        ),
        prep_watchdeck_root=prep_watchdeck_root.as_posix(),
        candidates=candidate_results,
        summary={
            "candidate_count": len(candidate_results),
            "status_counts": dict(sorted(status_counts.items())),
            "bridged_count": status_counts.get("BRIDGED_TECHNICAL_ONLY", 0),
            "blocked_count": len(candidate_results)
            - status_counts.get("BRIDGED_TECHNICAL_ONLY", 0),
            "candidate_scoped_outputs": True,
            "actual_cash_result_available": False,
            "backtest_kill_gate_state_counts": dict(sorted(gate_state_counts.items())),
            "profit_core_ref_status": "ATTACHED" if refs_attached else "MISSING_COMPATIBILITY_REFS",
        },
        known_gaps=[
            "C9_V0_DOES_NOT_PROVE_ALPHA_OR_PROFIT",
            "PREP_WATCHDECK_COSTS_ARE_ESTIMATE_ONLY",
            "DO_NOT_FEED_PREVIEW_OR_ESTIMATE_ROWS_TO_ACTUAL_CASH_REPORT",
            *([] if refs_attached else ["PROFIT_CORE_REFS_NOT_SUPPLIED_COMPATIBILITY_MODE"]),
        ],
    )
    write_json_artifact(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
    return StrategyIdeaCandidateAuthoringBridgeResult(
        manifest=manifest,
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
    )


def _process_candidate(
    *,
    candidate: StrategyIdeaCandidate,
    source: PrepWatchdeckBundle,
    out_dir: Path,
    protocol: CandidateProtocolManifest | None,
    multiplicity_account: TrialMultiplicityAccount | None,
    replace_existing: bool,
) -> StrategyIdeaCandidateAuthoringBridgeCandidate:
    candidate_dir = out_dir / candidate.idea_candidate_id
    if candidate_dir.exists() and any(candidate_dir.iterdir()) and not replace_existing:
        raise StrategyIdeaCandidateAuthoringBridgeOutputExistsError(
            f"output already exists: {candidate_dir}"
        )
    symbols = _normalize_symbols(candidate.instruments)
    status, blockers = _candidate_blockers(candidate, source, symbols)
    if status != "BRIDGED_TECHNICAL_ONLY":
        blocker_path = _write_blocker(
            candidate_dir=candidate_dir,
            candidate=candidate,
            status=status,
            blockers=blockers,
            symbols=symbols,
            source=source,
        )
        return StrategyIdeaCandidateAuthoringBridgeCandidate(
            candidate_id=candidate.idea_candidate_id,
            family=candidate.family,
            status=status,
            symbols=symbols,
            blockers=blockers,
            source_statuses=source.source_statuses,
            artifacts={"bridge_blocker": blocker_path.as_posix()},
        )

    try:
        artifacts, kill_gate = _write_bridged_candidate_artifacts(
            candidate_dir=candidate_dir,
            candidate=candidate,
            symbols=symbols,
            source=source,
            protocol=protocol,
            multiplicity_account=multiplicity_account,
        )
    except Exception as exc:
        blocker_path = _write_blocker(
            candidate_dir=candidate_dir,
            candidate=candidate,
            status="BLOCKED_BACKTEST_PACK",
            blockers=[str(exc)],
            symbols=symbols,
            source=source,
        )
        return StrategyIdeaCandidateAuthoringBridgeCandidate(
            candidate_id=candidate.idea_candidate_id,
            family=candidate.family,
            status="BLOCKED_BACKTEST_PACK",
            symbols=symbols,
            blockers=[str(exc)],
            source_statuses=source.source_statuses,
            artifacts={"bridge_blocker": blocker_path.as_posix()},
        )

    stale_blocker_path = candidate_dir / "bridge_blocker.json"
    if stale_blocker_path.is_file():
        stale_blocker_path.unlink()

    return StrategyIdeaCandidateAuthoringBridgeCandidate(
        candidate_id=candidate.idea_candidate_id,
        family=candidate.family,
        status="BRIDGED_TECHNICAL_ONLY",
        symbols=symbols,
        blockers=[],
        source_statuses=source.source_statuses,
        artifacts={key: path.as_posix() for key, path in artifacts.items()},
        backtest_kill_gate_state=kill_gate.gate_state.value,
        profit_core_blocker_codes=kill_gate.blocker_codes,
    )


def _candidate_blockers(
    candidate: StrategyIdeaCandidate,
    source: PrepWatchdeckBundle,
    symbols: list[str],
) -> tuple[BridgeStatus, list[str]]:
    if candidate.family not in SUPPORTED_FAMILIES:
        return (
            "BLOCKED_UNSUPPORTED_FAMILY",
            [f"unsupported C9 v0 family: {candidate.family}"],
        )
    side = str(candidate.parameter_set.get("side_bias") or "").lower()
    if side not in {"long", "short"}:
        return (
            "BLOCKED_UNSUPPORTED_FAMILY",
            [f"C9 v0 requires side_bias long or short: {side or '<missing>'}"],
        )
    product_type = str(candidate.parameter_set.get("product_type") or "")
    if product_type != SUPPORTED_PRODUCT_TYPE:
        return (
            "BLOCKED_UNSUPPORTED_FAMILY",
            [f"candidate product_type must be {SUPPORTED_PRODUCT_TYPE}: {product_type}"],
        )
    for symbol in symbols:
        contract = source.contracts_by_symbol.get(symbol)
        if contract is not None and contract.product_type != SUPPORTED_PRODUCT_TYPE:
            return (
                "BLOCKED_UNSUPPORTED_FAMILY",
                [f"source product_type must be {SUPPORTED_PRODUCT_TYPE}: {symbol}"],
            )
        if not source.candles_by_symbol.get(symbol):
            return "BLOCKED_MISSING_SOURCE", [f"missing 5m candle rows: {symbol}"]
    missing_columns = _missing_source_columns(candidate, source, symbols)
    if missing_columns:
        return "BLOCKED_MISSING_SOURCE", missing_columns
    return "BRIDGED_TECHNICAL_ONLY", []


def _missing_source_columns(
    candidate: StrategyIdeaCandidate,
    source: PrepWatchdeckBundle,
    symbols: list[str],
) -> list[str]:
    missing: list[str] = []
    if candidate.family == "perp_funding_rate_carry_filter":
        for symbol in symbols:
            ticker = source.tickers_by_symbol.get(symbol)
            if ticker is None or ticker.funding_rate is None:
                missing.append(f"funding_rate missing from prep-watchdeck source: {symbol}")
    return missing


def _write_bridged_candidate_artifacts(
    *,
    candidate_dir: Path,
    candidate: StrategyIdeaCandidate,
    symbols: list[str],
    source: PrepWatchdeckBundle,
    protocol: CandidateProtocolManifest | None,
    multiplicity_account: TrialMultiplicityAccount | None,
) -> tuple[dict[str, Path], BacktestKillGateDecision]:
    candidate_dir.mkdir(parents=True, exist_ok=True)
    feature_path = candidate_dir / "feature_panel.parquet"
    quote_path = candidate_dir / "quotes.parquet"
    cost_path = candidate_dir / "venue_cost_matrix.csv"
    spec_path = candidate_dir / "strategy_authoring_spec.yaml"
    suite_path = candidate_dir / "strategy_backtest_suite.yaml"
    bundle_path = candidate_dir / "strategy_authoring_bundle.yaml"
    source_manifest_path = candidate_dir / "prep_watchdeck_source_manifest.json"
    feature = _feature_panel(candidate=candidate, source=source, symbols=symbols)
    feature.write_parquet(feature_path)
    _quote_frame(candidate=candidate, feature=feature, source=source).write_parquet(quote_path)
    _cost_matrix(candidate=candidate, symbols=symbols, source=source).write_csv(cost_path)
    write_text_artifact(
        spec_path,
        _yaml_text(
            _authoring_spec(
                candidate,
                symbols,
                feature_panel_path=feature_path.resolve(),
                quote_data_path=quote_path.resolve(),
                cost_model_path=cost_path.resolve(),
            )
        ),
    )
    write_text_artifact(suite_path, _yaml_text(_backtest_suite(candidate)))
    write_text_artifact(bundle_path, _yaml_text(_authoring_bundle(candidate)))
    write_json_artifact(
        source_manifest_path,
        _source_manifest(candidate=candidate, source=source, symbols=symbols),
    )
    pack_result = _run_strategy_backtest_pack_from_repo_root(
        StrategyBacktestPackRunInputs(
            spec_path=spec_path.resolve(),
            suite_path=suite_path.resolve(),
            bundle_path=bundle_path.resolve(),
            label_horizon_minutes=_label_horizon_minutes(candidate),
            benchmark_series_path=None,
            benchmark_series_return_column=DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
            out_dir=(candidate_dir / "backtest_pack").resolve(),
            reports_dir=(candidate_dir / "backtest_reports").resolve(),
            data_dir=(candidate_dir / "backtest_runtime_data").resolve(),
        )
    )
    artifacts = {
        "prep_watchdeck_source_manifest": source_manifest_path,
        "feature_panel": feature_path,
        "quotes": quote_path,
        "venue_cost_matrix": cost_path,
        "strategy_authoring_spec": spec_path,
        "strategy_backtest_suite": suite_path,
        "strategy_authoring_bundle": bundle_path,
        "backtest_pack": pack_result.pack_path,
        "backtest_pack_validation": pack_result.validation_path,
        "backtest_stress": pack_result.stress_path,
        "backtest_baseline_comparison": pack_result.baseline_comparison_path,
        "backtest_benchmark_relative": pack_result.benchmark_relative_path,
    }
    gate_path = candidate_dir / "backtest_kill_gate.json"
    kill_gate = _build_and_write_backtest_kill_gate(
        candidate=candidate,
        protocol=protocol,
        multiplicity_account=multiplicity_account,
        baseline_comparison_path=pack_result.baseline_comparison_path,
        stress_path=pack_result.stress_path,
        out_path=gate_path,
    )
    artifacts["backtest_kill_gate"] = gate_path
    return artifacts, kill_gate


def _feature_panel(
    *,
    candidate: StrategyIdeaCandidate,
    source: PrepWatchdeckBundle,
    symbols: list[str],
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    lookback = _positive_int(candidate.parameter_set.get("lookback"), default=1)
    breakout_z = _positive_float(candidate.parameter_set.get("breakout_z"), default=1.0)
    for symbol in symbols:
        contract = source.contracts_by_symbol.get(symbol)
        ticker = source.tickers_by_symbol.get(symbol)
        funding_bps = _funding_rate_bps(ticker)
        spread_bps = _spread_bps_estimate(candidate, ticker)
        for candle in source.candles_by_symbol.get(symbol, []):
            rows.append(
                {
                    "canonical_symbol": symbol,
                    "ts": _datetime_from_ms(int(candle["ts"])),
                    "open": float(candle["open"]),
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "close": float(candle["close"]),
                    "volume": float(candle.get("base_vol") or 0.0),
                    "base_volume": float(candle.get("base_vol") or 0.0),
                    "quote_volume": float(candle.get("quote_vol") or 0.0),
                    "funding_rate_bps": funding_bps,
                    "spread_bps_estimate": spread_bps,
                    "max_leverage": _contract_max_leverage(contract),
                    "min_trade_usdt": _contract_min_trade_usdt(contract),
                    "source_quality": source.source_quality_by_symbol.get(symbol, "OK"),
                    "trade_allowed": True,
                    "source_confidence": 0.8,
                    "venue_quality_score": 0.8,
                    "momentum_breakout_z": breakout_z,
                }
            )
    frame = pl.DataFrame(rows).sort(["canonical_symbol", "ts"])
    if frame.is_empty():
        return frame
    mark_return = f"mark_return_{lookback}bars"
    realized_vol = f"realized_volatility_{lookback}bars"
    threshold = f"momentum_breakout_threshold_{lookback}bars"
    return (
        frame.with_columns(
            pl.col("close").pct_change(lookback).over("canonical_symbol").alias(mark_return),
            pl.col("close")
            .pct_change()
            .rolling_std(window_size=lookback, min_samples=1)
            .over("canonical_symbol")
            .alias(realized_vol),
        )
        .with_columns(
            pl.col(mark_return).fill_null(0.0),
            pl.col(realized_vol).fill_null(0.0),
        )
        .with_columns((pl.col(realized_vol) * breakout_z).alias(threshold))
    )


def _quote_frame(
    *, candidate: StrategyIdeaCandidate, feature: pl.DataFrame, source: PrepWatchdeckBundle
) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for row in feature.to_dicts():
        symbol = str(row["canonical_symbol"]).upper()
        ticker = source.tickers_by_symbol.get(symbol)
        mid = float(row["close"])
        spread_bps = float(row["spread_bps_estimate"])
        bid, ask, estimated = _bid_ask(ticker=ticker, mid=mid, spread_bps=spread_bps)
        ts = row["ts"]
        ts_iso = ts.isoformat() if isinstance(ts, datetime) else str(ts)
        rows.append(
            {
                "canonical_symbol": symbol,
                "ts": ts,
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "last": mid,
                "quote_volume": float(row.get("quote_volume") or 0.0),
                "bid_ask_source": "spread_bps_estimate" if estimated else "prep_watchdeck",
                "ts_client": ts_iso,
                "venue": AUTHORING_VENUE,
                "venue_symbol": symbol,
                "exec_buy_price": ask,
                "exec_sell_price": bid,
                "mark_price": mid,
                "mid_price": mid,
                "oracle_price": mid,
                "index_price": mid,
                "spread_bps": spread_bps,
                "min_side_depth_10bps_usd": None,
                "oracle_ts_ms": int(ts.timestamp() * 1000) if isinstance(ts, datetime) else None,
                "market_status": "open",
                "is_tradable": True,
            }
        )
    return pl.DataFrame(rows)


def _cost_matrix(
    *,
    candidate: StrategyIdeaCandidate,
    symbols: list[str],
    source: PrepWatchdeckBundle,
) -> pl.DataFrame:
    estimate = perp_cost_estimate_from_candidate(candidate)
    rows = []
    for symbol in symbols:
        ticker = source.tickers_by_symbol.get(symbol)
        spread_bps = _spread_bps_estimate(candidate, ticker)
        rows.append(
            {
                "venue": AUTHORING_VENUE,
                "symbol": symbol,
                "asset_class": "crypto_perp",
                "open_fee_bps": estimate.fee_rate * 10000,
                "close_fee_bps": estimate.fee_rate * 10000,
                "spread_p50_bps": spread_bps,
                "spread_p90_bps": spread_bps,
                "spread_p99_bps": spread_bps * 1.5,
                "holding_cost_4h_bps": abs(estimate.funding_rate_bps_per_8h) / 2,
                "holding_cost_24h_bps": abs(estimate.funding_rate_bps_per_8h) * 3,
                "holding_cost_72h_bps": abs(estimate.funding_rate_bps_per_8h) * 9,
                "stale_rate": 0.0,
                "tradable_rate": 1.0,
                "notes": "ESTIMATE_ONLY; not measured slippage or actual cash proof",
            }
        )
    return pl.DataFrame(rows)


def _authoring_spec(
    candidate: StrategyIdeaCandidate,
    symbols: list[str],
    *,
    feature_panel_path: Path,
    quote_data_path: Path,
    cost_model_path: Path,
) -> dict[str, Any]:
    lookback = _positive_int(candidate.parameter_set.get("lookback"), default=1)
    side = str(candidate.parameter_set.get("side_bias") or "long").lower()
    entry = _entry_rules(candidate, lookback)
    return {
        "schema_version": "strategy_authoring_spec.v1",
        "experiment": {
            "strategy_id": candidate.idea_candidate_id,
            "strategy_family": candidate.family,
            "strategy_version": "c9_v0",
            "description": candidate.hypothesis_template,
            "symbol_bindings": [
                {
                    "execution_venue": AUTHORING_VENUE,
                    "execution_symbol": symbol,
                    "real_market_symbol": symbol,
                    "asset_class": "crypto_perp",
                    "country": None,
                    "currency": "USDT",
                }
                for symbol in symbols
            ],
            "run_profile_id": "strategy_lab_research_only",
        },
        "data": {
            "feature_panel_path": feature_panel_path.as_posix(),
            "quote_data_path": quote_data_path.as_posix(),
            "cost_model_path": cost_model_path.as_posix(),
        },
        "rules": {
            "side": side,
            "timeframe": candidate.timeframe,
            "entry": entry,
            "exit": {
                "stop_loss_bps": 150,
                "take_profit_bps": 300,
                "max_holding_minutes": _label_horizon_minutes(candidate),
            },
            "sizing": {
                "position_weight": 1.0,
                "notional_usd": _positive_float(
                    candidate.parameter_set.get("max_position_notional_usd"),
                    default=100.0,
                ),
            },
            "execution": {
                "profile": "none",
                "slippage_bps": _positive_float(
                    candidate.parameter_set.get("slippage_bps"),
                    default=0.0,
                ),
                "max_spread_bps": 25.0,
            },
            "portfolio": {"max_signals_per_timestamp": 1},
            "score": {
                "weighted_sum": [
                    {
                        "column": f"mark_return_{lookback}bars",
                        "weight": 1.0 if side == "long" else -1.0,
                    }
                ]
            },
            "confidence": 0.5,
            "reason_code": f"{candidate.family}_c9_v0",
            "hold_reason_code": "c9_v0_hold",
        },
        "backtest": {
            "split_method": "purged_walk_forward",
            "era_unit": "trading_day",
            "label_horizon_minutes": _label_horizon_minutes(candidate),
            "purge_minutes": 0,
            "embargo_minutes": 0,
            "min_trade_count": 0,
            "primary_metric": "total_return",
            "pass_thresholds": {},
            "initial_capital_usd": 10000.0,
        },
        "optimizer": {
            "parameter_sweep": {},
            "selection_metric": "total_return",
            "selection_direction": "maximize",
            "max_variants": 1,
        },
        "promotion": {"default_decision": "hold", "allow_paper_preview": False},
    }


def _entry_rules(
    candidate: StrategyIdeaCandidate, lookback: int
) -> dict[str, list[dict[str, Any]]]:
    common = [
        {"column": "trade_allowed", "op": "is_true"},
        {"column": "spread_bps_estimate", "op": "lte", "value": 25.0},
    ]
    if candidate.family == "perp_momentum_continuation":
        side = str(candidate.parameter_set.get("side_bias") or "long").lower()
        op = "gt" if side == "long" else "lt"
        return {
            "all": [
                *common,
                {
                    "column": f"mark_return_{lookback}bars",
                    "op": op,
                    "value_column": f"momentum_breakout_threshold_{lookback}bars",
                },
            ]
        }
    threshold = _float(candidate.parameter_set.get("funding_rate_threshold_bps"), default=0.0)
    side = str(candidate.parameter_set.get("side_bias") or "long").lower()
    op = "lte" if side == "long" else "gte"
    return {"all": [*common, {"column": "funding_rate_bps", "op": op, "value": threshold}]}


def _backtest_suite(candidate: StrategyIdeaCandidate) -> dict[str, Any]:
    cases = [
        {"case_id": "single_window", "backtest": {"split_method": "single_window"}},
        {"case_id": "walk_forward_day", "backtest": {"split_method": "walk_forward"}},
        {
            "case_id": "purged_walk_forward_day",
            "backtest": {"split_method": "purged_walk_forward"},
        },
        {
            "case_id": "purged_return_bootstrap",
            "backtest": {"split_method": "purged_walk_forward"},
            "resampling": {"method": "return_bootstrap", "iterations": 10, "seed": 7},
        },
        {
            "case_id": "purged_block_bootstrap",
            "backtest": {"split_method": "purged_walk_forward"},
            "resampling": {
                "method": "block_bootstrap",
                "iterations": 10,
                "seed": 11,
                "block_size": 2,
            },
        },
    ]
    case_ids = [case["case_id"] for case in cases]
    return {
        "schema_version": "strategy_backtest_suite.v1",
        "suite_id": f"{candidate.idea_candidate_id}-c9-v0-suite",
        "selection_metric": "total_return",
        "selection_direction": "maximize",
        "cases": cases,
        "members": [
            {
                "spec_path": "strategy_authoring_spec.yaml",
                "enabled": True,
                "case_ids": case_ids,
            }
        ],
    }


def _authoring_bundle(candidate: StrategyIdeaCandidate) -> dict[str, Any]:
    return {
        "schema_version": "strategy_authoring_bundle.v1",
        "bundle_id": f"{candidate.idea_candidate_id}-c9-v0-bundle",
        "members": [
            {
                "spec_path": "strategy_authoring_spec.yaml",
                "allocation_weight": 1.0,
                "enabled": True,
            }
        ],
        "portfolio": {
            "allocation_method": "fixed_weight",
            "max_total_allocation_weight": 1.0,
            "selection_metric": "total_return",
            "selection_direction": "maximize",
        },
    }


def _run_strategy_backtest_pack_from_repo_root(
    inputs: StrategyBacktestPackRunInputs,
) -> Any:
    repo_root = Path(__file__).resolve().parents[3]
    old_cwd = Path.cwd()
    try:
        os.chdir(repo_root)
        return run_strategy_backtest_pack(inputs)
    finally:
        os.chdir(old_cwd)


def _source_manifest(
    *,
    candidate: StrategyIdeaCandidate,
    source: PrepWatchdeckBundle,
    symbols: list[str],
) -> dict[str, Any]:
    bid_ask_estimated = []
    for symbol in symbols:
        ticker = source.tickers_by_symbol.get(symbol)
        bid_ask_estimated.append(
            ticker is None or ticker.bid_price is None or ticker.ask_price is None
        )
    return {
        "schema_version": AUTHORING_BRIDGE_SCHEMA_VERSION,
        "candidate_id": candidate.idea_candidate_id,
        "family": candidate.family,
        "status": "BRIDGED_TECHNICAL_ONLY",
        "symbols": symbols,
        "prep_watchdeck_root": source.root.as_posix(),
        "sources": [ref.__dict__ for ref in source.sources],
        "source_statuses": source.source_statuses,
        "snapshot_source": source.snapshot_source,
        "source_exchange": source.snapshot_source.get("exchange") or "bitget",
        "source_product_type": source.snapshot_source.get("productType") or SUPPORTED_PRODUCT_TYPE,
        "authoring_execution_venue": AUTHORING_VENUE,
        "bid_ask_estimated_from_spread_bps": any(bid_ask_estimated),
        "cost_basis": "ESTIMATE_ONLY",
        "actual_cash_result_available": False,
        "known_gaps": [
            "ORDERBOOK_DEPTH_NOT_MEASURED",
            "SLIPPAGE_NOT_MEASURED",
            "LIQUIDATION_STREAM_NOT_AVAILABLE_IN_PREP_WATCHDECK",
        ],
        "boundary": CandidateBoundary().model_dump(mode="json"),
    }


def _write_blocker(
    *,
    candidate_dir: Path,
    candidate: StrategyIdeaCandidate,
    status: BridgeStatus,
    blockers: list[str],
    symbols: list[str],
    source: PrepWatchdeckBundle,
) -> Path:
    blocker_path = candidate_dir / "bridge_blocker.json"
    write_json_artifact(
        blocker_path,
        {
            "schema_version": AUTHORING_BRIDGE_SCHEMA_VERSION,
            "candidate_id": candidate.idea_candidate_id,
            "family": candidate.family,
            "status": status,
            "symbols": symbols,
            "blockers": blockers,
            "source_statuses": source.source_statuses,
            "sources": [ref.__dict__ for ref in source.sources],
            "boundary": CandidateBoundary().model_dump(mode="json"),
        },
    )
    return blocker_path


def _load_protocol_manifest(path: Path | None) -> CandidateProtocolManifest | None:
    if path is None:
        return None
    return CandidateProtocolManifest.model_validate(read_mapping_file(path))


def _load_multiplicity_account(path: Path | None) -> TrialMultiplicityAccount | None:
    if path is None:
        return None
    return TrialMultiplicityAccount.model_validate(read_mapping_file(path))


def _validate_multiplicity_account_matches_candidate_set(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    multiplicity_account: TrialMultiplicityAccount | None,
) -> None:
    if multiplicity_account is None:
        return
    summary = candidate_set.search_ledger_summary
    if multiplicity_account.candidate_count_total != summary.candidate_count_total:
        raise ValueError("multiplicity account candidate_count_total mismatch")
    if multiplicity_account.candidate_count_shortlisted != summary.candidate_count_shortlisted:
        raise ValueError("multiplicity account candidate_count_shortlisted mismatch")
    if multiplicity_account.sealed_test_used_for_selection is not False:
        raise ValueError("multiplicity account sealed_test_used_for_selection must be false")
    if multiplicity_account.success_only_reporting is not False:
        raise ValueError("multiplicity account success_only_reporting must be false")


def _artifact_ref(
    path: Path | None,
    *,
    schema_version: str,
    artifact_id: str | None,
) -> ProfitCoreArtifactRef | None:
    if path is None:
        return None
    return ProfitCoreArtifactRef(
        schema_version=schema_version,
        path=path.as_posix(),
        sha256=sha256_file(path),
        artifact_id=artifact_id,
    )


def _build_and_write_backtest_kill_gate(
    *,
    candidate: StrategyIdeaCandidate,
    protocol: CandidateProtocolManifest | None,
    multiplicity_account: TrialMultiplicityAccount | None,
    baseline_comparison_path: Path,
    stress_path: Path,
    out_path: Path,
) -> BacktestKillGateDecision:
    baseline_payload = read_mapping_file(baseline_comparison_path)
    stress_payload = read_mapping_file(stress_path)
    baseline_summary = baseline_payload.get("summary") or {}
    stress_summary = stress_payload.get("summary") or {}
    no_trade_present, no_trade_return = _cash_no_trade_baseline(baseline_payload)
    strategy_total_return = _float(baseline_summary.get("strategy_total_return"), default=0.0)
    worst_stressed_return = _float(
        stress_summary.get("worst_stressed_total_return"),
        default=strategy_total_return,
    )
    event_count = _positive_int(baseline_summary.get("return_count"), default=0)
    selection_status = _selection_adjustment_status(
        candidate=candidate,
        multiplicity_account=multiplicity_account,
    )
    gate = build_backtest_kill_gate(
        BacktestKillGateInput(
            candidate_id=candidate.idea_candidate_id,
            mode=_protocol_mode(protocol),
            family_id=candidate.family,
            event_count=event_count,
            closed_trade_count=event_count,
            no_trade_comparison_present=no_trade_present,
            after_cost_edge_over_no_trade=strategy_total_return - no_trade_return,
            stress_edge_over_no_trade=worst_stressed_return - no_trade_return,
            largest_loss_usd=0.0,
            profit_concentration=0.0,
            regime_stability="NOT_EVALUATED_C9_V0_THIN_GATE",
            source_gap_count=0,
            unexecutable_reason_count=0,
            selection_adjustment_status=selection_status,
            family_event_count_policy=_family_event_count_policy(
                candidate=candidate,
                protocol=protocol,
            ),
            execution_candidate=True,
        ),
        gate_id=f"{candidate.idea_candidate_id}-backtest-kill-gate",
        evaluated_at=datetime.now(timezone.utc).replace(microsecond=0),
    )
    write_json_artifact(out_path, gate.model_dump(mode="json", exclude_none=True))
    return gate


def _cash_no_trade_baseline(payload: dict[str, Any]) -> tuple[bool, float]:
    for row in payload.get("baselines") or []:
        if not isinstance(row, dict):
            continue
        if row.get("baseline_id") != "cash_no_trade":
            continue
        if row.get("status") != "available":
            return False, 0.0
        return True, _float(row.get("total_return"), default=0.0)
    return False, 0.0


def _selection_adjustment_status(
    *,
    candidate: StrategyIdeaCandidate,
    multiplicity_account: TrialMultiplicityAccount | None,
) -> SelectionAdjustmentStatus:
    if multiplicity_account is not None:
        return multiplicity_account.fdr_status
    status = str(candidate.selection_adjusted_metrics_status)
    if status.endswith("AVAILABLE") or status == "AVAILABLE":
        return SelectionAdjustmentStatus.AVAILABLE
    return SelectionAdjustmentStatus.NOT_ESTIMABLE


def _protocol_mode(protocol: CandidateProtocolManifest | None) -> CandidateProtocolMode:
    return protocol.mode if protocol is not None else CandidateProtocolMode.VERIFICATION_THROUGHPUT


def _family_event_count_policy(
    *,
    candidate: StrategyIdeaCandidate,
    protocol: CandidateProtocolManifest | None,
) -> FamilyEventCountPolicy:
    if protocol is not None:
        policy = protocol.family_event_count_policy.get(candidate.family)
        if policy is not None:
            return policy
    return FamilyEventCountPolicy(
        min_event_count_default=None,
        insufficient_data_state="INCONCLUSIVE_DATA",
    )


def _candidate_symbols(candidates: list[StrategyIdeaCandidate]) -> list[str]:
    return _normalize_symbols(
        [symbol for candidate in candidates for symbol in candidate.instruments]
    )


def _normalize_symbols(symbols: list[str]) -> list[str]:
    return sorted({symbol.strip().upper() for symbol in symbols if symbol.strip()})


def _label_horizon_minutes(candidate: StrategyIdeaCandidate) -> int:
    bars = _positive_int(
        candidate.parameter_set.get("holding_bars") or candidate.parameter_set.get("lookback"),
        default=2,
    )
    return max(5, bars * 5)


def _funding_rate_bps(ticker: PrepWatchdeckTicker | None) -> float | None:
    if ticker is None or ticker.funding_rate is None:
        return None
    return ticker.funding_rate * 10000


def _spread_bps_estimate(
    candidate: StrategyIdeaCandidate, ticker: PrepWatchdeckTicker | None
) -> float:
    if ticker and ticker.bid_price and ticker.ask_price and ticker.bid_price > 0:
        mid = (ticker.bid_price + ticker.ask_price) / 2
        if mid > 0:
            return (ticker.ask_price - ticker.bid_price) / mid * 10000
    return max(_positive_float(candidate.parameter_set.get("slippage_bps"), default=2.0), 1.0)


def _bid_ask(
    *, ticker: PrepWatchdeckTicker | None, mid: float, spread_bps: float
) -> tuple[float, float, bool]:
    if ticker and ticker.bid_price and ticker.ask_price:
        return ticker.bid_price, ticker.ask_price, False
    half_spread = mid * spread_bps / 20000
    return mid - half_spread, mid + half_spread, True


def _contract_max_leverage(contract: PrepWatchdeckContract | None) -> float | None:
    return contract.max_leverage if contract is not None else None


def _contract_min_trade_usdt(contract: PrepWatchdeckContract | None) -> float | None:
    return contract.min_trade_usdt if contract is not None else None


def _datetime_from_ms(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _positive_float(value: Any, *, default: float) -> float:
    parsed = _float(value, default=default)
    return parsed if parsed > 0 else default


def _float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _yaml_text(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
