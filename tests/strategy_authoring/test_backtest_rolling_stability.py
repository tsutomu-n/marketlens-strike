from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.rolling_stability import (
    build_strategy_backtest_rolling_stability,
    parse_rolling_windows,
)
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "rolling_demo",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "executed_count": 4,
                    "executed_signal_results": [
                        {"signal_id": "a", "signal_return": 0.01},
                        {"signal_id": "b", "signal_return": -0.002},
                        {"signal_id": "c", "signal_return": 0.004},
                        {"signal_id": "d", "signal_return": -0.006},
                    ],
                    "aggregate_metrics": {
                        "trade_count": 4,
                        "total_return": 0.006,
                        "max_drawdown": -0.006,
                        "cost_drag_bps": 0.0,
                    },
                    "backtest_passed": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_rolling_windows_rejects_bad_values() -> None:
    assert parse_rolling_windows("2,3") == [2, 3]
    with pytest.raises(ValueError, match="duplicate rolling window"):
        parse_rolling_windows("2,2")
    with pytest.raises(ValueError, match="must be > 0"):
        parse_rolling_windows("0")
    with pytest.raises(ValueError, match="must be an integer"):
        parse_rolling_windows("abc")
    with pytest.raises(ValueError, match="at least one"):
        parse_rolling_windows(" , ")


def test_build_strategy_backtest_rolling_stability_writes_schema_valid_artifact(
    tmp_path,
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_rolling_stability(
        metrics_path=metrics_path,
        window_csv="2,3",
        out_dir=tmp_path / "data/research/backtest_rolling_stability",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_rolling_stability.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_rolling_stability.v1"
    assert payload["stability_kind"] == "rolling_return_window"
    assert payload["window_count"] == 2
    assert payload["summary"]["return_count"] == 4
    assert payload["summary"]["worst_window_size"] == 3
    assert payload["summary"]["worst_window_start_index"] == 1
    assert payload["summary"]["worst_window_end_index"] == 3
    assert payload["summary"]["worst_window_total_return"] == pytest.approx(-0.004)
    window_2 = next(item for item in payload["windows"] if item["window_size"] == 2)
    assert window_2["window_count"] == 3
    assert window_2["worst_window_start_index"] == 2
    assert window_2["worst_window_total_return"] == pytest.approx(-0.002)
    assert window_2["rolling_windows"][0]["source_row_indices"] == [0, 1]
    assert payload["dependency_added"] is False
    assert payload["paper_only"] is True
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert result.rolling_stability_path.exists()
    assert result.report_path.exists()


def test_strategy_backtest_rolling_stability_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")

    result = runner.invoke(
        app,
        [
            "strategy-backtest-rolling-stability",
            "--window-csv",
            "2,3",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_rolling_stability=" in result.stdout
    assert "backtest_rolling_stability_report=" in result.stdout
    assert (
        data_dir / "research/backtest_rolling_stability/strategy_backtest_rolling_stability.json"
    ).exists()
    assert (data_dir / "reports/strategy_backtest_rolling_stability_report.md").exists()
