from __future__ import annotations

from copy import deepcopy
from typing import Any


HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64
HASH_D = "sha256:" + "d" * 64


def safe_boundary() -> dict[str, bool]:
    return {
        "paper_execution_allowed": False,
        "live_allowed": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
        "production_exchange_write_allowed": False,
        "production_exchange_write_used": False,
        "live_order_submitted": False,
        "auto_promote": False,
    }


def producer() -> dict[str, str]:
    return {"tool": "sis", "command": "edge-candidate-fixture"}


def artifact_ref(
    ref_id: str, schema_version: str, path: str, sha256: str = HASH_A
) -> dict[str, str]:
    return {
        "ref_id": ref_id,
        "schema_version": schema_version,
        "path": path,
        "sha256": sha256,
    }


def mechanism_card() -> dict[str, Any]:
    return {
        "mechanism_id": "forced_flow_liquidation_exhaustion",
        "mechanism_summary": "Large forced long liquidation may exhaust sell pressure.",
        "who_is_forced_or_constrained": "Leveraged long holders forced to liquidate.",
        "why_flow_may_be_unfavorable": "Forced sellers accept poor prices during thin liquidity.",
        "expected_time_horizon": "5m_to_60m",
        "failure_modes": ["cascade_continues", "spread_widens"],
        "counter_hypothesis": "Continuation after liquidation dominates reversal.",
    }


def source_requirement() -> dict[str, Any]:
    return {
        "source_id": "liquidation_feed",
        "source_type": "liquidation_events",
        "required": True,
        "expected_schema": "liquidation_event.v1",
        "available_at_policy": "available before candidate generation timestamp",
        "status": "PASS",
        "known_gaps": [],
    }


def execution_precheck() -> dict[str, Any]:
    return {
        "venue_id": "bitget",
        "product_type": "USDT-FUTURES",
        "symbol": "BTCUSDT",
        "min_notional_ok": True,
        "tick_size_ok": True,
        "lot_size_ok": True,
        "max_spread_bps": 8.0,
        "observed_spread_bps": 2.5,
        "min_depth_usd": 5000.0,
        "observed_depth_usd": 25000.0,
        "fee_rate_available": True,
        "funding_available": True,
        "estimated_operator_time_minutes": 15,
        "estimated_capital_tied_up_minutes": 60,
        "unexecutable_reasons": [],
        "execution_precheck_status": "PASS",
    }


def prior_score() -> dict[str, Any]:
    return {
        "mechanism_score": 0.7,
        "source_availability_score": 0.9,
        "execution_feasibility_score": 0.8,
        "testability_score": 0.75,
        "diversity_score": 0.6,
        "information_gain_score": 0.8,
        "operator_cost_penalty": 0.1,
        "unexecutable_penalty": 0.0,
        "overfit_surface_penalty": 0.2,
        "total_score": 0.72,
        "score_basis": "prior_not_profit_proof",
    }


def smart_candidate_card(candidate_id: str = "edge-cand-001") -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "candidate_status": "UNVERIFIED_CANDIDATE",
        "candidate_decision": "GENERATED",
        "cause_priors": ["FORCED_FLOW", "CROWDED_POSITIONING"],
        "family": "liquidation_exhaustion_reversal",
        "mechanism_card": mechanism_card(),
        "observables": ["liquidation_notional", "spread_bps", "open_interest"],
        "required_sources": [source_requirement()],
        "source_requirement_status": "PASS",
        "execution_precheck": execution_precheck(),
        "candidate_prior_score": prior_score(),
        "parameter_set": {"lookback_minutes": 30, "liquidation_notional_min": 1000000},
        "action_set": ["reversal_long", "no_trade"],
        "entry_logic": "consider reversal only after forced sell pressure slows",
        "exit_logic": "exit on spread widening or failed recovery",
        "kill_conditions": ["spread_widens", "no_trade_beats_after_cost"],
        "expected_information_gain": "tests whether forced-flow exhaustion beats no trade",
        "test_cost_estimate": "low",
        "operator_burden_estimate": "low",
        "candidate_cluster_id": "cluster-liquidation-exhaustion",
        "similar_candidate_count": 1,
        "negative_control_refs": ["no_trade"],
        "proof_status": "not_alpha_or_profit_proof",
        "rejection_reason": None,
        "shortlist_reason": "generated for research queue only",
        "boundary": safe_boundary(),
    }


