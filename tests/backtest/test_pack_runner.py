from __future__ import annotations

from pathlib import Path

import pytest

from sis.backtest.pack_contract import PACK_MANIFEST_ARTIFACT_KEYS
from sis.backtest.pack_runner import (
    StrategyBacktestPackRunResult,
    _assert_manifest_artifact_keys,
)


def test_pack_runner_manifest_key_guard_accepts_contract_keys() -> None:
    _assert_manifest_artifact_keys(
        {key: Path(f"{key}.json") for key in PACK_MANIFEST_ARTIFACT_KEYS}
    )


def test_pack_runner_manifest_key_guard_rejects_missing_or_extra_keys() -> None:
    artifacts = {key: Path(f"{key}.json") for key in PACK_MANIFEST_ARTIFACT_KEYS}
    artifacts.pop(PACK_MANIFEST_ARTIFACT_KEYS[0])
    artifacts["extra"] = Path("extra.json")

    with pytest.raises(ValueError, match="pack manifest artifact keys mismatch"):
        _assert_manifest_artifact_keys(artifacts)


def test_pack_runner_result_exposes_cli_echo_paths() -> None:
    result = StrategyBacktestPackRunResult(
        pack_path=Path("pack.json"),
        pack_report_path=Path("pack.md"),
        validation_path=Path("validation.json"),
        validation_report_path=Path("validation.md"),
        validation_decision="PASS",
        comparison_path=Path("comparison.json"),
        framework_run_path=Path("framework.json"),
        portfolio_comparison_path=Path("portfolio.json"),
        metric_extension_path=Path("metric.json"),
        report_extension_path=Path("report.json"),
        stress_path=Path("stress.json"),
        regime_split_path=Path("regime.json"),
        rolling_stability_path=Path("rolling.json"),
        benchmark_relative_path=Path("benchmark.json"),
        data_availability_path=Path("data.json"),
        baseline_comparison_path=Path("baseline.json"),
        no_lookahead_path=Path("no_lookahead.json"),
        execution_simulation_path=Path("execution.json"),
        assumption_ledger_path=Path("assumptions.json"),
        trial_ledger_path=Path("trials.json"),
        suite_result_path=Path("suite.json"),
    )

    assert result.validation_decision == "PASS"
    assert result.pack_path == Path("pack.json")
    assert result.framework_run_path == Path("framework.json")
    assert result.suite_result_path == Path("suite.json")
