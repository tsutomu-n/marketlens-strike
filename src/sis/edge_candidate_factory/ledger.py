from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sis.edge_candidate_factory.models import (
    EdgeCandidateSearchLedgerRow,
    SmartCandidatePriorReport,
    TrialMultiplicityAccount,
)
from sis.strategy_inputs.io import write_text_artifact


@dataclass(frozen=True)
class EdgeCandidateLedgerWriteResult:
    search_ledger_path: Path
    rejection_ledger_path: Path
    search_row_count: int
    rejection_row_count: int


def ledger_rows_to_jsonl(rows: list[EdgeCandidateSearchLedgerRow]) -> str:
    text = "\n".join(
        json.dumps(
            row.model_dump(mode="json", exclude_none=True), ensure_ascii=False, sort_keys=True
        )
        for row in rows
    )
    return f"{text}\n" if text else ""


def render_smart_candidate_prior_report_markdown(
    report: SmartCandidatePriorReport,
    multiplicity_account: TrialMultiplicityAccount,
    *,
    rejection_row_count: int,
) -> str:
    lines = [
        "# Smart Candidate Prior Report",
        "",
        f"- report_id: {report.report_id}",
        f"- schema_version: {report.schema_version}",
        f"- candidate_count_total: {report.candidate_count_total}",
        f"- candidate_count_accepted: {report.candidate_count_accepted}",
        f"- candidate_count_rejected: {report.candidate_count_rejected}",
        f"- search_trial_count: {multiplicity_account.candidate_count_total}",
        f"- rejection_row_count: {rejection_row_count}",
        "- proof_status: not_alpha_or_profit_proof",
        f"- permits_live_order: {str(report.boundary.permits_live_order).lower()}",
        f"- exchange_write_used: {str(report.boundary.exchange_write_used).lower()}",
        "",
        "## Candidate Cards",
        "",
    ]
    for card in report.candidate_cards:
        lines.extend(
            [
                f"### {card.candidate_id}",
                "",
                f"- family: {card.family}",
                f"- decision: {card.candidate_decision.value}",
                f"- actions: {', '.join(card.action_set)}",
                f"- cause_priors: {', '.join(cause.value for cause in card.cause_priors)}",
                f"- expected_information_gain: {card.expected_information_gain}",
                "",
            ]
        )
    if report.known_gaps:
        lines.extend(["## Known Gaps", ""])
        lines.extend(f"- {gap}" for gap in report.known_gaps)
        lines.append("")
    return "\n".join(lines)


def write_edge_candidate_ledgers(
    *,
    out_dir: Path,
    search_rows: list[EdgeCandidateSearchLedgerRow],
    rejection_rows: list[EdgeCandidateSearchLedgerRow],
) -> EdgeCandidateLedgerWriteResult:
    search_ledger_path = out_dir / "edge_candidate_search_ledger.jsonl"
    rejection_ledger_path = out_dir / "candidate_rejections.jsonl"
    write_text_artifact(search_ledger_path, ledger_rows_to_jsonl(search_rows))
    write_text_artifact(rejection_ledger_path, ledger_rows_to_jsonl(rejection_rows))
    return EdgeCandidateLedgerWriteResult(
        search_ledger_path=search_ledger_path,
        rejection_ledger_path=rejection_ledger_path,
        search_row_count=len(search_rows),
        rejection_row_count=len(rejection_rows),
    )
