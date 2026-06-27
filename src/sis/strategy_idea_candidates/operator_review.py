from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.policies import StrategyIdeaCandidatePolicyValidationResult
from sis.strategy_inputs.io import write_text_artifact


@dataclass(frozen=True)
class StrategyIdeaCandidateOperatorReviewWriteResult:
    report_path: Path


class StrategyIdeaCandidateOperatorReviewError(ValueError):
    pass


class StrategyIdeaCandidateOperatorReviewOutputExistsError(
    StrategyIdeaCandidateOperatorReviewError
):
    pass


def render_strategy_idea_candidate_operator_review_markdown(
    candidate_set: StrategyIdeaCandidateSet,
    *,
    policy_validation: StrategyIdeaCandidatePolicyValidationResult | None = None,
) -> str:
    summary = candidate_set.search_ledger_summary
    rejection_reasons = Counter(
        candidate.rejection_reason or ""
        for candidate in candidate_set.candidate_inventory
        if candidate.rejection_reason
    )
    policy_status = _policy_status(policy_validation)
    lines = [
        f"# Operator Review: {candidate_set.candidate_set_id}",
        "",
        "## Review Summary",
        "",
        f"- candidate_set_status: `{candidate_set.candidate_set_status.value}`",
        f"- generator_version: `{candidate_set.generator_version}`",
        f"- candidate_count_total: `{summary.candidate_count_total}`",
        f"- candidate_count_shortlisted: `{summary.candidate_count_shortlisted}`",
        f"- candidate_count_rejected: `{summary.candidate_count_rejected}`",
        f"- candidate_cap: `{summary.candidate_cap}`",
        f"- cap_rejection_count: `{summary.cap_rejection_count}`",
        f"- duplicate_rejection_count: `{summary.duplicate_rejection_count}`",
        f"- selection_policy: `{candidate_set.selection_policy.policy_id}`",
        f"- policy_validation: `{policy_status}`",
        "",
        "## Selection Policy",
        "",
        f"- description: {candidate_set.selection_policy.description}",
        f"- shortlisted_candidate_ids: `{', '.join(candidate_set.selection_policy.shortlisted_candidate_ids)}`",
        f"- rejected_candidate_ids: `{', '.join(candidate_set.selection_policy.rejected_candidate_ids)}`",
        "",
        "## Known Gaps",
        "",
    ]
    for gap in candidate_set.selection_policy.known_gaps:
        lines.append(f"- {gap}")
    if not candidate_set.selection_policy.known_gaps:
        lines.append("- none recorded")

    lines.extend(
        [
            "",
            "## Rejection Reasons",
            "",
        ]
    )
    if rejection_reasons:
        for reason, count in sorted(rejection_reasons.items()):
            lines.append(f"- `{count}` x {reason}")
    else:
        lines.append("- none recorded")

    lines.extend(
        [
            "",
            "## Policy Validation",
            "",
            f"- status: `{policy_status}`",
        ]
    )
    if policy_validation is not None and policy_validation.failures:
        for failure in policy_validation.failures:
            lines.append(f"- failure: {failure}")
    elif policy_validation is None:
        lines.append("- not run")
    else:
        lines.append("- no failures")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- permits_live_order: `false`",
            "- permits_paper_candidate: `false`",
            "- permits_paper_intent_preview: `false`",
            "- auto_promote: `false`",
            "- generated_strategy_idea_is_final: `false`",
            "- wallet_used: `false`",
            "- signing_used: `false`",
            "- exchange_write_used: `false`",
            "",
            "## Notice",
            "",
            "This review surface is for human inspection of unverified candidate generation evidence. It is not alpha proof, profit proof, paper / live approval, wallet approval, signing approval, or exchange-write approval.",
            "",
        ]
    )
    return "\n".join(lines)


def write_strategy_idea_candidate_operator_review(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    out_dir: Path,
    policy_validation: StrategyIdeaCandidatePolicyValidationResult | None = None,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateOperatorReviewWriteResult:
    report_path = out_dir / "strategy_idea_candidate_operator_review.md"
    if not replace_existing and report_path.exists():
        raise StrategyIdeaCandidateOperatorReviewOutputExistsError(
            f"output already exists: {report_path}"
        )
    write_text_artifact(
        report_path,
        render_strategy_idea_candidate_operator_review_markdown(
            candidate_set,
            policy_validation=policy_validation,
        ),
    )
    return StrategyIdeaCandidateOperatorReviewWriteResult(report_path=report_path)


def _policy_status(policy_validation: StrategyIdeaCandidatePolicyValidationResult | None) -> str:
    if policy_validation is None:
        return "NOT_RUN"
    return "PASS" if policy_validation.passed else "FAIL"
