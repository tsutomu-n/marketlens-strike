from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta, timezone

from jsonschema import validate
import polars as pl

from sis.backtest.assumptions import build_strategy_backtest_assumption_ledger
from sis.backtest.baselines import build_strategy_backtest_baseline_comparison
from sis.backtest.data_availability import build_backtest_data_availability_ledger
from sis.backtest.execution_simulation import build_strategy_backtest_execution_simulation
from sis.backtest.no_lookahead import build_strategy_backtest_no_lookahead_diff
from sis.backtest.trial_ledger import build_strategy_backtest_trial_ledger
from sis.research.strategy_lab.authoring.io import template_yaml


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


def _quote(ts: str, price: float) -> dict[str, Any]:
    return {
        "ts_client": ts,
        "venue": "trade_xyz",
        "canonical_symbol": "XYZ100",
        "venue_symbol": "XYZ100",
        "exec_buy_price": price,
        "exec_sell_price": price - 0.1,
        "mark_price": price,
        "mid_price": price,
        "oracle_price": price,
        "index_price": price,
        "spread_bps": 1.0,
        "min_side_depth_10bps_usd": 10_000.0,
        "oracle_ts_ms": 1760000000000,
        "market_status": "open",
        "is_tradable": True,
    }


def _write_runtime_authoring_fixture(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    feature_path = data_dir / "research/feature_panel.parquet"
    quote_path = data_dir / "normalized/quotes.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows = [
        {
            "ts": start + timedelta(hours=hour),
            "canonical_symbol": "QQQ",
            "trade_allowed": True,
            "close_above_sma20": True,
            "vix_level": 20.0,
            "research_return_1d": 0.02,
            "research_return_4h": 0.01,
            "source_confidence": 0.8,
            "venue_quality_score": 0.9,
        }
        for hour in (0, 4, 8, 12, 16)
    ]
    pl.DataFrame(rows).write_parquet(feature_path)
    pl.DataFrame(
        [
            _quote(f"2026-01-01T{hour:02d}:00:00+00:00", 100.0 + index)
            for index, hour in enumerate(range(0, 24, 4))
        ]
    ).write_parquet(quote_path)
    spec_path = tmp_path / "authoring.yaml"
    spec_path.write_text(template_yaml(), encoding="utf-8")
    return spec_path


def test_completion_artifact_builders_write_schema_valid_no_live_outputs(tmp_path: Path) -> None:
    metrics_path = _metrics_path(tmp_path)
    signals_path = tmp_path / "strategy_signals.parquet"
    quotes_path = tmp_path / "quotes.parquet"
    pl.DataFrame(
        [
            {"ts_signal": datetime(2026, 1, 1, tzinfo=timezone.utc), "signal_id": "a"},
            {"ts_signal": datetime(2026, 1, 1, 4, tzinfo=timezone.utc), "signal_id": "b"},
        ]
    ).write_parquet(signals_path)
    pl.DataFrame(
        [
            {"ts_client": "2026-01-01T00:00:00+00:00", "mid_price": 100.0},
            {"ts_client": "2026-01-01T04:00:00+00:00", "mid_price": 101.0},
            {"ts_client": "2026-01-01T08:00:00+00:00", "mid_price": 102.0},
        ]
    ).write_parquet(quotes_path)
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
    assert data_availability.payload["summary"]["total_duplicate_count"] == 0
    assert data_availability.payload["summary"]["total_gap_count"] == 0
    assert any(
        row["artifact_id"] == "strategy_signals"
        and row["row_count"] == 2
        and row["available_start"] is not None
        for row in data_availability.payload["rows"]
    )
    assert baseline.payload["summary"]["diagnostic_only_count"] == 1
    assert {
        row["baseline_id"]: row["comparison_role"] for row in baseline.payload["baselines"]
    } == {
        "cash_no_trade": "cash_control",
        "simple_momentum": "return_series_control",
        "simple_mean_reversion": "return_series_control",
        "random_throttle_seed_0": "return_series_control",
        "simple_leverage_1_5x": "strategy_derived_stress",
        "simple_funding_carry": "return_series_control",
    }
    assert not any(
        flag["baseline_id"] == "simple_leverage_1_5x" for flag in baseline.payload["weakness_flags"]
    )
    assert execution.payload["execution_mode"] == "native_metrics_order_fill_events_v1"
    assert execution.payload["summary"]["order_intent_count"] == 3
    assert execution.payload["summary"]["fill_event_count"] == 3
    assert execution.payload["order_intents"]
    assert execution.payload["fill_events"]
    assert execution.payload["fill_events"][2]["fill_status"] == "filled"
    assert (
        execution.payload["fill_events"][2]["fill_status_source"]
        == "executed_result_without_explicit_fill_fraction"
    )
    assert all(
        event["market_impact_claimed"] is False for event in execution.payload["fill_events"]
    )


