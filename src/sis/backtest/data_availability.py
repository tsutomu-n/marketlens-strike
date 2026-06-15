from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


@dataclass(frozen=True)
class BacktestDataAvailabilityResult:
    ledger_path: Path
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


def _csv_row_count(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
    except UnicodeDecodeError:
        return None
    if not rows:
        return 0
    return max(0, len(rows) - 1)


def _json_row_count(payload: dict[str, Any]) -> int:
    for key in ("signals", "results", "executed_signal_results", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            return len(value)
    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in ("signals_considered", "executed_count", "return_count"):
            value = summary.get(key)
            if isinstance(value, int):
                return value
    return 1


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _timestamp_column(columns: list[str]) -> str | None:
    for candidate in (
        "available_at",
        "ts_signal",
        "ts_client",
        "ts",
        "event_ts",
        "exchange_ts",
        "timestamp",
        "date",
    ):
        if candidate in columns:
            return candidate
    return None


def _group_columns(columns: list[str]) -> list[str]:
    return [
        candidate
        for candidate in (
            "venue",
            "canonical_symbol",
            "venue_symbol",
            "symbol",
            "instrument",
        )
        if candidate in columns
    ]


def _timestamp_groups(
    frame: pl.DataFrame, timestamp_column: str, group_columns: list[str]
) -> dict[tuple[str, ...], list[datetime]]:
    groups: dict[tuple[str, ...], list[datetime]] = {}
    selected = [timestamp_column, *group_columns]
    for row in frame.select(selected).to_dicts():
        timestamp = _timestamp(row.get(timestamp_column))
        if timestamp is None:
            continue
        group_key = (
            tuple(str(row.get(column) or "") for column in group_columns)
            if group_columns
            else ("__all__",)
        )
        groups.setdefault(group_key, []).append(timestamp)
    return groups


def _duplicate_count_by_group(groups: dict[tuple[str, ...], list[datetime]]) -> int:
    return sum(len(timestamps) - len(set(timestamps)) for timestamps in groups.values())


def _gap_count_by_group(groups: dict[tuple[str, ...], list[datetime]]) -> int:
    gap_count = 0
    for timestamps in groups.values():
        unique_timestamps = sorted(set(timestamps))
        deltas = [
            (right - left).total_seconds()
            for left, right in zip(unique_timestamps, unique_timestamps[1:], strict=False)
            if (right - left).total_seconds() > 0
        ]
        if not deltas:
            continue
        expected = min(deltas)
        gap_count += sum(1 for delta in deltas if delta > expected * 1.5)
    return gap_count


def _parquet_stats(path: Path) -> dict[str, Any]:
    try:
        frame = pl.read_parquet(path)
    except Exception as exc:
        return {
            "row_count": None,
            "available_start": None,
            "available_end": None,
            "timestamp_column": None,
            "gap_count": None,
            "duplicate_count": None,
            "unusable_reason": f"parquet_unreadable:{type(exc).__name__}",
        }
    timestamp_column = _timestamp_column(frame.columns)
    timestamps: list[datetime] = []
    group_columns = _group_columns(frame.columns)
    if timestamp_column is not None:
        timestamps = [
            item
            for item in (
                _timestamp(value) for value in frame.get_column(timestamp_column).to_list()
            )
            if item is not None
        ]
    duplicate_count: int | None = None
    gap_count: int | None = None
    if timestamps and timestamp_column is not None:
        groups = _timestamp_groups(frame, timestamp_column, group_columns)
        duplicate_count = _duplicate_count_by_group(groups)
        gap_count = _gap_count_by_group(groups)
    return {
        "row_count": frame.height,
        "available_start": min(timestamps).isoformat() if timestamps else None,
        "available_end": max(timestamps).isoformat() if timestamps else None,
        "timestamp_column": timestamp_column,
        "group_columns": group_columns,
        "gap_count": gap_count,
        "duplicate_count": duplicate_count,
        "unusable_reason": None,
    }


def _artifact_row(
    *,
    artifact_id: str,
    path: Path,
    data_type: str,
    provider: str = "strategy_authoring",
    capture_mode: str = "local_artifact",
) -> dict[str, Any]:
    row_count: int | None = None
    available_start: str | None = None
    available_end: str | None = None
    gap_count: int | None = None
    duplicate_count: int | None = None
    timestamp_column: str | None = None
    group_columns: list[str] = []
    unusable_reason: str | None = None
    if path.exists():
        if path.suffix == ".json":
            row_count = _json_row_count(_read_json(path))
        elif path.suffix == ".parquet":
            stats = _parquet_stats(path)
            row_count = stats["row_count"]
            available_start = stats["available_start"]
            available_end = stats["available_end"]
            gap_count = stats["gap_count"]
            duplicate_count = stats["duplicate_count"]
            timestamp_column = stats["timestamp_column"]
            group_columns = stats["group_columns"]
            unusable_reason = stats["unusable_reason"]
        elif path.suffix == ".csv":
            row_count = _csv_row_count(path)
        elif path.suffix == ".jsonl":
            row_count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line)
    repo_status = (
        "enabled" if path.exists() and unusable_reason is None else "missing_local_artifact"
    )
    if path.exists() and unusable_reason is not None:
        repo_status = "unreadable_local_artifact"
    return {
        "artifact_id": artifact_id,
        "provider": provider,
        "venue_id": "local_research",
        "symbol": None,
        "timeframe": None,
        "data_type": data_type,
        "capture_mode": capture_mode,
        "repo_status": repo_status,
        "path": path.as_posix(),
        "source_hash": _sha256_file(path) if path.exists() else None,
        "row_count": row_count,
        "available_start": available_start,
        "available_end": available_end,
        "timestamp_column": timestamp_column,
        "group_columns": group_columns,
        "gap_count": gap_count,
        "duplicate_count": duplicate_count,
        "available_at_policy": "local_artifact_timestamp_only",
        "unusable_reason": unusable_reason if path.exists() else "artifact_missing",
        "assumption_level": "measured" if repo_status == "enabled" else "unknown",
    }


def _future_candidate_rows() -> list[dict[str, Any]]:
    return [
        {
            "artifact_id": "bitget_futures_direct",
            "provider": "bitget",
            "venue_id": "bitget_futures",
            "symbol": None,
            "timeframe": None,
            "data_type": "candles_and_execution_constraints",
            "capture_mode": "external_candidate",
            "repo_status": "schema_disabled_venue",
            "path": None,
            "source_hash": None,
            "row_count": None,
            "available_start": None,
            "available_end": None,
            "gap_count": None,
            "duplicate_count": None,
            "available_at_policy": "not_implemented",
            "unusable_reason": "direct venue schema widening is future scope",
            "assumption_level": "unknown",
        },
        {
            "artifact_id": "hyperliquid_perp_direct",
            "provider": "hyperliquid",
            "venue_id": "hyperliquid_perp",
            "symbol": None,
            "timeframe": None,
            "data_type": "candles_and_execution_constraints",
            "capture_mode": "external_candidate",
            "repo_status": "schema_disabled_venue",
            "path": None,
            "source_hash": None,
            "row_count": None,
            "available_start": None,
            "available_end": None,
            "gap_count": None,
            "duplicate_count": None,
            "available_at_policy": "not_implemented",
            "unusable_reason": "direct venue schema widening is future scope",
            "assumption_level": "unknown",
        },
        {
            "artifact_id": "coinalyze_provider",
            "provider": "coinalyze",
            "venue_id": None,
            "symbol": None,
            "timeframe": None,
            "data_type": "oi_funding_liquidation_long_short",
            "capture_mode": "external_candidate",
            "repo_status": "provider_candidate",
            "path": None,
            "source_hash": None,
            "row_count": None,
            "available_start": None,
            "available_end": None,
            "gap_count": None,
            "duplicate_count": None,
            "available_at_policy": "not_implemented",
            "unusable_reason": "collector is future scope",
            "assumption_level": "unknown",
        },
    ]


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Backtest Data Availability Ledger",
        "",
        f"- status: {payload['status']}",
        f"- enabled_artifact_count: {payload['summary']['enabled_artifact_count']}",
        f"- future_candidate_count: {payload['summary']['future_candidate_count']}",
        "- network_used: false",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Artifact | Provider | Status | Rows | Start | End | Gaps | Duplicates | Path |",
        "|---|---|---|---:|---|---|---:|---:|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {artifact_id} | {provider} | {repo_status} | {row_count} | {start} | {end} | {gaps} | {dups} | `{path}` |".format(
                artifact_id=row["artifact_id"],
                provider=row["provider"],
                repo_status=row["repo_status"],
                row_count=row["row_count"],
                start=row.get("available_start"),
                end=row.get("available_end"),
                gaps=row.get("gap_count"),
                dups=row.get("duplicate_count"),
                path=row["path"],
            )
        )
    return write_markdown_report(path, lines)


