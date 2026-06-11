from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sis.research.ndx.artifacts import read_json, sha256_file, sha256_json, utc_now_iso, write_json

PASS = "PASS_BACKTEST_ACCEPTANCE"
FAIL = "FAIL_BACKTEST_ACCEPTANCE"
NEEDS_BACKTEST = "NEEDS_BACKTEST"
BLOCK = "BLOCK_BACKTEST_BOUNDARY"

BOUNDARY_FALSE_KEYS = {
    "live_order_submitted",
    "live_conversion_allowed",
    "wallet_used",
    "exchange_write_used",
    "venue_write_used",
    "permits_live_order",
}
FALSE_CLAIM_KEYS = {
    "profitability_claimed",
    "live_ready_claimed",
    "paper_ready_claimed",
    "tiny_live_ready_claimed",
}


@dataclass(frozen=True)
class BacktestAcceptanceResult:
    decision_path: Path
    report_path: Path
    decision: str
    acceptance_id: str


def run_backtest_acceptance(
    *,
    metrics_path: Path,
    out_dir: Path,
    reports_dir: Path,
) -> BacktestAcceptanceResult:
    if not metrics_path.exists():
        stable_payload = _stable_payload(
            metrics_path=metrics_path,
            metrics_hash="",
            decision=NEEDS_BACKTEST,
            summary={},
            decision_reasons=["BACKTEST_METRICS_MISSING"],
            boundary_flags={},
            era_summary={},
        )
        return _write_result(
            out_dir=out_dir, reports_dir=reports_dir, stable_payload=stable_payload
        )

    metrics = read_json(metrics_path)
    summary = metrics.get("summary") if isinstance(metrics.get("summary"), dict) else {}
    if not isinstance(summary, dict):
        summary = {}

    decision_reasons: list[str] = []
    boundary_flags = _boundary_flags(metrics)
    if boundary_flags:
        decision = BLOCK
        decision_reasons.extend(f"BOUNDARY_FLAG_{key.upper()}" for key in sorted(boundary_flags))
    elif metrics.get("schema_version") not in (None, "strategy_authoring_backtest_result.v1"):
        raise ValueError("strategy backtest schema_version mismatch.")
    elif (
        summary.get("backtest_passed") is True
        and summary.get("pass_min_trade_count") is True
        and summary.get("pass_all_thresholds") is True
    ):
        decision = PASS
        decision_reasons.append("BACKTEST_ACCEPTANCE_PASSED")
    else:
        decision = FAIL
        if summary.get("backtest_passed") is not True:
            decision_reasons.append("BACKTEST_NOT_PASSED")
        if summary.get("pass_min_trade_count") is not True:
            decision_reasons.append("MIN_TRADE_COUNT_NOT_PASSED")
        if summary.get("pass_all_thresholds") is not True:
            decision_reasons.append("THRESHOLDS_NOT_PASSED")

    stable_payload = _stable_payload(
        metrics_path=metrics_path,
        metrics_hash=sha256_file(metrics_path),
        decision=decision,
        summary=summary,
        decision_reasons=decision_reasons,
        boundary_flags=boundary_flags,
        era_summary=_era_summary(summary),
    )
    return _write_result(out_dir=out_dir, reports_dir=reports_dir, stable_payload=stable_payload)


def _stable_payload(
    *,
    metrics_path: Path,
    metrics_hash: str,
    decision: str,
    summary: dict[str, Any],
    decision_reasons: list[str],
    boundary_flags: dict[str, bool],
    era_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_backtest_acceptance_decision.v1",
        "decision": decision,
        "source_metrics_path": metrics_path.as_posix(),
        "source_metrics_hash": metrics_hash,
        "decision_reasons": decision_reasons,
        "summary_checks": {
            "backtest_passed": bool(summary.get("backtest_passed")),
            "pass_min_trade_count": bool(summary.get("pass_min_trade_count")),
            "pass_all_thresholds": bool(summary.get("pass_all_thresholds")),
        },
        "era_summary": era_summary,
        "boundary_flags": boundary_flags,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "venue_write_used": False,
        "exchange_write_used": False,
    }


def _write_result(
    *,
    out_dir: Path,
    reports_dir: Path,
    stable_payload: dict[str, Any],
) -> BacktestAcceptanceResult:
    acceptance_id = sha256_json(stable_payload)
    payload = {**stable_payload, "acceptance_id": acceptance_id, "created_at": utc_now_iso()}
    decision_path = write_json(out_dir / "backtest_acceptance_decision.json", payload)
    report_path = _write_report(reports_dir / "strategy_backtest_acceptance_report.md", payload)
    return BacktestAcceptanceResult(
        decision_path=decision_path,
        report_path=report_path,
        decision=str(payload["decision"]),
        acceptance_id=acceptance_id,
    )


def _boundary_flags(value: Any) -> dict[str, bool]:
    flags: dict[str, bool] = {}

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if key in BOUNDARY_FALSE_KEYS and child is not False:
                    flags[key] = True
                if key in FALSE_CLAIM_KEYS and child is True:
                    flags[key] = True
                if key == "paper_only" and child is not True:
                    flags[key] = True
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return flags


def _era_summary(summary: dict[str, Any]) -> dict[str, Any]:
    eras = summary.get("walk_forward_eras")
    if not isinstance(eras, list):
        return {
            "era_count": 0,
            "era_pass_count": 0,
            "era_fail_count": 0,
            "eras_present": False,
        }
    pass_count = 0
    fail_count = 0
    signal_counts: list[int] = []
    for era in eras:
        if not isinstance(era, dict):
            fail_count += 1
            continue
        signal_count = era.get("signal_count", era.get("signals_considered", 0))
        if isinstance(signal_count, int):
            signal_counts.append(signal_count)
        if era.get("backtest_passed") is False or era.get("passed") is False:
            fail_count += 1
        else:
            pass_count += 1
    return {
        "era_count": len(eras),
        "era_pass_count": pass_count,
        "era_fail_count": fail_count,
        "era_signal_counts": signal_counts,
        "eras_present": True,
    }


def _write_report(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Strategy Backtest Acceptance Report",
        "",
        f"- decision: {payload['decision']}",
        f"- acceptance_id: {payload['acceptance_id']}",
        f"- source_metrics_path: {payload['source_metrics_path']}",
        f"- source_metrics_hash: {payload['source_metrics_hash']}",
        f"- decision_reasons: {', '.join(payload['decision_reasons']) or 'none'}",
        "- permits_live_order: false",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
