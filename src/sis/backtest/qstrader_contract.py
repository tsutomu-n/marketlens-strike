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
class BacktestQstraderContractResult:
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


def _availability(component_id: str, required: set[str], columns: set[str]) -> dict[str, Any]:
    missing = sorted(required - columns)
    return {
        "component_id": component_id,
        "status": "available" if not missing else "missing",
        "required_columns": sorted(required),
        "missing_columns": missing,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest qstrader Contract",
        "",
        f"- decision: {payload['decision']}",
        "- dependency_added: false",
        "- engine_run: false",
        "- permits_live_order: false",
        "",
        "| Component | Status | Missing columns |",
        "|---|---:|---|",
    ]
    for row in payload["input_contract"]:
        lines.append(
            f"| {row['component_id']} | {row['status']} | {', '.join(row['missing_columns']) or 'none'} |"
        )
    return write_markdown_report(path, lines)


def build_strategy_backtest_qstrader_contract(
    *,
    signals_path: Path,
    quotes_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestQstraderContractResult:
    signal_columns = _columns(signals_path)
    quote_columns = _columns(quotes_path)
    input_contract = [
        _availability("universe", {"canonical_symbol"}, signal_columns | quote_columns),
        _availability("alpha_model_input", {"ts_signal", "side"}, signal_columns),
        _availability(
            "data_handler_input", {"ts_client", "canonical_symbol", "mid_price"}, quote_columns
        ),
        _availability("risk_model_input", {"notional_usd"}, signal_columns),
        _availability("rebalance_cadence", {"ts_signal"}, signal_columns),
        _availability("fee_model", {"taker_fee_bps"}, quote_columns),
    ]
    missing = [row["component_id"] for row in input_contract if row["status"] == "missing"]
    decision = (
        "READY_FOR_QSTRADER_CONTRACT_SPIKE" if not missing else "NOT_READY_FOR_QSTRADER_RUNNER"
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_qstrader_contract.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason_codes": missing or ["local_input_contract_available"],
            "source_paths": {
                "signals": signals_path.as_posix(),
                "quotes": quotes_path.as_posix(),
            },
            "source_hashes": {
                "signals": _sha256_file(signals_path) if signals_path.exists() else None,
                "quotes": _sha256_file(quotes_path) if quotes_path.exists() else None,
            },
            "input_contract": input_contract,
            "risk_notes": [
                "qstrader is not added as a dependency in this lane",
                "PyPI classifier risk: Python 3.13 support is not treated as proven by this contract",
                "external data download is not allowed by this contract",
            ],
            "dependency_added": False,
            "engine_run": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    contract_path = out_dir / "strategy_backtest_qstrader_contract.json"
    contract_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_qstrader_contract_report.md", payload
    )
    return BacktestQstraderContractResult(
        contract_path=contract_path, report_path=report_path, payload=payload
    )
