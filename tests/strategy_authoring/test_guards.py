# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


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


def test_authoring_risk_throttle_can_use_row_threshold_columns(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "risk-throttle-row-thresholds.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["strategy_drawdown"] = -0.12
    rows[0]["row_drawdown_floor"] = -0.10
    rows[0]["daily_pnl"] = 0.0
    rows[0]["row_daily_loss_floor"] = -0.05
    rows[0]["loss_streak"] = 0
    rows[0]["row_max_loss_streak"] = 5
    rows[1]["strategy_drawdown"] = -0.05
    rows[1]["row_drawdown_floor"] = -0.10
    rows[1]["daily_pnl"] = -0.08
    rows[1]["row_daily_loss_floor"] = -0.07
    rows[1]["loss_streak"] = 0
    rows[1]["row_max_loss_streak"] = 5
    rows[2]["strategy_drawdown"] = -0.05
    rows[2]["row_drawdown_floor"] = -0.10
    rows[2]["daily_pnl"] = 0.0
    rows[2]["row_daily_loss_floor"] = -0.05
    rows[2]["loss_streak"] = 4
    rows[2]["row_max_loss_streak"] = 4
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            "    max_drawdown_floor_column: row_drawdown_floor\n"
            "    daily_loss_column: daily_pnl\n"
            "    daily_loss_floor_column: row_daily_loss_floor\n"
            "    loss_streak_column: loss_streak\n"
            "    max_loss_streak_column: row_max_loss_streak",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["none", "none", "none"]
    assert frame.get_column("block_reasons").to_list() == [
        ["risk_throttle_max_drawdown"],
        ["risk_throttle_daily_loss"],
        ["risk_throttle_loss_streak"],
    ]


def test_authoring_risk_throttle_threshold_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "risk-throttle-empty-threshold-column.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            '    max_drawdown_floor_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_drawdown_floor_column"):
        load_authoring_spec(spec_path)


def test_authoring_risk_throttle_row_loss_streak_threshold_must_be_positive(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "risk-throttle-invalid-row-loss-streak.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["loss_streak"] = 1
    rows[0]["row_max_loss_streak"] = 0
    pl.DataFrame(rows[:1]).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    loss_streak_column: loss_streak\n"
            "    max_loss_streak_column: row_max_loss_streak",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyAuthoringValidationError, match="max_loss_streak"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)


def test_authoring_risk_throttle_conservative_profile_applies_defaults(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "risk-throttle-profile.yaml"
    _write_data(data_dir)
    rows = _feature_rows()
    rows[0]["strategy_drawdown"] = -0.05
    rows[0]["daily_pnl"] = 0.0
    rows[0]["loss_streak"] = 0
    rows[1]["strategy_drawdown"] = -0.20
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
            "    profile: conservative",
        ),
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert spec.rules.risk_throttle.max_drawdown_column == "strategy_drawdown"
    assert spec.rules.risk_throttle.max_drawdown_floor == -0.15
    assert spec.rules.risk_throttle.daily_loss_column == "daily_pnl"
    assert spec.rules.risk_throttle.daily_loss_floor == -0.05
    assert spec.rules.risk_throttle.loss_streak_column == "loss_streak"
    assert spec.rules.risk_throttle.max_loss_streak == 3
    assert frame.filter(pl.col("side") != "none").height == 1
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["risk_throttle_max_drawdown"],
        ["risk_throttle_loss_streak"],
    ]


def test_authoring_risk_throttle_profile_keeps_explicit_thresholds(tmp_path) -> None:
    spec_path = tmp_path / "risk-throttle-profile.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    profile: strict\n"
            "    max_drawdown_floor: -0.25\n"
            "    daily_loss_floor: -0.08\n"
            "    max_loss_streak: 5",
        ),
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)

    assert spec.rules.risk_throttle.max_drawdown_floor == -0.25
    assert spec.rules.risk_throttle.daily_loss_floor == -0.08
    assert spec.rules.risk_throttle.max_loss_streak == 5


