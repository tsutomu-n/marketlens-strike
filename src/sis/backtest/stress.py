from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import (
    read_json_object as _read_json,
    sha256_file as _sha256_file,
    write_json_object,
)
from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


DEFAULT_SCENARIO_CSV = "base:0:0,mild:1:4,moderate:2:8,severe:5:20"


@dataclass(frozen=True)
class BacktestStressResult:
    stress_path: Path
    report_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class StressScenario:
    scenario_id: str
    additional_cost_bps_per_trade: float
    additional_slippage_bps_per_trade: float

    @property
    def total_additional_bps_per_trade(self) -> float:
        return self.additional_cost_bps_per_trade + self.additional_slippage_bps_per_trade


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def parse_stress_scenarios(raw: str) -> list[StressScenario]:
    scenarios: list[StressScenario] = []
    seen: set[str] = set()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        pieces = item.split(":")
        if len(pieces) != 3:
            raise ValueError(
                "scenario format must be id:additional_cost_bps:additional_slippage_bps"
            )
        scenario_id = pieces[0].strip()
        if not scenario_id:
            raise ValueError("scenario id must not be empty")
        if scenario_id in seen:
            raise ValueError(f"duplicate scenario id: {scenario_id}")
        try:
            additional_cost = float(pieces[1])
            additional_slippage = float(pieces[2])
        except ValueError as exc:
            raise ValueError(f"scenario bps values must be numeric: {item}") from exc
        if additional_cost < 0 or additional_slippage < 0:
            raise ValueError("scenario bps values must be >= 0")
        scenarios.append(
            StressScenario(
                scenario_id=scenario_id,
                additional_cost_bps_per_trade=additional_cost,
                additional_slippage_bps_per_trade=additional_slippage,
            )
        )
        seen.add(scenario_id)
    if not scenarios:
        raise ValueError("at least one stress scenario is required")
    return scenarios


def _returns(metrics_payload: dict[str, Any]) -> list[float]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    rows: list[float] = []
    for raw in summary.get("executed_signal_results") or []:
        if not isinstance(raw, dict):
            continue
        signal_return = _numeric(raw.get("signal_return"))
        if signal_return is not None:
            rows.append(signal_return)
    return rows


def _aggregate_metrics(metrics_payload: dict[str, Any]) -> dict[str, Any]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        return {}
    aggregate = summary.get("aggregate_metrics")
    return aggregate if isinstance(aggregate, dict) else {}


def _max_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for item in returns:
        equity *= 1.0 + item
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, equity / peak - 1.0)
    return max_drawdown


def _positive_rate(returns: list[float]) -> float | None:
    if not returns:
        return None
    return sum(1 for item in returns if item > 0) / len(returns)


def _scenario_payload(
    *,
    scenario: StressScenario,
    base_returns: list[float],
    base_cost_drag_bps: float,
) -> dict[str, Any]:
    additional_return_drag = scenario.total_additional_bps_per_trade / 10_000
    stressed_returns = [item - additional_return_drag for item in base_returns]
    base_total_return = sum(base_returns)
    stressed_total_return = sum(stressed_returns)
    return {
        "scenario_id": scenario.scenario_id,
        "additional_cost_bps_per_trade": scenario.additional_cost_bps_per_trade,
        "additional_slippage_bps_per_trade": scenario.additional_slippage_bps_per_trade,
        "total_additional_bps_per_trade": scenario.total_additional_bps_per_trade,
        "return_count": len(stressed_returns),
        "base_total_return": base_total_return,
        "stressed_total_return": stressed_total_return,
        "delta_total_return": stressed_total_return - base_total_return,
        "stressed_avg_signal_return": (
            stressed_total_return / len(stressed_returns) if stressed_returns else None
        ),
        "stressed_min_signal_return": min(stressed_returns) if stressed_returns else None,
        "stressed_max_signal_return": max(stressed_returns) if stressed_returns else None,
        "stressed_positive_rate": _positive_rate(stressed_returns),
        "stressed_max_drawdown": _max_drawdown(stressed_returns),
        "stressed_cost_drag_bps": (
            base_cost_drag_bps + scenario.total_additional_bps_per_trade * len(stressed_returns)
        ),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Stress",
        "",
        f"- stress_kind: {payload['stress_kind']}",
        f"- source_backtest_metrics_path: `{payload['source_backtest_metrics_path']}`",
        f"- return_count: {payload['summary']['return_count']}",
        f"- base_total_return: {payload['summary']['base_total_return']}",
        f"- worst_scenario_id: {payload['summary']['worst_scenario_id']}",
        f"- worst_stressed_total_return: {payload['summary']['worst_stressed_total_return']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Scenario | Cost bps | Slippage bps | Total return | Delta | Positive rate | Max DD |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario in payload["scenarios"]:
        lines.append(
            "| {scenario_id} | {cost} | {slippage} | {total_return} | {delta} | {positive_rate} | {max_drawdown} |".format(
                scenario_id=scenario["scenario_id"],
                cost=scenario["additional_cost_bps_per_trade"],
                slippage=scenario["additional_slippage_bps_per_trade"],
                total_return=scenario["stressed_total_return"],
                delta=scenario["delta_total_return"],
                positive_rate=scenario["stressed_positive_rate"],
                max_drawdown=scenario["stressed_max_drawdown"],
            )
        )
    return write_markdown_report(path, lines)


def build_strategy_backtest_stress(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    scenario_csv: str = DEFAULT_SCENARIO_CSV,
) -> BacktestStressResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    returns = _returns(metrics_payload)
    aggregate = _aggregate_metrics(metrics_payload)
    base_cost_drag_bps = float(_numeric(aggregate.get("cost_drag_bps")) or 0.0)
    scenarios = [
        _scenario_payload(
            scenario=scenario,
            base_returns=returns,
            base_cost_drag_bps=base_cost_drag_bps,
        )
        for scenario in parse_stress_scenarios(scenario_csv)
    ]
    worst = min(
        scenarios,
        key=lambda item: (
            float(item["stressed_total_return"])
            if item["stressed_total_return"] is not None
            else float("inf")
        ),
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_stress.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stress_kind": "cost_slippage",
            "source_backtest_metrics_path": metrics_path.as_posix(),
            "source_backtest_metrics_hash": _sha256_file(metrics_path),
            "scenario_count": len(scenarios),
            "summary": {
                "return_count": len(returns),
                "base_total_return": sum(returns),
                "base_avg_signal_return": sum(returns) / len(returns) if returns else None,
                "base_positive_rate": _positive_rate(returns),
                "base_max_drawdown": _max_drawdown(returns),
                "base_cost_drag_bps": base_cost_drag_bps,
                "worst_scenario_id": worst["scenario_id"],
                "worst_stressed_total_return": worst["stressed_total_return"],
                "worst_delta_total_return": worst["delta_total_return"],
            },
            "scenarios": scenarios,
            "dependency_added": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    stress_path = out_dir / "strategy_backtest_stress.json"
    write_json_object(stress_path, payload)
    report_path = _write_report(reports_dir / "strategy_backtest_stress_report.md", payload)
    return BacktestStressResult(stress_path=stress_path, report_path=report_path, payload=payload)
