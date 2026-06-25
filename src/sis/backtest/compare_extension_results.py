from __future__ import annotations

from typing import Any

__all__ = ["metric_extension", "portfolio_comparison", "report_extension"]


def portfolio_comparison(portfolio_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if portfolio_payload is None:
        return None
    return {
        "framework_id": portfolio_payload.get("framework_id"),
        "adapter_role": portfolio_payload.get("adapter_role"),
        "framework_version": portfolio_payload.get("framework_version"),
        "runner_mode": portfolio_payload.get("runner_mode"),
        "dependency_source": portfolio_payload.get("dependency_source"),
        "run_status": portfolio_payload.get("run_status"),
        "reason_codes": portfolio_payload.get("reason_codes") or [],
        "dependency_added": portfolio_payload.get("dependency_added"),
        "engine_run": portfolio_payload.get("engine_run"),
        "allocation_rule_id": portfolio_payload.get("allocation_rule_id"),
        "rebalance_cadence": portfolio_payload.get("rebalance_cadence"),
        "portfolio_return": portfolio_payload.get("portfolio_return"),
        "max_drawdown": portfolio_payload.get("max_drawdown"),
        "turnover": portfolio_payload.get("turnover"),
        "rebalance_count": portfolio_payload.get("rebalance_count"),
        "permits_live_order": portfolio_payload.get("permits_live_order"),
        "wallet_used": portfolio_payload.get("wallet_used"),
        "exchange_write_used": portfolio_payload.get("exchange_write_used"),
    }


def metric_extension(metric_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if metric_payload is None:
        return None
    return {
        "framework_id": metric_payload.get("framework_id"),
        "adapter_role": metric_payload.get("adapter_role"),
        "framework_version": metric_payload.get("framework_version"),
        "runner_mode": metric_payload.get("runner_mode"),
        "dependency_source": metric_payload.get("dependency_source"),
        "metric_status": metric_payload.get("metric_status"),
        "reason_codes": metric_payload.get("reason_codes") or [],
        "dependency_added": metric_payload.get("dependency_added"),
        "engine_run": metric_payload.get("engine_run"),
        "frequency": metric_payload.get("frequency"),
        "risk_free_rate": metric_payload.get("risk_free_rate"),
        "return_count": metric_payload.get("return_count"),
        "sharpe_ratio": metric_payload.get("sharpe_ratio"),
        "sortino_ratio": metric_payload.get("sortino_ratio"),
        "max_drawdown": metric_payload.get("max_drawdown"),
        "annual_return": metric_payload.get("annual_return"),
        "annual_volatility": metric_payload.get("annual_volatility"),
        "calmar_ratio": metric_payload.get("calmar_ratio"),
        "omega_ratio": metric_payload.get("omega_ratio"),
        "permits_live_order": metric_payload.get("permits_live_order"),
        "wallet_used": metric_payload.get("wallet_used"),
        "exchange_write_used": metric_payload.get("exchange_write_used"),
    }


def report_extension(report_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if report_payload is None:
        return None
    return {
        "framework_id": report_payload.get("framework_id"),
        "adapter_role": report_payload.get("adapter_role"),
        "framework_version": report_payload.get("framework_version"),
        "runner_mode": report_payload.get("runner_mode"),
        "dependency_source": report_payload.get("dependency_source"),
        "report_status": report_payload.get("report_status"),
        "reason_codes": report_payload.get("reason_codes") or [],
        "dependency_added": report_payload.get("dependency_added"),
        "engine_run": report_payload.get("engine_run"),
        "frequency": report_payload.get("frequency"),
        "risk_free_rate": report_payload.get("risk_free_rate"),
        "periods_per_year": report_payload.get("periods_per_year"),
        "return_count": report_payload.get("return_count"),
        "metrics_table_row_count": report_payload.get("metrics_table_row_count"),
        "quantstats_html_path": report_payload.get("quantstats_html_path"),
        "quantstats_html_hash": report_payload.get("quantstats_html_hash"),
        "permits_live_order": report_payload.get("permits_live_order"),
        "wallet_used": report_payload.get("wallet_used"),
        "exchange_write_used": report_payload.get("exchange_write_used"),
    }
