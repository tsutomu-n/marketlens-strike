# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


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


def test_authoring_reduce_only_order_reduces_only_opposing_open_position(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "order-reduce-only.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("  side: long\n", "  side: auto\n  side_column: direction\n")
        .replace(
            "exit:\n    stop_loss_bps: 150",
            "exit:\n    exit_on_reduce_signal: true\n    reduce_fraction: 1.0\n    stop_loss_bps: 150",
        )
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  order:\n    reduce_only_column: reduce_only_order\n"
            "  portfolio:\n    max_signals_per_timestamp: 3",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {
            **_feature_rows()[0],
            "ts": start,
            "direction": "long",
            "reduce_only_order": False,
        },
        {
            **_feature_rows()[1],
            "ts": start + timedelta(hours=1),
            "direction": "short",
            "reduce_only_order": True,
        },
        {
            **_feature_rows()[2],
            "ts": start + timedelta(hours=2),
            "direction": "short",
            "reduce_only_order": True,
        },
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "reduce", "none"]
    assert frame.get_column("entry_reduce_only").to_list() == [False, True, False]
    assert frame.get_column("reduce_fraction").to_list() == [None, 1.0, 1.0]
    assert frame.get_column("reason_codes").to_list()[1][-1] == "reduce_only"
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_reduce_only_without_opposing_open"]
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


def test_strategy_authoring_trailing_stop_activation_defers_until_profit_threshold(
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
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "trailing_stop_bps: 120\n    trailing_stop_activation_bps: 0",
            "trailing_stop_bps: 100\n    trailing_stop_activation_bps: 500",
        ),
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
    assert metrics["summary"]["exit_reason_counts"]["fixed_horizon"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("trailing_stop_activation_bps").to_list() == [500.0]


def test_strategy_authoring_trailing_stop_activation_can_use_row_column(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    rows = [
        {**row, "row_trailing_activation_bps": activation}
        for row, activation in zip(_feature_rows()[:2], [500.0, 250.0], strict=True)
    ]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "trailing_stop_activation_bps: 0",
            "trailing_stop_activation_bps: null\n    trailing_stop_activation_bps_column: row_trailing_activation_bps",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("trailing_stop_activation_bps").to_list() == [500.0, 250.0]


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


def test_strategy_authoring_bracket_can_use_row_stop_column_as_exit_control(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "stop_loss_bps: 150", "stop_loss_bps: null\n    stop_loss_bps_column: row_stop_bps"
        )
        .replace("take_profit_bps: 300", "take_profit_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 900")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "row_stop_bps": 150.0} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 97.0),
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
    assert metrics["summary"]["exit_reason_counts"]["bracket_stop_loss"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("stop_loss_bps").to_list() == [150.0]


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


def test_strategy_authoring_bracket_break_even_can_use_row_column(tmp_path, monkeypatch) -> None:
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
            "sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco\n    break_even_after_bps_column: row_break_even_bps",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "row_break_even_bps": 100.0} for row in _feature_rows()[:1]]
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
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("bracket_break_even_after_bps").to_list() == [100.0]


