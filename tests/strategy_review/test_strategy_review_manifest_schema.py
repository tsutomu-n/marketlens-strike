from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from sis.strategy_review.manifest import StrategyReviewManifest


def _schema() -> dict:
    return json.loads(
        Path("schemas/strategy_review_manifest.v1.schema.json").read_text(encoding="utf-8")
    )


def _valid_manifest() -> dict:
    return {
        "schema_version": "strategy_review_manifest.v1",
        "review_id": "ndx-smoke-001",
        "created_at": "2026-06-16T09:00:00Z",
        "review_status": "READY_FOR_HUMAN_REVIEW",
        "strict": False,
        "paths": {
            "review_dir": "data/strategy_reviews/ndx-smoke-001",
            "review_markdown_path": "data/strategy_reviews/ndx-smoke-001/review.md",
            "manifest_path": "data/strategy_reviews/ndx-smoke-001/review_manifest.json",
        },
        "source_artifacts": [
            {
                "artifact_key": "pack",
                "path": "data/research/backtest_pack/strategy_backtest_pack.json",
                "exists": True,
                "required": True,
                "status": "present",
                "sha256": "sha256:" + "a" * 64,
                "summary": {"paper_only": True},
            },
            {
                "artifact_key": "stress",
                "path": "data/research/backtest_stress/strategy_backtest_stress.json",
                "exists": False,
                "required": False,
                "status": "missing",
                "summary": {},
            },
        ],
        "builder_safety": {
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "signing_used": False,
            "exchange_write_used": False,
        },
        "source_safety": {
            "status": "PASS",
            "boundary_violation_count": 0,
            "unknown_boundary_count": 0,
            "observed_flags": {
                "permits_live_order": False,
                "live_conversion_allowed": False,
                "wallet_used": False,
                "signing_used": False,
                "exchange_write_used": False,
                "venue_write_used": False,
            },
        },
        "evaluation_flags": {
            "pack_validation_status": "PASS",
            "pack_validation_pass_is_readiness_proof": False,
        },
        "summary": {
            "missing_required_count": 0,
            "invalid_required_count": 0,
            "boundary_violation_count": 0,
        },
    }


def test_strategy_review_manifest_schema_accepts_valid_manifest() -> None:
    payload = _valid_manifest()

    Draft202012Validator.check_schema(_schema())
    Draft202012Validator(_schema()).validate(payload)
    StrategyReviewManifest.model_validate(payload)


def test_strategy_review_manifest_rejects_bare_hex_hash() -> None:
    payload = _valid_manifest()
    payload["source_artifacts"][0]["sha256"] = "a" * 64

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyReviewManifest.model_validate(payload)


def test_strategy_review_manifest_rejects_true_safety_flags() -> None:
    payload = _valid_manifest()
    payload["builder_safety"]["wallet_used"] = True

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyReviewManifest.model_validate(payload)


def test_strategy_review_manifest_rejects_old_safety_only_shape() -> None:
    payload = _valid_manifest()
    payload["safety"] = payload.pop("builder_safety")
    payload.pop("source_safety")

    assert list(Draft202012Validator(_schema()).iter_errors(payload))
    with pytest.raises(ValidationError):
        StrategyReviewManifest.model_validate(payload)


def test_strategy_review_manifest_source_safety_unknown_maps_to_incomplete() -> None:
    payload = _valid_manifest()
    payload["review_status"] = "INCOMPLETE_ARTIFACTS"
    payload["source_safety"]["status"] = "UNKNOWN"
    payload["source_safety"]["unknown_boundary_count"] = 1
    payload["summary"]["missing_required_count"] = 1

    Draft202012Validator(_schema()).validate(payload)
    StrategyReviewManifest.model_validate(payload)

    payload["review_status"] = "READY_FOR_HUMAN_REVIEW"
    with pytest.raises(ValidationError):
        StrategyReviewManifest.model_validate(payload)


def test_strategy_review_manifest_source_safety_blocked_maps_to_blocked() -> None:
    payload = _valid_manifest()
    payload["review_status"] = "BLOCKED_BOUNDARY_VIOLATION"
    payload["source_safety"]["status"] = "BLOCKED"
    payload["source_safety"]["boundary_violation_count"] = 1
    payload["source_safety"]["observed_flags"]["wallet_used"] = True
    payload["summary"]["boundary_violation_count"] = 1

    Draft202012Validator(_schema()).validate(payload)
    StrategyReviewManifest.model_validate(payload)

    payload["review_status"] = "READY_FOR_HUMAN_REVIEW"
    with pytest.raises(ValidationError):
        StrategyReviewManifest.model_validate(payload)


def test_strategy_review_manifest_allows_missing_artifact_without_hash() -> None:
    payload = _valid_manifest()
    missing = payload["source_artifacts"][1]
    assert missing["exists"] is False
    assert "sha256" not in missing

    Draft202012Validator(_schema()).validate(payload)
    StrategyReviewManifest.model_validate(payload)


def test_strategy_review_id_rejects_path_segments() -> None:
    payload = _valid_manifest()
    for review_id in ("", ".hidden", "../foo", "foo/bar", r"foo\\bar"):
        payload["review_id"] = review_id
        with pytest.raises(ValidationError):
            StrategyReviewManifest.model_validate(payload)


def test_strategy_review_id_schema_and_model_accept_regex_valid_dotted_id() -> None:
    payload = _valid_manifest()
    payload["review_id"] = "foo..bar"

    Draft202012Validator(_schema()).validate(payload)
    StrategyReviewManifest.model_validate(payload)
