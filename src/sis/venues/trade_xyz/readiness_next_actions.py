from __future__ import annotations

import math
from typing import Any, cast

from sis.venues.trade_xyz.collection_config import DEFAULT_COLLECTION_CONFIG_PATH
from sis.venues.trade_xyz.collection_config import join_csv
from sis.venues.trade_xyz.collection_config import load_trade_xyz_data_collection_config


def _dict_or_empty(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _quote_coverage_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "quote_coverage" or requirement["status"] != "fail":
        return None
    details = _dict_or_empty(requirement.get("details"))
    per_symbol = _dict_or_empty(details.get("per_symbol"))
    failing_symbols = [
        symbol
        for symbol, item in sorted(per_symbol.items())
        if isinstance(item, dict) and item.get("coverage_status") != "pass"
    ]
    reasons: dict[str, list[str]] = {}
    missing_rates: dict[str, dict[str, Any]] = {}
    additional_days_required: dict[str, float] = {}
    estimated_collection_days_required: dict[str, int] = {}
    traceable_only = bool(details.get("traceable_only"))
    excluded_missing_raw_payload_ref_by_symbol = _dict_or_empty(
        details.get("excluded_missing_raw_payload_ref_by_symbol")
    )
    for symbol in failing_symbols:
        item = per_symbol.get(symbol, {})
        if not isinstance(item, dict):
            continue
        reasons[symbol] = list(item.get("insufficient_reasons") or [])
        missing_rates[symbol] = dict(item.get("missing_rates") or {})
        min_days = float(item.get("min_days_required") or 0.0)
        span_days = float(item.get("span_days") or 0.0)
        additional = max(0.0, min_days - span_days)
        additional_days_required[symbol] = additional
        estimated_collection_days_required[symbol] = math.ceil(additional)
    command = (
        "uv run sis collect-trade-xyz-data-cycle --duration-minutes 1440 --interval-seconds 60"
    )
    if failing_symbols:
        command += f" --symbols {','.join(failing_symbols)}"
    estimated_max_days = max(estimated_collection_days_required.values(), default=0)
    return {
        "key": "collect_quote_coverage",
        "reason": "quote coverage is insufficient",
        "command": command,
        "follow_up_command": "uv run sis trade-xyz-collection-status --fail-on-not-ready",
        "symbols": failing_symbols,
        "recommended_collection_duration_minutes": 1440,
        "recommended_interval_seconds": 60,
        "estimated_max_collection_days_required": estimated_max_days,
        "additional_days_required_by_symbol": additional_days_required,
        "estimated_collection_days_required_by_symbol": estimated_collection_days_required,
        "insufficient_reasons_by_symbol": reasons,
        "missing_rates_by_symbol": missing_rates,
        "traceable_only": traceable_only,
        "excluded_missing_raw_payload_ref_count": details.get(
            "excluded_missing_raw_payload_ref_count"
        ),
        "excluded_missing_raw_payload_ref_by_symbol": excluded_missing_raw_payload_ref_by_symbol,
        "notes": [
            "Run the one-day data cycle repeatedly until coverage_passed=true",
            "Use collect-trade-xyz-data-cycle rather than quote-only collection so bundle/readiness artifacts are regenerated after quotes",
            "Old raw rows with missing raw_payload_ref should not be patched in place",
            "When traceable_only=true, old untraceable rows are excluded from coverage and recorded in excluded_missing_raw_payload_ref_*",
        ],
    }


def _funding_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "funding_events" or requirement["status"] == "pass":
        return None
    return {
        "key": "collect_funding_history",
        "reason": requirement.get("reason"),
        "command": "uv run sis build-trade-xyz-data-bundle --auto-funding-window",
        "notes": [
            "This collects public fundingHistory for the raw quote time range and joins nearest quote oracle_price",
            "Inspect funding_history_join_manifest.json skipped.missing_oracle_quote_within_lag after the run",
        ],
    }


def _real_market_reference_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "real_market_reference" or requirement["status"] != "fail":
        return None
    command = "uv run sis collect-trade-xyz-real-market-reference --period-days 365 --interval 1d"
    try:
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
        if config.usable_start_date is not None:
            command = (
                "uv run sis collect-trade-xyz-real-market-reference "
                f"--start {config.usable_start_date} --interval 1d"
            )
    except (FileNotFoundError, ValueError):
        pass
    return {
        "key": "collect_real_market_reference",
        "reason": requirement.get("reason"),
        "command": command,
        "notes": [
            "This collects read-only real-market reference bars from Trade[XYZ] registry real_market_symbol mappings",
            "yfinance output is research/backtest reference data, not live execution data",
        ],
    }


def _signal_candles_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "signal_candles" or requirement["status"] != "fail":
        return None
    details = _dict_or_empty(requirement.get("details"))
    request_errors = details.get("request_errors")
    failed_symbols: set[str] = set()
    failed_intervals: set[str] = set()
    if isinstance(request_errors, list):
        for item in request_errors:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("canonical_symbol") or "").strip().upper()
            interval = str(item.get("interval") or "").strip()
            if symbol:
                failed_symbols.add(symbol)
            if interval:
                failed_intervals.add(interval)

    request_delay_seconds = 1.5
    period_days = 365
    intervals = ("30m", "4h", "1d", "3d")
    try:
        config = load_trade_xyz_data_collection_config(DEFAULT_COLLECTION_CONFIG_PATH)
        intervals = config.signal_candle_intervals
        period_days = config.signal_candle_period_days
        request_delay_seconds = config.signal_candle_request_delay_seconds
    except (FileNotFoundError, ValueError):
        config = None

    retry_delay_seconds = (
        max(request_delay_seconds * 2, 3.0) if failed_symbols else request_delay_seconds
    )
    if failed_intervals:
        ordered_failed_intervals = [
            interval for interval in intervals if interval in failed_intervals
        ]
        extra_failed_intervals = sorted(failed_intervals - set(ordered_failed_intervals))
        effective_intervals = tuple([*ordered_failed_intervals, *extra_failed_intervals])
    else:
        effective_intervals = intervals
    command = (
        "uv run sis collect-trade-xyz-signal-candles "
        f"--intervals {join_csv(effective_intervals)} "
        f"--period-days {period_days} "
        f"--request-delay-seconds {retry_delay_seconds:g}"
    )
    if failed_symbols:
        command += f" --symbols {join_csv(sorted(failed_symbols))}"
    if config is not None and config.usable_start_date is not None:
        command += f" --start {config.usable_start_date}"
    return {
        "key": "collect_signal_candles",
        "reason": requirement.get("reason"),
        "command": command,
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "notes": [
            "This collects historical candleSnapshot OHLCV for signal inputs",
            "Do not use signal candles as fill snapshots; fill modeling uses quote snapshots",
        ],
    }


