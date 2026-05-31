# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


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
    group_ids = frame.get_column("multi_leg_group_id").to_list()
    assert group_ids[0] is not None
    assert group_ids[0] == group_ids[1]
    assert frame.get_column("multi_leg_leg_index").to_list() == [1, 2]
    assert frame.get_column("multi_leg_leg_count").to_list() == [2, 2]
    assert frame.get_column("multi_leg_anchor_real_market_symbol").to_list() == ["AAA", "AAA"]
    assert frame.get_column("reason_codes").to_list() == [
        ["pair_trade_v1", "multi_leg", "long_leg"],
        ["pair_trade_v1", "multi_leg", "hedge_leg"],
    ]


def test_authoring_backtest_summarizes_multi_leg_groups(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "pair-backtest.yaml"
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
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
    quote_rows = []
    for symbol, entry, exit_ in (("AAA100", 100.0, 104.0), ("BBB100", 50.0, 48.0)):
        quote_rows.extend(
            [
                {**_quote(ts, entry), "canonical_symbol": symbol, "venue_symbol": symbol},
                {
                    **_quote(ts + timedelta(hours=4), exit_),
                    "canonical_symbol": symbol,
                    "venue_symbol": symbol,
                },
            ]
        )
    pl.DataFrame(quote_rows).write_parquet(quote_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: pair_trade_backtest_v1
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
    position_weight: 1.0
    notional_usd: 1000
  reason_code: pair_trade_v1
backtest:
  label_horizon_minutes: 240
  split_method: walk_forward
  era_unit: trading_day
  pass_thresholds:
    multi_leg_group_metrics.complete_group_count: 1
    multi_leg_group_metrics.incomplete_group_count: 0
    multi_leg_group_metrics.total_return: 0.01
    multi_leg_group_metrics.avg_leg_return_imbalance: 0.001
optimizer:
  parameter_sweep:
    rules.sizing.position_weight: [0.5, 1.0]
  selection_metric: multi_leg_group_metrics.total_return
  selection_direction: auto
  max_variants: 4
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["strategy-author-run", "--spec", str(spec_path), "--through", "paper-preview"]
    )

    assert result.exit_code == 0, result.stdout
    metrics = json.loads(
        (data_dir / "research/strategy_backtest_metrics.json").read_text(encoding="utf-8")
    )
    validate(
        metrics,
        json.loads(
            Path("schemas/strategy_authoring_backtest_result.v1.schema.json").read_text(
                encoding="utf-8"
            )
        ),
    )
    group_metrics = metrics["summary"]["multi_leg_group_metrics"]
    assert group_metrics["group_count"] == 1
    assert group_metrics["complete_group_count"] == 1
    assert group_metrics["executed_leg_count"] == 2
    assert group_metrics["expected_leg_count"] == 2
    assert group_metrics["avg_group_return"] == pytest.approx(group_metrics["total_return"])
    assert group_metrics["win_rate"] == 1.0
    assert group_metrics["worst_group_return"] == pytest.approx(group_metrics["total_return"])
    assert group_metrics["max_drawdown"] == 0.0
    assert group_metrics["profit_factor"] is None
    assert group_metrics["avg_leg_return_imbalance"] > 0
    executed_group_results = [
        result
        for result in metrics["summary"]["executed_signal_results"]
        if result["multi_leg_group_id"]
    ]
    expected_notional = sum(result["notional_usd"] for result in executed_group_results)
    expected_notional_weighted_return = (
        sum(result["signal_return"] * result["notional_usd"] for result in executed_group_results)
        / expected_notional
    )
    assert group_metrics["total_notional_usd"] == pytest.approx(1000.0)
    assert group_metrics["notional_weighted_total_return"] == pytest.approx(
        expected_notional_weighted_return
    )
    group = group_metrics["groups"][0]
    assert group["anchor_real_market_symbol"] == "AAA"
    assert group["leg_count"] == 2
    assert group["executed_leg_count"] == 2
    assert group["complete"] is True
    assert group["total_return"] > 0
    assert group["total_notional_usd"] == pytest.approx(1000.0)
    assert group["notional_weighted_return"] == pytest.approx(expected_notional_weighted_return)
    assert group["avg_leg_return"] > 0
    assert group["leg_return_imbalance"] > 0
    assert group["win"] is True
    assert group["exit_reason_counts"] == {"fixed_horizon": 2}
    era_group_metrics = metrics["summary"]["walk_forward_eras"][0]["multi_leg_group_metrics"]
    assert era_group_metrics["complete_group_count"] == 1
    variants = metrics["summary"]["optimizer"]["variants"]
    assert len(variants) == 2
    assert metrics["summary"]["optimizer"]["selection_direction"] == "auto"
    assert metrics["summary"]["optimizer"]["resolved_selection_direction"] == "maximize"
    assert all("multi_leg_group_metrics" in variant for variant in variants)
    assert (
        metrics["summary"]["optimizer"]["best_variant"]["multi_leg_group_metrics"][
            "complete_group_count"
        ]
        == 1
    )
    assert (
        metrics["summary"]["optimizer"]["best_variant"]["parameters"][
            "rules.sizing.position_weight"
        ]
        == 1.0
    )
    thresholds = metrics["summary"]["pass_thresholds"]
    assert thresholds["multi_leg_group_metrics.complete_group_count"]["actual"] == 1
    assert thresholds["multi_leg_group_metrics.complete_group_count"]["passed"] is True
    assert thresholds["multi_leg_group_metrics.incomplete_group_count"]["actual"] == 0
    assert thresholds["multi_leg_group_metrics.incomplete_group_count"]["passed"] is True
    assert thresholds["multi_leg_group_metrics.total_return"]["actual"] > 0.01
    assert thresholds["multi_leg_group_metrics.total_return"]["passed"] is True
    assert thresholds["multi_leg_group_metrics.avg_leg_return_imbalance"]["actual"] > 0.001
    assert thresholds["multi_leg_group_metrics.avg_leg_return_imbalance"]["passed"] is False
    decision = json.loads(
        (data_dir / "research/promotion_decision.json").read_text(encoding="utf-8")
    )
    scorecard_group_metrics = decision["scorecard_summary"]["multi_leg_group_metrics"]
    assert scorecard_group_metrics["group_count"] == 1
    assert scorecard_group_metrics["complete_group_count"] == 1
    assert scorecard_group_metrics["incomplete_group_count"] == 0
    assert scorecard_group_metrics["expected_leg_count"] == 2
    assert scorecard_group_metrics["executed_leg_count"] == 2
    assert scorecard_group_metrics["total_return"] == pytest.approx(group_metrics["total_return"])
    assert scorecard_group_metrics["avg_group_return"] == pytest.approx(
        group_metrics["avg_group_return"]
    )
    assert scorecard_group_metrics["win_rate"] == 1.0
    assert scorecard_group_metrics["worst_group_return"] == pytest.approx(
        group_metrics["worst_group_return"]
    )
    assert scorecard_group_metrics["max_drawdown"] == 0.0
    assert scorecard_group_metrics["profit_factor"] is None
    assert scorecard_group_metrics["avg_leg_return_imbalance"] == pytest.approx(
        group_metrics["avg_leg_return_imbalance"]
    )
    assert scorecard_group_metrics["total_notional_usd"] == pytest.approx(
        group_metrics["total_notional_usd"]
    )
    assert scorecard_group_metrics["notional_weighted_total_return"] == pytest.approx(
        group_metrics["notional_weighted_total_return"]
    )
    assert scorecard_group_metrics["cost_drag_bps"] == pytest.approx(group_metrics["cost_drag_bps"])
    assert "groups" not in scorecard_group_metrics


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


def test_authoring_multi_leg_supports_leg_exit_overrides(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "pair-leg-exit.yaml"
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
  strategy_id: pair_leg_exit_authoring_v1
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
  exit:
    stop_loss_bps: 100
    take_profit_bps: 200
    trailing_stop_bps: 80
    partial_take_profit_bps: 120
    partial_exit_fraction: 0.5
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 1.0
        stop_loss_bps: 90
        take_profit_bps: 180
        reason_code: lead_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.5
        stop_loss_bps: 140
        take_profit_bps: 260
        trailing_stop_bps: 110
        partial_take_profit_bps: 160
        partial_exit_fraction: 0.25
        reason_code: hedge_leg
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  reason_code: pair_leg_exit_v1
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
    assert frame.get_column("stop_loss_bps").to_list() == [90.0, 140.0]
    assert frame.get_column("take_profit_bps").to_list() == [180.0, 260.0]
    assert frame.get_column("trailing_stop_bps").to_list() == [80.0, 110.0]
    assert frame.get_column("partial_take_profit_bps").to_list() == [120.0, 160.0]
    assert frame.get_column("partial_exit_fraction").to_list() == [0.5, 0.25]


def test_authoring_multi_leg_supports_row_level_leg_exit_overrides(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "row-leg-exit.yaml"
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
                "global_stop_bps": 999.0,
                "global_take_bps": 999.0,
                "lead_stop_bps": 95.0,
                "lead_take_bps": 190.0,
                "hedge_stop_bps": 145.0,
                "hedge_take_bps": 270.0,
                "hedge_trailing_bps": 115.0,
                "hedge_partial_bps": 165.0,
                "hedge_partial_fraction": 0.3,
                "hedge_min_rr": 1.75,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: row_pair_leg_exit_authoring_v1
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
  exit:
    stop_loss_bps: 100
    stop_loss_bps_column: global_stop_bps
    take_profit_bps: 200
    take_profit_bps_column: global_take_bps
    trailing_stop_bps: 80
    partial_take_profit_bps: 120
    partial_exit_fraction: 0.5
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 1.0
        stop_loss_bps_column: lead_stop_bps
        take_profit_bps_column: lead_take_bps
        reason_code: lead_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.5
        stop_loss_bps_column: hedge_stop_bps
        take_profit_bps_column: hedge_take_bps
        trailing_stop_bps_column: hedge_trailing_bps
        partial_take_profit_bps_column: hedge_partial_bps
        partial_exit_fraction_column: hedge_partial_fraction
        min_reward_risk_ratio_column: hedge_min_rr
        reason_code: hedge_leg
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  reason_code: row_pair_leg_exit_v1
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
    assert frame.get_column("stop_loss_bps").to_list() == [95.0, 145.0]
    assert frame.get_column("take_profit_bps").to_list() == [190.0, 270.0]
    assert frame.get_column("trailing_stop_bps").to_list() == [80.0, 115.0]
    assert frame.get_column("partial_take_profit_bps").to_list() == [120.0, 165.0]
    assert frame.get_column("partial_exit_fraction").to_list() == [0.5, 0.3]
    assert frame.get_column("min_reward_risk_ratio").to_list() == [None, 1.75]


def test_authoring_multi_leg_exit_overrides_must_be_valid(tmp_path) -> None:
    spec_path = tmp_path / "bad-leg-exit.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  sizing:\n    position_weight: 1.0",
            "  multi_leg:\n"
            "    enabled: true\n"
            "    anchor_real_market_symbol: QQQ\n"
            "    legs:\n"
            "      - real_market_symbol: QQQ\n"
            "        side: same\n"
            "        stop_loss_bps: -1\n"
            "  sizing:\n    position_weight: 1.0",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.multi_leg.legs\\[\\].stop_loss_bps"):
        load_authoring_spec(spec_path)


def test_authoring_multi_leg_exit_override_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "bad-leg-exit-column.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  sizing:\n    position_weight: 1.0",
            "  multi_leg:\n"
            "    enabled: true\n"
            "    anchor_real_market_symbol: QQQ\n"
            "    legs:\n"
            "      - real_market_symbol: QQQ\n"
            "        side: same\n"
            '        stop_loss_bps_column: ""\n'
            "  sizing:\n    position_weight: 1.0",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.multi_leg.legs\\[\\].stop_loss_bps_column"):
        load_authoring_spec(spec_path)


def test_authoring_multi_leg_supports_leg_order_overrides(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "pair-leg-order.yaml"
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
                "hedge_limit_offset_bps": 35.0,
                "hedge_timeout_minutes": 45,
                "hedge_tif": "gtd",
                "hedge_post_only": True,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: pair_leg_order_authoring_v1
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
  order:
    entry_type: market
    time_in_force: gtc
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 1.0
        reason_code: lead_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.5
        entry_type: limit
        limit_offset_bps_column: hedge_limit_offset_bps
        time_in_force_column: hedge_tif
        timeout_minutes_column: hedge_timeout_minutes
        post_only_column: hedge_post_only
        reason_code: hedge_leg
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  reason_code: pair_leg_order_v1
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
    assert frame.get_column("entry_order_type").to_list() == ["market", "limit"]
    assert frame.get_column("entry_limit_offset_bps").to_list() == [None, 35.0]
    assert frame.get_column("entry_time_in_force").to_list() == ["gtc", "gtd"]
    assert frame.get_column("entry_timeout_minutes").to_list() == [None, 45]
    assert frame.get_column("entry_post_only").to_list() == [False, True]


def test_authoring_multi_leg_order_override_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "bad-leg-order-column.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  sizing:\n    position_weight: 1.0",
            "  multi_leg:\n"
            "    enabled: true\n"
            "    anchor_real_market_symbol: QQQ\n"
            "    legs:\n"
            "      - real_market_symbol: QQQ\n"
            "        side: same\n"
            '        entry_type_column: ""\n'
            "  sizing:\n    position_weight: 1.0",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.multi_leg.legs\\[\\].entry_type_column"):
        load_authoring_spec(spec_path)


def test_authoring_multi_leg_supports_leg_execution_overrides(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "pair-leg-execution.yaml"
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
                "hedge_slippage_bps": 22.0,
                "hedge_min_fill": 0.3,
                "hedge_spread_cap": 12.0,
                "hedge_latency_ms": 35.0,
                "hedge_queue_required": 0.7,
                "hedge_queue_score": 0.8,
                "hedge_tax_drag_bps": 4.0,
            }
        ]
    ).write_parquet(feature_path)
    spec_path.write_text(
        """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: pair_leg_execution_authoring_v1
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
  execution:
    slippage_bps: 5
    max_fill_fraction: 0.9
    max_spread_bps: 100
  multi_leg:
    enabled: true
    anchor_real_market_symbol: AAA
    legs:
      - real_market_symbol: AAA
        side: same
        position_weight: 1.0
        reason_code: lead_leg
      - real_market_symbol: BBB
        side: opposite
        position_weight: 0.5
        slippage_bps_column: hedge_slippage_bps
        max_fill_fraction: 0.4
        min_fill_fraction_column: hedge_min_fill
        max_spread_bps_column: hedge_spread_cap
        max_latency_ms: 50
        latency_column: hedge_latency_ms
        min_queue_position_score_column: hedge_queue_required
        queue_position_score_column: hedge_queue_score
        max_tax_drag_bps: 7
        tax_drag_column: hedge_tax_drag_bps
        reason_code: hedge_leg
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  reason_code: pair_leg_execution_v1
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
    assert frame.get_column("slippage_bps").to_list() == [5.0, 22.0]
    assert frame.get_column("max_fill_fraction").to_list() == [0.9, 0.4]
    assert frame.get_column("min_fill_fraction").to_list() == [None, 0.3]
    assert frame.get_column("max_spread_bps").to_list() == [100.0, 12.0]
    assert frame.get_column("max_latency_ms").to_list() == [None, 50.0]
    assert frame.get_column("latency_ms").to_list() == [None, 35.0]
    assert frame.get_column("min_queue_position_score").to_list() == [None, 0.7]
    assert frame.get_column("queue_position_score").to_list() == [None, 0.8]
    assert frame.get_column("max_tax_drag_bps").to_list() == [None, 7.0]
    assert frame.get_column("tax_drag_bps").to_list() == [None, 4.0]


def test_authoring_multi_leg_execution_override_columns_must_be_non_empty(
    tmp_path,
) -> None:
    spec_path = tmp_path / "bad-leg-execution-column.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "  sizing:\n    position_weight: 1.0",
            "  multi_leg:\n"
            "    enabled: true\n"
            "    anchor_real_market_symbol: QQQ\n"
            "    legs:\n"
            "      - real_market_symbol: QQQ\n"
            "        side: same\n"
            '        slippage_bps_column: ""\n'
            "  sizing:\n    position_weight: 1.0",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.multi_leg.legs\\[\\].slippage_bps_column"):
        load_authoring_spec(spec_path)
