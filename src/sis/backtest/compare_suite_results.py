from __future__ import annotations

from typing import Any

__all__ = ["suite_results"]


def _capital(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "initial_capital_usd": payload.get("initial_capital_usd"),
        "net_pnl_usd": payload.get("net_pnl_usd"),
        "ending_equity_usd": payload.get("ending_equity_usd"),
        "max_drawdown_loss_usd": payload.get("max_drawdown_loss_usd"),
    }


def _summary_capital(summary: dict[str, Any]) -> dict[str, Any]:
    capital = summary.get("capital")
    return _capital(capital) if isinstance(capital, dict) else _capital({})


def _aggregate_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    aggregate = summary.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    return {
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "stale_rejected_count": aggregate.get("stale_rejected_count"),
        "halt_rejected_count": aggregate.get("halt_rejected_count"),
    }


def _suite_run_metrics(run: dict[str, Any]) -> dict[str, Any]:
    summary = run.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return _aggregate_metrics(summary)


def _suite_run(run: dict[str, Any]) -> dict[str, Any]:
    backtest = run.get("backtest")
    if not isinstance(backtest, dict):
        backtest = {}
    summary = run.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "run_id": run.get("run_id"),
        "case_id": run.get("case_id"),
        "strategy_id": run.get("strategy_id"),
        "signal_count": run.get("signal_count"),
        "source_signal_count": run.get("source_signal_count"),
        "evaluation_signal_count": run.get("evaluation_signal_count"),
        "method_id": run.get("method_id"),
        "method_type": run.get("method_type"),
        "base_method_id": run.get("base_method_id"),
        "resampling": run.get("resampling") if isinstance(run.get("resampling"), dict) else None,
        "backtest_passed": summary.get("backtest_passed"),
        "split_method": backtest.get("split_method"),
        "era_unit": backtest.get("era_unit"),
        "label_horizon_minutes": backtest.get("label_horizon_minutes"),
        "initial_capital_usd": backtest.get("initial_capital_usd"),
        "evaluation_start_at": backtest.get("evaluation_start_at"),
        "evaluation_end_at": backtest.get("evaluation_end_at"),
        "capital": _summary_capital(summary),
        "metrics": _suite_run_metrics(run),
    }


def suite_results(suite_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if suite_payload is None:
        return []
    best_run = suite_payload.get("best_run")
    runs = [run for run in suite_payload.get("runs") or [] if isinstance(run, dict)]
    return [
        {
            "suite_id": suite_payload.get("suite_id"),
            "schema_version": suite_payload.get("schema_version"),
            "selection": suite_payload.get("selection") or {},
            "aggregate": suite_payload.get("aggregate") or {},
            "method_matrix": suite_payload.get("method_matrix") or {},
            "best_run": _suite_run(best_run) if isinstance(best_run, dict) else None,
            "runs": [_suite_run(run) for run in runs],
            "permits_live_order": suite_payload.get("permits_live_order"),
            "live_conversion_allowed": suite_payload.get("live_conversion_allowed"),
            "wallet_used": suite_payload.get("wallet_used"),
            "exchange_write_used": suite_payload.get("exchange_write_used"),
        }
    ]
