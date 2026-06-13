from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


DEFAULT_WINDOW_CSV = "3,5"


@dataclass(frozen=True)
class BacktestRollingStabilityResult:
    rolling_stability_path: Path
    report_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReturnRow:
    index: int
    signal_return: float


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


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def parse_rolling_windows(raw: str) -> list[int]:
    windows: list[int] = []
    seen: set[int] = set()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        try:
            window = int(item)
        except ValueError as exc:
            raise ValueError(f"rolling window must be an integer: {item}") from exc
        if window <= 0:
            raise ValueError("rolling window must be > 0")
        if window in seen:
            raise ValueError(f"duplicate rolling window: {window}")
        windows.append(window)
        seen.add(window)
    if not windows:
        raise ValueError("at least one rolling window is required")
    return windows


def _rows(metrics_payload: dict[str, Any]) -> list[ReturnRow]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    rows: list[ReturnRow] = []
    for index, raw in enumerate(summary.get("executed_signal_results") or []):
        if not isinstance(raw, dict):
            continue
        signal_return = _numeric(raw.get("signal_return"))
        if signal_return is None:
            continue
        rows.append(ReturnRow(index=index, signal_return=signal_return))
    return rows


def _max_drawdown(returns: list[float]) -> float | None:
    if not returns:
        return None
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for item in returns:
        equity *= 1.0 + item
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, equity / peak - 1.0)
    return max_drawdown


def _positive_rate(returns: list[float]) -> float | None:
    if not returns:
        return None
    return sum(1 for item in returns if item > 0) / len(returns)


def _window_payload(*, window_size: int, rows: list[ReturnRow], start: int) -> dict[str, Any]:
    window_rows = rows[start : start + window_size]
    returns = [row.signal_return for row in window_rows]
    total_return = sum(returns)
    return {
        "window_size": window_size,
        "start_index": window_rows[0].index,
        "end_index": window_rows[-1].index,
        "return_count": len(window_rows),
        "total_return": total_return,
        "avg_signal_return": total_return / len(returns) if returns else None,
        "min_signal_return": min(returns) if returns else None,
        "max_signal_return": max(returns) if returns else None,
        "positive_rate": _positive_rate(returns),
        "max_drawdown": _max_drawdown(returns),
        "source_row_indices": [row.index for row in window_rows],
    }


def _window_group_payload(*, window_size: int, rows: list[ReturnRow]) -> dict[str, Any]:
    rolling_windows = [
        _window_payload(window_size=window_size, rows=rows, start=start)
        for start in range(0, max(len(rows) - window_size + 1, 0))
    ]
    totals = [float(item["total_return"]) for item in rolling_windows]
    worst = min(rolling_windows, key=lambda item: float(item["total_return"]), default=None)
    return {
        "window_size": window_size,
        "window_count": len(rolling_windows),
        "min_total_return": min(totals) if totals else None,
        "max_total_return": max(totals) if totals else None,
        "avg_total_return": sum(totals) / len(totals) if totals else None,
        "positive_total_return_rate": _positive_rate(totals),
        "worst_window_start_index": worst["start_index"] if worst is not None else None,
        "worst_window_end_index": worst["end_index"] if worst is not None else None,
        "worst_window_total_return": worst["total_return"] if worst is not None else None,
        "worst_window_max_drawdown": worst["max_drawdown"] if worst is not None else None,
        "rolling_windows": rolling_windows,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    summary = payload["summary"]
    lines = [
        "# Strategy Backtest Rolling Stability",
        "",
        f"- stability_kind: {payload['stability_kind']}",
        f"- source_backtest_metrics_path: `{payload['source_backtest_metrics_path']}`",
        f"- return_count: {summary['return_count']}",
        f"- window_count: {summary['window_count']}",
        f"- worst_window_size: {summary['worst_window_size']}",
        f"- worst_window_start_index: {summary['worst_window_start_index']}",
        f"- worst_window_end_index: {summary['worst_window_end_index']}",
        f"- worst_window_total_return: {summary['worst_window_total_return']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Window | Count | Min Total Return | Max Total Return | Avg Total Return | Positive Rate | Worst Total Return | Worst Max DD |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for window in payload["windows"]:
        lines.append(
            "| {window_size} | {window_count} | {min_total_return} | {max_total_return} | {avg_total_return} | {positive_total_return_rate} | {worst_window_total_return} | {worst_window_max_drawdown} |".format(
                window_size=window["window_size"],
                window_count=window["window_count"],
                min_total_return=window["min_total_return"],
                max_total_return=window["max_total_return"],
                avg_total_return=window["avg_total_return"],
                positive_total_return_rate=window["positive_total_return_rate"],
                worst_window_total_return=window["worst_window_total_return"],
                worst_window_max_drawdown=window["worst_window_max_drawdown"],
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_rolling_stability(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    window_csv: str = DEFAULT_WINDOW_CSV,
) -> BacktestRollingStabilityResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    rows = _rows(metrics_payload)
    windows = [
        _window_group_payload(window_size=window, rows=rows)
        for window in parse_rolling_windows(window_csv)
    ]
    all_windows = [
        rolling_window
        for window in windows
        for rolling_window in window["rolling_windows"]
        if rolling_window["return_count"] > 0
    ]
    worst = min(all_windows, key=lambda item: float(item["total_return"]), default=None)
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_rolling_stability.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "stability_kind": "rolling_return_window",
        "source_backtest_metrics_path": metrics_path.as_posix(),
        "source_backtest_metrics_hash": _sha256_file(metrics_path),
        "window_count": len(windows),
        "summary": {
            "return_count": len(rows),
            "window_count": len(windows),
            "worst_window_size": worst["window_size"] if worst is not None else None,
            "worst_window_start_index": worst["start_index"] if worst is not None else None,
            "worst_window_end_index": worst["end_index"] if worst is not None else None,
            "worst_window_total_return": worst["total_return"] if worst is not None else None,
            "worst_window_max_drawdown": worst["max_drawdown"] if worst is not None else None,
        },
        "windows": windows,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    rolling_stability_path = out_dir / "strategy_backtest_rolling_stability.json"
    rolling_stability_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_rolling_stability_report.md",
        payload,
    )
    return BacktestRollingStabilityResult(
        rolling_stability_path=rolling_stability_path,
        report_path=report_path,
        payload=payload,
    )
