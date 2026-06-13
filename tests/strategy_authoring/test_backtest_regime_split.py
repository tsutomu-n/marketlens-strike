from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.regime_split import (
    build_strategy_backtest_regime_split,
    parse_regime_dimensions,
)
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "regime_demo",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "executed_count": 3,
                    "executed_signal_results": [
                        {
                            "signal_id": "a",
                            "ts_signal": "2026-01-05T14:00:00+00:00",
                            "side": "long",
                            "timeframe": "4h",
                            "exit_reason": "fixed_horizon",
                            "signal_return": 0.01,
                            "cost_drag_bps": 1.0,
                            "notional_usd": 1000.0,
                        },
                        {
                            "signal_id": "b",
                            "ts_signal": "2026-01-05T18:00:00+00:00",
                            "side": "short",
                            "timeframe": "4h",
                            "exit_reason": "stop_loss",
                            "signal_return": -0.003,
                            "cost_drag_bps": 2.0,
                            "notional_usd": 500.0,
                        },
                        {
                            "signal_id": "c",
                            "ts_signal": "2026-01-06T14:00:00+00:00",
                            "side": "long",
                            "timeframe": "1h",
                            "exit_reason": "fixed_horizon",
                            "signal_return": 0.004,
                            "cost_drag_bps": 1.5,
                            "notional_usd": 750.0,
                        },
                    ],
                    "aggregate_metrics": {
                        "trade_count": 3,
                        "total_return": 0.011,
                        "max_drawdown": -0.003,
                        "cost_drag_bps": 4.5,
                    },
                    "backtest_passed": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_regime_dimensions_rejects_bad_values() -> None:
    assert parse_regime_dimensions("side,ts_hour") == ["side", "ts_hour"]
    with pytest.raises(ValueError, match="duplicate regime split dimension"):
        parse_regime_dimensions("side,side")
    with pytest.raises(ValueError, match="at least one"):
        parse_regime_dimensions(" , ")


def test_build_strategy_backtest_regime_split_writes_schema_valid_artifact(tmp_path) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_regime_split(
        metrics_path=metrics_path,
        dimension_csv="side,ts_weekday,ts_hour",
        out_dir=tmp_path / "data/research/backtest_regime_split",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_regime_split.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_regime_split.v1"
    assert payload["split_kind"] == "regime_dimension"
    assert payload["dimension_count"] == 3
    assert payload["summary"]["return_count"] == 3
    assert payload["summary"]["worst_bucket_id"] == "side:short"
    side = next(item for item in payload["dimensions"] if item["dimension_id"] == "side")
    assert side["bucket_count"] == 2
    short_bucket = next(item for item in side["buckets"] if item["bucket_value"] == "short")
    assert short_bucket["total_return"] == pytest.approx(-0.003)
    assert short_bucket["cost_drag_bps"] == 2.0
    hour = next(item for item in payload["dimensions"] if item["dimension_id"] == "ts_hour")
    assert {item["bucket_value"] for item in hour["buckets"]} == {"14", "18"}
    assert payload["dependency_added"] is False
    assert payload["paper_only"] is True
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert result.regime_split_path.exists()
    assert result.report_path.exists()


def test_strategy_backtest_regime_split_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")

    result = runner.invoke(
        app,
        [
            "strategy-backtest-regime-split",
            "--dimension-csv",
            "side,ts_hour",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_regime_split=" in result.stdout
    assert "backtest_regime_split_report=" in result.stdout
    assert (
        data_dir / "research/backtest_regime_split/strategy_backtest_regime_split.json"
    ).exists()
    assert (data_dir / "reports/strategy_backtest_regime_split_report.md").exists()
