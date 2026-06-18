from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.strategy_drift_review.service import build_drift_review
from sis.strategy_runtime_observation.models import RuntimeObservationSourceStage
from sis.strategy_runtime_observation.service import ingest_runtime_observation


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/paper_vs_backtest_drift_review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return path


def _ledger_rows() -> list[dict]:
    return [
        {
            "created_at": "2026-06-18T12:01:00+00:00",
            "intent_id": "intent-1",
            "candidate_id": "candidate-1",
            "venue": "bitget_demo",
            "execution_symbol": "BTCUSDT",
            "real_market_symbol": "BTCUSDT",
            "status": "paper_filled",
            "block_reasons": [],
            "quote_age_ms": 120,
            "spread_bps": 8.5,
            "notional_usd": 100.0,
            "quantity": 1.0,
            "order_id": "order-1",
            "fill_id": "fill-1",
            "live_order_submitted": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "venue_write_used": False,
        },
        {
            "created_at": "2026-06-18T12:02:00+00:00",
            "intent_id": "intent-2",
            "candidate_id": "candidate-1",
            "venue": "bitget_demo",
            "execution_symbol": "BTCUSDT",
            "real_market_symbol": "BTCUSDT",
            "status": "blocked",
            "block_reasons": ["LATEST_QUOTE_MISSING"],
            "quote_age_ms": None,
            "spread_bps": None,
            "notional_usd": 100.0,
            "quantity": 1.0,
            "order_id": None,
            "fill_id": None,
            "live_order_submitted": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "venue_write_used": False,
        },
    ]


def _session_manifest(tmp_path: Path, *, ledger_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_session_manifest.json",
        {
            "schema_version": "paper_observation_session_manifest.v1",
            "session_id": "smoke-001",
            "created_at": "2026-06-18T12:00:00Z",
            "data_dir": (tmp_path / "data").as_posix(),
            "session_dir": (tmp_path / "data/paper/observations/smoke-001").as_posix(),
            "observation_ledger_path": ledger_path.as_posix(),
            "paper_orders_path": (tmp_path / "data/paper/orders.parquet").as_posix(),
            "paper_fills_path": (tmp_path / "data/paper/fills.parquet").as_posix(),
            "paper_positions_path": (tmp_path / "data/paper/positions.parquet").as_posix(),
            "source_backtest_acceptance_path": "data/research/strategy_lifecycle/backtest_acceptance_decision.json",
            "source_backtest_acceptance_sha256": "sha256:" + "a" * 64,
            "source_operator_promotion_path": "data/research/ndx/operator_promotion_decision.json",
            "source_operator_promotion_sha256": "sha256:" + "b" * 64,
            "source_intent_preview_path": "data/paper/observations/smoke-001/source_artifacts/paper_intent_preview.json",
            "source_intent_preview_sha256": "sha256:" + "c" * 64,
            "thresholds": {
                "min_fills_for_pass": 1,
                "min_trading_days_for_pass": 1,
                "max_blocked_rate": 0.5,
                "max_consecutive_blocked": 3,
                "max_open_position_age_hours": 0.0,
            },
            "smoke": True,
            "external_api_used": False,
            "credentials_used": False,
            "permits_live_order": False,
            "wallet_used": False,
            "venue_write_used": False,
            "exchange_write_used": False,
        },
    )


def _backtest_result(tmp_path: Path, *, live_order_submitted: bool = False) -> Path:
    return _write_json(
        tmp_path / "data/research/strategy_authoring/backtest_result.json",
        {
            "schema_version": "strategy_authoring_backtest_result.v1",
            "strategy_id": "ndx-breakout-001",
            "paper_only": True,
            "live_order_submitted": live_order_submitted,
            "summary": {
                "mode": "native",
                "signals_considered": 10,
                "executed_count": 5,
                "blocked_count": 1,
                "blocked_reason_counts": {"risk": 1},
                "exit_reason_counts": {"horizon": 5},
                "executed_signal_summary": {
                    "result_count": 5,
                    "first_ts_signal": "2026-06-17T00:00:00Z",
                    "last_ts_signal": "2026-06-18T00:00:00Z",
                    "side_counts": {"long": 5},
                    "symbol_counts": {"BTCUSDT": 5},
                    "timeframe_counts": {"1m": 5},
                    "exit_reason_counts": {"horizon": 5},
                    "total_signal_return": 0.04,
                    "avg_signal_return": 0.008,
                    "win_rate": 0.6,
                    "total_cost_drag_bps": 10,
                    "total_notional_usd": 500,
                    "notional_weighted_signal_return": 0.04,
                },
                "multi_leg_group_metrics": {
                    "group_count": 5,
                    "executed_group_count": 5,
                    "complete_group_count": 5,
                    "incomplete_group_count": 0,
                    "expected_leg_count": 1,
                    "executed_leg_count": 5,
                    "total_return": 0.04,
                    "avg_group_return": 0.008,
                    "win_rate": 0.6,
                    "worst_group_return": -0.01,
                    "max_drawdown": -0.02,
                    "profit_factor": 1.4,
                    "avg_leg_return_imbalance": None,
                    "total_notional_usd": 500,
                    "notional_weighted_total_return": 0.04,
                    "cost_drag_bps": 10,
                },
                "strategy_scorecard": {
                    "schema_version": "strategy_authoring_scorecard.v1",
                    "derived_feature_count": 2,
                    "signal_count": 10,
                    "side_counts": {"long": 10},
                    "block_reason_counts": {"risk": 1},
                    "execution_block_reason_counts": {},
                    "exit_reason_counts": {"horizon": 5},
                    "backtest_passed": True,
                    "paper_only": True,
                    "live_order_submitted": False,
                },
                "backtest_passed": True,
                "pass_all_thresholds": True,
            },
            "metrics": [
                {
                    "venue": "bitget_demo",
                    "canonical_symbol": "BTCUSDT",
                    "trade_count": 5,
                    "total_return": 0.04,
                    "max_drawdown": -0.02,
                    "cost_drag_bps": 10,
                }
            ],
        },
    )


