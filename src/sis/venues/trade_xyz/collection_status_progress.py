from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast

from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH


def format_counts(counts: dict[str, int]) -> str:
    return ",".join(f"{key}:{value}" for key, value in sorted(counts.items()))


def coverage_progress(coverage: dict[str, Any] | None) -> dict[str, Any]:
    if coverage is None:
        return {
            "coverage_passed": False,
            "reason": "missing trade_xyz_quote_coverage_manifest.json",
            "symbols": {},
            "estimated_max_collection_days_required": None,
            "min_span_days": None,
            "max_span_days": None,
            "max_remaining_days_exact": None,
            "completion_ratio_by_span": None,
            "slowest_symbols": [],
        }
    per_symbol_value = coverage.get("per_symbol")
    per_symbol = (
        cast(dict[str, Any], per_symbol_value) if isinstance(per_symbol_value, dict) else {}
    )
    symbols: dict[str, Any] = {}
    max_days = 0
    min_span_days: float | None = None
    max_span_days = 0.0
    max_remaining_days_exact = 0.0
    slowest_symbols: list[str] = []
    for symbol, item in sorted(per_symbol.items()):
        if not isinstance(item, dict):
            continue
        min_days = float(item.get("min_days_required") or 0.0)
        span_days = float(item.get("span_days") or 0.0)
        remaining = max(0.0, min_days - span_days)
        remaining_ceiling = int(remaining) if remaining.is_integer() else int(remaining) + 1
        max_days = max(max_days, remaining_ceiling)
        max_span_days = max(max_span_days, span_days)
        min_span_days = span_days if min_span_days is None else min(min_span_days, span_days)
        if remaining > max_remaining_days_exact:
            max_remaining_days_exact = remaining
            slowest_symbols = [symbol]
        elif remaining == max_remaining_days_exact:
            slowest_symbols.append(symbol)
        symbols[symbol] = {
            "coverage_status": item.get("coverage_status"),
            "row_count": item.get("row_count"),
            "raw_row_count": item.get("raw_row_count"),
            "span_days": span_days,
            "min_days_required": min_days,
            "max_gap_seconds": item.get("max_gap_seconds"),
            "estimated_collection_days_required": remaining_ceiling,
            "insufficient_reasons": item.get("insufficient_reasons", []),
            "missing_rates": item.get("missing_rates", {}),
            "excluded_missing_raw_payload_ref_count": item.get(
                "excluded_missing_raw_payload_ref_count"
            ),
        }
    return {
        "coverage_passed": bool(coverage.get("coverage_passed")),
        "traceable_only": coverage.get("traceable_only"),
        "row_count": coverage.get("row_count"),
        "raw_row_count": coverage.get("raw_row_count"),
        "excluded_missing_raw_payload_ref_count": coverage.get(
            "excluded_missing_raw_payload_ref_count"
        ),
        "raw_payload_ref_missing_rate_all_rows": coverage.get(
            "raw_payload_ref_missing_rate_all_rows"
        ),
        "estimated_max_collection_days_required": max_days,
        "min_span_days": min_span_days,
        "max_span_days": max_span_days,
        "max_remaining_days_exact": max_remaining_days_exact,
        "completion_ratio_by_span": (
            max_span_days / max(max_span_days + max_remaining_days_exact, 1e-12)
        ),
        "slowest_symbols": slowest_symbols,
        "symbols": symbols,
    }


def parse_generated_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def progress_since_previous(
    previous_status: dict[str, Any] | None,
    *,
    generated_at: datetime,
    raw_inventory: dict[str, Any],
    coverage: dict[str, Any],
    collector_process: dict[str, Any],
    latest_file_stale: bool,
    interval_seconds: int,
) -> dict[str, Any]:
    if previous_status is None:
        return {
            "previous_status_exists": False,
            "seconds_since_previous_status": None,
            "row_count_delta": None,
            "traceable_row_count_delta": None,
            "status": "unknown_no_previous_status",
            "warnings": [],
        }
    previous_generated_at = parse_generated_at(previous_status.get("generated_at"))
    previous_inventory_value = previous_status.get("raw_quote_inventory")
    previous_inventory = (
        cast(dict[str, Any], previous_inventory_value)
        if isinstance(previous_inventory_value, dict)
        else {}
    )
    previous_rows = int(previous_inventory.get("row_count") or 0)
    previous_traceable = int(previous_inventory.get("traceable_row_count") or 0)
    current_rows = int(raw_inventory.get("row_count") or 0)
    current_traceable = int(raw_inventory.get("traceable_row_count") or 0)
    seconds_since_previous = (
        max(0.0, (generated_at - previous_generated_at).total_seconds())
        if previous_generated_at is not None
        else None
    )
    row_delta = current_rows - previous_rows
    traceable_delta = current_traceable - previous_traceable
    warnings: list[str] = []
    if latest_file_stale:
        warnings.append("latest_file_stale")
    if not collector_process.get("running") and not coverage.get("coverage_passed"):
        warnings.append("collector_not_running_while_coverage_incomplete")
    if (
        collector_process.get("running")
        and seconds_since_previous is not None
        and seconds_since_previous >= interval_seconds * 2
        and traceable_delta <= 0
    ):
        warnings.append("no_traceable_row_growth_since_previous_status")
    return {
        "previous_status_exists": True,
        "seconds_since_previous_status": seconds_since_previous,
        "row_count_delta": row_delta,
        "traceable_row_count_delta": traceable_delta,
        "status": "warning" if warnings else "collecting_ok",
        "warnings": warnings,
    }


def cycle_command(symbols: list[str], *, duration_minutes: int, interval_seconds: int) -> str:
    command = (
        "uv run sis collect-trade-xyz-data-cycle "
        f"--collection-config {DEFAULT_COLLECTION_CONFIG_PATH} "
        f"--duration-minutes {duration_minutes} --interval-seconds {interval_seconds}"
    )
    if symbols:
        command += f" --symbols {','.join(symbols)}"
    return command
