from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.reporting import write_markdown_report


@dataclass(frozen=True)
class BacktestPortfolioValidationContractResult:
    contract_path: Path
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


def _executed_rows(metrics_payload: dict[str, Any]) -> list[dict[str, Any]]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        return []
    return [row for row in summary.get("executed_signal_results") or [] if isinstance(row, dict)]


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Portfolio Validation Contract",
        "",
        f"- decision: {payload['decision']}",
        f"- asset_count: {payload['summary']['asset_count']}",
        f"- return_count: {payload['summary']['return_count']}",
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


def build_strategy_backtest_portfolio_validation_contract(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestPortfolioValidationContractResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    rows = _executed_rows(metrics_payload)
    assets = sorted(
        {str(row.get("canonical_symbol")) for row in rows if row.get("canonical_symbol")}
    )
    return_count = sum(1 for row in rows if row.get("signal_return") is not None)
    input_availability = [
        {
            "input_id": "returns_matrix",
            "status": "available" if len(assets) > 1 and return_count >= 4 else "missing",
            "reason": "portfolio validation needs multi-asset return observations",
        },
        {
            "input_id": "asset_labels",
            "status": "available" if assets else "missing",
            "reason": "canonical_symbol labels are required",
        },
        {
            "input_id": "benchmark_labels",
            "status": "missing",
            "reason": "benchmark labels are not part of native signal metrics",
        },
        {
            "input_id": "cv_split_input",
            "status": "available" if return_count >= 8 else "missing",
            "reason": "portfolio CV needs enough observations to split",
        },
        {
            "input_id": "constraints_input",
            "status": "missing",
            "reason": "portfolio optimizer constraints are not defined by Strategy Authoring",
        },
    ]
    missing = [row["input_id"] for row in input_availability if row["status"] == "missing"]
    decision = (
        "READY_FOR_PORTFOLIO_VALIDATION_CONTRACT_SPIKE"
        if not missing
        else "NOT_READY_FOR_PORTFOLIO_VALIDATION_ENGINE"
    )
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_portfolio_validation_contract.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "decision": decision,
            "reason_codes": missing or ["portfolio_validation_inputs_available"],
            "source_paths": {"metrics": metrics_path.as_posix()},
            "source_hashes": {"metrics": _sha256_file(metrics_path)},
            "candidate_frameworks": [
                {
                    "framework_id": "skfolio",
                    "candidate_kind": "portfolio_validation_reference",
                    "engine_run": False,
                    "dependency_added": False,
                },
                {
                    "framework_id": "riskfolio-lib",
                    "candidate_kind": "portfolio_validation_reference",
                    "engine_run": False,
                    "dependency_added": False,
                },
            ],
            "summary": {"asset_count": len(assets), "return_count": return_count},
            "input_availability": input_availability,
            "risk_notes": [
                "skfolio and Riskfolio-Lib are portfolio validation/optimization references, not native signal execution engines",
            ],
            "dependency_added": False,
            "engine_run": False,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    contract_path = out_dir / "strategy_backtest_portfolio_validation_contract.json"
    contract_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_portfolio_validation_contract_report.md", payload
    )
    return BacktestPortfolioValidationContractResult(
        contract_path=contract_path, report_path=report_path, payload=payload
    )