def build_backtest_data_availability_ledger(
    *,
    metrics_path: Path,
    signals_path: Path,
    quotes_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestDataAvailabilityResult:
    rows = [
        _artifact_row(
            artifact_id="strategy_backtest_metrics",
            path=metrics_path,
            data_type="backtest_metrics",
        ),
        _artifact_row(
            artifact_id="strategy_signals",
            path=signals_path,
            data_type="strategy_signals",
        ),
        _artifact_row(
            artifact_id="strategy_quotes",
            path=quotes_path,
            data_type="quotes",
        ),
        *_future_candidate_rows(),
    ]
    enabled_count = sum(1 for row in rows if row["repo_status"] == "enabled")
    candidate_count = sum(1 for row in rows if row["capture_mode"] == "external_candidate")
    total_gap_count = sum(
        int(row["gap_count"]) for row in rows if isinstance(row.get("gap_count"), int)
    )
    total_duplicate_count = sum(
        int(row["duplicate_count"]) for row in rows if isinstance(row.get("duplicate_count"), int)
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "backtest_data_availability_ledger.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ledger_kind": "local_artifact_and_future_candidate",
            "status": "pass" if enabled_count >= 2 else "fail",
            "summary": {
                "enabled_artifact_count": enabled_count,
                "future_candidate_count": candidate_count,
                "network_used": False,
                "external_api_called": False,
                "schema_widening_required": False,
                "total_gap_count": total_gap_count,
                "total_duplicate_count": total_duplicate_count,
            },
            "rows": rows,
            "dependency_added": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "backtest_data_availability_ledger.json"
    ledger_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "backtest_data_availability_report.md", payload)
    return BacktestDataAvailabilityResult(
        ledger_path=ledger_path, report_path=report_path, payload=payload
    )
