from __future__ import annotations

from pathlib import Path

from sis.reports.remediation_evaluator_observations import (
    apply_aliases,
    manifest_note_observations,
    markdown_report_observations,
    merge_observation_sources,
)


def test_apply_aliases_copies_phase_gate_legacy_fields_and_counts() -> None:
    fields, counts = apply_aliases(
        {
            "phase_gate_checked_files": 7,
            "phase_gate_strict_validation_issue_count": 2,
            "phase_gate_decision": "NO_GO",
            "phase_gate_reason": "remain_in_phase1",
        },
        {
            "phase_gate_checked_files": 7,
            "phase_gate_strict_validation_issue_count": 2,
        },
    )

    assert fields["checked_files"] == 7
    assert fields["issues"] == 2
    assert fields["decision"] == "NO_GO"
    assert fields["phase2_entry_reason"] == "remain_in_phase1"
    assert counts["checked_files"] == 7
    assert counts["issues"] == 2


def test_merge_observation_sources_uses_first_source_for_fields_and_counts() -> None:
    merged_fields, merged_counts, field_sources, count_sources = merge_observation_sources(
        [
            (
                "live_evidence_summary",
                {"phase_gate_decision": "READ_ONLY_GO", "shared": "first"},
                {"phase_gate_checked_files": 7, "shared_count": 1},
            ),
            (
                "markdown_reports",
                {"phase_gate_decision": "NO_GO", "shared": "second"},
                {"phase_gate_checked_files": 9, "shared_count": 2},
            ),
        ]
    )

    assert merged_fields == {"phase_gate_decision": "READ_ONLY_GO", "shared": "first"}
    assert merged_counts == {"phase_gate_checked_files": 7, "shared_count": 1}
    assert field_sources == {
        "phase_gate_decision": "live_evidence_summary",
        "shared": "live_evidence_summary",
    }
    assert count_sources == {
        "phase_gate_checked_files": "live_evidence_summary",
        "shared_count": "live_evidence_summary",
    }


def test_manifest_note_observations_reads_latest_notes_first(tmp_path: Path) -> None:
    operation_chain = tmp_path / "operation_chain.jsonl"
    operation_chain.write_text(
        "\n".join(
            [
                (
                    '{"notes":["phase_gate_decision=OLD","phase_gate_checked_files=3",'
                    '"phase_gate_issue_1=old issue"]}'
                ),
                (
                    '{"notes":["phase_gate_decision=NO_GO","phase_gate_checked_files=7",'
                    '"phase_gate_strict_validation_issue_count=2",'
                    '"phase_gate_issue_1=data/ops/current.json: missing"]}'
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    fields, counts = manifest_note_observations({"operation_chain_path": str(operation_chain)})

    assert fields["phase_gate_decision"] == "NO_GO"
    assert fields["decision"] == "NO_GO"
    assert fields["phase_gate_checked_files"] == 7
    assert fields["checked_files"] == 7
    assert fields["phase_gate_issue_previews"] == [
        "data/ops/current.json: missing",
        "old issue",
    ]
    assert counts["phase_gate_checked_files"] == 7
    assert counts["checked_files"] == 7
    assert counts["phase_gate_strict_validation_issue_count"] == 2
    assert counts["issues"] == 2


def test_markdown_report_observations_reads_summary_bullets_and_validation_tables(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    phase_gate_report = reports_dir / "phase_gate_review.md"
    phase_gate_summary.parent.mkdir(parents=True)
    phase_gate_summary.write_text(
        '{"phase_gate_review_report_path":"' + str(phase_gate_report) + '"}',
        encoding="utf-8",
    )
    phase_gate_report.write_text(
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
    planner = {"phase_gate_summary_path": str(phase_gate_summary)}

    fields, counts = markdown_report_observations(
        planner,
        {"phase_gate_review": {"phase_gate_review_report_path": str(phase_gate_report)}},
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
