from __future__ import annotations

from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet


def render_strategy_idea_candidate_set_markdown(candidate_set: StrategyIdeaCandidateSet) -> str:
    summary = candidate_set.search_ledger_summary
    lines = [
        f"# Strategy Idea Candidate Set: {candidate_set.candidate_set_id}",
        "",
        "## Summary",
        "",
        f"- candidate_set_status: `{candidate_set.candidate_set_status.value}`",
        f"- generator_version: `{candidate_set.generator_version}`",
        f"- family_count: `{summary.family_count}`",
        f"- candidate_count_total: `{summary.candidate_count_total}`",
        f"- candidate_count_shortlisted: `{summary.candidate_count_shortlisted}`",
        f"- candidate_count_rejected: `{summary.candidate_count_rejected}`",
        f"- trial_count_total: `{summary.trial_count_total}`",
        f"- candidate_cap: `{summary.candidate_cap}`",
        f"- cap_rejection_count: `{summary.cap_rejection_count}`",
        f"- duplicate_rejection_count: `{summary.duplicate_rejection_count}`",
        f"- success_only_reporting: `{str(summary.success_only_reporting).lower()}`",
        f"- sealed_test_used_for_selection: `{str(summary.sealed_test_used_for_selection).lower()}`",
        "",
        "## Parameter Grids",
        "",
        "| family | grid_count |",
        "|---|---|",
    ]
    for family, grid in sorted(candidate_set.parameter_grids.items()):
        lines.append(f"| `{family}` | `{len(grid)}` |")
    lines.extend(
        [
            "",
            "## Input Contract Validation",
            "",
            "| contract_id | validation_status | validation_path | validation_sha256 |",
            "|---|---|---|---|",
        ]
    )
    for ref in candidate_set.input_contract_validation_refs:
        lines.append(
            "| "
            f"`{ref.contract_id}` | "
            f"`{ref.validation_status.value}` | "
            f"`{ref.validation_path}` | "
            f"`{ref.validation_sha256}` |"
        )
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            "| source_id | status | path | sha256 | available_at | max_observed_timestamp |",
            "|---|---|---|---|---|---|",
        ]
    )
    for source in candidate_set.source_artifacts:
        lines.append(
            "| "
            f"`{source.source_id}` | "
            f"`{source.source_validation_status.value}` | "
            f"`{source.path}` | "
            f"`{source.sha256}` | "
            f"`{source.available_at}` | "
            f"`{source.max_observed_timestamp or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Candidate Inventory",
            "",
            "| idea_candidate_id | decision | family | raw metrics status | reason |",
            "|---|---|---|---|---|",
        ]
    )
    for candidate in candidate_set.candidate_inventory:
        reason = candidate.shortlist_reason or candidate.rejection_reason or ""
        lines.append(
            "| "
            f"`{candidate.idea_candidate_id}` | "
            f"`{candidate.decision.value}` | "
            f"`{candidate.family}` | "
            f"`{candidate.selection_adjusted_metrics_status.value}` | "
            f"`{reason}` |"
        )
    if not candidate_set.candidate_inventory:
        lines.append("|  |  |  |  | `no candidates emitted` |")
    lines.extend(
        [
            "",
            "## Selection Policy",
            "",
            f"- policy_id: `{candidate_set.selection_policy.policy_id}`",
            f"- description: {candidate_set.selection_policy.description}",
            f"- shortlisted_candidate_ids: `{', '.join(candidate_set.selection_policy.shortlisted_candidate_ids)}`",
            f"- rejected_candidate_ids: `{', '.join(candidate_set.selection_policy.rejected_candidate_ids)}`",
            "",
            "## Leakage Policy",
            "",
            f"- feature_available_at_policy: {candidate_set.leakage_policy.feature_available_at_policy}",
            f"- purge_policy: `{candidate_set.leakage_policy.purge_policy}`",
            f"- embargo_policy: `{candidate_set.leakage_policy.embargo_policy}`",
            f"- uses_sealed_test_for_selection: `{str(candidate_set.leakage_policy.uses_sealed_test_for_selection).lower()}`",
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
            "## Readiness Notice",
            "",
            "この artifact は未検証の strategy idea candidate 証跡です。alpha proof、paper / live 実行許可ではありません。",
            "",
        ]
    )
    return "\n".join(lines)
