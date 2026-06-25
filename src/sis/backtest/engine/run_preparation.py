from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.data_quality import (
    DataQualityReport,
    apply_period_filter,
    evaluate_data_quality,
)
from sis.backtest.engine.manifest import DataManifest, build_data_manifest
from sis.backtest.engine.run_loop import BreakoutParameters
from sis.backtest.trade_xyz.schema import normalize_trade_xyz_market_data


@dataclass(frozen=True)
class PreparedBacktestInputs:
    normalized: pl.DataFrame
    quality: DataQualityReport
    event_time_source: str
    close_source: str
    bar_builder: str | None
    manifest: DataManifest
    filtered: pl.DataFrame
    rows: list[dict[str, object]]


def prepare_backtest_inputs(
    *,
    config: BacktestConfig,
    market_data: pl.DataFrame,
    input_data_ref: str,
    breakout: BreakoutParameters,
) -> PreparedBacktestInputs:
    normalized = normalize_trade_xyz_market_data(market_data, symbol=config.symbol)
    required_min_bars = breakout.entry_lookback + breakout.exit_lookback + 3
    quality = evaluate_data_quality(
        normalized,
        config=config,
        input_row_count=market_data.height,
        required_min_bars=required_min_bars,
    )
    if quality.status == "fail":
        raise ValueError(f"data quality failed: {quality.errors}")
    event_time_source = _first_string(normalized, "event_time_source") or "event_ts"
    close_source = _first_string(normalized, "close_source") or "close"
    bar_builder = _first_string(normalized, "bar_builder")
    manifest = build_data_manifest(
        config=config,
        frame=normalized,
        input_data_ref=input_data_ref,
        data_quality=quality,
        event_time_source=event_time_source,
        close_source=close_source,
        bar_builder=bar_builder,
    )
    filtered = apply_period_filter(normalized, config=config).with_row_index("_row_index")
    return PreparedBacktestInputs(
        normalized=normalized,
        quality=quality,
        event_time_source=event_time_source,
        close_source=close_source,
        bar_builder=bar_builder,
        manifest=manifest,
        filtered=filtered,
        rows=filtered.to_dicts(),
    )


def _first_string(frame: pl.DataFrame, column: str) -> str | None:
    if column not in frame.columns or frame.is_empty():
        return None
    values = frame.get_column(column).drop_nulls().head(1).to_list()
    return str(values[0]) if values else None
