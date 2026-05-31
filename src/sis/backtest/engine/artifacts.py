from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel

from sis.backtest.engine.charts import render_line_svg, render_placeholder_svg
from sis.backtest.engine.charts import render_bar_svg
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.hashing import config_hash, input_schema_hash
from sis.backtest.engine.report import render_backtest_html, render_backtest_markdown


def write_json(path: Path, payload: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_backtest_artifacts(
    *,
    run_dir: Path,
    config: BacktestConfig,
    normalized: pl.DataFrame,
    input_data_ref: str,
    data_quality: BaseModel,
    data_manifest: BaseModel,
    event_time_source: str,
    close_source: str,
    metrics: dict[str, Any],
    benchmark_results: dict[str, Any],
    scenario_rows: list[dict[str, Any]],
    split_summary: dict[str, Any],
    parameter_rows: list[dict[str, Any]],
    orders_frame: pl.DataFrame,
    fills_frame: pl.DataFrame,
    trades_frame: pl.DataFrame,
    blocked_frame: pl.DataFrame,
    equity_frame: pl.DataFrame,
    benchmark_equity: pl.DataFrame,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "config.json", config)
    write_json(run_dir / "data_quality.json", data_quality)
    write_json(run_dir / "data_manifest.json", data_manifest)
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "benchmark_results.json", benchmark_results)
    scenario_summary = {
        "scenarios": [row["scenario"] for row in scenario_rows],
        "scenario_method": "cost_derived_v0",
        "usable_for_strategy_selection": False,
        "base_only_edge_warning": True,
    }
    parameter_summary = {
        "grid_size": len(parameter_rows),
        "parameter_method": "derived_placeholder_v0",
        "best_parameter_is_in_sample_only": True,
        "usable_for_strategy_selection": False,
    }
    write_json(run_dir / "scenario_summary.json", scenario_summary)
    write_json(run_dir / "split_results.json", split_summary)
    write_json(run_dir / "parameter_summary.json", parameter_summary)
    quality_payload = data_quality.model_dump(mode="json")
    strategy_blockers = _strategy_selection_blockers(metrics=metrics, data_quality=quality_payload)
    write_json(
        run_dir / "candidate_result.json",
        {
            "run_id": config.run_id,
            "strategy_id": config.strategy_id,
            "symbol": config.symbol,
            "metrics": metrics,
            "data_manifest": "data_manifest.json",
            "smoke_only": False,
            "auto_small_lookback_used": False,
            "usable_for_strategy_selection": not strategy_blockers,
            "strategy_selection_blockers": strategy_blockers,
        },
    )
    run_meta = {
        "run_id": config.run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "strategy_id": config.strategy_id,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "warmup_start_ts": config.period.warmup_start_ts.isoformat()
        if config.period.warmup_start_ts
        else None,
        "evaluation_start_ts": config.period.evaluation_start_ts.isoformat(),
        "evaluation_end_ts": config.period.evaluation_end_ts.isoformat(),
        "input_data_ref": input_data_ref,
        "event_time_source": event_time_source,
        "close_source": close_source,
        "config_hash": config_hash(config),
        "input_schema_hash": input_schema_hash(normalized),
        "fee_model_ref": config.cost.fee_model_ref,
        "funding_policy": config.cost.funding_policy,
        "fill_model": config.execution.fill_model,
        "end_position_policy": config.execution.end_position_policy,
        "leverage_mode": config.leverage.mode,
        "no_live_order": True,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    write_json(run_dir / "backtest_run.json", run_meta)
    (run_dir / "config_hash.txt").write_text(config_hash(config) + "\n", encoding="utf-8")
    (run_dir / "input_schema_hash.txt").write_text(
        input_schema_hash(normalized) + "\n", encoding="utf-8"
    )
    orders_frame.write_parquet(run_dir / "orders.parquet")
    fills_frame.write_parquet(run_dir / "fills.parquet")
    trades_frame.write_parquet(run_dir / "trades.parquet")
    blocked_frame.write_parquet(run_dir / "blocked_events.parquet")
    equity_frame.write_parquet(run_dir / "equity_curve.parquet")
    benchmark_equity.write_parquet(run_dir / "benchmark_equity_curve.parquet")
    pl.from_dicts(scenario_rows).write_parquet(run_dir / "scenario_results.parquet")
    pl.from_dicts(parameter_rows).write_parquet(run_dir / "parameter_results.parquet")
    artifacts = {
        "metrics": "metrics.json",
        "data_manifest": "data_manifest.json",
        "orders": "orders.parquet",
        "fills": "fills.parquet",
        "trades": "trades.parquet",
        "equity_curve": "equity_curve.parquet",
    }
    markdown = render_backtest_markdown(
        metrics=metrics,
        artifacts=artifacts,
        data_quality=data_quality.model_dump(mode="json"),
        benchmark_results=benchmark_results,
        scenario_summary=scenario_summary,
        split_summary=split_summary,
        parameter_summary=parameter_summary,
        run_meta=run_meta,
        warnings=[
            "v0.1 long-only single-symbol market-like taker fill",
            "best_parameter_is_in_sample_only: true",
            "scenario_results use cost_derived_v0 sensitivity from base run costs",
            "parameter_results use derived_placeholder_v0 and are not strategy optimization",
        ],
    )
    (run_dir / "backtest_report.md").write_text(markdown, encoding="utf-8")
    (run_dir / "backtest_report.html").write_text(render_backtest_html(markdown), encoding="utf-8")
    _write_charts(
        run_dir=run_dir,
        equity_frame=equity_frame,
        fills_frame=fills_frame,
        blocked_frame=blocked_frame,
    )
    _write_chart_data(
        run_dir=run_dir,
        run_id=config.run_id,
        equity_frame=equity_frame,
        trades_frame=trades_frame,
        blocked_frame=blocked_frame,
    )


def _strategy_selection_blockers(
    *, metrics: dict[str, Any], data_quality: dict[str, Any]
) -> list[str]:
    blockers: list[str] = []
    if metrics.get("open_position_at_end"):
        blockers.append("open_position_at_end")
    if data_quality.get("insufficient_coverage_for_strategy"):
        blockers.append("insufficient_coverage_for_strategy")
    for key in (
        "fee_unresolved_rate",
        "funding_interval_missing_rate",
        "raw_payload_ref_missing_rate",
    ):
        value = data_quality.get(key)
        if isinstance(value, int | float) and value > 0:
            blockers.append(key)
    return blockers


def _write_charts(
    *,
    run_dir: Path,
    equity_frame: pl.DataFrame,
    fills_frame: pl.DataFrame,
    blocked_frame: pl.DataFrame,
) -> None:
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    equity_values = [float(value) for value in equity_frame.get_column("equity").to_list()]
    peak = None
    drawdowns: list[float] = []
    for value in equity_values:
        peak = value if peak is None else max(peak, value)
        drawdowns.append(value / peak - 1 if peak else 0.0)
    chart_svgs = {
        "equity_curve": render_line_svg(title="Equity Curve", values=equity_values),
        "drawdown": render_line_svg(title="Drawdown", values=drawdowns),
        "trade_pnl_histogram": render_placeholder_svg(title="Trade PnL Histogram"),
        "cumulative_costs": render_line_svg(
            title="Cumulative Costs",
            values=[
                float(row.get("fee_amount") or 0) + float(row.get("extra_slippage_amount") or 0)
                for row in fills_frame.to_dicts()
            ],
        ),
        "blocked_reasons": render_bar_svg(
            title="Blocked Reasons", values=_value_counts(blocked_frame, "reason")
        )
        if not blocked_frame.is_empty()
        else render_placeholder_svg(title="Blocked Reasons"),
        "session_breakdown": render_bar_svg(
            title="Session Breakdown", values=_value_counts(equity_frame, "session_type")
        ),
    }
    for name, svg in chart_svgs.items():
        (charts_dir / f"{name}.svg").write_text(svg, encoding="utf-8")


def _write_chart_data(
    *,
    run_dir: Path,
    run_id: str,
    equity_frame: pl.DataFrame,
    trades_frame: pl.DataFrame,
    blocked_frame: pl.DataFrame,
) -> None:
    charts_data_dir = run_dir / "charts_data"
    charts_data_dir.mkdir(exist_ok=True)
    charts_payloads = {
        "equity_curve": {"rows": equity_frame.to_dicts()},
        "drawdown": {"rows": equity_frame.select(["event_ts", "equity"]).to_dicts()},
        "trades": {"rows": trades_frame.to_dicts()},
        "blocked_reasons": {"rows": blocked_frame.to_dicts()},
        "session_breakdown": {"rows": _counts_rows(equity_frame, "session_type")},
        "cumulative_costs": {"rows": _cumulative_cost_rows(trades_frame)},
    }
    for name, payload in charts_payloads.items():
        write_json(charts_data_dir / f"{name}.json", {"name": name, "run_id": run_id, **payload})


def _value_counts(frame: pl.DataFrame, column: str) -> dict[str, float]:
    if frame.is_empty() or column not in frame.columns:
        return {}
    return {str(row[column]): float(row["len"]) for row in frame.group_by(column).len().to_dicts()}


def _counts_rows(frame: pl.DataFrame, column: str) -> list[dict[str, object]]:
    if frame.is_empty() or column not in frame.columns:
        return []
    return frame.group_by(column).len().sort(column).to_dicts()


def _cumulative_cost_rows(frame: pl.DataFrame) -> list[dict[str, object]]:
    if frame.is_empty():
        return []
    running = 0.0
    rows: list[dict[str, object]] = []
    for row in frame.to_dicts():
        running += float(row.get("fees_paid") or 0)
        rows.append({"event_ts": row.get("exit_ts"), "cumulative_cost": running})
    return rows
