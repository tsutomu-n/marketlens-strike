from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BacktestBaselineComparisonResult:
    comparison_path: Path
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


def _numeric(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        result = float(value)
        return result if math.isfinite(result) else None
    return None


def _returns(metrics_payload: dict[str, Any]) -> list[float]:
    summary = metrics_payload.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("strategy backtest metrics missing summary object.")
    rows: list[float] = []
    for raw in summary.get("executed_signal_results") or []:
        if not isinstance(raw, dict):
            continue
        signal_return = _numeric(raw.get("signal_return"))
        if signal_return is not None:
            rows.append(signal_return)
    return rows


def _baseline_row(
    *,
    baseline_id: str,
    description: str,
    total_return: float | None,
    return_count: int,
    status: str = "available",
    comparison_role: str = "return_series_control",
) -> dict[str, Any]:
    return {
        "baseline_id": baseline_id,
        "description": description,
        "status": status,
        "comparison_role": comparison_role,
        "return_count": return_count,
        "total_return": total_return,
        "avg_return": total_return / return_count
        if total_return is not None and return_count
        else None,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    lines = [
        "# Strategy Backtest Baseline Comparison",
        "",
        f"- status: {payload['status']}",
        f"- strategy_total_return: {payload['summary']['strategy_total_return']}",
        f"- strongest_baseline_id: {payload['summary']['strongest_baseline_id']}",
        f"- weakness_flag_count: {payload['summary']['weakness_flag_count']}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Baseline | Status | Total return | Description |",
        "|---|---|---:|---|",
    ]
    for row in payload["baselines"]:
        lines.append(
            f"| {row['baseline_id']} | {row['status']} | {row['total_return']} | {row['description']} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def build_strategy_backtest_baseline_comparison(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestBaselineComparisonResult:
    if not metrics_path.exists():
        raise FileNotFoundError(f"strategy backtest metrics missing: {metrics_path}")
    metrics_payload = _read_json(metrics_path)
    returns = _returns(metrics_payload)
    strategy_total_return = sum(returns)
    positive_returns = [item for item in returns if item > 0]
    negative_returns = [item for item in returns if item < 0]
    random_throttle_returns = [item for index, item in enumerate(returns) if index % 2 == 0]
    baselines = [
        _baseline_row(
            baseline_id="cash_no_trade",
            description="No position and no transaction cost.",
            total_return=0.0,
            return_count=len(returns),
            comparison_role="cash_control",
        ),
        _baseline_row(
            baseline_id="simple_momentum",
            description="Keeps only positive realized signal returns as a crude momentum control.",
            total_return=sum(positive_returns),
            return_count=len(positive_returns),
        ),
        _baseline_row(
            baseline_id="simple_mean_reversion",
            description="Keeps inverse of negative signal returns as a crude mean-reversion control.",
            total_return=sum(abs(item) for item in negative_returns),
            return_count=len(negative_returns),
        ),
        _baseline_row(
            baseline_id="random_throttle_seed_0",
            description="Deterministic half-sample throttle using even-indexed trades.",
            total_return=sum(random_throttle_returns),
            return_count=len(random_throttle_returns),
        ),
        _baseline_row(
            baseline_id="simple_leverage_1_5x",
            description="Naive 1.5x leverage of realized strategy returns; stress comparison only.",
            total_return=strategy_total_return * 1.5 if returns else None,
            return_count=len(returns),
            status="diagnostic_only" if returns else "skipped",
            comparison_role="strategy_derived_stress",
        ),
        _baseline_row(
            baseline_id="simple_funding_carry",
            description="Skipped unless funding rows exist in the native metrics artifact.",
            total_return=None,
            return_count=0,
            status="skipped_no_funding_series",
        ),
    ]
    available = [
        row
        for row in baselines
        if row["status"] == "available"
        and row["comparison_role"] in {"cash_control", "return_series_control"}
    ]
    strongest = max(
        available,
        key=lambda row: row["total_return"] if row["total_return"] is not None else float("-inf"),
        default=None,
    )
    weakness_flags = [
        {
            "baseline_id": row["baseline_id"],
            "reason": "baseline_total_return_gte_strategy_total_return",
            "baseline_total_return": row["total_return"],
            "strategy_total_return": strategy_total_return,
        }
        for row in available
        if row["total_return"] is not None and row["total_return"] >= strategy_total_return
    ]
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_baseline_comparison.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "source_backtest_metrics_path": metrics_path.as_posix(),
        "source_backtest_metrics_hash": _sha256_file(metrics_path),
        "summary": {
            "return_count": len(returns),
            "strategy_total_return": strategy_total_return,
            "baseline_count": len(baselines),
            "available_baseline_count": len(available),
            "diagnostic_only_count": sum(
                1 for row in baselines if row["status"] == "diagnostic_only"
            ),
            "strongest_baseline_id": strongest["baseline_id"] if strongest else None,
            "strongest_baseline_total_return": strongest["total_return"] if strongest else None,
            "weakness_flag_count": len(weakness_flags),
        },
        "baselines": baselines,
        "weakness_flags": weakness_flags,
        "dependency_added": False,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = out_dir / "strategy_backtest_baseline_comparison.json"
    comparison_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = _write_report(
        reports_dir / "strategy_backtest_baseline_comparison_report.md", payload
    )
    return BacktestBaselineComparisonResult(
        comparison_path=comparison_path, report_path=report_path, payload=payload
    )
