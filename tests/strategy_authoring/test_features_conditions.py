# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


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


def test_authoring_derived_features_support_benchmark_active_risk_inputs(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "benchmark-active-risk.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        (0.02, 0.01),
        (0.01, 0.01),
        (0.03, 0.01),
        (0.00, 0.01),
        (0.04, 0.01),
    ]
    pl.DataFrame(
        [
            {
                "ts": start + timedelta(hours=index),
                "canonical_symbol": "QQQ",
                "trade_allowed": index == 4,
                "asset_return": asset_return,
                "benchmark_return": benchmark_return,
            }
            for index, (asset_return, benchmark_return) in enumerate(rows)
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: benchmark_active_risk_v1
  strategy_family: benchmark_active_risk
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
    - name: active_tracking_error
      op: tracking_error
      columns: [asset_return, benchmark_return]
      window: 5
      value: 1
    - name: active_information_ratio
      op: information_ratio
      columns: [asset_return, benchmark_return]
      window: 5
      value: 1
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: active_tracking_error
        op: gt
        value: 0.01
      - column: active_tracking_error
        op: lt
        value: 0.02
      - column: active_information_ratio
        op: gt
        value: 0.5
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert frame.get_column("ts_signal").to_list() == [start + timedelta(hours=4)]
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


def test_authoring_derived_features_support_group_cross_sectional_standardization(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "group-cross-sectional-standardization.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        ("TECH_A", "tech", 1.0),
        ("TECH_B", "tech", 4.0),
        ("HEALTH_A", "health", 5.0),
        ("HEALTH_B", "health", 6.0),
    ]
    pl.DataFrame(
        [
            {
                "ts": start,
                "canonical_symbol": symbol,
                "sector_bucket": sector,
                "trade_allowed": True,
                "factor_score": score,
            }
            for symbol, sector, score in rows
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: group_cross_sectional_standardization_v1
  strategy_family: group_factor_rotation
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: TECHA100
      real_market_symbol: TECH_A
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: TECHB100
      real_market_symbol: TECH_B
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: HEALTHA100
      real_market_symbol: HEALTH_A
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: HEALTHB100
      real_market_symbol: HEALTH_B
      asset_class: equity
data:
  feature_panel_path: data/research/feature_panel.parquet
rules:
  side: long
  derived_features:
    - name: group_factor_rank
      op: group_cross_sectional_rank
      columns: [factor_score, sector_bucket]
    - name: group_factor_z
      op: group_cross_sectional_zscore
      columns: [factor_score, sector_bucket]
    - name: group_factor_demeaned
      op: group_cross_sectional_demean
      columns: [factor_score, sector_bucket]
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: group_factor_rank
        op: eq
        value: 1
      - column: group_factor_z
        op: gt
        value: 0.7
      - column: group_factor_demeaned
        op: gt
        value: 0
  reason_code: group_cross_sectional_standardization_v1
  hold_reason_code: group_cross_sectional_standardization_hold_v1
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert set(frame.get_column("execution_symbol").to_list()) == {"TECHB100", "HEALTHB100"}
    assert frame.get_column("side").to_list() == ["long", "long"]


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
