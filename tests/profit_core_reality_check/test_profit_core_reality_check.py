from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.profit_core_reality_check import build_profit_core_reality_check


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _write_ledger(path: Path, candidate_ids: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        json.dumps({"candidate_id": candidate_id, "decision": "RECORDED"}, sort_keys=True)
        for candidate_id in candidate_ids
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def _candidate(
    candidate_id: str,
    *,
    decision: str,
    family: str = "perp_momentum_continuation",
    side_bias: str = "long",
) -> dict[str, Any]:
    payload = {
        "idea_candidate_id": candidate_id,
        "decision": decision,
        "family": family,
        "parameter_set": {"side_bias": side_bias},
        "selection_adjusted_metrics_status": "NOT_ESTIMABLE",
        "leakage_checks": {"uses_sealed_test_for_selection": False},
    }
    if decision == "SHORTLISTED":
        payload["shortlist_reason"] = "fixture shortlist"
    else:
        payload["rejection_reason"] = "fixture reject"
    return payload


def _candidate_set(
    candidates: list[dict[str, Any]],
    *,
    success_only_reporting: bool = False,
    sealed_test_used_for_selection: bool = False,
) -> dict[str, Any]:
    shortlisted = [
        candidate["idea_candidate_id"]
        for candidate in candidates
        if candidate["decision"] == "SHORTLISTED"
    ]
    rejected = [
        candidate["idea_candidate_id"]
        for candidate in candidates
        if candidate["decision"] == "REJECTED"
    ]
    return {
        "schema_version": "strategy_idea_candidate_set.v1",
        "candidate_set_id": "profit-core-fixture-candidates",
        "candidate_inventory": candidates,
        "search_ledger_summary": {
            "candidate_count_total": len(candidates),
            "candidate_count_shortlisted": len(shortlisted),
            "candidate_count_rejected": len(rejected),
            "trial_count_total": len(candidates),
            "candidate_cap": 250,
            "cap_rejection_count": 0,
            "duplicate_rejection_count": 0,
            "validation_peek_count": 0,
            "rerank_count": 0,
            "success_only_reporting": success_only_reporting,
            "sealed_test_used_for_selection": sealed_test_used_for_selection,
        },
        "selection_policy": {
            "shortlisted_candidate_ids": shortlisted,
            "rejected_candidate_ids": rejected,
            "known_gaps": ["fixture candidate set"],
        },
        "split_policy": {"uses_sealed_test_for_selection": sealed_test_used_for_selection},
        "leakage_policy": {"uses_sealed_test_for_selection": sealed_test_used_for_selection},
    }


def _export_manifest(candidate_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "strategy_idea_candidate_export_manifest.v1",
        "manifest_id": "profit-core-fixture-export",
        "candidate_set_id": "profit-core-fixture-candidates",
        "exported_ideas": [
            {
                "idea_candidate_id": candidate_id,
                "strategy_idea_path": f"data/exported/{candidate_id}.json",
                "strategy_idea_sha256": "sha256:" + "a" * 64,
                "export_decision": "SHORTLISTED",
            }
            for candidate_id in candidate_ids
        ],
    }


def _schema() -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / "schemas/profit_core_reality_check.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def test_cli_writes_blocked_reality_check_for_candidate_and_ledger_only(tmp_path: Path) -> None:
    candidates = [
        _candidate("cand-001", decision="SHORTLISTED"),
        _candidate("cand-002", decision="REJECTED", family="perp_funding_rate_carry_filter"),
    ]
    candidate_set_path = _write_json(tmp_path / "strategy_idea_candidate_set.json", _candidate_set(candidates))
    ledger_path = _write_ledger(tmp_path / "search_ledger.jsonl", ["cand-001", "cand-002"])
    out_dir = tmp_path / "reality"

    result = runner.invoke(
        app,
        [
            "profit-core-reality-check",
            "--candidate-set",
            str(candidate_set_path),
            "--search-ledger",
            str(ledger_path),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "credentials_used=false" in result.stdout
    assert "production_exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "permits_live_order=false" in result.stdout
    assert "status=blocked" in result.stdout
    assert "next_single_blocker_to_fix=AUTHORING_BRIDGE_MISSING" in result.stdout
    payload = json.loads((out_dir / "profit_core_reality_check.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    assert payload["summary"]["overall_status"] == "BLOCKED"
    assert payload["candidate_generation"]["candidate_count_total"] == 2
    assert payload["bridge_summary"]["bridge_manifest_present"] is False
    assert payload["boundary"]["permits_live_order"] is False
    report = (out_dir / "profit_core_reality_check.md").read_text(encoding="utf-8")
    assert "next_single_blocker_to_fix: `AUTHORING_BRIDGE_MISSING`" in report


def test_success_only_reporting_preempts_missing_bridge(tmp_path: Path) -> None:
    candidates = [_candidate("cand-001", decision="SHORTLISTED")]
    candidate_set_path = _write_json(
        tmp_path / "strategy_idea_candidate_set.json",
        _candidate_set(candidates, success_only_reporting=True),
    )
    ledger_path = _write_ledger(tmp_path / "search_ledger.jsonl", ["cand-001"])

    check = build_profit_core_reality_check(
        candidate_set_path=candidate_set_path,
        search_ledger_path=ledger_path,
        created_at="2026-07-03T03:00:00Z",
    )

    assert check.candidate_generation.success_only_reporting_detected is True
    assert check.next_single_blocker_to_fix == "SUCCESS_ONLY_REPORTING_DETECTED"
    assert check.summary.overall_status == "BLOCKED"


def test_sealed_test_usage_preempts_missing_bridge_when_search_is_present(tmp_path: Path) -> None:
    candidates = [
        _candidate("cand-001", decision="SHORTLISTED"),
        _candidate("cand-002", decision="REJECTED"),
    ]
    candidate_set_path = _write_json(
        tmp_path / "strategy_idea_candidate_set.json",
        _candidate_set(candidates, sealed_test_used_for_selection=True),
    )
    ledger_path = _write_ledger(tmp_path / "search_ledger.jsonl", ["cand-001", "cand-002"])

    check = build_profit_core_reality_check(
        candidate_set_path=candidate_set_path,
        search_ledger_path=ledger_path,
        created_at="2026-07-03T03:00:00Z",
    )

    assert check.candidate_generation.sealed_test_used_for_selection is True
    assert check.next_single_blocker_to_fix == "SEALED_TEST_USED_FOR_SELECTION"


def test_bridge_unsupported_family_dominates_before_profit_inventory(tmp_path: Path) -> None:
    candidates = [
        _candidate(
            "cand-001",
            decision="SHORTLISTED",
            family="perp_basis_mark_index_spread",
        ),
        _candidate(
            "cand-002",
            decision="SHORTLISTED",
            family="perp_basis_mark_index_spread",
            side_bias="short",
        ),
        _candidate("cand-003", decision="REJECTED"),
    ]
    candidate_set_path = _write_json(tmp_path / "strategy_idea_candidate_set.json", _candidate_set(candidates))
    ledger_path = _write_ledger(tmp_path / "search_ledger.jsonl", ["cand-001", "cand-002", "cand-003"])
    export_path = _write_json(tmp_path / "export.json", _export_manifest(["cand-001", "cand-002"]))
    bridge_path = _write_json(
        tmp_path / "bridge.json",
        {
            "schema_version": "strategy_idea_candidate_authoring_bridge.v1",
            "manifest_id": "bridge-fixture",
            "candidates": [
                {
                    "candidate_id": "cand-001",
                    "family": "perp_basis_mark_index_spread",
                    "status": "BLOCKED_UNSUPPORTED_FAMILY_MAPPING",
                    "symbols": ["BTCUSDT"],
                    "blockers": ["BLOCKED_UNSUPPORTED_FAMILY_MAPPING"],
                },
                {
                    "candidate_id": "cand-002",
                    "family": "perp_basis_mark_index_spread",
                    "status": "BLOCKED_UNSUPPORTED_FAMILY_MAPPING",
                    "symbols": ["ETHUSDT"],
                    "blockers": ["BLOCKED_UNSUPPORTED_FAMILY_MAPPING"],
                },
            ],
            "known_gaps": ["C9_V0_DOES_NOT_PROVE_ALPHA_OR_PROFIT"],
        },
    )

    check = build_profit_core_reality_check(
        candidate_set_path=candidate_set_path,
        search_ledger_path=ledger_path,
        export_manifest_path=export_path,
        authoring_bridge_path=bridge_path,
        created_at="2026-07-03T03:00:00Z",
    )

    assert check.bridge_summary.bridge_blocked_count == 2
    assert check.bridge_summary.blocked_by_family == {"perp_basis_mark_index_spread": 2}
    assert check.next_single_blocker_to_fix == "UNSUPPORTED_FAMILY_DOMINATES"
    assert "PROFIT_READINESS_INVENTORY_MISSING" in check.blocker_summary.blocker_counts


def test_bridged_candidates_remain_technical_only_not_live_permission(tmp_path: Path) -> None:
    candidates = [
        _candidate("cand-001", decision="SHORTLISTED"),
        _candidate("cand-002", decision="REJECTED"),
    ]
    candidate_set_path = _write_json(tmp_path / "strategy_idea_candidate_set.json", _candidate_set(candidates))
    ledger_path = _write_ledger(tmp_path / "search_ledger.jsonl", ["cand-001", "cand-002"])
    export_path = _write_json(tmp_path / "export.json", _export_manifest(["cand-001"]))
    bridge_path = _write_json(
        tmp_path / "bridge.json",
        {
            "schema_version": "strategy_idea_candidate_authoring_bridge.v1",
            "manifest_id": "bridge-fixture",
            "candidates": [
                {
                    "candidate_id": "cand-001",
                    "family": "perp_momentum_continuation",
                    "status": "BRIDGED",
                    "symbols": ["BTCUSDT"],
                    "blockers": [],
                }
            ],
            "known_gaps": ["PREP_WATCHDECK_COSTS_ARE_ESTIMATE_ONLY"],
        },
    )

    check = build_profit_core_reality_check(
        candidate_set_path=candidate_set_path,
        search_ledger_path=ledger_path,
        export_manifest_path=export_path,
        authoring_bridge_path=bridge_path,
        created_at="2026-07-03T03:00:00Z",
    )

    assert check.bridge_summary.technical_bridged_candidate_ids == ["cand-001"]
    assert check.bridge_summary.actual_cash_result_available is False
    assert check.next_single_blocker_to_fix == "BRIDGED_TECHNICAL_ONLY"
    assert check.boundary.permits_live_order is False
