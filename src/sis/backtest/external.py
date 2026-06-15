from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import (
    read_json_object as _read_json,
    sha256_file as _sha256_file,
    write_json_object,
)
from sis.backtest.boundary import with_no_live_capability_boundary
from sis.backtest.frameworks import framework_adapter_status
from sis.backtest.optional_dependencies import optional_dependency_source
from sis.backtest.reporting import write_markdown_report
from sis.backtest.vectorbt_adapter import run_vectorbt_result

OPTIONAL_EXTRA_BY_FRAMEWORK = {
    "vectorbt": ("vectorbt", {"vectorbt"}),
    "bt": ("bt", {"bt"}),
    "quantstats": ("reports", {"quantstats"}),
    "empyrical_reloaded": ("metrics", {"empyrical-reloaded", "empyrical"}),
}


@dataclass(frozen=True)
class BacktestExternalResult:
    external_path: Path
    report_path: Path
    payload: dict[str, Any]


def _aggregate_metrics(metrics_payload: dict[str, Any]) -> dict[str, Any]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    aggregate = summary.get("aggregate_metrics")
    if not isinstance(aggregate, dict):
        aggregate = {}
    return {
        "trade_count": aggregate.get("trade_count"),
        "total_return": aggregate.get("total_return"),
        "max_drawdown": aggregate.get("max_drawdown"),
        "cost_drag_bps": aggregate.get("cost_drag_bps"),
        "stale_rejected_count": aggregate.get("stale_rejected_count"),
        "halt_rejected_count": aggregate.get("halt_rejected_count"),
    }


def _dependency_source(candidate: dict[str, Any]) -> str:
    extra_name, dependency_prefixes = OPTIONAL_EXTRA_BY_FRAMEWORK.get(
        str(candidate["framework_id"]),
        (str(candidate["framework_id"]), {str(candidate["framework_id"])}),
    )
    return optional_dependency_source(
        candidate, extra_name=extra_name, dependency_prefixes=dependency_prefixes
    )


def _skipped_result(candidate: dict[str, Any], reason_codes: list[str]) -> dict[str, Any]:
    return {
        "framework_id": candidate["framework_id"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "framework_version": candidate.get("version"),
        "runner_mode": "not_installed_in_current_env",
        "run_status": "skipped",
        "reason_codes": reason_codes,
        "dependency_added": False,
        "dependency_source": _dependency_source(candidate),
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "metrics": {
            "trade_count": None,
            "total_return": None,
            "max_drawdown": None,
            "cost_drag_bps": None,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    }


def _installed_without_runner_result(candidate: dict[str, Any]) -> dict[str, Any]:
    # The first external runner contract is intentionally conservative: a framework
    # must be installed before this can be swapped for a framework-specific engine call.
    return {
        "framework_id": candidate["framework_id"],
        "adapter_role": candidate["adapter_role"],
        "status": candidate["status"],
        "framework_version": candidate.get("version"),
        "runner_mode": "installed_without_runner",
        "run_status": "skipped",
        "reason_codes": ["framework_runner_not_implemented"],
        "dependency_added": False,
        "dependency_source": _dependency_source(candidate),
        "engine_run": False,
        "permits_live_order": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "metrics": {
            "trade_count": None,
            "total_return": None,
            "max_drawdown": None,
            "cost_drag_bps": None,
            "stale_rejected_count": None,
            "halt_rejected_count": None,
        },
    }


def _external_results(
    *,
    signals_path: Path | None,
    quotes_path: Path | None,
    label_horizon_minutes: int,
    initial_capital_usd: float,
    target_frameworks: list[str] | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    selected_frameworks = set(target_frameworks) if target_frameworks is not None else None
    for candidate in framework_adapter_status():
        if selected_frameworks is not None and candidate["framework_id"] not in selected_frameworks:
            continue
        if candidate["status"] != "installed":
            results.append(_skipped_result(candidate, ["not_installed_in_current_env"]))
            continue
        if candidate["framework_id"] == "vectorbt":
            results.append(
                run_vectorbt_result(
                    candidate,
                    signals_path=signals_path,
                    quotes_path=quotes_path,
                    label_horizon_minutes=label_horizon_minutes,
                    initial_capital_usd=initial_capital_usd,
                )
            )
            continue
        results.append(_installed_without_runner_result(candidate))
    return results


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest External Framework Result",
        "",
        f"- created_at: {payload['created_at']}",
        f"- source_metrics_path: `{payload['source_metrics_path']}`",
        f"- source_signals_path: `{payload['source_signals_path']}`",
        f"- source_quotes_path: `{payload['source_quotes_path']}`",
        f"- label_horizon_minutes: {payload['label_horizon_minutes']}",
        f"- dependency_added: {payload['dependency_added']}",
        f"- external_engine_run: {payload['external_engine_run']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Framework | Status | Run Status | Engine Run | Reason Codes | Trades | Total Return |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    for result in payload["results"]:
        metrics = result.get("metrics") or {}
        lines.append(
            "| {framework_id} | {status} | {run_status} | {engine_run} | {reasons} | {trade_count} | {total_return} |".format(
                framework_id=result["framework_id"],
                status=result["status"],
                run_status=result["run_status"],
                engine_run=result["engine_run"],
                reasons=", ".join(result.get("reason_codes") or []) or "none",
                trade_count=metrics.get("trade_count"),
                total_return=metrics.get("total_return"),
            )
        )
    lines.extend(
        [
            "",
            "This artifact never adds dependencies and never permits live orders.",
        ]
    )
    return write_markdown_report(path, lines)


def build_strategy_backtest_external_result(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
    signals_path: Path | None = None,
    quotes_path: Path | None = None,
    label_horizon_minutes: int = 240,
    initial_capital_usd: float = 10000.0,
    target_frameworks: list[str] | None = None,
) -> BacktestExternalResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    _aggregate_metrics(metrics_payload)
    results = _external_results(
        signals_path=signals_path,
        quotes_path=quotes_path,
        label_horizon_minutes=label_horizon_minutes,
        initial_capital_usd=initial_capital_usd,
        target_frameworks=target_frameworks,
    )
    payload: dict[str, Any] = with_no_live_capability_boundary(
        {
            "schema_version": "strategy_backtest_external_result.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_metrics_path": metrics_path.as_posix(),
            "source_metrics_hash": _sha256_file(metrics_path),
            "source_signals_path": (
                signals_path.as_posix()
                if signals_path is not None and signals_path.exists()
                else None
            ),
            "source_signals_hash": (
                _sha256_file(signals_path)
                if signals_path is not None and signals_path.exists()
                else None
            ),
            "source_quotes_path": (
                quotes_path.as_posix() if quotes_path is not None and quotes_path.exists() else None
            ),
            "source_quotes_hash": (
                _sha256_file(quotes_path)
                if quotes_path is not None and quotes_path.exists()
                else None
            ),
            "label_horizon_minutes": label_horizon_minutes,
            "initial_capital_usd": initial_capital_usd,
            "dependency_added": False,
            "external_engine_run": any(result["engine_run"] is True for result in results),
            "results": results,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    external_path = out_dir / "strategy_backtest_external_result.json"
    write_json_object(external_path, payload)
    report_path = _write_report(reports_dir / "strategy_backtest_external_report.md", payload)
    return BacktestExternalResult(
        external_path=external_path, report_path=report_path, payload=payload
    )
