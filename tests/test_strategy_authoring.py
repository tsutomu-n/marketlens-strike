from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import polars as pl
from typer.testing import CliRunner

from sis.cli import app
from sis.research.strategy_lab.authoring import (
    build_authoring_signals,
    load_authoring_spec,
    strategy_signals_to_research_signals,
    template_yaml,
    validate_authoring_inputs,
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
    assert metrics["summary"]["aggregate_metrics"]["trade_count"] > 0
    assert metrics["summary"]["pass_thresholds"]["max_drawdown"]["passed"] is True
    assert metrics["summary"]["backtest_passed"] is True


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
    preview = json.loads((data_dir / "bot/paper_intent_preview.json").read_text(encoding="utf-8"))
    assert preview == []
    decision = json.loads(
        (data_dir / "research/promotion_decision.json").read_text(encoding="utf-8")
    )
    assert decision["decision"] == "hold"


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
