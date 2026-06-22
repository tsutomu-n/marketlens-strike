from __future__ import annotations

from sis.strategy_input_feedback.models import (
    StrategyInputContractUpdateProposal,
    StrategyInputContractUpdateReview,
)


def render_input_feedback_proposal_markdown(
    proposal: StrategyInputContractUpdateProposal,
) -> str:
    lines = [
        "# Strategy Input Contract Update Proposal",
        "",
        f"- proposal_id: `{proposal.proposal_id}`",
        f"- strategy_id: `{proposal.strategy_id}`",
        f"- status: `{proposal.status.value}`",
        f"- requires_human_review: `{str(proposal.requires_human_review).lower()}`",
        f"- auto_applied: `{str(proposal.auto_applied).lower()}`",
        f"- direct_contract_edit_allowed: `{str(proposal.direct_contract_edit_allowed).lower()}`",
        "",
        "This artifact is review input only. It does not edit Strategy Input Contract files.",
        "",
        "## Source Artifacts",
        "",
    ]
    for source in proposal.source_artifacts:
        lines.append(
            f"- `{source.artifact_kind.value}` `{source.path}` `{source.sha256}` "
            f"`{source.schema_version}`"
        )
    lines.extend(["", "## Proposed Changes", ""])
    if not proposal.proposed_changes:
        lines.append("- none")
    for change in proposal.proposed_changes:
        lines.extend(
            [
                f"### {change.change_id}",
                "",
                f"- target_section: `{change.target_section.value}`",
                f"- recommendation: {change.recommendation}",
                f"- evidence_summary: {change.evidence_summary}",
                f"- source_reason: {change.source_reason}",
                "",
            ]
        )
    if proposal.blocked_reasons:
        lines.extend(["## Blocked Reasons", ""])
        lines.extend(f"- {reason}" for reason in proposal.blocked_reasons)
    return "\n".join(lines).rstrip() + "\n"


def render_input_feedback_review_markdown(review: StrategyInputContractUpdateReview) -> str:
    lines = [
        "# Strategy Input Contract Update Review",
        "",
        f"- review_id: `{review.review_id}`",
        f"- proposal_id: `{review.proposal_id}`",
        f"- strategy_id: `{review.strategy_id}`",
        f"- decision: `{review.decision.value}`",
        f"- manual_contract_update_input_allowed: "
        f"`{str(review.manual_contract_update_input_allowed).lower()}`",
        f"- auto_applied: `{str(review.auto_applied).lower()}`",
        f"- direct_contract_edit_allowed: `{str(review.direct_contract_edit_allowed).lower()}`",
        "",
        "This review can authorize manual contract update input only. It does not apply changes.",
        "",
        "## Rationale",
        "",
        review.rationale,
        "",
        "## Approved Change IDs",
        "",
    ]
    lines.extend(f"- `{change_id}`" for change_id in review.approved_change_ids)
    if not review.approved_change_ids:
        lines.append("- none")
    lines.extend(["", "## Required Actions", ""])
    lines.extend(f"- {action}" for action in review.required_actions)
    if not review.required_actions:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"
