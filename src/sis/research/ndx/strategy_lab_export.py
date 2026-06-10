from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast as type_cast

import polars as pl

from sis.research.ndx.artifacts import (
    DAG_ID,
    read_json,
    sha256_file,
    sha256_json,
    utc_now_iso,
    write_json,
)
from sis.research.strategy_lab.signal_artifact import (
    STRATEGY_SIGNAL_SCHEMA,
    StrategySignalManifest,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.specs import StrategySignalRecord, SymbolBinding

GENERATOR_ID = "ndx_layer25_residual_research_export"
STRATEGY_ID = "ndx_open_gap_residual_v1"
STRATEGY_FAMILY = "ndx_open_gap_residual"
STRATEGY_VERSION = "v1"
SIDE_POLICY = "residual_sign_directional_research_only"
RANK_POLICY = "percentile_rank_raw_score_and_abs_raw_score"
RESEARCH_ONLY_BLOCK = "RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED"
HASH_EXCLUDES = [
    "created_at",
    "strategy_signal_manifest_hash",
    "strategy_signal_manifest.generated_at",
    "replace_existing",
    "replaced_existing_artifact",
    "previous_strategy_signals_hash",
    "previous_strategy_signal_manifest_hash",
]


@dataclass(frozen=True)
class StrategyLabExportResult:
    signals_path: Path
    signal_manifest_path: Path
    export_manifest_path: Path
    report_path: Path
    export_id: str
    signal_count: int


def export_ndx_strategy_lab_research_artifact(
    *,
    data_dir: Path,
    artifact_dir: Path,
    reports_dir: Path,
    replace_existing: bool = False,
) -> StrategyLabExportResult:
    paths = _required_paths(artifact_dir=artifact_dir, reports_dir=reports_dir)
    _require_existing(paths)
    decision = read_json(paths["decision"])
    _validate_decision(decision)
    summary = read_json(paths["summary"])
    feature_manifest = read_json(paths["feature_manifest"])
    residual_manifest = read_json(paths["residual_manifest"])
    diagnostics = read_json(paths["diagnostics"])
    _validate_artifact_hashes(
        paths=paths,
        decision=decision,
        feature_manifest=feature_manifest,
        residual_manifest=residual_manifest,
        diagnostics=diagnostics,
    )

    signals_path = data_dir / "research/strategy_signals.parquet"
    signal_manifest_path = strategy_signal_manifest_path(data_dir)
    previous_hashes = _existing_strategy_signal_hashes(
        signals_path=signals_path,
        signal_manifest_path=signal_manifest_path,
    )
    if previous_hashes and not replace_existing:
        raise ValueError(
            "Strategy signal artifact already exists; use --replace-existing to overwrite: "
            f"{signals_path}"
        )

    signals = _build_signal_frame(
        feature_panel=pl.read_parquet(paths["feature_panel"]),
        residuals=pl.read_parquet(paths["residuals"]),
        neutralized=pl.read_parquet(paths["neutralized_residuals"]),
        feature_manifest_hash=str(feature_manifest["feature_manifest_hash"]),
        generated_at=_parse_datetime(str(decision["created_at"])),
    )
    binding = _symbol_binding()
    signals = validate_strategy_signal_frame(signals, symbol_bindings=[binding])
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    signals.write_parquet(signals_path)

    run_id = signal_artifact_run_id(signals)
    signal_manifest = StrategySignalManifest(
        schema_version="strategy_signal_manifest.v1",
        generated_at=_parse_datetime(str(decision["created_at"])),
        generator_id=GENERATOR_ID,
        strategy_id=STRATEGY_ID,
        strategy_family=STRATEGY_FAMILY,
        strategy_version=STRATEGY_VERSION,
        symbol_bindings=[binding],
        feature_panel_sha256=str(feature_manifest["feature_panel_hash"]),
        signal_count=signals.height,
        signal_artifact_run_id=run_id,
        signal_artifact_path=signals_path.as_posix(),
        generator_parameters={
            "side_policy": SIDE_POLICY,
            "rank_policy": RANK_POLICY,
            "research_only": True,
        },
    )
    write_strategy_signal_manifest(signal_manifest, signal_manifest_path)

    created_at = utc_now_iso()
    strategy_signals_hash = sha256_file(signals_path)
    signal_manifest_hash = sha256_file(signal_manifest_path)
    stable_payload = _stable_export_payload(
        decision=decision,
        summary=summary,
        feature_manifest=feature_manifest,
        residual_manifest=residual_manifest,
        diagnostics=diagnostics,
        paths=paths,
        signals_path=signals_path,
        signal_manifest_path=signal_manifest_path,
        strategy_signals_hash=strategy_signals_hash,
        signal_count=signals.height,
    )
    export_id = sha256_json(stable_payload)
    export_manifest = {
        **stable_payload,
        "created_at": created_at,
        "export_id": export_id,
        "strategy_signal_manifest_hash": signal_manifest_hash,
        "replace_existing": replace_existing,
        "replaced_existing_artifact": bool(previous_hashes),
        "previous_strategy_signals_hash": previous_hashes.get("strategy_signals"),
        "previous_strategy_signal_manifest_hash": previous_hashes.get("strategy_signal_manifest"),
    }
    export_manifest_path = write_json(
        artifact_dir / "strategy_lab_research_export_manifest.json",
        export_manifest,
    )
    report_path = _write_report(
        data_dir / "reports/ndx_strategy_lab_research_export_report.md",
        export_manifest=export_manifest,
    )
    return StrategyLabExportResult(
        signals_path=signals_path,
        signal_manifest_path=signal_manifest_path,
        export_manifest_path=export_manifest_path,
        report_path=report_path,
        export_id=export_id,
        signal_count=signals.height,
    )


def _required_paths(*, artifact_dir: Path, reports_dir: Path) -> dict[str, Path]:
    return {
        "decision": artifact_dir / "residual_validation_decision.json",
        "summary": artifact_dir / "residual_validation_summary.json",
        "feature_panel": artifact_dir / "ndx_feature_panel.parquet",
        "feature_manifest": artifact_dir / "ndx_feature_manifest.json",
        "residuals": artifact_dir / "open_gap_residuals.parquet",
        "residual_manifest": artifact_dir / "open_gap_residual_manifest.json",
        "neutralized_residuals": reports_dir / "neutralized_residuals.parquet",
        "diagnostics": reports_dir / "ndx_residual_diagnostics.json",
    }


def _require_existing(paths: dict[str, Path]) -> None:
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"NDX Layer 2.5 required inputs missing: {sorted(missing)}")


