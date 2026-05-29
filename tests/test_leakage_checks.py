from __future__ import annotations

from datetime import datetime, timezone

import polars as pl
import pytest

from sis.research_protocol.leakage import check_signal_time_order


def test_leakage_check_fails_feature_ts_after_signal_ts() -> None:
    frame = pl.DataFrame(
        {
            "signal_id": ["sig-001"],
            "source_feature_ts": [
                datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc),
            ],
            "source_quote_ts": [
                datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            ],
            "ts_signal": [
                datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc),
            ],
        }
    )

    with pytest.raises(ValueError, match="feature_ts > signal_ts"):
        check_signal_time_order(frame)


def test_leakage_check_fails_quote_ts_after_signal_ts() -> None:
    frame = pl.DataFrame(
        {
            "signal_id": ["sig-001"],
            "source_feature_ts": [
                datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            ],
            "source_quote_ts": [
                datetime(2026, 1, 1, 10, 5, tzinfo=timezone.utc),
            ],
            "ts_signal": [
                datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc),
            ],
        }
    )

    with pytest.raises(ValueError, match="quote_ts > signal_ts"):
        check_signal_time_order(frame)


def test_leakage_check_passes_when_sources_precede_signal() -> None:
    frame = pl.DataFrame(
        {
            "signal_id": ["sig-001"],
            "source_feature_ts": [
                datetime(2026, 1, 1, 9, 59, tzinfo=timezone.utc),
            ],
            "source_quote_ts": [
                datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            ],
            "ts_signal": [
                datetime(2026, 1, 1, 10, 1, tzinfo=timezone.utc),
            ],
        }
    )

    report = check_signal_time_order(frame)

    assert report["status"] == "pass"
    assert report["checked_rows"] == 1
