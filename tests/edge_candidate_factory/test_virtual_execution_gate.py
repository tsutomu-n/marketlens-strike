from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.edge_candidate_factory.models import ArtifactRef
from sis.edge_candidate_factory.virtual_execution_gate import build_virtual_execution_gate

from .fixtures import artifact_ref


REPO_ROOT = Path(__file__).resolve().parents[2]
TS = datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc)


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _source_ref() -> ArtifactRef:
    return ArtifactRef.model_validate(
        artifact_ref(
            "backtest-kill-gate",
            "backtest_kill_gate.v1",
            "data/edge_candidate_factory/backtest_kill_gate/edge-cand-001.json",
        )
    )


def test_virtual_execution_gate_fixture_pass_is_not_actual_cash() -> None:
    gate = build_virtual_execution_gate(
        gate_id="virtual-gate-001",
        created_at=TS,
        candidate_id="edge-cand-001",
        venue_id="bitget",
        source_refs=[_source_ref()],
    )

    assert gate.gate_status == "VIRTUAL_PASSED_EXECUTION_LIFECYCLE"
    assert gate.actual_cash is False
    assert gate.cash_metric_basis == "virtual_exchange"
    assert gate.exchange_write_used is False
    assert gate.production_exchange_write_used is False
    assert gate.permits_live_order is False
    assert gate.boundary.live_allowed is False
    assert "virtual lifecycle is not actual cash evidence" in gate.known_gaps
    Draft202012Validator(_schema("virtual_execution_gate.v1.schema.json")).validate(
        gate.model_dump(mode="json")
    )


def test_virtual_execution_gate_order_lifecycle_failure_blocks() -> None:
    gate = build_virtual_execution_gate(
        gate_id="virtual-gate-001",
        created_at=TS,
        candidate_id="edge-cand-001",
        venue_id="bitget",
        source_refs=[_source_ref()],
        partial_fill_handled=False,
    )

    assert gate.gate_status == "VIRTUAL_FAILED_ORDER_LIFECYCLE"
    assert gate.recommended_action == "fix_virtual_order_lifecycle_before_actual_cash"
    assert any(
        condition.condition_id == "partial_fill_handled" and condition.condition_status == "FAIL"
        for condition in gate.conditions
    )


def test_virtual_execution_gate_reconciliation_mismatch_is_hard_failure() -> None:
    gate = build_virtual_execution_gate(
        gate_id="virtual-gate-001",
        created_at=TS,
        candidate_id="edge-cand-001",
        venue_id="bitget",
        source_refs=[_source_ref()],
        flat_reconciliation_passed=False,
    )

    assert gate.gate_status == "VIRTUAL_FAILED_RECONCILIATION"
    assert gate.recommended_action == "fix_virtual_reconciliation_before_actual_cash"
    assert gate.reconciliation_summary["flat_reconciliation_status"] == "FAIL"


def test_virtual_execution_gate_source_or_precheck_blocks() -> None:
    source_blocked = build_virtual_execution_gate(
        gate_id="virtual-gate-source",
        created_at=TS,
        candidate_id="edge-cand-001",
        venue_id="bitget",
        source_refs=[],
        source_available=False,
    )
    precheck_blocked = build_virtual_execution_gate(
        gate_id="virtual-gate-precheck",
        created_at=TS,
        candidate_id="edge-cand-001",
        venue_id="bitget",
        source_refs=[_source_ref()],
        execution_precheck_passed=False,
    )

    assert source_blocked.gate_status == "VIRTUAL_BLOCKED_SOURCE"
    assert precheck_blocked.gate_status == "VIRTUAL_BLOCKED_EXECUTION_PRECHECK"
