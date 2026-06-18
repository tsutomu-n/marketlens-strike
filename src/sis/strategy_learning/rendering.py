from __future__ import annotations

from sis.strategy_learning.models import (
    StrategyAuthoringUpdateHandoff,
    StrategyLearningEvent,
    StrategyRevisionRequest,
    StrategyRevisionRequestReview,
)


def render_learning_summary_markdown(events: list[StrategyLearningEvent]) -> str:
    lines = [
        "# Strategy Learning Ledger",
        "",
        f"- event_count: `{len(events)}`",
        "",
        "| event_id | strategy_id | event_type | recommended_action | auto_applied |",
        "|---|---|---|---|---:|",
    ]
    for event in events:
        lines.append(
            f"| `{event.learning_event_id}` | `{event.strategy_id}` | `{event.event_type.value}` | `{event.recommended_action.value}` | `{str(event.auto_applied).lower()}` |"
        )
    if not events:
        lines.append("| none | none | none | none | false |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Learning events are review inputs, not automatic strategy edits.",
            "- `auto_applied` and `direct_spec_edit_allowed` remain false.",
            "- They do not permit paper execution or live execution.",
            "",
        ]
    )
    return "\n".join(lines)


def render_revision_request_markdown(request: StrategyRevisionRequest) -> str:
    lines = [
        f"# Strategy Revision Request: {request.revision_request_id}",
        "",
        f"- strategy_id: `{request.strategy_id}`",
        f"- request_status: `{request.request_status.value}`",
        f"- reason: `{request.reason}`",
        f"- requires_human_review: `{str(request.requires_human_review).lower()}`",
        f"- auto_applied: `{str(request.auto_applied).lower()}`",
        f"- direct_spec_edit_allowed: `{str(request.direct_spec_edit_allowed).lower()}`",
        f"- paper_execution_allowed: `{str(request.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(request.live_allowed).lower()}`",
        "",
        "## Source Learning Events",
        "",
    ]
    for event_id in request.source_learning_event_ids:
        lines.append(f"- `{event_id}`")
    if not request.source_learning_event_ids:
        lines.append("- none")

    lines.extend(["", "## Requested Changes", ""])
    for change in request.requested_changes:
        lines.append(f"- {change}")
    if not request.requested_changes:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "| artifact | path | sha256 | schema_version |",
            "|---|---|---|---|",
        ]
    )
    for artifact in request.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This request does not edit Strategy Authoring YAML.",
            "- A human must review it before any authoring update.",
            "- It does not permit paper execution, live execution, wallet use, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)


def render_revision_request_review_markdown(review: StrategyRevisionRequestReview) -> str:
    source = review.source_revision_request
    lines = [
        f"# Strategy Revision Request Review: {review.revision_request_id}",
        "",
        f"- strategy_id: `{review.strategy_id}`",
        f"- reviewer: `{review.reviewer}`",
        f"- decision: `{review.decision.value}`",
        f"- authoring_update_input_allowed: `{str(review.authoring_update_input_allowed).lower()}`",
        f"- requires_human_authoring_update: `{str(review.requires_human_authoring_update).lower()}`",
        f"- auto_applied: `{str(review.auto_applied).lower()}`",
        f"- direct_spec_edit_allowed: `{str(review.direct_spec_edit_allowed).lower()}`",
        f"- paper_execution_allowed: `{str(review.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(review.live_allowed).lower()}`",
        "",
        "## Source Revision Request",
        "",
        f"- path: `{source.revision_request_path}`",
        f"- sha256: `{source.revision_request_sha256}`",
        f"- request_status: `{source.request_status.value}`",
        f"- requested_change_count: `{source.requested_change_count}`",
        f"- source_learning_event_count: `{source.source_learning_event_count}`",
        "",
        "## Rationale",
        "",
        review.rationale,
        "",
        "## Required Actions",
        "",
    ]
    for action in review.required_actions:
        lines.append(f"- {action}")
    if not review.required_actions:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This review records a human decision for a revision request.",
            "- It does not edit Strategy Authoring YAML.",
            "- `APPROVE_FOR_AUTHORING_UPDATE` means the request can be used as input to a separate human authoring update.",
            "- It does not permit paper execution, live execution, wallet use, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)


def render_authoring_update_handoff_markdown(
    handoff: StrategyAuthoringUpdateHandoff,
) -> str:
    lines = [
        f"# Strategy Authoring Update Handoff: {handoff.handoff_id}",
        "",
        f"- strategy_id: `{handoff.strategy_id}`",
        f"- revision_request_id: `{handoff.revision_request_id}`",
        f"- handoff_status: `{handoff.handoff_status.value}`",
        f"- review_decision: `{handoff.review_decision.value}`",
        f"- authoring_update_input_allowed: `{str(handoff.authoring_update_input_allowed).lower()}`",
        f"- requires_human_authoring_update: `{str(handoff.requires_human_authoring_update).lower()}`",
        f"- auto_applied: `{str(handoff.auto_applied).lower()}`",
        f"- direct_spec_edit_allowed: `{str(handoff.direct_spec_edit_allowed).lower()}`",
        f"- paper_execution_allowed: `{str(handoff.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(handoff.live_allowed).lower()}`",
        "",
        "## Authoring Spec",
        "",
        f"- path: `{handoff.authoring_spec_path}`",
        f"- sha256: `{handoff.authoring_spec_sha256}`",
        f"- schema_version: `{handoff.authoring_spec_schema_version or ''}`",
        f"- strategy_id: `{handoff.authoring_spec_strategy_id or ''}`",
        f"- strategy_id_matches_authoring_spec: `{handoff.strategy_id_matches_authoring_spec}`",
        "",
        "## Requested Changes",
        "",
    ]
    for change in handoff.requested_changes:
        lines.append(f"- {change}")
    if not handoff.requested_changes:
        lines.append("- none")

    lines.extend(["", "## Authoring Update Tasks", ""])
    for task in handoff.authoring_update_tasks:
        lines.append(f"- {task}")
    if not handoff.authoring_update_tasks:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "| artifact | path | sha256 | schema_version |",
            "|---|---|---|---|",
        ]
    )
    for artifact in handoff.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This handoff is input for a separate human Strategy Authoring edit.",
            "- It does not edit Strategy Authoring YAML.",
            "- It does not validate that the edited strategy is ready for backtest, paper, or live.",
            "- It does not permit paper execution, live execution, wallet use, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)
