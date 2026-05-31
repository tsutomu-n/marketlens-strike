from __future__ import annotations

from sis.backtest.engine.fill import next_fill_row_index


def test_next_fill_row_index_uses_row_after_signal() -> None:
    assert next_fill_row_index(signal_row_index=0, row_count=3) == 1
    assert next_fill_row_index(signal_row_index=1, row_count=3) == 2


def test_next_fill_row_index_returns_none_when_no_future_row_exists() -> None:
    assert next_fill_row_index(signal_row_index=2, row_count=3) is None
