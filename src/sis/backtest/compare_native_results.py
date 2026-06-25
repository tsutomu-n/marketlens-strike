from __future__ import annotations

from typing import Any

__all__ = ["method_results", "native_result"]


def native_result(metrics_payload: dict[str, Any]) -> dict[str, Any]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    aggregate = summary.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    executed_summary = summary.get("executed_signal_summary")
    if not isinstance(executed_summary, dict):
        executed_summary = {}
    capital = summary.get("capital")
    if not isinstance(capital, dict):
        capital = {}
    return {
        "engine_id": "strategy_authoring_native",
        "strategy_id": metrics_payload.get("strategy_id"),
        "schema_version": metrics_payload.get("schema_version"),
        "backtest_passed": summary.get("backtest_passed"),
        "signals_considered": summary.get("signals_considered"),
        "executed_count": summary.get("executed_count"),
        "blocked_count": summary.get("blocked_count"),
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "win_rate": executed_summary.get("win_rate"),
        "avg_signal_return": executed_summary.get("avg_signal_return"),
        "total_notional_usd": executed_summary.get("total_notional_usd"),
        "capital": _capital(capital),
    }


def _capital(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "initial_capital_usd": payload.get("initial_capital_usd"),
        "net_pnl_usd": payload.get("net_pnl_usd"),
        "ending_equity_usd": payload.get("ending_equity_usd"),
        "max_drawdown_loss_usd": payload.get("max_drawdown_loss_usd"),
    }


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


def _variant_metrics(variant: dict[str, Any]) -> dict[str, Any]:
    aggregate = variant.get("aggregate_metrics")
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


def _summary_capital(summary: dict[str, Any]) -> dict[str, Any]:
    capital = summary.get("capital")
    return _capital(capital) if isinstance(capital, dict) else _capital({})


def method_results(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")

    results: list[dict[str, Any]] = [
        {
            "method_id": "strategy_authoring_native_overall",
            "method_type": "native_overall",
            "engine_id": "strategy_authoring_native",
            "status": "available",
            "backtest_passed": summary.get("backtest_passed"),
            "split_method": summary.get("authoring_split_method"),
            "era_unit": summary.get("authoring_era_unit"),
            "signals_considered": summary.get("signals_considered"),
            "executed_count": summary.get("executed_count"),
            "blocked_count": summary.get("blocked_count"),
            "capital": _summary_capital(summary),
            "metrics": _aggregate_metrics(summary),
        }
    ]

    eras = summary.get("walk_forward_eras")
    if isinstance(eras, list) and eras:
        normalized_eras = [
            {
                "era": era.get("era"),
                "signal_count": era.get("signal_count"),
                "executed_count": era.get("executed_count"),
                "capital": _summary_capital(era),
                "metrics": _aggregate_metrics(era),
            }
            for era in eras
            if isinstance(era, dict)
        ]
        results.append(
            {
                "method_id": "strategy_authoring_walk_forward",
                "method_type": "walk_forward",
                "engine_id": "strategy_authoring_native",
                "status": "available",
                "backtest_passed": summary.get("backtest_passed"),
                "split_method": summary.get("authoring_split_method"),
                "era_unit": summary.get("authoring_era_unit"),
                "era_count": len(normalized_eras),
                "eras": normalized_eras,
                "metrics": _aggregate_metrics(summary),
            }
        )

    optimizer = summary.get("optimizer")
    if isinstance(optimizer, dict):
        variants = [
            {
                "variant_id": variant.get("variant_id"),
                "parameters": variant.get("parameters") if isinstance(variant, dict) else {},
                "backtest_passed": variant.get("backtest_passed"),
                "capital": _summary_capital(variant),
                "metrics": _variant_metrics(variant),
            }
            for variant in optimizer.get("variants") or []
            if isinstance(variant, dict)
        ]
        best_variant = optimizer.get("best_variant")
        normalized_best = (
            {
                "variant_id": best_variant.get("variant_id"),
                "parameters": best_variant.get("parameters"),
                "backtest_passed": best_variant.get("backtest_passed"),
                "capital": _summary_capital(best_variant),
                "metrics": _variant_metrics(best_variant),
            }
            if isinstance(best_variant, dict)
            else None
        )
        results.append(
            {
                "method_id": "strategy_authoring_optimizer_sweep",
                "method_type": "parameter_sweep",
                "engine_id": "strategy_authoring_native",
                "status": "available",
                "selection_metric": optimizer.get("selection_metric"),
                "selection_direction": optimizer.get("selection_direction"),
                "resolved_selection_direction": optimizer.get("resolved_selection_direction"),
                "variant_count": optimizer.get("variant_count"),
                "best_variant": normalized_best,
                "variants": variants,
                "metrics": _aggregate_metrics(summary),
            }
        )

    return results
