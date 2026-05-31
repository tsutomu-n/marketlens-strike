from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.backtest.engine.validation import simple_train_test_split


def test_simple_train_test_split_marks_train_and_test_windows() -> None:
    frame = pl.DataFrame(
        {
            "event_ts": [datetime(2026, 1, 1, hour, tzinfo=timezone.utc) for hour in range(10)],
            "symbol": ["SP500"] * 10,
        }
    )

    split = simple_train_test_split(frame, train_ratio=0.7)

    assert split.train.height == 7
    assert split.test.height == 3
    assert split.summary["oos_validation_done"] is True
