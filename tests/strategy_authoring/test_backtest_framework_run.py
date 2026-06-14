from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

from jsonschema import validate
import polars as pl

from sis.backtest import external as external_module
from sis.backtest.framework_run import build_strategy_backtest_framework_run

from .helpers import runner, app


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "aggregate_metrics": {
                        "trade_count": 2,
                        "total_return": 0.03,
                        "max_drawdown": 0.0,
                        "cost_drag_bps": 2.0,
                    },
                    "executed_signal_results": [
                        {
                            "ts_signal": "2026-01-01T00:00:00+00:00",
                            "signal_id": "sig_1",
                            "canonical_symbol": "QQQ",
                            "side": "long",
                            "signal_return": 0.01,
                        },
                        {
                            "ts_signal": "2026-01-02T00:00:00+00:00",
                            "signal_id": "sig_2",
                            "canonical_symbol": "QQQ",
                            "side": "long",
                            "signal_return": 0.02,
                        },
                    ],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_strategy_backtest_framework_run_selects_only_requested_framework(
    tmp_path: Path,
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_framework_run(
        frameworks=["empyrical_reloaded"],
        metrics_path=metrics_path,
        bundle_path=tmp_path / "missing_bundle.json",
        price_frame_path=tmp_path / "missing_prices.parquet",
        signals_path=tmp_path / "missing_signals.parquet",
        quotes_path=tmp_path / "missing_quotes.parquet",
        out_dir=tmp_path / "data/research/backtest_framework_run",
        reports_dir=tmp_path / "data/reports",
    )

    schema = json.loads(
        Path("schemas/strategy_backtest_framework_run.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=result.payload, schema=schema)
    assert result.payload["schema_version"] == "strategy_backtest_framework_run.v1"
    assert result.payload["selected_frameworks"] == ["empyrical_reloaded"]
    assert result.payload["source_metrics_hash"].startswith("sha256:")
    assert result.payload["source_bundle_hash"] is None
    assert result.payload["sources"]["metrics"]["exists"] is True
    assert result.payload["sources"]["metrics"]["sha256"].startswith("sha256:")
    assert result.payload["sources"]["bundle"]["exists"] is False
    assert result.payload["sources"]["bundle"]["sha256"] is None
    assert result.payload["summary"]["framework_count"] == 1
    assert result.payload["runs"][0]["framework_id"] == "empyrical_reloaded"
    assert result.payload["runs"][0]["surface_type"] == "metrics_analytics"
    assert result.payload["runs"][0]["artifact"]["exists"] is True
    assert result.payload["runs"][0]["boundary"]["permits_live_order"] is False
    assert result.payload["runs"][0]["boundary"]["wallet_used"] is False
    assert result.payload["runs"][0]["boundary"]["exchange_write_used"] is False


def test_strategy_backtest_framework_run_cli_supports_metrics_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["strategy-backtest-framework-run", "--framework", "metrics"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_framework_run=" in result.stdout
    payload_path = data_dir / "research/backtest_framework_run/strategy_backtest_framework_run.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["selected_frameworks"] == ["empyrical_reloaded"]
    assert payload["sources"]["metrics"]["sha256"].startswith("sha256:")
    assert payload["runs"][0]["framework_id"] == "empyrical_reloaded"
    assert payload["runs"][0]["surface_type"] == "metrics_analytics"
    assert payload["permits_live_order"] is False


def test_build_strategy_backtest_framework_run_selects_vectorbt_runner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    signals_path = tmp_path / "data/research/strategy_signals.parquet"
    quotes_path = tmp_path / "data/research/quotes.parquet"
    _write_metrics(metrics_path)
    signals_path.parent.mkdir(parents=True, exist_ok=True)
    quotes_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "execution_symbol": "QQQ",
                "side": "long",
            }
        ]
    ).write_parquet(signals_path)
    pl.DataFrame(
        [
            {
                "ts_client": "2026-01-01T00:00:00+00:00",
                "canonical_symbol": "QQQ",
                "mark_price": 100.0,
                "mid_price": 100.0,
            },
            {
                "ts_client": "2026-01-01T04:00:00+00:00",
                "canonical_symbol": "QQQ",
                "mark_price": 102.0,
                "mid_price": 102.0,
            },
        ]
    ).write_parquet(quotes_path)

    class FakePortfolio:
        @classmethod
        def from_signals(cls, close, entries, exits, init_cash, fees):
            return cls()

        def total_return(self):
            return 0.02

        def max_drawdown(self):
            return -0.01

    monkeypatch.setitem(sys.modules, "vectorbt", SimpleNamespace(Portfolio=FakePortfolio))
    monkeypatch.setattr(
        external_module,
        "framework_adapter_status",
        lambda: [
            {
                "framework_id": "vectorbt",
                "adapter_role": "vectorized_research_candidate",
                "status": "installed",
                "version": "1.0.0",
            }
        ],
    )

    result = build_strategy_backtest_framework_run(
        frameworks=["vectorbt"],
        metrics_path=metrics_path,
        bundle_path=tmp_path / "missing_bundle.json",
        price_frame_path=tmp_path / "missing_prices.parquet",
        signals_path=signals_path,
        quotes_path=quotes_path,
        out_dir=tmp_path / "data/research/backtest_framework_run",
        reports_dir=tmp_path / "data/reports",
    )

    assert result.payload["summary"] == {
        "framework_count": 1,
        "executed_count": 1,
        "skipped_count": 0,
        "failed_count": 0,
    }
    assert result.payload["sources"]["signals"]["exists"] is True
    assert result.payload["sources"]["signals"]["sha256"].startswith("sha256:")
    assert result.payload["sources"]["quotes"]["exists"] is True
    assert result.payload["sources"]["quotes"]["sha256"].startswith("sha256:")
    assert result.payload["runs"][0]["framework_id"] == "vectorbt"
    assert result.payload["runs"][0]["surface_type"] == "backtest_engine"
    assert result.payload["runs"][0]["run_status"] == "completed"
    assert result.payload["runs"][0]["dependency_source"] == "optional_extra_available"
    assert result.payload["runs"][0]["boundary"]["engine_run"] is True
    assert result.payload["runs"][0]["boundary"]["dependency_added"] is False
    assert result.payload["runs"][0]["boundary"]["permits_live_order"] is False
