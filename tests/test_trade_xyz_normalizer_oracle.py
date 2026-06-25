from __future__ import annotations

from sis.venues.trade_xyz.normalizer_oracle import oracle_freshness_fields
from sis.venues.trade_xyz.normalizer_oracle import oracle_ts_fields
from sis.venues.trade_xyz.normalizer_oracle import to_int_ms


def test_to_int_ms_accepts_integer_like_values_without_bools() -> None:
    assert to_int_ms(1770000000000) == 1770000000000
    assert to_int_ms(1770000000000.0) == 1770000000000
    assert to_int_ms(" 1770000000000 ") == 1770000000000
    assert to_int_ms(True) is None
    assert to_int_ms("1770000000000.1") is None


def test_oracle_ts_fields_selects_first_supported_timestamp_field() -> None:
    assert oracle_ts_fields({"oracleTs": "1770000000000", "oracle_ts": "1"}) == (
        1770000000000,
        "oracleTs",
        "observed",
        None,
    )


def test_oracle_ts_fields_records_invalid_and_missing_reasons() -> None:
    assert oracle_ts_fields({"oracleTs": "not-a-timestamp"}) == (
        None,
        "oracleTs",
        "invalid",
        "invalid_oracle_ts_field:oracleTs",
    )
    assert oracle_ts_fields({}) == (
        None,
        None,
        "missing",
        "asset_ctx_missing",
    )
    assert oracle_ts_fields({"oraclePx": "100.1"}) == (
        None,
        None,
        "missing",
        "asset_ctx_missing_oracle_timestamp_field",
    )


def test_oracle_freshness_fields_classifies_snapshot_lag_states() -> None:
    assert oracle_freshness_fields(
        oracle_price=100.1,
        source_ts_ms=1000,
        recv_ts_ms=1250,
    ) == (
        1000,
        1250,
        250,
        "observed_snapshot_lag",
        (
            "This is not oracle_ts_ms. It measures raw snapshot receive lag for rows with "
            "oracle_price."
        ),
    )
    assert oracle_freshness_fields(
        oracle_price=None,
        source_ts_ms=1000,
        recv_ts_ms=1250,
    ) == (
        None,
        None,
        None,
        "missing_oracle_price",
        "No oracle freshness proxy is recorded because oracle_price is missing.",
    )
    assert oracle_freshness_fields(
        oracle_price=100.1,
        source_ts_ms=None,
        recv_ts_ms=1250,
    ) == (
        None,
        1250,
        None,
        "missing_snapshot_timestamp",
        (
            "oracle_freshness_* is a snapshot timing proxy; source_ts_ms and recv_ts_ms "
            "are both required."
        ),
    )
    assert oracle_freshness_fields(
        oracle_price=100.1,
        source_ts_ms=1250,
        recv_ts_ms=1000,
    ) == (
        1250,
        1000,
        None,
        "invalid_clock_order",
        "source_ts_ms is later than recv_ts_ms; do not treat this as oracle freshness.",
    )
