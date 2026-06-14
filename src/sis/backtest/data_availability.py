from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


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


def _artifact_row(
    *,
    artifact_id: str,
    path: Path,
    data_type: str,
    provider: str = "strategy_authoring",
    capture_mode: str = "local_artifact",
) -> dict[str, Any]:
    row_count: int | None = None
    if path.exists():
        if path.suffix == ".json":
            row_count = _json_row_count(_read_json(path))
        elif path.suffix == ".csv":
            row_count = _csv_row_count(path)
        elif path.suffix == ".jsonl":
            row_count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line)
    return {
        "artifact_id": artifact_id,
        "provider": provider,
        "venue_id": "local_research",
        "symbol": None,
        "timeframe": None,
        "data_type": data_type,
        "capture_mode": capture_mode,
        "repo_status": "enabled" if path.exists() else "missing_local_artifact",
        "path": path.as_posix(),
        "source_hash": _sha256_file(path) if path.exists() else None,
        "row_count": row_count,
        "available_start": None,
        "available_end": None,
        "gap_count": None,
        "duplicate_count": None,
        "available_at_policy": "local_artifact_timestamp_only",
        "unusable_reason": None if path.exists() else "artifact_missing",
        "assumption_level": "measured" if path.exists() else "unknown",
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
        "| Artifact | Provider | Status | Rows | Path |",
        "|---|---|---|---:|---|",
    ]
    for row in payload["rows"]:
        lines.append(
            "| {artifact_id} | {provider} | {repo_status} | {row_count} | `{path}` |".format(
                artifact_id=row["artifact_id"],
                provider=row["provider"],
                repo_status=row["repo_status"],
                row_count=row["row_count"],
                path=row["path"],
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


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
    payload: dict[str, Any] = {
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
        },
        "rows": rows,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
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
