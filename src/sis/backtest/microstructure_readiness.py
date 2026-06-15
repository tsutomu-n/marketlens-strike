from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import polars as pl

from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


@dataclass(frozen=True)
class BacktestMicrostructureReadinessResult:
    readiness_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _source(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "sha256": _sha256_file(path) if path.exists() else None,
    }


def _columns(path: Path) -> list[str]:
    if not path.exists() or path.suffix != ".parquet":
        return []
    try:
        return pl.read_parquet(path, n_rows=1).columns
    except Exception:
        return []


def _requirement(requirement_id: str, status: str, evidence: str) -> dict[str, Any]:
    return {"requirement_id": requirement_id, "status": status, "evidence": evidence}


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Microstructure Readiness",
        "",
        f"- decision: {payload['decision']}",
        f"- missing_requirement_count: {payload['summary']['missing_requirement_count']}",
        f"- market_impact_supported: {payload['market_impact_supported']}",
        "- dependency_added: false",
        "- engine_run: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Requirement | Status | Evidence |",
        "|---|---:|---|",
    ]
    for row in payload["requirements"]:
        lines.append(f"| {row['requirement_id']} | {row['status']} | {row['evidence']} |")
    return write_markdown_report(path, lines)


def build_strategy_backtest_microstructure_readiness(
    *,
    metrics_path: Path,
    signals_path: Path,
    quotes_path: Path,
    data_availability_path: Path | None,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestMicrostructureReadinessResult:
    quote_columns = set(_columns(quotes_path))
    signal_columns = set(_columns(signals_path))
    requirements = [
        _requirement(
            "order_book_depth",
            "available" if {"best_bid", "best_ask"}.issubset(quote_columns) else "missing",
            "best_bid/best_ask are L1 only; full L2/L3 depth is required",
        ),
        _requirement(
            "trade_ticks",
            "available"
            if {"trade_id", "trade_price", "trade_size"}.issubset(quote_columns)
            else "missing",
            "trade tick id/price/size columns are required",
        ),
        _requirement(
            "feed_latency",
            "available" if {"exchange_ts", "ts_client"}.issubset(quote_columns) else "missing",
            "exchange_ts and ts_client are required to estimate feed latency",
        ),
        _requirement(
            "order_latency",
            "available" if {"order_submitted_at", "ack_at"}.issubset(signal_columns) else "missing",
            "order submission and acknowledgement timestamps are required",
        ),
        _requirement(
            "queue_model_input",
            "available"
            if {"queue_position", "book_order_count"}.issubset(quote_columns)
            else "missing",
            "queue position or order-count depth fields are required",
        ),
    ]
    missing = [row["requirement_id"] for row in requirements if row["status"] == "missing"]
    decision = "READY_FOR_HFT_REPLAY_SPIKE" if not missing else "NOT_READY_FOR_HFT_REPLAY"
    sources = {
        "metrics": _source(metrics_path),
        "signals": _source(signals_path),
        "quotes": _source(quotes_path),
        "data_availability": _source(data_availability_path)
        if data_availability_path is not None
        else {"path": None, "exists": False, "sha256": None},
    }
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_microstructure_readiness.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason_codes": missing or ["all_microstructure_requirements_available"],
            "source_paths": {key: value["path"] for key, value in sources.items()},
            "source_hashes": {key: value["sha256"] for key, value in sources.items()},
            "sources": sources,
            "summary": {
                "requirement_count": len(requirements),
                "missing_requirement_count": len(missing),
                "available_requirement_count": len(requirements) - len(missing),
            },
            "requirements": requirements,
            "missing_requirements": missing,
            "market_impact_supported": False,
            "dependency_added": False,
            "engine_run": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    readiness_path = out_dir / "strategy_backtest_microstructure_readiness.json"
    readiness_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_microstructure_readiness_report.md", payload
    )
    return BacktestMicrostructureReadinessResult(
        readiness_path=readiness_path, report_path=report_path, payload=payload
    )
