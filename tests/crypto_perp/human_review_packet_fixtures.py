from __future__ import annotations

import json
from pathlib import Path

from sis.crypto_perp.human_review_packet import (
    EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES,
    _LINEAGE_VERIFIED_TOKEN,
    _build_human_review_packet,
    _decide,
)
from sis.crypto_perp.io import file_artifact_ref


ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _producer(command: str) -> dict:
    return {"tool": "sis", "command": command}


def _boundary() -> dict:
    return {
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _no_goal_flags() -> dict:
    return {
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
    }


def _selection_manifest() -> dict:
    return {
        "schema_version": "crypto_perp_real_market_no_cash_sample.v1",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-real-market-no-cash-sample"),
        "symbol": "BTCUSDT",
        "target_event_count": 30,
        "event_count": 30,
        "outcome_count": 30,
        "event_set": ["event-1"],
        "outcome_set": ["outcome-1"],
        "execution_windows": [
            {
                "event_id": "event-1",
                "outcome_id": "outcome-1",
                "information_cutoff_at": "2026-07-09T00:00:00Z",
                "entry_at": "2026-07-09T00:05:00Z",
                "settled_at": "2026-07-09T01:05:00Z",
                "horizon_minutes": 60,
            }
        ],
        "execution_window_coverage": {
            "raw_candidate_count": 30,
            "eligible_candidate_count": 30,
            "rejected_candidate_count": 0,
            "rejection_reason_counts": {},
            "entry_policy": "first_complete_bar_open_exactly_one_interval_after_cutoff",
            "full_horizon_contiguous_required": True,
        },
        "selection_policy": (
            "full_horizon_eligible_then_time_evenly_spaced_before_outcome; "
            "no outcome-favorable filtering; require_ticker_coverage=true"
        ),
        "source_coverage": {
            "ticker_available_count": 30,
            "funding_available_count": 30,
            "require_ticker_coverage": True,
            "ticker_covered_candidate_count": 30,
            "ticker_source_root": "source-root",
            "funding_source_root": "source-root",
            "ticker_max_staleness_seconds": 900,
        },
        "source_availability_count": 30,
        "artifact_paths": {
            "input_csv": "input.csv",
            "tournament_rows_v2": "rows.json",
            "bias_guard": "guard.json",
            "source_availability": ["source.json"],
        },
        "known_gaps": ["BOOKS_SOURCE_MISSING", "LOCAL_SIMULATION_ONLY"],
        "non_goal_flags": {
            "paper_permission_granted": False,
            "actual_cash_used": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "profit_proven": False,
            "real_market_public_source_used": True,
            "fixture_only": False,
        },
    }


def _decision() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_candidate_pack.v1",
        "artifact_id": "decision-artifact",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-backtest-candidate-pack"),
        "source_refs": [],
        "boundary": _boundary(),
        "pack_id": "pack-1",
        "decision": "BACKTEST_CANDIDATE_HOLD",
        "reason_codes": ["BACKTEST_CANDIDATE_HOLD"],
        "event_count": 30,
        "outcome_count": 30,
        "artifact_paths": {},
        "summary": {"pbo_status": "COMPUTED_PASS", "bias_guard_status": "PASS"},
        "evidence_grade_summary": {
            "strongest_evidence_level": "recomputed_minimal_simulated_estimate",
            "event_count": 30,
            "critical_missing_count": 0,
        },
        "non_goal_flags": _no_goal_flags(),
    }


def _tournament_rows() -> dict:
    return {
        "schema_version": "crypto_perp_tournament_rows.v2",
        "artifact_id": "rows-1",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-tournament-rows"),
        "source_refs": [],
        "boundary": _boundary(),
        "row_set_id": "row-set-1",
        "primary_metric": "cost_adjusted_cash_estimate_usd",
        "event_set": ["event-1"],
        "rows": [
            {
                "event_id": "event-1",
                "action": "CONTINUATION_LONG",
                "before_cost_proxy_usd": "1",
                "fee_estimate_usd": "0.1",
                "funding_estimate_usd": "0",
                "slippage_estimate_usd": "0.1",
                "operator_time_cost_usd": "0",
                "cost_adjusted_cash_estimate_usd": "0.8",
                "stress_cash_estimate_usd": "0.7",
                "evidence_level": "cost_adjusted_estimate",
                "actual_cash_result_usd": None,
                "market_adjusted_return": "0.01",
                "operator_time_minutes": "0",
                "known_gaps": [],
                "near_miss": False,
            }
        ],
        "known_gaps": [],
        "summary": {
            "execution_windows": {
                "event-1": {
                    "entry_at": "2026-07-09T00:05:00Z",
                    "settled_at": "2026-07-09T01:05:00Z",
                    "horizon_minutes": 60,
                }
            }
        },
    }


