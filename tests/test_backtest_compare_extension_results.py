from __future__ import annotations

from sis.backtest.compare_extension_results import (
    metric_extension,
    portfolio_comparison,
    report_extension,
)


def test_extension_result_helpers_return_none_for_missing_payloads() -> None:
    assert portfolio_comparison(None) is None
    assert metric_extension(None) is None
    assert report_extension(None) is None


def test_portfolio_comparison_normalizes_adapter_and_portfolio_fields() -> None:
    assert portfolio_comparison(
        {
            "framework_id": "bt",
            "adapter_role": "portfolio_comparison",
            "framework_version": "1.1",
            "runner_mode": "local",
            "dependency_source": "optional",
            "run_status": "skipped",
            "dependency_added": False,
            "engine_run": False,
            "allocation_rule_id": "equal_weight",
            "rebalance_cadence": "daily",
            "portfolio_return": 0.04,
            "max_drawdown": -0.02,
            "turnover": 0.3,
            "rebalance_count": 4,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "framework_id": "bt",
        "adapter_role": "portfolio_comparison",
        "framework_version": "1.1",
        "runner_mode": "local",
        "dependency_source": "optional",
        "run_status": "skipped",
        "reason_codes": [],
        "dependency_added": False,
        "engine_run": False,
        "allocation_rule_id": "equal_weight",
        "rebalance_cadence": "daily",
        "portfolio_return": 0.04,
        "max_drawdown": -0.02,
        "turnover": 0.3,
        "rebalance_count": 4,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def test_metric_extension_normalizes_metric_fields_and_reason_codes() -> None:
    assert metric_extension(
        {
            "framework_id": "quantstats",
            "adapter_role": "metric_extension",
            "framework_version": "0.0.62",
            "runner_mode": "local",
            "dependency_source": "not_installed",
            "metric_status": "skipped",
            "reason_codes": ["dependency_missing"],
            "dependency_added": False,
            "engine_run": False,
            "frequency": "daily",
            "risk_free_rate": 0.01,
            "return_count": 12,
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.8,
            "max_drawdown": -0.05,
            "annual_return": 0.12,
            "annual_volatility": 0.08,
            "calmar_ratio": 2.4,
            "omega_ratio": 1.1,
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "framework_id": "quantstats",
        "adapter_role": "metric_extension",
        "framework_version": "0.0.62",
        "runner_mode": "local",
        "dependency_source": "not_installed",
        "metric_status": "skipped",
        "reason_codes": ["dependency_missing"],
        "dependency_added": False,
        "engine_run": False,
        "frequency": "daily",
        "risk_free_rate": 0.01,
        "return_count": 12,
        "sharpe_ratio": 1.2,
        "sortino_ratio": 1.8,
        "max_drawdown": -0.05,
        "annual_return": 0.12,
        "annual_volatility": 0.08,
        "calmar_ratio": 2.4,
        "omega_ratio": 1.1,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def test_report_extension_normalizes_report_fields_and_defaults() -> None:
    assert report_extension(
        {
            "framework_id": "quantstats",
            "adapter_role": "html_report",
            "framework_version": "0.0.62",
            "runner_mode": "local",
            "dependency_source": "optional",
            "report_status": "built",
            "dependency_added": False,
            "engine_run": False,
            "frequency": "daily",
            "risk_free_rate": 0.01,
            "periods_per_year": 252,
            "return_count": 12,
            "metrics_table_row_count": 8,
            "quantstats_html_path": "report.html",
            "quantstats_html_hash": "abc123",
            "permits_live_order": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "framework_id": "quantstats",
        "adapter_role": "html_report",
        "framework_version": "0.0.62",
        "runner_mode": "local",
        "dependency_source": "optional",
        "report_status": "built",
        "reason_codes": [],
        "dependency_added": False,
        "engine_run": False,
        "frequency": "daily",
        "risk_free_rate": 0.01,
        "periods_per_year": 252,
        "return_count": 12,
        "metrics_table_row_count": 8,
        "quantstats_html_path": "report.html",
        "quantstats_html_hash": "abc123",
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
