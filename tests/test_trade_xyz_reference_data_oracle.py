from __future__ import annotations

from datetime import datetime, timezone

from sis.models import QuoteLog
from sis.venues.trade_xyz.reference_data_oracle import build_oracle_timestamp_summary
from sis.venues.trade_xyz.reference_data_oracle import oracle_freshness_proxy


def _quote(**overrides: object) -> QuoteLog:
    payload: dict[str, object] = {
        "ts_client": datetime(2026, 5, 26, 0, 15, tzinfo=timezone.utc),
        "venue": "trade_xyz",
        "canonical_symbol": "NVDA",
        "venue_symbol": "NVDA",
        "source": "fixture",
        "raw_payload_sha256": "sha",
    }
    payload.update(overrides)
    return QuoteLog(**payload)


def test_oracle_freshness_proxy_prefers_explicit_lag_and_classifies_gaps() -> None:
    assert oracle_freshness_proxy(
        _quote(oracle_freshness_status="asset_ctx_lag", oracle_freshness_lag_ms=42)
    ) == ("asset_ctx_lag", 42)
    assert oracle_freshness_proxy(_quote(oracle_freshness_status="missing_oracle_ts")) == (
        "missing_oracle_ts",
        None,
    )
    assert oracle_freshness_proxy(_quote(oracle_price=None)) == ("missing_oracle_price", None)
    assert oracle_freshness_proxy(_quote(oracle_price=100.1, source_ts_ms=None, recv_ts_ms=10)) == (
        "missing_snapshot_timestamp",
        None,
    )
    assert oracle_freshness_proxy(_quote(oracle_price=100.1, source_ts_ms=20, recv_ts_ms=10)) == (
        "invalid_clock_order",
        None,
    )
    assert oracle_freshness_proxy(_quote(oracle_price=100.1, source_ts_ms=10, recv_ts_ms=25)) == (
        "observed_snapshot_lag",
        15,
    )


def test_build_oracle_timestamp_summary_counts_global_and_symbol_details() -> None:
    summary = build_oracle_timestamp_summary(
        [
            _quote(
                oracle_ts_ms=1_770_000_000_000,
                oracle_ts_status="observed",
                oracle_ts_source="asset_ctx.oracleTs",
                oracle_price=100.1,
                source_ts_ms=100,
                recv_ts_ms=150,
            ),
            _quote(
                oracle_ts_status="missing",
                oracle_ts_missing_reason="asset_ctx_missing_oracle_timestamp_field",
                oracle_price=100.2,
                source_ts_ms=200,
                recv_ts_ms=250,
            ),
            _quote(
                canonical_symbol="TSLA",
                venue_symbol="TSLA",
                oracle_price=None,
            ),
        ]
    )

    assert summary["row_count"] == 3
    assert summary["oracle_ts_present_count"] == 1
    assert summary["oracle_ts_missing_count"] == 2
    assert summary["oracle_ts_present_rate"] == 1 / 3
    assert summary["oracle_ts_missing_rate"] == 2 / 3
    assert summary["oracle_ts_status_counts"] == {"observed": 1, "missing": 1, "unknown": 1}
    assert summary["oracle_ts_source_counts"] == {"asset_ctx.oracleTs": 1, "none": 2}
    assert summary["oracle_ts_missing_reasons"] == {
        "asset_ctx_missing_oracle_timestamp_field": 1,
        "missing_reason_not_recorded": 1,
    }
    assert summary["oracle_freshness_proxy"]["observed_count"] == 2
    assert summary["oracle_freshness_proxy"]["missing_count"] == 1
    assert summary["oracle_freshness_proxy"]["observed_rate"] == 2 / 3
    assert summary["oracle_freshness_proxy"]["status_counts"] == {
        "observed_snapshot_lag": 2,
        "missing_oracle_price": 1,
    }
    assert summary["oracle_freshness_proxy"]["lag_ms_min"] == 50
    assert summary["oracle_freshness_proxy"]["lag_ms_max"] == 50
    assert summary["per_symbol"]["NVDA"]["row_count"] == 2
    assert summary["per_symbol"]["NVDA"]["oracle_ts_present_count"] == 1
    assert summary["per_symbol"]["NVDA"]["oracle_ts_missing_count"] == 1
    assert summary["per_symbol"]["NVDA"]["oracle_freshness_observed_count"] == 2
    assert summary["per_symbol"]["TSLA"]["oracle_ts_missing_reasons"] == {
        "missing_reason_not_recorded": 1
    }
    assert "oracleTimestamp" in summary["searched_payload_fields"]