def _validate_decision(decision: dict[str, Any]) -> None:
    if decision.get("dag_id") != DAG_ID:
        raise ValueError("Layer 2.4 decision dag_id mismatch.")
    if decision.get("decision") != "APPROVE_STRATEGY_LAB_EXPORT":
        raise ValueError(f"Layer 2.4 decision is not approved: {decision.get('decision')}")
    if decision.get("permits_strategy_lab_research_only_export") is not True:
        raise ValueError("Layer 2.4 decision does not permit Strategy Lab research export.")
    for key in (
        "permits_backtest",
        "permits_paper_candidate",
        "permits_paper_intent_preview",
        "permits_live_order",
    ):
        if decision.get(key) is not False:
            raise ValueError(f"Layer 2.4 decision must keep {key}=false.")


def _validate_artifact_hashes(
    *,
    paths: dict[str, Path],
    decision: dict[str, Any],
    feature_manifest: dict[str, Any],
    residual_manifest: dict[str, Any],
    diagnostics: dict[str, Any],
) -> None:
    for payload_name, payload in (
        ("feature_manifest", feature_manifest),
        ("residual_manifest", residual_manifest),
        ("diagnostics", diagnostics),
    ):
        if payload.get("dag_id") != DAG_ID:
            raise ValueError(f"{payload_name} dag_id mismatch.")
    if not str(decision.get("summary_path", "")).endswith("residual_validation_summary.json"):
        raise ValueError("Layer 2.4 decision summary_path is invalid.")
    feature_manifest_hash = str(feature_manifest.get("feature_manifest_hash") or "")
    expected_feature_manifest_hash = sha256_json(
        {key: value for key, value in feature_manifest.items() if key != "feature_manifest_hash"}
    )
    if feature_manifest_hash != expected_feature_manifest_hash:
        raise ValueError("feature manifest hash mismatch.")
    if sha256_file(paths["feature_panel"]) != feature_manifest.get("feature_panel_hash"):
        raise ValueError("feature panel hash mismatch.")
    if sha256_file(paths["residuals"]) != residual_manifest.get("residuals_hash"):
        raise ValueError("residuals hash mismatch.")
    if sha256_file(paths["neutralized_residuals"]) != diagnostics.get("neutralized_residuals_hash"):
        raise ValueError("neutralized residuals hash mismatch.")
    for payload_name, payload in (
        ("residual_manifest", residual_manifest),
        ("diagnostics", diagnostics),
    ):
        if str(payload.get("feature_manifest_hash")) != feature_manifest_hash:
            raise ValueError(f"{payload_name} feature_manifest_hash mismatch.")
        if str(payload.get("dag_artifact_hash")) != str(feature_manifest.get("dag_artifact_hash")):
            raise ValueError(f"{payload_name} dag_artifact_hash mismatch.")


