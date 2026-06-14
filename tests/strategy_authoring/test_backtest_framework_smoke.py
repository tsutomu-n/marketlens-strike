from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest import framework_smoke
from sis.backtest.framework_smoke import build_backtest_framework_smoke
from sis.cli import app


runner = CliRunner()


class _FakeMetadata:
    def __init__(self, *, license_text: str, requires_python: str) -> None:
        self._license_text = license_text
        self._requires_python = requires_python

    def get(self, key: str) -> str | None:
        if key == "License":
            return self._license_text
        if key == "Requires-Python":
            return self._requires_python
        return None

    def get_all(self, key: str) -> list[str]:
        if key == "Classifier":
            return [
                "License :: OSI Approved :: Apache Software License",
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.13",
            ]
        return []


def test_build_backtest_framework_smoke_records_tier1_metadata(tmp_path, monkeypatch) -> None:
    imported_modules: list[str] = []

    def fake_import_module(module: str) -> object:
        imported_modules.append(module)
        return object()

    def fake_version(distribution: str) -> str:
        return {
            "vectorbt": "1.0.0",
            "bt": "1.1.1",
            "quantstats": "0.0.77",
            "empyrical-reloaded": "0.5.12",
        }[distribution]

    def fake_metadata(distribution: str) -> _FakeMetadata:
        return _FakeMetadata(license_text="Apache-2.0", requires_python=">=3.10")

    monkeypatch.setattr(framework_smoke.importlib, "import_module", fake_import_module)
    monkeypatch.setattr(framework_smoke.metadata, "version", fake_version)
    monkeypatch.setattr(framework_smoke.metadata, "metadata", fake_metadata)

    result = build_backtest_framework_smoke(
        out_dir=tmp_path / "data/research/backtest_framework_smoke",
        reports_dir=tmp_path / "data/reports",
    )

    payload = json.loads(result.smoke_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_framework_smoke.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "strategy_backtest_framework_smoke.v1"
    assert payload["dependency_added"] is False
    assert payload["external_engine_run"] is False
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert payload["target_frameworks"] == [
        "vectorbt",
        "bt",
        "quantstats",
        "empyrical_reloaded",
    ]
    assert payload["summary"] == {
        "target_count": 4,
        "imported_count": 4,
        "not_installed_count": 0,
        "import_failed_count": 0,
        "optional_extra_candidate_count": 2,
        "separate_runner_candidate_count": 0,
        "report_only_candidate_count": 2,
    }
    assert {result_item["framework_id"] for result_item in payload["results"]} == {
        "vectorbt",
        "bt",
        "quantstats",
        "empyrical_reloaded",
    }
    assert all(result_item["import_status"] == "imported" for result_item in payload["results"])
    assert all(
        result_item["python_classifiers"]
        == ["Programming Language :: Python :: 3", "Programming Language :: Python :: 3.13"]
        for result_item in payload["results"]
    )
    assert imported_modules == ["vectorbt", "bt", "quantstats", "empyrical"]
    assert result.report_path.exists()


def test_strategy_backtest_framework_smoke_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))

    result = runner.invoke(
        app,
        [
            "strategy-backtest-framework-smoke",
            "--framework",
            "vectorbt",
            "--framework",
            "quantstats",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_framework_smoke=" in result.stdout
    payload = json.loads(
        (
            data_dir / "research/backtest_framework_smoke/strategy_backtest_framework_smoke.json"
        ).read_text(encoding="utf-8")
    )
    assert payload["target_frameworks"] == ["vectorbt", "quantstats"]
    assert (data_dir / "reports/strategy_backtest_framework_smoke_report.md").exists()
