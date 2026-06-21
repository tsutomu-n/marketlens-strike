from __future__ import annotations

from sis.crypto_perp.book import (
    BitgetOrderBook,
    bitget_signed_crc32,
    checksum_payload,
)


def test_book_snapshot_validates_crc32_and_builds_bbo() -> None:
    bids = [["100", "1"], ["99", "2"]]
    asks = [["101", "3"], ["102", "4"]]
    checksum = bitget_signed_crc32(checksum_payload(bids, asks))
    book = BitgetOrderBook(native_symbol="BTCUSDT", channel="books15")

    result = book.apply_depth(
        action="snapshot",
        bids=bids,
        asks=asks,
        seq=10,
        checksum=checksum,
        ts_event_ms=1710000000000,
    )

    assert result.valid is True
    assert result.best_bid == ("100", "1")
    assert result.best_ask == ("101", "3")
    assert result.spread_bps.startswith("99.50")


def test_book_checksum_failure_invalidates_book() -> None:
    book = BitgetOrderBook(native_symbol="BTCUSDT", channel="books15")

    result = book.apply_depth(
        action="snapshot",
        bids=[["100", "1"]],
        asks=[["101", "1"]],
        seq=10,
        checksum=123,
        ts_event_ms=1710000000000,
    )

    assert result.valid is False
    assert result.invalid_reason == "CHECKSUM_FAILURE"
    assert book.valid is False


def test_book_sequence_gap_invalidates_book() -> None:
    bids = [["100", "1"]]
    asks = [["101", "1"]]
    checksum = bitget_signed_crc32(checksum_payload(bids, asks))
    book = BitgetOrderBook(native_symbol="BTCUSDT", channel="books")
    first = book.apply_depth(
        action="snapshot",
        bids=bids,
        asks=asks,
        seq=10,
        checksum=checksum,
        ts_event_ms=1710000000000,
    )
    second = book.apply_depth(
        action="update",
        bids=bids,
        asks=asks,
        seq=12,
        checksum=checksum,
        ts_event_ms=1710000000010,
    )

    assert first.valid is True
    assert second.valid is False
    assert second.invalid_reason == "SEQUENCE_GAP"
    assert book.valid is False
