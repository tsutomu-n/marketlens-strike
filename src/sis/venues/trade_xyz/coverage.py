from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sis.models import QuoteLog
from sis.storage.jsonl_store import read_jsonl
from sis.storage.jsonl_store import write_json
from sis.storage.normalize import quote_log_identity


def _utc_date(value: datetime) -> str:
    return value.astimezone(UTC).date().isoformat()


def _max_gap_seconds(timestamps: list[datetime]) -> float | None:
    if len(timestamps) < 2:
        return None
    ordered = sorted(item.astimezone(UTC) for item in timestamps)
    gaps = [
        (right - left).total_seconds() for left, right in zip(ordered, ordered[1:], strict=False)
    ]
    return max(gaps) if gaps else None


def _span_days(timestamps: list[datetime]) -> float:
    if not timestamps:
        return 0.0
    ordered = sorted(item.astimezone(UTC) for item in timestamps)
    return (ordered[-1] - ordered[0]).total_seconds() / 86_400


def _segments_by_gap(
    timestamps: list[datetime],
    *,
    max_gap_seconds_limit: float,
) -> list[list[datetime]]:
    ordered = sorted(item.astimezone(UTC) for item in timestamps)
    if not ordered:
        return []
    segments: list[list[datetime]] = [[ordered[0]]]
    for left, right in zip(ordered, ordered[1:], strict=False):
        if (right - left).total_seconds() > max_gap_seconds_limit:
            segments.append([right])
        else:
            segments[-1].append(right)
    return segments


