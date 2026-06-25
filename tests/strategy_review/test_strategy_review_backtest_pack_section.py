from __future__ import annotations

from sis.strategy_review.backtest_pack_section import backtest_pack_section
from sis.strategy_review.manifest import SourceArtifact, SourceArtifactStatus


SHA256_A = "sha256:" + "a" * 64
SHA256_B = "sha256:" + "b" * 64


def _artifact(
    artifact_key: str,
    *,
    status: SourceArtifactStatus = SourceArtifactStatus.PRESENT,
    summary: dict | None = None,
) -> SourceArtifact:
    if status is SourceArtifactStatus.MISSING:
        return SourceArtifact(
            artifact_key=artifact_key,
            path=f"data/{artifact_key}.json",
            exists=False,
            required=True,
            status=status,
            summary=summary or {},
        )
    return SourceArtifact(
        artifact_key=artifact_key,
        path=f"data/{artifact_key}.json",
        exists=True,
        required=True,
        status=status,
        sha256=SHA256_A if artifact_key == "pack" else SHA256_B,
        bytes=100,
        summary=summary or {},
        error="invalid input" if status is SourceArtifactStatus.INVALID else None,
    )


def test_backtest_pack_section_reports_missing_pack_and_validation() -> None:
    section = backtest_pack_section([])

    assert section.section_id == "backtest_pack_validation_summary"
    assert section.title == "Backtest Pack / Validation Summary"
    assert section.status == "present"
    assert section.source_artifact_keys == ("pack", "pack_validation")
    assert "- pack_status: `missing`" in section.markdown
    assert "- validation_status: `missing`" in section.markdown
    assert "- validation_decision: `None`" in section.markdown
    assert "- pack_validation_pass_is_readiness_proof: `false`" in section.markdown


def test_backtest_pack_section_uses_top_level_pack_counts() -> None:
    section = backtest_pack_section(
        [
            _artifact("pack", summary={"suite_run_count": 3, "suite_method_count": 5}),
            _artifact("pack_validation", summary={"decision": "PASS"}),
        ]
    )

    assert "- pack_status: `present`" in section.markdown
    assert "- validation_status: `present`" in section.markdown
    assert "- validation_decision: `PASS`" in section.markdown
    assert "- suite_run_count: `3`" in section.markdown
    assert "- suite_method_count: `5`" in section.markdown
    assert "- pack_validation_pass_is_readiness_proof: `false`" in section.markdown


def test_backtest_pack_section_falls_back_to_nested_summary_counts() -> None:
    section = backtest_pack_section(
        [
            _artifact("pack", summary={"summary": {"suite_run_count": 7, "suite_method_count": 9}}),
            _artifact("pack_validation", summary={"decision": "WARN"}),
        ]
    )

    assert "- validation_decision: `WARN`" in section.markdown
    assert "- suite_run_count: `7`" in section.markdown
    assert "- suite_method_count: `9`" in section.markdown


def test_backtest_pack_section_reports_invalid_artifact_statuses() -> None:
    section = backtest_pack_section(
        [
            _artifact("pack", status=SourceArtifactStatus.INVALID),
            _artifact("pack_validation", status=SourceArtifactStatus.MISSING),
        ]
    )

    assert "- pack_status: `invalid`" in section.markdown
    assert "- validation_status: `missing`" in section.markdown