def _account_fee_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "account_specific_fee" or requirement["status"] != "known_gap":
        return None
    return {
        "key": "collect_account_fee",
        "reason": requirement.get("reason"),
        "command": "uv run sis collect-trade-xyz-account-fee --user-address 0x...",
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "notes": [
            "This uses the read-only Hyperliquid /info userFees request",
            "Use a public Hyperliquid user address; no wallet secret, signing, live order, or exchange write is required",
            "For long-running collection, set SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS before scripts/collect_trade_xyz_data_cycle.sh",
            "builder_fee_bps still requires a specific builder address and is not inferred from userFees",
        ],
    }


def _oracle_timestamp_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "oracle_timestamp_provenance" or requirement["status"] == "pass":
        return None
    return {
        "key": "check_oracle_timestamp_provenance",
        "reason": requirement.get("reason"),
        "command": "uv run sis build-trade-xyz-reference-data",
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "details": requirement.get("details", {}),
        "notes": [
            "Rebuild oracle timestamp provenance from current raw quote logs",
            "Do not fill oracle_ts_ms from source_ts_ms, recv_ts, or client timestamp",
            "If the source payload does not expose oracle timestamp, keep the missing reason and treat it as a known gap",
        ],
    }


def _session_state_next_action(requirement: dict[str, Any]) -> dict[str, Any] | None:
    if requirement["key"] != "session_state" or requirement["status"] == "pass":
        return None
    return {
        "key": "build_session_state",
        "reason": requirement.get("reason"),
        "command": "uv run sis build-trade-xyz-session-state",
        "follow_up_command": "uv run sis build-trade-xyz-data-readiness",
        "details": requirement.get("details", {}),
        "notes": [
            "Build session state observations from raw Trade[XYZ] quote rows",
            "Do not interpret missing internal_session_open or maintenance_window as open/closed",
            "Unsupported symbols remain a known gap until a Trade[XYZ] session spec is added",
        ],
    }


def build_next_actions(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for requirement in requirements:
        quote_action = _quote_coverage_next_action(requirement)
        if quote_action is not None:
            actions.append(quote_action)
        funding_action = _funding_next_action(requirement)
        if funding_action is not None:
            actions.append(funding_action)
        real_market_action = _real_market_reference_next_action(requirement)
        if real_market_action is not None:
            actions.append(real_market_action)
        signal_candles_action = _signal_candles_next_action(requirement)
        if signal_candles_action is not None:
            actions.append(signal_candles_action)
        session_action = _session_state_next_action(requirement)
        if session_action is not None:
            actions.append(session_action)
        account_fee_action = _account_fee_next_action(requirement)
        if account_fee_action is not None:
            actions.append(account_fee_action)
        oracle_action = _oracle_timestamp_next_action(requirement)
        if oracle_action is not None:
            actions.append(oracle_action)
    return actions
