from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.research.strategy_lab.authoring import (
    build_authoring_signals,
    load_authoring_spec,
    strategy_signals_to_research_signals,
    template_yaml,
    validate_authoring_inputs,
    write_authoring_signal_artifacts,
)

runner = CliRunner()


def _write_spec(path: Path) -> None:
    path.write_text(template_yaml(), encoding="utf-8")


def _feature_rows() -> list[dict]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "ts": start + timedelta(hours=4 * index),
            "canonical_symbol": "QQQ",
            "trade_allowed": True,
            "close_above_sma20": True,
            "vix_level": 20.0,
            "research_return_1d": 0.02,
            "research_return_4h": 0.01,
            "source_confidence": 0.8,
            "venue_quality_score": 0.9,
            "atr_stop_bps": 150.0,
            "atr_take_profit_bps": 300.0,
            "direction": "long",
        }
        for index in range(3)
    ]


def _quote(ts: datetime, price: float) -> dict:
    return {
        "ts_client": ts.isoformat(),
        "venue": "trade_xyz",
        "canonical_symbol": "XYZ100",
        "venue_symbol": "XYZ100",
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
        "spread_bps": 1.0,
        "min_side_depth_10bps_usd": 10_000.0,
        "oracle_ts_ms": int(ts.timestamp() * 1000),
        "market_status": "open",
        "is_tradable": True,
    }


def _write_data(data_dir: Path) -> None:
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _feature_rows()
    pl.DataFrame(rows).write_parquet(feature_path)
    quotes = []
    for index in range(5):
        quotes.append(_quote(rows[0]["ts"] + timedelta(hours=index * 4), 100.0 + index))
    pl.DataFrame(quotes).write_parquet(quote_path)


def test_authoring_spec_validates_feature_columns_and_builds_strategy_signals(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []

    frame, manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.height == 3
    assert set(frame.get_column("execution_symbol").to_list()) == {"XYZ100"}
    assert set(frame.get_column("real_market_symbol").to_list()) == {"QQQ"}
    assert set(frame.get_column("reason_codes").to_list()[0]) == {"trend_pullback_authoring_v1"}
    assert set(frame.get_column("stop_loss_bps").to_list()) == {150.0}
    assert set(frame.get_column("take_profit_bps").to_list()) == {300.0}
    assert set(frame.get_column("trailing_stop_bps").to_list()) == {120.0}
    assert set(frame.get_column("partial_take_profit_bps").to_list()) == {200.0}
    assert set(frame.get_column("partial_exit_fraction").to_list()) == {0.5}
    assert set(frame.get_column("position_weight").to_list()) == {1.0}
    assert set(frame.get_column("notional_usd").to_list()) == {1000.0}
    assert manifest.generator_id == "strategy_authoring"
    assert manifest.signal_count == 3


def test_authoring_validation_reports_missing_feature_columns(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [{"ts": datetime(2026, 1, 1, tzinfo=timezone.utc), "canonical_symbol": "QQQ"}]
    ).write_parquet(feature_path)
    _write_spec(spec_path)

    errors = validate_authoring_inputs(load_authoring_spec(spec_path), data_dir=data_dir)

    assert errors
    assert "feature panel missing columns" in errors[0]
    assert "trade_allowed" in errors[0]


def test_strategy_lab_signal_adapter_avoids_legacy_csv(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    signals = strategy_signals_to_research_signals(frame)

    assert len(signals) == 3
    assert signals[0].canonical_symbol == "XYZ100"
    assert signals[0].side == "long"
    assert signals[0].stop_loss_bps == 150.0
    assert signals[0].take_profit_bps == 300.0


def test_authoring_sizing_volatility_target_scales_position_weight(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "vol-target.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["realized_vol"] = 0.10
    rows[1]["realized_vol"] = 0.40
    rows[2]["realized_vol"] = 0.0
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  sizing:\n    position_weight: 1.0",
            "  sizing:\n    position_weight: 1.0\n"
            "    volatility_target: 0.20\n"
            "    volatility_column: realized_vol\n"
            "    max_volatility_scaled_position_weight: 1.5",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("position_weight").to_list() == pytest.approx([1.5, 0.5, 1.0])


def test_authoring_risk_throttle_blocks_drawdown_daily_loss_and_loss_streak(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "risk-throttle.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["strategy_drawdown"] = -0.05
    rows[0]["daily_pnl"] = 0.0
    rows[0]["loss_streak"] = 0
    rows[1]["strategy_drawdown"] = -0.25
    rows[1]["daily_pnl"] = 0.0
    rows[1]["loss_streak"] = 0
    rows[2]["strategy_drawdown"] = -0.05
    rows[2]["daily_pnl"] = 0.0
    rows[2]["loss_streak"] = 3
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            "    max_drawdown_floor: -0.20\n"
            "    daily_loss_column: daily_pnl\n"
            "    daily_loss_floor: -0.10\n"
            "    loss_streak_column: loss_streak\n"
            "    max_loss_streak: 3",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") != "none").height == 1
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["risk_throttle_max_drawdown"],
        ["risk_throttle_loss_streak"],
    ]


def test_authoring_hold_rule_records_no_trade_signal_and_excludes_backtest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(
        pl.when(pl.arange(0, pl.len()) == 0)
        .then(31.0)
        .otherwise(pl.col("vix_level"))
        .alias("vix_level")
    ).write_parquet(feature_path)

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)
    research_signals = strategy_signals_to_research_signals(frame)

    assert frame.get_column("side").to_list().count("none") == 1
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["hold_rule"]
    ]
    assert len(research_signals) == 2
    artifacts = write_authoring_signal_artifacts(
        frame,
        _manifest,
        data_dir=data_dir,
    )
    legacy = pl.read_csv(artifacts["legacy_csv"])
    assert set(legacy.get_column("side").to_list()) == {"long"}


def test_authoring_auto_side_column_can_emit_long_short_and_hold(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("side: long", "side: auto\n  side_column: direction")
        .replace(
            "take_profit_bps: 300",
            "take_profit_bps: 300\n    stop_loss_bps_column: atr_stop_bps\n    take_profit_bps_column: atr_take_profit_bps",
        ),
        encoding="utf-8",
    )
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(
        pl.Series("direction", ["long", "short", "hold"]),
        pl.Series("atr_stop_bps", [111.0, 222.0, 333.0]),
        pl.Series("atr_take_profit_bps", [444.0, 555.0, 666.0]),
    ).write_parquet(feature_path)

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)
    research_signals = strategy_signals_to_research_signals(frame)

    assert frame.get_column("side").to_list() == ["long", "short", "none"]
    assert [signal.side for signal in research_signals] == ["long", "short"]
    assert [signal.stop_loss_bps for signal in research_signals] == [111.0, 222.0]
    assert [signal.take_profit_bps for signal in research_signals] == [444.0, 555.0]


def test_authoring_rule_dsl_supports_column_comparison_and_membership(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "      - column: close_above_sma20\n        op: is_true",
            "      - column: fast_ma\n        op: gt\n        value_column: slow_ma",
        )
        .replace(
            "      - column: vix_level\n        op: lt\n        value: 30",
            "      - column: market_regime\n        op: in\n        value: [bull, bear, neutral]",
        )
        .replace(
            "      - column: vix_level\n        op: gte\n        value: 30",
            "      - column: market_regime\n        op: not_in\n        value: [bull, neutral]",
        ),
        encoding="utf-8",
    )
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(
        pl.Series("fast_ma", [101.0, 101.0, 101.0]),
        pl.Series("slow_ma", [100.0, 100.0, 100.0]),
        pl.Series("market_regime", ["bull", "bear", "neutral"]),
    ).write_parquet(feature_path)

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "long"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["hold_rule"]
    ]


def test_authoring_entry_none_conditions_block_matching_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "none-entry.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["news_blackout"] = False
    rows[1]["news_blackout"] = True
    rows[2]["news_blackout"] = False
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  entry:\n    all:",
            "  entry:\n    none:\n      - column: news_blackout\n        op: is_true\n    all:",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [rows[0]["ts"], rows[2]["ts"]]
    assert frame.get_column("side").to_list() == ["long", "long"]


def test_authoring_conditions_support_cross_trend_and_consecutive_operators(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "cross-trend.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    for index, row in enumerate(rows):
        row["fast_ma"] = [99.0, 101.0, 99.0][index]
        row["slow_ma"] = 100.0
        row["research_return_1d"] = [0.01, 0.02, -0.01][index]
    rows.append(
        {
            **rows[-1],
            "ts": rows[-1]["ts"] + timedelta(hours=4),
            "fast_ma": 98.0,
            "research_return_1d": -0.02,
        }
    )
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml()
        .replace(
            "  hold:\n    any:\n      - column: vix_level\n        op: gte\n        value: 30",
            "  hold:\n    all:\n      - column: research_return_1d\n        op: consecutive_lt\n        value: 0\n        window: 2",
        )
        .replace(
            "  entry:\n    all:",
            "  close:\n    all:\n      - column: fast_ma\n        op: crosses_below\n        value_column: slow_ma\n      - column: fast_ma\n        op: falling\n  entry:\n    all:",
        )
        .replace(
            "      - column: close_above_sma20\n        op: is_true",
            "      - column: fast_ma\n        op: crosses_above\n        value_column: slow_ma\n      - column: fast_ma\n        op: rising",
        )
        .replace(
            "      - column: research_return_1d\n        op: gt\n        value: 0",
            "      - column: research_return_1d\n        op: consecutive_gt\n        value: 0\n        window: 2",
        ),
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "close", "none"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["hold_rule"]
    ]


