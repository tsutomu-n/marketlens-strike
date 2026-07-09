from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, cast

import polars as pl

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.funding_source import build_funding_source_status
from sis.crypto_perp.io import write_json_artifact, write_text_artifact
from sis.crypto_perp.models import stable_hash
from sis.crypto_perp.real_market_no_cash_sample import (
    HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE,
    _eligible_indices,
    _real_market_ticker_reason,
    _source_root_candle_rows,
)
from sis.crypto_perp.ticker_source import (
    HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE,
    TICKER_SOURCE_STALE,
    build_ticker_source_status,
)


REAL_MARKET_TICKER_COVERAGE_STATUS_SCHEMA_VERSION = (
    "crypto_perp_real_market_ticker_coverage_status.v1"
)
REAL_MARKET_TICKER_COVERAGE_STATUS_PRODUCER = "crypto-perp-real-market-ticker-coverage-status"

TickerCoverageDecision = Literal[
    "COLLECT_TICKER_SNAPSHOTS",
    "READY_FOR_TICKER_REQUIRED_SAMPLE",
    "SOURCE_ROOT_MISSING",
    "NO_CANDLES",
    "NO_TICKER_ROWS",
]


@dataclass(frozen=True)
class RealMarketTickerCoverageStatusResult:
    decision: TickerCoverageDecision
    coverage_passed: bool
    ticker_covered_candidate_count: int
    target_event_count: int
    json_path: Path
    markdown_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class _CoverageEvent:
    canonical_symbol: str
    information_cutoff_at: datetime


def write_real_market_ticker_coverage_status(
    *,
    source_root: Path,
    out_dir: Path,
    created_at: datetime | str,
    symbol: str = "BTCUSDT",
    target_event_count: int = 30,
    ticker_max_staleness_seconds: int = 900,
    lookback_minutes: int = 60,
    horizon_minutes: int = 60,
    interval_minutes: int = 5,
) -> RealMarketTickerCoverageStatusResult:
    payload = build_real_market_ticker_coverage_status(
        source_root=source_root,
        created_at=created_at,
        symbol=symbol,
        target_event_count=target_event_count,
        ticker_max_staleness_seconds=ticker_max_staleness_seconds,
        lookback_minutes=lookback_minutes,
        horizon_minutes=horizon_minutes,
        interval_minutes=interval_minutes,
    )
    json_path = out_dir / "ticker_coverage_status.json"
    markdown_path = out_dir / "ticker_coverage_status.md"
    write_json_artifact(json_path, payload)
    write_text_artifact(markdown_path, _render_markdown(payload))
    return RealMarketTickerCoverageStatusResult(
        decision=cast(TickerCoverageDecision, payload["decision"]),
        coverage_passed=bool(payload["coverage_passed"]),
        ticker_covered_candidate_count=int(payload["ticker_covered_candidate_count"]),
        target_event_count=int(payload["target_event_count"]),
        json_path=json_path,
        markdown_path=markdown_path,
        payload=payload,
    )


