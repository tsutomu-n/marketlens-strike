from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sis.backtest.artifact_io import json_artifact_payload, sha256_file
from sis.backtest.pack_contract import PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS


@dataclass(frozen=True)
class PackValidationFinding:
    check_id: str
    passed: bool
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"check_id": self.check_id, "passed": self.passed, "message": self.message}


@dataclass(frozen=True)
class PackValidationContext:
    pack: dict[str, Any]
    min_suite_method_count: int
    required_methods: list[str]


def run_pack_validation_rules(context: PackValidationContext) -> list[dict[str, Any]]:
    findings: list[PackValidationFinding] = []
    pack = context.pack

    def add_check(check_id: str, passed: bool, message: str) -> None:
        findings.append(PackValidationFinding(check_id=check_id, passed=passed, message=message))

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
        isinstance(suite_method_count, int)
        and suite_method_count >= context.min_suite_method_count,
        f"suite_method_count must be >= {context.min_suite_method_count}",
    )
    suite_methods = _dict_value(summary, "suite_methods")
    missing_methods = [method for method in context.required_methods if method not in suite_methods]
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
    missing_artifact_keys = [
        key for key in PACK_REQUIRED_COMPLETION_ARTIFACT_KEYS if key not in artifacts
    ]
    add_check(
        "completion_artifacts_present",
        not missing_artifact_keys,
        f"completion artifacts must be present; missing={missing_artifact_keys}",
    )
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
        actual_hash = sha256_file(artifact_path) if artifact_path.exists() else None
        add_check(
            f"artifact_{name}_hash",
            actual_hash == expected_hash,
            f"artifact hash must match manifest: {path_raw}",
        )
        artifact_payload = json_artifact_payload(artifact_path)
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

    return [finding.as_dict() for finding in findings]


def _dict_value(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}
