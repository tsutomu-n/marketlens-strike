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
class BacktestPyBrokerContractResult:
    contract_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _columns(path: Path) -> set[str]:
    if not path.exists() or path.suffix != ".parquet":
        return set()
    try:
        return set(pl.read_parquet(path, n_rows=1).columns)
    except Exception:
        return set()


def _availability(input_id: str, status: str, reason: str) -> dict[str, str]:
    return {"input_id": input_id, "status": status, "reason": reason}


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest PyBroker Contract",
        "",
        f"- decision: {payload['decision']}",
        f"- external_data_source_allowed: {payload['external_data_source_allowed']}",
        "- dependency_added: false",
        "- engine_run: false",
        "- permits_live_order: false",
        "",
        "| Input | Status | Reason |",
        "|---|---:|---|",
    ]
    for row in payload["input_availability"]:
        lines.append(f"| {row['input_id']} | {row['status']} | {row['reason']} |")
    return write_markdown_report(path, lines)


def build_strategy_backtest_pybroker_contract(
    *,
    signals_path: Path,
    quotes_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestPyBrokerContractResult:
    signal_columns = _columns(signals_path)
    quote_columns = _columns(quotes_path)
    local_dataframe_ready = {"ts_signal", "canonical_symbol", "side"}.issubset(signal_columns) and {
        "ts_client",
        "canonical_symbol",
        "mid_price",
    }.issubset(quote_columns)
    feature_provenance_ready = "available_at" in signal_columns or "available_at" in quote_columns
    input_availability = [
        _availability(
            "local_dataframe_input",
            "available" if local_dataframe_ready else "missing",
            "Strategy signals and local quotes must be convertible without external fetch",
        ),
        _availability(
            "feature_available_at_provenance",
            "available" if feature_provenance_ready else "missing",
            "point-in-time available_at provenance is required before model-style validation",
        ),
        _availability(
            "walk_forward_split",
            "available" if "ts_signal" in signal_columns else "missing",
            "timestamped signals are required for walk-forward splits",
        ),
        _availability(
            "bootstrap_settings",
            "missing",
            "bootstrap parameters are not defined in the native authoring spec",
        ),
        _availability(
            "model_input",
            "missing",
            "model features are not exposed as a PyBroker-ready local DataFrame contract",
        ),
    ]
    missing = [row["input_id"] for row in input_availability if row["status"] == "missing"]
    decision = (
        "READY_FOR_PYBROKER_CONTRACT_SPIKE"
        if not missing
        else "NOT_READY_FOR_PYBROKER_REFERENCE_RUN"
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_pybroker_contract.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason_codes": missing or ["pybroker_local_contract_available"],
            "source_paths": {"signals": signals_path.as_posix(), "quotes": quotes_path.as_posix()},
            "source_hashes": {
                "signals": _sha256_file(signals_path) if signals_path.exists() else None,
                "quotes": _sha256_file(quotes_path) if quotes_path.exists() else None,
            },
            "input_availability": input_availability,
            "external_data_source_allowed": False,
            "risk_notes": [
                "PyBroker distribution is lib-pybroker while import name is pybroker",
                "Commons Clause / non-commercial license risk must be reviewed before dependency adoption",
                "Alpaca, Yahoo Finance, AKShare, and other built-in external data sources are prohibited in this lane",
            ],
            "dependency_added": False,
            "engine_run": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    contract_path = out_dir / "strategy_backtest_pybroker_contract.json"
    contract_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_pybroker_contract_report.md", payload
    )
    return BacktestPyBrokerContractResult(
        contract_path=contract_path, report_path=report_path, payload=payload
    )
