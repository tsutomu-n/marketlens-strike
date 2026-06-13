from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.benchmark_relative import build_strategy_backtest_benchmark_relative
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "benchmark_demo",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "executed_count": 2,
                    "executed_signal_results": [
                        {
                            "signal_id": "a",
                            "ts_signal": "2026-01-05T14:00:00+00:00",
                            "venue": "trade_xyz",
                            "canonical_symbol": "XYZ100",
                            "side": "long",
                            "signal_return": 0.12,
                        },
                        {
                            "signal_id": "b",
                            "ts_signal": "2026-01-05T15:00:00+00:00",
                            "venue": "trade_xyz",
                            "canonical_symbol": "XYZ100",
                            "side": "long",
                            "signal_return": -0.02,
                        },
                    ],
                    "aggregate_metrics": {
                        "trade_count": 2,
                        "total_return": 0.10,
                        "max_drawdown": -0.02,
                        "cost_drag_bps": 0.0,
                    },
                    "backtest_passed": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_quotes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "ts_client": "2026-01-05T14:00:00Z",
                "venue": "trade_xyz",
                "canonical_symbol": "XYZ100",
                "mid_price": 100.0,
            },
            {
                "ts_client": "2026-01-05T15:00:00Z",
                "venue": "trade_xyz",
                "canonical_symbol": "XYZ100",
                "mid_price": 110.0,
            },
            {
                "ts_client": "2026-01-05T16:00:00Z",
                "venue": "trade_xyz",
                "canonical_symbol": "XYZ100",
                "mid_price": 105.0,
            },
        ]
    ).write_parquet(path)


def test_build_strategy_backtest_benchmark_relative_writes_schema_valid_artifact(
    tmp_path,
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    quotes_path = tmp_path / "data/research/quotes.parquet"
    _write_metrics(metrics_path)
    _write_quotes(quotes_path)

    result = build_strategy_backtest_benchmark_relative(
        metrics_path=metrics_path,
        quotes_path=quotes_path,
        horizon_minutes=60,
        out_dir=tmp_path / "data/research/backtest_benchmark_relative",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_benchmark_relative.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_benchmark_relative.v1"
    assert payload["comparison_kind"] == "benchmark_relative_return"
    assert payload["source_quotes_path"] == quotes_path.as_posix()
    assert payload["source_quotes_hash"].startswith("sha256:")
    assert payload["horizon_minutes"] == 60
    assert payload["summary"]["return_count"] == 2
    assert payload["summary"]["paired_return_count"] == 2
    assert payload["summary"]["missing_benchmark_count"] == 0
    assert payload["summary"]["strategy_total_return"] == pytest.approx(0.10)
    assert payload["summary"]["benchmark_total_return"] == pytest.approx(0.05454545454545445)
    assert payload["summary"]["active_total_return"] == pytest.approx(0.04545454545454555)
    assert payload["summary"]["tracking_error"] == pytest.approx(0.0027272727272727284)
    assert payload["comparisons"][0]["benchmark_return"] == pytest.approx(0.10)
    assert payload["comparisons"][0]["active_return"] == pytest.approx(0.02)
    assert payload["comparisons"][0]["benchmark_source"] == "quote_frame"
    assert payload["dependency_added"] is False
    assert payload["paper_only"] is True
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert result.benchmark_relative_path.exists()
    assert result.report_path.exists()


def test_strategy_backtest_benchmark_relative_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")
    _write_quotes(data_dir / "research/quotes.parquet")

    result = runner.invoke(
        app,
        [
            "strategy-backtest-benchmark-relative",
            "--quotes-path",
            str(data_dir / "research/quotes.parquet"),
            "--horizon-minutes",
            "60",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_benchmark_relative=" in result.stdout
    assert "backtest_benchmark_relative_report=" in result.stdout
    assert (
        data_dir / "research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json"
    ).exists()
    assert (data_dir / "reports/strategy_backtest_benchmark_relative_report.md").exists()