def _existing_strategy_signal_hashes(
    *,
    signals_path: Path,
    signal_manifest_path: Path,
) -> dict[str, str | None]:
    exists = signals_path.exists() or signal_manifest_path.exists()
    if not exists:
        return {}
    return {
        "strategy_signals": sha256_file(signals_path) if signals_path.exists() else None,
        "strategy_signal_manifest": (
            sha256_file(signal_manifest_path) if signal_manifest_path.exists() else None
        ),
    }


def _build_signal_frame(
    *,
    feature_panel: pl.DataFrame,
    residuals: pl.DataFrame,
    neutralized: pl.DataFrame,
    feature_manifest_hash: str,
    generated_at: datetime,
) -> pl.DataFrame:
    required_feature_columns = {"date", "feature_ts", "dag_id", "dag_artifact_hash"}
    missing_feature = required_feature_columns - set(feature_panel.columns)
    if missing_feature:
        raise ValueError(f"feature panel missing columns: {sorted(missing_feature)}")
    for name, frame, columns in (
        ("residuals", residuals, {"date", "open_gap_residual"}),
        ("neutralized_residuals", neutralized, {"date", "combined_neutralized_residual"}),
    ):
        missing = columns - set(frame.columns)
        if missing:
            raise ValueError(f"{name} missing columns: {sorted(missing)}")
    joined = (
        residuals.select(["date", "open_gap_residual"])
        .join(
            neutralized.select(["date", "combined_neutralized_residual"]),
            on="date",
            how="inner",
        )
        .join(
            feature_panel.select(
                ["date", "feature_ts", "dag_id", "dag_artifact_hash", "source_ts_max"]
            ),
            on="date",
            how="inner",
        )
        .sort("date")
    )
    if joined.height != residuals.height or joined.height != neutralized.height:
        raise ValueError("residual, neutralized, and feature panel rows do not align by date.")
    scores = [float(value) for value in joined.get_column("combined_neutralized_residual")]
    percentile_ranks = _percentile_ranks(scores)
    rank_scores = _percentile_ranks([abs(value) for value in scores])
    max_abs = max([abs(value) for value in scores], default=0.0)
    records: list[dict[str, Any]] = []
    for index, row in enumerate(joined.to_dicts()):
        raw_score = scores[index]
        ts_signal = _parse_datetime(str(row["feature_ts"]))
        side = "long" if raw_score > 0 else "short" if raw_score < 0 else "none"
        percentile_rank = percentile_ranks[index]
        records.append(
            StrategySignalRecord(
                schema_version="strategy_signal.v1",
                signal_id=_signal_id(ts_signal=ts_signal, raw_score=raw_score),
                generated_at=generated_at,
                strategy_id=STRATEGY_ID,
                strategy_family=STRATEGY_FAMILY,
                strategy_version=STRATEGY_VERSION,
                trial_id=None,
                parameter_hash=None,
                ts_signal=ts_signal,
                timeframe="1d",
                execution_venue="trade_xyz",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                side=side,
                raw_score=raw_score,
                rank_score=rank_scores[index],
                percentile_rank=percentile_rank,
                tail_bucket=_tail_bucket(percentile_rank),
                confidence=0.0 if max_abs == 0.0 else min(1.0, abs(raw_score) / max_abs),
                source_confidence=None,
                venue_quality_score=None,
                feature_snapshot_ref=f"ndx_feature_manifest:{feature_manifest_hash}:{row['date']}",
                quote_ref=None,
                tracking_ref=None,
                reason_codes=["ndx_layer25_research_export", "approved_residual_validation"],
                block_reasons=[RESEARCH_ONLY_BLOCK],
            ).model_dump(mode="python")
        )
    return pl.DataFrame(records).cast(type_cast(Any, STRATEGY_SIGNAL_SCHEMA))


