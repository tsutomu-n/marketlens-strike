from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sis.strategy_review.manifest import SourceArtifact
from sis.strategy_review.provenance import read_source_json, repo_relative_path
from sis.strategy_review.sections import ReviewSection
from sis.strategy_review.source_artifacts import (
    invalid_optional_artifact,
    missing_optional_artifact,
    present_optional_artifact,
)


def _string_list_field(payload: dict[str, Any], field_name: str) -> list[str]:
    value = payload.get(field_name)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return value


def _object_field(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    return value


def lifecycle_review_summary(path: Path) -> tuple[SourceArtifact, ReviewSection]:
    if not path.exists():
        return (
            missing_optional_artifact("lifecycle_review", path),
            ReviewSection(
                section_id="lifecycle_summary",
                title="Lifecycle Summary",
                status="missing",
                markdown=f"- status: `missing`\n- path: `{repo_relative_path(path)}`",
                source_artifact_keys=("lifecycle_review",),
            ),
        )
    try:
        payload = read_source_json(path)
        if payload.get("schema_version") != "strategy_lifecycle_review.v1":
            raise ValueError("schema_version must be strategy_lifecycle_review.v1")
        decision_reasons = _string_list_field(payload, "decision_reasons")
        next_actions = _string_list_field(payload, "next_actions")
        input_status = _object_field(payload, "input_status")
        blocker_counts = _object_field(payload, "blocker_counts")
    except Exception as exc:
        return (
            invalid_optional_artifact("lifecycle_review", path, exc),
            ReviewSection(
                section_id="lifecycle_summary",
                title="Lifecycle Summary",
                status="invalid",
                markdown=f"- status: `invalid`\n- path: `{repo_relative_path(path)}`\n- error: `{exc}`",
                source_artifact_keys=("lifecycle_review",),
            ),
        )

    summary = {
        "decision": payload.get("decision"),
        "decision_reasons": decision_reasons,
        "next_actions": next_actions,
        "input_status": input_status,
        "blocker_counts": blocker_counts,
        "permits_live_order": payload.get("permits_live_order"),
        "wallet_used": payload.get("wallet_used"),
        "venue_write_used": payload.get("venue_write_used"),
        "exchange_write_used": payload.get("exchange_write_used"),
    }
    markdown = "\n".join(
        [
            "- status: `present`",
            f"- decision: `{summary['decision']}`",
            f"- decision_reasons: `{', '.join(summary['decision_reasons'])}`",
            f"- next_actions: `{', '.join(summary['next_actions'])}`",
            f"- input_status: `{json.dumps(summary['input_status'], sort_keys=True)}`",
            f"- blocker_counts: `{json.dumps(summary['blocker_counts'], sort_keys=True)}`",
            f"- permits_live_order: `{str(summary['permits_live_order']).lower()}`",
            f"- wallet_used: `{str(summary['wallet_used']).lower()}`",
            f"- venue_write_used: `{str(summary['venue_write_used']).lower()}`",
            f"- exchange_write_used: `{str(summary['exchange_write_used']).lower()}`",
        ]
    )
    return (
        present_optional_artifact("lifecycle_review", path, summary, payload=payload),
        ReviewSection(
            section_id="lifecycle_summary",
            title="Lifecycle Summary",
            status="present",
            markdown=markdown,
            source_artifact_keys=("lifecycle_review",),
        ),
    )