def _runtime_observation(tmp_path: Path, *, rows: list[dict] | None = None) -> Path:
    ledger_path = _write_jsonl(
        tmp_path / "data/paper/observations/smoke-001/paper_observation_ledger.jsonl",
        rows if rows is not None else _ledger_rows(),
    )
    session_manifest = _session_manifest(tmp_path, ledger_path=ledger_path)
    result = ingest_runtime_observation(
        strategy_id="ndx-breakout-001",
        session_manifest_path=session_manifest,
        out_dir=tmp_path / "data/runtime_observations/ndx-breakout-001/smoke-001",
        source_stage=RuntimeObservationSourceStage.PAPER_SMOKE,
    )
    return result.manifest_path


def test_drift_review_writes_schema_valid_review(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    backtest = _backtest_result(tmp_path)
    runtime = _runtime_observation(tmp_path)

    result = build_drift_review(
        strategy_id=None,
        backtest_result_path=backtest,
        runtime_observation_path=runtime,
        out_dir=tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/smoke-001",
    )

    assert result.review.review_status.value == "READY_FOR_HUMAN_DRIFT_REVIEW"
    assert result.review.recommended_action.value == "HUMAN_REVIEW_REQUIRED"
    assert result.review.drift_metrics.runtime_blocked_rate == 0.5
    assert result.review.drift_metrics.runtime_no_fill_rate == 0.5
    assert result.review.drift_metrics.pnl_drift_available is False
    assert result.review.runtime_summary is not None
    assert result.review.runtime_summary.pnl_available is False
    payload = json.loads(result.review_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    report = result.report_path.read_text(encoding="utf-8")
    assert "Paper vs Backtest Drift Review" in report
    assert "pnl_drift_available" in report
    assert "limited fill/block/spread review" in report


def test_drift_review_recommends_revision_when_return_drift_exceeds_limit(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rows = _ledger_rows()
    rows[0].update(
        {
            "realized_pnl_usd": -20.0,
            "gross_pnl_usd": -19.0,
            "fee_usd": 1.0,
            "slippage_usd": -0.5,
            "slippage_bps": -5.0,
            "fill_price_drift_bps": -3.0,
            "filled_notional_usd": 100.0,
            "order_status": "filled",
        }
    )
    rows[1].update({"order_status": "blocked"})

    result = build_drift_review(
        strategy_id=None,
        backtest_result_path=_backtest_result(tmp_path),
        runtime_observation_path=_runtime_observation(tmp_path, rows=rows),
        out_dir=tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/smoke-001",
        max_return_drift=0.05,
    )

    assert result.review.review_status.value == "READY_FOR_HUMAN_DRIFT_REVIEW"
    assert result.review.recommended_action.value == "REVISE_STRATEGY"
    assert result.review.runtime_summary is not None
    assert result.review.runtime_summary.pnl_available is True
    assert result.review.drift_metrics.pnl_drift_available is True
    assert result.review.drift_metrics.runtime_realized_pnl_usd_total == -20.0
    assert result.review.drift_metrics.runtime_fee_usd_total == 1.0
    assert result.review.drift_metrics.runtime_slippage_usd_total == -0.5
    assert result.review.drift_metrics.runtime_return_on_filled_notional == -0.2
    assert result.review.drift_metrics.runtime_vs_backtest_return_drift == pytest.approx(-0.24)
    failed_ids = {condition.condition_id for condition in result.review.failed_conditions}
    assert "runtime_return_drift_within_limit" in failed_ids

    payload = json.loads(result.review_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema()).validate(payload)
    assert payload["drift_metrics"]["pnl_drift_available"] is True
    assert payload["runtime_summary"]["order_lifecycle_counts"] == {"blocked": 1, "filled": 1}


def test_drift_review_recommends_revision_when_no_fill_rate_exceeds_limit(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = build_drift_review(
        strategy_id=None,
        backtest_result_path=_backtest_result(tmp_path),
        runtime_observation_path=_runtime_observation(tmp_path),
        out_dir=tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/smoke-001",
        max_no_fill_rate=0.1,
    )

    assert result.review.recommended_action.value == "REVISE_STRATEGY"
    failed_ids = {condition.condition_id for condition in result.review.failed_conditions}
    assert "runtime_no_fill_rate_within_limit" in failed_ids


def test_drift_review_blocks_boundary_violation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = build_drift_review(
        strategy_id=None,
        backtest_result_path=_backtest_result(tmp_path, live_order_submitted=True),
        runtime_observation_path=_runtime_observation(tmp_path),
        out_dir=tmp_path / "data/strategy_drift_reviews/ndx-breakout-001/smoke-001",
    )

    assert result.review.review_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert result.review.recommended_action.value == "REPAIR_ARTIFACTS"
    assert result.review.live_allowed is False
