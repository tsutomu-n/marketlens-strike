from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import polars as pl
from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.specs import SymbolBinding

STRATEGY_SIGNAL_MANIFEST_FILENAME = "strategy_signal_manifest.json"

SIGNAL_IDENTITY_COLUMNS = (
    "strategy_id",
    "strategy_family",
    "strategy_version",
    "execution_venue",
    "execution_symbol",
    "real_market_symbol",
)

SIGNAL_RUN_ID_COLUMNS = (
    "schema_version",
    "signal_id",
    "strategy_id",
    "strategy_family",
    "strategy_version",
    "parameter_hash",
    "ts_signal",
    "timeframe",
    "execution_venue",
    "execution_symbol",
    "real_market_symbol",
    "side",
    "raw_score",
    "rank_score",
    "percentile_rank",
    "tail_bucket",
    "confidence",
    "source_confidence",
    "venue_quality_score",
    "feature_snapshot_ref",
    "quote_ref",
    "tracking_ref",
    "stop_loss_bps",
    "take_profit_bps",
    "trailing_stop_bps",
    "partial_take_profit_bps",
    "partial_exit_fraction",
    "min_holding_minutes",
    "exit_on_opposite_signal",
    "exit_on_close_signal",
    "exit_on_reduce_signal",
    "reduce_fraction",
    "exit_on_add_signal",
    "add_fraction",
    "exit_on_rebalance_signal",
    "rebalance_target_fraction",
    "bracket_type",
    "bracket_time_stop_minutes",
    "bracket_break_even_after_bps",
    "entry_order_type",
    "entry_limit_offset_bps",
    "entry_stop_offset_bps",
    "entry_timeout_minutes",
    "slippage_bps",
    "max_fill_fraction",
    "max_spread_bps",
    "min_depth_usd",
    "depth_column",
    "depth_participation_rate",
    "max_latency_ms",
    "latency_ms",
    "min_queue_position_score",
    "queue_position_score",
    "min_borrow_availability_ratio",
    "borrow_availability_ratio",
    "max_borrow_cost_bps",
    "borrow_cost_bps",
    "max_tax_drag_bps",
    "tax_drag_bps",
    "max_turnover_pressure",
    "turnover_pressure",
    "min_fee_edge_bps",
    "fee_edge_bps",
    "position_weight",
    "notional_usd",
    "reason_codes",
    "block_reasons",
)

STRATEGY_SIGNAL_SCHEMA: dict[str, Any] = {
    "schema_version": pl.Utf8,
    "signal_id": pl.Utf8,
    "generated_at": pl.Datetime(time_zone="UTC"),
    "strategy_id": pl.Utf8,
    "strategy_family": pl.Utf8,
    "strategy_version": pl.Utf8,
    "trial_id": pl.Utf8,
    "parameter_hash": pl.Utf8,
    "ts_signal": pl.Datetime(time_zone="UTC"),
    "timeframe": pl.Utf8,
    "execution_venue": pl.Utf8,
    "execution_symbol": pl.Utf8,
    "real_market_symbol": pl.Utf8,
    "side": pl.Utf8,
    "raw_score": pl.Float64,
    "rank_score": pl.Float64,
    "percentile_rank": pl.Float64,
    "tail_bucket": pl.Utf8,
    "confidence": pl.Float64,
    "source_confidence": pl.Float64,
    "venue_quality_score": pl.Float64,
    "feature_snapshot_ref": pl.Utf8,
    "quote_ref": pl.Utf8,
    "tracking_ref": pl.Utf8,
    "stop_loss_bps": pl.Float64,
    "take_profit_bps": pl.Float64,
    "trailing_stop_bps": pl.Float64,
    "partial_take_profit_bps": pl.Float64,
    "partial_exit_fraction": pl.Float64,
    "min_holding_minutes": pl.Int64,
    "exit_on_opposite_signal": pl.Boolean,
    "exit_on_close_signal": pl.Boolean,
    "exit_on_reduce_signal": pl.Boolean,
    "reduce_fraction": pl.Float64,
    "exit_on_add_signal": pl.Boolean,
    "add_fraction": pl.Float64,
    "exit_on_rebalance_signal": pl.Boolean,
    "rebalance_target_fraction": pl.Float64,
    "bracket_type": pl.Utf8,
    "bracket_time_stop_minutes": pl.Int64,
    "bracket_break_even_after_bps": pl.Float64,
    "entry_order_type": pl.Utf8,
    "entry_limit_offset_bps": pl.Float64,
    "entry_stop_offset_bps": pl.Float64,
    "entry_timeout_minutes": pl.Int64,
    "slippage_bps": pl.Float64,
    "max_fill_fraction": pl.Float64,
    "max_spread_bps": pl.Float64,
    "min_depth_usd": pl.Float64,
    "depth_column": pl.Utf8,
    "depth_participation_rate": pl.Float64,
    "max_latency_ms": pl.Float64,
    "latency_ms": pl.Float64,
    "min_queue_position_score": pl.Float64,
    "queue_position_score": pl.Float64,
    "min_borrow_availability_ratio": pl.Float64,
    "borrow_availability_ratio": pl.Float64,
    "max_borrow_cost_bps": pl.Float64,
    "borrow_cost_bps": pl.Float64,
    "max_tax_drag_bps": pl.Float64,
    "tax_drag_bps": pl.Float64,
    "max_turnover_pressure": pl.Float64,
    "turnover_pressure": pl.Float64,
    "min_fee_edge_bps": pl.Float64,
    "fee_edge_bps": pl.Float64,
    "position_weight": pl.Float64,
    "notional_usd": pl.Float64,
    "reason_codes": pl.List(pl.Utf8),
    "block_reasons": pl.List(pl.Utf8),
}


