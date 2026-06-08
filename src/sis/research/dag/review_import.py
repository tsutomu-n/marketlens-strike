from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from pydantic import ValidationError

from sis.research.dag.review_contracts import LlmDagReview
from sis.research.dag.review_contracts import LlmReviewPackInput
from sis.research.dag.review_pack import reports_dir_for_review_dir


class ReviewImportError(ValueError):
    """Raised when a manual LLM review cannot be imported."""


@dataclass(frozen=True)
class ReviewImportResult:
    review: LlmDagReview
    normalized_path: Path
    report_path: Path


def import_review_result(pack_path: Path, result_path: Path) -> ReviewImportResult:
    try:
        pack = LlmReviewPackInput.model_validate(_read_json(pack_path))
        review = LlmDagReview.model_validate(_read_json(result_path))
        _validate_review_against_pack(review, pack)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        if isinstance(exc, ReviewImportError):
            raise
        raise ReviewImportError(str(exc)) from exc

    review_dir = pack_path.parent
    normalized_path = review_dir / "normalized_review.json"
    report_path = reports_dir_for_review_dir(review_dir) / "ndx_llm_review_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.write_text(
        json.dumps(review.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(_render_review_report(review), encoding="utf-8")
    return ReviewImportResult(
        review=review, normalized_path=normalized_path, report_path=report_path
    )


def _validate_review_against_pack(review: LlmDagReview, pack: LlmReviewPackInput) -> None:
    if review.pack_hash != pack.pack_hash:
        raise ReviewImportError(f"pack_hash mismatch: {review.pack_hash} != {pack.pack_hash}")
    if review.dag_id != pack.dag_id:
        raise ReviewImportError(f"dag_id mismatch: {review.dag_id} != {pack.dag_id}")
    unknown_refs = sorted(_evidence_refs(review) - set(pack.evidence_catalog))
    if unknown_refs:
        raise ReviewImportError("unknown evidence_refs: " + ", ".join(unknown_refs))
    if review.overall_decision in {"APPROVE", "APPROVE_WITH_WARNINGS"}:
        if review.severity_counts.BLOCKER > 0:
            raise ReviewImportError("BLOCKER finding cannot be imported with APPROVE decision")


def _evidence_refs(review: LlmDagReview) -> set[str]:
    refs: set[str] = set()
    for finding in review.findings:
        refs.update(finding.evidence_refs)
    for decision in review.required_human_decisions:
        refs.update(decision.evidence_refs)
    return refs


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_review_report(review: LlmDagReview) -> str:
    lines = [
        "# NDX Layer 2.2 LLM Review Import",
        "",
        f"- review_id: {review.review_id}",
        f"- dag_id: {review.dag_id}",
        f"- pack_hash: {review.pack_hash}",
        f"- overall_decision: {review.overall_decision}",
        f"- blocker_count: {review.severity_counts.BLOCKER}",
        f"- high_count: {review.severity_counts.HIGH}",
        f"- required_human_decisions: {len(review.required_human_decisions)}",
        "",
    ]
    if review.findings:
        lines.extend(["## Findings", ""])
        for finding in review.findings:
            lines.append(f"- {finding.finding_id}: {finding.severity}; {finding.category}")
        lines.append("")
    return "\n".join(lines)
