from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_backtest_suite_outputs(payload: dict[str, Any], *, data_dir: Path) -> dict[str, Path]:
    result_path = data_dir / "research/backtest_suite/strategy_backtest_suite_result.json"
    report_path = data_dir / "reports/strategy_backtest_suite_report.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )

    rows = "\n".join(
        "| {case_id} | {method_id} | {strategy_id} | {trades} | {total_return:.6f} | {drawdown} | {passed} |".format(
            case_id=run["case_id"],
            method_id=run["method_id"],
            strategy_id=run["strategy_id"],
            trades=int(run["summary"].get("aggregate_metrics", {}).get("trade_count") or 0),
            total_return=float(
                run["summary"].get("aggregate_metrics", {}).get("total_return") or 0.0
            ),
            drawdown=run["summary"].get("aggregate_metrics", {}).get("max_drawdown"),
            passed=run["summary"].get("backtest_passed"),
        )
        for run in payload["runs"]
    )
    best_run = payload.get("best_run") or {}
    report_path.write_text(
        "# Strategy Backtest Suite Report\n\n"
        "paper_only: true\n\n"
        f"- suite_id: {payload['suite_id']}\n"
        f"- run_count: {payload['aggregate']['run_count']}\n"
        f"- passed_count: {payload['aggregate']['passed_count']}\n"
        f"- method_count: {payload['method_matrix']['method_count']}\n"
        f"- selection_metric: {payload['selection']['metric']}\n"
        f"- resolved_selection_direction: {payload['selection']['resolved_direction']}\n"
        f"- best_run_id: {best_run.get('run_id')}\n"
        f"- permits_live_order: {payload['permits_live_order']}\n"
        f"- wallet_used: {payload['wallet_used']}\n"
        f"- exchange_write_used: {payload['exchange_write_used']}\n\n"
        "| Case | Method | Strategy | Trades | Total Return | Max Drawdown | Passed |\n"
        "|---|---|---|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"suite_result": result_path, "suite_report": report_path}
