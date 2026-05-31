# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


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


def test_authoring_portfolio_total_exposure_limit_can_use_row_column(tmp_path) -> None:
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
                "max_total_budget": 1.0,
            }
            for symbol, score in [("AAA", 0.03), ("BBB", 0.02), ("CCC", 0.01)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: row_total_exposure_limited_authoring_v1
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
    max_total_position_weight_column: max_total_budget
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: row_total_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list().count("long") == 1
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.height == 2
    assert blocked.get_column("block_reasons").to_list() == [
        ["portfolio_total_exposure_limit"],
        ["portfolio_total_exposure_limit"],
    ]


def test_authoring_portfolio_total_exposure_limit_rejects_mixed_row_column(
    tmp_path,
) -> None:
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
                "research_return_1d": 0.01,
                "research_return_4h": 0.01,
                "max_total_budget": budget,
            }
            for symbol, budget in [("AAA", 1.0), ("BBB", 0.5)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: mixed_row_total_exposure_limited_authoring_v1
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
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  portfolio:
    max_total_position_weight_column: max_total_budget
  reason_code: mixed_row_total_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_total_position_weight_column"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)


def test_authoring_portfolio_side_exposure_limits_can_use_row_columns(tmp_path) -> None:
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
                "max_long_budget": 1.0,
                "max_short_budget": 1.0,
            }
            for symbol, direction, score in [
                ("AAA", "long", 0.04),
                ("BBB", "short", 0.03),
                ("CCC", "long", 0.02),
                ("DDD", "short", 0.01),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: row_side_exposure_limited_authoring_v1
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
    position_weight: 0.6
  portfolio:
    max_long_position_weight_column: max_long_budget
    max_short_position_weight_column: max_short_budget
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: row_side_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    live = frame.filter(pl.col("side") != "none").sort("execution_symbol")
    assert live.select("execution_symbol", "side").rows() == [
        ("AAA100", "long"),
        ("BBB100", "short"),
    ]
    blocked = frame.filter(pl.col("side") == "none").sort("execution_symbol")
    assert blocked.select("execution_symbol", "block_reasons").rows() == [
        ("CCC100", ["portfolio_long_exposure_limit"]),
        ("DDD100", ["portfolio_short_exposure_limit"]),
    ]


def test_authoring_portfolio_net_exposure_limit_can_use_row_column(tmp_path) -> None:
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
                "max_net_budget": 0.2,
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
  strategy_id: row_net_exposure_limited_authoring_v1
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
    max_abs_net_position_weight_column: max_net_budget
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: row_net_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    live = frame.filter(pl.col("side") != "none").sort("execution_symbol")
    assert live.select("execution_symbol", "side").rows() == [
        ("AAA100", "long"),
        ("BBB100", "short"),
    ]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_net_exposure_limit"]]


def test_authoring_portfolio_symbol_and_group_limits_can_use_row_columns(tmp_path) -> None:
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
                "max_symbol_budget": 0.8,
                "max_group_budget": 1.0,
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
  strategy_id: row_group_exposure_limited_authoring_v1
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
    max_symbol_position_weight_column: max_symbol_budget
    max_group_position_weight_column: max_group_budget
    group_column: sector_bucket
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: row_group_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    live = frame.filter(pl.col("side") == "long").sort("execution_symbol")
    assert live.get_column("execution_symbol").to_list() == ["AAA100", "CCC100"]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["BBB100"]
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_group_exposure_limit"]]


def test_authoring_portfolio_group_net_exposure_limit_can_use_row_column(tmp_path) -> None:
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
                "max_group_net_budget": 0.2,
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
  strategy_id: row_group_net_exposure_limited_authoring_v1
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
    max_group_abs_net_position_weight_column: max_group_net_budget
    group_column: sector_bucket
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: row_group_net_exposure_limited_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    live = frame.filter(pl.col("side") != "none").sort("execution_symbol")
    assert live.select("execution_symbol", "side").rows() == [
        ("AAA100", "long"),
        ("BBB100", "short"),
    ]
    blocked = frame.filter(pl.col("side") == "none")
    assert blocked.get_column("execution_symbol").to_list() == ["CCC100"]
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_group_net_exposure_limit"]]


def test_authoring_portfolio_exposure_limit_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: empty_portfolio_exposure_column_v1
  strategy_family: exposure_limited
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
  portfolio:
    max_long_position_weight_column: ""
  reason_code: empty_portfolio_exposure_column_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_long_position_weight_column"):
        load_authoring_spec(spec_path)


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


def test_authoring_portfolio_turnover_budget_blocks_excess_rotation(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-turnover-budget.yaml"
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
                "planned_turnover_weight": turnover_weight,
            }
            for symbol, score, turnover_weight in [
                ("AAA", 0.03, 0.6),
                ("BBB", 0.02, 0.5),
                ("CCC", 0.01, 0.4),
            ]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: turnover_budget_authoring_v1
  strategy_family: turnover_budget
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
    position_weight: 0.5
  portfolio:
    max_turnover_weight_per_timestamp: 1.0
    turnover_weight_column: planned_turnover_weight
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
  reason_code: turnover_budget_v1
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
    assert blocked.get_column("block_reasons").to_list() == [["portfolio_turnover_budget_limit"]]


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


def test_authoring_portfolio_allocation_can_use_row_target_total_weight(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-row-target.yaml"
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
                "target_weight_budget": 0.5,
            }
            for symbol, score in [("AAA", 0.03), ("BBB", 0.01)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: row_target_allocation_authoring_v1
  strategy_family: allocation
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
    target_total_position_weight_column: target_weight_budget
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 100
  reason_code: row_target_allocation_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)
    assert validate_authoring_inputs(spec, data_dir=data_dir) == []
    frame, _manifest = build_authoring_signals(spec, data_dir=data_dir)
    frame = frame.sort("execution_symbol")

    assert frame.get_column("position_weight").to_list() == pytest.approx([0.375, 0.125])


def test_authoring_portfolio_allocation_rejects_mixed_row_target_total_weight(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "portfolio-mixed-row-target.yaml"
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
                "target_weight_budget": target,
            }
            for symbol, target in [("AAA", 0.5), ("BBB", 1.0)]
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: mixed_row_target_allocation_authoring_v1
  strategy_family: allocation
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
    allocation_method: equal_weight
    target_total_position_weight_column: target_weight_budget
  reason_code: mixed_row_target_allocation_v1
backtest:
  label_horizon_minutes: 240
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="one value per timestamp"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)


def test_authoring_portfolio_target_total_weight_column_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "portfolio-empty-row-target.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "    allocation_method: equal_weight\n"
            '    target_total_position_weight_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="target_total_position_weight_column"):
        load_authoring_spec(spec_path)


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
    validate(
        payload,
        json.loads(
            Path("schemas/strategy_authoring_bundle_result.v1.schema.json").read_text(
                encoding="utf-8"
            )
        ),
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
