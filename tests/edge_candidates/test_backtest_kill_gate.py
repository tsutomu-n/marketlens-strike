from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.edge_candidates.backtest_kill_gate import (
    BacktestKillGateInput,
    build_backtest_kill_gate,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def valid_gate_input_payload() -> dict:
    return {
        "candidate_id": "idea-cand-001",
        "mode": "verification_throughput",
        "family_id": "intraday_breakout",
        "event_count": 120,
        "closed_trade_count": 80,
        "no_trade_comparison_present": True,
        "after_cost_edge_over_no_trade": 1.2,
        "stress_edge_over_no_trade": 0.4,
        "largest_loss_usd": -12.5,
        "profit_concentration": 0.25,
        "regime_stability": "PASS",
        "source_gap_count": 0,
        "unexecutable_reason_count": 0,
        "selection_adjustment_status": "AVAILABLE",
        "family_event_count_policy": {
            "min_event_count_default": 100,
            "insufficient_data_state": "INCONCLUSIVE_DATA",
        },
        "execution_candidate": True,
    }


def test_backtest_kill_gate_shortlists_without_permission() -> None:
    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(valid_gate_input_payload()),
        gate_id="gate-001",
        evaluated_at="2026-06-30T11:36:00Z",
    )

    assert gate.gate_state == "SHORTLIST_FOR_VIRTUAL"
    assert gate.actual_cash is False
    assert gate.permits_live_order is False
    assert gate.permits_paper_order is False
    assert gate.permits_actual_cash is False
    assert gate.summary["no_trade_comparison_present"] is True


def test_backtest_kill_gate_stops_missing_no_trade_comparison() -> None:
    payload = valid_gate_input_payload()
    payload["no_trade_comparison_present"] = False

    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(payload),
        gate_id="gate-001",
        evaluated_at="2026-06-30T11:36:00Z",
    )

    assert gate.gate_state == "INCONCLUSIVE_DATA"
    assert "missing_no_trade_comparison" in gate.blocker_codes


def test_backtest_kill_gate_kills_nonpositive_after_cost_edge() -> None:
    payload = valid_gate_input_payload()
    payload["after_cost_edge_over_no_trade"] = 0

    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(payload),
        gate_id="gate-001",
        evaluated_at="2026-06-30T11:36:00Z",
    )

    assert gate.gate_state == "KILL"
    assert "after_cost_edge_over_no_trade_nonpositive" in gate.blocker_codes


def test_backtest_kill_gate_stops_execution_candidate_with_source_gap() -> None:
    payload = valid_gate_input_payload()
    payload["source_gap_count"] = 1

    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(payload),
        gate_id="gate-001",
        evaluated_at="2026-06-30T11:36:00Z",
    )

    assert gate.gate_state == "INCONCLUSIVE_DATA"
    assert "source_gap_for_execution_candidate" in gate.blocker_codes


def test_backtest_kill_gate_uses_family_specific_event_count_policy() -> None:
    payload = valid_gate_input_payload()
    payload["event_count"] = 3
    payload["family_event_count_policy"] = {
        "min_event_count_default": 30,
        "insufficient_data_state": "RESEARCH_ONLY",
    }

    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(payload),
        gate_id="gate-001",
        evaluated_at="2026-06-30T11:36:00Z",
    )

    assert gate.gate_state == "RESEARCH_ONLY"
    assert "event_count_below_family_policy" in gate.blocker_codes


def test_backtest_kill_gate_schema_validates_output() -> None:
    gate = build_backtest_kill_gate(
        BacktestKillGateInput.model_validate(valid_gate_input_payload()),
        gate_id="gate-001",
        evaluated_at="2026-06-30T11:36:00Z",
    )
    payload = json.loads(json.dumps(gate.model_dump(mode="json")))
    schema = json.loads(
        (REPO_ROOT / "schemas/backtest_kill_gate.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
