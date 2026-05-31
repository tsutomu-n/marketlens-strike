from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.blocked import BlockedEvent, blocked_events_to_frame


def test_blocked_events_to_frame_has_rev3_columns_for_empty_and_non_empty() -> None:
    empty = blocked_events_to_frame([])

    assert empty.schema == {
        "event_ts": pl.Datetime(time_zone="UTC"),
        "symbol": pl.Utf8,
        "action": pl.Utf8,
        "reason": pl.Utf8,
        "reason_detail": pl.Utf8,
        "strategy_id": pl.Utf8,
        "signal_id": pl.Utf8,
        "row_index": pl.Int64,
    }

    frame = blocked_events_to_frame(
        [
            BlockedEvent(
                event_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
                symbol="SP500",
                action="entry",
                reason="fee_unresolved",
                reason_detail="fee_mode=unknown",
                strategy_id="sp500_breakout_v0",
                signal_id="sig-001",
                row_index=3,
            )
        ]
    )

    assert frame.to_dicts()[0]["reason"] == "fee_unresolved"