def smart_candidate_prior_report_payload() -> dict[str, Any]:
    return {
        "schema_version": "smart_candidate_prior_report.v1",
        "report_id": "edge-report-001",
        "generated_at": "2026-07-02T10:54:00Z",
        "producer": producer(),
        "source_refs": [
            artifact_ref(
                "source-prep-watchdeck",
                "prep_watchdeck_snapshot.v1",
                "data/prep/watchdeck/source_manifest.json",
                HASH_A,
            )
        ],
        "generator_config": {
            "profile": "core",
            "symbols": ["BTCUSDT"],
            "product_type": "USDT-FUTURES",
            "timeframe": "5m",
            "families": ["liquidation_exhaustion_reversal"],
            "candidate_cap": 10,
            "parameter_grid_hash": HASH_B,
            "source_root": "data/prep/watchdeck",
            "sealed_test_policy": "do_not_use_for_selection",
            "network_attempted": False,
            "credentials_used": False,
            "production_exchange_write_used": False,
        },
        "candidate_cards": [smart_candidate_card()],
        "candidate_count_total": 1,
        "candidate_count_accepted": 1,
        "candidate_count_rejected": 0,
        "rejection_summary": {"duplicate": 0},
        "score_summary": {"max_total_score": 0.72},
        "boundary": safe_boundary(),
        "known_gaps": ["no actual cash evidence"],
    }


def edge_candidate_search_ledger_row_payload() -> dict[str, Any]:
    return {
        "schema_version": "edge_candidate_search_ledger.v1",
        "run_id": "edge-run-001",
        "candidate_id": "edge-cand-001",
        "row_kind": "candidate",
        "family": "liquidation_exhaustion_reversal",
        "cause_priors": ["FORCED_FLOW"],
        "parameter_hash": HASH_C,
        "parameter_set": {"lookback_minutes": 30},
        "candidate_cluster_id": "cluster-liquidation-exhaustion",
        "similar_candidate_count": 1,
        "candidate_prior_score": prior_score(),
        "candidate_decision": "GENERATED",
        "rejection_reason": None,
        "source_requirement_status": "PASS",
        "execution_precheck_status": "PASS",
        "validation_peek_count_at_generation": 0,
        "sealed_test_used_for_selection": False,
        "proof_status": "not_alpha_or_profit_proof",
        "boundary": safe_boundary(),
    }


def trial_multiplicity_account_payload() -> dict[str, Any]:
    return {
        "schema_version": "trial_multiplicity_account.v1",
        "account_id": "multiplicity-001",
        "created_at": "2026-07-02T10:54:00Z",
        "producer": producer(),
        "source_refs": [
            artifact_ref(
                "smart-prior-report",
                "smart_candidate_prior_report.v1",
                "data/edge_candidate_factory/run/smart_candidate_prior_report.json",
                HASH_A,
            )
        ],
        "candidate_run_id": "edge-run-001",
        "candidate_count_total": 1,
        "candidate_count_shortlisted": 1,
        "candidate_count_rejected": 0,
        "family_count": 1,
        "family_trial_counts": {"liquidation_exhaustion_reversal": 1},
        "parameter_grid_hashes": [HASH_B],
        "candidate_cluster_count": 1,
        "effective_trial_count_status": "NOT_ESTIMABLE",
        "effective_trial_count": None,
        "validation_peek_count": 0,
        "rerank_count": 0,
        "sealed_test_used_for_selection": False,
        "success_only_reporting": False,
        "adjustment_methods": {
            "benjamini_hochberg_fdr": "NOT_ESTIMABLE",
            "benjamini_yekutieli_fdr": "NOT_ESTIMABLE",
            "pbo": "NOT_ESTIMABLE",
            "white_reality_check": "NOT_ESTIMABLE",
            "deflated_sharpe_ratio": "NOT_ESTIMABLE",
        },
        "known_gaps": ["effective trial count requires full search ledger"],
        "boundary": safe_boundary(),
    }


def gate_condition(condition_id: str, status: str = "PASS") -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "condition_status": status,
        "observed": "observed fixture value",
        "required": "required fixture value",
        "source_ref": "fixture",
    }


