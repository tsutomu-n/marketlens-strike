from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from support.cli import invoke_cli


def _write_metrics(path: Path, *, summary: dict | None = None, **extra: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "strategy_authoring_backtest_result.v1",
        "strategy_id": "strategy-001",
        "paper_only": True,
        "live_order_submitted": False,
        "summary": {
            "backtest_passed": True,
            "pass_min_trade_count": True,
            "pass_all_thresholds": True,
            "walk_forward_eras": [{"signal_count": 3, "backtest_passed": True}],
        },
        "metrics": [],
    }
    if summary is not None:
        payload["summary"].update(summary)
    payload.update(extra)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_strategy_backtest_acceptance_passes_valid_metrics(tmp_path) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    out_dir = tmp_path / "data/research/strategy_lifecycle"
    reports_dir = tmp_path / "data/reports"
    _write_metrics(metrics_path)

    result = invoke_cli(
        [
            "strategy-backtest-acceptance",
            "--metrics-path",
            str(metrics_path),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out_dir / "backtest_acceptance_decision.json").read_text())
    assert payload["decision"] == "PASS_BACKTEST_ACCEPTANCE"
    assert payload["summary_checks"] == {
        "backtest_passed": True,
        "pass_min_trade_count": True,
        "pass_all_thresholds": True,
    }
    assert payload["era_summary"]["era_count"] == 1
    assert payload["permits_live_order"] is False
    Draft202012Validator(
        json.loads(Path("schemas/strategy_backtest_acceptance_decision.v1.schema.json").read_text())
    ).validate(payload)
    assert (reports_dir / "strategy_backtest_acceptance_report.md").exists()


def test_strategy_backtest_acceptance_fails_when_thresholds_fail(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    _write_metrics(metrics_path, summary={"pass_all_thresholds": False})

    result = invoke_cli(
        [
            "strategy-backtest-acceptance",
            "--metrics-path",
            str(metrics_path),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out_dir / "backtest_acceptance_decision.json").read_text())
    assert payload["decision"] == "FAIL_BACKTEST_ACCEPTANCE"
    assert "THRESHOLDS_NOT_PASSED" in payload["decision_reasons"]


def test_strategy_backtest_acceptance_needs_backtest_when_metrics_missing(tmp_path) -> None:
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"

    result = invoke_cli(
        [
            "strategy-backtest-acceptance",
            "--metrics-path",
            str(tmp_path / "missing.json"),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out_dir / "backtest_acceptance_decision.json").read_text())
    assert payload["decision"] == "NEEDS_BACKTEST"
    assert payload["source_metrics_hash"] == ""


def test_strategy_backtest_acceptance_blocks_boundary_flags(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    _write_metrics(metrics_path, live_order_submitted=True)

    result = invoke_cli(
        [
            "strategy-backtest-acceptance",
            "--metrics-path",
            str(metrics_path),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((out_dir / "backtest_acceptance_decision.json").read_text())
    assert payload["decision"] == "BLOCK_BACKTEST_BOUNDARY"
    assert payload["boundary_flags"]["live_order_submitted"] is True


def test_strategy_backtest_acceptance_exits_on_schema_mismatch(tmp_path) -> None:
    metrics_path = tmp_path / "metrics.json"
    out_dir = tmp_path / "out"
    reports_dir = tmp_path / "reports"
    _write_metrics(metrics_path, schema_version="wrong")

    result = invoke_cli(
        [
            "strategy-backtest-acceptance",
            "--metrics-path",
            str(metrics_path),
            "--out",
            str(out_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 2
    assert "schema_version mismatch" in result.stdout


def test_strategy_backtest_acceptance_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(Path("schemas/strategy_backtest_acceptance_decision.v1.schema.json").read_text())
    )
