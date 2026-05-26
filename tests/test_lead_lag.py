from sis.tracking.lead_lag import best_lag_correlation
from sis.tracking.models import TrackingRecord
from sis.tracking.reports import build_tracking_report


def test_best_lag_correlation_returns_signal() -> None:
    lag, corr = best_lag_correlation(
        real_prices=[100, 101, 102, 103, 104],
        venue_prices=[99, 100, 101, 102, 103],
    )
    assert isinstance(lag, int)
    assert corr is not None


def test_tracking_report_contains_symbol_decisions() -> None:
    rows = [
        TrackingRecord(
            ts_client="2026-05-26T00:00:00+00:00",
            canonical_symbol="NVDA",
            venue="trade_xyz",
            real_market_symbol="NVDA",
            real_price=100.0,
            venue_spread_bps=10.0,
            venue_depth_10bps_usd=10000.0,
            mark_real_diff_bps=5.0,
            source_confidence=0.9,
            venue_quality_score=1.0,
            trade_allowed=True,
        )
    ]
    report = build_tracking_report(rows)
    assert "Symbol Decisions" in report
    assert "NVDA" in report
