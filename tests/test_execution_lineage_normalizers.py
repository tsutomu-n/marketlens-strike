from __future__ import annotations

from sis.reports.execution_lineage_normalizers import (
    defaulted_all_latest_execution_lineage_fields,
    first_remapped_latest_execution_lineage_fields,
    latest_execution_flat_lines,
    latest_execution_lineage_fields_from_payload,
    latest_execution_lineage_from_notes,
    latest_execution_payload_and_fields_from_summary,
    normalize_execution_comparison_summary,
    normalize_execution_snapshot_summary,
)


def test_normalize_execution_snapshot_and_comparison_summary_accept_aliases() -> None:
    snapshot = normalize_execution_snapshot_summary(
        {
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
            "execution_report_path": "data/reports/execution_snapshot.md",
            "snapshot_reason": "connected",
        }
    )
    comparison = normalize_execution_comparison_summary(
        {
            "execution_comparison_all_registries_present": "true",
            "execution_comparison_report_path": "data/reports/execution_comparison.md",
        }
    )

    assert snapshot["overall_status"] == "ok"
    assert snapshot["venue_count"] == 2
    assert snapshot["execution_snapshot_reason"] == "connected"
    assert comparison["all_registries_present"] is True
    assert comparison["report_path"] == "data/reports/execution_comparison.md"


def test_latest_execution_lineage_from_payload_flattens_three_sources() -> None:
    fields = latest_execution_lineage_fields_from_payload(
        timeline_latest_execution_summary={"overall_status": "ok", "venue_count": 2},
        timeline_latest_execution_comparison_summary={"all_registries_present": True},
        bundle_history_latest_execution_summary={"overall_status": "warn", "venue_count": 1},
        bundle_history_latest_execution_comparison_summary={"all_registries_present": False},
        cycle_history_latest_execution_summary={"overall_status": "ok", "venue_count": 3},
        cycle_history_latest_execution_comparison_summary={"all_registries_present": True},
    )

    assert fields["timeline_latest_execution_overall_status"] == "ok"
    assert fields["timeline_latest_execution_venue_count"] == 2
    assert fields["timeline_latest_execution_comparison_all_registries_present"] is True
    assert fields["bundle_history_latest_execution_overall_status"] == "warn"
    assert fields["bundle_history_latest_execution_comparison_all_registries_present"] is False
    assert fields["cycle_history_latest_execution_venue_count"] == 3


def test_latest_execution_lineage_from_notes_preserves_optional_none_values() -> None:
    fields = latest_execution_lineage_from_notes(
        [
            "execution_overall_status=degraded",
            "execution_venue_count=0",
            "execution_comparison_all_registries_present=False",
            "execution_snapshot_reason=None",
            "execution_snapshot_next_action=connect_snapshot",
        ],
        prefix="latest",
    )

    assert fields["latest_execution_overall_status"] == "degraded"
    assert fields["latest_execution_venue_count"] == "0"
    assert fields["latest_execution_comparison_all_registries_present"] is False
    assert fields["latest_execution_snapshot_reason"] is None
    assert fields["latest_execution_snapshot_next_action"] == "connect_snapshot"


def test_payload_and_remap_helpers_keep_default_shape() -> None:
    payload, fields = latest_execution_payload_and_fields_from_summary(
        {
            "timeline_latest_execution_summary": {"overall_status": "ok", "venue_count": 2},
            "timeline_latest_execution_comparison_summary": {"all_registries_present": True},
        }
    )
    defaulted = defaulted_all_latest_execution_lineage_fields({})
    remapped = first_remapped_latest_execution_lineage_fields(
        (
            {
                "latest_execution_summary": {"overall_status": "warn", "venue_count": 1},
                "latest_execution_comparison_summary": {"all_registries_present": False},
            },
            "audit_latest",
        )
    )

    assert payload["timeline_latest_execution_summary"] == {
        "overall_status": "ok",
        "venue_count": 2,
    }
    assert fields["timeline_latest_execution_overall_status"] == "ok"
    assert defaulted["timeline_latest_execution_summary"] == {}
    assert remapped["audit_latest_execution_overall_status"] == "warn"
    assert remapped["audit_latest_execution_comparison_all_registries_present"] is False


def test_latest_execution_flat_lines_omits_empty_values() -> None:
    assert (
        latest_execution_flat_lines(
            overall_status=None,
            venue_count=None,
            all_registries_present=None,
        )
        == []
    )
    assert latest_execution_flat_lines(
        overall_status="ok",
        venue_count=2,
        all_registries_present=True,
        overall_status_label="status",
    ) == [
        "- status: ok",
        "- venue_count: 2",
        "- all_registries_present: True",
    ]
