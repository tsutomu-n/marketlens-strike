from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.no_cash_backtest_gate import (
    GateThresholds,
    build_no_cash_backtest_gate,
)
from .test_profit_readiness_local_automation import _schema


runner = CliRunner()


def _decision_payload(
    *,
    decision: str = "BACKTEST_CANDIDATE_HOLD",
    event_count: int = 30,
    outcome_count: int = 30,
    critical_missing_count: int = 0,
    future_signal_source_count: int = 0,
    simulated_trade_count: int = 10,
    overall_grade: str = "local_simulation_from_existing_artifacts",
    pbo_status: str = "COMPUTED_PASS",
    bias_guard_status: str | None = "PASS",
    bias_guard_stop_reasons: list[str] | None = None,
    bias_guard_warning_codes: list[str] | None = None,
    include_evidence_grade: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "crypto_perp_backtest_candidate_pack.v1",
        "artifact_id": "decision-artifact",
        "created_at": "2026-07-06T08:00:00Z",
        "producer": {"tool": "sis", "command": "crypto-perp-backtest-candidate-pack"},
        "source_refs": [],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
        "pack_id": "pack-id",
        "decision": decision,
        "reason_codes": [],
        "event_count": event_count,
        "outcome_count": outcome_count,
        "artifact_paths": {},
        "summary": {
            "pbo_status": pbo_status,
            **({"bias_guard_status": bias_guard_status} if bias_guard_status is not None else {}),
            "bias_guard_stop_reasons": bias_guard_stop_reasons or [],
            "bias_guard_warning_codes": bias_guard_warning_codes or [],
        },
        "non_goal_flags": {
            "actual_cash_used": False,
            "profit_proven": False,
            "actual_cash_readiness_claimed": False,
            "tiny_live_readiness_claimed": False,
            "live_trading_readiness_claimed": False,
            "wallet_or_signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "backtest_promote_to_live_available": False,
            "ml_or_llm_trade_decision_used": False,
        },
    }
    if include_evidence_grade:
        payload["evidence_grade_summary"] = {
            "overall_grade": overall_grade,
            "strongest_evidence_level": "local_simulated_estimate",
            "basis": "timestamp_safe_local_simulation",
            "actual_cash_used": False,
            "profit_proven": False,
            "permits_live_order": False,
            "event_count": event_count,
            "simulated_trade_count": simulated_trade_count,
            "critical_missing_count": critical_missing_count,
            "future_signal_source_count": future_signal_source_count,
            "artifact_origin_counts": {"source_availability:existing": event_count},
            "source_available_counts": {"event": event_count, "bars": event_count},
            "source_missing_counts": {},
            "recomputed_minimal_artifact_count": 0,
            "existing_artifact_only": True,
            "known_limits": ["LOCAL_SIMULATION_ONLY"],
        }
    return payload