def backtest_kill_gate_payload() -> dict[str, Any]:
    condition_statuses = {
        "candidate_scoped_backtest_exists": "NOT_ESTIMABLE",
        "no_trade_comparison_available": "NOT_ESTIMABLE",
        "event_count_meets_family_threshold": "NOT_ESTIMABLE",
        "closed_trade_count_meets_threshold": "NOT_ESTIMABLE",
        "after_cost_edge_positive": "NOT_ESTIMABLE",
        "stress_edge_positive": "NOT_ESTIMABLE",
        "largest_loss_within_limit": "NOT_ESTIMABLE",
        "profit_concentration_within_limit": "NOT_ESTIMABLE",
    }
    return {
        "schema_version": "backtest_kill_gate.v1",
        "gate_id": "backtest-kill-001",
        "created_at": "2026-07-02T10:54:00Z",
        "producer": producer(),
        "candidate_id": "edge-cand-001",
        "candidate_source_refs": [
            artifact_ref(
                "smart-prior-report",
                "smart_candidate_prior_report.v1",
                "data/edge_candidate_factory/run/smart_candidate_prior_report.json",
                HASH_A,
            )
        ],
        "bridge_refs": [],
        "multiplicity_account_ref": artifact_ref(
            "multiplicity",
            "trial_multiplicity_account.v1",
            "data/edge_candidate_factory/run/trial_multiplicity_account.json",
            HASH_B,
        ),
        "backtest_refs": [],
        "gate_status": "INCONCLUSIVE_DATA",
        "recommended_action": "collect candidate scoped backtest evidence",
        "metric_extraction_status": "NOT_ESTIMABLE",
        "metric_source_refs": [],
        "metric_not_estimable_reasons": ["candidate scoped backtest missing"],
        "conditions": [
            gate_condition(condition_id, condition_statuses.get(condition_id, "PASS"))
            for condition_id in [
                "source_available",
                "bridge_technical_ready",
                "candidate_scoped_backtest_exists",
                "no_trade_comparison_available",
                "event_count_meets_family_threshold",
                "closed_trade_count_meets_threshold",
                "after_cost_edge_positive",
                "stress_edge_positive",
                "largest_loss_within_limit",
                "profit_concentration_within_limit",
                "multiplicity_account_available",
                "unexecutable_reason_count_zero",
                "sealed_test_not_used_for_selection",
                "execution_precheck_passed",
            ]
        ],
        "metrics": {
            "event_count": None,
            "closed_trade_count": None,
            "after_cost_edge_over_no_trade_usd": None,
            "stress_edge_over_no_trade_usd": None,
            "largest_loss_usd": None,
            "profit_concentration": None,
            "source_gap_count": 0,
            "unexecutable_reason_count": 0,
            "validation_peek_count": 0,
            "candidate_cluster_count": 1,
            "effective_trial_count": None,
        },
        "known_gaps": ["backtest metrics not available"],
        "boundary": safe_boundary(),
    }


def virtual_execution_gate_payload() -> dict[str, Any]:
    condition_statuses = {
        "order_preview_ready": "NOT_ESTIMABLE",
        "order_accepted_or_rejected_with_reason": "NOT_ESTIMABLE",
        "client_oid_unique": "NOT_ESTIMABLE",
        "partial_fill_handled": "NOT_ESTIMABLE",
        "cancel_handled": "NOT_ESTIMABLE",
        "reduce_only_close_checked": "NOT_ESTIMABLE",
        "flat_reconciliation_passed": "NOT_ESTIMABLE",
        "fee_like_fields_captured": "NOT_ESTIMABLE",
        "funding_like_fields_captured": "NOT_ESTIMABLE",
        "duplicate_order_prevented": "NOT_ESTIMABLE",
    }
    return {
        "schema_version": "virtual_execution_gate.v1",
        "gate_id": "virtual-gate-001",
        "created_at": "2026-07-02T10:54:00Z",
        "producer": producer(),
        "candidate_id": "edge-cand-001",
        "execution_environment": "fixture",
        "venue_id": "bitget",
        "source_refs": [],
        "order_lifecycle_summary": {"orders_submitted": 0, "orders_rejected": 0},
        "fill_ledger_summary": {"fills": 0},
        "reconciliation_summary": {"flat": True},
        "gate_status": "VIRTUAL_NOT_RUN",
        "recommended_action": "run fixture or demo lifecycle before actual cash",
        "actual_cash": False,
        "cash_metric_basis": "virtual_exchange",
        "exchange_write_used": False,
        "production_exchange_write_used": False,
        "permits_live_order": False,
        "conditions": [
            gate_condition(condition_id, condition_statuses.get(condition_id, "PASS"))
            for condition_id in [
                "order_preview_ready",
                "order_accepted_or_rejected_with_reason",
                "client_oid_unique",
                "partial_fill_handled",
                "cancel_handled",
                "reduce_only_close_checked",
                "flat_reconciliation_passed",
                "fee_like_fields_captured",
                "funding_like_fields_captured",
                "duplicate_order_prevented",
                "production_exchange_write_not_used",
            ]
        ],
        "known_gaps": ["virtual lifecycle not run"],
        "boundary": safe_boundary(),
    }


