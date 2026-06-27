from __future__ import annotations

from copy import deepcopy
from typing import Any


HASH_A = "sha256:" + "a" * 64
HASH_B = "sha256:" + "b" * 64
HASH_C = "sha256:" + "c" * 64


def candidate_boundary() -> dict[str, bool]:
    return {
        "permits_live_order": False,
        "permits_paper_candidate": False,
        "permits_paper_intent_preview": False,
        "auto_promote": False,
        "generated_strategy_idea_is_final": False,
        "wallet_used": False,
        "signing_used": False,
        "exchange_write_used": False,
    }


def _candidate(candidate_id: str, *, decision: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "idea_candidate_id": candidate_id,
        "candidate_status": "UNVERIFIED_CANDIDATE",
        "decision": decision,
        "family": "trend_momentum",
        "title": "NDX close momentum after compression",
        "hypothesis_template": "NDX may follow through after a low-volatility close breakout.",
        "mechanism_status": "UNVERIFIED_TEMPLATE",
        "signal_expression": "close > sma(close, 20)",
        "parameter_set": {"lookback": 20, "threshold_z": 1.5},
        "parameter_grid_ref": "grid:trend_momentum:v1",
        "target_definition": "next_5_session_return",
        "prediction_horizon": "5_sessions",
        "timeframe": "1d",
        "instruments": ["NDX"],
        "label_window": {
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-12-31T00:00:00Z",
        },
        "feature_observation_window": {
            "start": "2024-01-01T00:00:00Z",
            "end": "2025-12-30T00:00:00Z",
        },
        "feature_columns_used": ["close", "volume"],
        "available_at_policy": "features must be available at or before decision timestamp",
        "source_artifact_sha256": HASH_B,
        "trial_count_refs": ["trial-001"],
        "baseline_refs": ["cash_or_no_trade"],
        "novelty_checks": {"duplicate_signal": False},
        "raw_validation_metrics": {"validation_return": 0.01},
        "selection_adjusted_metrics_status": "NOT_IMPLEMENTED",
        "leakage_checks": {
            "uses_sealed_test_for_selection": False,
            "available_at_checked": True,
        },
        "boundary": candidate_boundary(),
    }
    if decision == "SHORTLISTED":
        payload["shortlist_reason"] = (
            "highest raw validation return before selection-adjusted metrics exist"
        )
    else:
        payload["rejection_reason"] = "duplicate parameterization rejected before shortlist"
    return payload