def test_strategy_authoring_bracket_time_stop_can_use_row_column(tmp_path, monkeypatch) -> None:
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
            "sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco\n    time_stop_minutes_column: row_time_stop_minutes",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "row_time_stop_minutes": 60} for row in _feature_rows()[:1]]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 101.0),
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
    assert metrics["summary"]["exit_reason_counts"]["bracket_time_stop"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("bracket_time_stop_minutes").to_list() == [60]


def test_strategy_authoring_bracket_break_even_can_arm_after_partial_take_profit(
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
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: 150")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  bracket:\n"
            "    enabled: true\n"
            "    bracket_type: oco\n"
            "    break_even_after_partial_take_profit: true",
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
    assert (
        metrics["summary"]["exit_reason_counts"]["partial_take_profit+bracket_break_even_stop"] == 1
    )
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("bracket_break_even_after_partial_take_profit").to_list() == [True]


def test_strategy_authoring_bracket_partial_take_profit_break_even_accepts_row_columns(
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
        .replace(
            "partial_take_profit_bps: 200",
            "partial_take_profit_bps: null\n    partial_take_profit_bps_column: row_partial_take_profit_bps",
        )
        .replace(
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: null\n    partial_exit_fraction_column: row_partial_exit_fraction",
        )
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  bracket:\n"
            "    enabled: true\n"
            "    bracket_type: oco\n"
            "    break_even_after_partial_take_profit: true",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            **row,
            "row_partial_take_profit_bps": 150.0,
            "row_partial_exit_fraction": 0.5,
        }
        for row in _feature_rows()[:1]
    ]
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
    assert (
        metrics["summary"]["exit_reason_counts"]["partial_take_profit+bracket_break_even_stop"] == 1
    )
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("partial_take_profit_bps").to_list() == [150.0]
    assert signals.get_column("partial_exit_fraction").to_list() == [0.5]


def test_strategy_authoring_bracket_partial_take_profit_break_even_requires_partial_exit(
    tmp_path,
) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml()
        .replace("partial_take_profit_bps: 200", "partial_take_profit_bps: null")
        .replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  bracket:\n"
            "    enabled: true\n"
            "    bracket_type: oco\n"
            "    break_even_after_partial_take_profit: true",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="break_even_after_partial_take_profit requires"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_bracket_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco\n    time_stop_minutes_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.bracket.time_stop_minutes_column"):
        load_authoring_spec(spec_path)

    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  bracket:\n    enabled: true\n    bracket_type: oco\n    break_even_after_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.bracket.break_even_after_bps_column"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_reward_risk_gate_blocks_low_ratio(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "take_profit_bps: 300",
            "take_profit_bps: 300\n    min_reward_risk_ratio: 2.5",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["none", "none", "none"]
    assert frame.get_column("reward_risk_ratio").to_list() == [2.0, 2.0, 2.0]
    assert frame.get_column("min_reward_risk_ratio").to_list() == [2.5, 2.5, 2.5]
    assert frame.get_column("block_reasons").to_list() == [
        ["reward_risk_ratio_too_low"],
        ["reward_risk_ratio_too_low"],
        ["reward_risk_ratio_too_low"],
    ]


def test_strategy_authoring_reward_risk_gate_can_use_row_threshold_column(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    frame = pl.read_parquet(data_dir / "research/feature_panel.parquet").with_columns(
        pl.Series("required_reward_risk", [1.5, 2.5, 1.0])
    )
    frame.write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "take_profit_bps: 300",
            "take_profit_bps: 300\n    min_reward_risk_ratio_column: required_reward_risk",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "long"]
    assert frame.get_column("reward_risk_ratio").to_list() == [2.0, 2.0, 2.0]
    assert frame.get_column("min_reward_risk_ratio").to_list() == [1.5, 2.5, 1.0]
    assert frame.get_column("block_reasons").to_list() == [
        [],
        ["reward_risk_ratio_too_low"],
        [],
    ]


def test_strategy_authoring_reward_risk_gate_requires_non_negative_ratio(tmp_path) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "take_profit_bps: 300",
            "take_profit_bps: 300\n    min_reward_risk_ratio: -1",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="min_reward_risk_ratio must be >= 0"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_stop_target_width_guard_blocks_bad_widths(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("min_stop_loss_bps: 50", "min_stop_loss_bps: 200")
        .replace("max_take_profit_bps: 1000", "max_take_profit_bps: 250"),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["none", "none", "none"]
    assert frame.get_column("min_stop_loss_bps").to_list() == [200.0, 200.0, 200.0]
    assert frame.get_column("block_reasons").to_list() == [
        ["stop_loss_bps_too_low"],
        ["stop_loss_bps_too_low"],
        ["stop_loss_bps_too_low"],
    ]


def test_strategy_authoring_stop_target_width_guard_can_use_row_columns(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    frame = pl.read_parquet(data_dir / "research/feature_panel.parquet").with_columns(
        pl.Series("row_min_stop_bps", [100.0, 200.0, 100.0]),
        pl.Series("row_max_take_profit_bps", [400.0, 400.0, 250.0]),
    )
    frame.write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml()
        .replace(
            "stop_loss_bps: 150",
            "stop_loss_bps: 150\n    min_stop_loss_bps_column: row_min_stop_bps",
        )
        .replace(
            "take_profit_bps: 300",
            "take_profit_bps: 300\n    max_take_profit_bps_column: row_max_take_profit_bps",
        ),
        encoding="utf-8",
    )

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "none"]
    assert frame.get_column("min_stop_loss_bps").to_list() == [100.0, 200.0, 100.0]
    assert frame.get_column("max_take_profit_bps").to_list() == [400.0, 400.0, 250.0]
    assert frame.get_column("block_reasons").to_list() == [
        [],
        ["stop_loss_bps_too_low"],
        ["take_profit_bps_too_high"],
    ]


def test_strategy_authoring_stop_target_width_guard_columns_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "stop_loss_bps: 150",
            'stop_loss_bps: 150\n    min_stop_loss_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="min_stop_loss_bps_column"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_reward_risk_column_must_be_non_empty(tmp_path) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "take_profit_bps: 300",
            'take_profit_bps: 300\n    min_reward_risk_ratio_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="min_reward_risk_ratio_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_rebalance_min_delta_skips_small_drift(tmp_path, monkeypatch) -> None:
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
            "    rebalance_target_fraction: 1.05\n"
            "    rebalance_min_delta_fraction: 0.10\n"
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
    assert (
        sum(count for reason, count in exit_reasons.items() if "rebalance_band_skip" in reason) == 1
    )
    assert sum(count for reason, count in exit_reasons.items() if "rebalance_signal" in reason) == 0
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0.09 < total_return < 0.11
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("side").to_list() == ["long", "rebalance"]
    assert signals.get_column("rebalance_min_delta_fraction").to_list() == [None, 0.1]


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


def test_strategy_authoring_ioc_limit_entry_does_not_wait_for_later_fill(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n    limit_offset_bps: 100\n    time_in_force: ioc",
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
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("entry_time_in_force").to_list() == ["ioc"]


def test_strategy_authoring_post_only_limit_blocks_marketable_entry(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n    limit_offset_bps: 0\n    post_only: true",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
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
    assert metrics["summary"]["blocked_reason_counts"]["entry_order_post_only_would_cross"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("entry_post_only").to_list() == [True]


def test_strategy_authoring_time_in_force_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n"
            "    limit_offset_bps: 100\n    time_in_force_column: order_tif",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    rows[0]["order_tif"] = "ioc"
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=1), 99.0),
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
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("entry_time_in_force").to_list() == ["ioc"]


def test_strategy_authoring_entry_order_type_can_use_row_columns(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n"
            "    entry_type_column: order_type\n"
            "    limit_offset_bps_column: limit_offset\n"
            "    stop_offset_bps_column: stop_offset",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()
    rows[0]["order_type"] = "market"
    rows[0]["limit_offset"] = None
    rows[0]["stop_offset"] = None
    rows[1]["order_type"] = "limit"
    rows[1]["limit_offset"] = 100.0
    rows[1]["stop_offset"] = None
    rows[2]["order_type"] = "stop_market"
    rows[2]["limit_offset"] = None
    rows[2]["stop_offset"] = 75.0
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")

    signals, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert signals.get_column("entry_order_type").to_list() == ["market", "limit", "stop_market"]
    assert signals.get_column("entry_limit_offset_bps").to_list() == [None, 100.0, None]
    assert signals.get_column("entry_stop_offset_bps").to_list() == [None, None, 75.0]


def test_strategy_authoring_entry_order_type_column_requires_row_offset(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n"
            "    entry_type_column: order_type\n"
            "    limit_offset_bps_column: limit_offset",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    rows[0]["order_type"] = "limit"
    rows[0]["limit_offset"] = None
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")

    with pytest.raises(ValueError, match="row entry_type is limit"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)


def test_strategy_authoring_entry_order_type_column_rejects_unsupported_value(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n"
            "    entry_type_column: order_type\n"
            "    limit_offset_bps: 100",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    rows[0]["order_type"] = "peg"
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")

    with pytest.raises(ValueError, match="Unsupported rules.order.entry_type_column value"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)


def test_strategy_authoring_gtd_timeout_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n"
            "    limit_offset_bps: 100\n    time_in_force: gtd\n"
            "    timeout_minutes_column: order_timeout_minutes",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    rows[0]["order_timeout_minutes"] = 60
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
            _quote(start + timedelta(hours=2), 99.0),
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
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("entry_time_in_force").to_list() == ["gtd"]
    assert signals.get_column("entry_timeout_minutes").to_list() == [60]


def test_strategy_authoring_post_only_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n"
            "    limit_offset_bps: 0\n    post_only_column: order_post_only",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    rows[0]["order_post_only"] = True
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
    pl.DataFrame(
        [
            _quote(start, 100.0),
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
    assert metrics["summary"]["blocked_reason_counts"]["entry_order_post_only_would_cross"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("entry_post_only").to_list() == [True]


def test_strategy_authoring_post_only_column_rejects_unsupported_boolean(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  order:\n    entry_type: limit\n"
            "    limit_offset_bps: 0\n    post_only_column: order_post_only",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    rows[0]["order_post_only"] = "maybe"
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec = load_authoring_spec(spec_path)

    with pytest.raises(ValueError, match="Unsupported boolean value in order_post_only"):
        build_authoring_signals(spec, data_dir=data_dir)


@pytest.mark.parametrize(
    ("field_name", "expected_error"),
    [
        ("entry_type_column", "rules.order.entry_type_column"),
        ("limit_offset_bps_column", "rules.order.limit_offset_bps_column"),
        ("stop_offset_bps_column", "rules.order.stop_offset_bps_column"),
        ("timeout_minutes_column", "rules.order.timeout_minutes_column"),
        ("time_in_force_column", "rules.order.time_in_force_column"),
        ("post_only_column", "rules.order.post_only_column"),
    ],
)
def test_strategy_authoring_order_columns_must_be_non_empty(
    tmp_path, field_name: str, expected_error: str
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            f'sizing:\n    position_weight: 1.0\n  order:\n    {field_name}: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=expected_error):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_slippage_can_use_row_column(tmp_path, monkeypatch) -> None:
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
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  execution:\n"
            "    slippage_bps_column: expected_slippage_bps",
        ),
        encoding="utf-8",
    )
    rows = [{**_feature_rows()[0], "expected_slippage_bps": 75.0}]
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
    assert metrics["summary"]["aggregate_metrics"]["cost_drag_bps"] == 76.0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("slippage_bps").to_list() == [75.0]


def test_strategy_authoring_slippage_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    slippage_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.slippage_bps_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_max_spread_bps_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  execution:\n"
            "    max_spread_bps_column: max_allowed_spread_bps",
        ),
        encoding="utf-8",
    )
    rows = [{**_feature_rows()[0], "max_allowed_spread_bps": 5.0}]
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
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_spread_bps").to_list() == [5.0]


def test_strategy_authoring_max_spread_bps_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_spread_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_spread_bps_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_min_depth_usd_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0\n    notional_usd: 1000",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "    notional_usd: 1000\n"
            "  execution:\n"
            "    min_depth_usd_column: required_depth_usd\n"
            "    depth_column: min_side_depth_10bps_usd",
        ),
        encoding="utf-8",
    )
    rows = [{**_feature_rows()[0], "required_depth_usd": 1_000.0}]
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
    assert metrics["summary"]["blocked_reason_counts"]["microstructure_depth_too_low"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_depth_usd").to_list() == [1_000.0]


def test_strategy_authoring_min_depth_usd_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    min_depth_usd_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.min_depth_usd_column"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_min_fill_fraction_blocks_small_effective_fill(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_fill_fraction: 0.4\n    min_fill_fraction: 0.5",
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
    assert metrics["summary"]["blocked_reason_counts"]["execution_fill_fraction_too_low"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_fill_fraction").to_list() == [0.4]
    assert signals.get_column("min_fill_fraction").to_list() == [0.5]


def test_strategy_authoring_max_fill_fraction_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  execution:\n"
            "    max_fill_fraction_column: expected_fill_fraction",
        ),
        encoding="utf-8",
    )
    rows = [{**_feature_rows()[0], "expected_fill_fraction": 0.4}]
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
    assert 0 < total_return < 0.02
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_fill_fraction").to_list() == [0.4]


def test_strategy_authoring_min_fill_fraction_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  execution:\n"
            "    max_fill_fraction: 0.4\n"
            "    min_fill_fraction_column: required_fill_fraction",
        ),
        encoding="utf-8",
    )
    rows = [{**_feature_rows()[0], "required_fill_fraction": 0.5}]
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
    assert metrics["summary"]["blocked_reason_counts"]["execution_fill_fraction_too_low"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("min_fill_fraction").to_list() == [0.5]


def test_strategy_authoring_max_fill_fraction_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_fill_fraction_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_fill_fraction_column"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_min_fill_fraction_must_be_unit_interval(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_fill_fraction: 1.5",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.min_fill_fraction"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_min_fill_fraction_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    min_fill_fraction_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.min_fill_fraction_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_max_latency_ms_can_use_row_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n"
            "    position_weight: 1.0\n"
            "  execution:\n"
            "    max_latency_ms_column: allowed_latency_ms\n"
            "    latency_column: observed_latency_ms",
        ),
        encoding="utf-8",
    )
    rows = [
        {**row, "allowed_latency_ms": 100.0, "observed_latency_ms": 250.0}
        for row in _feature_rows()[:1]
    ]
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


def test_strategy_authoring_max_latency_ms_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_latency_ms_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_latency_ms_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_queue_position_score_can_use_row_threshold_column(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_queue_position_score_column: required_queue_score\n    queue_position_score_column: queue_score",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            **row,
            "required_queue_score": 0.7,
            "queue_score": 0.4,
        }
        for row in _feature_rows()[:1]
    ]
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
    assert signals.get_column("min_queue_position_score").to_list() == [0.7]
    assert signals.get_column("queue_position_score").to_list() == [0.4]