def build_trade_xyz_quote_coverage_manifest(
    *,
    data_dir: Path,
    raw_quotes_root: Path | None = None,
    symbols: list[str] | None = None,
    min_days: float = 30.0,
    max_gap_minutes: float = 10.0,
    traceable_only: bool = True,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    effective_raw_root = raw_quotes_root or data_dir / "raw/quotes"
    requested_symbols = [item.upper() for item in symbols] if symbols else None
    requested_symbol_set = set(requested_symbols or [])
    raw_payload_ref_missing_by_symbol: dict[str, int] = defaultdict(int)
    raw_row_count_by_symbol: dict[str, int] = defaultdict(int)
    logs: list[QuoteLog] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in sorted((effective_raw_root / "trade_xyz").glob("*.jsonl")):
        for row in read_jsonl(path):
            symbol = row.get("canonical_symbol")
            if not isinstance(symbol, str):
                continue
            normalized_symbol = symbol.upper()
            if requested_symbols is not None and normalized_symbol not in requested_symbol_set:
                continue
            raw_row_count_by_symbol[normalized_symbol] += 1
            if row.get("raw_payload_ref") is None:
                raw_payload_ref_missing_by_symbol[normalized_symbol] += 1
                if traceable_only:
                    continue
            log = QuoteLog.model_validate(row)
            key = quote_log_identity(log)
            if key in seen:
                continue
            seen.add(key)
            logs.append(log)
    if not raw_row_count_by_symbol:
        raise FileNotFoundError(f"No Trade[XYZ] quote JSONL rows found under {effective_raw_root}")

    grouped: dict[str, list[datetime]] = defaultdict(list)
    quality_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "row_count": 0,
            "missing_raw_payload_ref": 0,
            "missing_exec_buy_price": 0,
            "missing_exec_sell_price": 0,
            "missing_oracle_ts_ms": 0,
            "missing_fee_bps": 0,
            "missing_funding_rate": 0,
        }
    )
    for log in logs:
        symbol = log.canonical_symbol.upper()
        grouped[symbol].append(log.ts_client)
        counts = quality_counts[symbol]
        counts["row_count"] += 1
        counts["missing_raw_payload_ref"] += 1 if log.raw_payload_ref is None else 0
        counts["missing_exec_buy_price"] += 1 if log.exec_buy_price is None else 0
        counts["missing_exec_sell_price"] += 1 if log.exec_sell_price is None else 0
        counts["missing_oracle_ts_ms"] += 1 if log.oracle_ts_ms is None else 0
        counts["missing_fee_bps"] += (
            1 if log.taker_fee_bps is None or log.maker_fee_bps is None else 0
        )
        counts["missing_funding_rate"] += 1 if log.funding_rate is None else 0

    max_gap_seconds_limit = max_gap_minutes * 60
    per_symbol: dict[str, dict[str, Any]] = {}
    for symbol, timestamps in sorted(grouped.items()):
        ordered = sorted(item.astimezone(UTC) for item in timestamps)
        observed_distinct_dates = sorted({_utc_date(item) for item in ordered})
        observed_span_days = _span_days(ordered)
        observed_max_gap = _max_gap_seconds(ordered)
        segments = _segments_by_gap(ordered, max_gap_seconds_limit=max_gap_seconds_limit)
        selected_segment = segments[-1] if segments else []
        distinct_dates = sorted({_utc_date(item) for item in selected_segment})
        span_days = _span_days(selected_segment)
        max_gap = _max_gap_seconds(selected_segment)
        counts = quality_counts[symbol]
        n = counts["row_count"]
        insufficient_reasons: list[str] = []
        if span_days < min_days:
            insufficient_reasons.append("span_days_below_min")
        if max_gap is None:
            insufficient_reasons.append("single_or_missing_gap_basis")
        elif max_gap > max_gap_seconds_limit:
            insufficient_reasons.append("max_gap_above_limit")
        if counts["missing_raw_payload_ref"] > 0:
            insufficient_reasons.append("raw_payload_ref_missing")
        per_symbol[symbol] = {
            "row_count": n,
            "raw_row_count": raw_row_count_by_symbol.get(symbol, n),
            "excluded_missing_raw_payload_ref_count": (
                raw_payload_ref_missing_by_symbol.get(symbol, 0) if traceable_only else 0
            ),
            "first_ts": selected_segment[0].isoformat() if selected_segment else None,
            "last_ts": selected_segment[-1].isoformat() if selected_segment else None,
            "span_days": span_days,
            "distinct_utc_date_count": len(distinct_dates),
            "distinct_utc_dates": distinct_dates,
            "max_gap_seconds": max_gap,
            "observed_first_ts": ordered[0].isoformat(),
            "observed_last_ts": ordered[-1].isoformat(),
            "observed_span_days": observed_span_days,
            "observed_distinct_utc_date_count": len(observed_distinct_dates),
            "observed_max_gap_seconds": observed_max_gap,
            "gap_segment_count": len(segments),
            "selected_gap_segment_index": len(segments) - 1 if segments else None,
            "selected_gap_segment_row_count": len(selected_segment),
            "min_days_required": min_days,
            "max_gap_minutes_allowed": max_gap_minutes,
            "coverage_status": "pass" if not insufficient_reasons else "insufficient",
            "insufficient_reasons": insufficient_reasons,
            "missing_rates": {
                "raw_payload_ref": counts["missing_raw_payload_ref"] / n if n else 0.0,
                "exec_buy_price": counts["missing_exec_buy_price"] / n if n else 0.0,
                "exec_sell_price": counts["missing_exec_sell_price"] / n if n else 0.0,
                "oracle_ts_ms": counts["missing_oracle_ts_ms"] / n if n else 0.0,
                "fee_bps": counts["missing_fee_bps"] / n if n else 0.0,
                "funding_rate": counts["missing_funding_rate"] / n if n else 0.0,
            },
        }
    for symbol in sorted(set(raw_row_count_by_symbol) - set(per_symbol)):
        excluded_count = raw_payload_ref_missing_by_symbol.get(symbol, 0)
        per_symbol[symbol] = {
            "row_count": 0,
            "raw_row_count": raw_row_count_by_symbol.get(symbol, 0),
            "excluded_missing_raw_payload_ref_count": excluded_count,
            "first_ts": None,
            "last_ts": None,
            "span_days": 0.0,
            "distinct_utc_date_count": 0,
            "distinct_utc_dates": [],
            "max_gap_seconds": None,
            "min_days_required": min_days,
            "max_gap_minutes_allowed": max_gap_minutes,
            "coverage_status": "insufficient",
            "insufficient_reasons": [
                "no_traceable_rows" if traceable_only else "single_or_missing_gap_basis"
            ],
            "missing_rates": {
                "raw_payload_ref": 1.0 if excluded_count else 0.0,
                "exec_buy_price": None,
                "exec_sell_price": None,
                "oracle_ts_ms": None,
                "fee_bps": None,
                "funding_rate": None,
            },
        }

    generated = generated_at or datetime.now(UTC)
    raw_row_count = sum(raw_row_count_by_symbol.values())
    raw_payload_ref_missing_count = sum(raw_payload_ref_missing_by_symbol.values())
    summary = {
        "schema_version": "trade_xyz_quote_coverage_manifest.v1",
        "generated_at": generated.isoformat(),
        "raw_quotes_root": str(effective_raw_root),
        "requested_symbols": requested_symbols,
        "min_days_required": min_days,
        "max_gap_minutes_allowed": max_gap_minutes,
        "traceable_only": traceable_only,
        "raw_row_count": raw_row_count,
        "excluded_missing_raw_payload_ref_count": (
            raw_payload_ref_missing_count if traceable_only else 0
        ),
        "excluded_missing_raw_payload_ref_by_symbol": (
            dict(sorted(raw_payload_ref_missing_by_symbol.items())) if traceable_only else {}
        ),
        "raw_payload_ref_missing_count_all_rows": raw_payload_ref_missing_count,
        "raw_payload_ref_missing_by_symbol_all_rows": dict(
            sorted(raw_payload_ref_missing_by_symbol.items())
        ),
        "raw_payload_ref_missing_rate_all_rows": (
            raw_payload_ref_missing_count / raw_row_count if raw_row_count else 0.0
        ),
        "symbol_count": len(per_symbol),
        "row_count": len(logs),
        "coverage_passed": all(item["coverage_status"] == "pass" for item in per_symbol.values()),
        "per_symbol": per_symbol,
    }
    manifest_path = data_dir / "manifests/trade_xyz_quote_coverage_manifest.json"
    write_json(manifest_path, summary)
    return summary