def test_data_availability_counts_duplicate_and_gap_per_symbol_group(tmp_path: Path) -> None:
    metrics_path = _metrics_path(tmp_path)
    signals_path = tmp_path / "strategy_signals.parquet"
    quotes_path = tmp_path / "quotes.parquet"
    reports_dir = tmp_path / "reports"
    pl.DataFrame(
        [
            {
                "ts_signal": "2026-01-01T00:00:00+00:00",
                "canonical_symbol": "AAA",
            }
        ]
    ).write_parquet(signals_path)
    pl.DataFrame(
        [
            {
                "ts_client": "2026-01-01T00:00:00+00:00",
                "venue": "demo",
                "canonical_symbol": "AAA",
                "mid_price": 100.0,
            },
            {
                "ts_client": "2026-01-01T00:00:00+00:00",
                "venue": "demo",
                "canonical_symbol": "BBB",
                "mid_price": 200.0,
            },
            {
                "ts_client": "2026-01-01T04:00:00+00:00",
                "venue": "demo",
                "canonical_symbol": "AAA",
                "mid_price": 101.0,
            },
            {
                "ts_client": "2026-01-01T12:00:00+00:00",
                "venue": "demo",
                "canonical_symbol": "AAA",
                "mid_price": 102.0,
            },
            {
                "ts_client": "2026-01-01T00:00:00+00:00",
                "venue": "demo",
                "canonical_symbol": "AAA",
                "mid_price": 100.1,
            },
        ]
    ).write_parquet(quotes_path)

    result = build_backtest_data_availability_ledger(
        metrics_path=metrics_path,
        signals_path=signals_path,
        quotes_path=quotes_path,
        out_dir=tmp_path / "data_availability",
        reports_dir=reports_dir,
    )

    quote_row = next(
        row for row in result.payload["rows"] if row["artifact_id"] == "strategy_quotes"
    )
    assert quote_row["group_columns"] == ["venue", "canonical_symbol"]
    assert quote_row["duplicate_count"] == 1
    assert quote_row["gap_count"] == 1


def test_no_lookahead_diff_runs_future_feature_mutation_replay(tmp_path: Path) -> None:
    spec_path = _write_runtime_authoring_fixture(tmp_path)
    metrics_path = _metrics_path(tmp_path)
    signals_path = tmp_path / "strategy_signals.parquet"
    quotes_path = tmp_path / "data/normalized/quotes.parquet"
    signals_path.write_bytes(b"signals")

    result = build_strategy_backtest_no_lookahead_diff(
        metrics_path=metrics_path,
        signals_path=signals_path,
        quotes_path=quotes_path,
        spec_path=spec_path,
        data_dir=tmp_path / "data",
        out_dir=tmp_path / "no_lookahead",
        reports_dir=tmp_path / "reports",
    )

    validate(
        instance=result.payload,
        schema=_schema("strategy_backtest_no_lookahead_diff.v1.schema.json"),
    )
    assert result.payload["status"] == "pass"
    assert result.payload["diff_mode"] == "runtime_future_feature_mutation_v1"
    assert result.payload["summary"]["runtime_future_mutation_replay"] is True
    assert result.payload["summary"]["checked_signal_count"] >= 1
    assert (
        result.payload["summary"]["verified_signal_count"]
        == result.payload["summary"]["checked_signal_count"]
    )
    assert result.payload["summary"]["unverified_signal_count"] == 0
    assert result.payload["summary"]["coverage_status"] in {
        "runtime_replay_verified",
        "insufficient_signal_coverage",
    }
    assert result.payload["summary"]["false_negative_risk"] in {"low", "high"}
    assert result.payload["mutation_scenarios"]
    assert all(check["passed"] is True for check in result.payload["checks"])