def test_strategy_authoring_queue_position_score_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    min_queue_position_score_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.min_queue_position_score_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_short_borrow_availability_can_use_row_threshold_column(
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
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_borrow_availability_ratio_column: required_borrow_available\n    borrow_availability_column: borrow_available",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            **row,
            "required_borrow_available": 0.8,
            "borrow_available": 0.4,
        }
        for row in _feature_rows()[:1]
    ]
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
    assert signals.get_column("min_borrow_availability_ratio").to_list() == [0.8]
    assert signals.get_column("borrow_availability_ratio").to_list() == [0.4]


def test_strategy_authoring_short_borrow_availability_column_must_be_non_empty(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("side: long", "side: short")
        .replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    min_borrow_availability_ratio_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.min_borrow_availability_ratio_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_short_borrow_cost_can_use_row_threshold_column(
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
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_borrow_cost_bps_column: allowed_borrow_cost\n    borrow_cost_column: borrow_cost",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            **row,
            "allowed_borrow_cost": 30.0,
            "borrow_cost": 75.0,
        }
        for row in _feature_rows()[:1]
    ]
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
    assert signals.get_column("max_borrow_cost_bps").to_list() == [30.0]
    assert signals.get_column("borrow_cost_bps").to_list() == [75.0]


def test_strategy_authoring_short_borrow_cost_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("side: long", "side: short")
        .replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_borrow_cost_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_borrow_cost_bps_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_tax_drag_can_use_row_threshold_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_tax_drag_bps_column: allowed_tax_drag\n    tax_drag_column: tax_drag",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            **row,
            "allowed_tax_drag": 15.0,
            "tax_drag": 40.0,
        }
        for row in _feature_rows()[:1]
    ]
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
    assert signals.get_column("max_tax_drag_bps").to_list() == [15.0]
    assert signals.get_column("tax_drag_bps").to_list() == [40.0]


