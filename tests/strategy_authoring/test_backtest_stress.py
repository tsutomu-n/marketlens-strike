from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.stress import build_strategy_backtest_stress, parse_stress_scenarios
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "stress_demo",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "executed_count": 3,
                    "executed_signal_results": [
                        {"signal_id": "a", "signal_return": 0.01, "cost_drag_bps": 1.0},
                        {"signal_id": "b", "signal_return": -0.002, "cost_drag_bps": 1.0},
                        {"signal_id": "c", "signal_return": 0.004, "cost_drag_bps": 1.0},
                    ],
                    "aggregate_metrics": {
                        "trade_count": 3,
                        "total_return": 0.012,
                        "max_drawdown": -0.002,
                        "cost_drag_bps": 3.0,
                    },
                    "backtest_passed": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_parse_stress_scenarios_rejects_bad_values() -> None:
    assert [item.scenario_id for item in parse_stress_scenarios("base:0:0,severe:5:20")] == [
        "base",
        "severe",
    ]
    with pytest.raises(ValueError, match="scenario format"):
        parse_stress_scenarios("bad")
    with pytest.raises(ValueError, match="duplicate scenario id"):
        parse_stress_scenarios("base:0:0,base:1:1")
    with pytest.raises(ValueError, match=">= 0"):
        parse_stress_scenarios("bad:-1:0")


def test_build_strategy_backtest_stress_writes_schema_valid_artifact(tmp_path) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_stress(
        metrics_path=metrics_path,
        scenario_csv="base:0:0,severe:5:20",
        out_dir=tmp_path / "data/research/backtest_stress",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_stress.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_stress.v1"
    assert payload["stress_kind"] == "cost_slippage"
    assert payload["scenario_count"] == 2
    assert payload["summary"]["return_count"] == 3
    assert payload["summary"]["base_total_return"] == pytest.approx(0.012)
    assert payload["summary"]["base_cost_drag_bps"] == 3.0
    assert payload["summary"]["worst_scenario_id"] == "severe"
    severe = payload["scenarios"][1]
    assert severe["total_additional_bps_per_trade"] == 25.0
    assert severe["stressed_total_return"] == pytest.approx(0.0045)
    assert severe["delta_total_return"] == pytest.approx(-0.0075)
    assert severe["stressed_cost_drag_bps"] == 78.0
    assert payload["dependency_added"] is False
    assert payload["paper_only"] is True
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert result.stress_path.exists()
    assert result.report_path.exists()


def test_strategy_backtest_stress_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")

    result = runner.invoke(
        app,
        [
            "strategy-backtest-stress",
            "--scenario-csv",
            "base:0:0,severe:5:20",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_stress=" in result.stdout
    assert "backtest_stress_report=" in result.stdout
    assert (data_dir / "research/backtest_stress/strategy_backtest_stress.json").exists()
    assert (data_dir / "reports/strategy_backtest_stress_report.md").exists()
