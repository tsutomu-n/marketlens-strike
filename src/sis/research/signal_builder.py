from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from sis.research.strategy_lab.specs import StrategyExperimentSpec
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    empty_signal_artifact_run_id,
    empty_strategy_signal_frame,
    file_sha256,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.signal_registry import (
    SignalGeneratorDefinition,
    default_signal_generator_registry,
)

DEFAULT_GENERATOR_ID = "qqq_trend_rates_vix"


def _stable_digest(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _signal_id(
    *,
    strategy_id: str,
    ts_signal: object,
    execution_symbol: str,
    side: str,
    parameter_hash: str | None = None,
) -> str:
    raw = f"{strategy_id}|{parameter_hash or 'default'}|{ts_signal}|{execution_symbol}|{side}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _rank_bucket(rank_score: float | None) -> str:
    if rank_score is None:
        return "none"
    if rank_score >= 0.8:
        return "top"
    if rank_score <= 0.2:
        return "bottom"
    return "middle"


def _execution_symbol_for_real_market_symbol(
    real_market_symbol: str, definition: SignalGeneratorDefinition
) -> str:
    normalized = real_market_symbol.strip().upper()
    for binding in definition.symbol_bindings:
        if binding.real_market_symbol == normalized:
            return binding.execution_symbol
    return normalized


def _build_strategy_signal_artifact(
    signals: pl.DataFrame,
    *,
    definition: SignalGeneratorDefinition,
    parameter_hash: str | None = None,
    variant_reason_code: str | None = None,
) -> pl.DataFrame:
    rows: list[dict] = []
    generated_at = datetime.now(timezone.utc)
    for row in signals.to_dicts():
        ts_signal = row["ts_signal"]
        side = str(row["side"])
        signal_strength = row.get("signal_strength")
        raw_score = float(signal_strength) if isinstance(signal_strength, int | float) else None
        rank_score = None
        if raw_score is not None:
            rank_score = max(0.0, min(1.0, raw_score))
        real_market_symbol = str(row["canonical_symbol"]).upper()
        execution_symbol = _execution_symbol_for_real_market_symbol(real_market_symbol, definition)
        rows.append(
            {
                "schema_version": "strategy_signal.v1",
                "signal_id": _signal_id(
                    strategy_id=definition.strategy_id,
                    ts_signal=ts_signal,
                    execution_symbol=execution_symbol,
                    side=side,
                    parameter_hash=parameter_hash,
                ),
                "generated_at": generated_at,
                "strategy_id": definition.strategy_id,
                "strategy_family": definition.strategy_family,
                "strategy_version": definition.strategy_version,
                "trial_id": None,
                "parameter_hash": parameter_hash,
                "ts_signal": ts_signal,
                "timeframe": str(row["timeframe"]),
                "execution_venue": "trade_xyz",
                "execution_symbol": execution_symbol,
                "real_market_symbol": real_market_symbol,
                "side": side,
                "raw_score": raw_score,
                "rank_score": rank_score,
                "percentile_rank": rank_score,
                "tail_bucket": _rank_bucket(rank_score),
                "confidence": 0.7,
                "source_confidence": row.get("source_confidence"),
                "venue_quality_score": row.get("venue_quality_score"),
                "feature_snapshot_ref": None,
                "quote_ref": None,
                "tracking_ref": None,
                "reason_codes": [
                    item
                    for item in [
                        str(row.get("reason") or definition.generator_id),
                        variant_reason_code,
                    ]
                    if item
                ],
                "block_reasons": [],
            }
        )
    if not rows:
        return empty_strategy_signal_frame()
    return validate_strategy_signal_frame(
        pl.DataFrame(rows),
        symbol_bindings=definition.symbol_bindings,
    )


def _write_jsonl(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in frame.to_dicts():
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _legacy_export(strategy_signals: pl.DataFrame) -> pl.DataFrame:
    if strategy_signals.is_empty():
        return pl.DataFrame(
            schema={
                "ts_signal": pl.Datetime(time_zone="UTC"),
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "timeframe": pl.Utf8,
                "signal_strength": pl.Float64,
                "strategy_name": pl.Utf8,
                "reason": pl.Utf8,
            }
        )
    trade_signals = strategy_signals.filter(pl.col("side").is_in(["long", "short"]))
    if trade_signals.is_empty():
        return pl.DataFrame(
            schema={
                "ts_signal": pl.Datetime(time_zone="UTC"),
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "timeframe": pl.Utf8,
                "signal_strength": pl.Float64,
                "strategy_name": pl.Utf8,
                "reason": pl.Utf8,
            }
        )
    return trade_signals.select(
        pl.col("ts_signal"),
        pl.col("execution_symbol").alias("canonical_symbol"),
        pl.col("side"),
        pl.col("timeframe"),
        pl.col("raw_score").alias("signal_strength"),
        pl.col("strategy_id").alias("strategy_name"),
        pl.col("reason_codes").list.join("|").alias("reason"),
    )


def build_signals(data_dir: Path, *, generator_id: str = DEFAULT_GENERATOR_ID) -> Path:
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    if not feature_panel_path.exists():
        raise FileNotFoundError(f"Research feature panel not found: {feature_panel_path}")

    frame = pl.read_parquet(feature_panel_path)
    if frame.is_empty():
        raise ValueError("Feature panel is empty.")

    registry = default_signal_generator_registry()
    definition = registry.definition(generator_id)
    signals = registry.run(definition.generator_id, frame, spec=None)
    strategy_signals = _build_strategy_signal_artifact(signals, definition=definition)
    feature_panel_sha256 = file_sha256(feature_panel_path)
    if strategy_signals.is_empty():
        run_id = empty_signal_artifact_run_id(
            generator_id=definition.generator_id,
            strategy_id=definition.strategy_id,
            strategy_family=definition.strategy_family,
            strategy_version=definition.strategy_version,
            symbol_bindings=definition.symbol_bindings,
            feature_panel_sha256=feature_panel_sha256,
        )
    else:
        run_id = signal_artifact_run_id(strategy_signals)

    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    strategy_signals.write_parquet(parquet_out)
    _write_jsonl(strategy_signals, jsonl_out)
    write_strategy_signal_manifest(
        StrategySignalManifest(
            schema_version="strategy_signal_manifest.v1",
            generated_at=datetime.now(timezone.utc),
            generator_id=definition.generator_id,
            strategy_id=definition.strategy_id,
            strategy_family=definition.strategy_family,
            strategy_version=definition.strategy_version,
            symbol_bindings=list(definition.symbol_bindings),
            feature_panel_sha256=feature_panel_sha256,
            signal_count=strategy_signals.height,
            signal_artifact_run_id=run_id,
        ),
        strategy_signal_manifest_path(data_dir),
    )

    out = data_dir / "research/signals.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    _legacy_export(strategy_signals).write_csv(out)
    return out


def load_strategy_experiment_spec(path: Path) -> StrategyExperimentSpec:
    text = path.read_text(encoding="utf-8")
    payload = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError("StrategyExperimentSpec file must contain an object")
    return StrategyExperimentSpec.model_validate(payload)


def _parameter_grid_variants(
    parameter_grid: dict[str, list[Any]], *, max_variants: int
) -> list[dict[str, Any]]:
    if max_variants <= 0:
        raise ValueError("max_variants must be positive")
    if not parameter_grid:
        return [{}]
    keys = sorted(parameter_grid)
    values_by_key: list[list[Any]] = []
    for key in keys:
        values = parameter_grid[key]
        if not values:
            raise ValueError(f"parameter_grid.{key} must not be empty")
        values_by_key.append(values)
    variants = [dict(zip(keys, values, strict=True)) for values in product(*values_by_key)]
    if len(variants) > max_variants:
        raise ValueError(
            f"parameter_grid expands to {len(variants)} variants, max_variants={max_variants}"
        )
    return variants


def build_signals_from_experiment_spec(
    data_dir: Path, *, spec: StrategyExperimentSpec, max_variants: int = 64
) -> Path:
    if not spec.enabled:
        raise ValueError(f"StrategyExperimentSpec is disabled: {spec.strategy_id}")
    feature_panel_path = data_dir / "research/feature_panel.parquet"
    if not feature_panel_path.exists():
        raise FileNotFoundError(f"Research feature panel not found: {feature_panel_path}")

    frame = pl.read_parquet(feature_panel_path)
    if frame.is_empty():
        raise ValueError("Feature panel is empty.")

    registry = default_signal_generator_registry()
    registered_definition = registry.definition(spec.generator_id)
    experiment_definition = SignalGeneratorDefinition(
        generator_id=spec.generator_id,
        strategy_id=spec.strategy_id,
        strategy_family=spec.strategy_family,
        strategy_version=spec.strategy_version,
        symbol_bindings=tuple(spec.symbol_bindings),
        build=registered_definition.build,
    )
    strategy_signal_frames: list[pl.DataFrame] = []
    for variant in _parameter_grid_variants(spec.parameter_grid, max_variants=max_variants):
        variant_hash = _stable_digest(variant) if variant else None
        variant_spec = spec.model_copy(
            update={"parameter_grid": {key: [value] for key, value in variant.items()}}
        )
        signals = registered_definition.build(frame, variant_spec)
        strategy_signal_frames.append(
            _build_strategy_signal_artifact(
                signals,
                definition=experiment_definition,
                parameter_hash=variant_hash,
                variant_reason_code=f"parameter_grid:{variant_hash}" if variant_hash else None,
            )
        )
    non_empty_frames = [frame for frame in strategy_signal_frames if not frame.is_empty()]
    strategy_signals = (
        pl.concat(non_empty_frames, how="vertical")
        if non_empty_frames
        else empty_strategy_signal_frame()
    )
    feature_panel_sha256 = file_sha256(feature_panel_path)
    if strategy_signals.is_empty():
        run_id = empty_signal_artifact_run_id(
            generator_id=spec.generator_id,
            strategy_id=spec.strategy_id,
            strategy_family=spec.strategy_family,
            strategy_version=spec.strategy_version,
            symbol_bindings=spec.symbol_bindings,
            feature_panel_sha256=feature_panel_sha256,
        )
    else:
        run_id = signal_artifact_run_id(strategy_signals)

    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    strategy_signals.write_parquet(parquet_out)
    _write_jsonl(strategy_signals, jsonl_out)
    write_strategy_signal_manifest(
        StrategySignalManifest(
            schema_version="strategy_signal_manifest.v1",
            generated_at=datetime.now(timezone.utc),
            generator_id=spec.generator_id,
            strategy_id=spec.strategy_id,
            strategy_family=spec.strategy_family,
            strategy_version=spec.strategy_version,
            symbol_bindings=list(spec.symbol_bindings),
            feature_panel_sha256=feature_panel_sha256,
            signal_count=strategy_signals.height,
            signal_artifact_run_id=run_id,
        ),
        strategy_signal_manifest_path(data_dir),
    )

    out = data_dir / "research/signals.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    _legacy_export(strategy_signals).write_csv(out)
    return out