def test_strategy_authoring_tax_drag_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_tax_drag_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_tax_drag_bps_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_turnover_pressure_can_use_row_threshold_column(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_turnover_pressure_column: allowed_turnover_pressure\n    turnover_pressure_column: turnover_pressure",
        ),
        encoding="utf-8",
    )
    rows = [
        {
            **row,
            "allowed_turnover_pressure": 0.3,
            "turnover_pressure": 0.8,
        }
        for row in _feature_rows()[:1]
    ]
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
    assert signals.get_column("max_turnover_pressure").to_list() == [0.3]
    assert signals.get_column("turnover_pressure").to_list() == [0.8]


def test_strategy_authoring_turnover_pressure_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_turnover_pressure_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_turnover_pressure_column"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_capacity_usage_filter_blocks_trade(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_capacity_usage_ratio: 0.6\n    capacity_usage_column: capacity_usage",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "capacity_usage": 0.85} for row in _feature_rows()[:1]]
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
    assert metrics["summary"]["blocked_reason_counts"]["capacity_usage_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_capacity_usage_ratio").to_list() == [0.6]
    assert signals.get_column("capacity_usage_ratio").to_list() == [0.85]


def test_strategy_authoring_capacity_usage_can_use_row_threshold_column(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_capacity_usage_ratio_column: allowed_capacity_usage\n    capacity_usage_column: capacity_usage",
        ),
        encoding="utf-8",
    )
    rows = [
        {**row, "allowed_capacity_usage": 0.5, "capacity_usage": 0.85}
        for row in _feature_rows()[:1]
    ]
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
    assert metrics["summary"]["blocked_reason_counts"]["capacity_usage_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_capacity_usage_ratio").to_list() == [0.5]
    assert signals.get_column("capacity_usage_ratio").to_list() == [0.85]


