from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.adapter_selection import build_backtest_adapter_selection
from sis.cli import app


runner = CliRunner()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _adapter_spike_payload() -> dict:
    return {
        "schema_version": "strategy_backtest_adapter_spike.v1",
        "created_at": "2026-06-13T00:00:00+00:00",
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "candidates": [
            {"framework_id": "vectorbt", "adoption_blockers": ["not_installed_in_current_env"]},
            {"framework_id": "bt", "adoption_blockers": ["not_installed_in_current_env"]},
            {"framework_id": "quantstats", "adoption_blockers": ["not_installed_in_current_env"]},
            {
                "framework_id": "empyrical_reloaded",
                "adoption_blockers": ["not_installed_in_current_env"],
            },
        ],
        "decision": {"selected_for_dependency_adoption": None},
    }


def _framework_smoke_payload() -> dict:
    return {
        "schema_version": "strategy_backtest_framework_smoke.v1",
        "created_at": "2026-06-13T00:00:00+00:00",
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "runner_mode": "temporary_import_smoke",
        "target_frameworks": ["vectorbt", "bt", "quantstats", "empyrical_reloaded"],
        "results": [
            {
                "framework_id": "vectorbt",
                "import_status": "imported",
            "version": "1.0.0",
            "requires_python": ">=3.10",
            "adoption_classification": "optional_extra_candidate",
            "adoption_blockers": [],
            "license_classifiers": ["License :: Other/Proprietary License"],
            "python_classifiers": ["Programming Language :: Python :: 3.13"],
        },
        {
            "framework_id": "bt",
            "import_status": "imported",
            "version": "1.2.0",
            "requires_python": ">=3.9",
            "adoption_classification": "optional_extra_candidate",
            "adoption_blockers": [],
            "license_classifiers": ["License :: OSI Approved :: MIT License"],
            "python_classifiers": ["Programming Language :: Python :: 3.13"],
        },
        {
            "framework_id": "quantstats",
            "import_status": "imported",
            "version": "0.0.81",
            "requires_python": ">=3.10",
            "adoption_classification": "report_only_candidate",
            "adoption_blockers": [],
            "license_classifiers": ["License :: OSI Approved :: Apache Software License"],
            "python_classifiers": ["Programming Language :: Python :: 3.13"],
        },
        {
            "framework_id": "empyrical_reloaded",
            "import_status": "imported",
            "version": "0.5.12",
            "requires_python": ">=3.9",
            "adoption_classification": "report_only_candidate",
            "adoption_blockers": [],
            "license_classifiers": ["License :: OSI Approved :: Apache Software License"],
            "python_classifiers": ["Programming Language :: Python :: 3.13"],
        },
        ],
        "summary": {"imported_count": 4},
        "decision": {"selected_for_dependency_adoption": None},
    }


def _framework_smoke_payload_with_qstrader() -> dict:
    payload = _framework_smoke_payload()
    payload["target_frameworks"] = [
        "vectorbt",
        "bt",
        "quantstats",
        "empyrical_reloaded",
        "qstrader",
    ]
    payload["results"].append(
        {
            "framework_id": "qstrader",
            "import_status": "imported",
            "version": "0.3.0",
            "requires_python": ">=3.9",
            "adoption_classification": "separate_runner_candidate",
            "adoption_blockers": [],
            "license_classifiers": ["License :: OSI Approved :: MIT License"],
            "python_classifiers": [
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
            ],
        }
    )
    payload["summary"] = {"imported_count": 5}
    return payload