def _bias_guard(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_bias_guard.v1",
        "artifact_id": "guard-1",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-bias-guard"),
        "source_refs": [],
        "boundary": _boundary(),
        "guard_id": "guard-1",
        "event_set": ["event-1"],
        "guard_status": "PASS",
        "pbo_status": "COMPUTED_PASS",
        "event_count": 1,
        "min_events_for_pbo": 30,
        "fold_count": 0,
        "max_profit_concentration": "0.5",
        "checks": [],
        "stop_reasons": [],
        "known_gaps": [],
        "summary": {"pbo_computed": False},
    }
    payload.update(overrides)
    return payload


def _data_availability() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_data_availability_ledger.v1",
        "summary": {
            "event_count": 30,
            "row_count": 1,
            "critical_missing_count": 0,
            "future_signal_source_count": 0,
            "network_used": False,
            "external_api_called": False,
        },
        "rows": [
            {
                "timestamp": "2026-07-09T00:00:00Z",
                "symbol": "BTCUSDT",
                "event_id": "event-1",
                "source_type": "bars",
                "source_artifact_id": "source-1",
                "available_at": "2026-07-09T00:00:00Z",
                "used_at": "2026-07-09T00:00:00Z",
                "usage_role": "signal_input",
                "is_available": True,
                "missing_reason": None,
                "staleness_seconds": 0,
                "row_count": 100,
                "source_ref_count": 0,
                "available_at_policy": "information_cutoff_fallback",
                "metadata": {},
            }
        ],
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _profit_robustness() -> dict:
    return {
        "holding_minutes": 60,
        "holding_minutes_source": "tournament_rows.summary.execution_windows",
        "execution_windows_verified": True,
        "peak_concurrent_positions": 1,
        "peak_gross_notional_usd": "100",
        "market_episode_count": 1,
        "market_episode_win_count": 1,
        "market_episode_totals_usd": ["2.4"],
        "non_overlapping_trade_count": 1,
        "single_position_total_result_usd": "2.4",
        "position_overlap_accounted": True,
        "gross_profit_usd": "2.4",
        "gross_loss_usd": "0",
        "profit_factor": None,
        "top_3_win_share_of_gross_profit": "1",
        "break_even_extra_cost_per_trade_usd": "2.4",
        "signal_score_result_correlation": None,
        "static_action_totals_usd": {"CONTINUATION_LONG": "2.4"},
        "best_static_action": "CONTINUATION_LONG",
        "best_static_total_result_usd": "2.4",
        "selector_beats_best_static_action": False,
        "action_performance": {
            "CONTINUATION_LONG": {
                "trade_count": 1,
                "win_count": 1,
                "loss_count": 0,
                "total_result_usd": "2.4",
            }
        },
    }


def _result_summary(total: str) -> dict:
    return {
        "event_count": 30,
        "executed_trade_count": 13,
        "no_trade_count": 17,
        "unknown_count": 0,
        "blocked_missing_action_row_count": 0,
        "total_result_usd": total,
        "average_result_usd": "0.08",
        "win_rate": "0.6",
        "max_drawdown_usd": "-0.5",
        "beats_no_trade": True,
        "profit_robustness": _profit_robustness(),
    }


def _result_row(total: str) -> dict:
    return {
        "event_id": "event-1",
        "outcome_id": "outcome-1",
        "selected_action": "CONTINUATION_LONG",
        "fill_status": "filled",
        "metric": "cost_adjusted_cash_estimate_usd",
        "result_usd": total,
    }


def _rolling_stability() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_rolling_stability_result.v1",
        "status": "complete",
        "summary": {
            "event_count": 30,
            "min_events_for_stability": 30,
            "final_cumulative_result_usd": "2.4",
            "min_cumulative_result_usd": "0",
            "max_cumulative_result_usd": "2.4",
        },
        "points": [{"index": 1, "event_id": "event-1", "cumulative_result_usd": "2.4"}],
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }


