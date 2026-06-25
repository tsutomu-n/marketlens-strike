from __future__ import annotations

from datetime import datetime

from sis.backtest.engine.blocked import BlockedEvent
from sis.backtest.engine.config import BacktestConfig
from sis.backtest.engine.portfolio import Portfolio
from sis.backtest.engine.run_loop import optional_float, row_event_ts, row_index
from sis.backtest.trade_xyz.cost_model import calculate_v0_funding_amount


def _funding_event_ts(row: dict[str, object]) -> datetime | None:
    value = row.get("event_ts")
    return value if isinstance(value, datetime) else None


def _apply_due_funding_events(
    *,
    events: list[dict[str, object]],
    next_event_index: int,
    through_ts: datetime | None,
    config: BacktestConfig,
    portfolio: Portfolio,
    blocked: list[BlockedEvent],
    recorded_warnings: set[str],
) -> tuple[int, Portfolio]:
    if through_ts is None:
        return next_event_index, portfolio
    while next_event_index < len(events):
        event = events[next_event_index]
        event_ts = _funding_event_ts(event)
        if event_ts is None or event_ts > through_ts:
            break
        if portfolio.position_qty <= 0:
            next_event_index += 1
            continue
        portfolio = _apply_funding_amount(
            row=event,
            config=config,
            portfolio=portfolio,
            blocked=blocked,
            recorded_warnings=recorded_warnings,
            is_funding_event=True,
            blocked_row_index=next_event_index,
        )
        next_event_index += 1
    return next_event_index, portfolio


def apply_external_funding_before_signal(
    *,
    events: list[dict[str, object]],
    next_event_index: int,
    row: dict[str, object],
    config: BacktestConfig,
    portfolio: Portfolio,
    blocked: list[BlockedEvent],
    recorded_warnings: set[str],
) -> tuple[int, Portfolio]:
    if not events:
        return next_event_index, portfolio
    return _apply_due_funding_events(
        events=events,
        next_event_index=next_event_index,
        through_ts=row_event_ts(row),
        config=config,
        portfolio=portfolio,
        blocked=blocked,
        recorded_warnings=recorded_warnings,
    )


def _apply_quote_row_funding(
    *,
    row: dict[str, object],
    config: BacktestConfig,
    portfolio: Portfolio,
    blocked: list[BlockedEvent],
    recorded_warnings: set[str],
) -> Portfolio:
    if portfolio.position_qty <= 0:
        return portfolio
    return _apply_funding_amount(
        row=row,
        config=config,
        portfolio=portfolio,
        blocked=blocked,
        recorded_warnings=recorded_warnings,
        is_funding_event=bool(row.get("is_funding_event")),
        blocked_row_index=row_index(row),
    )


def apply_quote_row_funding_after_signal(
    *,
    row: dict[str, object],
    has_external_funding_events: bool,
    config: BacktestConfig,
    portfolio: Portfolio,
    blocked: list[BlockedEvent],
    recorded_warnings: set[str],
) -> Portfolio:
    if has_external_funding_events:
        return portfolio
    return _apply_quote_row_funding(
        row=row,
        config=config,
        portfolio=portfolio,
        blocked=blocked,
        recorded_warnings=recorded_warnings,
    )


def apply_external_funding_after_loop(
    *,
    events: list[dict[str, object]],
    next_event_index: int,
    config: BacktestConfig,
    portfolio: Portfolio,
    blocked: list[BlockedEvent],
    recorded_warnings: set[str],
) -> tuple[int, Portfolio]:
    if not events:
        return next_event_index, portfolio
    return _apply_due_funding_events(
        events=events,
        next_event_index=next_event_index,
        through_ts=config.period.evaluation_end_ts,
        config=config,
        portfolio=portfolio,
        blocked=blocked,
        recorded_warnings=recorded_warnings,
    )


def _apply_funding_amount(
    *,
    row: dict[str, object],
    config: BacktestConfig,
    portfolio: Portfolio,
    blocked: list[BlockedEvent],
    recorded_warnings: set[str],
    is_funding_event: bool,
    blocked_row_index: int,
) -> Portfolio:
    funding_amount, funding_warning = calculate_v0_funding_amount(
        policy=config.cost.funding_policy,
        position_qty=portfolio.position_qty,
        oracle_price=optional_float(row.get("oracle_price")),
        funding_rate=optional_float(row.get("funding_rate")),
        is_funding_event=is_funding_event,
        event_ts=row_event_ts(row),
    )
    if funding_amount:
        portfolio = portfolio.apply_funding(funding_amount)
    if funding_warning is not None and funding_warning not in recorded_warnings:
        recorded_warnings.add(funding_warning)
        blocked.append(
            BlockedEvent(
                event_ts=row_event_ts(row),
                symbol=config.symbol,
                action="funding",
                reason=funding_warning,
                strategy_id=config.strategy_id,
                signal_id=None,
                row_index=blocked_row_index,
            )
        )
    return portfolio
