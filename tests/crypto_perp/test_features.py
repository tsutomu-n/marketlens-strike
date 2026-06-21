from __future__ import annotations

from sis.crypto_perp.bars import CandleBar, build_candle_bars, interval_to_milliseconds
from sis.crypto_perp.features import EventDetectorConfig, compute_event_features
from sis.crypto_perp.heartbeat import MarketTickerSnapshot


def make_bars(closes: list[str], turnovers: list[str]) -> list[CandleBar]:
    base_ms = 1710000000000
    interval_ms = interval_to_milliseconds("15m")
    rows = []
    for index, close in enumerate(closes):
        rows.append(
            {
                "ts_open": str(base_ms + index * interval_ms),
                "open": "100",
                "high": str(max(100, float(close)) + 1),
                "low": "99",
                "close": close,
                "base_volume": "10",
                "quote_turnover": turnovers[index],
                "candle_type": "market",
                "interval": "15m",
            }
        )
    return build_candle_bars(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        candle_rows=rows,
        ts_ingested="2026-06-21T04:00:00Z",
        source_payload_sha256="c" * 64,
        now_ms=base_ms + (len(closes) + 2) * interval_ms,
    )


def ticker() -> MarketTickerSnapshot:
    return MarketTickerSnapshot(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        ts_event="1710000000000",
        ts_received="2026-06-21T04:00:00Z",
        last_price="105",
        bid1_price="104.9",
        ask1_price="105.1",
        bid1_size="1",
        ask1_size="1",
        spread_bps="1.90476190",
        price_change_24h="0.05",
        volume_24h_base="100",
        turnover_24h_quote="10000",
        index_price="104",
        mark_price="105",
        funding_rate="0.0001",
        open_interest_raw="1234",
        open_interest_unit="base",
        source_payload_sha256="d" * 64,
    )


def test_compute_event_features_for_slow_74h_window() -> None:
    closes = ["100"] * 591 + ["105"]
    turnovers = ["1000"] * 296 + ["1200"] * 296

    features = compute_event_features(
        bars=make_bars(closes, turnovers),
        ticker=ticker(),
        detector_config=EventDetectorConfig(),
    )

    assert features.return_74h == "0.05"
    assert features.recent_turnover == "355200"
    assert features.previous_turnover == "296000"
    assert features.turnover_impulse == "0.2"
    assert features.spread_bps == "1.90476190"
    assert features.mark_index_basis_bps.startswith("96.153")
    assert features.funding_rate == "0.0001"
    assert features.open_interest_raw == "1234"