def risk_actual_cash_handoff_payload() -> dict[str, Any]:
    return {
        "schema_version": "edge_candidate_risk_actual_cash_handoff.v1",
        "handoff_id": "risk-cash-handoff-001",
        "created_at": "2026-07-02T10:54:00Z",
        "producer": producer(),
        "candidate_id": "edge-cand-001",
        "candidate_report_ref": artifact_ref(
            "smart-prior-report",
            "smart_candidate_prior_report.v1",
            "data/edge_candidate_factory/run/smart_candidate_prior_report.json",
            HASH_A,
        ),
        "search_ledger_ref": artifact_ref(
            "search-ledger",
            "edge_candidate_search_ledger.v1",
            "data/edge_candidate_factory/run/edge_candidate_search_ledger.jsonl",
            HASH_B,
        ),
        "multiplicity_account_ref": artifact_ref(
            "multiplicity",
            "trial_multiplicity_account.v1",
            "data/edge_candidate_factory/run/trial_multiplicity_account.json",
            HASH_C,
        ),
        "backtest_kill_gate_ref": artifact_ref(
            "backtest-kill",
            "backtest_kill_gate.v1",
            "data/edge_candidate_factory/run/backtest_kill_gate/edge-cand-001.json",
            HASH_D,
        ),
        "virtual_execution_gate_ref": artifact_ref(
            "virtual-gate",
            "virtual_execution_gate.v1",
            "data/edge_candidate_factory/run/virtual_execution_gate/edge-cand-001.json",
            HASH_A,
        ),
        "risk_taker_review_input_status": "BLOCKED_NEEDS_ACTUAL_CASH_ROWS",
        "actual_cash_report_gate_input_status": "BLOCKED_NEEDS_ACTUAL_CASH_ROWS",
        "actual_cash_rows_required": True,
        "actual_cash_rows_ref": None,
        "virtual_or_backtest_used_as_actual_cash": False,
        "known_gaps": ["actual cash rows are missing"],
        "boundary": safe_boundary(),
    }


def llm_adversarial_evidence_review_payload() -> dict[str, Any]:
    return {
        "schema_version": "llm_adversarial_evidence_review.v1",
        "review_id": "llm-adversarial-001",
        "created_at": "2026-07-02T10:54:00Z",
        "producer": producer(),
        "source_refs": [
            artifact_ref(
                "smart-prior-report",
                "smart_candidate_prior_report.v1",
                "data/edge_candidate_factory/run/smart_candidate_prior_report.json",
                HASH_A,
            )
        ],
        "packet_hash": HASH_B,
        "review_status": "ADVERSARIAL_FINDING",
        "findings": [
            {
                "finding_id": "finding-001",
                "finding_type": "MISSING_ARTIFACT",
                "severity": "hard",
                "source_ref": "backtest_kill_gate",
                "claim_text": "candidate can move to actual cash",
                "problem": "actual cash rows are missing",
                "required_fix": "collect actual cash rows before actual cash gate",
                "machine_checkable": True,
                "hard_blocker": True,
            }
        ],
        "hard_blocker_count": 1,
        "soft_warning_count": 0,
        "llm_approval_ignored": True,
        "paper_execution_allowed": False,
        "live_allowed": False,
        "actual_cash_decision_allowed": False,
        "gate_override_allowed": False,
        "boundary": safe_boundary(),
    }


def payloads_by_schema() -> dict[str, dict[str, Any]]:
    return {
        "smart_candidate_prior_report.v1.schema.json": smart_candidate_prior_report_payload(),
        "edge_candidate_search_ledger.v1.schema.json": edge_candidate_search_ledger_row_payload(),
        "trial_multiplicity_account.v1.schema.json": trial_multiplicity_account_payload(),
        "backtest_kill_gate.v1.schema.json": backtest_kill_gate_payload(),
        "virtual_execution_gate.v1.schema.json": virtual_execution_gate_payload(),
        "edge_candidate_risk_actual_cash_handoff.v1.schema.json": (
            risk_actual_cash_handoff_payload()
        ),
        "llm_adversarial_evidence_review.v1.schema.json": (
            llm_adversarial_evidence_review_payload()
        ),
    }


def copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload)
