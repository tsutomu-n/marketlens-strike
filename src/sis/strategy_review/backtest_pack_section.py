from __future__ import annotations

from sis.strategy_review.manifest import SourceArtifact
from sis.strategy_review.sections import ReviewSection


def backtest_pack_section(source_artifacts: list[SourceArtifact]) -> ReviewSection:
    by_key = {artifact.artifact_key: artifact for artifact in source_artifacts}
    pack = by_key.get("pack")
    validation = by_key.get("pack_validation")
    pack_summary = pack.summary if pack is not None else {}
    validation_summary = validation.summary if validation is not None else {}
    lines = [
        f"- pack_status: `{pack.status.value if pack else 'missing'}`",
        f"- validation_status: `{validation.status.value if validation else 'missing'}`",
        f"- validation_decision: `{validation_summary.get('decision')}`",
        f"- suite_run_count: `{pack_summary.get('suite_run_count', pack_summary.get('summary', {}).get('suite_run_count'))}`",
        f"- suite_method_count: `{pack_summary.get('suite_method_count', pack_summary.get('summary', {}).get('suite_method_count'))}`",
        f"- pack_validation_pass_is_readiness_proof: `{str(False).lower()}`",
    ]
    return ReviewSection(
        section_id="backtest_pack_validation_summary",
        title="Backtest Pack / Validation Summary",
        status="present",
        markdown="\n".join(lines),
        source_artifact_keys=("pack", "pack_validation"),
    )
