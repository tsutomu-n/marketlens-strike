from __future__ import annotations

from datetime import datetime, timezone

from sis.models import QuoteLog
from sis.venues.trade_xyz.reference_data_funding import funding_event_rows


def _quote(**overrides: object) -> QuoteLog:
    payload: dict[str, object] = {
        "ts_client": datetime(2026, 5, 26, 0, 15, tzinfo=timezone.utc),
        "venue": "trade_xyz",
        "canonical_symbol": "NVDA",
        "venue_symbol": "NVDA",
        "source": "fixture",
        "raw_payload_sha256": "sha",
        "recv_ts_ms": 1_770_000_600_000,
        "source_ts_ms": 1_770_000_123_456,
        "funding_rate": -0.00001,
        "funding_interval_minutes": 60,
        "oracle_price": 100.1,
        "premium": -0.1,
        "raw_payload_ref": "fixture://quote#row=0",
    }
    payload.update(overrides)
    return QuoteLog(**payload)


def test_funding_event_rows_bucket_and_preserve_payload_fields() -> None:
    rows, skipped = funding_event_rows([_quote()])

    assert skipped == {
        "missing_funding_rate": 0,
        "missing_funding_interval_minutes": 0,
        "missing_oracle_price": 0,
        "missing_recv_ts_ms": 0,
        "missing_raw_payload_ref": 0,
    }
    assert rows == [
        {
            "schema_version": "funding_event.v1",
            "funding_event_ts": "2026-02-02T02:00:00+00:00",
            "canonical_symbol": "NVDA",
            "venue_symbol": "NVDA",
            "funding_rate": -0.00001,
            "funding_interval_minutes": 60,
            "oracle_price_at_funding": 100.1,
            "premium": -0.1,
            "impact_bid_px": None,
            "impact_ask_px": None,
            "impact_notional_usd": None,
            "source_ts_ms": 1_770_000_123_456,
            "recv_ts_ms": 1_770_000_600_000,
            "raw_payload_sha256": "sha",
            "raw_payload_ref": "fixture://quote#row=0",
        }
    ]


def test_funding_event_rows_count_skip_reasons() -> None:
    rows, skipped = funding_event_rows(
        [
            _quote(funding_rate=None),
            _quote(funding_interval_minutes=None),
            _quote(oracle_price=None),
            _quote(recv_ts_ms=None),
            _quote(raw_payload_ref=None),
        ]
    )

    assert rows == []
    assert skipped == {
        "missing_funding_rate": 1,
        "missing_funding_interval_minutes": 1,
        "missing_oracle_price": 1,
        "missing_recv_ts_ms": 1,
        "missing_raw_payload_ref": 1,
    }


def test_funding_event_rows_add_source_timestamp_fallback_notes() -> None:
    recv_rows, _ = funding_event_rows([_quote(source_ts_ms=None)])
    client_rows, _ = funding_event_rows([_quote(source_ts_ms=None, recv_ts_ms=None)])

    assert recv_rows[0]["source_ts_ms"] == 1_770_000_600_000
    assert recv_rows[0]["notes"] == ["source_ts_ms_fallback=recv_ts_ms"]
    assert client_rows == []


def test_funding_event_rows_keep_latest_by_symbol_and_hour() -> None:
    early = _quote(
        ts_client=datetime(2026, 5, 26, 0, 1, tzinfo=timezone.utc),
        source_ts_ms=1_770_000_111_111,
        raw_payload_ref="fixture://quote#row=early",
    )
    later = _quote(
        ts_client=datetime(2026, 5, 26, 0, 59, tzinfo=timezone.utc),
        source_ts_ms=1_770_000_222_222,
        raw_payload_ref="fixture://quote#row=later",
    )

    rows, skipped = funding_event_rows([later, early])

    assert skipped["missing_funding_rate"] == 0
    assert len(rows) == 1
    assert rows[0]["raw_payload_ref"] == "fixture://quote#row=later"
    assert rows[0]["source_ts_ms"] == 1_770_000_222_222
