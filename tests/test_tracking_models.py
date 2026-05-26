from datetime import datetime, timezone

from sis.tracking.models import TrackingRecord


def test_tracking_record_model() -> None:
    row = TrackingRecord(
        ts_client=datetime.now(timezone.utc),
        canonical_symbol="NVDA",
        venue="trade_xyz",
        real_market_symbol="NVDA",
        real_price=100.0,
    )
    assert row.canonical_symbol == "NVDA"