def _percentile_ranks(values: list[float]) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [1.0]
    sorted_pairs = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    denominator = len(values) - 1
    for rank, (_value, index) in enumerate(sorted_pairs):
        ranks[index] = rank / denominator
    return ranks


def _tail_bucket(percentile_rank: float) -> Literal["top", "middle", "bottom", "none"]:
    if percentile_rank >= 0.8:
        return "top"
    if percentile_rank <= 0.2:
        return "bottom"
    return "middle"


def _signal_id(*, ts_signal: datetime, raw_score: float) -> str:
    payload = {
        "strategy_id": STRATEGY_ID,
        "ts_signal": ts_signal.isoformat(),
        "raw_score": raw_score,
    }
    return sha256_json(payload).removeprefix("sha256:")[:16]


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _symbol_binding() -> SymbolBinding:
    return SymbolBinding(
        execution_venue="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        asset_class="equity_index_proxy",
        country="US",
    )


def _stable_export_payload(
    *,
    decision: dict[str, Any],
    summary: dict[str, Any],
    feature_manifest: dict[str, Any],
    residual_manifest: dict[str, Any],
    diagnostics: dict[str, Any],
    paths: dict[str, Path],
    signals_path: Path,
    signal_manifest_path: Path,
    strategy_signals_hash: str,
    signal_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": "ndx_strategy_lab_research_export_manifest.v1",
        "dag_id": DAG_ID,
        "source_decision": decision["decision"],
        "source_decision_id": decision["decision_id"],
        "source_decision_path": paths["decision"].as_posix(),
        "source_summary_path": paths["summary"].as_posix(),
        "source_reason_codes": list(decision.get("reason_codes") or []),
        "source_thresholds": summary.get("thresholds", {}),
        "feature_panel_path": paths["feature_panel"].as_posix(),
        "feature_panel_hash": feature_manifest["feature_panel_hash"],
        "residuals_path": paths["residuals"].as_posix(),
        "residuals_hash": residual_manifest["residuals_hash"],
        "neutralized_residuals_path": paths["neutralized_residuals"].as_posix(),
        "neutralized_residuals_hash": diagnostics["neutralized_residuals_hash"],
        "strategy_signals_path": signals_path.as_posix(),
        "strategy_signals_hash": strategy_signals_hash,
        "strategy_signal_manifest_path": signal_manifest_path.as_posix(),
        "signal_count": signal_count,
        "strategy_id": STRATEGY_ID,
        "strategy_family": STRATEGY_FAMILY,
        "strategy_version": STRATEGY_VERSION,
        "generator_id": GENERATOR_ID,
        "tested_variant_count": 1,
        "side_policy": SIDE_POLICY,
        "rank_policy": RANK_POLICY,
        "hash_excludes": HASH_EXCLUDES,
        "research_only": True,
        "permits_backtest": False,
        "permits_paper_candidate": False,
        "permits_paper_intent_preview": False,
        "permits_live_order": False,
        "external_api_used": False,
        "credentials_used": False,
        "wallet_used": False,
        "venue_write_used": False,
    }


def _write_report(path: Path, *, export_manifest: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Strategy Lab Research Export\n\n"
        f"- export_id: {export_manifest['export_id']}\n"
        f"- signal_count: {export_manifest['signal_count']}\n"
        "- research_only: true\n"
        "- permits_backtest: false\n"
        "- permits_paper_candidate: false\n"
        "- permits_paper_intent_preview: false\n"
        "- permits_live_order: false\n",
        encoding="utf-8",
    )
    return path
