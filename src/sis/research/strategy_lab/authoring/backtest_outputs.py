from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.scorecard import _metrics_json


def write_authoring_backtest_outputs(
    spec: StrategyAuthoringSpec, metrics: list[Any], summary: dict[str, Any], *, data_dir: Path
) -> dict[str, Path]:
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    report_path = data_dir / "reports/strategy_backtest_report.md"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _metrics_json(metrics, summary, spec)
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {item.venue} | {item.canonical_symbol} | {item.trade_count} | {item.total_return:.6f} | {item.max_drawdown:.6f} | {item.cost_drag_bps:.2f} |"
        for item in metrics
    )
    scorecard = summary.get("strategy_scorecard") or {}
    capital = summary.get("capital") or {}
    scorecard_lines = (
        "\n".join(
            f"- {name}: {count}"
            for name, count in (scorecard.get("derived_feature_ops") or {}).items()
        )
        or "- none"
    )
    block_reason_lines = (
        "\n".join(
            f"- {name}: {count}"
            for name, count in (scorecard.get("block_reason_counts") or {}).items()
        )
        or "- none"
    )
    report_path.write_text(
        "# Strategy Authoring Backtest Report\n\n"
        "paper_only: true\n\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- source_signal_count: {summary.get('source_signal_count')}\n"
        f"- evaluation_signal_count: {summary.get('evaluation_signal_count')}\n"
        f"- evaluation_start_at: {summary.get('evaluation_window', {}).get('evaluation_start_at')}\n"
        f"- evaluation_end_at: {summary.get('evaluation_window', {}).get('evaluation_end_at')}\n"
        f"- signals_considered: {summary.get('signals_considered')}\n"
        f"- executed_count: {summary.get('executed_count')}\n"
        f"- pass_min_trade_count: {summary.get('pass_min_trade_count')}\n\n"
        f"- pass_all_thresholds: {summary.get('pass_all_thresholds')}\n"
        f"- backtest_passed: {summary.get('backtest_passed')}\n\n"
        "## Capital\n\n"
        f"- initial_capital_usd: {capital.get('initial_capital_usd')}\n"
        f"- net_pnl_usd: {capital.get('net_pnl_usd')}\n"
        f"- ending_equity_usd: {capital.get('ending_equity_usd')}\n"
        f"- max_drawdown_loss_usd: {capital.get('max_drawdown_loss_usd')}\n\n"
        "## Strategy Scorecard\n\n"
        f"- derived_feature_count: {scorecard.get('derived_feature_count', 0)}\n"
        f"- failed_thresholds: {scorecard.get('failed_thresholds', [])}\n\n"
        "### Derived Feature Ops\n\n"
        f"{scorecard_lines}\n\n"
        "### Signal Block Reasons\n\n"
        f"{block_reason_lines}\n\n"
        "| Venue | Symbol | Trades | Total Return | Max Drawdown | Cost Drag bps |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"metrics": metrics_path, "report": report_path}
