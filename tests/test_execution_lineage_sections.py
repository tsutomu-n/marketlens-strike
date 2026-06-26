from __future__ import annotations

from sis.reports.execution_lineage_sections import (
    latest_execution_flat_lines,
    latest_execution_flat_section_lines,
    latest_execution_flat_sections,
    latest_execution_lineage_flat_lines,
    latest_execution_section_lines,
    latest_execution_sections,
)


def test_latest_execution_section_lines_normalizes_execution_summaries() -> None:
    assert latest_execution_section_lines(
        "## Latest Execution",
        {"execution_overall_status": "ok", "execution_venue_count": 2},
        {"execution_comparison_all_registries_present": "true"},
    ) == [
        "## Latest Execution",
        "",
        "- overall_status: ok",
        "- venue_count: 2",
        "- all_registries_present: True",
        "",
    ]


def test_latest_execution_section_lines_omits_empty_execution_summary() -> None:
    assert latest_execution_section_lines("## Empty", {}, {"all_registries_present": True}) == []


def test_latest_execution_sections_concatenates_non_empty_sections() -> None:
    assert latest_execution_sections(
        [
            ("## Empty", {}, {}),
            (
                "## Timeline",
                {"overall_status": "ok", "venue_count": 1},
                {"all_registries_present": False},
            ),
        ]
    ) == [
        "## Timeline",
        "",
        "- overall_status: ok",
        "- venue_count: 1",
        "- all_registries_present: False",
        "",
    ]


def test_latest_execution_flat_section_lines_omits_all_empty_values() -> None:
    assert (
        latest_execution_flat_section_lines(
            "## Flat",
            overall_status=None,
            venue_count=None,
            all_registries_present=None,
        )
        == []
    )


def test_latest_execution_flat_sections_preserves_section_order() -> None:
    assert latest_execution_flat_sections(
        [
            ("## Timeline", "ok", 2, True),
            ("## Bundle", None, None, None),
            ("## Cycle", "warn", 1, False),
        ]
    ) == [
        "## Timeline",
        "",
        "- overall_status: ok",
        "- venue_count: 2",
        "- all_registries_present: True",
        "",
        "## Cycle",
        "",
        "- overall_status: warn",
        "- venue_count: 1",
        "- all_registries_present: False",
        "",
    ]


def test_latest_execution_flat_lines_supports_custom_labels() -> None:
    assert latest_execution_flat_lines(
        overall_status="ok",
        venue_count=2,
        all_registries_present=True,
        overall_status_label="status",
        venue_count_label="venues",
        all_registries_present_label="registries",
    ) == [
        "- status: ok",
        "- venues: 2",
        "- registries: True",
    ]


def test_latest_execution_lineage_flat_lines_preserves_all_lineage_labels() -> None:
    assert latest_execution_lineage_flat_lines(
        {
            "timeline_latest_execution_overall_status": "ok",
            "timeline_latest_execution_venue_count": 2,
            "timeline_latest_execution_comparison_all_registries_present": True,
            "bundle_history_latest_execution_overall_status": "warn",
            "bundle_history_latest_execution_venue_count": 1,
            "bundle_history_latest_execution_comparison_all_registries_present": False,
            "cycle_history_latest_execution_overall_status": "ok",
            "cycle_history_latest_execution_venue_count": 3,
            "cycle_history_latest_execution_comparison_all_registries_present": True,
        }
    ) == [
        "- timeline_latest_execution_overall_status: ok",
        "- timeline_latest_execution_venue_count: 2",
        "- timeline_latest_execution_comparison_all_registries_present: True",
        "- bundle_history_latest_execution_overall_status: warn",
        "- bundle_history_latest_execution_venue_count: 1",
        "- bundle_history_latest_execution_comparison_all_registries_present: False",
        "- cycle_history_latest_execution_overall_status: ok",
        "- cycle_history_latest_execution_venue_count: 3",
        "- cycle_history_latest_execution_comparison_all_registries_present: True",
    ]
