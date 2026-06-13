from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import polars as pl
from typer.testing import CliRunner

from sis.backtest import external as external_module
from sis.backtest.external import build_strategy_backtest_external_result
from sis.cli import app

from .test_backtest_compare import _write_metrics


runner = CliRunner()


def test_build_strategy_backtest_external_result_skips_missing_frameworks(tmp_path) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    out_dir = tmp_path / "data/research/backtest_external"
    reports_dir = tmp_path / "data/reports"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_external_result(
        metrics_path=metrics_path,
        out_dir=out_dir,
        reports_dir=reports_dir,
    )

    payload = json.loads(result.external_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_external_result.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "strategy_backtest_external_result.v1"
    assert payload["source_metrics_path"] == metrics_path.as_posix()
    assert payload["source_signals_path"] is None
    assert payload["source_signals_hash"] is None
    assert payload["source_quotes_path"] is None
    assert payload["source_quotes_hash"] is None
    assert payload["label_horizon_minutes"] == 240
    assert payload["dependency_added"] is False
    assert payload["external_engine_run"] is False
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert {item["framework_id"] for item in payload["results"]} == {
        "vectorbt",
        "backtesting",
        "backtrader",
        "zipline_reloaded",
    }
    assert all(item["run_status"] == "skipped" for item in payload["results"])
    assert all(
        "not_installed_in_current_env" in item["reason_codes"] for item in payload["results"]
    )
    assert all(item["engine_run"] is False for item in payload["results"])
    assert result.report_path.exists()


def test_strategy_backtest_external_run_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")

    result = runner.invoke(app, ["strategy-backtest-external-run"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_external_result=" in result.stdout
    payload = json.loads(
        (data_dir / "research/backtest_external/strategy_backtest_external_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["external_engine_run"] is False
    assert (data_dir / "reports/strategy_backtest_external_report.md").exists()


def test_build_strategy_backtest_external_result_runs_vectorbt_when_installed(
    tmp_path, monkeypatch
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    signals_path = tmp_path / "data/research/strategy_signals.parquet"
    quotes_path = tmp_path / "data/research/quotes.parquet"
    out_dir = tmp_path / "data/research/backtest_external"
    reports_dir = tmp_path / "data/reports"
    _write_metrics(metrics_path)
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    quotes_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "execution_symbol": "XYZ100",
                "side": "long",
            }
        ]
    ).write_parquet(signals_path)
    pl.DataFrame(
        [
            {
                "ts_client": "2026-01-01T00:00:00+00:00",
                "canonical_symbol": "XYZ100",
                "mark_price": 100.0,
                "mid_price": 100.0,
            },
            {
                "ts_client": "2026-01-01T04:00:00+00:00",
                "canonical_symbol": "XYZ100",
                "mark_price": 105.0,
                "mid_price": 105.0,
            },
        ]
    ).write_parquet(quotes_path)

    calls: list[dict[str, object]] = []

    class FakePortfolio:
        @classmethod
        def from_signals(cls, close, entries, exits, init_cash, fees):
            calls.append(
                {
                    "close": close,
                    "entries": entries,
                    "exits": exits,
                    "init_cash": init_cash,
                    "fees": fees,
                }
            )
            return cls()

        def total_return(self):
            return 0.05

        def max_drawdown(self):
            return -0.01

    fake_vectorbt = SimpleNamespace(Portfolio=FakePortfolio)
    monkeypatch.setitem(sys.modules, "vectorbt", fake_vectorbt)
    monkeypatch.setattr(
        external_module,
        "framework_adapter_status",
        lambda: [
            {
                "framework_id": "vectorbt",
                "adapter_role": "vectorized_research_candidate",
                "status": "installed",
            }
        ],
    )

    result = build_strategy_backtest_external_result(
        metrics_path=metrics_path,
        signals_path=signals_path,
        quotes_path=quotes_path,
        label_horizon_minutes=240,
        out_dir=out_dir,
        reports_dir=reports_dir,
    )

    payload = json.loads(result.external_path.read_text(encoding="utf-8"))
    assert calls
    assert payload["external_engine_run"] is True
    assert payload["source_signals_path"] == signals_path.as_posix()
    assert payload["source_signals_hash"].startswith("sha256:")
    assert payload["source_quotes_path"] == quotes_path.as_posix()
    assert payload["source_quotes_hash"].startswith("sha256:")
    assert payload["label_horizon_minutes"] == 240
    assert payload["results"] == [
        {
            "framework_id": "vectorbt",
            "adapter_role": "vectorized_research_candidate",
            "status": "installed",
            "run_status": "completed",
            "reason_codes": [],
            "dependency_added": False,
            "engine_run": True,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "metrics": {
                "trade_count": 1,
                "total_return": 0.05,
                "max_drawdown": -0.01,
                "cost_drag_bps": 0.0,
                "stale_rejected_count": None,
                "halt_rejected_count": None,
            },
        }
    ]
