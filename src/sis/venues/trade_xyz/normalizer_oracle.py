from __future__ import annotations

from typing import Any


def to_int_ms(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def oracle_ts_fields(
    asset_ctx: dict[str, Any] | None,
) -> tuple[int | None, str | None, str, str | None]:
    if not asset_ctx:
        return None, None, "missing", "asset_ctx_missing"
    for key in (
        "oracleTs",
        "oracle_ts",
        "oracleTsMs",
        "oracle_ts_ms",
        "oracleTime",
        "oracle_time",
        "oracleTimestamp",
        "oracle_timestamp",
    ):
        if key not in asset_ctx:
            continue
        parsed = to_int_ms(asset_ctx.get(key))
        if parsed is None:
            return None, key, "invalid", f"invalid_oracle_ts_field:{key}"
        return parsed, key, "observed", None
    return None, None, "missing", "asset_ctx_missing_oracle_timestamp_field"


def oracle_freshness_fields(
    *,
    oracle_price: float | None,
    source_ts_ms: int | None,
    recv_ts_ms: int | None,
) -> tuple[int | None, int | None, int | None, str, str]:
    if oracle_price is None:
        return (
            None,
            None,
            None,
            "missing_oracle_price",
            "No oracle freshness proxy is recorded because oracle_price is missing.",
        )
    if source_ts_ms is None or recv_ts_ms is None:
        return (
            source_ts_ms,
            recv_ts_ms,
            None,
            "missing_snapshot_timestamp",
            (
                "oracle_freshness_* is a snapshot timing proxy; source_ts_ms and recv_ts_ms "
                "are both required."
            ),
        )
    lag_ms = recv_ts_ms - source_ts_ms
    if lag_ms < 0:
        return (
            source_ts_ms,
            recv_ts_ms,
            None,
            "invalid_clock_order",
            "source_ts_ms is later than recv_ts_ms; do not treat this as oracle freshness.",
        )
    return (
        source_ts_ms,
        recv_ts_ms,
        lag_ms,
        "observed_snapshot_lag",
        (
            "This is not oracle_ts_ms. It measures raw snapshot receive lag for rows with "
            "oracle_price."
        ),
    )