class StrategySignalManifest(BaseModel):
    schema_version: Literal["strategy_signal_manifest.v1"]
    generated_at: datetime
    generator_id: str
    strategy_id: str
    strategy_family: str
    strategy_version: str
    symbol_bindings: list[SymbolBinding]
    feature_panel_sha256: str
    signal_count: int
    signal_artifact_run_id: str
    signal_artifact_path: str = "data/research/strategy_signals.parquet"
    generator_parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_manifest(self) -> StrategySignalManifest:
        for field_name in (
            "generator_id",
            "strategy_id",
            "strategy_family",
            "strategy_version",
            "feature_panel_sha256",
            "signal_artifact_run_id",
            "signal_artifact_path",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if not self.symbol_bindings:
            raise ValueError("symbol_bindings must be non-empty")
        if self.signal_count < 0:
            raise ValueError("signal_count must be >= 0")
        return self


def empty_strategy_signal_frame() -> pl.DataFrame:
    return pl.DataFrame(schema=STRATEGY_SIGNAL_SCHEMA)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def strategy_signal_manifest_path(data_dir: Path) -> Path:
    return data_dir / "research" / STRATEGY_SIGNAL_MANIFEST_FILENAME


def read_strategy_signal_manifest(path: Path) -> StrategySignalManifest:
    return StrategySignalManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def write_strategy_signal_manifest(manifest: StrategySignalManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def require_single_signal_identity(frame: pl.DataFrame) -> dict[str, Any]:
    if frame.is_empty():
        return {}
    missing = [column for column in SIGNAL_IDENTITY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Strategy signal artifact missing identity columns: {missing}")
    identities = frame.select(list(SIGNAL_IDENTITY_COLUMNS)).unique()
    if identities.height != 1:
        raise ValueError(
            "Strategy signal artifact contains mixed strategy/symbol identities; "
            "rebuild one generator per strategy_signals.parquet artifact."
        )
    return identities.to_dicts()[0]


def run_id_from_trial_group(trial_group_id: str | None) -> str:
    text = str(trial_group_id or "").strip()
    if text.startswith("trial-group-"):
        return text.removeprefix("trial-group-")
    if not text:
        return "empty"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def run_id_from_pack_id(pack_id: str) -> str:
    text = str(pack_id).strip()
    if text.startswith("paper-pack-"):
        return text.removeprefix("paper-pack-")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def empty_signal_artifact_run_id(
    *,
    generator_id: str,
    strategy_id: str,
    strategy_family: str,
    strategy_version: str,
    symbol_bindings: tuple[SymbolBinding, ...] | list[SymbolBinding],
    feature_panel_sha256: str,
) -> str:
    return _stable_digest(
        {
            "generator_id": generator_id,
            "strategy_id": strategy_id,
            "strategy_family": strategy_family,
            "strategy_version": strategy_version,
            "symbol_bindings": [
                binding.model_dump(mode="json")
                for binding in sorted(
                    symbol_bindings,
                    key=lambda item: (item.execution_venue, item.execution_symbol),
                )
            ],
            "feature_panel_sha256": feature_panel_sha256,
            "signal_count": 0,
        }
    )


def signal_artifact_run_id(frame: pl.DataFrame) -> str:
    if frame.is_empty():
        raise ValueError("Empty strategy signal artifact requires a manifest run id.")
    columns = [column for column in SIGNAL_RUN_ID_COLUMNS if column in frame.columns]
    if not columns:
        return hashlib.sha256(b"strategy-signals:missing-run-columns").hexdigest()[:12]
    stable_frame = frame.select(columns)
    sort_columns = [
        column
        for column in (
            "strategy_id",
            "strategy_version",
            "execution_symbol",
            "real_market_symbol",
            "ts_signal",
            "signal_id",
        )
        if column in columns
    ]
    if sort_columns:
        stable_frame = stable_frame.sort(sort_columns)
    return _stable_digest(stable_frame.to_dicts())


def latest_signal_row(frame: pl.DataFrame) -> dict[str, Any]:
    if frame.is_empty():
        return {}
    return frame.sort(["ts_signal", "signal_id"], descending=[True, False]).to_dicts()[0]


def _stable_digest(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
