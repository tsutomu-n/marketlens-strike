from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    empty_signal_artifact_run_id,
    signal_artifact_run_id,
)


def evaluation_window(spec: StrategyAuthoringSpec) -> dict[str, str | None]:
    return {
        "evaluation_start_at": (
            spec.backtest.evaluation_start_at.isoformat()
            if spec.backtest.evaluation_start_at is not None
            else None
        ),
        "evaluation_end_at": (
            spec.backtest.evaluation_end_at.isoformat()
            if spec.backtest.evaluation_end_at is not None
            else None
        ),
        "boundary": "evaluation_start_at <= ts_signal < evaluation_end_at",
    }


def apply_evaluation_window(spec: StrategyAuthoringSpec, frame: pl.DataFrame) -> pl.DataFrame:
    if spec.backtest.evaluation_start_at is None or spec.backtest.evaluation_end_at is None:
        return frame
    if "ts_signal" not in frame.columns:
        raise ValueError("Strategy signal frame missing ts_signal for evaluation window")
    start = _normalize_utc(spec.backtest.evaluation_start_at)
    end = _normalize_utc(spec.backtest.evaluation_end_at)
    return frame.filter((pl.col("ts_signal") >= start) & (pl.col("ts_signal") < end))


def evaluation_counts(
    spec: StrategyAuthoringSpec, source_frame: pl.DataFrame, evaluation_frame: pl.DataFrame
) -> dict[str, Any]:
    return {
        "source_signal_count": source_frame.height,
        "evaluation_signal_count": evaluation_frame.height,
        "evaluation_window": evaluation_window(spec),
    }


def manifest_for_evaluation_frame(
    spec: StrategyAuthoringSpec,
    source_frame: pl.DataFrame,
    evaluation_frame: pl.DataFrame,
    manifest: StrategySignalManifest,
) -> StrategySignalManifest:
    parameters = {
        **manifest.generator_parameters,
        **evaluation_counts(spec, source_frame, evaluation_frame),
    }
    run_id = (
        empty_signal_artifact_run_id(
            generator_id=manifest.generator_id,
            strategy_id=manifest.strategy_id,
            strategy_family=manifest.strategy_family,
            strategy_version=manifest.strategy_version,
            symbol_bindings=manifest.symbol_bindings,
            feature_panel_sha256=manifest.feature_panel_sha256,
        )
        if evaluation_frame.is_empty()
        else signal_artifact_run_id(evaluation_frame)
    )
    return manifest.model_copy(
        update={
            "signal_count": evaluation_frame.height,
            "signal_artifact_run_id": run_id,
            "generator_parameters": parameters,
        }
    )


def capital_metrics(
    spec: StrategyAuthoringSpec, aggregate_metrics: dict[str, Any]
) -> dict[str, Any]:
    initial = float(spec.backtest.initial_capital_usd)
    total_return = _float_or_none(aggregate_metrics.get("total_return")) or 0.0
    max_drawdown = _float_or_none(aggregate_metrics.get("max_drawdown"))
    net_pnl = initial * total_return
    return {
        "initial_capital_usd": initial,
        "net_pnl_usd": net_pnl,
        "ending_equity_usd": initial + net_pnl,
        "max_drawdown_loss_usd": abs(max_drawdown) * initial if max_drawdown is not None else None,
    }


def _normalize_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
