from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.edge_candidate_factory.backtest_inputs import extract_backtest_metrics
from sis.edge_candidate_factory.backtest_kill_gate import build_backtest_kill_gate
from sis.edge_candidate_factory.generator import (
    EdgeCandidateFactoryConfig,
    build_edge_candidate_factory_run,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TS = datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc)


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _run():
    return build_edge_candidate_factory_run(
        EdgeCandidateFactoryConfig(
            run_id="edge-backtest-001",
            generated_at=TS,
            source_root="data/prep/watchdeck",
            symbols=["BTCUSDT"],
            families=["liquidation_exhaustion_reversal"],
            candidate_cap=1,
        )
    )


def _gate_from_metrics(
    payloads: list[dict],
    *,
    family_id: str = "liquidation_exhaustion_reversal",
    source_available: bool = True,
    bridge_technical_ready: bool = True,
    execution_precheck_passed: bool = True,
):
    run = _run()
    return build_backtest_kill_gate(
        gate_id="backtest-gate-001",
        created_at=TS,
        candidate_id=run.report.candidate_cards[0].candidate_id,
        family_id=family_id,
        candidate_source_refs=run.report.source_refs,
        multiplicity_account=run.multiplicity_account,
        metrics=extract_backtest_metrics(payloads),
        source_available=source_available,
        bridge_technical_ready=bridge_technical_ready,
        execution_precheck_passed=execution_precheck_passed,
    )


def test_backtest_kill_gate_missing_metrics_is_inconclusive() -> None:
    gate = _gate_from_metrics([{"summary": {}}])

    assert gate.gate_status == "INCONCLUSIVE_DATA"
    assert gate.metrics.after_cost_edge_over_no_trade_usd is None
    assert any(
        condition.condition_id == "after_cost_edge_positive"
        and condition.condition_status == "NOT_ESTIMABLE"
        for condition in gate.conditions
    )
    assert gate.boundary.paper_execution_allowed is False
    Draft202012Validator(_schema("backtest_kill_gate.v1.schema.json")).validate(
        gate.model_dump(mode="json")
    )


def test_backtest_kill_gate_no_trade_underperformance_kills_candidate() -> None:
    gate = _gate_from_metrics(
        [
            {
                "summary": {
                    "event_count": 120,
                    "closed_trade_count": 80,
                    "after_cost_edge_over_no_trade_usd": -1.0,
                    "stress_edge_over_no_trade_usd": -2.0,
                    "largest_loss_usd": -100.0,
                    "profit_concentration": 0.25,
                    "source_gap_count": 0,
                    "unexecutable_reason_count": 0,
                }
            }
        ]
    )

    assert gate.gate_status == "KILL"
    assert gate.recommended_action == "kill_candidate"


def test_backtest_pass_stays_research_only_not_virtual_shortlist() -> None:
    gate = _gate_from_metrics(
        [
            {
                "summary": {
                    "event_count": 120,
                    "closed_trade_count": 80,
                    "after_cost_edge_over_no_trade_usd": 10.0,
                    "stress_edge_over_no_trade_usd": 4.0,
                    "largest_loss_usd": -100.0,
                    "profit_concentration": 0.25,
                    "source_gap_count": 0,
                    "unexecutable_reason_count": 0,
                }
            }
        ]
    )

    assert gate.gate_status == "RESEARCH_ONLY"
    assert gate.gate_status != "SHORTLIST_FOR_VIRTUAL"
    assert gate.recommended_action == "manual_review_before_virtual_gate"


def test_rare_event_low_count_is_not_immediate_kill() -> None:
    gate = _gate_from_metrics(
        [
            {
                "summary": {
                    "event_count": 5,
                    "closed_trade_count": 5,
                    "after_cost_edge_over_no_trade_usd": 10.0,
                    "stress_edge_over_no_trade_usd": 4.0,
                    "largest_loss_usd": -100.0,
                    "profit_concentration": 0.25,
                    "source_gap_count": 0,
                    "unexecutable_reason_count": 0,
                }
            }
        ],
        family_id="cross_market_basis_dislocation",
    )

    assert gate.gate_status == "RESEARCH_ONLY"
    assert any(
        condition.condition_id == "event_count_meets_family_threshold"
        and condition.condition_status == "FAIL"
        for condition in gate.conditions
    )


def test_source_missing_is_inconclusive_not_kill() -> None:
    gate = _gate_from_metrics(
        [
            {
                "summary": {
                    "event_count": 120,
                    "closed_trade_count": 80,
                    "after_cost_edge_over_no_trade_usd": 10.0,
                    "stress_edge_over_no_trade_usd": 4.0,
                    "largest_loss_usd": -100.0,
                    "profit_concentration": 0.25,
                }
            }
        ],
        source_available=False,
    )

    assert gate.gate_status == "INCONCLUSIVE_DATA"
    assert gate.recommended_action == "collect_missing_source_or_multiplicity_evidence"


def test_bridge_or_execution_blocker_is_inconclusive() -> None:
    gate = _gate_from_metrics(
        [
            {
                "summary": {
                    "event_count": 120,
                    "closed_trade_count": 80,
                    "after_cost_edge_over_no_trade_usd": 10.0,
                    "stress_edge_over_no_trade_usd": 4.0,
                    "largest_loss_usd": -100.0,
                    "profit_concentration": 0.25,
                    "unexecutable_reason_count": 1,
                }
            }
        ],
        bridge_technical_ready=False,
        execution_precheck_passed=False,
    )

    assert gate.gate_status == "INCONCLUSIVE_DATA"
    assert gate.recommended_action == "resolve_backtest_bridge_or_execution_precheck_blockers"
    assert "bridge technical readiness failed" in gate.known_gaps
    assert "execution precheck failed" in gate.known_gaps
    assert "unexecutable reasons present" in gate.known_gaps
    assert any(
        condition.condition_id == "unexecutable_reason_count_zero"
        and condition.condition_status == "FAIL"
        for condition in gate.conditions
    )
