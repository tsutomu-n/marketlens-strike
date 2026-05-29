from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.real_market.providers.alpaca import (
    AlpacaNoBarsReturned,
    AlpacaProviderUnavailable,
    fetch_alpaca_bars,
)
from sis.real_market.quality import estimate_source_confidence, live_suitability_reasons
from sis.storage.jsonl_store import write_json


def _default_raw_payload_path(data_dir: Path, symbol: str, timeframe: str) -> Path:
    return data_dir / "raw/real_market/alpaca" / f"{symbol}_{timeframe}_latest.json"


def _summary_path(data_dir: Path) -> Path:
    return data_dir / "ops/alpaca_live_smoke_summary.json"


def _report_path(data_dir: Path) -> Path:
    return data_dir / "reports/alpaca_live_smoke.md"


def _write_report(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# Alpaca Live Smoke",
        "",
        f"- status: {summary.get('status')}",
        f"- provider_connectivity_status: {summary.get('provider_connectivity_status')}",
        f"- data_availability_status: {summary.get('data_availability_status')}",
        f"- symbol: {summary.get('symbol')}",
        f"- timeframe: {summary.get('timeframe')}",
        f"- feed: {summary.get('feed')}",
        f"- requested_window: {summary.get('requested_window')}",
        f"- start: {summary.get('start')}",
        f"- end: {summary.get('end')}",
        f"- bar_count: {summary.get('bar_count')}",
        f"- latest_bar_ts: {summary.get('latest_bar_ts')}",
        f"- latest_ts_start: {summary.get('latest_ts_start')}",
        f"- latest_ts_end: {summary.get('latest_ts_end')}",
        f"- market_session: {summary.get('market_session')}",
        f"- source_confidence: {summary.get('source_confidence')}",
        f"- source_confidence_reason: {summary.get('source_confidence_reason')}",
        f"- live_suitability_reasons: {summary.get('live_suitability_reasons')}",
        f"- raw_payload_path: {summary.get('raw_payload_path')}",
        f"- checked_at: {summary.get('checked_at')}",
    ]
    if summary.get("status") != "pass":
        lines.extend(
            [
                f"- error_class: {summary.get('error_class')}",
                f"- error_message: {summary.get('error_message')}",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _safe_error_message(exc: AlpacaProviderUnavailable) -> str:
    text = str(exc)
    if "credentials are not configured" in text.lower():
        return "Alpaca credentials are not configured."
    return text


def _requested_window(start: datetime | None, end: datetime | None) -> str:
    if start is None and end is None:
        return "latest"
    if start is not None and end is not None:
        return "bounded"
    if start is not None:
        return "start_only"
    return "end_only"


def _market_session(ts: datetime, *, requested_window: str) -> str:
    if requested_window != "latest":
        return "historical_window"
    aware = ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    utc_ts = aware.astimezone(timezone.utc)
    minutes = utc_ts.hour * 60 + utc_ts.minute
    is_weekday = utc_ts.weekday() < 5
    regular_open_utc_minutes = 13 * 60 + 30
    regular_close_utc_minutes = 20 * 60
    if is_weekday and regular_open_utc_minutes <= minutes <= regular_close_utc_minutes:
        return "us_equity_regular_utc_window"
    return "outside_us_equity_regular_utc_window"


def _source_confidence_reason(
    *,
    score: float,
    latest_delay_seconds: float | None,
    market_session: str,
    feed: str,
    threshold: float = 0.70,
) -> str:
    status = "pass" if score >= threshold else "blocked"
    delay_text = "unknown" if latest_delay_seconds is None else f"{latest_delay_seconds:.3f}s"
    return (
        f"{status}: score={score:.3f} threshold={threshold:.3f} "
        f"latest_delay={delay_text} feed={feed} market_session={market_session}"
    )


def run_alpaca_live_smoke(
    *,
    data_dir: Path,
    symbol: str = "NVDA",
    timeframe: str = "15m",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 1,
    feed: str = "iex",
    timeout: float = 10.0,
    raw_payload_path: Path | None = None,
    opener: Callable[..., Any] | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    checked_at = now or datetime.now(timezone.utc)
    raw_path = raw_payload_path or _default_raw_payload_path(data_dir, symbol, timeframe)
    summary_path = _summary_path(data_dir)
    report_path = _report_path(data_dir)
    requested_window = _requested_window(start, end)
    try:
        if opener is None:
            bars = fetch_alpaca_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit,
                feed=feed,
                timeout=timeout,
                raw_payload_path=raw_path,
            )
        else:
            bars = fetch_alpaca_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit,
                feed=feed,
                timeout=timeout,
                raw_payload_path=raw_path,
                opener=opener,
            )
        latest = bars[-1]
        source_confidence = estimate_source_confidence(latest, now=checked_at)
        latest_delay_seconds = max((checked_at - latest.ts_end).total_seconds(), 0.0)
        market_session = _market_session(latest.ts_end, requested_window=requested_window)
        source_confidence_reason = _source_confidence_reason(
            score=source_confidence,
            latest_delay_seconds=latest_delay_seconds,
            market_session=market_session,
            feed=feed,
        )
        reasons = live_suitability_reasons(
            source_confidence=source_confidence,
            providers=["alpaca"],
        )
        summary: dict[str, object] = {
            "status": "pass" if not reasons else "blocked",
            "provider_connectivity_status": "pass",
            "data_availability_status": "pass",
            "provider": "alpaca",
            "symbol": symbol,
            "timeframe": timeframe,
            "feed": feed,
            "requested_window": requested_window,
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
            "limit": max(1, limit),
            "bar_count": len(bars),
            "latest_bar_ts": latest.ts_end.isoformat(),
            "latest_ts_start": latest.ts_start.isoformat(),
            "latest_ts_end": latest.ts_end.isoformat(),
            "latest_close": latest.close,
            "latest_volume": latest.volume,
            "latest_delay_seconds": latest_delay_seconds,
            "market_session": market_session,
            "source_confidence": source_confidence,
            "source_confidence_reason": source_confidence_reason,
            "live_suitability_reasons": reasons,
            "raw_payload_path": str(raw_path),
            "summary_path": str(summary_path),
            "report_path": str(report_path),
            "checked_at": checked_at.isoformat(),
        }
        if reasons:
            summary["error_class"] = "AlpacaLiveSuitabilityBlocked"
            summary["error_message"] = ",".join(reasons)
    except AlpacaNoBarsReturned as exc:
        summary = {
            "status": "blocked",
            "provider_connectivity_status": "pass",
            "data_availability_status": "empty",
            "provider": "alpaca",
            "symbol": symbol,
            "timeframe": timeframe,
            "feed": feed,
            "requested_window": requested_window,
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
            "limit": max(1, limit),
            "bar_count": 0,
            "latest_bar_ts": None,
            "latest_ts_start": None,
            "latest_ts_end": None,
            "latest_delay_seconds": None,
            "market_session": "unknown",
            "source_confidence": 0.0,
            "source_confidence_reason": (
                f"blocked: no_bars feed={feed} requested_window={requested_window}"
            ),
            "live_suitability_reasons": ["BLOCK_ALPACA_NO_BARS"],
            "raw_payload_path": str(raw_path),
            "summary_path": str(summary_path),
            "report_path": str(report_path),
            "checked_at": checked_at.isoformat(),
            "error_class": exc.__class__.__name__,
            "error_message": _safe_error_message(exc),
        }
    except AlpacaProviderUnavailable as exc:
        summary = {
            "status": "failed",
            "provider_connectivity_status": "failed",
            "data_availability_status": "unknown",
            "provider": "alpaca",
            "symbol": symbol,
            "timeframe": timeframe,
            "feed": feed,
            "requested_window": requested_window,
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
            "limit": max(1, limit),
            "bar_count": 0,
            "latest_bar_ts": None,
            "latest_ts_start": None,
            "latest_ts_end": None,
            "latest_delay_seconds": None,
            "market_session": "unknown",
            "source_confidence": 0.0,
            "source_confidence_reason": (
                f"failed: provider_unavailable feed={feed} requested_window={requested_window}"
            ),
            "live_suitability_reasons": ["BLOCK_ALPACA_PROVIDER_UNAVAILABLE"],
            "raw_payload_path": str(raw_path),
            "summary_path": str(summary_path),
            "report_path": str(report_path),
            "checked_at": checked_at.isoformat(),
            "error_class": exc.__class__.__name__,
            "error_message": _safe_error_message(exc),
        }
    write_json(summary_path, summary)
    _write_report(report_path, summary)
    return summary