def valid_candidate_set_payload() -> dict[str, Any]:
    return {
        "schema_version": "strategy_idea_candidate_set.v1",
        "candidate_set_id": "ndx-candidate-set-001",
        "generated_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "strategy-idea-candidates-build-fixture"},
        "generator_version": "fixture-0.1",
        "candidate_set_status": "BUILT",
        "input_contract_validation_refs": [
            {
                "contract_id": "ndx-breakout-inputs-001",
                "validation_path": (
                    "data/strategy_inputs/ndx/strategy_input_contract_validation.json"
                ),
                "validation_sha256": HASH_A,
                "validation_status": "PASS",
            }
        ],
        "source_artifacts": [
            {
                "source_id": "ndx_ohlcv_daily",
                "path": "data/research/ndx/source/ohlcv.csv",
                "sha256": HASH_B,
                "required": True,
                "source_validation_status": "present",
                "available_at": "2026-06-18T00:05:00Z",
                "max_observed_timestamp": "2026-06-17T21:00:00Z",
            }
        ],
        "candidate_inventory": [
            _candidate("idea-cand-001", decision="SHORTLISTED"),
            _candidate("idea-cand-002", decision="REJECTED"),
        ],
        "parameter_grids": {
            "trend_momentum": [
                {"lookback": 20, "threshold_z": 1.5},
                {"lookback": 20, "threshold_z": 1.5},
            ]
        },
        "search_ledger_summary": {
            "family_count": 1,
            "candidate_count_total": 2,
            "candidate_count_shortlisted": 1,
            "candidate_count_rejected": 1,
            "trial_count_total": 2,
            "parameter_grid_hash": HASH_C,
            "candidate_cap": 1,
            "cap_rejection_count": 0,
            "validation_peek_count": 0,
            "rerank_count": 0,
            "duplicate_rejection_count": 1,
            "success_only_reporting": False,
            "sealed_test_used_for_selection": False,
        },
        "selection_policy": {
            "policy_id": "raw-metric-with-boundary-guard",
            "description": "Shortlist only candidates that keep all boundary flags false.",
            "shortlisted_candidate_ids": ["idea-cand-001"],
            "rejected_candidate_ids": ["idea-cand-002"],
            "known_gaps": ["selection-adjusted metrics are not implemented"],
        },
        "split_policy": {
            "split_method": "blocked_time_split",
            "train_window": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T00:00:00Z",
            },
            "validation_window": {
                "start": "2025-01-01T00:00:00Z",
                "end": "2025-12-31T00:00:00Z",
            },
            "sealed_test_window": {
                "start": "2026-01-01T00:00:00Z",
                "end": "2026-06-18T00:00:00Z",
            },
            "uses_sealed_test_for_selection": False,
        },
        "leakage_policy": {
            "feature_available_at_policy": (
                "features must be available at or before decision timestamp"
            ),
            "purge_policy": "policy_record_only:not_implemented",
            "embargo_policy": "policy_record_only:not_implemented",
            "uses_sealed_test_for_selection": False,
        },
        "dependency_versions": {"python": "3.13", "sis": "local-test"},
        "boundary": candidate_boundary(),
    }


def valid_input_validation_payload() -> dict[str, Any]:
    return {
        "schema_version": "strategy_input_contract_validation.v1",
        "contract_id": "ndx-breakout-inputs-001",
        "validated_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "strategy-input-contract-validate"},
        "validation_status": "PASS",
        "strict": False,
        "source_results": [
            {
                "source_id": "ndx_ohlcv_daily",
                "status": "present",
                "path": "data/research/ndx/source/ohlcv.csv",
                "actual_sha256": HASH_B,
                "declared_sha256": HASH_B,
                "hash_matches": True,
                "available_at_present": True,
                "generated_before_available": True,
                "max_observed_timestamp": "2026-06-17T21:00:00Z",
            }
        ],
        "summary": {
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "boundary_violation_count": 0,
            "warning_count": 0,
            "column_check_failure_count": 0,
            "timestamp_violation_count": 0,
        },
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def valid_input_contract_payload(*, sha256: str = HASH_B) -> dict[str, Any]:
    return {
        "schema_version": "strategy_input_contract.v1",
        "contract_id": "ndx-breakout-inputs-001",
        "created_at": "2026-06-18T12:45:00Z",
        "producer": {"tool": "sis", "command": "manual"},
        "strategy_scope": {
            "strategy_family": "breakout",
            "instruments": ["NDX"],
            "timeframe": "1d",
            "intended_use": "research_backtest_only",
        },
        "sources": [
            {
                "source_id": "ndx_ohlcv_daily",
                "source_type": "raw_market_data",
                "path": "data/research/ndx/source/ohlcv.csv",
                "required": True,
                "declared_sha256": sha256,
                "schema_version": "market_ohlcv.v1",
                "generated_at": "2026-06-18T00:00:00Z",
                "available_at": "2026-06-18T00:05:00Z",
                "revision_policy": "append_only",
                "survivorship_policy": "current_constituents_not_allowed",
                "execution_reality": {
                    "includes_fills": False,
                    "includes_slippage": False,
                    "includes_latency": False,
                    "assumed_order_type": "paper_only_intent",
                },
            }
        ],
        "known_gaps": ["no intraday spread data"],
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
    }


def copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(payload)