def test_strategy_authoring_capacity_usage_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_capacity_usage_ratio_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_capacity_usage_ratio_column"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_correlation_crowding_filter_blocks_trade(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_correlation_crowding_score: 0.7\n    correlation_crowding_column: crowding",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "crowding": 0.95} for row in _feature_rows()[:1]]
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
    assert metrics["summary"]["blocked_reason_counts"]["correlation_crowding_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_correlation_crowding_score").to_list() == [0.7]
    assert signals.get_column("correlation_crowding_score").to_list() == [0.95]


def test_strategy_authoring_correlation_crowding_can_use_row_threshold_column(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    max_correlation_crowding_score_column: allowed_crowding\n    correlation_crowding_column: crowding",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "allowed_crowding": 0.6, "crowding": 0.95} for row in _feature_rows()[:1]]
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
    assert metrics["summary"]["blocked_reason_counts"]["correlation_crowding_too_high"] == 1
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] == 0
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_correlation_crowding_score").to_list() == [0.6]
    assert signals.get_column("correlation_crowding_score").to_list() == [0.95]


def test_strategy_authoring_correlation_crowding_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    max_correlation_crowding_score_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.max_correlation_crowding_score_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_fee_edge_can_use_row_threshold_column(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            "sizing:\n    position_weight: 1.0\n  execution:\n    min_fee_edge_bps_column: required_fee_edge\n    fee_edge_column: fee_edge",
        ),
        encoding="utf-8",
    )
    rows = [{**row, "required_fee_edge": 2.0, "fee_edge": -1.0} for row in _feature_rows()[:1]]
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
    assert signals.get_column("min_fee_edge_bps").to_list() == [2.0]
    assert signals.get_column("fee_edge_bps").to_list() == [-1.0]


