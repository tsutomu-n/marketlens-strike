from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate

from sis.backtest.assumptions import build_strategy_backtest_assumption_ledger
from sis.backtest.baselines import build_strategy_backtest_baseline_comparison
from sis.backtest.data_availability import build_backtest_data_availability_ledger
from sis.backtest.execution_simulation import build_strategy_backtest_execution_simulation
from sis.backtest.no_lookahead import build_strategy_backtest_no_lookahead_diff
from sis.backtest.trial_ledger import build_strategy_backtest_trial_ledger


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _schema(name: str) -> dict[str, Any]:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def _metrics_path(tmp_path: Path) -> Path:
    path = tmp_path / "strategy_backtest_metrics.json"
    _write_json(
        path,
        {
            "schema_version": "strategy_backtest_metrics.v1",
            "strategy_id": "demo",
            "summary": {
                "signals_considered": 3,
                "executed_count": 3,
                "blocked_count": 0,
                "backtest_passed": True,
                "aggregate_metrics": {
                    "trade_count": 3,
                    "total_return": 0.03,
                    "max_drawdown": -0.01,
                    "cost_drag_bps": 2.0,
                },
                "executed_signal_results": [
                    {"signal_return": 0.02, "slippage_bps": 1.0, "fill_fraction": 1.0},
                    {"signal_return": -0.01, "slippage_bps": 1.0, "fill_fraction": 0.5},
                    {"signal_return": 0.03, "order_type": "limit", "time_in_force": "GTD"},
                ],
            },
        },
    )
    return path


def test_completion_artifact_builders_write_schema_valid_no_live_outputs(tmp_path: Path) -> None:
    metrics_path = _metrics_path(tmp_path)
    signals_path = tmp_path / "strategy_signals.parquet"
    quotes_path = tmp_path / "quotes.parquet"
    signals_path.write_bytes(b"signals")
    quotes_path.write_bytes(b"quotes")
    reports_dir = tmp_path / "reports"

    data_availability = build_backtest_data_availability_ledger(
        metrics_path=metrics_path,
        signals_path=signals_path,
        quotes_path=quotes_path,
        out_dir=tmp_path / "data_availability",
        reports_dir=reports_dir,
    )
    baseline = build_strategy_backtest_baseline_comparison(
        metrics_path=metrics_path,
        out_dir=tmp_path / "baseline",
        reports_dir=reports_dir,
    )
    no_lookahead = build_strategy_backtest_no_lookahead_diff(
        metrics_path=metrics_path,
        signals_path=signals_path,
        quotes_path=quotes_path,
        out_dir=tmp_path / "no_lookahead",
        reports_dir=reports_dir,
    )
    execution = build_strategy_backtest_execution_simulation(
        metrics_path=metrics_path,
        signals_path=signals_path,
        out_dir=tmp_path / "execution",
        reports_dir=reports_dir,
    )
    assumptions = build_strategy_backtest_assumption_ledger(
        data_availability_path=data_availability.ledger_path,
        baseline_comparison_path=baseline.comparison_path,
        no_lookahead_path=no_lookahead.diff_path,
        execution_simulation_path=execution.simulation_path,
        out_dir=tmp_path / "assumptions",
        reports_dir=reports_dir,
    )
    trials = build_strategy_backtest_trial_ledger(
        artifacts={
            "data_availability": data_availability.ledger_path,
            "baseline_comparison": baseline.comparison_path,
            "no_lookahead_diff": no_lookahead.diff_path,
            "execution_simulation": execution.simulation_path,
            "assumption_ledger": assumptions.ledger_path,
        },
        out_dir=tmp_path / "trials",
        reports_dir=reports_dir,
    )

    payloads_and_schemas = [
        (data_availability.payload, "backtest_data_availability_ledger.v1.schema.json"),
        (baseline.payload, "strategy_backtest_baseline_comparison.v1.schema.json"),
        (no_lookahead.payload, "strategy_backtest_no_lookahead_diff.v1.schema.json"),
        (execution.payload, "strategy_backtest_execution_simulation.v1.schema.json"),
        (assumptions.payload, "strategy_backtest_assumption_ledger.v1.schema.json"),
        (trials.payload, "strategy_backtest_trial_ledger.v1.schema.json"),
    ]
    for payload, schema_name in payloads_and_schemas:
        validate(instance=payload, schema=_schema(schema_name))
        assert payload["paper_only"] is True
        assert payload["permits_live_order"] is False
        assert payload["wallet_used"] is False
        assert payload["exchange_write_used"] is False
        assert payload["status"] == "pass"
