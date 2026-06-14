from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BacktestTrialLedgerResult:
    ledger_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _trial_type(name: str) -> str:
    if "suite" in name:
        return "multi_method_suite"
    if "external" in name or "framework" in name:
        return "external_framework"
    if "baseline" in name:
        return "baseline_negative_control"
    if "lookahead" in name:
        return "no_lookahead_guard"
    if "execution" in name:
        return "execution_simulation"
    return "artifact_generation"


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Trial Ledger",
        "",
        f"- status: {payload['status']}",
        f"- trial_count: {payload['summary']['trial_count']}",
        f"- missing_count: {payload['summary']['missing_count']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Trial | Type | Status | Path |",
        "|---|---|---|---|",
    ]
    for row in payload["trials"]:
        lines.append(
            f"| {row['trial_id']} | {row['trial_type']} | {row['status']} | `{row['path']}` |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_trial_ledger(
    *,
    artifacts: dict[str, Path],
    out_dir: Path,
    reports_dir: Path,
) -> BacktestTrialLedgerResult:
    trials: list[dict[str, Any]] = []
    for name, path in sorted(artifacts.items()):
        digest = hashlib.sha256(f"{name}:{path.as_posix()}".encode("utf-8")).hexdigest()
        exists = path.exists()
        trials.append(
            {
                "trial_id": f"sha256:{digest}",
                "artifact_name": name,
                "trial_type": _trial_type(name),
                "status": "available" if exists else "missing",
                "path": path.as_posix(),
                "source_hash": _sha256_file(path) if exists else None,
                "reason_code": None if exists else "missing_artifact",
                "paper_only": True,
            }
        )
    missing_count = sum(1 for row in trials if row["status"] != "available")
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_trial_ledger.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if missing_count == 0 else "fail",
        "summary": {
            "trial_count": len(trials),
            "missing_count": missing_count,
            "success_only_reporting": False,
        },
        "trials": trials,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = out_dir / "strategy_backtest_trial_ledger.json"
    ledger_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "strategy_backtest_trial_ledger_report.md", payload)
    return BacktestTrialLedgerResult(
        ledger_path=ledger_path, report_path=report_path, payload=payload
    )
