from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.frameworks import framework_adapter_status


@dataclass(frozen=True)
class BacktestExternalResult:
    external_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _aggregate_metrics(metrics_payload: dict[str, Any]) -> dict[str, Any]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    aggregate = summary.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    return {
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "stale_rejected_count": aggregate.get("stale_rejected_count"),
        "halt_rejected_count": aggregate.get("halt_rejected_count"),
    }


def _skipped_result(candidate: dict[str, Any], reason_codes: list[str]) -> dict[str, Any]:
    return {
        "framework_id": candidate["framework_id"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "run_status": "skipped",
        "reason_codes": reason_codes,
        "dependency_added": False,
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "metrics": {
            "trade_count": None,
            "total_return": None,
            "max_drawdown": None,
            "cost_drag_bps": None,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    }


def _failed_result(candidate: dict[str, Any], reason_codes: list[str]) -> dict[str, Any]:
    result = _skipped_result(candidate, reason_codes)
    result["run_status"] = "failed"
    return result


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


def _vectorbt_signal_arrays(
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


def _run_vectorbt_result(
    candidate: dict[str, Any],
    *,
    signals_path: Path | None,
    quotes_path: Path | None,
    label_horizon_minutes: int,
) -> dict[str, Any]:
    if signals_path is None or quotes_path is None:
        return _skipped_result(candidate, ["input_paths_missing"])
    if not signals_path.exists() or not quotes_path.exists():
        return _skipped_result(candidate, ["input_paths_missing"])
    try:
        vectorbt = importlib.import_module("vectorbt")
        close, entries, exits = _vectorbt_signal_arrays(
            signals_path=signals_path,
            quotes_path=quotes_path,
            label_horizon_minutes=label_horizon_minutes,
        )
        if not any(entries):
            return _skipped_result(candidate, ["no_entries_for_external_engine"])
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
        return _failed_result(candidate, ["framework_run_failed"])
    return {
        "framework_id": candidate["framework_id"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "run_status": "completed",
        "reason_codes": [],
        "dependency_added": False,
        "engine_run": True,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "metrics": {
            "trade_count": sum(1 for item in entries if item),
            "total_return": total_return,
            "max_drawdown": max_drawdown,
            "cost_drag_bps": 0.0,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    }


def _installed_without_runner_result(candidate: dict[str, Any]) -> dict[str, Any]:
    # The first external runner contract is intentionally conservative: a framework
    # must be installed before this can be swapped for a framework-specific engine call.
    return {
        "framework_id": candidate["framework_id"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "run_status": "skipped",
        "reason_codes": ["framework_runner_not_implemented"],
        "dependency_added": False,
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "metrics": {
            "trade_count": None,
            "total_return": None,
            "max_drawdown": None,
            "cost_drag_bps": None,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    }


def _external_results(
    *,
    signals_path: Path | None,
    quotes_path: Path | None,
    label_horizon_minutes: int,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for candidate in framework_adapter_status():
        if candidate["status"] != "installed":
            results.append(_skipped_result(candidate, ["not_installed_in_current_env"]))
            continue
        if candidate["framework_id"] == "vectorbt":
            results.append(
                _run_vectorbt_result(
                    candidate,
                    signals_path=signals_path,
                    quotes_path=quotes_path,
                    label_horizon_minutes=label_horizon_minutes,
                )
            )
            continue
        results.append(_installed_without_runner_result(candidate))
    return results


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest External Framework Result",
        "",
        f"- created_at: {payload['created_at']}",
        f"- source_metrics_path: `{payload['source_metrics_path']}`",
        f"- source_signals_path: `{payload['source_signals_path']}`",
        f"- source_quotes_path: `{payload['source_quotes_path']}`",
        f"- label_horizon_minutes: {payload['label_horizon_minutes']}",
        f"- dependency_added: {payload['dependency_added']}",
        f"- external_engine_run: {payload['external_engine_run']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Framework | Status | Run Status | Engine Run | Reason Codes | Trades | Total Return |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for result in payload["results"]:
        metrics = result.get("metrics") or {}
        lines.append(
            "| {framework_id} | {status} | {run_status} | {engine_run} | {reasons} | {trade_count} | {total_return} |".format(
                framework_id=result["framework_id"],
                status=result["status"],
                run_status=result["run_status"],
                engine_run=result["engine_run"],
                reasons=", ".join(result.get("reason_codes") or []) or "none",
                trade_count=metrics.get("trade_count"),
                total_return=metrics.get("total_return"),
            )
        )
    lines.extend(
        [
            "",
            "This artifact never adds dependencies and never permits live orders.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_external_result(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    signals_path: Path | None = None,
    quotes_path: Path | None = None,
    label_horizon_minutes: int = 240,
) -> BacktestExternalResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    _aggregate_metrics(metrics_payload)
    results = _external_results(
        signals_path=signals_path,
        quotes_path=quotes_path,
        label_horizon_minutes=label_horizon_minutes,
    )
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_external_result.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_metrics_path": metrics_path.as_posix(),
        "source_metrics_hash": _sha256_file(metrics_path),
        "source_signals_path": (
            signals_path.as_posix() if signals_path is not None and signals_path.exists() else None
        ),
        "source_signals_hash": (
            _sha256_file(signals_path)
            if signals_path is not None and signals_path.exists()
            else None
        ),
        "source_quotes_path": (
            quotes_path.as_posix() if quotes_path is not None and quotes_path.exists() else None
        ),
        "source_quotes_hash": (
            _sha256_file(quotes_path) if quotes_path is not None and quotes_path.exists() else None
        ),
        "label_horizon_minutes": label_horizon_minutes,
        "dependency_added": False,
        "external_engine_run": any(result["engine_run"] is True for result in results),
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "results": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    external_path = out_dir / "strategy_backtest_external_result.json"
    external_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "strategy_backtest_external_report.md", payload)
    return BacktestExternalResult(
        external_path=external_path, report_path=report_path, payload=payload
    )
