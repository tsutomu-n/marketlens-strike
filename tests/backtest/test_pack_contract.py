from __future__ import annotations

from pathlib import Path

from sis.backtest.pack_contract import (
    PACK_MANIFEST_ARTIFACT_KEYS,
    PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS,
    PACK_REQUIRED_SUITE_METHODS,
    BacktestArtifactKey,
    default_pack_artifact_paths,
    external_framework_policy,
)


def test_pack_required_completion_keys_are_current_validation_subset() -> None:
    assert PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS == (
        "data_availability",
        "baseline_comparison",
        "trial_ledger",
        "assumption_ledger",
        "no_lookahead_diff",
        "execution_simulation",
    )
    assert set(PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS).issubset(PACK_MANIFEST_ARTIFACT_KEYS)


def test_pack_manifest_keys_are_unique_and_include_non_required_artifacts() -> None:
    assert len(PACK_MANIFEST_ARTIFACT_KEYS) == len(set(PACK_MANIFEST_ARTIFACT_KEYS))
    assert BacktestArtifactKey.EXTERNAL_RESULT in PACK_MANIFEST_ARTIFACT_KEYS
    assert BacktestArtifactKey.EXTERNAL_RESULT not in PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS
    assert BacktestArtifactKey.COMPARISON_REPORT in PACK_MANIFEST_ARTIFACT_KEYS


def test_pack_required_suite_methods_match_current_gate() -> None:
    assert PACK_REQUIRED_SUITE_METHODS == (
        "single_window",
        "walk_forward:trading_day",
        "purged_walk_forward:trading_day",
        "purged_walk_forward:trading_day+return_bootstrap",
        "purged_walk_forward:trading_day+block_bootstrap",
    )


def test_external_framework_policy_matches_current_artifact_contract_and_is_fresh() -> None:
    policy = external_framework_policy()
    assert policy == {
        "policy_id": "native_primary_external_evaluation_only.v1",
        "standard_engine": "strategy_authoring_native",
        "decision": "complete_without_locked_external_dependency",
        "locked_dependency_added": False,
        "external_adapters_required_for_completion": False,
        "temporary_uv_with_allowed": ["vectorbt", "bt", "empyrical-reloaded", "quantstats"],
        "candidate_frameworks": [
            "vectorbt",
            "bt",
            "backtesting.py",
            "zipline-reloaded",
            "backtrader",
            "quantstats",
            "empyrical-reloaded",
            "pyfolio-reloaded",
            "qstrader",
        ],
        "adoption_requires": [
            "license_review",
            "python_3_13_uv_lock_review",
            "ci_green",
            "schema_boundary_review",
        ],
    }

    policy["temporary_uv_with_allowed"].append("mutated")

    assert "mutated" not in external_framework_policy()["temporary_uv_with_allowed"]


def test_default_pack_artifact_paths_cover_manifest_keys() -> None:
    data_dir = Path("data")
    paths = default_pack_artifact_paths(data_dir)

    assert set(paths) == set(PACK_MANIFEST_ARTIFACT_KEYS)
    assert paths[BacktestArtifactKey.ADAPTER_SPIKE] == (
        data_dir / "research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"
    )
    assert paths[BacktestArtifactKey.BUNDLE_RESULT] == (
        data_dir / "research/strategy_authoring_bundle_result.json"
    )
    assert paths[BacktestArtifactKey.RETURNS_SERIES] == (
        data_dir / "research/backtest_metric_extension/strategy_backtest_returns.jsonl"
    )
    assert paths[BacktestArtifactKey.REPORT_RETURNS_SERIES] == (
        data_dir / "research/backtest_report_extension/strategy_backtest_report_returns.jsonl"
    )
    assert paths[BacktestArtifactKey.DATA_AVAILABILITY] == (
        data_dir / "research/backtest_data_availability/backtest_data_availability_ledger.json"
    )
    assert paths[BacktestArtifactKey.COMPARISON_REPORT] == (
        data_dir / "reports/strategy_backtest_comparison_report.md"
    )