def test_strategy_authoring_fee_edge_column_must_be_non_empty(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "sizing:\n    position_weight: 1.0",
            'sizing:\n    position_weight: 1.0\n  execution:\n    min_fee_edge_bps_column: ""',
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="rules.execution.min_fee_edge_bps_column"):
        load_authoring_spec(spec_path)


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


def test_strategy_authoring_max_holding_minutes_caps_fixed_horizon(tmp_path, monkeypatch) -> None:
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
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n    max_holding_minutes: 60",
        ),
        encoding="utf-8",
    )
    rows = _feature_rows()[:1]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
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
    assert metrics["summary"]["exit_reason_counts"]["max_holding_time"] == 1
    total_return = metrics["summary"]["aggregate_metrics"]["total_return"]
    assert 0.008 < total_return < 0.01
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_holding_minutes").to_list() == [60]


def test_strategy_authoring_max_holding_minutes_can_use_row_column(tmp_path, monkeypatch) -> None:
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
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n    max_holding_minutes_column: row_max_hold_minutes",
        ),
        encoding="utf-8",
    )
    rows = [{**_feature_rows()[0], "row_max_hold_minutes": 60}]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    start = rows[0]["ts"]
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
    assert metrics["summary"]["exit_reason_counts"]["max_holding_time"] == 1
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("max_holding_minutes").to_list() == [60]


