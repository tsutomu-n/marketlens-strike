from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import polars as pl

from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.signal_registry import default_signal_generator_registry
from sis.research.strategy_lab.specs import SymbolBinding

DEFAULT_STRATEGY_ID = "equity_index_momentum_v0"
DEFAULT_STRATEGY_FAMILY = "momentum"
DEFAULT_STRATEGY_VERSION = "v0"
DEFAULT_GENERATOR_ID = "qqq_trend_rates_vix"


@dataclass(frozen=True)
class SignalBuildProfile:
    generator_id: str
    strategy_id: str
    strategy_family: str
    strategy_version: str
    symbol_bindings: tuple[SymbolBinding, ...]


GENERATOR_PROFILES: dict[str, SignalBuildProfile] = {
    "qqq_trend_rates_vix": SignalBuildProfile(
        generator_id="qqq_trend_rates_vix",
        strategy_id=DEFAULT_STRATEGY_ID,
        strategy_family=DEFAULT_STRATEGY_FAMILY,
        strategy_version=DEFAULT_STRATEGY_VERSION,
        symbol_bindings=(
            SymbolBinding(
                execution_venue="trade_xyz",
                execution_symbol="XYZ100",
                real_market_symbol="QQQ",
                asset_class="basket_index",
            ),
        ),
    ),
    "sp500_trend_rates_vix": SignalBuildProfile(
        generator_id="sp500_trend_rates_vix",
        strategy_id="sp500_index_momentum_v0",
        strategy_family="momentum",
        strategy_version="v0",
        symbol_bindings=(
            SymbolBinding(
                execution_venue="trade_xyz",
                execution_symbol="SP500",
                real_market_symbol="SPY",
                asset_class="index",
            ),
        ),
    ),
}


def _profile_for_generator(generator_id: str) -> SignalBuildProfile:
    normalized = generator_id.strip()
    try:
        return GENERATOR_PROFILES[normalized]
    except KeyError as exc:
        raise KeyError(f"Unknown signal generator profile: {normalized}") from exc


def _signal_id(*, strategy_id: str, ts_signal: object, execution_symbol: str, side: str) -> str:
    raw = f"{strategy_id}|{ts_signal}|{execution_symbol}|{side}"
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
    real_market_symbol: str, profile: SignalBuildProfile
) -> str:
    normalized = real_market_symbol.strip().upper()
    for binding in profile.symbol_bindings:
        if binding.real_market_symbol == normalized:
            return binding.execution_symbol
    return normalized


def _build_strategy_signal_artifact(
    signals: pl.DataFrame, *, profile: SignalBuildProfile
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
        execution_symbol = _execution_symbol_for_real_market_symbol(real_market_symbol, profile)
        rows.append(
            {
                "schema_version": "strategy_signal.v1",
                "signal_id": _signal_id(
                    strategy_id=profile.strategy_id,
                    ts_signal=ts_signal,
                    execution_symbol=execution_symbol,
                    side=side,
                ),
                "generated_at": generated_at,
                "strategy_id": profile.strategy_id,
                "strategy_family": profile.strategy_family,
                "strategy_version": profile.strategy_version,
                "trial_id": None,
                "parameter_hash": None,
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
                "reason_codes": [str(row.get("reason") or profile.generator_id)],
                "block_reasons": [],
            }
        )
    if not rows:
        return pl.DataFrame()
    return validate_strategy_signal_frame(
        pl.DataFrame(rows),
        symbol_bindings=profile.symbol_bindings,
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
    return strategy_signals.select(
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

    profile = _profile_for_generator(generator_id)
    signals = default_signal_generator_registry().run(profile.generator_id, frame, spec=None)
    strategy_signals = _build_strategy_signal_artifact(signals, profile=profile)

    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    strategy_signals.write_parquet(parquet_out)
    _write_jsonl(strategy_signals, jsonl_out)

    out = data_dir / "research/signals.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    _legacy_export(strategy_signals).write_csv(out)
    return out
