from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sis.backtest.pack import validate_strategy_backtest_pack


def _sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_pack_validation_fails_when_child_json_artifact_breaks_no_live_boundary(
    tmp_path: Path,
) -> None:
    artifact_path = tmp_path / "artifact.json"
    _write_json(
        artifact_path,
        {
            "schema_version": "test_artifact.v1",
            "paper_only": True,
            "permits_live_order": True,
            "wallet_used": False,
            "exchange_write_used": False,
        },
    )
    pack_path = tmp_path / "pack.json"
    _write_json(
        pack_path,
        {
            "schema_version": "strategy_backtest_pack.v1",
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
            "summary": {
                "suite_method_count": 5,
                "suite_methods": {
                    "single_window": 1,
                    "walk_forward:trading_day": 1,
                    "purged_walk_forward:trading_day": 1,
                    "purged_walk_forward:trading_day+return_bootstrap": 1,
                    "purged_walk_forward:trading_day+block_bootstrap": 1,
                },
                "comparison_id": "sha256:" + "a" * 64,
            },
            "external_framework_policy": {
                "policy_id": "native_primary_external_evaluation_only.v1",
                "standard_engine": "strategy_authoring_native",
                "decision": "complete_without_locked_external_dependency",
                "locked_dependency_added": False,
                "external_adapters_required_for_completion": False,
                "temporary_uv_with_allowed": [
                    "vectorbt",
                    "bt",
                    "empyrical-reloaded",
                    "quantstats",
                ],
                "adoption_requires": [
                    "license_review",
                    "python_3_13_uv_lock_review",
                    "ci_green",
                    "schema_boundary_review",
                ],
            },
            "artifacts": {
                "external_result": {
                    "path": artifact_path.as_posix(),
                    "exists": True,
                    "sha256": _sha256_file(artifact_path),
                }
            },
        },
    )

    result = validate_strategy_backtest_pack(
        pack_path=pack_path,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    assert result.payload["decision"] == "FAIL"
    assert any(
        finding["check_id"] == "artifact_external_result_boundary_permits_live_order"
        and finding["passed"] is False
        for finding in result.payload["findings"]
    )
