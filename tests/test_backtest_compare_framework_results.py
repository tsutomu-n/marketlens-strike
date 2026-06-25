from __future__ import annotations

from sis.backtest.compare_framework_results import adapter_spike, external_results, framework_run


def test_framework_result_helpers_return_empty_values_for_missing_payloads() -> None:
    assert adapter_spike(None) is None
    assert external_results(None) == []
    assert framework_run(None) is None


def test_adapter_spike_normalizes_candidates_and_boundaries() -> None:
    normalized = adapter_spike(
        {
            "schema_version": "strategy_backtest_adapter_spike.v1",
            "created_at": "2026-06-26T00:00:00Z",
            "dependency_added": False,
            "external_engine_run": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "decision": {"selected": "vectorbt"},
            "candidates": [
                "skip-me",
                {
                    "framework_id": "vectorbt",
                    "adapter_role": "vectorized_research",
                    "status": "candidate",
                    "version": "0.27",
                    "adoption_status": "deferred",
                    "adoption_blockers": ["dependency_not_added"],
                    "dependency_added": False,
                    "engine_run": False,
                    "permits_live_order": False,
                    "wallet_used": False,
                    "exchange_write_used": False,
                },
                {
                    "framework_id": "bt",
                    "adapter_role": "portfolio_comparison",
                    "status": "candidate",
                },
            ],
        }
    )

    assert normalized == {
        "schema_version": "strategy_backtest_adapter_spike.v1",
        "created_at": "2026-06-26T00:00:00Z",
        "dependency_added": False,
        "external_engine_run": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "decision": {"selected": "vectorbt"},
        "candidates": [
            {
                "framework_id": "vectorbt",
                "adapter_role": "vectorized_research",
                "status": "candidate",
                "version": "0.27",
                "adoption_status": "deferred",
                "adoption_blockers": ["dependency_not_added"],
                "dependency_added": False,
                "engine_run": False,
                "permits_live_order": False,
                "wallet_used": False,
                "exchange_write_used": False,
            },
            {
                "framework_id": "bt",
                "adapter_role": "portfolio_comparison",
                "status": "candidate",
                "version": None,
                "adoption_status": None,
                "adoption_blockers": [],
                "dependency_added": None,
                "engine_run": None,
                "permits_live_order": None,
                "wallet_used": None,
                "exchange_write_used": None,
            },
        ],
    }


def test_external_results_filters_entries_and_defaults_lists_and_metrics() -> None:
    assert external_results(
        {
            "results": [
                "skip-me",
                {
                    "framework_id": "vectorbt",
                    "adapter_role": "vectorized_research",
                    "status": "available",
                    "framework_version": "0.27",
                    "runner_mode": "local",
                    "run_status": "skipped",
                    "dependency_added": False,
                    "engine_run": False,
                    "permits_live_order": False,
                    "wallet_used": False,
                    "exchange_write_used": False,
                },
                {
                    "framework_id": "bt",
                    "adapter_role": "portfolio",
                    "reason_codes": ["dependency_missing"],
                    "metrics": {"total_return": 0.03},
                },
            ]
        }
    ) == [
        {
            "framework_id": "vectorbt",
            "adapter_role": "vectorized_research",
            "status": "available",
            "framework_version": "0.27",
            "runner_mode": "local",
            "run_status": "skipped",
            "reason_codes": [],
            "dependency_added": False,
            "engine_run": False,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "metrics": {},
        },
        {
            "framework_id": "bt",
            "adapter_role": "portfolio",
            "status": None,
            "framework_version": None,
            "runner_mode": None,
            "run_status": None,
            "reason_codes": ["dependency_missing"],
            "dependency_added": None,
            "engine_run": None,
            "permits_live_order": None,
            "wallet_used": None,
            "exchange_write_used": None,
            "metrics": {"total_return": 0.03},
        },
    ]


def test_framework_run_normalizes_runs_and_defaults_nested_sections() -> None:
    normalized = framework_run(
        {
            "schema_version": "strategy_backtest_framework_run.v1",
            "created_at": "2026-06-26T00:00:00Z",
            "selected_frameworks": ["vectorbt", "bt"],
            "summary": "not-a-dict",
            "dependency_added": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "runs": [
                "skip-me",
                {
                    "framework_id": "vectorbt",
                    "surface_type": "vectorized_backtest",
                    "status": "available",
                    "run_status": "skipped",
                    "dependency_source": "not_installed",
                    "artifact": {"path": "artifact.json"},
                    "report": "not-a-dict",
                    "boundary": "not-a-dict",
                },
                {
                    "framework_id": "bt",
                    "surface_type": "portfolio_backtest",
                    "reason_codes": ["dependency_missing"],
                    "report": {"path": "report.md"},
                    "boundary": {"permits_live_order": False},
                },
            ],
        }
    )

    assert normalized == {
        "schema_version": "strategy_backtest_framework_run.v1",
        "created_at": "2026-06-26T00:00:00Z",
        "selected_frameworks": ["vectorbt", "bt"],
        "summary": {},
        "dependency_added": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "runs": [
            {
                "framework_id": "vectorbt",
                "surface_type": "vectorized_backtest",
                "status": "available",
                "run_status": "skipped",
                "reason_codes": [],
                "dependency_source": "not_installed",
                "artifact": {"path": "artifact.json"},
                "report": None,
                "boundary": {},
            },
            {
                "framework_id": "bt",
                "surface_type": "portfolio_backtest",
                "status": None,
                "run_status": None,
                "reason_codes": ["dependency_missing"],
                "dependency_source": None,
                "artifact": None,
                "report": {"path": "report.md"},
                "boundary": {"permits_live_order": False},
            },
        ],
    }
