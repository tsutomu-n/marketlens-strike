from __future__ import annotations

from typing import Any

from sis.models import QuoteLog


def oracle_freshness_proxy(log: QuoteLog) -> tuple[str, int | None]:
    if log.oracle_freshness_lag_ms is not None:
        return log.oracle_freshness_status or "observed_snapshot_lag", int(
            log.oracle_freshness_lag_ms
        )
    if log.oracle_freshness_status:
        return log.oracle_freshness_status, None
    if log.oracle_price is None:
        return "missing_oracle_price", None
    if log.source_ts_ms is None or log.recv_ts_ms is None:
        return "missing_snapshot_timestamp", None
    lag_ms = log.recv_ts_ms - log.source_ts_ms
    if lag_ms < 0:
        return "invalid_clock_order", None
    return "observed_snapshot_lag", int(lag_ms)


def build_oracle_timestamp_summary(logs: list[QuoteLog]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    missing_reasons: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    freshness_status_counts: dict[str, int] = {}
    freshness_lags: list[int] = []
    per_symbol: dict[str, dict[str, Any]] = {}
    for log in logs:
        status = log.oracle_ts_status or ("observed" if log.oracle_ts_ms is not None else "unknown")
        reason = log.oracle_ts_missing_reason or (
            "none" if log.oracle_ts_ms is not None else "missing_reason_not_recorded"
        )
        source = log.oracle_ts_source or "none"
        freshness_status, freshness_lag_ms = oracle_freshness_proxy(log)
        status_counts[status] = status_counts.get(status, 0) + 1
        source_counts[source] = source_counts.get(source, 0) + 1
        freshness_status_counts[freshness_status] = (
            freshness_status_counts.get(freshness_status, 0) + 1
        )
        if freshness_lag_ms is not None:
            freshness_lags.append(freshness_lag_ms)
        if log.oracle_ts_ms is None:
            missing_reasons[reason] = missing_reasons.get(reason, 0) + 1

        symbol_entry = per_symbol.setdefault(
            log.canonical_symbol,
            {
                "row_count": 0,
                "oracle_ts_present_count": 0,
                "oracle_ts_missing_count": 0,
                "oracle_ts_status_counts": {},
                "oracle_ts_missing_reasons": {},
                "oracle_freshness_status_counts": {},
                "oracle_freshness_observed_count": 0,
            },
        )
        symbol_entry["row_count"] += 1
        if log.oracle_ts_ms is None:
            symbol_entry["oracle_ts_missing_count"] += 1
            symbol_entry["oracle_ts_missing_reasons"][reason] = (
                symbol_entry["oracle_ts_missing_reasons"].get(reason, 0) + 1
            )
        else:
            symbol_entry["oracle_ts_present_count"] += 1
        symbol_entry["oracle_ts_status_counts"][status] = (
            symbol_entry["oracle_ts_status_counts"].get(status, 0) + 1
        )
        symbol_entry["oracle_freshness_status_counts"][freshness_status] = (
            symbol_entry["oracle_freshness_status_counts"].get(freshness_status, 0) + 1
        )
        if freshness_lag_ms is not None:
            symbol_entry["oracle_freshness_observed_count"] += 1

    return {
        "row_count": len(logs),
        "oracle_ts_present_count": sum(1 for log in logs if log.oracle_ts_ms is not None),
        "oracle_ts_missing_count": sum(1 for log in logs if log.oracle_ts_ms is None),
        "oracle_ts_present_rate": (
            sum(1 for log in logs if log.oracle_ts_ms is not None) / len(logs) if logs else 0.0
        ),
        "oracle_ts_missing_rate": (
            sum(1 for log in logs if log.oracle_ts_ms is None) / len(logs) if logs else 0.0
        ),
        "oracle_ts_status_counts": status_counts,
        "oracle_ts_source_counts": source_counts,
        "oracle_ts_missing_reasons": missing_reasons,
        "oracle_freshness_proxy": {
            "description": (
                "Not oracle_ts_ms. This proxy measures raw snapshot lag using source_ts_ms "
                "and recv_ts_ms for rows that include oracle_price."
            ),
            "observed_count": len(freshness_lags),
            "missing_count": len(logs) - len(freshness_lags),
            "observed_rate": len(freshness_lags) / len(logs) if logs else 0.0,
            "status_counts": freshness_status_counts,
            "lag_ms_min": min(freshness_lags) if freshness_lags else None,
            "lag_ms_max": max(freshness_lags) if freshness_lags else None,
        },
        "per_symbol": per_symbol,
        "searched_payload_fields": [
            "oracleTs",
            "oracle_ts",
            "oracleTsMs",
            "oracle_ts_ms",
            "oracleTime",
            "oracle_time",
            "oracleTimestamp",
            "oracle_timestamp",
        ],
    }
