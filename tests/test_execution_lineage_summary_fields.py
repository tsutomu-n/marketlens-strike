from __future__ import annotations

from sis.reports.execution_lineage_summary_fields import (
    execution_comparison_flat_fields,
    execution_snapshot_flat_fields,
    normalize_execution_comparison_summary,
    normalize_execution_snapshot_summary,
)


def test_normalize_execution_snapshot_summary_accepts_flat_aliases() -> None:
    normalized = normalize_execution_snapshot_summary(
        {
            "execution_overall_status": "read_only_go",
            "execution_venue_count": 3,
            "execution_report_path": "data/reports/execution_snapshot.md",
            "snapshot_reason": "all_venues_reported",
            "execution_snapshot_next_action": "continue_paper_only",
        }
    )

    assert normalized["overall_status"] == "read_only_go"
    assert normalized["venue_count"] == 3
    assert normalized["report_path"] == "data/reports/execution_snapshot.md"
    assert normalized["snapshot_reason"] == "all_venues_reported"
    assert normalized["execution_snapshot_reason"] == "all_venues_reported"
    assert normalized["execution_snapshot_reason_codes"] == ["all_venues_reported"]
    assert normalized["execution_snapshot_next_action"] == "continue_paper_only"
    assert normalized["execution_report_path"] == "data/reports/execution_snapshot.md"


def test_execution_snapshot_flat_fields_preserve_existing_key_names() -> None:
    fields = execution_snapshot_flat_fields(
        {
            "overall_status": "blocked",
            "venue_count": 0,
            "execution_snapshot_reason": "missing_snapshot",
            "execution_snapshot_reason_codes": ["missing_snapshot"],
            "execution_snapshot_root_source": "runtime",
            "execution_snapshot_next_action": "refresh_execution_snapshot",
            "report_path": "data/reports/execution_snapshot.md",
        }
    )

    assert fields == {
        "execution_overall_status": "blocked",
        "execution_venue_count": 0,
        "execution_snapshot_reason": "missing_snapshot",
        "execution_snapshot_reason_codes": ["missing_snapshot"],
        "execution_snapshot_root_source": "runtime",
        "execution_snapshot_next_action": "refresh_execution_snapshot",
        "execution_report_path": "data/reports/execution_snapshot.md",
    }


def test_normalize_execution_comparison_summary_accepts_bool_aliases() -> None:
    normalized_true = normalize_execution_comparison_summary(
        {
            "execution_comparison_all_registries_present": "true",
            "execution_comparison_report_path": "data/reports/execution_comparison.md",
            "execution_comparison_reason": "matched",
        }
    )
    normalized_false = normalize_execution_comparison_summary({"all_registries_present": "False"})

    assert normalized_true["all_registries_present"] is True
    assert normalized_true["execution_comparison_all_registries_present"] is True
    assert normalized_true["report_path"] == "data/reports/execution_comparison.md"
    assert normalized_true["execution_comparison_report_path"] == (
        "data/reports/execution_comparison.md"
    )
    assert normalized_false["all_registries_present"] is False


def test_execution_comparison_flat_fields_preserve_existing_key_names() -> None:
    fields = execution_comparison_flat_fields(
        {
            "execution_comparison_all_registries_present": "false",
            "execution_comparison_reason": "missing_registry",
            "execution_comparison_root_source": "bundle",
            "execution_comparison_report_path": "data/reports/execution_comparison.md",
        }
    )

    assert fields == {
        "execution_comparison_all_registries_present": False,
        "execution_comparison_reason": "missing_registry",
        "execution_comparison_root_source": "bundle",
        "execution_comparison_report_path": "data/reports/execution_comparison.md",
    }