def build_real_market_ticker_coverage_status(
    *,
    source_root: Path,
    created_at: datetime | str,
    symbol: str = "BTCUSDT",
    target_event_count: int = 30,
    ticker_max_staleness_seconds: int = 900,
    lookback_minutes: int = 60,
    horizon_minutes: int = 60,
    interval_minutes: int = 5,
) -> dict[str, Any]:
    if target_event_count < 1:
        raise ValueError("target_event_count must be positive")
    if ticker_max_staleness_seconds < 0:
        raise ValueError("ticker_max_staleness_seconds must be non-negative")
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be positive")
    if lookback_minutes < interval_minutes or horizon_minutes < interval_minutes:
        raise ValueError("lookback_minutes and horizon_minutes must be at least interval_minutes")

    created = ensure_utc_aware("created_at", created_at)
    root = source_root.expanduser()
    symbol_upper = symbol.upper()
    base = _base_payload(
        created_at=created,
        source_root=root,
        symbol=symbol_upper,
        target_event_count=target_event_count,
        ticker_max_staleness_seconds=ticker_max_staleness_seconds,
        lookback_minutes=lookback_minutes,
        horizon_minutes=horizon_minutes,
        interval_minutes=interval_minutes,
    )
    if not root.exists():
        return _finish_payload(
            base,
            decision="SOURCE_ROOT_MISSING",
            next_command=_append_refresh_command(root, symbol_upper),
        )

    try:
        rows = _source_root_candle_rows(root, symbol_upper)
        lookback_bars = max(1, lookback_minutes // interval_minutes)
        horizon_bars = max(1, horizon_minutes // interval_minutes)
        candidate_indices = _eligible_indices(len(rows), lookback_bars, horizon_bars)
    except ValueError:
        return _finish_payload(
            base,
            decision="NO_CANDLES",
            next_command=_append_refresh_command(root, symbol_upper),
        )

    ticker_inventory = _ticker_inventory(root, symbol_upper, created)
    base["candidate_window_count"] = len(candidate_indices)
    base["latest_ticker_ts_received_ms"] = ticker_inventory["latest_ticker_ts_received_ms"]
    base["latest_ticker_age_seconds"] = ticker_inventory["latest_ticker_age_seconds"]
    base["valid_bid_ask_row_count"] = ticker_inventory["valid_bid_ask_row_count"]
    base["ticker_row_count"] = ticker_inventory["ticker_row_count"]

    if ticker_inventory["ticker_row_count"] == 0:
        base["missing_reason_counts"][HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE] = len(
            candidate_indices
        )
        return _finish_payload(
            base,
            decision="NO_TICKER_ROWS",
            next_command=_append_refresh_command(root, symbol_upper),
        )

    covered_count = 0
    funding_available_count = 0
    for row_index in candidate_indices:
        cutoff = ensure_utc_aware("information_cutoff_at", rows[row_index]["available_at"])
        event = cast(
            Any,
            _CoverageEvent(
                canonical_symbol=symbol_upper,
                information_cutoff_at=cutoff,
            ),
        )
        ticker_status = build_ticker_source_status(
            event=event,
            source_root=root,
            max_staleness_seconds=ticker_max_staleness_seconds,
        )
        if ticker_status.row_count > 0:
            covered_count += 1
        else:
            reason = _real_market_ticker_reason(ticker_status.reason)
            base["missing_reason_counts"][reason] = base["missing_reason_counts"].get(reason, 0) + 1
        funding_status = build_funding_source_status(event=event, source_root=root)
        if funding_status.row_count > 0:
            funding_available_count += 1

    base["ticker_covered_candidate_count"] = covered_count
    base["funding_available_candidate_count"] = funding_available_count
    if covered_count >= target_event_count:
        return _finish_payload(
            base,
            decision="READY_FOR_TICKER_REQUIRED_SAMPLE",
            next_command=_ticker_required_sample_command(
                root,
                target_event_count=target_event_count,
                ticker_max_staleness_seconds=ticker_max_staleness_seconds,
            ),
        )
    return _finish_payload(
        base,
        decision="COLLECT_TICKER_SNAPSHOTS",
        next_command=_append_refresh_command(root, symbol_upper),
    )


def _base_payload(
    *,
    created_at: datetime,
    source_root: Path,
    symbol: str,
    target_event_count: int,
    ticker_max_staleness_seconds: int,
    lookback_minutes: int,
    horizon_minutes: int,
    interval_minutes: int,
) -> dict[str, Any]:
    return {
        "schema_version": REAL_MARKET_TICKER_COVERAGE_STATUS_SCHEMA_VERSION,
        "artifact_id": stable_hash(
            [
                REAL_MARKET_TICKER_COVERAGE_STATUS_SCHEMA_VERSION,
                source_root.as_posix(),
                symbol,
                serialize_utc_z(created_at),
            ]
        ),
        "created_at": serialize_utc_z(created_at),
        "producer": {"tool": "sis", "command": REAL_MARKET_TICKER_COVERAGE_STATUS_PRODUCER},
        "source_root": source_root.as_posix(),
        "symbol": symbol,
        "target_event_count": target_event_count,
        "ticker_max_staleness_seconds": ticker_max_staleness_seconds,
        "lookback_minutes": lookback_minutes,
        "horizon_minutes": horizon_minutes,
        "interval_minutes": interval_minutes,
        "candidate_window_count": 0,
        "ticker_covered_candidate_count": 0,
        "funding_available_candidate_count": 0,
        "coverage_passed": False,
        "missing_reason_counts": {
            HISTORICAL_TICKER_SOURCE_NOT_AVAILABLE: 0,
            TICKER_SOURCE_STALE: 0,
            HISTORICAL_TICKER_BID_ASK_NOT_AVAILABLE: 0,
        },
        "latest_ticker_ts_received_ms": None,
        "latest_ticker_age_seconds": None,
        "valid_bid_ask_row_count": 0,
        "ticker_row_count": 0,
        "next_actions": [],
        "boundary_flags": _boundary_flags(),
    }


def _finish_payload(
    payload: dict[str, Any],
    *,
    decision: TickerCoverageDecision,
    next_command: str,
) -> dict[str, Any]:
    coverage_passed = decision == "READY_FOR_TICKER_REQUIRED_SAMPLE"
    payload["decision"] = decision
    payload["coverage_passed"] = coverage_passed
    payload["next_actions"] = [
        {
            "key": (
                "run_ticker_required_sample" if coverage_passed else "append_public_ticker_snapshot"
            ),
            "command": next_command,
            "network_allowed": not coverage_passed,
            "exchange_write_allowed": False,
            "live_order_allowed": False,
        }
    ]
    return payload


def _ticker_inventory(source_root: Path, symbol: str, created_at: datetime) -> dict[str, Any]:
    paths = sorted(
        (source_root / "data" / "ticker_rows").glob(
            f"exchange=*/symbol={symbol}/date=*/ticker_rows.parquet"
        )
    )
    frames: list[pl.DataFrame] = []
    for path in paths:
        frame = pl.read_parquet(path)
        if "symbol_canonical" not in frame.columns or "ts_received_ms" not in frame.columns:
            continue
        frames.append(
            frame.with_columns(
                pl.col("symbol_canonical").cast(pl.Utf8).str.to_uppercase(),
                pl.col("ts_received_ms").cast(pl.Int64),
            ).filter(pl.col("symbol_canonical") == symbol)
        )
    if not frames:
        return _empty_ticker_inventory()
    rows = pl.concat(frames, how="vertical_relaxed")
    if rows.is_empty():
        return _empty_ticker_inventory()
    latest_value = rows.select(pl.col("ts_received_ms").max()).item()
    if latest_value is None:
        return _empty_ticker_inventory()
    latest = int(cast(int, latest_value))
    valid_bid_ask_count = 0
    if "bid_px" in rows.columns and "ask_px" in rows.columns:
        valid_bid_ask_count = rows.filter(
            pl.col("bid_px").is_not_null()
            & pl.col("ask_px").is_not_null()
            & (pl.col("bid_px").cast(pl.Float64) > 0)
            & (pl.col("ask_px").cast(pl.Float64) > 0)
            & (pl.col("ask_px").cast(pl.Float64) >= pl.col("bid_px").cast(pl.Float64))
        ).height
    created_ms = int(created_at.timestamp() * 1000)
    return {
        "ticker_row_count": rows.height,
        "valid_bid_ask_row_count": valid_bid_ask_count,
        "latest_ticker_ts_received_ms": latest,
        "latest_ticker_age_seconds": (created_ms - latest) / 1000,
    }


def _empty_ticker_inventory() -> dict[str, Any]:
    return {
        "ticker_row_count": 0,
        "valid_bid_ask_row_count": 0,
        "latest_ticker_ts_received_ms": None,
        "latest_ticker_age_seconds": None,
    }


def _append_refresh_command(source_root: Path, symbol: str) -> str:
    out_dir = source_root.parent if source_root.name == "source_root" else source_root
    return (
        "SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis "
        "strategy-idea-candidates-bitget-source-refresh "
        f"--symbol {symbol} "
        "--product-type USDT-FUTURES "
        "--granularity 5m "
        "--limit 200 "
        f"--out {out_dir.as_posix()} "
        "--append-existing"
    )


def _ticker_required_sample_command(
    source_root: Path,
    *,
    target_event_count: int,
    ticker_max_staleness_seconds: int,
) -> str:
    return (
        "uv run sis crypto-perp-real-market-no-cash-sample "
        f"--source-root {source_root.as_posix()} "
        "--require-ticker-coverage "
        f"--ticker-max-staleness-seconds {ticker_max_staleness_seconds} "
        f"--target-event-count {target_event_count} "
        "--out data/crypto_perp/real_market_no_cash/latest"
    )


def _boundary_flags() -> dict[str, bool]:
    return {
        "network_attempted": False,
        "credentialed_exchange_api_used": False,
        "paper_permission_granted": False,
        "paper_order_created": False,
        "actual_cash_used": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "profit_proven": False,
    }


def _render_markdown(payload: dict[str, Any]) -> str:
    next_command = payload["next_actions"][0]["command"] if payload["next_actions"] else ""
    return f"""# Real-Market Ticker Coverage Status

## Summary

- decision: `{payload["decision"]}`
- coverage_passed: `{str(payload["coverage_passed"]).lower()}`
- ticker_covered_candidate_count: `{payload["ticker_covered_candidate_count"]}`
- target_event_count: `{payload["target_event_count"]}`
- valid_bid_ask_row_count: `{payload["valid_bid_ask_row_count"]}`

## Missing Reasons

```json
{payload["missing_reason_counts"]}
```

## Next Action

```bash
{next_command}
```

This artifact does not grant Paper Observation, paper order permission, actual cash readiness, live readiness, wallet/signing use, exchange write, or profit proof.
"""
