from __future__ import annotations

from sis.reports.remediation_evaluator_observation_fields import collect_mapped_observations


def test_collect_mapped_observations_preserves_existing_targets_and_counts_ints() -> None:
    fields, counts = collect_mapped_observations(
        {
            "phase_gate_decision": "READ_ONLY_GO",
            "phase_gate_checked_files": 7,
            "phase2_entry_allowed": "True",
            "ignored_none": None,
        },
        {
            "phase_gate_decision": "decision",
            "phase_gate_checked_files": "checked_files",
            "phase2_entry_allowed": "phase2_entry_allowed",
            "ignored_none": "ignored_none",
        },
        observed_fields={"decision": "NO_GO"},
        observed_counts={"checked_files": 3},
    )

    assert fields == {
        "decision": "NO_GO",
        "checked_files": 7,
        "phase2_entry_allowed": True,
    }
    assert counts == {
        "checked_files": 3,
        "phase2_entry_allowed": True,
    }


def test_collect_mapped_observations_collects_issue_previews() -> None:
    fields, counts = collect_mapped_observations(
        {
            "phase_gate_strict_validation_issues": [
                {"path": "data/ops/current.json", "message": "missing field"},
            ],
            "phase_gate_checked_files": "4",
        },
        {
            "phase_gate_strict_validation_issues": "phase_gate_issue_previews",
            "phase_gate_checked_files": "phase_gate_checked_files",
        },
        issue_preview_source_keys={"phase_gate_strict_validation_issues"},
    )

    assert fields == {
        "phase_gate_issue_previews": ["data/ops/current.json: missing field"],
        "phase_gate_checked_files": 4,
    }
    assert counts == {"phase_gate_checked_files": 4}


def test_collect_mapped_observations_omits_empty_issue_previews() -> None:
    fields, counts = collect_mapped_observations(
        {"phase_gate_strict_validation_issues": []},
        {"phase_gate_strict_validation_issues": "phase_gate_issue_previews"},
        issue_preview_source_keys={"phase_gate_strict_validation_issues"},
    )

    assert fields == {}
    assert counts == {}
