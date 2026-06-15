from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.artifact_io import (
    read_json_object as _read_json,
    sha256_file as _sha256_file,
    write_json_object,
)
from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


DEFAULT_BENCHMARK_RETURN_COLUMN = "benchmark_return"
DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN = "benchmark_return"
DEFAULT_PRICE_COLUMN = "mid_price"
DEFAULT_HORIZON_MINUTES = 240


@dataclass(frozen=True)
class BacktestBenchmarkRelativeResult:
    benchmark_relative_path: Path
    report_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class ReturnRow:
    index: int
    signal_return: float
    raw: dict[str, Any]


@dataclass(frozen=True)
class QuoteRow:
    ts: datetime
    price: float


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
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
        rows.append(ReturnRow(index=index, signal_return=signal_return, raw=raw))
    return rows


def _quote_groups(
    quotes_path: Path | None,
    *,
    price_column: str,
) -> dict[tuple[str, str], list[QuoteRow]]:
    if quotes_path is None or not quotes_path.exists():
        return {}
    frame = pl.read_parquet(quotes_path)
    required = {"ts_client", "venue", "canonical_symbol", price_column}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"quote frame missing benchmark columns: {missing}")
    groups: dict[tuple[str, str], list[QuoteRow]] = {}
    for raw in frame.sort("ts_client").to_dicts():
        ts = _parse_ts(raw.get("ts_client"))
        price = _numeric(raw.get(price_column))
        if ts is None or price is None or price <= 0:
            continue
        key = (str(raw.get("venue")), str(raw.get("canonical_symbol")).upper())
        groups.setdefault(key, []).append(QuoteRow(ts=ts, price=price))
    return groups


def _read_benchmark_series_frame(path: Path) -> pl.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pl.read_parquet(path)
    if suffix == ".csv":
        return pl.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pl.read_ndjson(path)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("rows") if isinstance(payload, dict) else payload
        if not isinstance(rows, list):
            raise ValueError("benchmark series JSON must be an array or an object with rows.")
        return pl.DataFrame(rows)
    raise ValueError("benchmark series path must use .parquet, .csv, .jsonl, .ndjson, or .json")


def _ts_key(value: Any) -> str | None:
    parsed = _parse_ts(value)
    if parsed is not None:
        return parsed.isoformat()
    if isinstance(value, str) and value:
        return value
    return None