def _availability_payload(
    *,
    event_count: int = 30,
    critical_missing_count: int = 0,
    future_signal_source_count: int = 0,
    missing_optional_market_sources: bool = True,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index in range(event_count):
        event_id = f"event-{index:02d}"
        rows.append(
            {
                "event_id": event_id,
                "source_type": "bars",
                "is_available": critical_missing_count == 0,
                "missing_reason": None if critical_missing_count == 0 else "missing",
            }
        )
        for source_type in ("books", "trades", "replay"):
            rows.append(
                {
                    "event_id": event_id,
                    "source_type": source_type,
                    "is_available": not missing_optional_market_sources,
                    "missing_reason": "not_fetched" if missing_optional_market_sources else None,
                }
            )
    return {
        "schema_version": "crypto_perp_backtest_data_availability_ledger.v1",
        "summary": {
            "event_count": event_count,
            "row_count": len(rows),
            "critical_missing_count": critical_missing_count,
            "future_signal_source_count": future_signal_source_count,
            "network_used": False,
            "external_api_called": False,
        },
        "rows": rows,
        "paper_only": True,
        "permits_live_order": False,
    }


def _backtest_payload(
    *,
    event_count: int = 30,
    executed_trade_count: int = 10,
    unknown_count: int = 0,
    total_result_usd: str = "100",
    max_drawdown_usd: str = "-10",
    beats_no_trade: bool = True,
) -> dict[str, Any]:
    results = []
    for index in range(event_count):
        simulated = index < executed_trade_count
        results.append(
            {
                "event_id": f"event-{index:02d}",
                "outcome_id": f"outcome-{index:02d}",
                "selected_action": "CONTINUATION_LONG" if simulated else "NO_TRADE",
                "fill_status": "simulated" if simulated else "no_trade_baseline",
                "result_usd": "10" if simulated else "0",
                "metric": "cost_adjusted_cash_estimate_usd",
            }
        )
    return {
        "schema_version": "crypto_perp_backtest_result.v1",
        "status": "complete",
        "summary": {
            "event_count": event_count,
            "executed_trade_count": executed_trade_count,
            "no_trade_count": event_count - executed_trade_count,
            "unknown_count": unknown_count,
            "blocked_missing_action_row_count": 0,
            "total_result_usd": total_result_usd,
            "average_result_usd": "3.3333333333",
            "win_rate": "1",
            "max_drawdown_usd": max_drawdown_usd,
            "beats_no_trade": beats_no_trade,
        },
        "results": results,
        "paper_only": True,
        "profit_proven": False,
        "permits_live_order": False,
    }


def _stress_payload(total_result_usd: str = "50") -> dict[str, Any]:
    payload = _backtest_payload(total_result_usd=total_result_usd)
    payload["schema_version"] = "crypto_perp_backtest_stress_result.v1"
    payload["stress_kind"] = "row_level_conservative_cost_slippage"
    return payload


def _rolling_payload(status: str = "complete", event_count: int = 30) -> dict[str, Any]:
    return {
        "schema_version": "crypto_perp_backtest_rolling_stability_result.v1",
        "status": status,
        "summary": {"event_count": event_count, "min_events_for_stability": 30},
        "points": [],
        "paper_only": True,
        "permits_live_order": False,
    }


def _build_gate(**overrides: Any):
    payloads = {
        "decision": _decision_payload(),
        "data_availability": _availability_payload(),
        "backtest": _backtest_payload(),
        "stress": _stress_payload(),
        "rolling_stability": _rolling_payload(),
    }
    payloads.update(overrides)
    return build_no_cash_backtest_gate(
        decision=payloads["decision"],
        data_availability=payloads["data_availability"],
        backtest=payloads["backtest"],
        stress=payloads["stress"],
        rolling_stability=payloads["rolling_stability"],
        created_at="2026-07-06T08:00:00Z",
        input_artifacts={
            "decision": "decision.json",
            "data_availability": "data_availability_ledger.json",
            "backtest": "backtest_result.json",
            "stress": "stress_result.json",
            "rolling_stability": "rolling_stability_result.json",
        },
    )


def test_legacy_decision_without_evidence_grade_collects_more_data() -> None:
    gate = _build_gate(decision=_decision_payload(include_evidence_grade=False))

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "EVIDENCE_GRADE_SUMMARY_MISSING_LEGACY_COMPATIBILITY" in gate.reason_codes
    assert gate.paper_permission_granted is False


def test_backtest_collect_more_data_decision_collects_more_data() -> None:
    gate = _build_gate(decision=_decision_payload(decision="BACKTEST_COLLECT_MORE_DATA"))

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "BACKTEST_CANDIDATE_PACK_COLLECT_MORE_DATA" in gate.reason_codes


def test_blocked_bias_guard_rejects_even_when_candidate_decision_is_hold() -> None:
    gate = _build_gate(
        decision=_decision_payload(
            bias_guard_status="BLOCKED",
            bias_guard_stop_reasons=["BIAS_GUARD_FAILED_stress_cash_non_negative"],
        )
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_REJECT"
    assert "BIAS_GUARD_BLOCKED" in gate.reason_codes
    assert "BIAS_GUARD_FAILED_stress_cash_non_negative" in gate.reason_codes
    assert gate.summary["bias_guard_status"] == "BLOCKED"


def test_blocked_bias_guard_rejects_even_with_collect_blockers() -> None:
    gate = _build_gate(
        decision=_decision_payload(
            decision="BACKTEST_COLLECT_MORE_DATA",
            bias_guard_status="BLOCKED",
            bias_guard_stop_reasons=["BIAS_GUARD_FAILED_profit_concentration"],
            pbo_status="INPUT_THRESHOLD_MET",
        )
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_REJECT"
    assert "BIAS_GUARD_BLOCKED" in gate.reason_codes
    assert "BIAS_GUARD_FAILED_profit_concentration" in gate.reason_codes


def test_bias_guard_warning_is_preserved_without_blocking_existing_gate_checks() -> None:
    warning = "BIAS_GUARD_WARNING_stress_cash_non_negative"
    gate = _build_gate(
        decision=_decision_payload(bias_guard_warning_codes=[warning]),
        data_availability=_availability_payload(missing_optional_market_sources=False),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_HOLD"
    assert gate.summary["bias_guard_status"] == "PASS"
    assert gate.summary["bias_guard_warning_codes"] == [warning]
    assert warning in gate.known_gaps
    assert warning not in gate.reason_codes


@pytest.mark.parametrize("status", [None, "NOT_RUN", "UNKNOWN"])
def test_missing_or_unknown_bias_guard_collects_more_data(status: str | None) -> None:
    gate = _build_gate(decision=_decision_payload(bias_guard_status=status))

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "BIAS_GUARD_STATUS_MISSING_OR_UNKNOWN" in gate.reason_codes


@pytest.mark.parametrize(
    ("decision", "rolling_status", "pbo_status"),
    [
        ("GARBAGE", "complete", "ESTIMATED"),
        ("BACKTEST_CANDIDATE_HOLD", "GARBAGE", "ESTIMATED"),
        ("BACKTEST_CANDIDATE_HOLD", "complete", "GARBAGE"),
    ],
)
def test_unknown_required_gate_state_never_holds(
    decision: str,
    rolling_status: str,
    pbo_status: str,
) -> None:
    gate = _build_gate(
        decision=_decision_payload(decision=decision, pbo_status=pbo_status),
        rolling_stability=_rolling_payload(status=rolling_status),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert gate.blockers


def test_unknown_evidence_grade_never_holds() -> None:
    gate = _build_gate(
        decision=_decision_payload(overall_grade="MYSTERY"),
        data_availability=_availability_payload(missing_optional_market_sources=False),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "EVIDENCE_GRADE_STATUS_MISSING_OR_UNKNOWN" in gate.reason_codes


def test_required_books_trades_replay_blockers_never_hold() -> None:
    payloads = {
        "decision": _decision_payload(),
        "data_availability": _availability_payload(missing_optional_market_sources=True),
        "backtest": _backtest_payload(),
        "stress": _stress_payload(),
        "rolling_stability": _rolling_payload(),
    }
    gate = build_no_cash_backtest_gate(
        **payloads,
        created_at="2026-07-06T08:00:00Z",
        input_artifacts={},
        thresholds=GateThresholds(require_books_trades_replay=True),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert gate.blockers


def test_candidate_non_hold_reason_codes_propagate_through_gate() -> None:
    decision = _decision_payload(
        decision="BACKTEST_COLLECT_MORE_DATA", pbo_status="INPUT_THRESHOLD_MET"
    )
    decision["reason_codes"] = ["PBO_NOT_COMPUTED", "POSITION_OVERLAP_NOT_ACCOUNTED"]

    gate = _build_gate(
        decision=decision,
        data_availability=_availability_payload(missing_optional_market_sources=False),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "POSITION_OVERLAP_NOT_ACCOUNTED" in gate.reason_codes
    blocker_codes = [blocker.code for blocker in gate.blockers]
    assert len(blocker_codes) == len(set(blocker_codes))


def test_pbo_input_threshold_without_computation_never_holds() -> None:
    gate = _build_gate(
        decision=_decision_payload(pbo_status="INPUT_THRESHOLD_MET"),
        data_availability=_availability_payload(missing_optional_market_sources=False),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "PBO_NOT_COMPUTED" in gate.reason_codes


def test_critical_missing_source_collects_more_data() -> None:
    gate = _build_gate(
        decision=_decision_payload(
            critical_missing_count=1,
            overall_grade="insufficient_source_for_local_simulation",
        ),
        data_availability=_availability_payload(critical_missing_count=1),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "CRITICAL_SIGNAL_SOURCE_MISSING" in gate.reason_codes
    assert "CRITICAL_SIGNAL_SOURCE_MISSING_BARS" in gate.reason_codes
    bar_blocker = next(
        blocker
        for blocker in gate.blockers
        if blocker.code == "CRITICAL_SIGNAL_SOURCE_MISSING_BARS"
    )
    assert bar_blocker.source_type == "bars"
    assert bar_blocker.metric == "critical_missing_count"


def test_future_signal_source_collects_more_data() -> None:
    gate = _build_gate(
        decision=_decision_payload(future_signal_source_count=1),
        data_availability=_availability_payload(future_signal_source_count=1),
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "FUTURE_SIGNAL_SOURCE_USED" in gate.reason_codes


def test_rolling_stability_sample_insufficient_collects_more_data() -> None:
    gate = _build_gate(rolling_stability=_rolling_payload(status="sample_insufficient"))

    assert gate.gate_decision == "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    assert "ROLLING_STABILITY_SAMPLE_INSUFFICIENT" in gate.reason_codes


def test_no_trade_not_beaten_never_holds() -> None:
    gate = _build_gate(
        backtest=_backtest_payload(total_result_usd="0", beats_no_trade=False),
        stress=_stress_payload(total_result_usd="10"),
    )

    assert gate.gate_decision in {
        "NO_CASH_BACKTEST_REJECT",
        "NO_CASH_BACKTEST_COLLECT_MORE_DATA",
    }
    assert gate.gate_decision != "NO_CASH_BACKTEST_HOLD"
    assert "NO_TRADE_NOT_BEATEN_AFTER_COST" in gate.reason_codes


def test_existing_artifact_positive_simulation_can_hold_without_paper_permission() -> None:
    gate = _build_gate(
        data_availability=_availability_payload(missing_optional_market_sources=False)
    )

    assert gate.gate_decision == "NO_CASH_BACKTEST_HOLD"
    assert gate.reason_codes == [
        "NO_CASH_BACKTEST_GATE_HOLD_FOR_HUMAN_REVIEW",
        "PAPER_PERMISSION_NOT_GRANTED",
        "ACTUAL_CASH_NOT_IN_SCOPE",
    ]
    assert gate.permits_paper_order is False
    assert gate.paper_permission_granted is False
    assert gate.actual_cash_used is False
    assert gate.permits_live_order is False


def test_no_cash_backtest_gate_schema_validates_output() -> None:
    gate = _build_gate()
    schema = _schema("crypto_perp_no_cash_backtest_gate.v1.schema.json")

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(gate.model_dump(mode="json"))


def test_cli_writes_gate_artifacts_and_boundary_stdout(tmp_path: Path) -> None:
    inputs = {
        "decision": _decision_payload(decision="BACKTEST_COLLECT_MORE_DATA"),
        "data_availability": _availability_payload(),
        "backtest": _backtest_payload(),
        "stress": _stress_payload(),
        "rolling_stability": _rolling_payload(),
    }
    paths: dict[str, Path] = {}
    for name, payload in inputs.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path

    result = runner.invoke(
        app,
        [
            "crypto-perp-no-cash-backtest-gate",
            "--decision",
            str(paths["decision"]),
            "--data-availability",
            str(paths["data_availability"]),
            "--backtest",
            str(paths["backtest"]),
            "--stress",
            str(paths["stress"]),
            "--rolling-stability",
            str(paths["rolling_stability"]),
            "--out",
            str(tmp_path / "gate"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "actual_cash_used=false" in result.stdout
    assert "paper_permission_granted=false" in result.stdout
    assert "status=blocked" in result.stdout
    assert "gate_decision=NO_CASH_BACKTEST_COLLECT_MORE_DATA" in result.stdout
    gate_path = tmp_path / "gate/no_cash_backtest_gate.json"
    report_path = tmp_path / "gate/no_cash_backtest_gate.md"
    assert gate_path.exists()
    assert report_path.exists()
    payload = json.loads(gate_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("crypto_perp_no_cash_backtest_gate.v1.schema.json")).validate(
        payload
    )
    assert payload["paper_permission_granted"] is False
    assert payload["permits_paper_order"] is False


def test_missing_optional_books_trades_replay_are_known_gaps_when_not_required() -> None:
    gate = _build_gate()

    assert gate.gate_decision == "NO_CASH_BACKTEST_HOLD"
    assert "BOOKS_SOURCE_MISSING" in gate.known_gaps
    assert "TRADES_SOURCE_MISSING" in gate.known_gaps
    assert "REPLAY_SOURCE_MISSING" in gate.known_gaps
    assert not any(blocker.code.endswith("SOURCE_MISSING") for blocker in gate.blockers)
