from __future__ import annotations

from datetime import datetime, timezone

from sis.core.context import DecisionContext
from sis.core.execution_plan import build_execution_plan
from sis.core.strategy import ResearchSignalStrategy
from sis.risk.risk_gate import evaluate_risk_gate


def _row(**overrides) -> dict:
    row = {
        "ts_client": datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc).isoformat(),
        "venue": "gtrade",
        "canonical_symbol": "QQQ",
        "venue_symbol": "QQQ/USD",
        "mark_price": 100.0,
        "index_price": 100.0,
        "oracle_price": 100.0,
        "exec_buy_price": 100.1,
        "exec_sell_price": 99.9,
        "spread_bps": 2.0,
        "oracle_ts_ms": 1779415479000,
        "market_status": "open",
        "is_tradable": True,
        "source": "test",
        "raw_payload_sha256": "abc123",
    }
    row.update(overrides)
    return row


def _context(**overrides) -> DecisionContext:
    payload = {
        "decision_ts": datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc),
        "venue": "gtrade",
        "canonical_symbol": "QQQ",
        "timeframe": "4h",
        "quote_ts": datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc),
        "signal_ts": datetime(2026, 5, 22, 14, 0, tzinfo=timezone.utc),
        "signal_side": "long",
        "signal_strength": 1.0,
        "strategy_name": "qqq_seed",
        "market_status": "open",
        "is_tradable": True,
    }
    payload.update(overrides)
    return DecisionContext(**payload)


def test_research_signal_strategy_builds_entry_decision() -> None:
    context = _context()
    decision = ResearchSignalStrategy().evaluate(context)

    assert decision.should_enter is True
    assert decision.side == "long"
    assert decision.timeframe == "4h"


def test_risk_gate_blocks_scalping_timeframe() -> None:
    context = _context(timeframe="5m")
    risk = evaluate_risk_gate(context, _row())

    assert risk.allowed is False
    assert "BLOCK_SCALPING_TIMEFRAME" in risk.blocked_reasons


def test_risk_gate_blocks_missing_oracle_timestamp() -> None:
    context = _context()
    risk = evaluate_risk_gate(context, _row(oracle_ts_ms=None))

    assert risk.allowed is False
    assert "BLOCK_ORACLE_TIMESTAMP_MISSING" in risk.blocked_reasons
    assert risk.stale_rejected is True


def test_execution_plan_enters_long_when_risk_allows() -> None:
    context = _context()
    strategy_decision = ResearchSignalStrategy().evaluate(context)
    risk_decision = evaluate_risk_gate(context, _row())
    plan = build_execution_plan(context, strategy_decision, risk_decision)

    assert plan.action == "enter_long"
    assert plan.canonical_symbol == "QQQ"


def test_execution_plan_skips_when_risk_blocks() -> None:
    context = _context(timeframe="5m")
    strategy_decision = ResearchSignalStrategy().evaluate(context)
    risk_decision = evaluate_risk_gate(context, _row())
    plan = build_execution_plan(context, strategy_decision, risk_decision)

    assert plan.action == "skip"
    assert "BLOCK_SCALPING_TIMEFRAME" in plan.notes
