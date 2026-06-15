from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from sis.backtest.artifact_io import (
    artifact_row,
    read_json_object,
    sha256_file,
    write_json_object,
)
from sis.backtest.boundary import with_backtest_paper_only_boundary
from sis.backtest.pack_contract import (
    PACK_REQUIRED_SUITE_METHODS,
    external_framework_policy,
)
from sis.backtest.pack_validation import PackValidationContext, run_pack_validation_rules


@dataclass(frozen=True)
class BacktestPackResult:
    pack_path: Path
    report_path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class BacktestPackValidationResult:
    validation_path: Path
    report_path: Path
    payload: dict[str, Any]


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def write_strategy_backtest_pack_outputs(
    *,
    spec_path: Path,
    suite_path: Path,
    artifacts: dict[str, Path],
    suite_payload: dict[str, Any],
    external_payload: dict[str, Any],
    comparison_payload: dict[str, Any],
    out_dir: Path,
    reports_dir: Path,
) -> BacktestPackResult:
    artifact_rows = {name: artifact_row(path) for name, path in sorted(artifacts.items())}
    policy = external_framework_policy()
    native_result = _dict_value(comparison_payload, "native_result")
    capital = _dict_value(native_result, "capital")
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_pack.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "spec_path": spec_path.as_posix(),
            "suite_path": suite_path.as_posix(),
            "summary": {
                "suite_run_count": suite_payload.get("aggregate", {}).get("run_count"),
                "suite_passed_count": suite_payload.get("aggregate", {}).get("passed_count"),
                "suite_method_count": suite_payload.get("method_matrix", {}).get("method_count"),
                "suite_methods": suite_payload.get("method_matrix", {}).get("counts_by_method")
                or {},
                "external_engine_run": external_payload.get("external_engine_run"),
                "external_result_count": len(external_payload.get("results") or []),
                "comparison_id": comparison_payload.get("comparison_id"),
                "capital": capital,
            },
            "external_framework_policy": policy,
            "artifacts": artifact_rows,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    pack_path = out_dir / "strategy_backtest_pack.json"
    write_json_object(pack_path, payload)
    report_path = reports_dir / "strategy_backtest_pack_report.md"
    lines = [
        "# Strategy Backtest Pack",
        "",
        f"- spec_path: `{payload['spec_path']}`",
        f"- suite_path: `{payload['suite_path']}`",
        f"- suite_run_count: {payload['summary']['suite_run_count']}",
        f"- suite_method_count: {payload['summary']['suite_method_count']}",
        f"- external_engine_run: {payload['summary']['external_engine_run']}",
        f"- initial_capital_usd: {capital.get('initial_capital_usd')}",
        f"- net_pnl_usd: {capital.get('net_pnl_usd')}",
        f"- ending_equity_usd: {capital.get('ending_equity_usd')}",
        f"- max_drawdown_loss_usd: {capital.get('max_drawdown_loss_usd')}",
        f"- external_framework_policy: {policy['policy_id']}",
        f"- external_framework_decision: {policy['decision']}",
        "- locked_dependency_added: false",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Artifact | Exists | Path |",
        "|---|---:|---|",
    ]
    for name, row in artifact_rows.items():
        lines.append(f"| {name} | {row['exists']} | `{row['path']}` |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return BacktestPackResult(pack_path=pack_path, report_path=report_path, payload=payload)


def validate_strategy_backtest_pack(
    *,
    pack_path: Path,
    out_dir: Path,
    reports_dir: Path,
    min_suite_method_count: int = 5,
    required_methods: list[str] | None = None,
) -> BacktestPackValidationResult:
    if not pack_path.exists():
        raise FileNotFoundError(f"strategy backtest pack missing: {pack_path}")
    pack = read_json_object(pack_path)
    required_methods = required_methods or list(PACK_REQUIRED_SUITE_METHODS)
    findings = run_pack_validation_rules(
        PackValidationContext(
            pack=pack,
            min_suite_method_count=min_suite_method_count,
            required_methods=required_methods,
        )
    )
    external_framework_policy = _dict_value(pack, "external_framework_policy")

    decision = "PASS" if all(item["passed"] is True for item in findings) else "FAIL"
    payload: dict[str, Any] = with_backtest_paper_only_boundary(
        {
            "schema_version": "strategy_backtest_pack_validation.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pack_path": pack_path.as_posix(),
            "pack_hash": sha256_file(pack_path),
            "decision": decision,
            "summary": {
                "check_count": len(findings),
                "passed_count": sum(1 for item in findings if item["passed"] is True),
                "failed_count": sum(1 for item in findings if item["passed"] is not True),
                "min_suite_method_count": min_suite_method_count,
                "required_methods": required_methods,
                "external_framework_policy_decision": external_framework_policy.get("decision"),
                "locked_dependency_added": external_framework_policy.get("locked_dependency_added"),
            },
            "external_framework_policy": external_framework_policy,
            "findings": findings,
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    validation_path = out_dir / "strategy_backtest_pack_validation.json"
    write_json_object(validation_path, payload)
    report_path = reports_dir / "strategy_backtest_pack_validation_report.md"
    lines = [
        "# Strategy Backtest Pack Validation",
        "",
        f"- decision: {decision}",
        f"- pack_path: `{payload['pack_path']}`",
        f"- check_count: {payload['summary']['check_count']}",
        f"- passed_count: {payload['summary']['passed_count']}",
        f"- failed_count: {payload['summary']['failed_count']}",
        f"- external_framework_policy: {external_framework_policy.get('policy_id')}",
        f"- external_framework_decision: {external_framework_policy.get('decision')}",
        f"- locked_dependency_added: {external_framework_policy.get('locked_dependency_added')}",
        "- permits_live_order: false",
        "- wallet_used: false",
        "- exchange_write_used: false",
        "",
        "| Check | Passed | Message |",
        "|---|---:|---|",
    ]
    for finding in findings:
        lines.append(f"| {finding['check_id']} | {finding['passed']} | {finding['message']} |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return BacktestPackValidationResult(
        validation_path=validation_path, report_path=report_path, payload=payload
    )
