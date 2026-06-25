from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.engine.config import BacktestConfig, PeriodConfig, PositionSizingConfig
from sis.backtest.engine.funding_events import build_funding_event_rows


def _config() -> BacktestConfig:
    return BacktestConfig(
        run_id="run-funding-events",
        strategy_id="sp500_breakout_v0",
        symbol="SP500",
        timeframe="1h",
        period=PeriodConfig(
            evaluation_start_ts=datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            evaluation_end_ts=datetime(2026, 1, 1, 14, tzinfo=timezone.utc),
        ),
        initial_cash_usd=10_000,
        position_sizing=PositionSizingConfig(notional_usd=1_000),
    )


def test_build_funding_event_rows_normalizes_filters_and_sorts_events() -> None:
    events = pl.DataFrame(
        {
            "funding_event_ts": [
                "2026-01-01T13:00:00Z",
                "2026-01-01T12:00:00Z",
                "2026-01-01T12:30:00Z",
            ],
            "canonical_symbol": ["sp500", "SP500", "NDX"],
            "funding_rate": [0.02, 0.01, 0.99],
            "oracle_price_at_funding": [101.0, 100.0, 999.0],
        }
    )

    rows = build_funding_event_rows(events, config=_config())

    assert [row["event_ts"] for row in rows] == [
        datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
    ]
    assert [row["funding_rate"] for row in rows] == [0.01, 0.02]
    assert [row["oracle_price"] for row in rows] == [100.0, 101.0]


def test_build_funding_event_rows_applies_evaluation_period_boundaries() -> None:
    events = pl.DataFrame(
        {
            "funding_event_ts": [
                datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
                datetime(2026, 1, 1, 14, tzinfo=timezone.utc),
            ],
            "symbol": ["SP500", "SP500"],
            "funding_rate": [0.01, 0.02],
            "oracle_price_at_funding": [100.0, 101.0],
        }
    )

    rows = build_funding_event_rows(events, config=_config())

    assert len(rows) == 1
    assert rows[0]["event_ts"] == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def test_build_funding_event_rows_validates_required_timestamp_column() -> None:
    events = pl.DataFrame(
        {
            "symbol": ["SP500"],
            "funding_rate": [0.01],
            "oracle_price_at_funding": [100.0],
        }
    )

    with pytest.raises(
        ValueError, match="funding_events missing required column: funding_event_ts"
    ):
        build_funding_event_rows(events, config=_config())


def test_build_funding_event_rows_validates_symbol_column() -> None:
    events = pl.DataFrame(
        {
            "funding_event_ts": [datetime(2026, 1, 1, 12, tzinfo=timezone.utc)],
            "funding_rate": [0.01],
            "oracle_price_at_funding": [100.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="funding_events missing symbol column: canonical_symbol or symbol",
    ):
        build_funding_event_rows(events, config=_config())


def test_build_funding_event_rows_validates_required_payload_columns() -> None:
    events = pl.DataFrame(
        {
            "funding_event_ts": [datetime(2026, 1, 1, 12, tzinfo=timezone.utc)],
            "symbol": ["SP500"],
            "funding_rate": [0.01],
        }
    )

    with pytest.raises(
        ValueError,
        match="funding_events missing required columns: oracle_price_at_funding",
    ):
        build_funding_event_rows(events, config=_config())
