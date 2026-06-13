from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


DEFAULT_DIMENSION_CSV = "side,timeframe,exit_reason,ts_weekday,ts_hour"


@dataclass(frozen=True)
class BacktestRegimeSplitResult:
    regime_split_path: Path
    report_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReturnRow:
    index: int
    signal_return: float
    cost_drag_bps: float
    notional_usd: float | None
    raw: dict[str, Any]


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


def parse_regime_dimensions(raw: str) -> list[str]:
    dimensions: list[str] = []
    seen: set[str] = set()
    for part in raw.split(","):
        dimension = part.strip()
        if not dimension:
            continue
        if dimension in seen:
            raise ValueError(f"duplicate regime split dimension: {dimension}")
        dimensions.append(dimension)
        seen.add(dimension)
    if not dimensions:
        raise ValueError("at least one regime split dimension is required")
    return dimensions


def _parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


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
        rows.append(
            ReturnRow(
                index=index,
                signal_return=signal_return,
                cost_drag_bps=float(_numeric(raw.get("cost_drag_bps")) or 0.0),
                notional_usd=_numeric(raw.get("notional_usd")),
                raw=raw,
            )
        )
    return rows


def _dimension_value(row: ReturnRow, dimension: str) -> str:
    if dimension in {"ts_date", "ts_weekday", "ts_hour"}:
        parsed = _parse_ts(row.raw.get("ts_signal"))
        if parsed is None:
            return "missing"
        if dimension == "ts_date":
            return parsed.date().isoformat()
        if dimension == "ts_weekday":
            return str(parsed.weekday())
        return str(parsed.hour)
    value = row.raw.get(dimension)
    if value is None or value == "":
        return "missing"
    return str(value)


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


def _bucket_payload(*, dimension: str, bucket_value: str, rows: list[ReturnRow]) -> dict[str, Any]:
    returns = [row.signal_return for row in rows]
    total_return = sum(returns)
    return {
        "dimension_id": dimension,
        "bucket_id": f"{dimension}:{bucket_value}",
        "bucket_value": bucket_value,
        "return_count": len(rows),
        "total_return": total_return,
        "avg_signal_return": total_return / len(rows) if rows else None,
        "min_signal_return": min(returns) if returns else None,
        "max_signal_return": max(returns) if returns else None,
        "positive_rate": _positive_rate(returns),
        "max_drawdown": _max_drawdown(returns),
        "cost_drag_bps": sum(row.cost_drag_bps for row in rows),
        "notional_usd": sum(row.notional_usd for row in rows if row.notional_usd is not None),
        "source_row_indices": [row.index for row in rows],
    }


def _dimension_payload(*, dimension: str, rows: list[ReturnRow]) -> dict[str, Any]:
    grouped: dict[str, list[ReturnRow]] = {}
    for row in rows:
        grouped.setdefault(_dimension_value(row, dimension), []).append(row)
    buckets = [
        _bucket_payload(dimension=dimension, bucket_value=value, rows=bucket_rows)
        for value, bucket_rows in sorted(grouped.items())
    ]
    return {
        "dimension_id": dimension,
        "bucket_count": len(buckets),
        "buckets": buckets,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    summary = payload["summary"]
    lines = [
        "# Strategy Backtest Regime Split",
        "",
        f"- split_kind: {payload['split_kind']}",
        f"- source_backtest_metrics_path: `{payload['source_backtest_metrics_path']}`",
        f"- return_count: {summary['return_count']}",
        f"- dimension_count: {summary['dimension_count']}",
        f"- worst_dimension_id: {summary['worst_dimension_id']}",
        f"- worst_bucket_id: {summary['worst_bucket_id']}",
        f"- worst_bucket_total_return: {summary['worst_bucket_total_return']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
    ]
    for dimension in payload["dimensions"]:
        lines.extend(
            [
                f"## {dimension['dimension_id']}",
                "",
                "| Bucket | Count | Total Return | Avg Return | Positive Rate | Max DD | Cost Drag bps |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for bucket in dimension["buckets"]:
            lines.append(
                "| {bucket} | {count} | {total} | {avg} | {positive} | {drawdown} | {cost} |".format(
                    bucket=bucket["bucket_value"],
                    count=bucket["return_count"],
                    total=bucket["total_return"],
                    avg=bucket["avg_signal_return"],
                    positive=bucket["positive_rate"],
                    drawdown=bucket["max_drawdown"],
                    cost=bucket["cost_drag_bps"],
                )
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_regime_split(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    dimension_csv: str = DEFAULT_DIMENSION_CSV,
) -> BacktestRegimeSplitResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    rows = _rows(metrics_payload)
    dimensions = [
        _dimension_payload(dimension=dimension, rows=rows)
        for dimension in parse_regime_dimensions(dimension_csv)
    ]
    all_buckets = [
        bucket
        for dimension in dimensions
        for bucket in dimension["buckets"]
        if bucket["return_count"] > 0
    ]
    worst = min(
        all_buckets,
        key=lambda item: float(item["total_return"]),
        default={
            "dimension_id": None,
            "bucket_id": None,
            "total_return": None,
        },
    )
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_regime_split.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split_kind": "regime_dimension",
        "source_backtest_metrics_path": metrics_path.as_posix(),
        "source_backtest_metrics_hash": _sha256_file(metrics_path),
        "dimension_count": len(dimensions),
        "summary": {
            "return_count": len(rows),
            "dimension_count": len(dimensions),
            "worst_dimension_id": worst["dimension_id"],
            "worst_bucket_id": worst["bucket_id"],
            "worst_bucket_total_return": worst["total_return"],
        },
        "dimensions": dimensions,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    regime_split_path = out_dir / "strategy_backtest_regime_split.json"
    regime_split_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "strategy_backtest_regime_split_report.md", payload)
    return BacktestRegimeSplitResult(
        regime_split_path=regime_split_path,
        report_path=report_path,
        payload=payload,
    )
