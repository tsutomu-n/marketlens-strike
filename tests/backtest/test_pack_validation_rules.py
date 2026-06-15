from __future__ import annotations

import json
from pathlib import Path

from sis.backtest.artifact_io import artifact_row, write_json_object
from sis.backtest.pack_contract import PACK_REQUIRED_SUITE_METHODS, external_framework_policy
from sis.backtest.pack_validation import PackValidationContext, run_pack_validation_rules


def test_pack_validation_rules_keep_completion_artifacts_present_check(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    write_json_object(
        artifact_path,
        {
            "schema_version": "test_artifact.v1",
            "paper_only": True,
            "live_order_submitted": False,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        },
    )
    artifacts = {
        "data_availability": artifact_row(artifact_path),
        "baseline_comparison": artifact_row(artifact_path),
        "trial_ledger": artifact_row(artifact_path),
        "assumption_ledger": artifact_row(artifact_path),
        "no_lookahead_diff": artifact_row(artifact_path),
        "execution_simulation": artifact_row(artifact_path),
    }
    findings = run_pack_validation_rules(
        PackValidationContext(
            pack=_pack_payload(artifacts),
            min_suite_method_count=5,
            required_methods=list(PACK_REQUIRED_SUITE_METHODS),
        )
    )

    assert any(
        finding["check_id"] == "completion_artifacts_present" and finding["passed"] is True
        for finding in findings
    )


def test_pack_validation_rules_detect_child_boundary_failure(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.json"
    artifact_path.write_text(
        json.dumps(
            {
                "schema_version": "test_artifact.v1",
                "paper_only": True,
                "permits_live_order": True,
                "wallet_used": False,
                "exchange_write_used": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    findings = run_pack_validation_rules(
        PackValidationContext(
            pack=_pack_payload({"external_result": artifact_row(artifact_path)}),
            min_suite_method_count=5,
            required_methods=list(PACK_REQUIRED_SUITE_METHODS),
        )
    )

    assert any(
        finding["check_id"] == "artifact_external_result_boundary_permits_live_order"
        and finding["passed"] is False
        for finding in findings
    )


def _pack_payload(artifacts: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "strategy_backtest_pack.v1",
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "summary": {
            "suite_method_count": 5,
            "suite_methods": {method: 1 for method in PACK_REQUIRED_SUITE_METHODS},
            "comparison_id": "sha256:" + "a" * 64,
        },
        "external_framework_policy": external_framework_policy(),
        "artifacts": artifacts,
    }
