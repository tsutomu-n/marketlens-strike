from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.external import build_strategy_backtest_external_result
from sis.backtest.metric_extension import build_strategy_backtest_metric_extension
from sis.backtest.portfolio_comparison import build_strategy_backtest_portfolio_comparison
from sis.backtest.report_extension import build_strategy_backtest_report_extension


SUPPORTED_FRAMEWORKS = {
    "vectorbt",
    "bt",
    "empyrical_reloaded",
    "quantstats",
}

FRAMEWORK_ALIASES = {
    "empyrical": "empyrical_reloaded",
    "empyrical-reloaded": "empyrical_reloaded",
    "metrics": "empyrical_reloaded",
    "reports": "quantstats",
}


@dataclass(frozen=True)
class BacktestFrameworkRunResult:
    run_path: Path
    report_path: Path
    payload: dict[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def normalize_framework_ids(frameworks: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in frameworks:
        framework_id = FRAMEWORK_ALIASES.get(raw, raw)
        if framework_id in seen:
            continue
        seen.add(framework_id)
        normalized.append(framework_id)
    return normalized


def _artifact_row(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "sha256": _sha256_file(path) if path.exists() else None,
    }


def _source_row(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "sha256": _sha256_file(path) if path.exists() else None,
    }


def _boundary_row(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "dependency_added": payload.get("dependency_added"),
        "engine_run": payload.get("engine_run", payload.get("external_engine_run")),
        "permits_live_order": payload.get("permits_live_order"),
        "live_conversion_allowed": payload.get("live_conversion_allowed"),
        "wallet_used": payload.get("wallet_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }


def _external_run_status(payload: dict[str, Any], framework_id: str) -> str:
    for result in payload.get("results") or []:
        if isinstance(result, dict) and result.get("framework_id") == framework_id:
            return str(result.get("run_status") or "unknown")
    return "unknown"


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Framework Run",
        "",
        f"- framework_count: {payload['summary']['framework_count']}",
        f"- executed_count: {payload['summary']['executed_count']}",
        f"- skipped_count: {payload['summary']['skipped_count']}",
        f"- failed_count: {payload['summary']['failed_count']}",
        "- dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Framework | Status | Run Status | Engine Run | Artifact |",
        "|---|---:|---:|---:|---|",
    ]
    for run in payload["runs"]:
        artifact = run.get("artifact")
        artifact_path = artifact.get("path") if isinstance(artifact, dict) else None
        lines.append(
            "| {framework_id} | {status} | {run_status} | {engine_run} | `{artifact}` |".format(
                framework_id=run["framework_id"],
                status=run["status"],
                run_status=run["run_status"],
                engine_run=run["boundary"]["engine_run"],
                artifact=artifact_path,
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_framework_run(
    *,
    frameworks: list[str],
    metrics_path: Path,
    bundle_path: Path,
    price_frame_path: Path,
    signals_path: Path,
    quotes_path: Path,
    out_dir: Path,
    reports_dir: Path,
    label_horizon_minutes: int = 240,
    frequency: str = "daily",
    risk_free_rate: float = 0.0,
    suppress_framework_warnings: bool = True,
) -> BacktestFrameworkRunResult:
    selected_frameworks = normalize_framework_ids(frameworks)
    if not selected_frameworks:
        raise ValueError("at least one --framework is required.")

    runs: list[dict[str, Any]] = []
    for framework_id in selected_frameworks:
        if framework_id not in SUPPORTED_FRAMEWORKS:
            runs.append(
                {
                    "framework_id": framework_id,
                    "status": "unsupported",
                    "run_status": "skipped",
                    "reason_codes": ["unsupported_framework_selector"],
                    "artifact": None,
                    "report": None,
                    "boundary": {
                        "dependency_added": False,
                        "engine_run": False,
                        "permits_live_order": False,
                        "live_conversion_allowed": False,
                        "wallet_used": False,
                        "exchange_write_used": False,
                    },
                }
            )
            continue
        if framework_id == "vectorbt":
            result = build_strategy_backtest_external_result(
                metrics_path=metrics_path,
                signals_path=signals_path,
                quotes_path=quotes_path,
                label_horizon_minutes=label_horizon_minutes,
                out_dir=out_dir / "vectorbt_external",
                reports_dir=reports_dir / "backtest_framework_run" / "vectorbt",
                target_frameworks=["vectorbt"],
            )
            runs.append(
                {
                    "framework_id": framework_id,
                    "status": "supported",
                    "run_status": _external_run_status(result.payload, framework_id),
                    "reason_codes": [],
                    "artifact": _artifact_row(result.external_path),
                    "report": _artifact_row(result.report_path),
                    "boundary": _boundary_row(result.payload),
                }
            )
            continue
        if framework_id == "bt":
            result = build_strategy_backtest_portfolio_comparison(
                bundle_path=bundle_path,
                price_frame_path=price_frame_path,
                out_dir=out_dir / "bt_portfolio",
                reports_dir=reports_dir / "backtest_framework_run" / "bt",
            )
            runs.append(
                {
                    "framework_id": framework_id,
                    "status": "supported",
                    "run_status": str(result.payload.get("run_status") or "unknown"),
                    "reason_codes": result.payload.get("reason_codes") or [],
                    "artifact": _artifact_row(result.comparison_path),
                    "report": _artifact_row(result.report_path),
                    "boundary": _boundary_row(result.payload),
                }
            )
            continue
        if framework_id == "empyrical_reloaded":
            result = build_strategy_backtest_metric_extension(
                metrics_path=metrics_path,
                frequency=frequency,
                risk_free_rate=risk_free_rate,
                out_dir=out_dir / "empyrical_metrics",
                reports_dir=reports_dir / "backtest_framework_run" / "empyrical_reloaded",
            )
            runs.append(
                {
                    "framework_id": framework_id,
                    "status": "supported",
                    "run_status": str(result.payload.get("metric_status") or "unknown"),
                    "reason_codes": result.payload.get("reason_codes") or [],
                    "artifact": _artifact_row(result.metric_extension_path),
                    "report": _artifact_row(result.report_path),
                    "boundary": _boundary_row(result.payload),
                }
            )
            continue
        result = build_strategy_backtest_report_extension(
            metrics_path=metrics_path,
            frequency=frequency,
            risk_free_rate=risk_free_rate,
            suppress_framework_warnings=suppress_framework_warnings,
            out_dir=out_dir / "quantstats_report",
            reports_dir=reports_dir / "backtest_framework_run" / "quantstats",
        )
        runs.append(
            {
                "framework_id": framework_id,
                "status": "supported",
                "run_status": str(result.payload.get("report_status") or "unknown"),
                "reason_codes": result.payload.get("reason_codes") or [],
                "artifact": _artifact_row(result.report_extension_path),
                "report": _artifact_row(result.report_path),
                "boundary": _boundary_row(result.payload),
            }
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_framework_run.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selected_frameworks": selected_frameworks,
        "source_metrics_path": metrics_path.as_posix(),
        "source_metrics_hash": _sha256_file(metrics_path) if metrics_path.exists() else None,
        "source_bundle_path": bundle_path.as_posix(),
        "source_bundle_hash": _sha256_file(bundle_path) if bundle_path.exists() else None,
        "source_price_frame_path": price_frame_path.as_posix(),
        "source_price_frame_hash": (
            _sha256_file(price_frame_path) if price_frame_path.exists() else None
        ),
        "source_signals_path": signals_path.as_posix(),
        "source_signals_hash": _sha256_file(signals_path) if signals_path.exists() else None,
        "source_quotes_path": quotes_path.as_posix(),
        "source_quotes_hash": _sha256_file(quotes_path) if quotes_path.exists() else None,
        "sources": {
            "metrics": _source_row(metrics_path),
            "bundle": _source_row(bundle_path),
            "price_frame": _source_row(price_frame_path),
            "signals": _source_row(signals_path),
            "quotes": _source_row(quotes_path),
        },
        "dependency_added": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "summary": {
            "framework_count": len(runs),
            "executed_count": sum(1 for run in runs if run["boundary"].get("engine_run") is True),
            "skipped_count": sum(1 for run in runs if run["run_status"] == "skipped"),
            "failed_count": sum(1 for run in runs if run["run_status"] == "failed"),
        },
        "runs": runs,
    }
    run_path = out_dir / "strategy_backtest_framework_run.json"
    run_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(reports_dir / "strategy_backtest_framework_run_report.md", payload)
    return BacktestFrameworkRunResult(run_path=run_path, report_path=report_path, payload=payload)