def test_authoring_confirmation_panels_support_higher_timeframe_conditions(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "multi-timeframe.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    confirmation_path = data_dir / "research/feature_panel_1d.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_return_1d": 0.02,
                "research_return_4h": 0.01,
                "source_confidence": 0.8,
                "venue_quality_score": 0.9,
            }
            for index in range(3)
        ]
    ).write_parquet(feature_path)
    pl.DataFrame(
        [
            {
                "ts": start - timedelta(hours=1),
                "canonical_symbol": "QQQ",
                "daily_trend_ok": True,
                "daily_regime_score": 0.7,
            },
            {
                "ts": start + timedelta(hours=2),
                "canonical_symbol": "QQQ",
                "daily_trend_ok": False,
                "daily_regime_score": 0.2,
            },
        ]
    ).write_parquet(confirmation_path)
    spec_path.write_text(
        f"""schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: multi_timeframe_confirmation_v1
  strategy_family: multi_timeframe
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
data:
  feature_panel_path: {feature_path}
  confirmation_panels:
    - path: {confirmation_path}
      prefix: d1
      max_age_minutes: 120
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: confirmed_score
      op: add
      columns: [d1_daily_regime_score]
      value: 0.1
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: d1_daily_trend_ok
        op: is_true
      - column: confirmed_score
        op: gt
        value: 0.75
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [
        start,
        start + timedelta(hours=1),
    ]
    assert frame.get_column("side").to_list() == ["long", "long"]


def test_authoring_derived_features_support_arithmetic_and_rolling_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  derived_features:\n    - name: trend_spread\n      op: diff\n      columns: [fast_ma, slow_ma]\n    - name: return_z\n      op: rolling_zscore\n      columns: [research_return_1d]\n      window: 2\n      fill_null: 0\n  entry:\n    all:",
        )
        .replace(
            "      - column: close_above_sma20\n        op: is_true",
            "      - column: trend_spread\n        op: gt\n        value: 0",
        )
        .replace(
            "      - column: research_return_1d\n        op: gt\n        value: 0",
            "      - column: return_z\n        op: gte\n        value: 0",
        ),
        encoding="utf-8",
    )
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(
        pl.Series("fast_ma", [101.0, 99.0, 103.0]),
        pl.Series("slow_ma", [100.0, 100.0, 100.0]),
    ).write_parquet(feature_path)

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "long"]


def test_authoring_derived_features_support_breakout_channel_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "breakout.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  derived_features:\n"
            "    - name: rolling_high\n"
            "      op: rolling_max\n"
            "      columns: [research_close]\n"
            "      window: 2\n"
            "    - name: prior_high\n"
            "      op: lag\n"
            "      columns: [rolling_high]\n"
            "      window: 1\n"
            "    - name: rolling_low\n"
            "      op: rolling_min\n"
            "      columns: [research_close]\n"
            "      window: 2\n"
            "  entry:\n    all:",
        )
        .replace(
            "      - column: close_above_sma20\n        op: is_true",
            "      - column: research_close\n        op: gt\n        value_column: prior_high",
        )
        .replace(
            "      - column: research_return_1d\n        op: gt\n        value: 0",
            "      - column: rolling_low\n        op: lt\n        value: 103",
        ),
        encoding="utf-8",
    )
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(pl.Series("research_close", [100.0, 99.0, 104.0])).write_parquet(
        feature_path
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [_feature_rows()[2]["ts"]]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_ema_crossover_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "ema-cross.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  derived_features:\n"
            "    - name: fast_ema\n"
            "      op: ewm_mean\n"
            "      columns: [research_close]\n"
            "      window: 2\n"
            "    - name: slow_ema\n"
            "      op: ewm_mean\n"
            "      columns: [research_close]\n"
            "      window: 4\n"
            "  entry:\n    all:",
        )
        .replace(
            "      - column: close_above_sma20\n        op: is_true",
            "      - column: fast_ema\n        op: gt\n        value_column: slow_ema",
        )
        .replace(
            "      - column: research_return_1d\n        op: gt\n        value: 0",
            "      - column: research_close\n        op: gt\n        value: 102",
        )
        .replace(
            "      - column: research_return_4h\n        op: gt\n        value: 0",
            "      - column: research_close\n        op: gt\n        value: 102",
        ),
        encoding="utf-8",
    )
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(pl.Series("research_close", [100.0, 101.0, 104.0])).write_parquet(
        feature_path
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [_feature_rows()[2]["ts"]]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_rsi_mean_reversion_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "rsi-mean-reversion.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_close": price,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, price in enumerate([100.0, 99.0, 98.0, 97.0, 100.0])
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: rsi_mean_reversion_v1
  strategy_family: mean_reversion
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: rsi_3
      op: rsi
      columns: [research_close]
      window: 3
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: rsi_3
        op: lt
        value: 30
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [
        start + timedelta(hours=2),
        start + timedelta(hours=3),
    ]
    assert frame.get_column("side").to_list() == ["long", "long"]


def test_authoring_derived_features_support_distance_from_ma_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "distance-from-ma.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_close": close,
                "research_return_1d": 0.01,
                "research_return_4h": 0.0,
            }
            for index, close in enumerate([100.0, 110.0, 120.0])
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: distance_from_ma_authoring_v1
  strategy_family: mean_reversion
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: long
  derived_features:
    - name: close_distance_from_ma
      op: distance_from_ma
      columns: [research_close]
      window: 3
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: close_distance_from_ma
        op: gt
        value: 0.08
  reason_code: distance_from_ma_authoring_v1
  hold_reason_code: distance_from_ma_hold_v1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=2)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_rolling_autocorr_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "rolling-autocorr.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_return_1d": value,
                "research_return_4h": 0.0,
            }
            for index, value in enumerate([0.01, 0.02, 0.03, 0.04])
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: rolling_autocorr_authoring_v1
  strategy_family: regime_persistence
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: long
  derived_features:
    - name: return_autocorr
      op: rolling_autocorr
      columns: [research_return_1d]
      window: 3
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: return_autocorr
        op: gt
        value: 0.9
  reason_code: rolling_autocorr_authoring_v1
  hold_reason_code: rolling_autocorr_hold_v1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [
        start + timedelta(hours=2),
        start + timedelta(hours=3),
    ]
    assert frame.get_column("side").to_list() == ["long", "long"]


def test_authoring_derived_features_support_atr_volatility_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "atr-volatility.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        (100.0, 98.0, 99.0),
        (106.0, 100.0, 105.0),
        (108.0, 104.0, 107.0),
    ]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_high": high,
                "research_low": low,
                "research_close": close,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, (high, low, close) in enumerate(rows)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: atr_volatility_breakout_v1
  strategy_family: volatility_breakout
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: true_range
      op: true_range
      columns: [research_high, research_low, research_close]
    - name: atr_2
      op: atr
      columns: [research_high, research_low, research_close]
      window: 2
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: true_range
        op: gt
        value: 4
      - column: atr_2
        op: gte
        value: 4
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=1)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_bollinger_band_inputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "bollinger-reversal.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prices = [100.0, 100.0, 100.0, 90.0]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_close": price,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, price in enumerate(prices)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: bollinger_reversal_v1
  strategy_family: mean_reversion
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: bb_upper
      op: bollinger_upper
      columns: [research_close]
      window: 3
      value: 2
    - name: bb_lower
      op: bollinger_lower
      columns: [research_close]
      window: 3
      value: 2
    - name: bb_width
      op: bollinger_width
      columns: [research_close]
      window: 3
      value: 2
    - name: bb_percent_b
      op: bollinger_percent_b
      columns: [research_close]
      window: 3
      value: 2
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: bb_percent_b
        op: lt
        value: 0.3
      - column: bb_width
        op: gt
        value: 0
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=3)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_macd_stochastic_and_adx_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "trend-strength.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        (101.0, 99.0, 100.0),
        (102.0, 100.0, 101.0),
        (104.0, 101.0, 103.0),
        (106.0, 103.0, 105.0),
        (108.0, 105.0, 107.0),
    ]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_high": high,
                "research_low": low,
                "research_close": close,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, (high, low, close) in enumerate(rows)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: trend_strength_v1
  strategy_family: trend_following
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: macd_fast_slow
      op: macd_line
      columns: [research_close]
      window: 2
      value: 4
    - name: stoch_k_3
      op: stochastic_k
      columns: [research_high, research_low, research_close]
      window: 3
    - name: stoch_d_2
      op: stochastic_d
      columns: [stoch_k_3]
      window: 2
    - name: adx_3
      op: adx
      columns: [research_high, research_low, research_close]
      window: 3
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: macd_fast_slow
        op: gt
        value: 0
      - column: stoch_d_2
        op: gt
        value: 75
      - column: adx_3
        op: gt
        value: 50
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [
        start + timedelta(hours=3),
        start + timedelta(hours=4),
    ]
    assert frame.get_column("side").to_list() == ["long", "long"]


def test_authoring_derived_features_support_channel_envelope_and_volume_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "channel-volume.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        (101.0, 99.0, 100.0, 1000.0),
        (102.0, 100.0, 101.0, 1200.0),
        (103.0, 101.0, 102.0, 1100.0),
        (108.0, 102.0, 107.0, 3000.0),
    ]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_high": high,
                "research_low": low,
                "research_close": close,
                "research_volume": volume,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, (high, low, close, volume) in enumerate(rows)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: channel_volume_breakout_v1
  strategy_family: breakout
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: donchian_high
      op: donchian_upper
      columns: [research_high, research_low]
      window: 3
    - name: prior_donchian_high
      op: lag
      columns: [donchian_high]
      window: 1
    - name: donchian_width
      op: donchian_width
      columns: [research_high, research_low]
      window: 3
    - name: keltner_width
      op: keltner_width
      columns: [research_high, research_low, research_close]
      window: 3
      value: 1.5
    - name: volume_z
      op: volume_zscore
      columns: [research_volume]
      window: 3
      fill_null: 0
    - name: obv_line
      op: obv
      columns: [research_close, research_volume]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: research_close
        op: gt
        value_column: prior_donchian_high
      - column: volume_z
        op: gt
        value: 1
      - column: obv_line
        op: gt
        value: 3000
      - column: donchian_width
        op: gt
        value: 0
      - column: keltner_width
        op: gt
        value: 0
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=3)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_ichimoku_and_calendar_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "ichimoku-calendar.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 5, 13, tzinfo=timezone.utc)
    rows = [
        (101.0, 99.0, 100.0),
        (104.0, 100.0, 103.0),
        (106.0, 102.0, 105.0),
        (108.0, 104.0, 107.0),
    ]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_high": high,
                "research_low": low,
                "research_close": close,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, (high, low, close) in enumerate(rows)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: ichimoku_calendar_v1
  strategy_family: trend_following
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: tenkan
      op: ichimoku_conversion
      columns: [research_high, research_low]
      window: 3
    - name: kijun
      op: ichimoku_base
      columns: [research_high, research_low]
      window: 4
    - name: span_a
      op: ichimoku_span_a
      columns: [tenkan, kijun]
    - name: span_b
      op: ichimoku_span_b
      columns: [research_high, research_low]
      window: 4
    - name: weekday
      op: ts_weekday
      columns: [ts]
    - name: signal_hour
      op: ts_hour
      columns: [ts]
    - name: signal_month
      op: ts_month
      columns: [ts]
    - name: signal_day
      op: ts_day
      columns: [ts]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: research_close
        op: gt
        value_column: span_a
      - column: span_a
        op: gt
        value_column: span_b
      - column: weekday
        op: eq
        value: 0
      - column: signal_hour
        op: eq
        value: 16
      - column: signal_month
        op: eq
        value: 1
      - column: signal_day
        op: eq
        value: 5
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=3)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_cross_asset_pair_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "cross-asset-pair.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        (0.01, 0.01),
        (0.02, 0.02),
        (0.03, 0.03),
        (0.06, 0.04),
    ]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "asset_return": asset_return,
                "benchmark_return": benchmark_return,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
            for index, (asset_return, benchmark_return) in enumerate(rows)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_asset_pair_v1
  strategy_family: relative_value
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: rolling_corr
      op: rolling_corr
      columns: [asset_return, benchmark_return]
      window: 4
    - name: rolling_beta
      op: rolling_beta
      columns: [asset_return, benchmark_return]
      window: 4
    - name: pair_spread_z
      op: rolling_spread_zscore
      columns: [asset_return, benchmark_return]
      window: 4
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: rolling_corr
        op: gt
        value: 0.8
      - column: rolling_beta
        op: gt
        value: 1.2
      - column: pair_spread_z
        op: gt
        value: 1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=3)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_flow_carry_liquidity_and_vol_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "flow-carry-liquidity-vol.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start,
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "bid_size": 1300.0,
                "ask_size": 700.0,
                "bid_depth_usd": 2_000_000.0,
                "ask_depth_usd": 1_000_000.0,
                "best_bid": 99.95,
                "best_ask": 100.05,
                "depth_1pct_usd": 2_000_000.0,
                "research_return_1h": 0.004,
                "funding_rate": 0.00005,
                "implied_vol": 0.32,
                "realized_vol": 0.24,
                "put_iv": 0.35,
                "call_iv": 0.29,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: flow_carry_liquidity_vol_v1
  strategy_family: microstructure_carry_vol
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: flow_imbalance
      op: order_flow_imbalance
      columns: [bid_size, ask_size]
    - name: depth_ratio
      op: liquidity_depth_ratio
      columns: [bid_depth_usd, ask_depth_usd]
    - name: quoted_spread_bps
      op: spread_bps
      columns: [best_bid, best_ask]
    - name: funding_cost_bps
      op: funding_bps
      columns: [funding_rate]
    - name: carry_adjusted_return
      op: carry_adjusted_return
      columns: [research_return_1h, funding_rate]
    - name: vrp
      op: vol_risk_premium
      columns: [implied_vol, realized_vol]
    - name: downside_skew
      op: put_call_skew
      columns: [put_iv, call_iv]
    - name: liquidity_stress
      op: liquidity_stress
      columns: [best_bid, best_ask, depth_1pct_usd]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: flow_imbalance
        op: gt
        value: 0.25
      - column: depth_ratio
        op: gt
        value: 1.5
      - column: quoted_spread_bps
        op: lt
        value: 11
      - column: funding_cost_bps
        op: lt
        value: 1
      - column: carry_adjusted_return
        op: gt
        value: 0.003
      - column: vrp
        op: gt
        value: 0.05
      - column: downside_skew
        op: gt
        value: 0.05
      - column: liquidity_stress
        op: lt
        value: 0.00001
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_onchain_sentiment_event_and_factor_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "onchain-sentiment-event-factor.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start,
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "exchange_inflow": 100.0,
                "exchange_outflow": 250.0,
                "active_addresses": 1500.0,
                "active_address_baseline": 1000.0,
                "sentiment_score": 0.8,
                "sentiment_confidence": 0.9,
                "reported_eps": 2.4,
                "expected_eps": 2.0,
                "fair_value": 125.0,
                "research_close": 100.0,
                "factor_score": 0.7,
                "factor_volatility": 0.2,
                "forecast_volatility": 0.25,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            },
            {
                "ts": start,
                "canonical_symbol": "SPY",
                "trade_allowed": True,
                "exchange_inflow": 300.0,
                "exchange_outflow": 200.0,
                "active_addresses": 900.0,
                "active_address_baseline": 1000.0,
                "sentiment_score": 0.3,
                "sentiment_confidence": 0.8,
                "reported_eps": 1.9,
                "expected_eps": 2.0,
                "fair_value": 101.0,
                "research_close": 100.0,
                "factor_score": 0.2,
                "factor_volatility": 0.3,
                "forecast_volatility": 0.5,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            },
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: onchain_sentiment_event_factor_v1
  strategy_family: composite_factor
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: net_flow
      op: net_exchange_flow
      columns: [exchange_inflow, exchange_outflow]
    - name: activity_ratio
      op: onchain_activity_ratio
      columns: [active_addresses, active_address_baseline]
    - name: weighted_sentiment
      op: sentiment_weighted_score
      columns: [sentiment_score, sentiment_confidence]
    - name: earnings_surprise
      op: event_surprise
      columns: [reported_eps, expected_eps]
    - name: value_gap
      op: fundamental_value_gap
      columns: [fair_value, research_close]
    - name: risk_adjusted_factor
      op: risk_adjusted_score
      columns: [factor_score, factor_volatility]
    - name: inv_vol_weight
      op: inverse_volatility_weight
      columns: [forecast_volatility]
    - name: factor_rank
      op: cross_sectional_rank
      columns: [factor_score]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: net_flow
        op: lt
        value: 0
      - column: activity_ratio
        op: gt
        value: 1.4
      - column: weighted_sentiment
        op: gt
        value: 0.7
      - column: earnings_surprise
        op: gt
        value: 0.3
      - column: value_gap
        op: gt
        value: 0.2
      - column: risk_adjusted_factor
        op: gt
        value: 3
      - column: inv_vol_weight
        op: gt
        value: 3
      - column: factor_rank
        op: eq
        value: 1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_cross_sectional_standardization(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "cross-sectional-standardization.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "factor_score": score,
                "research_return_1d": 0.01,
                "research_return_4h": 0.0,
            }
            for symbol, score in [("AAA", 1.0), ("BBB", 2.0), ("CCC", 4.0)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_sectional_standardization_v1
  strategy_family: factor_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: long
  derived_features:
    - name: factor_z
      op: cross_sectional_zscore
      columns: [factor_score]
    - name: factor_demeaned
      op: cross_sectional_demean
      columns: [factor_score]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: factor_z
        op: gt
        value: 1.0
      - column: factor_demeaned
        op: gt
        value: 1.5
  reason_code: cross_sectional_standardization_v1
  hold_reason_code: cross_sectional_standardization_hold_v1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("execution_symbol").to_list() == ["CCC100"]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_execution_constraint_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "execution-constraints.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start,
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "queue_ahead_usd": 200_000.0,
                "queue_behind_usd": 800_000.0,
                "latency_ms": 30.0,
                "maker_fee_bps": 1.0,
                "taker_fee_bps": 5.0,
                "borrow_rate": 0.0002,
                "holding_days": 2.0,
                "available_borrow_usd": 600_000.0,
                "target_short_notional_usd": 300_000.0,
                "unrealized_gain_pct": 0.04,
                "tax_rate": 0.2,
                "current_weight": 0.36,
                "target_weight": 0.3,
                "source_confidence": 0.9,
                "venue_quality_score": 0.9,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: execution_constraints_v1
  strategy_family: execution_aware
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: short
  timeframe: 1h
  derived_features:
    - name: queue_score
      op: queue_position_score
      columns: [queue_ahead_usd, queue_behind_usd]
    - name: latency_cost
      op: latency_penalty_bps
      columns: [latency_ms]
      value: 0.1
    - name: fee_edge
      op: maker_taker_fee_edge_bps
      columns: [maker_fee_bps, taker_fee_bps]
    - name: borrow_cost
      op: borrow_cost_bps
      columns: [borrow_rate, holding_days]
    - name: borrow_ratio
      op: borrow_availability_ratio
      columns: [available_borrow_usd, target_short_notional_usd]
    - name: tax_drag
      op: tax_drag_bps
      columns: [unrealized_gain_pct, tax_rate]
    - name: weight_drift
      op: rebalance_drift
      columns: [current_weight, target_weight]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: queue_score
        op: gt
        value: 0.7
      - column: latency_cost
        op: lt
        value: 4
      - column: fee_edge
        op: gt
        value: 3
      - column: borrow_cost
        op: lt
        value: 5
      - column: borrow_ratio
        op: gt
        value: 1.5
      - column: tax_drag
        op: lt
        value: 100
      - column: weight_drift
        op: gt
        value: 0.05
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start]
    assert frame.get_column("side").to_list() == ["short"]


def test_authoring_derived_features_support_quality_ensemble_capacity_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "quality-ensemble-capacity.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    prices = [100.0, 105.0, 102.0]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "feature_age_minutes": 5.0,
                "source_confidence": 0.9,
                "venue_quality_score": 0.8,
                "lineage_completeness": 1.0,
                "trend_vote": 1.0,
                "mean_reversion_vote": 1.0,
                "event_vote": 0.0,
                "current_regime_score": 0.7,
                "previous_regime_score": 0.3,
                "research_close": price,
                "trade_notional_usd": 100_000.0,
                "average_daily_volume_usd": 2_000_000.0,
                "target_notional_usd": 200_000.0,
                "strategy_capacity_usd": 1_000_000.0,
                "average_pair_corr": 0.4,
                "gross_exposure": 1.2,
            }
            for index, price in enumerate(prices)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: quality_ensemble_capacity_v1
  strategy_family: quality_aware_ensemble
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: freshness
      op: freshness_score
      columns: [feature_age_minutes]
      value: 30
    - name: stale_cost
      op: staleness_bps
      columns: [feature_age_minutes]
      value: 0.2
    - name: quality_blend
      op: data_quality_blend
      columns: [source_confidence, venue_quality_score, lineage_completeness]
    - name: votes
      op: ensemble_vote_count
      columns: [trend_vote, mean_reversion_vote, event_vote]
    - name: vote_ratio
      op: ensemble_vote_ratio
      columns: [trend_vote, mean_reversion_vote, event_vote]
    - name: regime_shift
      op: regime_transition_score
      columns: [current_regime_score, previous_regime_score]
    - name: drawdown
      op: drawdown_from_peak
      columns: [research_close]
      window: 3
    - name: turnover_pressure
      op: turnover_pressure
      columns: [trade_notional_usd, average_daily_volume_usd]
    - name: capacity_usage
      op: capacity_usage_ratio
      columns: [target_notional_usd, strategy_capacity_usd]
    - name: crowding
      op: correlation_crowding_score
      columns: [average_pair_corr, gross_exposure]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: freshness
        op: gt
        value: 0.8
      - column: stale_cost
        op: lt
        value: 2
      - column: quality_blend
        op: gt
        value: 0.85
      - column: votes
        op: gte
        value: 2
      - column: vote_ratio
        op: gt
        value: 0.6
      - column: regime_shift
        op: gt
        value: 0.3
      - column: drawdown
        op: gt
        value: -0.05
      - column: turnover_pressure
        op: lt
        value: 0.1
      - column: capacity_usage
        op: lt
        value: 0.5
      - column: crowding
        op: lt
        value: 0.6
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [
        start,
        start + timedelta(hours=1),
        start + timedelta(hours=2),
    ]
    assert frame.get_column("side").to_list() == ["long", "long", "long"]


def test_authoring_derived_features_support_return_volatility_and_shape_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "return-volatility-shape.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    closes = [100.0, 102.0, 101.0, 105.0, 110.0]
    returns = [0.01, -0.02, 0.03, 0.04, 0.02]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "research_close": close,
                "research_return": returns[index],
            }
            for index, close in enumerate(closes)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: return_volatility_shape_v1
  strategy_family: return_volatility_shape
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: price_pct
      op: pct_change
      columns: [research_close]
      fill_null: 0
    - name: price_log
      op: log_return
      columns: [research_close]
      fill_null: 0
    - name: two_bar_return
      op: rolling_return
      columns: [research_close]
      window: 2
      fill_null: 0
    - name: return_sum
      op: rolling_sum
      columns: [research_return]
      window: 3
    - name: return_vol
      op: rolling_volatility
      columns: [research_return]
      window: 3
      fill_null: 0
    - name: annual_vol
      op: annualized_volatility
      columns: [research_return]
      window: 3
      value: 252
      fill_null: 0
    - name: realized_var
      op: realized_variance
      columns: [research_return]
      window: 3
    - name: downside_vol
      op: downside_volatility
      columns: [research_return]
      window: 5
      fill_null: 0
    - name: rolling_sharpe
      op: sharpe_like
      columns: [research_return]
      window: 3
      value: 252
      fill_null: 0
    - name: rolling_sortino
      op: sortino_like
      columns: [research_return]
      window: 5
      value: 252
      fill_null: 0
    - name: compounded_return
      op: cumulative_return
      columns: [research_return]
    - name: price_slope
      op: slope
      columns: [research_close]
      window: 2
      fill_null: 0
    - name: fade_score
      op: mean_reversion_score
      columns: [research_close]
      window: 3
      fill_null: 0
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: price_pct
        op: gt
        value: 0.04
      - column: price_log
        op: gt
        value: 0.04
      - column: two_bar_return
        op: gt
        value: 0.08
      - column: return_sum
        op: gt
        value: 0.08
      - column: return_vol
        op: gt
        value: 0
      - column: annual_vol
        op: gt
        value: 0
      - column: realized_var
        op: gt
        value: 0
      - column: downside_vol
        op: gt
        value: 0
      - column: rolling_sharpe
        op: gt
        value: 10
      - column: rolling_sortino
        op: gt
        value: 10
      - column: compounded_return
        op: gt
        value: 0.08
      - column: price_slope
        op: gt
        value: 4
      - column: fade_score
        op: lt
        value: -0.5
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=4)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_kelly_var_and_expected_shortfall(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "risk-sizing.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    returns = [0.02, -0.01, 0.03, -0.02, 0.04]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": index == 4,
                "research_return": value,
            }
            for index, value in enumerate(returns)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: risk_sizing_v1
  strategy_family: risk_sizing
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: kelly
      op: kelly_fraction
      columns: [research_return]
      window: 5
      fill_null: 0
    - name: var_20
      op: historical_var
      columns: [research_return]
      window: 5
      value: 0.2
    - name: expected_shortfall_20
      op: expected_shortfall
      columns: [research_return]
      window: 5
      value: 0.2
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: kelly
        op: gt
        value: 1
      - column: var_20
        op: lt
        value: 0.03
      - column: expected_shortfall_20
        op: lt
        value: 0.03
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=4)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_percentile_skew_and_kurtosis(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "distribution-shape.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    values = [1.0, 2.0, 3.0, 4.0, 10.0]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": index == 4,
                "tail_signal": value,
            }
            for index, value in enumerate(values)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: distribution_shape_v1
  strategy_family: distribution_shape
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: local_percentile
      op: rolling_percentile_rank
      columns: [tail_signal]
      window: 5
    - name: local_skew
      op: rolling_skew
      columns: [tail_signal]
      window: 5
      fill_null: 0
    - name: local_kurtosis
      op: rolling_kurtosis
      columns: [tail_signal]
      window: 5
      fill_null: 0
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: local_percentile
        op: gte
        value: 1.0
      - column: local_skew
        op: gt
        value: 0
      - column: local_kurtosis
        op: gt
        value: -0.3
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=4)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_derived_features_support_rolling_drawdown_path_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "drawdown-path.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    equity_curve = [100.0, 110.0, 105.0, 99.0, 108.0]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": index == 3,
                "paper_equity": value,
            }
            for index, value in enumerate(equity_curve)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: drawdown_path_v1
  strategy_family: drawdown_path
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  derived_features:
    - name: current_drawdown
      op: drawdown_from_peak
      columns: [paper_equity]
      window: 5
    - name: worst_drawdown
      op: rolling_max_drawdown
      columns: [paper_equity]
      window: 5
    - name: bars_since_peak
      op: drawdown_duration
      columns: [paper_equity]
      window: 5
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: current_drawdown
        op: lte
        value: -0.09
      - column: worst_drawdown
        op: lte
        value: -0.09
      - column: bars_since_peak
        op: gte
        value: 2
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=3)]
    assert frame.get_column("side").to_list() == ["long"]


def test_authoring_multi_leg_expands_anchor_signal_into_pair_trade_legs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "pair.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": "AAA",
                "trade_allowed": True,
                "spread_z": 2.0,
                "research_return_1d": 0.02,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: pair_trade_authoring_v1
  strategy_family: pair_trade
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: spread_z
        op: gt
        value: 1
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 0.6
        reason_code: long_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.4
        reason_code: hedge_leg
  sizing:
    position_weight: 2.0
    notional_usd: 1000
  reason_code: pair_trade_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
    frame = frame.sort("execution_symbol")

    assert frame.get_column("execution_symbol").to_list() == ["AAA100", "BBB100"]
    assert frame.get_column("side").to_list() == ["long", "short"]
    assert frame.get_column("position_weight").to_list() == [1.2, 0.8]
    assert frame.get_column("notional_usd").to_list() == [600.0, 400.0]
    assert frame.get_column("reason_codes").to_list() == [
        ["pair_trade_v1", "multi_leg", "long_leg"],
        ["pair_trade_v1", "multi_leg", "hedge_leg"],
    ]


def test_authoring_multi_leg_supports_dynamic_hedge_ratio_columns(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "dynamic-pair.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": "AAA",
                "trade_allowed": True,
                "spread_z": 2.0,
                "research_return_1d": 0.02,
                "hedge_ratio": 0.75,
                "hedge_notional_usd": 725.0,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: dynamic_pair_trade_authoring_v1
  strategy_family: pair_trade
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: spread_z
        op: gt
        value: 1
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 1.0
        reason_code: long_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.5
        position_weight_column: hedge_ratio
        notional_usd_column: hedge_notional_usd
        reason_code: dynamic_hedge_leg
  sizing:
    position_weight: 2.0
    notional_usd: 1000
  reason_code: dynamic_pair_trade_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
    frame = frame.sort("execution_symbol")

    assert frame.get_column("execution_symbol").to_list() == ["AAA100", "BBB100"]
    assert frame.get_column("side").to_list() == ["long", "short"]
    assert frame.get_column("position_weight").to_list() == [2.0, 1.5]
    assert frame.get_column("notional_usd").to_list() == [1000.0, 725.0]
    assert frame.get_column("reason_codes").to_list() == [
        ["dynamic_pair_trade_v1", "multi_leg", "long_leg"],
        ["dynamic_pair_trade_v1", "multi_leg", "dynamic_hedge_leg"],
    ]


def test_authoring_portfolio_exposure_limits_block_excess_weight(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.01,
            }
            for symbol, score in [("AAA", 0.03), ("BBB", 0.02), ("CCC", 0.01)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: exposure_limited_authoring_v1
  strategy_family: exposure_limited
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 0.7
  portfolio:
    max_total_position_weight: 1.0
    max_symbol_position_weight: 1.0
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list().count("long") == 1
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.height == 2
    assert set(blocked.get_column("block_reasons").to_list()[0]) == {
        "portfolio_total_exposure_limit"
    }


def test_authoring_portfolio_group_exposure_limit_blocks_same_bucket(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "sector_bucket": bucket,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.01,
            }
            for symbol, bucket, score in [
                ("AAA", "mega_cap", 0.03),
                ("BBB", "mega_cap", 0.02),
                ("CCC", "defensive", 0.01),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: group_exposure_limited_authoring_v1
  strategy_family: exposure_limited
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 0.6
  portfolio:
    max_group_position_weight: 1.0
    group_column: sector_bucket
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: group_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []

    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    live = frame.filter(pl.col("side") == "long").sort("execution_symbol")
    assert live.get_column("execution_symbol").to_list() == ["AAA100", "CCC100"]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["BBB100"]
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_group_exposure_limit"]]


def test_authoring_portfolio_net_exposure_limit_keeps_balanced_long_short(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "direction": direction,
                "research_return_1d": score,
                "research_return_4h": 0.01,
            }
            for symbol, direction, score in [
                ("AAA", "long", 0.03),
                ("BBB", "short", 0.02),
                ("CCC", "long", 0.01),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: net_exposure_limited_authoring_v1
  strategy_family: exposure_limited
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
rules:
  side_column: direction
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 0.6
  portfolio:
    max_abs_net_position_weight: 0.2
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: net_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []

    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    live = frame.filter(pl.col("side") != "none").sort("execution_symbol")
    assert live.select("execution_symbol", "side").rows() == [
        ("AAA100", "long"),
        ("BBB100", "short"),
    ]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_net_exposure_limit"]]


def test_authoring_portfolio_group_net_exposure_limit_balances_each_bucket(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "sector_bucket": "technology",
                "trade_allowed": True,
                "direction": direction,
                "research_return_1d": score,
                "research_return_4h": 0.01,
            }
            for symbol, direction, score in [
                ("AAA", "long", 0.03),
                ("BBB", "short", 0.02),
                ("CCC", "long", 0.01),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: group_net_exposure_limited_authoring_v1
  strategy_family: exposure_limited
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
rules:
  side_column: direction
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 0.6
  portfolio:
    max_group_abs_net_position_weight: 0.2
    group_column: sector_bucket
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: group_net_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []

    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    live = frame.filter(pl.col("side") != "none").sort("execution_symbol")
    assert live.select("execution_symbol", "side").rows() == [
        ("AAA100", "long"),
        ("BBB100", "short"),
    ]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_group_net_exposure_limit"]]


def test_authoring_portfolio_score_proportional_allocation_sets_timestamp_weights(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-allocation.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.01,
            }
            for symbol, score in [("AAA", 0.03), ("BBB", 0.01)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: portfolio_allocation_authoring_v1
  strategy_family: portfolio_allocation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  portfolio:
    allocation_method: score_proportional
    target_total_position_weight: 1.0
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 100
  reason_code: allocation_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)
    frame = frame.sort("execution_symbol")

    assert frame.get_column("position_weight").to_list() == pytest.approx([0.75, 0.25])


def test_authoring_portfolio_inverse_volatility_allocation_sets_timestamp_weights(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-inverse-vol.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "research_return_1d": 0.01,
                "research_return_4h": 0.01,
                "realized_vol": vol,
            }
            for symbol, vol in [("AAA", 0.10), ("BBB", 0.30)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: inverse_vol_authoring_v1
  strategy_family: inverse_volatility
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  portfolio:
    allocation_method: inverse_volatility
    target_total_position_weight: 1.0
    allocation_volatility_column: realized_vol
  reason_code: inverse_vol_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
    frame = frame.sort("execution_symbol")

    assert frame.get_column("position_weight").to_list() == pytest.approx([0.75, 0.25])


def test_authoring_portfolio_dollar_neutral_allocation_balances_long_short_gross(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-dollar-neutral.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "direction": direction,
                "research_return_1d": 0.01,
                "research_return_4h": 0.01,
            }
            for symbol, direction in [
                ("AAA", "long"),
                ("BBB", "long"),
                ("CCC", "short"),
                ("DDD", "short"),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: dollar_neutral_authoring_v1
  strategy_family: neutral_portfolio
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: DDD100
      real_market_symbol: DDD
      asset_class: equity
rules:
  side_column: direction
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 1.0
  portfolio:
    allocation_method: dollar_neutral
    target_total_position_weight: 1.0
  reason_code: dollar_neutral_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") == "long").get_column("position_weight").sum() == 0.5
    assert frame.filter(pl.col("side") == "short").get_column("position_weight").sum() == 0.5


def test_authoring_portfolio_beta_neutral_allocation_balances_beta_exposure(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-beta-neutral.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "direction": direction,
                "benchmark_beta": beta,
                "research_return_1d": 0.01,
                "research_return_4h": 0.01,
            }
            for symbol, direction, beta in [
                ("AAA", "long", 1.0),
                ("BBB", "short", 2.0),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: beta_neutral_authoring_v1
  strategy_family: neutral_portfolio
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
rules:
  side_column: direction
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 1.0
  portfolio:
    allocation_method: beta_neutral
    target_total_position_weight: 1.0
    allocation_beta_column: benchmark_beta
  reason_code: beta_neutral_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    long_beta_exposure = (
        frame.filter(pl.col("side") == "long").get_column("position_weight").sum() * 1.0
    )
    short_beta_exposure = (
        frame.filter(pl.col("side") == "short").get_column("position_weight").sum() * 2.0
    )
    assert long_beta_exposure == pytest.approx(short_beta_exposure)
    assert frame.get_column("position_weight").sum() == pytest.approx(1.0)


def test_authoring_portfolio_group_neutral_allocation_balances_each_group(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-group-neutral.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "sector_bucket": sector,
                "trade_allowed": True,
                "direction": direction,
                "research_return_1d": 0.01,
                "research_return_4h": 0.01,
            }
            for symbol, sector, direction in [
                ("AAA", "technology", "long"),
                ("BBB", "technology", "short"),
                ("CCC", "energy", "long"),
                ("DDD", "energy", "short"),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: group_neutral_authoring_v1
  strategy_family: neutral_portfolio
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: DDD100
      real_market_symbol: DDD
      asset_class: equity
rules:
  side_column: direction
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  sizing:
    position_weight: 1.0
  portfolio:
    allocation_method: group_neutral
    target_total_position_weight: 1.0
    group_column: sector_bucket
  reason_code: group_neutral_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    for symbols in (("AAA100", "BBB100"), ("CCC100", "DDD100")):
        group = frame.filter(pl.col("execution_symbol").is_in(symbols))
        assert group.filter(pl.col("side") == "long").get_column("position_weight").sum() == 0.25
        assert group.filter(pl.col("side") == "short").get_column("position_weight").sum() == 0.25


def test_authoring_regime_overrides_adjust_risk_sizing_and_execution(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  exit:\n    stop_loss_bps: 150",
            "  regime_overrides:\n    - name: high_vol\n      when:\n        all:\n          - column: vix_level\n            op: gte\n            value: 25\n      stop_loss_bps: 90\n      take_profit_bps: 180\n      position_weight: 0.25\n      slippage_bps: 40\n      max_fill_fraction: 0.5\n  exit:\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    feature_path = data_dir / "research/feature_panel.parquet"
    feature = pl.read_parquet(feature_path)
    feature.with_columns(pl.Series("vix_level", [20.0, 26.0, 27.0])).write_parquet(feature_path)

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)
    frame = frame.sort("ts_signal")

    assert frame.get_column("stop_loss_bps").to_list() == [150.0, 90.0, 90.0]
    assert frame.get_column("take_profit_bps").to_list() == [300.0, 180.0, 180.0]
    assert frame.get_column("position_weight").to_list() == [1.0, 0.25, 0.25]
    assert frame.get_column("slippage_bps").to_list() == [0.0, 40.0, 40.0]
    assert frame.get_column("max_fill_fraction").to_list() == [1.0, 0.5, 0.5]
    assert frame.get_column("reason_codes").to_list()[1] == [
        "trend_pullback_authoring_v1",
        "regime:high_vol",
    ]


def test_authoring_cross_sectional_top_bottom_rotation_filters_middle_rank(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "rotation.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": "AAA",
                "trade_allowed": True,
                "research_return_1d": 0.03,
                "research_return_4h": 0.01,
            },
            {
                "ts": ts,
                "canonical_symbol": "BBB",
                "trade_allowed": True,
                "research_return_1d": 0.01,
                "research_return_4h": 0.00,
            },
            {
                "ts": ts,
                "canonical_symbol": "CCC",
                "trade_allowed": True,
                "research_return_1d": -0.02,
                "research_return_4h": -0.01,
            },
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_sectional_rotation_v1
  strategy_family: cross_sectional_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
      country: US
      currency: USD
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
      country: US
      currency: USD
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
      country: US
      currency: USD
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: auto
  entry:
    all:
      - column: trade_allowed
        op: is_true
  cross_sectional:
    long_top_n: 1
    short_bottom_n: 1
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
  reason_code: cross_sectional_rotation_v1
  hold_reason_code: cross_sectional_hold_v1
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)
    research_signals = strategy_signals_to_research_signals(frame)

    assert frame.height == 3
    assert frame.filter(pl.col("side") == "long").get_column("execution_symbol").to_list() == [
        "AAA100"
    ]
    assert frame.filter(pl.col("side") == "short").get_column("execution_symbol").to_list() == [
        "CCC100"
    ]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["BBB100"]
    assert blocked.get_column("block_reasons").to_list() == [["cross_sectional_rank_filter"]]
    sides_by_symbol = {signal.canonical_symbol: signal.side for signal in research_signals}
    assert sides_by_symbol == {"AAA100": "long", "CCC100": "short"}


def test_authoring_cross_sectional_group_top_bottom_rotation_filters_per_group(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "group-rotation.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "sector_bucket": sector,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.0,
            }
            for symbol, sector, score in [
                ("AAA", "tech", 0.03),
                ("BBB", "tech", 0.01),
                ("CCC", "tech", -0.02),
                ("DDD", "defensive", 0.04),
                ("EEE", "defensive", 0.00),
                ("FFF", "defensive", -0.01),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: group_cross_sectional_rotation_v1
  strategy_family: cross_sectional_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: DDD100
      real_market_symbol: DDD
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: EEE100
      real_market_symbol: EEE
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: FFF100
      real_market_symbol: FFF
      asset_class: equity
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: auto
  entry:
    all:
      - column: trade_allowed
        op: is_true
  cross_sectional:
    long_top_n: 1
    short_bottom_n: 1
    group_column: sector_bucket
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: group_cross_sectional_rotation_v1
  hold_reason_code: group_cross_sectional_hold_v1
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    long_symbols = sorted(frame.filter(pl.col("side") == "long").get_column("execution_symbol"))
    short_symbols = sorted(frame.filter(pl.col("side") == "short").get_column("execution_symbol"))
    blocked = frame.filter(pl.col("side") == "none").sort("execution_symbol")

    assert long_symbols == ["AAA100", "DDD100"]
    assert short_symbols == ["CCC100", "FFF100"]
    assert blocked.get_column("execution_symbol").to_list() == ["BBB100", "EEE100"]
    assert blocked.get_column("block_reasons").to_list() == [
        ["cross_sectional_rank_filter"],
        ["cross_sectional_rank_filter"],
    ]


def test_authoring_cross_sectional_score_thresholds_filter_weak_tails(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "rotation-thresholds.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.0,
            }
            for symbol, score in [
                ("AAA", 0.03),
                ("BBB", 0.01),
                ("CCC", 0.00),
                ("DDD", -0.01),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_sectional_threshold_rotation_v1
  strategy_family: cross_sectional_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: DDD100
      real_market_symbol: DDD
      asset_class: equity
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: auto
  entry:
    all:
      - column: trade_allowed
        op: is_true
  cross_sectional:
    long_top_n: 2
    short_bottom_n: 2
    min_long_score: 0.2
    max_short_score: -0.05
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: cross_sectional_threshold_rotation_v1
  hold_reason_code: cross_sectional_threshold_hold_v1
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") == "long").get_column("execution_symbol").to_list() == [
        "AAA100"
    ]
    assert frame.filter(pl.col("side") == "short").get_column("execution_symbol").to_list() == [
        "DDD100"
    ]
    blocked = frame.filter(pl.col("side") == "none").sort("execution_symbol")
    assert blocked.get_column("execution_symbol").to_list() == ["BBB100", "CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [
        ["cross_sectional_long_score_threshold"],
        ["cross_sectional_short_score_threshold"],
    ]


def test_authoring_cross_sectional_fraction_rotation_selects_quantile_tails(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "fraction-rotation.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    symbols = ["AAA", "BBB", "CCC", "DDD", "EEE"]
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.0,
            }
            for symbol, score in zip(symbols, [0.05, 0.04, 0.01, -0.02, -0.03], strict=True)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_sectional_fraction_rotation_v1
  strategy_family: cross_sectional_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: DDD100
      real_market_symbol: DDD
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: EEE100
      real_market_symbol: EEE
      asset_class: equity
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: auto
  entry:
    all:
      - column: trade_allowed
        op: is_true
  cross_sectional:
    long_top_fraction: 0.4
    short_bottom_fraction: 0.4
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: cross_sectional_fraction_rotation_v1
  hold_reason_code: cross_sectional_fraction_hold_v1
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    long_symbols = sorted(frame.filter(pl.col("side") == "long").get_column("execution_symbol"))
    short_symbols = sorted(frame.filter(pl.col("side") == "short").get_column("execution_symbol"))
    blocked = frame.filter(pl.col("side") == "none")

    assert long_symbols == ["AAA100", "BBB100"]
    assert short_symbols == ["DDD100", "EEE100"]
    assert blocked.get_column("execution_symbol").to_list() == ["CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [["cross_sectional_rank_filter"]]


def test_authoring_cross_sectional_min_candidates_blocks_small_groups(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "min-candidates-rotation.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "sector_bucket": sector,
                "trade_allowed": True,
                "research_return_1d": score,
                "research_return_4h": 0.0,
            }
            for symbol, sector, score in [
                ("AAA", "tech", 0.05),
                ("BBB", "tech", -0.04),
                ("CCC", "defensive", 0.03),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_sectional_min_candidates_rotation_v1
  strategy_family: cross_sectional_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: BBB100
      real_market_symbol: BBB
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: CCC100
      real_market_symbol: CCC
      asset_class: equity
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: auto
  entry:
    all:
      - column: trade_allowed
        op: is_true
  cross_sectional:
    long_top_fraction: 0.5
    short_bottom_fraction: 0.5
    group_column: sector_bucket
    min_candidates: 2
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: cross_sectional_min_candidates_rotation_v1
  hold_reason_code: cross_sectional_min_candidates_hold_v1
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    live = frame.filter(pl.col("side") != "none").sort("execution_symbol")
    blocked = frame.filter(pl.col("side") == "none").sort("execution_symbol")

    assert live.select("execution_symbol", "side").rows() == [
        ("AAA100", "long"),
        ("BBB100", "short"),
    ]
    assert blocked.get_column("execution_symbol").to_list() == ["CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [["cross_sectional_min_candidates"]]


def test_authoring_model_score_builds_raw_score_without_weighted_sum(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "model_score.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            """  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
""",
            """  score:
    model_score:
      model_type: linear
      intercept: 0.1
      activation: clamp_0_1
      missing_value: 0.0
      coefficients:
        - column: research_return_1d
          weight: 20
        - column: source_confidence
          weight: 0.5
""",
        ),
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("raw_score").to_list() == pytest.approx([0.9, 0.9, 0.9])
    assert frame.get_column("rank_score").to_list() == pytest.approx([0.9, 0.9, 0.9])


def test_authoring_model_score_reports_missing_feature_column(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "model_score.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            """  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: research_return_4h
        weight: 5
""",
            """  score:
    model_score:
      coefficients:
        - column: missing_model_feature
          weight: 1
""",
        ),
        encoding="utf-8",
    )

    errors = validate_authoring_inputs(load_authoring_spec(spec_path), data_dir=data_dir)

    assert errors
    assert "missing_model_feature" in errors[0]


def test_strategy_authoring_train_model_writes_model_score_and_spec(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    out_spec = tmp_path / "trained_authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_spec(spec_path)
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = []
    for index, (x_value, y_value) in enumerate([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (2.0, 1.0)]):
        rows.append(
            {
                **_feature_rows()[0],
                "ts": start + timedelta(hours=index),
                "research_return_1d": x_value,
                "source_confidence": y_value,
                "target_forward_return": 0.5 + 2.0 * x_value - y_value,
            }
        )
    pl.DataFrame(rows).write_parquet(feature_path)

    result = runner.invoke(
        app,
        [
            "strategy-author-train-model",
            "--spec",
            str(spec_path),
            "--target-column",
            "target_forward_return",
            "--feature-column",
            "research_return_1d",
            "--feature-column",
            "source_confidence",
            "--ridge-lambda",
            "0",
            "--out-spec",
            str(out_spec),
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (data_dir / "research/strategy_authoring_model_score.json").read_text(encoding="utf-8")
    )
    assert payload["paper_only"] is True
    assert payload["live_order_submitted"] is False
    assert payload["row_count"] == 4
    assert payload["model_score"]["intercept"] == pytest.approx(0.5)
    weights = {item["column"]: item["weight"] for item in payload["model_score"]["coefficients"]}
    assert weights == pytest.approx({"research_return_1d": 2.0, "source_confidence": -1.0})
    trained_spec = load_authoring_spec(out_spec)
    assert trained_spec.rules.score.model_score is not None
    assert trained_spec.rules.score.model_score.intercept == pytest.approx(0.5)


def test_authoring_temporal_rules_block_out_of_schedule_and_cooldown(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "temporal.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n  temporal:\n    allowed_weekdays_utc: [3]\n    allowed_hours_utc: [0, 4]\n    cooldown_minutes: 300\n    max_signals_per_symbol_per_day: 1",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    trade_rows = frame.filter(pl.col("side") != "none")
    blocked_rows = frame.filter(pl.col("side") == "none")
    assert trade_rows.height == 1
    assert blocked_rows.get_column("block_reasons").to_list() == [
        ["temporal_cooldown"],
        ["temporal_hour_filter"],
    ]


def test_authoring_temporal_validation_rejects_invalid_hour(tmp_path) -> None:
    spec_path = tmp_path / "temporal.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n  temporal:\n    allowed_hours_utc: [24]",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="allowed_hours_utc"):
        load_authoring_spec(spec_path)


def test_authoring_position_rules_block_overlapping_symbol_entries(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    max_open_signals_per_symbol: 1\n"
            "    holding_horizon_minutes: 480",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "long"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_open_signal_limit"]
    ]


def test_authoring_event_window_allow_blocks_outside_or_missing_event(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "event-window.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["earnings_ts"] = (rows[0]["ts"] + timedelta(minutes=30)).isoformat()
    rows[1]["earnings_ts"] = (rows[1]["ts"] + timedelta(hours=2)).isoformat()
    rows[2]["earnings_ts"] = None
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  event_windows:\n"
            "    - name: earnings_pre\n"
            "      event_ts_column: earnings_ts\n"
            "      mode: allow\n"
            "      before_minutes: 60\n"
            "      after_minutes: 0\n"
            "      block_reason: event_pre_earnings",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") != "none").height == 1
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["event_pre_earnings_outside"],
        ["event_pre_earnings_missing"],
    ]


def test_authoring_event_window_block_blocks_inside_blackout(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "event-blackout.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["macro_ts"] = (rows[0]["ts"] + timedelta(minutes=15)).isoformat()
    rows[1]["macro_ts"] = (rows[1]["ts"] + timedelta(hours=2)).isoformat()
    rows[2]["macro_ts"] = None
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  event_windows:\n"
            "    - name: macro_blackout\n"
            "      event_ts_column: macro_ts\n"
            "      mode: block\n"
            "      before_minutes: 30\n"
            "      after_minutes: 30",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.filter(pl.col("side") != "none").height == 2
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["event_window_macro_blackout"],
    ]


def test_authoring_partial_take_profit_and_position_weight_affect_backtest(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("position_weight: 1.0", "position_weight: 0.5")
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 150"),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 103.0),
            _quote(start + timedelta(hours=4), 101.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["partial_take_profit+fixed_horizon"] == 1
    assert 0 < metrics["summary"]["aggregate_metrics"]["total_return"] < 0.02


def test_strategy_authoring_trailing_stop_can_exit_before_horizon(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("stop_loss_bps: 150", "stop_loss_bps: 900")
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 100"),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 104.0),
            _quote(start + timedelta(hours=2), 101.0),
            _quote(start + timedelta(hours=4), 105.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["trailing_stop"] == 1


def test_strategy_authoring_min_holding_minutes_defers_early_stop_loss(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n    min_holding_minutes: 120",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 98.0),
            _quote(start + timedelta(hours=2), 101.0),
            _quote(start + timedelta(hours=4), 102.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["fixed_horizon"] == 1
    assert metrics["summary"]["aggregate_metrics"]["total_return"] > 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_holding_minutes").to_list() == [120]


def test_strategy_authoring_bracket_oco_take_profit_records_lifecycle(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("take_profit_bps: 300", "take_profit_bps: 150")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 103.0),
            _quote(start + timedelta(hours=4), 98.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["bracket_take_profit"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("bracket_type").to_list() == ["oco"]


def test_strategy_authoring_bracket_break_even_stop_can_exit_after_arm(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("stop_loss_bps: 150", "stop_loss_bps: 900")
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco\n    break_even_after_bps: 100",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 102.0),
            _quote(start + timedelta(hours=2), 100.0),
            _quote(start + timedelta(hours=4), 105.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["bracket_break_even_stop"] == 1


def test_strategy_authoring_opposite_signal_can_exit_before_horizon(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("side: long", "side: auto\n  side_column: direction")
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_opposite_signal: true\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "direction": "long",
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "direction": "short",
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
            _quote(start + timedelta(hours=5), 110.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["opposite_signal"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert set(signals.get_column("exit_on_opposite_signal").to_list()) == {True}


def test_strategy_authoring_close_signal_can_exit_without_opening_reverse_trade(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  close:\n    all:\n      - column: close_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: close_signal\n        op: is_true\n    all:",
        )
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_close_signal: true\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "close_signal": False,
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "close_signal": True,
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
            _quote(start + timedelta(hours=5), 110.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["close_signal"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("side").to_list() == ["long", "close"]
    assert signals.get_column("exit_on_close_signal").to_list() == [True, False]
    research_signals = strategy_signals_to_research_signals(signals)
    assert [signal.side for signal in research_signals] == ["long", "close"]


def test_strategy_authoring_reduce_signal_partially_exits_before_horizon(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  reduce:\n    all:\n      - column: reduce_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: reduce_signal\n        op: is_true\n    all:",
        )
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_reduce_signal: true\n    reduce_fraction: 0.5\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "reduce_signal": False,
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "reduce_signal": True,
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
            _quote(start + timedelta(hours=4), 110.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    exit_reasons = metrics["summary"]["exit_reason_counts"]
    assert sum(count for reason, count in exit_reasons.items() if "reduce_signal" in reason) == 1
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0.05 < total_return < 0.06
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("side").to_list() == ["long", "reduce"]
    assert signals.get_column("exit_on_reduce_signal").to_list() == [True, False]
    assert signals.get_column("reduce_fraction").to_list() == [None, 0.5]


def test_strategy_authoring_add_signal_scales_into_existing_paper_position(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  add:\n    all:\n      - column: add_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: add_signal\n        op: is_true\n    all:",
        )
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_add_signal: true\n    add_fraction: 0.5\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "add_signal": False,
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "add_signal": True,
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
            _quote(start + timedelta(hours=4), 110.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    exit_reasons = metrics["summary"]["exit_reason_counts"]
    assert sum(count for reason, count in exit_reasons.items() if "add_signal" in reason) == 1
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0.14 < total_return < 0.15
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("side").to_list() == ["long", "add"]
    assert signals.get_column("exit_on_add_signal").to_list() == [True, False]
    assert signals.get_column("add_fraction").to_list() == [None, 0.5]


def test_strategy_authoring_rebalance_signal_moves_to_target_paper_exposure(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  rebalance:\n    all:\n      - column: rebalance_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: rebalance_signal\n        op: is_true\n    all:",
        )
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_rebalance_signal: true\n"
            "    rebalance_target_fraction: 1.5\n"
            "    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "rebalance_signal": False,
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "rebalance_signal": True,
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
            _quote(start + timedelta(hours=4), 110.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    exit_reasons = metrics["summary"]["exit_reason_counts"]
    assert sum(count for reason, count in exit_reasons.items() if "rebalance_signal" in reason) == 1
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0.14 < total_return < 0.15
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("side").to_list() == ["long", "rebalance"]
    assert signals.get_column("exit_on_rebalance_signal").to_list() == [True, False]
    assert signals.get_column("rebalance_target_fraction").to_list() == [None, 1.5]


def test_strategy_authoring_add_then_rebalance_resizes_open_paper_legs(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  add:\n    all:\n      - column: add_signal\n        op: is_true\n"
            "  rebalance:\n    all:\n      - column: rebalance_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: add_signal\n        op: is_true\n"
            "      - column: rebalance_signal\n        op: is_true\n"
            "    all:",
        )
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_add_signal: true\n"
            "    add_fraction: 0.5\n"
            "    exit_on_rebalance_signal: true\n"
            "    rebalance_target_fraction: 0.5\n"
            "    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "add_signal": False,
            "rebalance_signal": False,
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "add_signal": True,
            "rebalance_signal": False,
        },
        {
            **_feature_rows()[2],
            "ts": start + timedelta(hours=2),
            "add_signal": False,
            "rebalance_signal": True,
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
            _quote(start + timedelta(hours=2), 102.0),
            _quote(start + timedelta(hours=4), 110.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    exit_reasons = metrics["summary"]["exit_reason_counts"]
    assert sum(count for reason, count in exit_reasons.items() if "add_signal" in reason) == 1
    assert sum(count for reason, count in exit_reasons.items() if "rebalance_signal" in reason) == 1
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0.06 < total_return < 0.07
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("side").to_list() == ["long", "add", "rebalance"]


def test_strategy_authoring_limit_entry_can_fill_after_signal_and_before_horizon(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n    limit_offset_bps: 100\n    timeout_minutes: 180",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 99.0),
            _quote(start + timedelta(hours=5), 103.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["entry_order_type_counts"]["limit"] == 1
    assert metrics["summary"]["entry_order_unfilled_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("entry_order_type").to_list() == ["limit"]
    assert signals.get_column("entry_limit_offset_bps").to_list() == [100.0]


def test_strategy_authoring_limit_entry_unfilled_is_counted(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n    limit_offset_bps: 100\n    timeout_minutes: 60",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 100.5),
            _quote(start + timedelta(hours=4), 103.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["entry_order_unfilled_count"] == 1
    assert metrics["summary"]["blocked_reason_counts"]["entry_order_unfilled"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0


def test_strategy_authoring_slippage_and_partial_fill_reduce_paper_return(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    slippage_bps: 50\n    max_fill_fraction: 0.5",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=4), 104.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0 < total_return < 0.04
    assert metrics["summary"]["aggregate_metrics"]["cost_drag_bps"] == 51.0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("slippage_bps").to_list() == [50.0]
    assert signals.get_column("max_fill_fraction").to_list() == [0.5]


def test_strategy_authoring_microstructure_spread_filter_blocks_trade(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_spread_bps: 5",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    wide_entry = {**_quote(start, 100.0), "spread_bps": 10.0}
    pl.DataFrame([wide_entry, _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["microstructure_spread_too_wide"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0


def test_strategy_authoring_microstructure_depth_scales_fill_fraction(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "sizing:\n    position_weight: 1.0\n    notional_usd: 1000",
            "sizing:\n    position_weight: 1.0\n    notional_usd: 1000\n  execution:\n    min_depth_usd: 100\n    depth_column: min_side_depth_10bps_usd\n    depth_participation_rate: 0.5",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    shallow_entry = {**_quote(start, 100.0), "min_side_depth_10bps_usd": 500.0}
    pl.DataFrame([shallow_entry, _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0 < total_return < 0.02
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_depth_usd").to_list() == [100.0]
    assert signals.get_column("depth_participation_rate").to_list() == [0.5]


def test_strategy_authoring_microstructure_latency_filter_blocks_trade(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_latency_ms: 100\n    latency_column: observed_latency_ms",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "observed_latency_ms": 250.0} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["microstructure_latency_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_latency_ms").to_list() == [100.0]
    assert signals.get_column("latency_ms").to_list() == [250.0]


def test_strategy_authoring_microstructure_queue_position_filter_blocks_trade(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_queue_position_score: 0.6\n    queue_position_score_column: queue_score",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "queue_score": 0.2} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["microstructure_queue_position_too_low"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_queue_position_score").to_list() == [0.6]
    assert signals.get_column("queue_position_score").to_list() == [0.2]


def test_strategy_authoring_short_borrow_availability_filter_blocks_short_trade(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("side: long", "side: short")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_borrow_availability_ratio: 0.5\n    borrow_availability_column: borrow_available",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "borrow_available": 0.1} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 96.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["short_borrow_availability_too_low"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_borrow_availability_ratio").to_list() == [0.5]
    assert signals.get_column("borrow_availability_ratio").to_list() == [0.1]


def test_strategy_authoring_short_borrow_cost_filter_blocks_short_trade(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("side: long", "side: short")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_borrow_cost_bps: 25\n    borrow_cost_column: borrow_cost",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "borrow_cost": 80.0} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 96.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["short_borrow_cost_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_borrow_cost_bps").to_list() == [25.0]
    assert signals.get_column("borrow_cost_bps").to_list() == [80.0]


def test_strategy_authoring_tax_drag_filter_blocks_trade(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_tax_drag_bps: 20\n    tax_drag_column: tax_drag",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "tax_drag": 45.0} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["tax_drag_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_tax_drag_bps").to_list() == [20.0]
    assert signals.get_column("tax_drag_bps").to_list() == [45.0]


def test_strategy_authoring_turnover_pressure_filter_blocks_trade(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_turnover_pressure: 0.4\n    turnover_pressure_column: turnover_pressure",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "turnover_pressure": 0.9} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["turnover_pressure_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_turnover_pressure").to_list() == [0.4]
    assert signals.get_column("turnover_pressure").to_list() == [0.9]


def test_strategy_authoring_fee_edge_filter_blocks_trade(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_fee_edge_bps: 1\n    fee_edge_column: fee_edge",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "fee_edge": -2.0} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame([_quote(start, 100.0), _quote(start + timedelta(hours=4), 104.0)]).write_parquet(
        data_dir / "normalized/quotes.parquet"
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["blocked_reason_counts"]["fee_edge_too_low"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_fee_edge_bps").to_list() == [1.0]
    assert signals.get_column("fee_edge_bps").to_list() == [-2.0]


def test_strategy_authoring_cli_init_validate_explain_and_run_backtest(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)

    result = runner.invoke(app, ["strategy-author-init", "--out", str(spec_path)])
    assert result.exit_code == 0
    assert spec_path.exists()

    result = runner.invoke(app, ["strategy-author-validate", "--spec", str(spec_path)])
    assert result.exit_code == 0
    assert "valid" in result.stdout

    result = runner.invoke(app, ["strategy-author-explain", "--spec", str(spec_path)])
    assert result.exit_code == 0
    assert (data_dir / "reports/strategy_authoring_explain.md").exists()

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )
    assert result.exit_code == 0, result.stdout
    assert (data_dir / "research/strategy_signals.parquet").exists()
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert metrics["paper_only"] is True
    assert metrics["live_order_submitted"] is False
    assert metrics["summary"]["exit_model"] == "fixed_horizon"
    assert metrics["summary"]["exit_reason_counts"]["fixed_horizon"] > 0
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] > 0
    assert metrics["summary"]["pass_thresholds"]["max_drawdown"]["passed"] is True
    assert metrics["summary"]["backtest_passed"] is True
    assert metrics["summary"]["optimizer"]["variant_count"] == 4
    assert "best_variant" in metrics["summary"]["optimizer"]
    assert metrics["summary"]["walk_forward_eras"]
    assert metrics["summary"]["strategy_scorecard"]["schema_version"] == (
        "strategy_authoring_scorecard.v1"
    )
    assert metrics["summary"]["strategy_scorecard"]["paper_only"] is True
    assert metrics["summary"]["strategy_scorecard"]["live_order_submitted"] is False


def test_strategy_authoring_backtest_scorecard_summarizes_features_and_blocks(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "scorecard.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    rows = _feature_rows()
    for index, row in enumerate(rows):
        row["feature_age_minutes"] = 40.0 if index == 1 else 5.0
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows).write_parquet(feature_path)
    pl.DataFrame(
        [_quote(rows[0]["ts"] + timedelta(hours=index * 4), 100.0 + index) for index in range(5)]
    ).write_parquet(quote_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: scorecard_v1
  strategy_family: explainable
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 4h
  derived_features:
    - name: freshness
      op: freshness_score
      columns: [feature_age_minutes]
      value: 30
  hold:
    all:
      - column: freshness
        op: lt
        value: 0.5
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: freshness
        op: gt
        value: 0.8
backtest:
  label_horizon_minutes: 240
  min_trade_count: 1
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    scorecard = metrics["summary"]["strategy_scorecard"]
    assert scorecard["derived_feature_names"] == ["freshness"]
    assert scorecard["derived_feature_ops"] == {"freshness_score": 1}
    assert scorecard["side_counts"] == {"long": 2, "none": 1}
    assert scorecard["block_reason_counts"] == {"hold_rule": 1}
    report = (data_dir / "reports/strategy_backtest_report.md").read_text(encoding="utf-8")
    assert "## Strategy Scorecard" in report
    assert "- freshness_score: 1" in report


def test_strategy_authoring_optimizer_rejects_unsupported_parameter_path(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "rules.exit.stop_loss_bps: [100, 150]",
            "rules.unsafe_python: [1, 2]",
        ),
        encoding="utf-8",
    )

    try:
        load_authoring_spec(spec_path)
    except ValueError as exc:
        assert "unsupported path" in str(exc)
    else:
        raise AssertionError("Expected unsupported optimizer path to fail")


def test_strategy_authoring_optimizer_accepts_cross_sectional_tail_controls(tmp_path) -> None:
    spec_path = tmp_path / "cross-sectional-optimizer.yaml"
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: cross_sectional_optimizer_v1
  strategy_family: cross_sectional
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: auto
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  score:
    weighted_sum:
      - column: factor_score
        weight: 1
  cross_sectional:
    long_top_fraction: 0.5
    short_bottom_fraction: 0.5
    min_candidates: 2
    min_long_score: 0.1
    max_short_score: -0.1
  reason_code: cross_sectional_optimizer_v1
  hold_reason_code: cross_sectional_optimizer_hold_v1
optimizer:
  parameter_sweep:
    rules.cross_sectional.long_top_fraction: [0.25, 0.5]
    rules.cross_sectional.short_bottom_fraction: [0.25, 0.5]
    rules.cross_sectional.min_candidates: [2, 4]
    rules.cross_sectional.min_long_score: [0.1, 0.2]
    rules.cross_sectional.max_short_score: [-0.1, -0.2]
  max_variants: 64
backtest:
  label_horizon_minutes: 240
  min_trade_count: 1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)

    assert set(spec.optimizer.parameter_sweep) == {
        "rules.cross_sectional.long_top_fraction",
        "rules.cross_sectional.short_bottom_fraction",
        "rules.cross_sectional.min_candidates",
        "rules.cross_sectional.min_long_score",
        "rules.cross_sectional.max_short_score",
    }


def test_strategy_authoring_bundle_runs_multiple_specs_and_writes_portfolio_summary(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_a = tmp_path / "trend.yaml"
    spec_b = tmp_path / "mean_reversion.yaml"
    _write_spec(spec_a)
    spec_b.write_text(
        template_yaml()
        .replace("strategy_id: trend_pullback_user_v1", "strategy_id: mean_reversion_user_v1")
        .replace("strategy_family: trend_pullback", "strategy_family: mean_reversion")
        .replace("position_weight: 1.0", "position_weight: 0.5"),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(
        f"""schema_version: strategy_authoring_bundle.v1
bundle_id: user_multi_strategy_v1
members:
  - spec_path: {spec_a.name}
    allocation_weight: 0.7
  - spec_path: {spec_b.name}
    allocation_weight: 0.6
portfolio:
  max_total_allocation_weight: 1.0
  selection_metric: total_return
  selection_direction: maximize
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-author-bundle-run", "--bundle", str(bundle_path)])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (data_dir / "research/strategy_authoring_bundle_result.json").read_text(encoding="utf-8")
    )
    assert payload["paper_only"] is True
    assert payload["live_order_submitted"] is False
    assert payload["aggregate_metrics"]["member_count"] == 2
    assert payload["best_member"]["strategy_id"] in {
        "trend_pullback_user_v1",
        "mean_reversion_user_v1",
    }
    assert sum(
        member["effective_allocation_weight"] for member in payload["members"]
    ) == pytest.approx(1.0)
    assert (data_dir / "reports/strategy_authoring_bundle_report.md").exists()


