from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.backtest.compare import build_strategy_backtest_comparison
from sis.cli import app


runner = CliRunner()


def _write_metrics(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_backtest_result.v1",
                "strategy_id": "demo_strategy",
                "paper_only": True,
                "live_order_submitted": False,
                "summary": {
                    "mode": "strategy_authoring",
                    "signals_considered": 3,
                    "executed_count": 2,
                    "blocked_count": 1,
                    "blocked_reason_counts": {"spread_too_wide": 1},
                    "exit_reason_counts": {"fixed_horizon": 2},
                    "executed_signal_summary": {
                        "result_count": 2,
                        "total_signal_return": 0.03,
                        "avg_signal_return": 0.015,
                        "win_rate": 1.0,
                        "total_cost_drag_bps": 12.5,
                        "total_notional_usd": 2000.0,
                        "notional_weighted_signal_return": 0.015,
                    },
                    "multi_leg_group_metrics": {"group_count": 0},
                    "strategy_scorecard": {
                        "schema_version": "strategy_authoring_scorecard.v1",
                        "backtest_passed": True,
                        "paper_only": True,
                        "live_order_submitted": False,
                    },
                    "aggregate_metrics": {
                        "trade_count": 2,
                        "total_return": 0.03,
                        "max_drawdown": -0.01,
                        "cost_drag_bps": 12.5,
                    },
                    "pass_thresholds": {
                        "total_return": {"actual": 0.03, "threshold": 0.01, "passed": True},
                        "cost_drag_bps": {"actual": 12.5, "threshold": 10.0, "passed": False},
                    },
                    "authoring_split_method": "purged_walk_forward",
                    "authoring_era_unit": "week",
                    "walk_forward_eras": [
                        {
                            "era": "2026-W01",
                            "signal_count": 2,
                            "executed_count": 1,
                            "aggregate_metrics": {
                                "trade_count": 1,
                                "total_return": 0.01,
                                "max_drawdown": -0.005,
                                "cost_drag_bps": 6.0,
                            },
                        },
                        {
                            "era": "2026-W02",
                            "signal_count": 1,
                            "executed_count": 1,
                            "aggregate_metrics": {
                                "trade_count": 1,
                                "total_return": 0.02,
                                "max_drawdown": -0.01,
                                "cost_drag_bps": 6.5,
                            },
                        },
                    ],
                    "optimizer": {
                        "selection_metric": "total_return",
                        "selection_direction": "maximize",
                        "resolved_selection_direction": "maximize",
                        "variant_count": 2,
                        "best_variant": {
                            "variant_id": "variant-001-best",
                            "parameters": {"backtest.label_horizon_minutes": 240},
                            "aggregate_metrics": {
                                "trade_count": 2,
                                "total_return": 0.04,
                                "max_drawdown": -0.01,
                                "cost_drag_bps": 12.0,
                            },
                            "backtest_passed": True,
                        },
                        "variants": [
                            {
                                "variant_id": "variant-001-best",
                                "parameters": {"backtest.label_horizon_minutes": 240},
                                "aggregate_metrics": {
                                    "trade_count": 2,
                                    "total_return": 0.04,
                                    "max_drawdown": -0.01,
                                    "cost_drag_bps": 12.0,
                                },
                                "backtest_passed": True,
                            },
                            {
                                "variant_id": "variant-000-base",
                                "parameters": {"backtest.label_horizon_minutes": 120},
                                "aggregate_metrics": {
                                    "trade_count": 2,
                                    "total_return": 0.03,
                                    "max_drawdown": -0.015,
                                    "cost_drag_bps": 12.5,
                                },
                                "backtest_passed": True,
                            },
                        ],
                    },
                    "backtest_passed": True,
                },
                "metrics": [
                    {
                        "venue": "trade_xyz",
                        "canonical_symbol": "XYZ100",
                        "trade_count": 2,
                        "total_return": 0.03,
                        "max_drawdown": -0.01,
                        "cost_drag_bps": 12.5,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_suite_result(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_backtest_suite_result.v1",
                "suite_id": "demo_suite",
                "created_at": "2026-06-13T00:00:00+00:00",
                "paper_only": True,
                "live_order_submitted": False,
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "exchange_write_used": False,
                "selection": {
                    "metric": "total_return",
                    "direction": "maximize",
                    "resolved_direction": "maximize",
                },
                "aggregate": {
                    "run_count": 2,
                    "strategy_count": 1,
                    "case_count": 2,
                    "passed_count": 2,
                    "failed_count": 0,
                    "trade_count": 4,
                    "total_return": 0.07,
                    "cost_drag_bps": 24.5,
                },
                "method_matrix": {
                    "method_count": 2,
                    "counts_by_method": {
                        "purged_walk_forward:trading_day": 1,
                        "single_window": 1,
                    },
                    "methods": [
                        {
                            "method_id": "purged_walk_forward:trading_day",
                            "method_type": "walk_forward",
                            "split_method": "purged_walk_forward",
                            "era_unit": "trading_day",
                            "case_ids": ["walk_forward_240m"],
                            "run_count": 1,
                            "passed_count": 1,
                            "failed_count": 0,
                        },
                        {
                            "method_id": "single_window",
                            "method_type": "single_window",
                            "split_method": "single_window",
                            "era_unit": None,
                            "case_ids": ["single_window_120m"],
                            "run_count": 1,
                            "passed_count": 1,
                            "failed_count": 0,
                        },
                    ],
                },
                "best_run": {
                    "run_id": "000-walk_forward_240m",
                    "member_index": 0,
                    "case_id": "walk_forward_240m",
                    "spec_path": "authoring.yaml",
                    "strategy_id": "demo_strategy",
                    "signal_count": 3,
                    "method_id": "purged_walk_forward:trading_day",
                    "method_type": "walk_forward",
                    "backtest": {
                        "split_method": "purged_walk_forward",
                        "era_unit": "trading_day",
                        "label_horizon_minutes": 240,
                    },
                    "summary": {
                        "backtest_passed": True,
                        "aggregate_metrics": {
                            "trade_count": 2,
                            "total_return": 0.04,
                            "max_drawdown": -0.01,
                            "cost_drag_bps": 12.0,
                        },
                    },
                },
                "runs": [
                    {
                        "run_id": "000-walk_forward_240m",
                        "member_index": 0,
                        "case_id": "walk_forward_240m",
                        "spec_path": "authoring.yaml",
                        "strategy_id": "demo_strategy",
                        "signal_count": 3,
                        "method_id": "purged_walk_forward:trading_day",
                        "method_type": "walk_forward",
                        "backtest": {
                            "split_method": "purged_walk_forward",
                            "era_unit": "trading_day",
                            "label_horizon_minutes": 240,
                        },
                        "summary": {
                            "backtest_passed": True,
                            "aggregate_metrics": {
                                "trade_count": 2,
                                "total_return": 0.04,
                                "max_drawdown": -0.01,
                                "cost_drag_bps": 12.0,
                            },
                        },
                    },
                    {
                        "run_id": "000-single_window_120m",
                        "member_index": 0,
                        "case_id": "single_window_120m",
                        "spec_path": "authoring.yaml",
                        "strategy_id": "demo_strategy",
                        "signal_count": 3,
                        "method_id": "single_window",
                        "method_type": "single_window",
                        "backtest": {
                            "split_method": "single_window",
                            "label_horizon_minutes": 120,
                        },
                        "summary": {
                            "backtest_passed": True,
                            "aggregate_metrics": {
                                "trade_count": 2,
                                "total_return": 0.03,
                                "max_drawdown": -0.015,
                                "cost_drag_bps": 12.5,
                            },
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_adapter_spike(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_backtest_adapter_spike.v1",
                "created_at": "2026-06-13T00:00:00+00:00",
                "dependency_added": False,
                "external_engine_run": False,
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "exchange_write_used": False,
                "candidates": [
                    {
                        "framework_id": "vectorbt",
                        "module": "vectorbt",
                        "distribution": "vectorbt",
                        "adapter_role": "vectorized_research_candidate",
                        "status": "not_installed",
                        "version": None,
                        "license": None,
                        "requires_python": None,
                        "license_classifiers": [],
                        "adoption_note": "metadata spike fixture",
                        "adoption_status": "requires_temporary_install_spike",
                        "adoption_blockers": ["not_installed_in_current_env"],
                        "dependency_added": False,
                        "engine_run": False,
                        "permits_live_order": False,
                        "wallet_used": False,
                        "exchange_write_used": False,
                    }
                ],
                "decision": {
                    "selected_for_dependency_adoption": None,
                    "reason_codes": ["not_installed_in_current_env"],
                    "recommended_next_step": "Run isolated temporary install.",
                },
            }
        ),
        encoding="utf-8",
    )


def _write_external_result(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "strategy_backtest_external_result.v1",
                "created_at": "2026-06-13T00:00:00+00:00",
                "source_metrics_path": "data/research/strategy_backtest_metrics.json",
                "source_metrics_hash": "sha256:" + "0" * 64,
                "dependency_added": False,
                "external_engine_run": False,
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "exchange_write_used": False,
                "results": [
                    {
                        "framework_id": "vectorbt",
                        "adapter_role": "vectorized_research_candidate",
                        "status": "not_installed",
                        "run_status": "skipped",
                        "reason_codes": ["not_installed_in_current_env"],
                        "dependency_added": False,
                        "engine_run": False,
                        "permits_live_order": False,
                        "wallet_used": False,
                        "exchange_write_used": False,
                        "metrics": {
                            "trade_count": None,
                            "total_return": None,
                            "max_drawdown": None,
                            "cost_drag_bps": None,
                            "stale_rejected_count": None,
                            "halt_rejected_count": None,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_build_strategy_backtest_comparison_writes_boundary_safe_artifacts(tmp_path) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    suite_result_path = (
        tmp_path / "data/research/backtest_suite/strategy_backtest_suite_result.json"
    )
    adapter_spike_path = (
        tmp_path / "data/research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"
    )
    external_result_path = (
        tmp_path / "data/research/backtest_external/strategy_backtest_external_result.json"
    )
    out_dir = tmp_path / "data/research/backtest_compare"
    reports_dir = tmp_path / "data/reports"
    _write_metrics(metrics_path)
    _write_suite_result(suite_result_path)
    _write_adapter_spike(adapter_spike_path)
    _write_external_result(external_result_path)

    result = build_strategy_backtest_comparison(
        metrics_path=metrics_path,
        suite_result_path=suite_result_path,
        adapter_spike_path=adapter_spike_path,
        external_result_path=external_result_path,
        out_dir=out_dir,
        reports_dir=reports_dir,
    )

    payload = json.loads(result.comparison_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_comparison.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["schema_version"] == "strategy_backtest_comparison.v1"
    assert payload["native_result"]["strategy_id"] == "demo_strategy"
    assert payload["native_result"]["backtest_passed"] is True
    assert payload["native_result"]["trade_count"] == 2
    method_ids = {item["method_id"] for item in payload["method_results"]}
    assert method_ids == {
        "strategy_authoring_native_overall",
        "strategy_authoring_walk_forward",
        "strategy_authoring_optimizer_sweep",
    }
    walk_forward = next(
        item
        for item in payload["method_results"]
        if item["method_id"] == "strategy_authoring_walk_forward"
    )
    assert walk_forward["split_method"] == "purged_walk_forward"
    assert walk_forward["era_count"] == 2
    optimizer = next(
        item
        for item in payload["method_results"]
        if item["method_id"] == "strategy_authoring_optimizer_sweep"
    )
    assert optimizer["variant_count"] == 2
    assert optimizer["best_variant"]["variant_id"] == "variant-001-best"
    assert payload["source_suite_result_path"] == suite_result_path.as_posix()
    assert payload["source_suite_result_hash"].startswith("sha256:")
    assert payload["source_adapter_spike_path"] == adapter_spike_path.as_posix()
    assert payload["source_adapter_spike_hash"].startswith("sha256:")
    assert payload["source_external_result_path"] == external_result_path.as_posix()
    assert payload["source_external_result_hash"].startswith("sha256:")
    assert payload["suite_results"][0]["suite_id"] == "demo_suite"
    assert payload["suite_results"][0]["aggregate"]["run_count"] == 2
    assert payload["suite_results"][0]["method_matrix"]["method_count"] == 2
    assert payload["suite_results"][0]["method_matrix"]["counts_by_method"] == {
        "purged_walk_forward:trading_day": 1,
        "single_window": 1,
    }
    assert payload["suite_results"][0]["best_run"]["case_id"] == "walk_forward_240m"
    assert payload["suite_results"][0]["best_run"]["method_id"] == (
        "purged_walk_forward:trading_day"
    )
    assert {run["case_id"] for run in payload["suite_results"][0]["runs"]} == {
        "single_window_120m",
        "walk_forward_240m",
    }
    assert {run["method_id"] for run in payload["suite_results"][0]["runs"]} == {
        "single_window",
        "purged_walk_forward:trading_day",
    }
    diagnostics = payload["comparison_diagnostics"]
    assert diagnostics["threshold_failures"] == [
        {
            "metric": "cost_drag_bps",
            "actual": 12.5,
            "threshold": 10.0,
        }
    ]
    assert diagnostics["weakest_eras"][0]["era"] == "2026-W01"
    assert diagnostics["suite_best_runs"][0]["case_id"] == "walk_forward_240m"
    assert "THRESHOLD_FAILURES_PRESENT" in diagnostics["diagnostic_notes"]
    assert payload["permits_live_order"] is False
    assert payload["wallet_used"] is False
    assert payload["exchange_write_used"] is False
    assert payload["adapter_spike"]["decision"]["selected_for_dependency_adoption"] is None
    assert payload["adapter_spike"]["candidates"][0]["framework_id"] == "vectorbt"
    assert payload["adapter_spike"]["candidates"][0]["dependency_added"] is False
    assert payload["external_results"][0]["framework_id"] == "vectorbt"
    assert payload["external_results"][0]["run_status"] == "skipped"
    assert payload["external_results"][0]["reason_codes"] == ["not_installed_in_current_env"]
    assert {item["framework_id"] for item in payload["framework_adapters"]} == {
        "vectorbt",
        "backtesting",
        "backtrader",
        "zipline_reloaded",
    }
    assert result.report_path.exists()


def test_strategy_backtest_compare_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")
    _write_suite_result(data_dir / "research/backtest_suite/strategy_backtest_suite_result.json")
    _write_adapter_spike(
        data_dir / "research/backtest_adapter_spike/strategy_backtest_adapter_spike.json"
    )
    _write_external_result(
        data_dir / "research/backtest_external/strategy_backtest_external_result.json"
    )

    result = runner.invoke(app, ["strategy-backtest-compare"])

    assert result.exit_code == 0, result.stdout
    assert "backtest_comparison=" in result.stdout
    payload = json.loads(
        (data_dir / "research/backtest_compare/strategy_backtest_comparison.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["suite_results"][0]["suite_id"] == "demo_suite"
    assert payload["adapter_spike"]["decision"]["reason_codes"] == ["not_installed_in_current_env"]
    assert payload["external_results"][0]["run_status"] == "skipped"
    assert (data_dir / "reports/strategy_backtest_comparison_report.md").exists()


def test_strategy_backtest_compare_without_suite_result_keeps_empty_suite_section(tmp_path) -> None:
    metrics_path = tmp_path / "data/research/strategy_backtest_metrics.json"
    out_dir = tmp_path / "data/research/backtest_compare"
    reports_dir = tmp_path / "data/reports"
    _write_metrics(metrics_path)

    result = build_strategy_backtest_comparison(
        metrics_path=metrics_path,
        out_dir=out_dir,
        reports_dir=reports_dir,
    )

    payload = json.loads(result.comparison_path.read_text(encoding="utf-8"))
    schema = json.loads(
        Path("schemas/strategy_backtest_comparison.v1.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(payload)
    assert payload["source_suite_result_path"] is None
    assert payload["source_suite_result_hash"] is None
    assert payload["source_adapter_spike_path"] is None
    assert payload["source_adapter_spike_hash"] is None
    assert payload["source_external_result_path"] is None
    assert payload["source_external_result_hash"] is None
    assert payload["suite_results"] == []
    assert payload["adapter_spike"] is None
    assert payload["external_results"] == []
    assert payload["comparison_diagnostics"]["suite_best_runs"] == []
