from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.adapter_spike import build_backtest_adapter_spike
from sis.cli import app


runner = CliRunner()


def test_build_backtest_adapter_spike_writes_dependency_free_artifacts(tmp_path) -> None:
    result = build_backtest_adapter_spike(
        out_dir=tmp_path / "data/research/backtest_adapter_spike",
        reports_dir=tmp_path / "data/reports",
    )

    payload = json.loads(result.spike_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_adapter_spike.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "strategy_backtest_adapter_spike.v1"
    assert payload["dependency_added"] is False
    assert payload["external_engine_run"] is False
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert {candidate["framework_id"] for candidate in payload["candidates"]} == {
        "vectorbt",
        "bt",
        "backtesting",
        "zipline_reloaded",
        "backtrader",
        "quantstats",
        "empyrical_reloaded",
        "pyfolio_reloaded",
        "qstrader",
        "nautilus_trader",
        "freqtrade",
        "qlib",
        "finrl",
        "hftbacktest",
        "skfolio",
    }
    reference_only = {
        candidate["framework_id"]
        for candidate in payload["candidates"]
        if candidate["candidate_kind"] == "reference_only"
    }
    assert reference_only == {
        "nautilus_trader",
        "freqtrade",
        "qlib",
        "finrl",
        "hftbacktest",
        "skfolio",
    }
    hftbacktest = next(
        candidate
        for candidate in payload["candidates"]
        if candidate["framework_id"] == "hftbacktest"
    )
    assert hftbacktest["adapter_role"] == "reference_only_microstructure_replay"
    assert len(payload["candidates"]) == 15
    assert all(candidate["engine_run"] is False for candidate in payload["candidates"])
    assert all(candidate["dependency_added"] is False for candidate in payload["candidates"])
    assert payload["decision"]["selected_for_dependency_adoption"] is None
    assert result.report_path.exists()


def test_strategy_backtest_adapter_spike_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["strategy-backtest-adapter-spike"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_adapter_spike=" in result.stdout
    assert (
        data_dir / "research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"
    ).exists()
    assert (data_dir / "reports/strategy_backtest_adapter_spike_report.md").exists()
