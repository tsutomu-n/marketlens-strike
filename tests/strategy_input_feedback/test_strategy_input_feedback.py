from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.strategy_input_feedback.models import StrategyInputFeedbackReviewDecision
from sis.strategy_input_feedback.service import (
    StrategyInputFeedbackError,
    build_input_feedback_proposal,
    build_input_feedback_review,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _proposal_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract_update_proposal.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _review_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_input_contract_update_review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _runtime_observation(tmp_path: Path, *, boundary_violation: bool = False) -> Path:
    payload = {
        "schema_version": "strategy_runtime_observation_manifest.v1",
        "strategy_id": "ndx-breakout-001",
        "session_id": "smoke-001",
        "source_stage": "paper_smoke",
        "created_at": "2026-06-22T09:00:00Z",
        "producer": {"tool": "sis", "command": "strategy-runtime-observation-ingest"},
        "ingest_status": "INGESTED",
        "source_artifacts": [
            {
                "artifact_key": "paper_observation_ledger",
                "path": "data/paper/observations/smoke-001/ledger.jsonl",
                "sha256": "sha256:" + "a" * 64,
                "schema_version": "paper_observation_ledger.v1",
            }
        ],
        "runtime_observation_ledger_path": "data/paper/observations/smoke-001/ledger.jsonl",
        "runtime_observation_ledger_sha256": "sha256:" + "b" * 64,
        "summary": {
            "ledger_entry_count": 2,
            "paper_order_count": 1,
            "paper_fill_count": 0,
            "blocked_count": 1,
            "no_fill_count": 1,
            "unique_intent_count": 2,
            "unique_symbol_count": 1,
            "pnl_available": False,
            "block_reasons": {"LATEST_QUOTE_MISSING": 1},
            "status_counts": {"blocked": 1, "paper_no_fill": 1},
            "order_lifecycle_counts": {"blocked": 1, "paper_no_fill": 1},
        },
        "includes_live_order": False,
        "includes_wallet": False,
        "includes_signing": False,
        "includes_exchange_write": False,
        "live_allowed": False,
        "boundary": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": boundary_violation,
        },
    }
    return _write_json(tmp_path / "data/runtime_observations/obs.json", payload)


def _learning_event(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_learning/event.json",
        {
            "schema_version": "strategy_learning_event.v1",
            "learning_event_id": "learn-001",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-22T09:05:00Z",
            "producer": {"tool": "sis", "command": "strategy-learning-ledger-update"},
            "source_stage": "paper_smoke",
            "source_artifacts": [
                {
                    "artifact_key": "paper_vs_backtest_drift_review",
                    "path": "data/drift/review.json",
                    "sha256": "sha256:" + "c" * 64,
                    "schema_version": "paper_vs_backtest_drift_review.v1",
                }
            ],
            "event_type": "execution_assumption_update",
            "finding": "Runtime no-fill behavior differs from the initial assumption.",
            "impact": "Strategy Input Contract may need execution reality notes.",
            "recommended_action": "revise_strategy",
            "source_review_status": "READY_FOR_HUMAN_DRIFT_REVIEW",
            "source_recommended_action": "REVISE_STRATEGY",
            "requires_human_review": True,
            "auto_applied": False,
            "direct_spec_edit_allowed": False,
            "paper_execution_allowed": False,
            "live_allowed": False,
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
        },
    )


def _source_contract(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "data/strategy_inputs/contract.json",
        {
            "schema_version": "strategy_input_contract.v1",
            "contract_id": "ndx-breakout-inputs-001",
            "created_at": "2026-06-22T08:00:00Z",
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
                    "path": "data/research/ndx/ohlcv.csv",
                    "required": True,
                    "declared_sha256": "sha256:" + "d" * 64,
                    "schema_version": "market_ohlcv.v1",
                    "generated_at": "2026-06-22T07:00:00Z",
                    "available_at": "2026-06-22T07:05:00Z",
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
            "known_gaps": ["no spread source yet"],
            "boundary": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
            },
        },
    )


