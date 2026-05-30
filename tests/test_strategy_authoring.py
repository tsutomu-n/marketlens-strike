from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from jsonschema import validate
import polars as pl
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.research.strategy_lab.authoring import (
    StrategyAuthoringValidationError,
    build_authoring_signals,
    load_authoring_bundle_spec,
    load_authoring_spec,
    strategy_signals_to_research_signals,
    template_yaml,
    validate_authoring_inputs,
    write_authoring_signal_artifacts,
)

runner = CliRunner()


def _write_spec(path: Path) -> None:
    path.write_text(template_yaml(), encoding="utf-8")


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


def test_authoring_position_rules_close_marker_releases_open_state(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-close.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace(
            "  entry:\n    all:",
            "  close:\n    all:\n      - column: close_signal\n        op: is_true\n"
            "  entry:\n    none:\n      - column: close_signal\n        op: is_true\n    all:",
        )
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    max_open_signals_per_symbol: 1\n"
            "    holding_horizon_minutes: 480",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start, "close_signal": False},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1), "close_signal": True},
        {**_feature_rows()[2], "ts": start + timedelta(hours=2), "close_signal": False},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "close", "long"]
    assert frame.filter(pl.col("side") == "none").is_empty()


def test_authoring_position_rules_can_require_open_position_for_markers(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-require-marker.yaml"
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
        )
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    require_open_position_for_markers: true",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start, "reduce_signal": True},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1), "reduce_signal": False},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["none", "long"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_marker_without_open"]
    ]


def test_authoring_position_rules_can_block_opposing_open_positions(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-no-opposing.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml()
        .replace("  side: long\n", "  side: auto\n  side_column: direction\n")
        .replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    allow_opposing_open_positions: false",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start, "direction": "long"},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1), "direction": "short"},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_opposing_open_position"]
    ]


def test_authoring_position_rules_can_block_same_side_pyramiding(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "position-no-pyramiding.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  portfolio:\n    max_signals_per_timestamp: 3",
            "  portfolio:\n    max_signals_per_timestamp: 3\n"
            "  position:\n"
            "    allow_pyramiding: false",
        ),
        encoding="utf-8",
    )
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    feature_rows = [
        {**_feature_rows()[0], "ts": start},
        {**_feature_rows()[1], "ts": start + timedelta(hours=1)},
        {**_feature_rows()[2], "ts": start + timedelta(hours=2)},
    ]
    pl.DataFrame(feature_rows).write_parquet(data_dir / "research/feature_panel.parquet")

    frame, _manifest = build_authoring_signals(load_authoring_spec(spec_path), data_dir=data_dir)

    assert frame.get_column("side").to_list() == ["long", "none", "none"]
    assert frame.filter(pl.col("side") == "none").get_column("block_reasons").to_list() == [
        ["position_pyramiding_not_allowed"],
        ["position_pyramiding_not_allowed"],
    ]


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
