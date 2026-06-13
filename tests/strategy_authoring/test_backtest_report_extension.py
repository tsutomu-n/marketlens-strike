from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.report_extension import build_strategy_backtest_report_extension
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "report_extension_demo",
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


def test_build_strategy_backtest_report_extension_skips_when_quantstats_missing(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("sis.backtest.report_extension.framework_adapter_status", lambda: [])
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_report_extension(
        metrics_path=metrics_path,
        out_dir=tmp_path / "data/research/backtest_report_extension",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    schema = json.loads(
        Path("schemas/strategy_backtest_report_extension.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validate(instance=payload, schema=schema)
    assert payload["schema_version"] == "strategy_backtest_report_extension.v1"
    assert payload["framework_id"] == "quantstats"
    assert payload["report_status"] == "skipped"
    assert payload["reason_codes"] == ["not_installed_in_current_env"]
    assert payload["runner_mode"] == "not_installed_in_current_env"
    assert payload["engine_run"] is False
    assert payload["dependency_added"] is False
    assert payload["return_count"] == 3
    assert payload["quantstats_html_path"] is None
    assert payload["returns_series_hash"].startswith("sha256:")
    assert result.returns_series_path.exists()
    assert result.quantstats_html_path is None
    assert result.report_path.exists()
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False


def test_build_strategy_backtest_report_extension_runs_quantstats_when_installed(
    tmp_path, monkeypatch
) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)
    calls: list[tuple[str, int]] = []

    class FakeDataFrame:
        shape = (12, 1)

    class FakePandas:
        @staticmethod
        def Series(values, index=None, dtype=None):  # noqa: N802
            calls.append(("series", len(values)))
            return list(values)

        @staticmethod
        def to_datetime(values, **_kwargs):
            return list(values)

    def fake_html(returns, **kwargs):
        calls.append(("html", len(returns)))
        Path(kwargs["output"]).write_text("<html>quantstats</html>\n", encoding="utf-8")

    def fake_metrics(returns, **_kwargs):
        calls.append(("metrics", len(returns)))
        return FakeDataFrame()

    fake_quantstats = SimpleNamespace(reports=SimpleNamespace(html=fake_html, metrics=fake_metrics))
    monkeypatch.setitem(sys.modules, "quantstats", fake_quantstats)
    monkeypatch.setitem(sys.modules, "pandas", FakePandas)
    monkeypatch.setattr(
        "sis.backtest.report_extension.framework_adapter_status",
        lambda: [
            {
                "framework_id": "quantstats",
                "adapter_role": "report_only_candidate",
                "status": "installed",
                "version": "0.0.81",
            }
        ],
    )

    result = build_strategy_backtest_report_extension(
        metrics_path=metrics_path,
        frequency="daily",
        out_dir=tmp_path / "data/research/backtest_report_extension",
        reports_dir=tmp_path / "data/reports",
    )

    payload = result.payload
    assert calls == [("series", 3), ("html", 3), ("metrics", 3)]
    assert payload["framework_version"] == "0.0.81"
    assert payload["runner_mode"] == "temporary_or_optional_import"
    assert payload["report_status"] == "completed"
    assert payload["engine_run"] is True
    assert payload["metrics_table_row_count"] == 12
    assert payload["quantstats_html_hash"].startswith("sha256:")
    assert result.quantstats_html_path is not None
    assert result.quantstats_html_path.exists()


def test_strategy_backtest_report_extension_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    monkeypatch.setattr("sis.backtest.report_extension.framework_adapter_status", lambda: [])
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")

    result = runner.invoke(app, ["strategy-backtest-report-extension"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_report_extension=" in result.stdout
    assert "backtest_report_returns_series=" in result.stdout
    assert (
        data_dir / "research/backtest_report_extension/strategy_backtest_report_extension.json"
    ).exists()
    assert (data_dir / "reports/strategy_backtest_report_extension_report.md").exists()
