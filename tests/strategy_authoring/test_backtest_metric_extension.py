from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.metric_extension import build_strategy_backtest_metric_extension
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "metric_extension_demo",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "executed_count": 3,
                    "executed_signal_results": [
                        {
                            "signal_id": "a",
                            "ts_signal": "2026-01-01T00:00:00+00:00",
                            "canonical_symbol": "XYZ100",
                            "side": "long",
                            "signal_return": 0.01,
                        },
                        {
                            "signal_id": "b",
                            "ts_signal": "2026-01-02T00:00:00+00:00",
                            "canonical_symbol": "XYZ100",
                            "side": "long",
                            "signal_return": -0.005,
                        },
                        {
                            "signal_id": "c",
                            "ts_signal": "2026-01-03T00:00:00+00:00",
                            "canonical_symbol": "XYZ100",
                            "side": "long",
                            "signal_return": 0.02,
                        },
                    ],
                    "aggregate_metrics": {
                        "trade_count": 3,
                        "total_return": 0.025,
                        "max_drawdown": -0.005,
                        "cost_drag_bps": 3.0,
                    },
                    "backtest_passed": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_build_strategy_backtest_metric_extension_skips_when_empyrical_missing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("sis.backtest.metric_extension.framework_adapter_status", lambda: [])
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_metric_extension(
        metrics_path=metrics_path,
        out_dir=tmp_path / "data/research/backtest_metric_extension",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_metric_extension.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_metric_extension.v1"
    assert payload["framework_id"] == "empyrical_reloaded"
    assert payload["metric_status"] == "skipped"
    assert payload["reason_codes"] == ["not_installed_in_current_env"]
    assert payload["runner_mode"] == "not_installed_in_current_env"
    assert payload["engine_run"] is False
    assert payload["dependency_added"] is False
    assert payload["return_count"] == 3
    assert payload["returns_series_hash"].startswith("sha256:")
    assert result.returns_series_path.exists()
    assert result.report_path.exists()
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False


def test_build_strategy_backtest_metric_extension_runs_empyrical_when_installed(
    tmp_path, monkeypatch
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)
    calls: list[tuple[str, list[float]]] = []

    def fake_metric(name: str, value: float):
        def _inner(returns, **_kwargs):
            calls.append((name, list(returns)))
            return value

        return _inner

    fake_empyrical = SimpleNamespace(
        sharpe_ratio=fake_metric("sharpe_ratio", 1.2),
        sortino_ratio=fake_metric("sortino_ratio", 1.4),
        max_drawdown=fake_metric("max_drawdown", -0.005),
        annual_return=fake_metric("annual_return", 0.8),
        annual_volatility=fake_metric("annual_volatility", 0.2),
        calmar_ratio=fake_metric("calmar_ratio", 4.0),
        omega_ratio=fake_metric("omega_ratio", 1.1),
    )
    monkeypatch.setitem(sys.modules, "empyrical", fake_empyrical)
    monkeypatch.setattr(
        "sis.backtest.metric_extension.framework_adapter_status",
        lambda: [
            {
                "framework_id": "empyrical_reloaded",
                "adapter_role": "metrics_only_candidate",
                "status": "installed",
                "version": "0.5.12",
            }
        ],
    )

    result = build_strategy_backtest_metric_extension(
        metrics_path=metrics_path,
        frequency="daily",
        out_dir=tmp_path / "data/research/backtest_metric_extension",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    assert calls
    assert payload["framework_version"] == "0.5.12"
    assert payload["runner_mode"] == "temporary_or_optional_import"
    assert payload["metric_status"] == "completed"
    assert payload["engine_run"] is True
    assert payload["sharpe_ratio"] == 1.2
    assert payload["sortino_ratio"] == 1.4
    assert payload["max_drawdown"] == -0.005
    assert payload["annual_return"] == 0.8
    assert payload["annual_volatility"] == 0.2
    assert payload["calmar_ratio"] == 4.0
    assert payload["omega_ratio"] == 1.1


def test_strategy_backtest_metric_extension_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    monkeypatch.setattr("sis.backtest.metric_extension.framework_adapter_status", lambda: [])
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")

    result = runner.invoke(app, ["strategy-backtest-metric-extension"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_metric_extension=" in result.stdout
    assert "backtest_returns_series=" in result.stdout
    assert (
        data_dir / "research/backtest_metric_extension/strategy_backtest_metric_extension.json"
    ).exists()
    assert (data_dir / "reports/strategy_backtest_metric_extension_report.md").exists()
