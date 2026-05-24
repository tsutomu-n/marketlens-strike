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


def test_paper_broker_creates_fill_for_enter_long() -> None:
    record, plan = _decision_record("enter_long")
    fill = PaperBroker().create_fill(
        plan,
        record,
        {
            "exec_buy_price": 100.0,
            "mark_price": 100.1,
        },
    )

    assert fill is not None
    assert fill.action == "enter_long"
    assert fill.price == 100.0
    assert fill.canonical_symbol == "QQQ"


def test_paper_broker_skips_when_execution_plan_skips() -> None:
    record, plan = _decision_record("skip")
    fill = PaperBroker().create_fill(plan, record, {"exec_buy_price": 100.0})

    assert fill is None


def test_paper_portfolio_tracks_entry_and_exit_and_writes_artifacts(tmp_path) -> None:
    broker = PaperBroker()
    entry_record, entry_plan = _decision_record("enter_long")
    exit_record, exit_plan = _decision_record("exit_long")
    entry_fill = broker.create_fill(entry_plan, entry_record, {"exec_buy_price": 100.0})
    exit_fill = broker.create_fill(exit_plan, exit_record, {"exec_sell_price": 105.0})
    assert entry_fill is not None
    assert exit_fill is not None

    portfolio = PaperPortfolio()
    portfolio.apply_fill(entry_fill)
    realized = portfolio.apply_fill(exit_fill)

    assert realized == 5.0
    assert portfolio.positions() == []

    fills_path = write_fills_parquet(tmp_path / "fills.parquet", [entry_fill, exit_fill])
    positions_path = write_positions_parquet(tmp_path / "positions.parquet", portfolio.positions())
    report = build_daily_paper_report([entry_fill, exit_fill], portfolio.positions(), tmp_path / "report.md")

    assert fills_path.exists()
    assert positions_path.exists()
    assert "Daily Paper Report" in report
