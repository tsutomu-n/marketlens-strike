from __future__ import annotations

from datetime import datetime, timezone

from sis.core.context import DecisionContext
from sis.core.decision import DecisionRecord, RiskDecision, StrategyDecision
from sis.core.execution_plan import ExecutionPlan
from sis.paper.broker import PaperBroker
from sis.paper.fills import write_fills_parquet
from sis.paper.portfolio import PaperPortfolio, write_positions_parquet
from sis.paper.report import build_daily_paper_report


def _decision_record(action: str = "enter_long") -> tuple[DecisionRecord, ExecutionPlan]:
    context = DecisionContext(
        decision_ts=datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
        venue="gtrade",
        canonical_symbol="QQQ",
        timeframe="4h",
        quote_ts=datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
        signal_ts=datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
        signal_side="long",
        signal_strength=1.0,
        strategy_name="qqq_trend_rates_vix",
        market_status="open",
        is_tradable=True,
    )
    strategy_decision = StrategyDecision(
        strategy_name="qqq_trend_rates_vix",
        should_enter=action != "skip",
        side="long",
        timeframe="4h",
        reason="test",
        score=1.0,
    )
    risk_decision = RiskDecision(allowed=action != "skip", blocked_reasons=[] if action != "skip" else ["BLOCK_TEST"])
    execution_plan = ExecutionPlan(
        action=action,
        venue="gtrade",
        canonical_symbol="QQQ",
        timeframe="4h",
        price_reference="mark_or_exec",
        notes=[],
    )
    record = DecisionRecord(
        context=context,
        strategy_decision=strategy_decision,
        risk_decision=risk_decision,
        execution_plan=execution_plan.model_dump(mode="json"),
    )
    return record, execution_plan


def _quote_row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "best_bid": 99.9,
        "best_ask": 100.1,
        "bid_price": 99.9,
        "ask_price": 100.1,
        "mid_price": 100.0,
        "mark_price": 100.0,
        "trade_allowed": True,
        "source_confidence": 0.95,
        "venue_quality_score": 0.96,
        "market_status": "open",
        "is_tradable": True,
        "spread_bps": 2.0,
        "depth_10bps_usd": 5000.0,
        "funding_rate": 0.0001,
        "fee_mode": "standard",
    }
    base.update(overrides)
    return base


def test_paper_broker_creates_fill_for_enter_long() -> None:
    record, plan = _decision_record("enter_long")
    fill = PaperBroker().create_fill(plan, record, _quote_row(best_ask=100.2, ask_price=100.3, mark_price=100.4))

    assert fill is not None
    assert fill.action == "enter_long"
    assert fill.price == 100.2
    assert fill.fill_price_source == "best_ask"
    assert fill.canonical_symbol == "QQQ"


def test_paper_fill_uses_best_bid_for_long_exit() -> None:
    record, plan = _decision_record("exit_long")
    fill = PaperBroker().create_fill(plan, record, _quote_row(best_bid=104.8, bid_price=104.7, mark_price=104.6))

    assert fill is not None
    assert fill.action == "exit_long"
    assert fill.price == 104.8
    assert fill.fill_price_source == "best_bid"


def test_paper_broker_skips_when_execution_plan_skips() -> None:
    record, plan = _decision_record("skip")
    fill = PaperBroker().create_fill(plan, record, _quote_row())

    assert fill is None


def test_paper_rejects_when_tracking_disallows_trade() -> None:
    record, plan = _decision_record("enter_long")
    fill = PaperBroker().create_fill(plan, record, _quote_row(trade_allowed=False))

    assert fill is None


def test_paper_records_fee_mode_and_cost_bps() -> None:
    record, plan = _decision_record("enter_long")
    broker = PaperBroker(
        fee_model={
            "fee_model": {
                "trade_xyz": {
                    "fallback": {
                        "standard": {
                            "taker_bps": 9.0,
                            "maker_bps": 3.0,
                        }
                    }
                }
            }
        }
    )
    fill = broker.create_fill(
        plan,
        record,
        _quote_row(spread_bps=2.0, funding_rate=0.0001, fee_mode="standard"),
    )

    assert fill is not None
    assert fill.fee_mode == "standard"
    assert fill.estimated_round_trip_cost_bps == 14.0


def test_paper_portfolio_tracks_entry_and_exit_and_writes_artifacts(tmp_path) -> None:
    broker = PaperBroker()
    entry_record, entry_plan = _decision_record("enter_long")
    exit_record, exit_plan = _decision_record("exit_long")
    entry_fill = broker.create_fill(entry_plan, entry_record, _quote_row(best_ask=100.0, ask_price=100.1))
    exit_fill = broker.create_fill(exit_plan, exit_record, _quote_row(best_bid=105.0, bid_price=104.9))
    assert entry_fill is not None
    assert exit_fill is not None

    portfolio = PaperPortfolio()
    portfolio.apply_fill(entry_fill)
    realized = portfolio.apply_fill(exit_fill)

    assert realized == 5.0
    assert portfolio.positions() == []

    fills_path = write_fills_parquet(tmp_path / "fills.parquet", [entry_fill, exit_fill])
    positions_path = write_positions_parquet(tmp_path / "positions.parquet", portfolio.positions())
    report = build_daily_paper_report(
        [entry_fill, exit_fill],
        portfolio.positions(),
        tmp_path / "report.md",
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
        },
        execution_drift_overview_summary={
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_drift_overview.md",
        },
    )

    assert fills_path.exists()
    assert positions_path.exists()
    assert "Daily Paper Report" in report
    assert "Audit Summary" in report
    assert "overall_status: ok" in report
    assert "Phase Gate Summary" in report
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report
    assert "Execution Drift Overview" in report
    assert "overall_status: degraded" in report
    assert "source_confidence" in report
    assert "venue_quality_score" in report
    assert "block_reasons" in report
    assert "fee_mode" in report
    assert "estimated_round_trip_cost_bps" in report
    assert "fill_price_source" in report