def test_runtime_observation_without_contract_builds_context_limited_proposal(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    runtime = _runtime_observation(tmp_path)

    result = build_input_feedback_proposal(
        strategy_id="ndx-breakout-001",
        runtime_observation_paths=[runtime],
        learning_event_paths=[],
        out_dir=tmp_path / "data/strategy_input_feedback",
        proposal_id="proposal-runtime",
    )

    assert result.proposal.status.value == "NEEDS_SOURCE_CONTRACT_CONTEXT"
    assert result.proposal.proposed_changes[0].change_id == "runtime-001"
    assert result.proposal.source_artifacts[0].schema_version == (
        "strategy_runtime_observation_manifest.v1"
    )
    payload = json.loads(result.proposal_path.read_text(encoding="utf-8"))
    Draft202012Validator(_proposal_schema()).validate(payload)
    assert "does not edit Strategy Input Contract" in result.report_path.read_text(encoding="utf-8")


def test_learning_event_with_contract_builds_ready_proposal_and_review(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    learning = _learning_event(tmp_path)
    contract = _source_contract(tmp_path)

    proposal = build_input_feedback_proposal(
        strategy_id="ndx-breakout-001",
        runtime_observation_paths=[],
        learning_event_paths=[learning],
        source_contract_path=contract,
        out_dir=tmp_path / "data/strategy_input_feedback",
        proposal_id="proposal-learning",
    )

    assert proposal.proposal.status.value == "READY_FOR_HUMAN_REVIEW"
    assert {source.artifact_kind.value for source in proposal.proposal.source_artifacts} == {
        "strategy_input_contract",
        "learning_event",
    }

    review = build_input_feedback_review(
        proposal_path=proposal.proposal_path,
        out_dir=None,
        reviewer="operator-a",
        decision=StrategyInputFeedbackReviewDecision.APPROVE_FOR_MANUAL_CONTRACT_UPDATE,
        rationale="Approved only as input to manual contract update.",
        approved_change_ids=["learning-001"],
        review_id="proposal-learning-review",
    )

    assert review.review.manual_contract_update_input_allowed is True
    assert review.review.direct_contract_edit_allowed is False
    payload = json.loads(review.review_path.read_text(encoding="utf-8"))
    Draft202012Validator(_review_schema()).validate(payload)
    assert "does not apply changes" in review.report_path.read_text(encoding="utf-8")


def test_empty_source_inputs_fail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(StrategyInputFeedbackError, match="at least one"):
        build_input_feedback_proposal(
            strategy_id="ndx-breakout-001",
            runtime_observation_paths=[],
            learning_event_paths=[],
            out_dir=tmp_path / "data/strategy_input_feedback",
        )


def test_boundary_violation_source_blocks_ready_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runtime = _runtime_observation(tmp_path, boundary_violation=True)
    contract = _source_contract(tmp_path)

    result = build_input_feedback_proposal(
        strategy_id="ndx-breakout-001",
        runtime_observation_paths=[runtime],
        learning_event_paths=[],
        source_contract_path=contract,
        out_dir=tmp_path / "data/strategy_input_feedback",
        proposal_id="proposal-blocked",
    )

    assert result.proposal.status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert result.proposal.blocked_reasons == ["runtime_observation:boundary.exchange_write_used"]


def test_review_rejects_unknown_change_id(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    proposal = build_input_feedback_proposal(
        strategy_id="ndx-breakout-001",
        runtime_observation_paths=[_runtime_observation(tmp_path)],
        learning_event_paths=[],
        source_contract_path=_source_contract(tmp_path),
        out_dir=tmp_path / "data/strategy_input_feedback",
        proposal_id="proposal-review-check",
    )

    with pytest.raises(ValueError, match="approved_change_ids not found"):
        build_input_feedback_review(
            proposal_path=proposal.proposal_path,
            out_dir=None,
            reviewer="operator-a",
            decision=StrategyInputFeedbackReviewDecision.APPROVE_FOR_MANUAL_CONTRACT_UPDATE,
            rationale="Attempt unknown approval.",
            approved_change_ids=["missing-change"],
        )


def test_default_proposal_and_review_ids_stay_within_model_limit(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    long_strategy_id = "s" * 128
    runtime = _runtime_observation(tmp_path)
    contract = _source_contract(tmp_path)

    proposal = build_input_feedback_proposal(
        strategy_id=long_strategy_id,
        runtime_observation_paths=[runtime],
        learning_event_paths=[],
        source_contract_path=contract,
        out_dir=tmp_path / "data/strategy_input_feedback",
    )

    assert len(proposal.proposal.proposal_id) <= 128
    assert "-input-feedback-" in proposal.proposal.proposal_id
    review = build_input_feedback_review(
        proposal_path=proposal.proposal_path,
        out_dir=None,
        reviewer="operator-a",
        decision=StrategyInputFeedbackReviewDecision.APPROVE_FOR_MANUAL_CONTRACT_UPDATE,
        rationale="Approved only as input to manual contract update.",
        approved_change_ids=["runtime-001"],
    )
    assert len(review.review.review_id) <= 128
    assert "-review-" in review.review.review_id
