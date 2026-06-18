from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pydantic import ValidationError

from sis.strategy_learning.models import RevisionRequestReviewDecision
from sis.strategy_learning.service import (
    build_authoring_update_handoff,
    build_revision_request,
    record_revision_request_review,
    update_learning_ledger,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _event_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_learning_event.v1.schema.json").read_text(encoding="utf-8")
    )


def _revision_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_revision_request.v1.schema.json").read_text(encoding="utf-8")
    )


def _review_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_revision_request_review.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _handoff_schema() -> dict:
    return json.loads(
        (REPO_ROOT / "schemas/strategy_authoring_update_handoff.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _authoring_spec(tmp_path: Path, *, strategy_id: str = "ndx-breakout-001") -> Path:
    path = tmp_path / "configs/strategies/ndx-breakout-001.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "schema_version: strategy_authoring_spec.v1",
                f"strategy_id: {strategy_id}",
                "description: fixture strategy",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _condition(condition_id: str, passed: bool, severity: str = "error") -> dict:
    return {
        "condition_id": condition_id,
        "passed": passed,
        "observed": "0.75",
        "required": "<= 0.5",
        "severity": severity,
    }


def _drift_review(
    tmp_path: Path,
    *,
    review_status: str = "READY_FOR_HUMAN_DRIFT_REVIEW",
    recommended_action: str = "REVISE_STRATEGY",
    failed_conditions: list[dict] | None = None,
) -> Path:
    return _write_json(
        tmp_path
        / "data/strategy_drift_reviews/ndx-breakout-001/paper_vs_backtest_drift_review.json",
        {
            "schema_version": "paper_vs_backtest_drift_review.v1",
            "strategy_id": "ndx-breakout-001",
            "created_at": "2026-06-19T00:00:00Z",
            "producer": {"tool": "sis", "command": "strategy-drift-review"},
            "review_status": review_status,
            "recommended_action": recommended_action,
            "source_artifacts": [
                {
                    "artifact_key": "strategy_authoring_backtest_result",
                    "path": "data/research/strategy_authoring/backtest_result.json",
                    "sha256": "sha256:" + "a" * 64,
                    "schema_version": "strategy_authoring_backtest_result.v1",
                }
            ],
            "backtest_summary": {
                "strategy_id": "ndx-breakout-001",
                "backtest_passed": True,
                "signals_considered": 10,
                "executed_count": 5,
                "blocked_count": 1,
                "trade_count": 5,
                "total_return": 0.04,
                "max_drawdown": -0.02,
                "win_rate": 0.6,
            },
            "runtime_summary": {
                "strategy_id": "ndx-breakout-001",
                "session_id": "smoke-001",
                "source_stage": "paper_smoke",
                "ingest_status": "INGESTED",
                "ledger_entry_count": 4,
                "paper_fill_count": 1,
                "blocked_count": 1,
                "no_fill_count": 3,
                "max_observed_spread_bps": 12.5,
                "max_observed_quote_age_ms": 120,
            },
            "drift_metrics": {
                "runtime_to_backtest_trade_count_ratio": 0.2,
                "runtime_blocked_rate": 0.25,
                "runtime_no_fill_rate": 0.75,
                "max_observed_spread_bps": 12.5,
                "max_observed_quote_age_ms": 120,
                "pnl_drift_available": False,
            },
            "passed_conditions": [],
            "failed_conditions": failed_conditions
            if failed_conditions is not None
            else [_condition("runtime_no_fill_rate_within_limit", False)],
            "warning_conditions": [],
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


def test_learning_ledger_update_and_revision_request_are_schema_valid(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    drift_review = _drift_review(tmp_path)

    learning = update_learning_ledger(
        drift_review_path=drift_review,
        out_dir=tmp_path / "data/strategy_learning",
        learning_event_id="learn-001",
    )

    assert learning.event.recommended_action.value == "revise_strategy"
    assert learning.event.auto_applied is False
    event_payload = json.loads(learning.event_path.read_text(encoding="utf-8"))
    Draft202012Validator(_event_schema()).validate(event_payload)
    assert learning.ledger_path.read_text(encoding="utf-8").count("\n") == 1

    revision = build_revision_request(
        strategy_id="ndx-breakout-001",
        learning_ledger_path=learning.ledger_path,
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests",
        revision_request_id="revise-001",
    )

    assert revision.request.request_status.value == "READY_FOR_HUMAN_REVIEW"
    assert revision.request.reason == "no_fill_drift"
    assert revision.request.auto_applied is False
    assert revision.request.direct_spec_edit_allowed is False
    assert "Add or tighten no-fill / no-trade conditions." in revision.request.requested_changes
    request_payload = json.loads(revision.request_path.read_text(encoding="utf-8"))
    Draft202012Validator(_revision_schema()).validate(request_payload)
    report = revision.report_path.read_text(encoding="utf-8")
    assert "does not edit Strategy Authoring YAML" in report


def test_learning_boundary_review_builds_repair_request(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    drift_review = _drift_review(
        tmp_path,
        review_status="BLOCKED_BOUNDARY_VIOLATION",
        recommended_action="REPAIR_ARTIFACTS",
        failed_conditions=[_condition("no_boundary_violation", False)],
    )

    learning = update_learning_ledger(
        drift_review_path=drift_review,
        out_dir=tmp_path / "data/strategy_learning",
        learning_event_id="learn-boundary",
    )
    revision = build_revision_request(
        strategy_id="ndx-breakout-001",
        learning_ledger_path=learning.ledger_path,
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests",
        revision_request_id="revise-boundary",
    )

    assert learning.event.event_type.value == "artifact_boundary_violation"
    assert revision.request.request_status.value == "BLOCKED_BOUNDARY_VIOLATION"
    assert revision.request.reason == "artifact_boundary_violation"


def test_revision_request_review_approves_for_authoring_update_input(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    learning = update_learning_ledger(
        drift_review_path=_drift_review(tmp_path),
        out_dir=tmp_path / "data/strategy_learning",
        learning_event_id="learn-001",
    )
    revision = build_revision_request(
        strategy_id="ndx-breakout-001",
        learning_ledger_path=learning.ledger_path,
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests",
        revision_request_id="revise-001",
    )

    review = record_revision_request_review(
        revision_request_path=revision.request_path,
        out_dir=revision.request_path.parent,
        reviewer="operator-a",
        decision=RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE,
        rationale="Use as authoring update input after checking requested changes.",
    )

    assert review.review.decision.value == "APPROVE_FOR_AUTHORING_UPDATE"
    assert review.review.authoring_update_input_allowed is True
    assert review.review.direct_spec_edit_allowed is False
    payload = json.loads(review.review_path.read_text(encoding="utf-8"))
    Draft202012Validator(_review_schema()).validate(payload)
    report = review.report_path.read_text(encoding="utf-8")
    assert "does not edit Strategy Authoring YAML" in report


def test_revision_request_review_rejects_approval_for_no_revision_request(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    drift_review = _drift_review(
        tmp_path,
        recommended_action="HUMAN_REVIEW_REQUIRED",
        failed_conditions=[],
    )
    learning = update_learning_ledger(
        drift_review_path=drift_review,
        out_dir=tmp_path / "data/strategy_learning",
        learning_event_id="learn-context",
    )
    revision = build_revision_request(
        strategy_id="ndx-breakout-001",
        learning_ledger_path=learning.ledger_path,
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests",
        revision_request_id="revise-context",
    )

    assert revision.request.request_status.value == "NO_REVISION_REQUIRED"
    try:
        record_revision_request_review(
            revision_request_path=revision.request_path,
            out_dir=revision.request_path.parent,
            reviewer="operator-a",
            decision=RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE,
            rationale="Should not approve a no-revision request.",
        )
    except ValidationError as exc:
        assert "READY_FOR_HUMAN_REVIEW" in str(exc)
    else:
        raise AssertionError("expected validation error")


def test_authoring_update_handoff_is_schema_valid_for_approved_review(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    learning = update_learning_ledger(
        drift_review_path=_drift_review(tmp_path),
        out_dir=tmp_path / "data/strategy_learning",
        learning_event_id="learn-001",
    )
    revision = build_revision_request(
        strategy_id="ndx-breakout-001",
        learning_ledger_path=learning.ledger_path,
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests",
        revision_request_id="revise-001",
    )
    review = record_revision_request_review(
        revision_request_path=revision.request_path,
        out_dir=revision.request_path.parent,
        reviewer="operator-a",
        decision=RevisionRequestReviewDecision.APPROVE_FOR_AUTHORING_UPDATE,
        rationale="Use as authoring update input after checking requested changes.",
    )

    handoff = build_authoring_update_handoff(
        revision_request_path=revision.request_path,
        revision_review_path=review.review_path,
        authoring_spec_path=_authoring_spec(tmp_path),
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/authoring_update_handoffs",
        handoff_id="authoring-handoff-001",
    )

    assert handoff.handoff.handoff_status.value == "READY_FOR_HUMAN_AUTHORING_UPDATE"
    assert handoff.handoff.auto_applied is False
    assert handoff.handoff.direct_spec_edit_allowed is False
    assert handoff.handoff.strategy_id_matches_authoring_spec is True
    payload = json.loads(handoff.handoff_path.read_text(encoding="utf-8"))
    Draft202012Validator(_handoff_schema()).validate(payload)
    report = handoff.report_path.read_text(encoding="utf-8")
    assert "does not edit Strategy Authoring YAML" in report


def test_authoring_update_handoff_needs_approval_for_hold_review(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    learning = update_learning_ledger(
        drift_review_path=_drift_review(tmp_path),
        out_dir=tmp_path / "data/strategy_learning",
        learning_event_id="learn-001",
    )
    revision = build_revision_request(
        strategy_id="ndx-breakout-001",
        learning_ledger_path=learning.ledger_path,
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/revision_requests",
        revision_request_id="revise-001",
    )
    review = record_revision_request_review(
        revision_request_path=revision.request_path,
        out_dir=revision.request_path.parent,
        reviewer="operator-a",
        decision=RevisionRequestReviewDecision.HOLD,
        rationale="Hold until operator compares the requested changes manually.",
    )

    handoff = build_authoring_update_handoff(
        revision_request_path=revision.request_path,
        revision_review_path=review.review_path,
        authoring_spec_path=_authoring_spec(tmp_path),
        out_dir=tmp_path / "data/strategy_learning/ndx-breakout-001/authoring_update_handoffs",
        handoff_id="authoring-handoff-hold",
    )

    assert handoff.handoff.handoff_status.value == "NEEDS_REVISION_REVIEW_APPROVAL"
    assert handoff.handoff.authoring_update_input_allowed is False
    assert handoff.handoff.paper_execution_allowed is False