def test_strategy_authoring_max_holding_minutes_must_not_be_shorter_than_min(
    tmp_path,
) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n    min_holding_minutes: 120\n    max_holding_minutes: 60",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_holding_minutes must be >= min_holding_minutes"):
        load_authoring_spec(spec_path)


def test_strategy_authoring_holding_minutes_columns_validate_row_order(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    _write_data(data_dir)
    rows = [{**_feature_rows()[0], "row_min_hold_minutes": 120, "row_max_hold_minutes": 60}]
    pl.DataFrame(rows).write_parquet(data_dir / "research/feature_panel.parquet")
    spec_path.write_text(
        template_yaml().replace(
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n"
            "    min_holding_minutes_column: row_min_hold_minutes\n"
            "    max_holding_minutes_column: row_max_hold_minutes",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_holding_minutes must be >= min_holding_minutes"):
        build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)


def test_strategy_authoring_exit_priority_can_take_profit_before_partial(
    tmp_path, monkeypatch
) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "authoring.yaml"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("stop_loss_bps: 150", "stop_loss_bps: 900")
        .replace("trailing_stop_bps: 120", "trailing_stop_bps: 900")
        .replace(
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n"
            "    exit_priority:\n"
            "      - take_profit\n"
            "      - partial_take_profit\n"
            "      - stop_loss\n"
            "      - trailing_stop\n"
            "      - break_even_stop\n"
            "      - time_stop",
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
    assert metrics["summary"]["exit_reason_counts"]["take_profit"] == 1
    assert "partial_take_profit" not in metrics["summary"]["exit_reason_counts"]
    signals = pl.read_parquet(data_dir / "research/strategy_signals.parquet")
    assert signals.get_column("exit_priority").to_list() == [
        "take_profit,partial_take_profit,stop_loss,trailing_stop,break_even_stop,time_stop"
    ]


def test_strategy_authoring_exit_priority_rejects_duplicates(tmp_path) -> None:
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "partial_exit_fraction: 0.5",
            "partial_exit_fraction: 0.5\n"
            "    exit_priority:\n"
            "      - take_profit\n"
            "      - take_profit",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exit_priority must not contain duplicates"):
        load_authoring_spec(spec_path)
