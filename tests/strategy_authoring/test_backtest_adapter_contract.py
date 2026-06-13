from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.adapter_contract import build_backtest_adapter_contract
from sis.cli import app


runner = CliRunner()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _selection_payload() -> dict:
    return {
        "schema_version": "strategy_backtest_adapter_selection.v1",
        "created_at": "2026-06-13T00:00:00+00:00",
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "selected_adapters": [
            {
                "framework_id": "vectorbt",
                "selection_role": "high_speed_signal_runner",
                "adoption_classification": "optional_extra_candidate",
            },
            {
                "framework_id": "bt",
                "selection_role": "portfolio_allocation_rebalance",
                "adoption_classification": "optional_extra_candidate",
            },
            {
                "framework_id": "empyrical_reloaded",
                "selection_role": "metrics_normalization",
                "adoption_classification": "report_only_candidate",
            },
            {
                "framework_id": "quantstats",
                "selection_role": "report_tearsheet",
                "adoption_classification": "report_only_candidate",
            },
        ],
        "deferred_adapters": [],
    }


def test_build_backtest_adapter_contract_writes_selected_contracts(tmp_path) -> None:
    selection_path = tmp_path / "data/research/backtest_adapter_selection/selection.json"
    _write_json(selection_path, _selection_payload())

    result = build_backtest_adapter_contract(
        adapter_selection_path=selection_path,
        out_dir=tmp_path / "data/research/backtest_adapter_contract",
        reports_dir=tmp_path / "data/reports",
    )

    payload = json.loads(result.contract_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_adapter_contract.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "strategy_backtest_adapter_contract.v1"
    assert payload["dependency_added"] is False
    assert payload["external_engine_run"] is False
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert [item["framework_id"] for item in payload["contracts"]] == [
        "vectorbt",
        "bt",
        "empyrical_reloaded",
        "quantstats",
    ]
    assert payload["summary"] == {
        "contract_count": 4,
        "optional_extra_contract_count": 2,
        "report_only_contract_count": 2,
    }
    assert payload["decision"]["decision"] == "DESIGN_ADAPTER_CONTRACTS_BEFORE_DEPENDENCY"
    vectorbt = payload["contracts"][0]
    assert "source_signals_hash" in vectorbt["provenance_requirements"]
    assert "external_result_schema_validation" in vectorbt["acceptance_checks"]
    assert result.report_path.exists()


def test_strategy_backtest_adapter_contract_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_json(
        data_dir / "research/backtest_adapter_selection/strategy_backtest_adapter_selection.json",
        _selection_payload(),
    )

    result = runner.invoke(app, ["strategy-backtest-adapter-contract"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_adapter_contract=" in result.stdout
    payload = json.loads(
        (
            data_dir / "research/backtest_adapter_contract/strategy_backtest_adapter_contract.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["summary"]["contract_count"] == 4
    assert (data_dir / "reports/strategy_backtest_adapter_contract_report.md").exists()