def test_build_backtest_adapter_selection_chooses_phase_c_adapters(tmp_path) -> None:
    adapter_spike_path = tmp_path / "data/research/backtest_adapter_spike/spike.json"
    framework_smoke_path = tmp_path / "data/research/backtest_framework_smoke/smoke.json"
    _write_json(adapter_spike_path, _adapter_spike_payload())
    _write_json(framework_smoke_path, _framework_smoke_payload())

    result = build_backtest_adapter_selection(
        adapter_spike_path=adapter_spike_path,
        framework_smoke_path=framework_smoke_path,
        out_dir=tmp_path / "data/research/backtest_adapter_selection",
        reports_dir=tmp_path / "data/reports",
    )

    payload = json.loads(result.selection_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_adapter_selection.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "strategy_backtest_adapter_selection.v1"
    assert payload["dependency_added"] is False
    assert payload["external_engine_run"] is False
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert [item["framework_id"] for item in payload["selected_adapters"]] == [
        "vectorbt",
        "bt",
        "empyrical_reloaded",
        "quantstats",
    ]
    assert [item["framework_id"] for item in payload["deferred_adapters"]] == [
        "backtesting",
        "zipline_reloaded",
        "backtrader",
        "pyfolio_reloaded",
        "qstrader",
    ]
    assert payload["summary"] == {
        "selected_count": 4,
        "deferred_count": 5,
        "optional_extra_selected_count": 2,
        "report_only_selected_count": 2,
        "separate_runner_selected_count": 0,
    }
    assert payload["decision"]["decision"] == "SELECT_PHASE_C_ADAPTERS"
    assert result.report_path.exists()


def test_build_backtest_adapter_selection_promotes_imported_qstrader_spike(tmp_path) -> None:
    adapter_spike_path = tmp_path / "data/research/backtest_adapter_spike/spike.json"
    framework_smoke_path = tmp_path / "data/research/backtest_framework_smoke/smoke.json"
    _write_json(adapter_spike_path, _adapter_spike_payload())
    _write_json(framework_smoke_path, _framework_smoke_payload_with_qstrader())

    result = build_backtest_adapter_selection(
        adapter_spike_path=adapter_spike_path,
        framework_smoke_path=framework_smoke_path,
        out_dir=tmp_path / "data/research/backtest_adapter_selection",
        reports_dir=tmp_path / "data/reports",
    )

    payload = json.loads(result.selection_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_adapter_selection.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(payload)
    assert [item["framework_id"] for item in payload["selected_adapters"]] == [
        "vectorbt",
        "bt",
        "empyrical_reloaded",
        "quantstats",
        "qstrader",
    ]
    qstrader = payload["selected_adapters"][-1]
    assert qstrader["selection_role"] == "separate_runner_research"
    assert qstrader["import_status"] == "imported"
    assert qstrader["version"] == "0.3.0"
    assert qstrader["dependency_added"] is False
    assert qstrader["engine_run"] is False
    assert qstrader["permits_live_order"] is False
    assert qstrader["rationale_codes"] == [
        "explicit_import_smoke_passed",
        "isolated_runner_contract_before_optional_extra",
        "mit_license_signal_observed",
        "mit_license_signal_required",
        "python_3_13_classifier_missing_but_local_import_passed",
        "schedule_event_driven_role_matches_equity_etf_research",
    ]
    assert "qstrader" not in [item["framework_id"] for item in payload["deferred_adapters"]]
    assert payload["summary"] == {
        "selected_count": 5,
        "deferred_count": 4,
        "optional_extra_selected_count": 2,
        "report_only_selected_count": 2,
        "separate_runner_selected_count": 1,
    }
    assert "qstrader isolated runner contract" in payload["decision"]["recommended_next_step"]


def test_build_backtest_adapter_selection_does_not_promote_qstrader_without_license_signal(
    tmp_path,
) -> None:
    adapter_spike_path = tmp_path / "data/research/backtest_adapter_spike/spike.json"
    framework_smoke_path = tmp_path / "data/research/backtest_framework_smoke/smoke.json"
    smoke_payload = _framework_smoke_payload_with_qstrader()
    smoke_payload["results"][-1]["license_classifiers"] = []
    _write_json(adapter_spike_path, _adapter_spike_payload())
    _write_json(framework_smoke_path, smoke_payload)

    result = build_backtest_adapter_selection(
        adapter_spike_path=adapter_spike_path,
        framework_smoke_path=framework_smoke_path,
        out_dir=tmp_path / "data/research/backtest_adapter_selection",
        reports_dir=tmp_path / "data/reports",
    )

    payload = json.loads(result.selection_path.read_text(encoding="utf-8"))
    assert "qstrader" not in [item["framework_id"] for item in payload["selected_adapters"]]
    assert "qstrader" in [item["framework_id"] for item in payload["deferred_adapters"]]


def test_strategy_backtest_adapter_selection_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_json(
        data_dir / "research/backtest_adapter_spike/strategy_backtest_adapter_spike.json",
        _adapter_spike_payload(),
    )
    _write_json(
        data_dir / "research/backtest_framework_smoke/strategy_backtest_framework_smoke.json",
        _framework_smoke_payload(),
    )

    result = runner.invoke(app, ["strategy-backtest-adapter-selection"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_adapter_selection=" in result.stdout
    payload = json.loads(
        (
            data_dir
            / "research/backtest_adapter_selection/strategy_backtest_adapter_selection.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["summary"]["selected_count"] == 4
    assert (data_dir / "reports/strategy_backtest_adapter_selection_report.md").exists()
