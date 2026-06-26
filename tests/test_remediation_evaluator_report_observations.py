from __future__ import annotations

from pathlib import Path

from sis.reports.remediation_evaluator_report_observations import (
    markdown_report_observations,
)


def test_markdown_report_observations_reads_summary_table_and_aliases(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    report_path = data_dir / "reports/phase_gate_review.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text(
        "\n".join(
            [
                "# Phase Gate Review",
                "",
                "## Executive Summary",
                "",
                "- phase_gate_decision: NO_GO",
                "- phase_gate_checked_files: 7",
                "- phase2_entry_reason: remain_in_phase1",
                "",
                "## Strict Validation",
                "",
                "| path | message |",
                "| --- | --- |",
                "| data/ops/current.json | missing field |",
                "",
                "## Next Actions",
                "",
                "- uv run sis validate-artifacts --strict",
            ]
        ),
        encoding="utf-8",
    )

    fields, counts = markdown_report_observations(
        {},
        {"phase_gate_review": {"phase_gate_review_report_path": str(report_path)}},
    )

    assert fields["phase_gate_decision"] == "NO_GO"
    assert fields["decision"] == "NO_GO"
    assert fields["phase_gate_checked_files"] == 7
    assert fields["checked_files"] == 7
    assert fields["phase_gate_issue_previews"] == ["data/ops/current.json: missing field"]
    assert fields["next_actions"] == ["uv run sis validate-artifacts --strict"]
    assert fields["blockers"] == ["remain_in_phase1"]
    assert counts["phase_gate_checked_files"] == 7
    assert counts["checked_files"] == 7


def test_markdown_report_observations_clears_issue_previews_when_report_says_none(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "phase_gate_review.md"
    report_path.write_text(
        "\n".join(
            [
                "# Phase Gate Review",
                "",
                "## Strict Validation",
                "",
                "| path | message |",
                "| --- | --- |",
                "| data/ops/current.json | missing field |",
                "- issues: none",
            ]
        ),
        encoding="utf-8",
    )

    fields, _counts = markdown_report_observations(
        {},
        {"phase_gate_review": {"phase_gate_review_report_path": str(report_path)}},
    )

    assert "phase_gate_issue_previews" not in fields


def test_markdown_report_observations_collects_blockers_and_ignores_table_header(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "phase_gate_review.md"
    report_path.write_text(
        "\n".join(
            [
                "# Live Evidence",
                "",
                "## Strict Validation Preview",
                "",
                "- checked_files: 3",
                "- data/live/current.json: stale",
                "",
                "## Blockers",
                "",
                "- exchange write disabled",
            ]
        ),
        encoding="utf-8",
    )

    fields, counts = markdown_report_observations(
        {},
        {"phase_gate_review": {"phase_gate_review_report_path": str(report_path)}},
    )

    assert fields["phase_gate_issue_previews"] == ["data/live/current.json: stale"]
    assert fields["blockers"] == ["exchange write disabled"]
    assert fields["checked_files"] == 3
    assert counts["checked_files"] == 3
