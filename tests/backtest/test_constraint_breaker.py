from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from sis.backtest.constraint_breaker import build_strategy_backtest_constraint_breaker_decision


def _schema(name: str) -> dict:
    return json.loads(Path("schemas", name).read_text(encoding="utf-8"))


def test_constraint_breaker_approves_only_complete_scorecard(tmp_path: Path) -> None:
    result = build_strategy_backtest_constraint_breaker_decision(
        candidate_id="hftbacktest",
        constraint_to_break="native-only",
        capability_gap="material",
        expected_failure_mode_reduction="high",
        proof_fixture_status="synthetic_only",
        license_terms_status="reviewed_allowed",
        external_data_status="not_used",
        ci_cost_status="acceptable",
        rollback_complexity="low",
        owner_approval_ref=None,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    validate(
        instance=result.payload,
        schema=_schema("strategy_backtest_constraint_breaker_decision.v1.schema.json"),
    )
    assert result.payload["decision"] == "APPROVE_BREAK"
    assert result.payload["dependency_added"] is False
    assert result.payload["engine_run"] is False
    assert result.payload["permits_live_order"] is False


def test_constraint_breaker_needs_more_evidence_without_fixture(tmp_path: Path) -> None:
    result = build_strategy_backtest_constraint_breaker_decision(
        candidate_id="hftbacktest",
        constraint_to_break="native-only",
        capability_gap="material",
        expected_failure_mode_reduction="high",
        proof_fixture_status="missing",
        license_terms_status="reviewed_allowed",
        external_data_status="not_used",
        ci_cost_status="acceptable",
        rollback_complexity="low",
        owner_approval_ref=None,
        out_dir=tmp_path / "out",
        reports_dir=tmp_path / "reports",
    )

    assert result.payload["decision"] == "NEEDS_MORE_EVIDENCE"
