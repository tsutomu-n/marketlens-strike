from __future__ import annotations

from sis.reports.remediation_evaluator_observation_core import (
    apply_aliases,
    merge_observation_sources,
)


def test_apply_aliases_copies_phase_gate_legacy_fields_and_counts() -> None:
    fields, counts = apply_aliases(
        {
            "phase_gate_checked_files": 7,
            "phase_gate_strict_validation_issue_count": 2,
            "phase_gate_decision": "NO_GO",
            "phase_gate_reason": "remain_in_phase1",
            "checked_files": 5,
        },
        {
            "phase_gate_checked_files": 7,
            "phase_gate_strict_validation_issue_count": 2,
            "checked_files": 5,
        },
    )

    assert fields["checked_files"] == 5
    assert fields["issues"] == 2
    assert fields["decision"] == "NO_GO"
    assert fields["phase2_entry_reason"] == "remain_in_phase1"
    assert counts["checked_files"] == 5
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
