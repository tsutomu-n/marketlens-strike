# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


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


def test_strategy_backtest_suite_runs_multiple_cases_for_spec(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    suite_path = tmp_path / "suite.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    _write_spec(spec_path)
    suite_path.write_text(
        f"""schema_version: strategy_backtest_suite.v1
suite_id: demo_backtest_suite
selection_metric: total_return
selection_direction: maximize
cases:
  - case_id: single_window_120m
    backtest:
      split_method: single_window
      label_horizon_minutes: 120
      min_trade_count: 1
  - case_id: walk_forward_240m
    backtest:
      split_method: walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
  - case_id: purged_walk_forward_240m
    backtest:
      split_method: purged_walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
  - case_id: return_bootstrap_240m
    backtest:
      split_method: purged_walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
    resampling:
      method: return_bootstrap
      iterations: 16
      seed: 7
  - case_id: block_bootstrap_240m
    backtest:
      split_method: purged_walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
    resampling:
      method: block_bootstrap
      iterations: 16
      seed: 11
      block_size: 2
members:
  - spec_path: {spec_path.name}
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["strategy-backtest-suite", "--suite", str(suite_path)])

    assert result.exit_code == 0, result.stdout
    assert "backtest_suite_result=" in result.stdout
    result_path = data_dir / "research/backtest_suite/strategy_backtest_suite_result.json"
    report_path = data_dir / "reports/strategy_backtest_suite_report.md"
    assert result_path.exists()
    assert report_path.exists()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_suite_result.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_suite_result.v1"
    assert payload["paper_only"] is True
    assert payload["live_order_submitted"] is False
    assert payload["permits_live_order"] is False
    assert payload["aggregate"]["run_count"] == 5
    assert payload["aggregate"]["passed_count"] == 5
    assert payload["method_matrix"]["method_count"] == 5
    assert {method["method_id"] for method in payload["method_matrix"]["methods"]} == {
        "single_window",
        "walk_forward:trading_day",
        "purged_walk_forward:trading_day",
        "purged_walk_forward:trading_day+return_bootstrap",
        "purged_walk_forward:trading_day+block_bootstrap",
    }
    assert payload["method_matrix"]["counts_by_method"] == {
        "purged_walk_forward:trading_day+block_bootstrap": 1,
        "purged_walk_forward:trading_day+return_bootstrap": 1,
        "purged_walk_forward:trading_day": 1,
        "single_window": 1,
        "walk_forward:trading_day": 1,
    }
    assert {run["case_id"] for run in payload["runs"]} == {
        "single_window_120m",
        "walk_forward_240m",
        "purged_walk_forward_240m",
        "return_bootstrap_240m",
        "block_bootstrap_240m",
    }
    assert {run["method_id"] for run in payload["runs"]} == {
        "single_window",
        "walk_forward:trading_day",
        "purged_walk_forward:trading_day",
        "purged_walk_forward:trading_day+return_bootstrap",
        "purged_walk_forward:trading_day+block_bootstrap",
    }
    resampled_runs = [
        run
        for run in payload["runs"]
        if run["method_id"]
        in {
            "purged_walk_forward:trading_day+return_bootstrap",
            "purged_walk_forward:trading_day+block_bootstrap",
        }
    ]
    assert len(resampled_runs) == 2
    assert all(run["resampling"]["status"] == "completed" for run in resampled_runs)
    assert all(run["summary"]["resampling"]["iteration_count"] == 16 for run in resampled_runs)
    assert all("total_return_p05" in run["summary"]["resampling"] for run in resampled_runs)
    assert payload["best_run"]["case_id"] in {
        "single_window_120m",
        "walk_forward_240m",
        "purged_walk_forward_240m",
        "return_bootstrap_240m",
        "block_bootstrap_240m",
    }
    assert all(run["summary"]["backtest_passed"] is True for run in payload["runs"])


def test_strategy_backtest_pack_runs_standard_backtest_artifact_chain(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    suite_path = tmp_path / "suite.yaml"
    bundle_path = tmp_path / "bundle.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    _write_spec(spec_path)
    suite_path.write_text(
        f"""schema_version: strategy_backtest_suite.v1
suite_id: demo_backtest_pack_suite
selection_metric: total_return
selection_direction: maximize
cases:
  - case_id: single_window_120m
    backtest:
      split_method: single_window
      label_horizon_minutes: 120
      min_trade_count: 1
  - case_id: walk_forward_240m
    backtest:
      split_method: walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
  - case_id: purged_walk_forward_240m
    backtest:
      split_method: purged_walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
  - case_id: return_bootstrap_240m
    backtest:
      split_method: purged_walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
    resampling:
      method: return_bootstrap
      iterations: 16
      seed: 7
  - case_id: block_bootstrap_240m
    backtest:
      split_method: purged_walk_forward
      era_unit: trading_day
      label_horizon_minutes: 240
      min_trade_count: 1
    resampling:
      method: block_bootstrap
      iterations: 16
      seed: 11
      block_size: 2
members:
  - spec_path: {spec_path.name}
""",
        encoding="utf-8",
    )
    bundle_path.write_text(
        f"""schema_version: strategy_authoring_bundle.v1
bundle_id: demo_pack_bundle
members:
  - spec_path: {spec_path.name}
    allocation_weight: 1.0
    enabled: true
portfolio:
  allocation_method: fixed_weight
  max_total_allocation_weight: 1.0
  selection_metric: total_return
  selection_direction: maximize
""",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "strategy-backtest-pack",
            "--spec",
            str(spec_path),
            "--suite",
            str(suite_path),
            "--bundle",
            str(bundle_path),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_pack=" in result.stdout
    assert "backtest_pack_validation=" in result.stdout
    assert "backtest_comparison=" in result.stdout
    assert "backtest_portfolio_comparison=" in result.stdout
    assert "backtest_metric_extension=" in result.stdout
    assert "backtest_report_extension=" in result.stdout
    assert "backtest_stress=" in result.stdout
    pack_path = data_dir / "research/backtest_pack/strategy_backtest_pack.json"
    validation_path = data_dir / "research/backtest_pack/strategy_backtest_pack_validation.json"
    comparison_path = data_dir / "research/backtest_compare/strategy_backtest_comparison.json"
    portfolio_path = (
        data_dir / "research/backtest_portfolio/strategy_backtest_portfolio_comparison.json"
    )
    metric_extension_path = (
        data_dir / "research/backtest_metric_extension/strategy_backtest_metric_extension.json"
    )
    report_extension_path = (
        data_dir / "research/backtest_report_extension/strategy_backtest_report_extension.json"
    )
    stress_path = data_dir / "research/backtest_stress/strategy_backtest_stress.json"
    assert pack_path.exists()
    assert validation_path.exists()
    assert comparison_path.exists()
    assert portfolio_path.exists()
    assert metric_extension_path.exists()
    assert report_extension_path.exists()
    assert stress_path.exists()
    payload = json.loads(pack_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_pack.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_pack.v1"
    assert payload["paper_only"] is True
    assert payload["permits_live_order"] is False
    assert payload["summary"]["suite_run_count"] == 5
    assert payload["summary"]["suite_method_count"] == 5
    assert payload["summary"]["suite_methods"] == {
        "purged_walk_forward:trading_day+block_bootstrap": 1,
        "purged_walk_forward:trading_day+return_bootstrap": 1,
        "purged_walk_forward:trading_day": 1,
        "single_window": 1,
        "walk_forward:trading_day": 1,
    }
    assert payload["external_framework_policy"] == {
        "policy_id": "native_primary_external_evaluation_only.v1",
        "standard_engine": "strategy_authoring_native",
        "decision": "complete_without_locked_external_dependency",
        "locked_dependency_added": False,
        "external_adapters_required_for_completion": False,
        "temporary_uv_with_allowed": ["vectorbt", "bt", "empyrical-reloaded", "quantstats"],
        "candidate_frameworks": [
            "vectorbt",
            "bt",
            "backtesting.py",
            "zipline-reloaded",
            "backtrader",
            "quantstats",
            "empyrical-reloaded",
            "pyfolio-reloaded",
            "qstrader",
        ],
        "adoption_requires": [
            "license_review",
            "python_3_13_uv_lock_review",
            "ci_green",
            "schema_boundary_review",
        ],
    }
    assert payload["artifacts"]["comparison"]["exists"] is True
    assert payload["artifacts"]["external_result"]["exists"] is True
    assert payload["artifacts"]["portfolio_comparison"]["exists"] is True
    assert payload["artifacts"]["metric_extension"]["exists"] is True
    assert payload["artifacts"]["report_extension"]["exists"] is True
    assert payload["artifacts"]["stress"]["exists"] is True
    assert payload["artifacts"]["stress_report"]["exists"] is True
    assert payload["artifacts"]["returns_series"]["exists"] is True
    assert (data_dir / "reports/strategy_backtest_pack_report.md").exists()
    validation_payload = json.loads(validation_path.read_text(encoding="utf-8"))
    validation_schema = json.loads(
        Path("schemas/strategy_backtest_pack_validation.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=validation_payload, schema=validation_schema)
    assert validation_payload["decision"] == "PASS"
    assert validation_payload["summary"]["failed_count"] == 0
    assert validation_payload["summary"]["external_framework_policy_decision"] == (
        "complete_without_locked_external_dependency"
    )
    assert validation_payload["summary"]["locked_dependency_added"] is False
    assert validation_payload["external_framework_policy"]["policy_id"] == (
        "native_primary_external_evaluation_only.v1"
    )
    assert (data_dir / "reports/strategy_backtest_pack_validation_report.md").exists()

    validate_result = runner.invoke(app, ["strategy-backtest-pack-validate"])

    assert validate_result.exit_code == 0, validate_result.stdout
    assert "decision=PASS" in validate_result.stdout


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


def test_strategy_authoring_bundle_can_rank_by_dotted_summary_metric(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
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
    spec_template = """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: {strategy_id}
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
    position_weight: {position_weight}
    notional_usd: 1000
  reason_code: pair_trade_v1
backtest:
  label_horizon_minutes: 240
  min_trade_count: 1
"""
    spec_low = tmp_path / "pair_low.yaml"
    spec_high = tmp_path / "pair_high.yaml"
    spec_low.write_text(
        spec_template.format(strategy_id="pair_low_group_return_v1", position_weight=0.25),
        encoding="utf-8",
    )
    spec_high.write_text(
        spec_template.format(strategy_id="pair_high_group_return_v1", position_weight=1.0),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(
        f"""schema_version: strategy_authoring_bundle.v1
bundle_id: pair_group_metric_bundle_v1
members:
  - spec_path: {spec_low.name}
    allocation_weight: 0.5
  - spec_path: {spec_high.name}
    allocation_weight: 0.5
portfolio:
  selection_metric: multi_leg_group_metrics.total_return
  selection_direction: maximize
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-author-bundle-run", "--bundle", str(bundle_path)])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (data_dir / "research/strategy_authoring_bundle_result.json").read_text(encoding="utf-8")
    )
    assert payload["best_member"]["strategy_id"] == "pair_high_group_return_v1"
    assert (
        payload["best_member"]["summary"]["multi_leg_group_metrics"]["total_return"]
        > payload["members"][1]["summary"]["multi_leg_group_metrics"]["total_return"]
    )
    bundle_group_metrics = payload["aggregate_metrics"]["multi_leg_group_metrics"]
    member_weighted_return = sum(
        member["summary"]["multi_leg_group_metrics"]["total_return"]
        * member["effective_allocation_weight"]
        for member in payload["members"]
    )
    assert bundle_group_metrics["group_count"] == 2
    assert bundle_group_metrics["complete_group_count"] == 2
    assert bundle_group_metrics["incomplete_group_count"] == 0
    assert bundle_group_metrics["expected_leg_count"] == 4
    assert bundle_group_metrics["executed_leg_count"] == 4
    assert bundle_group_metrics["weighted_total_return"] == pytest.approx(member_weighted_return)
    assert bundle_group_metrics["weighted_cost_drag_bps"] == pytest.approx(
        sum(
            member["summary"]["multi_leg_group_metrics"]["cost_drag_bps"]
            * member["effective_allocation_weight"]
            for member in payload["members"]
        )
    )
    assert bundle_group_metrics["weighted_avg_leg_return_imbalance"] == pytest.approx(
        sum(
            member["summary"]["multi_leg_group_metrics"]["avg_leg_return_imbalance"]
            * member["effective_allocation_weight"]
            for member in payload["members"]
        )
    )
    expected_total_notional = sum(
        member["summary"]["multi_leg_group_metrics"]["total_notional_usd"]
        for member in payload["members"]
    )
    expected_weighted_notional_return = sum(
        member["summary"]["multi_leg_group_metrics"]["notional_weighted_total_return"]
        * member["effective_allocation_weight"]
        for member in payload["members"]
    )
    assert bundle_group_metrics["total_notional_usd"] == pytest.approx(expected_total_notional)
    assert bundle_group_metrics["weighted_notional_return"] == pytest.approx(
        expected_weighted_notional_return
    )
    report = (data_dir / "reports/strategy_authoring_bundle_report.md").read_text(encoding="utf-8")
    assert "## Multi-Leg Group Metrics" in report
    assert f"- group_count: {bundle_group_metrics['group_count']}" in report
    assert "- complete_group_count: 2" in report
    assert "- incomplete_group_count: 0" in report
    assert "- weighted_total_return:" in report
    assert "- group_completion_rate: 1.000000" in report
    assert "- weighted_win_rate:" in report
    assert "- worst_group_return:" in report
    assert "- weighted_max_drawdown:" in report
    assert "- total_notional_usd:" in report
    assert "- weighted_notional_return:" in report
    assert "- weighted_profit_factor:" in report
    assert "- weighted_avg_leg_return_imbalance:" in report
    assert (
        "| Strategy | Groups | Complete | Completion Rate | Weighted Group Return | "
        "Weighted Notional Return | Total Notional USD | Weighted Win Rate | "
        "Weighted Max Drawdown | Weighted Profit Factor | Weighted Leg Imbalance |"
    ) in report


def test_strategy_authoring_bundle_auto_direction_minimizes_lower_is_better_metric(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
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
    spec_template = """
schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: {strategy_id}
  strategy_family: pair_trade
  strategy_version: v1
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: AAA100
      real_market_symbol: AAA
      asset_class: equity
    - execution_venue: trade_xyz
      execution_symbol: {hedge_execution_symbol}
      real_market_symbol: {hedge_real_market_symbol}
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
      - real_market_symbol: {hedge_real_market_symbol}
        side: opposite
        position_weight: 0.4
        reason_code: hedge_leg
  sizing:
    position_weight: 1.0
    notional_usd: 1000
  reason_code: pair_trade_v1
backtest:
  label_horizon_minutes: 240
  min_trade_count: 1
"""
    complete_spec = tmp_path / "pair_complete.yaml"
    incomplete_spec = tmp_path / "pair_incomplete.yaml"
    complete_spec.write_text(
        spec_template.format(
            strategy_id="pair_complete_group_v1",
            hedge_execution_symbol="BBB100",
            hedge_real_market_symbol="BBB",
        ),
        encoding="utf-8",
    )
    incomplete_spec.write_text(
        spec_template.format(
            strategy_id="pair_incomplete_group_v1",
            hedge_execution_symbol="CCC100",
            hedge_real_market_symbol="CCC",
        ),
        encoding="utf-8",
    )
    bundle_path = tmp_path / "bundle.yaml"
    bundle_path.write_text(
        f"""schema_version: strategy_authoring_bundle.v1
bundle_id: pair_auto_direction_bundle_v1
members:
  - spec_path: {incomplete_spec.name}
    allocation_weight: 0.5
  - spec_path: {complete_spec.name}
    allocation_weight: 0.5
portfolio:
  selection_metric: multi_leg_group_metrics.incomplete_group_count
  selection_direction: auto
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["strategy-author-bundle-run", "--bundle", str(bundle_path)])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (data_dir / "research/strategy_authoring_bundle_result.json").read_text(encoding="utf-8")
    )
    assert payload["portfolio"]["selection_direction"] == "auto"
    assert payload["portfolio"]["resolved_selection_direction"] == "minimize"
    assert payload["best_member"]["strategy_id"] == "pair_complete_group_v1"
    assert (
        payload["best_member"]["summary"]["multi_leg_group_metrics"]["incomplete_group_count"] == 0
    )
    assert payload["members"][1]["strategy_id"] == "pair_incomplete_group_v1"
    assert (
        payload["members"][1]["summary"]["multi_leg_group_metrics"]["incomplete_group_count"] == 1
    )


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
