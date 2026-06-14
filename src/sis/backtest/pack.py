from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, cast


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


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _json_artifact_payload(path: Path) -> dict[str, Any] | None:
    if path.suffix != ".json" or not path.exists():
        return None
    try:
        return _read_json(path)
    except (json.JSONDecodeError, ValueError):
        return None


def _artifact_row(path: Path) -> dict[str, Any]:
    return {
        "path": path.as_posix(),
        "exists": path.exists(),
        "sha256": _sha256_file(path) if path.exists() else None,
    }


def _external_framework_policy() -> dict[str, Any]:
    return {
        "policy_id": "native_primary_external_evaluation_only.v1",
        "standard_engine": "strategy_authoring_native",
        "decision": "complete_without_locked_external_dependency",
        "locked_dependency_added": False,
        "external_adapters_required_for_completion": False,
        "temporary_uv_with_allowed": ["vectorbt", "bt", "empyrical-reloaded", "quantstats"],
        "candidate_frameworks": [
            "vectorbt",
            "bt",
            "backtesting.py",
            "zipline-reloaded",
            "backtrader",
            "quantstats",
            "empyrical-reloaded",
            "pyfolio-reloaded",
            "qstrader",
        ],
        "adoption_requires": [
            "license_review",
            "python_3_13_uv_lock_review",
            "ci_green",
            "schema_boundary_review",
        ],
    }


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
    artifact_rows = {name: _artifact_row(path) for name, path in sorted(artifacts.items())}
    external_framework_policy = _external_framework_policy()
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_pack.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "spec_path": spec_path.as_posix(),
        "suite_path": suite_path.as_posix(),
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "summary": {
            "suite_run_count": suite_payload.get("aggregate", {}).get("run_count"),
            "suite_passed_count": suite_payload.get("aggregate", {}).get("passed_count"),
            "suite_method_count": suite_payload.get("method_matrix", {}).get("method_count"),
            "suite_methods": suite_payload.get("method_matrix", {}).get("counts_by_method") or {},
            "external_engine_run": external_payload.get("external_engine_run"),
            "external_result_count": len(external_payload.get("results") or []),
            "comparison_id": comparison_payload.get("comparison_id"),
        },
        "external_framework_policy": external_framework_policy,
        "artifacts": artifact_rows,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    pack_path = out_dir / "strategy_backtest_pack.json"
    pack_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report_path = reports_dir / "strategy_backtest_pack_report.md"
    lines = [
        "# Strategy Backtest Pack",
        "",
        f"- spec_path: `{payload['spec_path']}`",
        f"- suite_path: `{payload['suite_path']}`",
        f"- suite_run_count: {payload['summary']['suite_run_count']}",
        f"- suite_method_count: {payload['summary']['suite_method_count']}",
        f"- external_engine_run: {payload['summary']['external_engine_run']}",
        f"- external_framework_policy: {external_framework_policy['policy_id']}",
        f"- external_framework_decision: {external_framework_policy['decision']}",
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
    pack = _read_json(pack_path)
    findings: list[dict[str, Any]] = []
    required_methods = required_methods or [
        "single_window",
        "walk_forward:trading_day",
        "purged_walk_forward:trading_day",
        "purged_walk_forward:trading_day+return_bootstrap",
        "purged_walk_forward:trading_day+block_bootstrap",
    ]

    def add_check(check_id: str, passed: bool, message: str) -> None:
        findings.append({"check_id": check_id, "passed": passed, "message": message})

    add_check(
        "schema_version",
        pack.get("schema_version") == "strategy_backtest_pack.v1",
        "pack schema_version must be strategy_backtest_pack.v1",
    )
    for field, expected in {
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }.items():
        add_check(f"boundary_{field}", pack.get(field) is expected, f"{field} must be {expected}")

    summary = _dict_value(pack, "summary")
    suite_method_count = summary.get("suite_method_count")
    add_check(
        "suite_method_count",
        isinstance(suite_method_count, int) and suite_method_count >= min_suite_method_count,
        f"suite_method_count must be >= {min_suite_method_count}",
    )
    suite_methods = _dict_value(summary, "suite_methods")
    missing_methods = [method for method in required_methods if method not in suite_methods]
    add_check(
        "required_methods",
        not missing_methods,
        f"required suite methods must be present; missing={missing_methods}",
    )
    add_check(
        "comparison_id",
        isinstance(summary.get("comparison_id"), str)
        and str(summary.get("comparison_id")).startswith("sha256:"),
        "comparison_id must be a sha256 id",
    )

    external_framework_policy = _dict_value(pack, "external_framework_policy")
    add_check(
        "external_framework_policy_id",
        external_framework_policy.get("policy_id") == "native_primary_external_evaluation_only.v1",
        "external framework policy must keep native Strategy Authoring as the standard engine",
    )
    add_check(
        "external_framework_policy_decision",
        external_framework_policy.get("decision") == "complete_without_locked_external_dependency",
        "external framework policy must not require a locked external dependency for completion",
    )
    add_check(
        "external_framework_locked_dependency",
        external_framework_policy.get("locked_dependency_added") is False,
        "locked external framework dependency must not be added by the standard pack",
    )
    add_check(
        "external_framework_completion_scope",
        external_framework_policy.get("external_adapters_required_for_completion") is False,
        "additional external adapters must remain optional evaluation surfaces",
    )
    temporary_allowed = external_framework_policy.get("temporary_uv_with_allowed")
    add_check(
        "external_framework_temporary_vectorbt_bt_empyrical_quantstats",
        isinstance(temporary_allowed, list)
        and {"vectorbt", "bt", "empyrical-reloaded", "quantstats"}.issubset(set(temporary_allowed)),
        "temporary uv --with vectorbt/bt/empyrical-reloaded/quantstats smoke paths must remain allowed external execution paths",
    )
    adoption_requires = external_framework_policy.get("adoption_requires")
    add_check(
        "external_framework_adoption_review",
        isinstance(adoption_requires, list)
        and {
            "license_review",
            "python_3_13_uv_lock_review",
            "ci_green",
            "schema_boundary_review",
        }.issubset(set(adoption_requires)),
        "external framework adoption must require license, lockfile, CI, and boundary review",
    )

    artifacts = _dict_value(pack, "artifacts")
    add_check("artifacts_present", bool(artifacts), "pack artifacts must not be empty")
    for name, row in sorted(artifacts.items()):
        if not isinstance(row, dict):
            add_check(f"artifact_{name}", False, "artifact row must be an object")
            continue
        path_raw = row.get("path")
        expected_hash = row.get("sha256")
        if not isinstance(path_raw, str):
            add_check(f"artifact_{name}_path", False, "artifact path must be a string")
            continue
        artifact_path = Path(path_raw)
        add_check(
            f"artifact_{name}_exists",
            artifact_path.exists() and row.get("exists") is True,
            f"artifact must exist: {path_raw}",
        )
        actual_hash = _sha256_file(artifact_path) if artifact_path.exists() else None
        add_check(
            f"artifact_{name}_hash",
            actual_hash == expected_hash,
            f"artifact hash must match manifest: {path_raw}",
        )
        artifact_payload = _json_artifact_payload(artifact_path)
        if artifact_payload is None:
            continue
        for field, expected in {
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }.items():
            if field not in artifact_payload:
                continue
            add_check(
                f"artifact_{name}_boundary_{field}",
                artifact_payload.get(field) is expected,
                f"artifact {name} {field} must be {expected}: {path_raw}",
            )

    decision = "PASS" if all(item["passed"] is True for item in findings) else "FAIL"
    payload: dict[str, Any] = {
        "schema_version": "strategy_backtest_pack_validation.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pack_path": pack_path.as_posix(),
        "pack_hash": _sha256_file(pack_path),
        "decision": decision,
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
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
    out_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    validation_path = out_dir / "strategy_backtest_pack_validation.json"
    validation_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
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
