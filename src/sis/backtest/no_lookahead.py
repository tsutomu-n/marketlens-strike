from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BacktestNoLookaheadDiffResult:
    diff_path: Path
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


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest No-Lookahead Diff",
        "",
        f"- status: {payload['status']}",
        f"- check_count: {payload['summary']['check_count']}",
        f"- failed_count: {payload['summary']['failed_count']}",
        f"- diff_mode: {payload['diff_mode']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Check | Passed | Message |",
        "|---|---:|---|",
    ]
    for row in payload["checks"]:
        lines.append(f"| {row['check_id']} | {row['passed']} | {row['message']} |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_no_lookahead_diff(
    *,
    metrics_path: Path,
    signals_path: Path,
    quotes_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestNoLookaheadDiffResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    executed_rows = summary.get("executed_signal_results")
    checks = [
        {
            "check_id": "metrics_source_exists",
            "passed": metrics_path.exists(),
            "message": "native metrics artifact exists",
        },
        {
            "check_id": "signals_source_exists",
            "passed": signals_path.exists(),
            "message": "signals artifact exists",
        },
        {
            "check_id": "quotes_source_exists",
            "passed": quotes_path.exists(),
            "message": "quotes artifact exists",
        },
        {
            "check_id": "executed_results_are_row_level",
            "passed": isinstance(executed_rows, list),
            "message": "native metrics expose row-level executed_signal_results for future differential replay",
        },
        {
            "check_id": "future_mutation_not_runtime_supported",
            "passed": True,
            "message": "v0 records a static guard; runtime future-row mutation replay remains a later extension",
        },
    ]
    failed_count = sum(1 for row in checks if row["passed"] is not True)
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_no_lookahead_diff.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if failed_count == 0 else "fail",
        "diff_mode": "static_artifact_guard_v0",
        "source_backtest_metrics_path": metrics_path.as_posix(),
        "source_backtest_metrics_hash": _sha256_file(metrics_path),
        "source_signals_path": signals_path.as_posix(),
        "source_signals_hash": _sha256_file(signals_path) if signals_path.exists() else None,
        "source_quotes_path": quotes_path.as_posix(),
        "source_quotes_hash": _sha256_file(quotes_path) if quotes_path.exists() else None,
        "summary": {
            "check_count": len(checks),
            "failed_count": failed_count,
            "runtime_future_mutation_replay": False,
        },
        "checks": checks,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_path = out_dir / "strategy_backtest_no_lookahead_diff.json"
    diff_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_no_lookahead_diff_report.md", payload
    )
    return BacktestNoLookaheadDiffResult(
        diff_path=diff_path, report_path=report_path, payload=payload
    )