def _backtest() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_result.v1",
        "status": "complete",
        "summary": _result_summary("2.4"),
        "results": [_result_row("2.4")],
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "profit_proven": False,
    }


def _stress() -> dict:
    return {
        "schema_version": "crypto_perp_backtest_stress_result.v1",
        "status": "complete",
        "stress_kind": "extra_slippage",
        "summary": _result_summary("2.1"),
        "results": [_result_row("2.1")],
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
        "profit_proven": False,
    }


def _gate(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_no_cash_backtest_gate.v1",
        "artifact_id": "gate-1",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-no-cash-backtest-gate"),
        "source_refs": [],
        "boundary": _boundary(),
        "gate_decision": "NO_CASH_BACKTEST_HOLD",
        "reason_codes": ["NO_CASH_BACKTEST_HOLD"],
        "blockers": [],
        "known_gaps": ["TRADES_SOURCE_MISSING"],
        "thresholds": {
            "min_events_for_gate": 30,
            "min_simulated_trades": 10,
            "max_largest_loss_to_total_result_ratio": "1",
            "max_drawdown_to_total_result_ratio": "1",
            "require_books_trades_replay": False,
        },
        "summary": {
            "event_count": 30,
            "outcome_count": 30,
            "critical_missing_count": 0,
            "unknown_count": 0,
            "executed_trade_count": 13,
            "pbo_status": "COMPUTED_PASS",
            "rolling_stability_status": "complete",
        },
        "input_artifacts": {},
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    payload.update(overrides)
    return payload


def _kill(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_no_trade_kill_report.v1",
        "artifact_id": "kill-1",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-no-trade-kill-report"),
        "source_refs": [],
        "boundary": _boundary(),
        "input_artifacts": {},
        "event_count": 30,
        "trade_event_count": 13,
        "no_trade_win_count": 0,
        "trade_action_win_count": 8,
        "selected_action_counts": {"CONTINUATION_LONG": 13},
        "cost_adjusted_delta_vs_no_trade": "2.4",
        "stress_delta_vs_no_trade": "2.1",
        "fee_drag": "0.1",
        "funding_drag": "0",
        "slippage_drag": "0.1",
        "largest_win_concentration": "0.4",
        "top2_win_concentration": "0.6",
        "episode_concentration_estimated": True,
        "episode_largest_win_concentration": "0.4",
        "episode_top2_win_concentration": "0.6",
        "largest_loss_concentration": "0.5",
        "total_loss_usd": "-1",
        "largest_loss_to_total_result_ratio": "0.4",
        "kill_decision": "HOLD_FOR_LEADERBOARD",
        "reason_codes": ["NO_TRADE_KILL_REPORT_HOLD_FOR_LEADERBOARD"],
        "thresholds": {},
        "summary": {},
        "known_gaps": ["NOT_ACTUAL_CASH"],
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    payload.update(overrides)
    return payload


def _leaderboard(**overrides) -> dict:
    payload = {
        "schema_version": "crypto_perp_candidate_leaderboard.v1",
        "artifact_id": "leaderboard-1",
        "created_at": "2026-07-09T00:00:00Z",
        "producer": _producer("crypto-perp-candidate-leaderboard"),
        "source_refs": [],
        "boundary": _boundary(),
        "input_artifacts": {},
        "rows": [
            {
                "rank": 1,
                "candidate_id": "candidate-1",
                "symbol": "BTCUSDT",
                "timeframe": "5m",
                "family": "continuation",
                "setup_type": "continuation",
                "ranking_score": "1",
                "source_quality_score": "1",
                "cost_adjusted_total": "2.4",
                "stress_total": "2.1",
                "no_trade_delta": "2.4",
                "executed_trade_count": 13,
                "win_rate": "0.6",
                "payoff_ratio": "1.5",
                "max_drawdown": "-1",
                "loss_concentration": "0.5",
                "profit_concentration": "0.4",
                "pbo_status": "COMPUTED_PASS",
                "rolling_stability_status": "complete",
                "gate_decision": "NO_CASH_BACKTEST_HOLD",
                "kill_decision": "HOLD_FOR_LEADERBOARD",
                "next_action": "HOLD_FOR_HUMAN_REVIEW",
                "reason_codes": [],
                "known_gaps": [],
            }
        ],
        "summary": {},
        "known_gaps": ["NOT_LIVE_READINESS"],
        "paper_permission_granted": False,
        "permits_paper_order": False,
        "permits_live_order": False,
        "actual_cash_used": False,
        "profit_proven": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "live_order_submitted": False,
    }
    payload.update(overrides)
    return payload


def _packet(**overrides) -> dict:
    return _build_human_review_packet(
        selection_manifest=overrides.pop("selection_manifest", _selection_manifest()),
        decision=overrides.pop("decision", _decision()),
        tournament_rows=overrides.pop("tournament_rows", _tournament_rows()),
        bias_guard=overrides.pop("bias_guard", _bias_guard()),
        data_availability=overrides.pop("data_availability", _data_availability()),
        signal_rows=overrides.pop("signal_rows", []),
        backtest=overrides.pop("backtest", _backtest()),
        stress=overrides.pop("stress", _stress()),
        rolling_stability=overrides.pop("rolling_stability", _rolling_stability()),
        gate=overrides.pop("gate", _gate()),
        kill_report=overrides.pop("kill_report", _kill()),
        leaderboard=overrides.pop("leaderboard", _leaderboard()),
        created_at="2026-07-09T00:00:00Z",
        input_artifacts=overrides.pop(
            "input_artifacts",
            {name: f"{name}.json" for name in EXPECTED_HUMAN_REVIEW_INPUT_ARTIFACT_NAMES},
        ),
        source_refs=[],
        _lineage_token=overrides.pop("_lineage_token", _LINEAGE_VERIFIED_TOKEN),
    )


def _decide_state(**overrides) -> tuple[str, list[str]]:
    values = {
        "boundary_violation": False,
        "lineage_violations": [],
        "candidate_decision": "BACKTEST_CANDIDATE_HOLD",
        "bias_guard_status": "PASS",
        "bias_guard_stop_reasons": [],
        "pbo_status": "COMPUTED_PASS",
        "pbo_evidence_verified": True,
        "gate_decision": "NO_CASH_BACKTEST_HOLD",
        "kill_decision": "HOLD_FOR_LEADERBOARD",
        "top_next_action": "HOLD_FOR_HUMAN_REVIEW",
    }
    values.update(overrides)
    return _decide(**values)


def _write_ready_cli_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "selection": tmp_path / "selection_manifest.json",
        "decision": tmp_path / "decision.json",
        "rows": tmp_path / "tournament_rows_v2.json",
        "guard": tmp_path / "bias_guard.json",
        "availability": tmp_path / "data_availability_ledger.json",
        "signal": tmp_path / "signal_rows.jsonl",
        "backtest": tmp_path / "backtest.json",
        "stress": tmp_path / "stress.json",
        "rolling": tmp_path / "rolling_stability.json",
        "gate": tmp_path / "gate.json",
        "kill": tmp_path / "kill.json",
        "leaderboard": tmp_path / "leaderboard.json",
    }
    selection = _selection_manifest()
    selection.update({"event_count": 1, "outcome_count": 1})
    paths["selection"].write_text(json.dumps(selection), encoding="utf-8")
    rows = _tournament_rows()
    paths["rows"].write_text(json.dumps(rows), encoding="utf-8")
    guard = _bias_guard(
        event_count=1,
        source_refs=[file_artifact_ref(paths["rows"], "crypto_perp_tournament_rows.v2")],
    )
    paths["guard"].write_text(json.dumps(guard), encoding="utf-8")
    availability = _data_availability()
    availability["summary"]["event_count"] = 1
    paths["availability"].write_text(json.dumps(availability), encoding="utf-8")
    paths["signal"].write_text(
        json.dumps(
            {
                "timestamp": "2026-07-09T00:00:00Z",
                "entry_at": "2026-07-09T00:05:00Z",
                "outcome_horizon_minutes": 60,
                "symbol": "BTCUSDT",
                "event_id": "event-1",
                "outcome_id": "outcome-1",
                "information_cutoff_at": "2026-07-09T00:00:00Z",
                "source_availability_id": "source-1",
                "feature_pack_id": "feature-1",
                "edge_score_id": "edge-1",
                "selected_action": "CONTINUATION_LONG",
                "signal_score": "1",
                "entry_allowed": True,
                "no_trade_reason": [],
                "artifact_origin": {},
            }
        )
        + chr(10),
        encoding="utf-8",
    )
    backtest = _backtest()
    backtest["summary"].update({"event_count": 1, "executed_trade_count": 1})
    paths["backtest"].write_text(json.dumps(backtest), encoding="utf-8")
    stress = _stress()
    stress["summary"]["event_count"] = 1
    paths["stress"].write_text(json.dumps(stress), encoding="utf-8")
    rolling = _rolling_stability()
    rolling["summary"]["event_count"] = 1
    paths["rolling"].write_text(json.dumps(rolling), encoding="utf-8")

    component_specs = {
        "signal_rows.jsonl": (paths["signal"], None),
        "data_availability_ledger.json": (
            paths["availability"],
            "crypto_perp_backtest_data_availability_ledger.v1",
        ),
        "tournament_rows_v2.json": (
            paths["rows"],
            "crypto_perp_tournament_rows.v2",
        ),
        "bias_guard.json": (paths["guard"], "crypto_perp_bias_guard.v1"),
        "backtest_result.json": (
            paths["backtest"],
            "crypto_perp_backtest_result.v1",
        ),
        "stress_result.json": (
            paths["stress"],
            "crypto_perp_backtest_stress_result.v1",
        ),
        "rolling_stability_result.json": (
            paths["rolling"],
            "crypto_perp_backtest_rolling_stability_result.v1",
        ),
    }
    decision = _decision()
    decision.pop("evidence_grade_summary")
    decision.update({"event_count": 1, "outcome_count": 1})
    decision["source_refs"] = [
        file_artifact_ref(paths["selection"], "crypto_perp_real_market_no_cash_sample.v1")
    ]
    decision["artifact_paths"] = {
        name: component_path.as_posix() for name, (component_path, _) in component_specs.items()
    }
    decision["summary"].update(
        {
            "bias_guard_stop_reasons": [],
            "bias_guard_warning_codes": [],
            "backtest": backtest["summary"],
            "stress": stress["summary"],
            "pack_component_refs": {
                name: file_artifact_ref(component_path, schema_version)
                for name, (component_path, schema_version) in component_specs.items()
            },
        }
    )
    paths["decision"].write_text(json.dumps(decision), encoding="utf-8")
    gate = _gate(
        summary={**_gate()["summary"], "event_count": 1, "outcome_count": 1},
        source_refs=[
            file_artifact_ref(paths["decision"]),
            file_artifact_ref(paths["availability"]),
            file_artifact_ref(paths["backtest"]),
            file_artifact_ref(paths["stress"]),
            file_artifact_ref(paths["rolling"]),
        ],
    )
    paths["gate"].write_text(json.dumps(gate), encoding="utf-8")
    kill = _kill(
        upstream_gate_decision="NO_CASH_BACKTEST_HOLD",
        source_refs=[
            file_artifact_ref(paths["signal"]),
            file_artifact_ref(paths["backtest"]),
            file_artifact_ref(paths["stress"]),
            file_artifact_ref(paths["rows"]),
            file_artifact_ref(paths["gate"]),
        ],
    )
    paths["kill"].write_text(json.dumps(kill), encoding="utf-8")
    leaderboard_row = _leaderboard()["rows"][0]
    leaderboard = _leaderboard(
        rows=[leaderboard_row],
        source_refs=[
            file_artifact_ref(paths["decision"]),
            file_artifact_ref(paths["backtest"]),
            file_artifact_ref(paths["stress"]),
            file_artifact_ref(paths["gate"]),
            file_artifact_ref(paths["kill"]),
            file_artifact_ref(paths["signal"]),
        ],
    )
    paths["leaderboard"].write_text(json.dumps(leaderboard), encoding="utf-8")
    return paths


def _packet_cli_args(paths: dict[str, Path], out: Path) -> list[str]:
    return [
        "crypto-perp-human-review-packet",
        "--selection-manifest",
        str(paths["selection"]),
        "--decision",
        str(paths["decision"]),
        "--tournament-rows",
        str(paths["rows"]),
        "--bias-guard",
        str(paths["guard"]),
        "--data-availability",
        str(paths["availability"]),
        "--signal-rows",
        str(paths["signal"]),
        "--backtest",
        str(paths["backtest"]),
        "--stress",
        str(paths["stress"]),
        "--rolling-stability",
        str(paths["rolling"]),
        "--gate",
        str(paths["gate"]),
        "--kill-report",
        str(paths["kill"]),
        "--leaderboard",
        str(paths["leaderboard"]),
        "--out",
        str(out),
    ]
