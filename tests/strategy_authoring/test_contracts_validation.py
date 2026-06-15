# ruff: noqa: F403,F405

from .helpers import *  # noqa: F403,F405


def test_strategy_authoring_example_specs_and_bundles_parse() -> None:
    examples_dir = Path("docs/strategy_research_lab/examples")
    spec_paths = sorted(examples_dir.glob("*_authoring_spec.yaml"))
    bundle_paths = sorted(examples_dir.glob("*bundle.yaml"))

    assert spec_paths
    assert bundle_paths
    for spec_path in spec_paths:
        assert load_authoring_spec(spec_path).schema_version == "strategy_authoring_spec.v1"
    for bundle_path in bundle_paths:
        bundle = load_authoring_bundle_spec(bundle_path)
        assert bundle.schema_version == "strategy_authoring_bundle.v1"
        for member in bundle.members:
            assert (bundle_path.parent / member.spec_path).exists()


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
    assert set(frame.get_column("trailing_stop_activation_bps").to_list()) == {0.0}
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


def test_authoring_backtest_capital_and_evaluation_window_contract(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "backtest:\n",
            "backtest:\n"
            "  initial_capital_usd: 100\n"
            "  evaluation_start_at: 2026-01-01T00:00:00+00:00\n"
            "  evaluation_end_at: 2026-01-02T00:00:00+00:00\n",
        ),
        encoding="utf-8",
    )

    spec = load_authoring_spec(spec_path)

    assert spec.backtest.initial_capital_usd == 100
    assert spec.backtest.evaluation_start_at is not None
    assert spec.backtest.evaluation_end_at is not None


@pytest.mark.parametrize("initial_capital_usd", [99.99, 50000.01, "1000", True])
def test_authoring_backtest_rejects_invalid_initial_capital(
    tmp_path, initial_capital_usd
) -> None:
    spec_path = tmp_path / "spec.yaml"
    import yaml

    payload = yaml.safe_load(template_yaml())
    payload["backtest"]["initial_capital_usd"] = initial_capital_usd
    spec_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(Exception):
        load_authoring_spec(spec_path)


def test_authoring_backtest_rejects_invalid_evaluation_window(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "backtest:\n",
            "backtest:\n"
            "  evaluation_start_at: 2026-01-02T00:00:00+00:00\n"
            "  evaluation_end_at: 2026-01-01T00:00:00+00:00\n",
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        load_authoring_spec(spec_path)


def test_authoring_backtest_rejects_naive_evaluation_datetime(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        template_yaml().replace(
            "backtest:\n",
            "backtest:\n"
            "  evaluation_start_at: 2026-01-01T00:00:00\n"
            "  evaluation_end_at: 2026-01-02T00:00:00+00:00\n",
        ),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        load_authoring_spec(spec_path)


def test_authoring_backtest_rejects_unknown_fields(tmp_path) -> None:
    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text(
        template_yaml().replace("backtest:\n", "backtest:\n  unknown_field: true\n"),
        encoding="utf-8",
    )

    with pytest.raises(Exception):
        load_authoring_spec(spec_path)