def _string_key(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _row_index_key(value: Any) -> int | None:
    numeric = _numeric(value)
    if numeric is None:
        return None
    row_index = int(numeric)
    return row_index if row_index == numeric and row_index >= 0 else None


def _benchmark_series_indexes(
    benchmark_series_path: Path | None,
    *,
    return_column: str,
) -> dict[str, dict[Any, float]]:
    if benchmark_series_path is None:
        return {"row_index": {}, "signal_id": {}, "identity": {}}
    if not benchmark_series_path.exists():
        raise FileNotFoundError(f"benchmark series missing: {benchmark_series_path}")
    frame = _read_benchmark_series_frame(benchmark_series_path)
    if return_column not in frame.columns:
        raise ValueError(f"benchmark series missing return column: {return_column}")
    indexes: dict[str, dict[Any, float]] = {"row_index": {}, "signal_id": {}, "identity": {}}
    for raw in frame.to_dicts():
        benchmark_return = _numeric(raw.get(return_column))
        if benchmark_return is None:
            continue
        row_index = _row_index_key(raw.get("source_row_index"))
        if row_index is not None:
            indexes["row_index"][row_index] = benchmark_return
        signal_id = _string_key(raw.get("signal_id"))
        if signal_id is not None:
            indexes["signal_id"][signal_id] = benchmark_return
        ts_signal = _ts_key(raw.get("ts_signal"))
        venue = _string_key(raw.get("venue"))
        symbol = _string_key(raw.get("canonical_symbol"))
        if ts_signal is not None and venue is not None and symbol is not None:
            indexes["identity"][(ts_signal, venue, symbol.upper())] = benchmark_return
    return indexes


def _series_benchmark_return(
    row: ReturnRow,
    benchmark_series_indexes: dict[str, dict[Any, float]],
) -> float | None:
    by_row_index = benchmark_series_indexes.get("row_index") or {}
    if row.index in by_row_index:
        return by_row_index[row.index]
    signal_id = _string_key(row.raw.get("signal_id"))
    by_signal_id = benchmark_series_indexes.get("signal_id") or {}
    if signal_id is not None and signal_id in by_signal_id:
        return by_signal_id[signal_id]
    ts_signal = _ts_key(row.raw.get("ts_signal"))
    venue = _string_key(row.raw.get("venue"))
    symbol = _string_key(row.raw.get("canonical_symbol"))
    by_identity = benchmark_series_indexes.get("identity") or {}
    if ts_signal is not None and venue is not None and symbol is not None:
        return by_identity.get((ts_signal, venue, symbol.upper()))
    return None


def _quote_benchmark_return(
    row: ReturnRow,
    quote_groups: dict[tuple[str, str], list[QuoteRow]],
    *,
    horizon_minutes: int,
) -> float | None:
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be > 0")
    ts_signal = _parse_ts(row.raw.get("ts_signal"))
    venue = row.raw.get("venue")
    symbol = row.raw.get("canonical_symbol")
    if ts_signal is None or venue is None or symbol is None:
        return None
    quotes = quote_groups.get((str(venue), str(symbol).upper())) or []
    entry_index = next(
        (index for index, quote in enumerate(quotes) if quote.ts >= ts_signal),
        None,
    )
    if entry_index is None:
        return None
    target_exit_ts = quotes[entry_index].ts + timedelta(minutes=horizon_minutes)
    exit_index = next(
        (
            index
            for index, quote in enumerate(quotes[entry_index + 1 :], start=entry_index + 1)
            if quote.ts >= target_exit_ts
        ),
        None,
    )
    if exit_index is None:
        return None
    entry_price = quotes[entry_index].price
    exit_price = quotes[exit_index].price
    if entry_price <= 0:
        return None
    return exit_price / entry_price - 1.0


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


def _population_std(values: list[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((item - mean) ** 2 for item in values) / len(values))


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_var = sum((item - left_mean) ** 2 for item in left)
    right_var = sum((item - right_mean) ** 2 for item in right)
    if left_var <= 0 or right_var <= 0:
        return None
    covariance = sum(
        (l_item - left_mean) * (r_item - right_mean)
        for l_item, r_item in zip(left, right, strict=True)
    )
    return covariance / math.sqrt(left_var * right_var)


def _comparison_rows(
    *,
    rows: list[ReturnRow],
    benchmark_series_indexes: dict[str, dict[Any, float]],
    quote_groups: dict[tuple[str, str], list[QuoteRow]],
    benchmark_return_column: str,
    horizon_minutes: int,
) -> tuple[list[dict[str, Any]], int]:
    comparisons: list[dict[str, Any]] = []
    missing_benchmark_count = 0
    for row in rows:
        benchmark_return = _numeric(row.raw.get(benchmark_return_column))
        source = "row_column"
        if benchmark_return is None:
            benchmark_return = _series_benchmark_return(row, benchmark_series_indexes)
            source = "external_series" if benchmark_return is not None else "missing"
        if benchmark_return is None:
            benchmark_return = _quote_benchmark_return(
                row,
                quote_groups,
                horizon_minutes=horizon_minutes,
            )
            source = "quote_frame" if benchmark_return is not None else "missing"
        if benchmark_return is None:
            missing_benchmark_count += 1
            continue
        active_return = row.signal_return - benchmark_return
        comparisons.append(
            {
                "source_row_index": row.index,
                "signal_id": row.raw.get("signal_id"),
                "ts_signal": row.raw.get("ts_signal"),
                "venue": row.raw.get("venue"),
                "canonical_symbol": row.raw.get("canonical_symbol"),
                "side": row.raw.get("side"),
                "strategy_return": row.signal_return,
                "benchmark_return": benchmark_return,
                "active_return": active_return,
                "benchmark_source": source,
            }
        )
    return comparisons, missing_benchmark_count


def _summary(
    *,
    return_count: int,
    rows: list[dict[str, Any]],
    missing_benchmark_count: int,
) -> dict[str, Any]:
    strategy_returns = [float(item["strategy_return"]) for item in rows]
    benchmark_returns = [float(item["benchmark_return"]) for item in rows]
    active_returns = [float(item["active_return"]) for item in rows]
    tracking_error = _population_std(active_returns)
    avg_active_return = sum(active_returns) / len(active_returns) if active_returns else None
    information_ratio = None
    if avg_active_return is not None and tracking_error is not None and tracking_error != 0.0:
        information_ratio = avg_active_return / tracking_error
    return {
        "return_count": return_count,
        "paired_return_count": len(rows),
        "missing_benchmark_count": missing_benchmark_count,
        "strategy_total_return": sum(strategy_returns),
        "benchmark_total_return": sum(benchmark_returns),
        "active_total_return": sum(active_returns),
        "avg_active_return": avg_active_return,
        "min_active_return": min(active_returns) if active_returns else None,
        "max_active_return": max(active_returns) if active_returns else None,
        "active_positive_rate": _positive_rate(active_returns),
        "active_max_drawdown": _max_drawdown(active_returns),
        "tracking_error": tracking_error,
        "information_ratio": information_ratio,
        "strategy_benchmark_correlation": _correlation(strategy_returns, benchmark_returns),
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    summary = payload["summary"]
    lines = [
        "# Strategy Backtest Benchmark Relative",
        "",
        f"- comparison_kind: {payload['comparison_kind']}",
        f"- source_backtest_metrics_path: `{payload['source_backtest_metrics_path']}`",
        f"- source_quotes_path: `{payload['source_quotes_path']}`",
        f"- source_benchmark_series_path: `{payload['source_benchmark_series_path']}`",
        f"- benchmark_return_column: {payload['benchmark_return_column']}",
        f"- benchmark_series_return_column: {payload['benchmark_series_return_column']}",
        f"- price_column: {payload['price_column']}",
        f"- horizon_minutes: {payload['horizon_minutes']}",
        f"- return_count: {summary['return_count']}",
        f"- paired_return_count: {summary['paired_return_count']}",
        f"- missing_benchmark_count: {summary['missing_benchmark_count']}",
        f"- active_total_return: {summary['active_total_return']}",
        f"- tracking_error: {summary['tracking_error']}",
        f"- information_ratio: {summary['information_ratio']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Row | Signal | Strategy | Benchmark | Active | Source |",
        "|---:|---|---:|---:|---:|---|",
    ]
    for row in payload["comparisons"]:
        lines.append(
            "| {index} | {signal_id} | {strategy_return} | {benchmark_return} | {active_return} | {source} |".format(
                index=row["source_row_index"],
                signal_id=row["signal_id"],
                strategy_return=row["strategy_return"],
                benchmark_return=row["benchmark_return"],
                active_return=row["active_return"],
                source=row["benchmark_source"],
            )
        )
    return write_markdown_report(path, lines)


def build_strategy_backtest_benchmark_relative(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    quotes_path: Path | None = None,
    benchmark_series_path: Path | None = None,
    benchmark_return_column: str = DEFAULT_BENCHMARK_RETURN_COLUMN,
    benchmark_series_return_column: str = DEFAULT_BENCHMARK_SERIES_RETURN_COLUMN,
    price_column: str = DEFAULT_PRICE_COLUMN,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
) -> BacktestBenchmarkRelativeResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    if horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be > 0")
    metrics_payload = _read_json(metrics_path)
    rows = _rows(metrics_payload)
    benchmark_series_indexes = _benchmark_series_indexes(
        benchmark_series_path,
        return_column=benchmark_series_return_column,
    )
    quote_groups = _quote_groups(quotes_path, price_column=price_column)
    comparisons, missing_benchmark_count = _comparison_rows(
        rows=rows,
        benchmark_series_indexes=benchmark_series_indexes,
        quote_groups=quote_groups,
        benchmark_return_column=benchmark_return_column,
        horizon_minutes=horizon_minutes,
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_benchmark_relative.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "comparison_kind": "benchmark_relative_return",
            "source_backtest_metrics_path": metrics_path.as_posix(),
            "source_backtest_metrics_hash": _sha256_file(metrics_path),
            "source_quotes_path": (
                quotes_path.as_posix() if quotes_path is not None and quotes_path.exists() else None
            ),
            "source_quotes_hash": (
                _sha256_file(quotes_path)
                if quotes_path is not None and quotes_path.exists()
                else None
            ),
            "source_benchmark_series_path": (
                benchmark_series_path.as_posix()
                if benchmark_series_path is not None and benchmark_series_path.exists()
                else None
            ),
            "source_benchmark_series_hash": (
                _sha256_file(benchmark_series_path)
                if benchmark_series_path is not None and benchmark_series_path.exists()
                else None
            ),
            "benchmark_return_column": benchmark_return_column,
            "benchmark_series_return_column": benchmark_series_return_column,
            "price_column": price_column,
            "horizon_minutes": horizon_minutes,
            "summary": _summary(
                return_count=len(rows),
                rows=comparisons,
                missing_benchmark_count=missing_benchmark_count,
            ),
            "comparisons": comparisons,
            "dependency_added": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    benchmark_relative_path = out_dir / "strategy_backtest_benchmark_relative.json"
    write_json_object(benchmark_relative_path, payload)
    report_path = _write_report(
        reports_dir / "strategy_backtest_benchmark_relative_report.md",
        payload,
    )
    return BacktestBenchmarkRelativeResult(
        benchmark_relative_path=benchmark_relative_path,
        report_path=report_path,
        payload=payload,
    )
