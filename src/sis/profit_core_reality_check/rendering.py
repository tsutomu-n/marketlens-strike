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
        *_input_collection_lines(check),
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


def _input_collection_lines(check: ProfitCoreRealityCheck) -> list[str]:
    lines = [
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
    ]
    if check.summary.next_action != "COLLECT_INPUTS":
        return lines
    blockers = set(check.blocker_summary.blocker_counts)
    lines.extend(["", "## Input Collection", ""])
    if "SEARCH_LEDGER_MISSING" in blockers:
        lines.append(
            "- required_input: `search_ledger.jsonl` from the same candidate generation run."
        )
    if "BLOCKED_MISSING_EVENT_OR_OUTCOME" in blockers:
        lines.extend(
            [
                "- required_input: real `crypto_perp_event.v1` with information cutoff and source refs.",
                "- required_input: matured `crypto_perp_outcome.v1` recorded after the observation horizon.",
                "- next_command_after_inputs: `uv run sis crypto-perp-truth-cycle-status --event <event.json> --outcome <outcome.json>`",
                "- next_command_after_inputs: `uv run sis crypto-perp-profit-readiness-run-local --event <event.json> --outcome <outcome.json> --notional-usd <amount>`",
            ]
        )
    if "ACTUAL_CASH_SOURCE_MISSING" in blockers:
        lines.extend(
            [
                "- required_input: cash ledger plus explicit assignment, or live measurement artifact.",
                "- do_not_run_yet: `crypto-perp-actual-cash-rows-build` until cash source exists.",
                "- do_not_run_yet: `crypto-perp-actual-cash-report-gate` until actual-cash rows exist.",
            ]
        )
    lines.extend(
        [
            "- rejected_substitute: C9 bridge outputs and backtest packs are technical artifacts, not event/outcome evidence.",
            "- rejected_substitute: dogfood/status/viewer artifacts are not profit evidence.",
            "- rejected_substitute: preview, estimate, virtual, or before-cost proxy rows are not actual cash evidence.",
        ]
    )
    return lines