def test_authoring_risk_throttle_cooldown_blocks_following_signals(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "risk-throttle-cooldown.yaml"
    _write_data(data_dir)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        {**_feature_rows()[0], "ts": start, "strategy_drawdown": -0.20},
        {
            **_feature_rows()[1],
            "ts": start + timedelta(minutes=60),
            "strategy_drawdown": -0.05,
        },
        {
            **_feature_rows()[2],
            "ts": start + timedelta(minutes=120),
            "strategy_drawdown": -0.05,
        },
    ]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    max_drawdown_column: strategy_drawdown\n"
            "    max_drawdown_floor: -0.15\n"
            "    cooldown_minutes: 90",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["none", "none", "long"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["risk_throttle_max_drawdown"],
        ["risk_throttle_cooldown"],
    ]


def test_authoring_risk_throttle_cooldown_must_be_positive(tmp_path) -> None:
    spec_path = tmp_path / "risk-throttle-cooldown-invalid.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  risk_throttle:\n"
            "    cooldown_minutes: 0",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cooldown_minutes must be positive"):
        load_authoring_spec(spec_path)


def test_authoring_execution_profile_applies_defaults_without_overriding_explicit_fields(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "execution-profile.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pl.DataFrame(
        [
            {
                "ts": start,
                "canonical_symbol": "QQQ",
                "trade_allowed": True,
                "latency_ms": 50.0,
                "queue_position_score": 0.8,
                "turnover_pressure": 0.2,
                "capacity_usage_ratio": 0.3,
                "correlation_crowding_score": 0.4,
                "maker_taker_fee_edge_bps": 1.5,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: conservative_execution_profile_v1
  strategy_family: execution_profile
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
rules:
  side: long
  timeframe: 1h
  execution:
    profile: conservative
    max_spread_bps: 12
  entry:
    all:
      - column: trade_allowed
        op: is_true
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    assert spec.rules.execution.slippage_bps == 25.0
    assert spec.rules.execution.max_fill_fraction == 0.5
    assert spec.rules.execution.max_spread_bps == 12.0
    assert spec.rules.execution.min_depth_usd == 250_000.0
    assert spec.rules.execution.depth_participation_rate == 0.05
    assert spec.rules.execution.max_latency_ms == 100.0
    assert spec.rules.execution.min_queue_position_score == 0.6
    assert spec.rules.execution.max_turnover_pressure == 0.4
    assert spec.rules.execution.max_capacity_usage_ratio == 0.5
    assert spec.rules.execution.max_correlation_crowding_score == 0.6
    assert spec.rules.execution.min_fee_edge_bps == 0.0
    assert frame.select(
        [
            "slippage_bps",
            "max_fill_fraction",
            "max_spread_bps",
            "min_depth_usd",
            "depth_participation_rate",
            "max_latency_ms",
            "latency_ms",
            "min_queue_position_score",
            "queue_position_score",
            "max_turnover_pressure",
            "turnover_pressure",
            "max_capacity_usage_ratio",
            "capacity_usage_ratio",
            "max_correlation_crowding_score",
            "correlation_crowding_score",
            "min_fee_edge_bps",
            "fee_edge_bps",
        ]
    ).rows() == [
        (
            25.0,
            0.5,
            12.0,
            250_000.0,
            0.05,
            100.0,
            50.0,
            0.6,
            0.8,
            0.4,
            0.2,
            0.5,
            0.3,
            0.6,
            0.4,
            0.0,
            1.5,
        )
    ]


def test_authoring_data_guard_strict_profile_blocks_stale_low_quality_and_regime_shift(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "data-guard-strict.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        ("AAA", 0.01, 10.0, 0.9, 0.9, 1.0, 0.1),
        ("BBB", 0.04, 45.0, 0.9, 0.9, 1.0, 0.1),
        ("CCC", 0.03, 10.0, 0.5, 0.9, 1.0, 0.1),
        ("DDD", 0.02, 10.0, 0.9, 0.9, 1.0, 0.8),
    ]
    pl.DataFrame(
        [
            {
                "ts": ts,
                "canonical_symbol": symbol,
                "trade_allowed": True,
                "research_return_1d": score,
                "feature_age_minutes": feature_age,
                "source_confidence": source_confidence,
                "venue_quality_score": venue_quality,
                "staleness_bps": staleness_bps,
                "regime_transition_score": regime_transition,
            }
            for (
                symbol,
                score,
                feature_age,
                source_confidence,
                venue_quality,
                staleness_bps,
                regime_transition,
            ) in rows
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: strict_data_guard_authoring_v1
  strategy_family: data_guard
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
  side: long
  timeframe: 1h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  data_guard:
    profile: strict
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: strict_data_guard_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)

    live = frame.filter(pl.col("side") == "long")
    assert live.get_column("execution_symbol").to_list() == ["AAA100"]
    blocked = frame.filter(pl.col("side") == "none").sort("execution_symbol")
    assert blocked.get_column("execution_symbol").to_list() == ["BBB100", "CCC100", "DDD100"]
    assert blocked.get_column("block_reasons").to_list() == [
        ["data_guard_feature_age_too_old"],
        ["data_guard_source_confidence_too_low"],
        ["data_guard_regime_transition_too_high"],
    ]


def test_authoring_data_guard_can_use_row_threshold_columns(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "data-guard-row-thresholds.yaml"
    _write_data(data_dir)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        {
            **_feature_rows()[0],
            "ts": start + timedelta(hours=index),
            "feature_age_minutes": feature_age,
            "row_max_feature_age_minutes": max_feature_age,
            "source_confidence": source_confidence,
            "row_min_source_confidence": min_source_confidence,
            "venue_quality_score": venue_quality,
            "row_min_venue_quality_score": min_venue_quality,
            "staleness_bps": staleness_bps,
            "row_max_staleness_bps": max_staleness_bps,
            "regime_transition_score": regime_transition,
            "row_max_regime_transition_score": max_regime_transition,
        }
        for index, (
            feature_age,
            max_feature_age,
            source_confidence,
            min_source_confidence,
            venue_quality,
            min_venue_quality,
            staleness_bps,
            max_staleness_bps,
            regime_transition,
            max_regime_transition,
        ) in enumerate(
            [
                (10.0, 30.0, 0.9, 0.8, 0.9, 0.8, 1.0, 5.0, 0.1, 0.5),
                (45.0, 30.0, 0.9, 0.8, 0.9, 0.8, 1.0, 5.0, 0.1, 0.5),
                (10.0, 30.0, 0.7, 0.8, 0.9, 0.8, 1.0, 5.0, 0.1, 0.5),
                (10.0, 30.0, 0.9, 0.8, 0.7, 0.8, 1.0, 5.0, 0.1, 0.5),
                (10.0, 30.0, 0.9, 0.8, 0.9, 0.8, 9.0, 5.0, 0.1, 0.5),
                (10.0, 30.0, 0.9, 0.8, 0.9, 0.8, 1.0, 5.0, 0.8, 0.5),
            ]
        )
    ]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  data_guard:\n"
            "    max_feature_age_minutes: 60\n"
            "    max_feature_age_minutes_column: row_max_feature_age_minutes\n"
            "    min_source_confidence: 0.5\n"
            "    min_source_confidence_column: row_min_source_confidence\n"
            "    min_venue_quality_score: 0.5\n"
            "    min_venue_quality_score_column: row_min_venue_quality_score\n"
            "    max_staleness_bps: 10\n"
            "    max_staleness_bps_column: row_max_staleness_bps\n"
            "    max_regime_transition_score: 1.0\n"
            "    max_regime_transition_score_column: row_max_regime_transition_score",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == [
        "long",
        "none",
        "none",
        "none",
        "none",
        "none",
    ]
    assert frame.get_column("block_reasons").to_list() == [
        [],
        ["data_guard_feature_age_too_old"],
        ["data_guard_source_confidence_too_low"],
        ["data_guard_venue_quality_too_low"],
        ["data_guard_staleness_too_high"],
        ["data_guard_regime_transition_too_high"],
    ]


def test_authoring_data_guard_threshold_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "data-guard-empty-threshold-column.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            '  portfolio:\n    max_signals_per_timestamp: 3\n  data_guard:\n    max_feature_age_minutes_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_feature_age_minutes_column"):
        load_authoring_spec(spec_path)


def test_authoring_data_guard_row_thresholds_validate_ranges(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "data-guard-invalid-row-threshold.yaml"
    _write_data(data_dir)
    rows = [
        {
            **_feature_rows()[0],
            "feature_age_minutes": 10.0,
            "row_min_source_confidence": 1.5,
        }
    ]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  data_guard:\n"
            "    min_source_confidence_column: row_min_source_confidence",
        ),
        encoding="utf-8",
    )

    with pytest.raises(StrategyAuthoringValidationError, match="min_source_confidence"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)
