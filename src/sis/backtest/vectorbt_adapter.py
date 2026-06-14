from __future__ import annotations

from datetime import datetime
import importlib
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.optional_dependencies import optional_dependency_source


def _base_result(
    candidate: dict[str, Any],
    *,
    run_status: str,
    reason_codes: list[str],
    engine_run: bool,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "framework_id": candidate["framework_id"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "framework_version": candidate.get("version"),
        "runner_mode": "temporary_or_optional_import",
        "run_status": run_status,
        "reason_codes": reason_codes,
        "dependency_added": False,
        "dependency_source": optional_dependency_source(
            candidate, extra_name="vectorbt", dependency_prefixes={"vectorbt"}
        ),
        "engine_run": engine_run,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "metrics": metrics
        or {
            "trade_count": None,
            "total_return": None,
            "max_drawdown": None,
            "cost_drag_bps": None,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    }


def _scalar(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return value
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _scalar(item())
        except Exception:
            return None
    return None


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _first_index_at_or_after(rows: list[dict[str, Any]], symbol: str, ts: datetime) -> int | None:
    for index, row in enumerate(rows):
        if row["symbol"] == symbol and row["ts"] >= ts:
            return index
    return None


def vectorbt_signal_arrays(
    *, signals_path: Path, quotes_path: Path, label_horizon_minutes: int
) -> tuple[list[float], list[bool], list[bool]]:
    signals = pl.read_parquet(signals_path).to_dicts()
    quote_rows: list[dict[str, Any]] = []
    for row in pl.read_parquet(quotes_path).to_dicts():
        price = row.get("mark_price")
        if price is None:
            price = row.get("mid_price")
        if price is None:
            continue
        quote_rows.append(
            {
                "ts": _parse_dt(row["ts_client"]),
                "symbol": str(row.get("canonical_symbol") or row.get("venue_symbol") or ""),
                "price": float(price),
            }
        )
    quote_rows.sort(key=lambda item: (item["symbol"], item["ts"]))
    close = [float(row["price"]) for row in quote_rows]
    entries = [False for _row in quote_rows]
    exits = [False for _row in quote_rows]
    horizon_seconds = label_horizon_minutes * 60
    for signal in signals:
        if str(signal.get("side") or "").lower() != "long":
            continue
        symbol = str(signal.get("execution_symbol") or signal.get("canonical_symbol") or "")
        ts_signal = _parse_dt(signal["ts_signal"])
        entry_index = _first_index_at_or_after(quote_rows, symbol, ts_signal)
        exit_index = _first_index_at_or_after(
            quote_rows,
            symbol,
            datetime.fromtimestamp(ts_signal.timestamp() + horizon_seconds, tz=ts_signal.tzinfo),
        )
        if entry_index is None or exit_index is None or exit_index <= entry_index:
            continue
        entries[entry_index] = True
        exits[exit_index] = True
    return close, entries, exits


def run_vectorbt_result(
    candidate: dict[str, Any],
    *,
    signals_path: Path | None,
    quotes_path: Path | None,
    label_horizon_minutes: int,
) -> dict[str, Any]:
    if signals_path is None or quotes_path is None:
        return _base_result(
            candidate,
            run_status="skipped",
            reason_codes=["input_paths_missing"],
            engine_run=False,
        )
    if not signals_path.exists() or not quotes_path.exists():
        return _base_result(
            candidate,
            run_status="skipped",
            reason_codes=["input_paths_missing"],
            engine_run=False,
        )
    try:
        vectorbt = importlib.import_module("vectorbt")
        close, entries, exits = vectorbt_signal_arrays(
            signals_path=signals_path,
            quotes_path=quotes_path,
            label_horizon_minutes=label_horizon_minutes,
        )
        if not any(entries):
            return _base_result(
                candidate,
                run_status="skipped",
                reason_codes=["no_entries_for_external_engine"],
                engine_run=False,
            )
        portfolio = vectorbt.Portfolio.from_signals(
            close,
            entries,
            exits,
            init_cash=100_000.0,
            fees=0.0,
        )
        total_return = _scalar(portfolio.total_return())
        max_drawdown = _scalar(portfolio.max_drawdown())
    except Exception:
        return _base_result(
            candidate,
            run_status="failed",
            reason_codes=["framework_run_failed"],
            engine_run=False,
        )
    return _base_result(
        candidate,
        run_status="completed",
        reason_codes=[],
        engine_run=True,
        metrics={
            "trade_count": sum(1 for item in entries if item),
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "cost_drag_bps": 0.0,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    )
