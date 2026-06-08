from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from pydantic import ValidationError

from sis.research.dag.freeze_manifest import write_freeze_manifest
from sis.research.dag.review_contracts import Layer22ExitDecision
from sis.research.dag.review_contracts import Layer22HumanResolutions
from sis.research.dag.review_contracts import ExitGateDecision
from sis.research.dag.review_contracts import LlmDagReview
from sis.research.dag.review_contracts import LlmReviewPackInput
from sis.research.dag.review_pack import ReviewPackPrecheckError
from sis.research.dag.review_pack import compute_current_pack_hash
from sis.research.dag.review_pack import reports_dir_for_review_dir


class ExitGateError(ValueError):
    """Raised when the exit gate input cannot be evaluated."""


@dataclass(frozen=True)
class ExitGateResult:
    decision: Layer22ExitDecision
    decision_path: Path
    report_path: Path
    freeze_manifest_path: Path | None


def run_exit_gate(
    *,
    root: Path,
    pack_path: Path,
    review_path: Path,
    out_dir: Path,
    human_resolutions_path: Path | None = None,
    require_second_review: bool = False,
) -> ExitGateResult:
    try:
        pack = LlmReviewPackInput.model_validate(_read_json(pack_path))
        review = LlmDagReview.model_validate(_read_json(review_path))
        resolutions = _load_resolutions(human_resolutions_path, review_dir=pack_path.parent)
        _validate_gate_inputs(root=root, pack=pack, review=review, resolutions=resolutions)
    except (
        OSError,
        json.JSONDecodeError,
        ValidationError,
        ValueError,
        ReviewPackPrecheckError,
    ) as exc:
        if isinstance(exc, ExitGateError):
            raise
        raise ExitGateError(str(exc)) from exc

    resolved_ids = resolutions.resolved_decision_ids() if resolutions is not None else set[str]()
    required_ids = {decision.decision_id for decision in review.required_human_decisions}
    high_resolution_ids = {
        finding.human_decision_id
        for finding in review.findings
        if finding.severity == "HIGH" and finding.human_decision_id is not None
    }
    unresolved = sorted((required_ids | high_resolution_ids) - resolved_ids)
    blocker_count = review.severity_counts.BLOCKER
    high_count = review.severity_counts.HIGH
    second_review_required = _second_review_required(
        review=review,
        require_second_review=require_second_review,
    )
    decision_value = _decision_value(
        review=review,
        unresolved=unresolved,
        require_second_review=require_second_review,
        resolved_ids=resolved_ids,
    )
    decision = Layer22ExitDecision(
        schema_version="layer_2_2_exit_decision.v1",
        dag_id=review.dag_id,
        decision=decision_value,
        pack_hash=pack.pack_hash,
        review_ids=[review.review_id],
        unresolved_human_decisions=unresolved,
        blocker_count=blocker_count,
        high_count=high_count,
        second_review_required=second_review_required,
        created_at=datetime.now(timezone.utc),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    decision_path = out_dir / "layer_2_2_exit_decision.json"
    decision_path.write_text(
        json.dumps(decision.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    freeze_manifest_path: Path | None = None
    if decision.decision == "APPROVE_2_3":
        freeze_manifest_path = out_dir / "layer_2_2_freeze_manifest.json"
        write_freeze_manifest(
            root=root,
            artifact_dir=Path(pack.artifact_dir),
            decision=decision,
            out_path=freeze_manifest_path,
        )
    report_path = reports_dir_for_review_dir(out_dir) / "ndx_layer_2_2_exit_gate_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_exit_gate_report(decision), encoding="utf-8")
    return ExitGateResult(
        decision=decision,
        decision_path=decision_path,
        report_path=report_path,
        freeze_manifest_path=freeze_manifest_path,
    )


def _validate_gate_inputs(
    *,
    root: Path,
    pack: LlmReviewPackInput,
    review: LlmDagReview,
    resolutions: Layer22HumanResolutions | None,
) -> None:
    if review.pack_hash != pack.pack_hash:
        raise ExitGateError(f"pack_hash mismatch: {review.pack_hash} != {pack.pack_hash}")
    if review.dag_id != pack.dag_id:
        raise ExitGateError(f"dag_id mismatch: {review.dag_id} != {pack.dag_id}")
    if resolutions is not None:
        if resolutions.pack_hash != pack.pack_hash:
            raise ExitGateError("human resolutions pack_hash mismatch")
        if resolutions.dag_id != pack.dag_id:
            raise ExitGateError("human resolutions dag_id mismatch")
    current_hash = compute_current_pack_hash(root=root, artifact_dir=Path(pack.artifact_dir))
    if current_hash != pack.pack_hash:
        raise ExitGateError(
            f"current artifact pack_hash mismatch: {current_hash} != {pack.pack_hash}"
        )


def _decision_value(
    *,
    review: LlmDagReview,
    unresolved: list[str],
    require_second_review: bool,
    resolved_ids: set[str],
) -> ExitGateDecision:
    if require_second_review:
        return "REVISE_2_2"
    if _is_confirmed_reject_seed(review, resolved_ids):
        return "REJECT_SEED"
    if review.severity_counts.BLOCKER > 0:
        return "REVISE_2_2"
    if unresolved:
        return "REVISE_2_2"
    if review.overall_decision in {"REVISE_REQUIRED", "INSUFFICIENT_EVIDENCE"}:
        return "REVISE_2_2"
    if review.overall_decision == "REJECT_SEED":
        return "REVISE_2_2"
    return "APPROVE_2_3"


def _is_confirmed_reject_seed(review: LlmDagReview, resolved_ids: set[str]) -> bool:
    if review.overall_decision != "REJECT_SEED":
        return False
    reject_categories = {"causal_misspecification", "temporal_leakage"}
    for finding in review.findings:
        if finding.category in reject_categories and finding.human_decision_id in resolved_ids:
            return True
    return False


def _second_review_required(*, review: LlmDagReview, require_second_review: bool) -> bool:
    return (
        require_second_review
        or review.severity_counts.BLOCKER > 0
        or review.severity_counts.HIGH > 0
        or review.overall_decision in {"REVISE_REQUIRED", "REJECT_SEED"}
        or bool(review.required_human_decisions)
    )


def _load_resolutions(
    path: Path | None,
    *,
    review_dir: Path,
) -> Layer22HumanResolutions | None:
    candidate = path or (review_dir / "layer_2_2_human_resolutions.json")
    if not candidate.exists():
        return None
    return Layer22HumanResolutions.model_validate(_read_json(candidate))


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_exit_gate_report(decision: Layer22ExitDecision) -> str:
    lines = [
        "# NDX Layer 2.2 Exit Gate Report",
        "",
        f"- dag_id: {decision.dag_id}",
        f"- decision: {decision.decision}",
        f"- pack_hash: {decision.pack_hash}",
        f"- review_ids: {', '.join(decision.review_ids)}",
        f"- blocker_count: {decision.blocker_count}",
        f"- high_count: {decision.high_count}",
        f"- second_review_required: {decision.second_review_required}",
        f"- unresolved_human_decisions: {', '.join(decision.unresolved_human_decisions) or 'none'}",
        "",
    ]
    return "\n".join(lines)
