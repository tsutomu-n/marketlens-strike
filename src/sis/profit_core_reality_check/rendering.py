from __future__ import annotations

from sis.profit_core_reality_check.models import ProfitCoreRealityCheck


def render_profit_core_reality_check_markdown(check: ProfitCoreRealityCheck) -> str:
    lines = [
        "# Profit Core Reality Check",
        "",
        f"- artifact_id: `{check.artifact_id}`",
        f"- overall_status: `{check.summary.overall_status}`",
        f"- next_action: `{check.summary.next_action}`",
        f"- next_single_blocker_to_fix: `{check.next_single_blocker_to_fix}`",
        "- network_attempted: `false`",
        "- credentials_used: `false`",
        "- exchange_write_used: `false`",
        "- production_exchange_write_used: `false`",
        "- live_order_submitted: `false`",
        "- permits_live_order: `false`",
        "",
        "## Candidate Generation",
        "",
        f"- candidate_set_present: `{str(check.candidate_generation.candidate_set_present).lower()}`",
        f"- search_ledger_present: `{str(check.candidate_generation.search_ledger_present).lower()}`",
        f"- export_manifest_present: `{str(check.candidate_generation.export_manifest_present).lower()}`",
        f"- candidate_set_id: `{check.candidate_generation.candidate_set_id or 'NONE'}`",
        f"- candidate_count_total: `{check.candidate_generation.candidate_count_total}`",
        f"- candidate_count_shortlisted: `{check.candidate_generation.candidate_count_shortlisted}`",
        f"- candidate_count_rejected: `{check.candidate_generation.candidate_count_rejected}`",
        f"- success_only_reporting_detected: `{str(check.candidate_generation.success_only_reporting_detected).lower()}`",
        f"- sealed_test_used_for_selection: `{str(check.candidate_generation.sealed_test_used_for_selection).lower()}`",
        "",
        "## Bridge",
        "",
        f"- bridge_manifest_present: `{str(check.bridge_summary.bridge_manifest_present).lower()}`",
        f"- bridge_bridged_count: `{check.bridge_summary.bridge_bridged_count}`",
        f"- bridge_blocked_count: `{check.bridge_summary.bridge_blocked_count}`",
        f"- bridge_success_semantics: `{check.bridge_summary.bridge_success_semantics}`",
        f"- economic_gate_status: `{check.bridge_summary.economic_gate_status}`",
        "",
        "## Profit Readiness",
        "",
        f"- inventory_present: `{str(check.profit_readiness_summary.inventory_present).lower()}`",
        f"- inventory_status: `{check.profit_readiness_summary.inventory_status or 'NONE'}`",
        f"- source_availability_present: `{str(check.profit_readiness_summary.source_availability_present).lower()}`",
        f"- can_compute_actual_cash: `{str(check.profit_readiness_summary.can_compute_actual_cash).lower()}`",
        "",
        "## Risk Review",
        "",
        f"- risk_review_present: `{str(check.risk_review_summary.risk_review_present).lower()}`",
        f"- risk_review_status: `{check.risk_review_summary.risk_review_status or 'NONE'}`",
        f"- recommended_action: `{check.risk_review_summary.recommended_action or 'NONE'}`",
        "",
        "## Actual Cash",
        "",
        f"- actual_cash_rows_summary_present: `{str(check.actual_cash_summary.actual_cash_rows_summary_present).lower()}`",
        f"- actual_cash_row_count: `{check.actual_cash_summary.actual_cash_row_count}`",
        f"- actual_cash_report_gate_present: `{str(check.actual_cash_summary.actual_cash_report_gate_present).lower()}`",
        f"- actual_cash_gate_status: `{check.actual_cash_summary.actual_cash_gate_status or 'NONE'}`",
        "",
        "## Blockers",
        "",
    ]
    if check.blocker_summary.blocker_counts:
        lines.extend(
            f"- `{blocker}`: `{count}`"
            for blocker, count in sorted(check.blocker_summary.blocker_counts.items())
        )
    else:
        lines.append("- `NO_BLOCKER_IDENTIFIED`: `0`")
    if check.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in check.known_gaps)
    return "\n".join(lines) + "\n"