def test_strategy_authoring_bundle_risk_parity_allocates_by_drawdown_proxy(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_a = tmp_path / "low_risk.yaml"
    spec_b = tmp_path / "high_risk.yaml"
    spec_a.write_text(
        template_yaml().replace(
            "strategy_id: trend_pullback_user_v1", "strategy_id: low_risk_user_v1"
        ),
        encoding="utf-8",
    )
    spec_b.write_text(
        template_yaml()
        .replace("strategy_id: trend_pullback_user_v1", "strategy_id: high_risk_user_v1")
        .replace("strategy_family: trend_pullback", "strategy_family: high_risk")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 2.0\n  execution:\n    slippage_bps: 1000",
        ),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "risk_parity_bundle.yaml"
    bundle_path.write_text(
        f"""schema_version: strategy_authoring_bundle.v1
bundle_id: risk_parity_bundle_v1
members:
  - spec_path: {spec_a.name}
    allocation_weight: 0.1
  - spec_path: {spec_b.name}
    allocation_weight: 0.9
portfolio:
  allocation_method: risk_parity
  max_total_allocation_weight: 1.0
  selection_metric: total_return
  selection_direction: maximize
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-author-bundle-run", "--bundle", str(bundle_path)])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (data_dir / "research/strategy_authoring_bundle_result.json").read_text(encoding="utf-8")
    )
    weights = {
        member["strategy_id"]: member["effective_allocation_weight"]
        for member in payload["members"]
    }
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["low_risk_user_v1"] > weights["high_risk_user_v1"]
    assert payload["portfolio"]["allocation_method"] == "risk_parity"


def test_strategy_authoring_bundle_schema_file_is_parseable() -> None:
    json.loads(Path("schemas/strategy_authoring_bundle.v1.schema.json").read_text(encoding="utf-8"))


def test_strategy_authoring_cli_paper_preview_writes_hold_preview_artifacts(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    _write_spec(spec_path)

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "paper-preview"]
    )

    assert result.exit_code == 0, result.stdout
    assert (data_dir / "research/trial_ledger.jsonl").exists()
    assert (data_dir / "research/paper_candidate_pack.json").exists()
    assert (data_dir / "research/promotion_decision.json").exists()
    ledger = json.loads((data_dir / "research/trial_ledger.jsonl").read_text().strip())
    assert ledger["metrics"]["strategy_scorecard"]["schema_version"] == (
        "strategy_authoring_scorecard.v1"
    )
    preview = json.loads((data_dir / "bot/paper_intent_preview.json").read_text(encoding="utf-8"))
    assert preview == []
    decision = json.loads(
        (data_dir / "research/promotion_decision.json").read_text(encoding="utf-8")
    )
    assert decision["decision"] == "hold"
    assert "strategy_scorecard" in decision["required_evidence"]
    assert decision["scorecard_summary"]["schema_version"] == "strategy_authoring_scorecard.v1"
    assert decision["scorecard_summary"]["paper_only"] is True
    assert decision["scorecard_summary"]["live_order_submitted"] is False
    report = (data_dir / "reports/paper_intent_preview.md").read_text(encoding="utf-8")
    assert "scorecard_schema_version: strategy_authoring_scorecard.v1" in report


def test_strategy_authoring_threshold_failure_blocks_next_stage(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace("max_drawdown: -0.2", "total_return: 99.0"),
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "paper-preview"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["pass_thresholds"]["total_return"]["passed"] is False
    assert metrics["summary"]["backtest_passed"] is False
    ledger = json.loads((data_dir / "research/trial_ledger.jsonl").read_text().strip())
    assert ledger["selected_for_next_stage"] is False


def test_strategy_authoring_stop_loss_can_end_before_fixed_horizon(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    _write_spec(spec_path)
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 98.0),
            _quote(start + timedelta(hours=4), 105.0),
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "backtest"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["summary"]["exit_reason_counts"]["stop_loss"] == 1
    assert metrics["summary"]["aggregate_metrics"]["total_return"] < 0
