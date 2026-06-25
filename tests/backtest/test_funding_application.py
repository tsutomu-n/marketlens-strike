from __future__ import annotations

from datetime import datetime, timezone

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import (
    BacktestConfig,
    CostConfig,
    PeriodConfig,
    PositionSizingConfig,
)
from sis.backtest.engine.funding import (
    _apply_due_funding_events,
    _apply_quote_row_funding,
    apply_external_funding_after_loop,
    apply_external_funding_before_signal,
    apply_quote_row_funding_after_signal,
)
from sis.backtest.engine.portfolio import Portfolio


def _config(*, cost: CostConfig | None = None) -> BacktestConfig:
    return BacktestConfig(
        run_id="funding-application",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 2, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
        cost=cost or CostConfig(),
    )


def _open_portfolio() -> Portfolio:
    return Portfolio(
        initial_cash_usd=10_000,
        cash_usd=9_000,
        position_qty=10,
        avg_entry_price=100,
        equity=10_000,
    )


def test_apply_due_funding_events_applies_due_external_event_only() -> None:
    blocked: list[BlockedEvent] = []
    recorded: set[str] = set()
    next_index, portfolio = _apply_due_funding_events(
        events=[
            {
                "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                "funding_rate": 0.01,
                "oracle_price": 100.0,
            },
            {
                "event_ts": datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
                "funding_rate": 0.99,
                "oracle_price": 100.0,
            },
        ],
        next_event_index=0,
        through_ts=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        config=_config(cost=CostConfig(funding_policy="fixture_hourly_v0")),
        portfolio=_open_portfolio(),
        blocked=blocked,
        recorded_warnings=recorded,
    )

    assert next_index == 1
    assert portfolio.funding_pnl == -10.0
    assert blocked == []
    assert recorded == set()


def test_apply_external_funding_before_signal_uses_current_row_timestamp() -> None:
    blocked: list[BlockedEvent] = []
    recorded: set[str] = set()
    next_index, portfolio = apply_external_funding_before_signal(
        events=[
            {
                "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                "funding_rate": 0.01,
                "oracle_price": 100.0,
            },
            {
                "event_ts": datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
                "funding_rate": 0.99,
                "oracle_price": 100.0,
            },
        ],
        next_event_index=0,
        row={"event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc)},
        config=_config(cost=CostConfig(funding_policy="fixture_hourly_v0")),
        portfolio=_open_portfolio(),
        blocked=blocked,
        recorded_warnings=recorded,
    )

    assert next_index == 1
    assert portfolio.funding_pnl == -10.0
    assert blocked == []
    assert recorded == set()


def test_apply_quote_row_funding_deduplicates_nullable_zero_warning() -> None:
    blocked: list[BlockedEvent] = []
    recorded: set[str] = set()
    row = {
        "_row_index": 7,
        "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        "oracle_price": 100.0,
        "funding_rate": 0.01,
        "is_funding_event": False,
    }
    config = _config()

    portfolio = _apply_quote_row_funding(
        row=row,
        config=config,
        portfolio=_open_portfolio(),
        blocked=blocked,
        recorded_warnings=recorded,
    )
    portfolio = _apply_quote_row_funding(
        row=row,
        config=config,
        portfolio=portfolio,
        blocked=blocked,
        recorded_warnings=recorded,
    )

    assert portfolio.funding_pnl == 0.0
    assert recorded == {"funding_rate_present_without_interval_assertion"}
    assert len(blocked) == 1
    assert blocked[0].action == "funding"
    assert blocked[0].reason == "funding_rate_present_without_interval_assertion"
    assert blocked[0].row_index == 7


def test_apply_quote_row_funding_after_signal_skips_rows_when_external_events_exist() -> None:
    blocked: list[BlockedEvent] = []
    recorded: set[str] = set()
    portfolio = apply_quote_row_funding_after_signal(
        row={
            "_row_index": 7,
            "event_ts": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            "oracle_price": 100.0,
            "funding_rate": 0.01,
            "is_funding_event": True,
        },
        has_external_funding_events=True,
        config=_config(cost=CostConfig(funding_policy="fixture_hourly_v0")),
        portfolio=_open_portfolio(),
        blocked=blocked,
        recorded_warnings=recorded,
    )

    assert portfolio.funding_pnl == 0.0
    assert blocked == []
    assert recorded == set()


def test_apply_external_funding_after_loop_catches_up_to_evaluation_end() -> None:
    blocked: list[BlockedEvent] = []
    recorded: set[str] = set()
    next_index, portfolio = apply_external_funding_after_loop(
        events=[
            {
                "event_ts": datetime(2026, 1, 1, 23, tzinfo=timezone.utc),
                "funding_rate": 0.01,
                "oracle_price": 100.0,
            },
            {
                "event_ts": datetime(2026, 1, 3, tzinfo=timezone.utc),
                "funding_rate": 0.99,
                "oracle_price": 100.0,
            },
        ],
        next_event_index=0,
        config=_config(cost=CostConfig(funding_policy="fixture_hourly_v0")),
        portfolio=_open_portfolio(),
        blocked=blocked,
        recorded_warnings=recorded,
    )

    assert next_index == 1
    assert portfolio.funding_pnl == -10.0
    assert blocked == []
    assert recorded == set()
