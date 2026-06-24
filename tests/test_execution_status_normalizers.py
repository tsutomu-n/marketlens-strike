from __future__ import annotations

from sis.reports import summary_normalizers
from sis.reports.execution_status_normalizers import (
    execution_diagnostics_flat_fields,
    execution_drift_overview_flat_fields,
    execution_gap_history_flat_fields,
    execution_snapshot_drift_flat_fields,
    execution_state_comparison_flat_fields,
    normalize_execution_diagnostics_summary,
    normalize_execution_drift_overview_summary,
    normalize_execution_gap_history_summary,
    normalize_execution_snapshot_drift_summary,
    normalize_execution_state_comparison_summary,
)


def test_execution_diagnostics_normalizer_preserves_prefixed_aliases() -> None:
    normalized = normalize_execution_diagnostics_summary(
        {
            "execution_diagnostics_status": "degraded",
            "execution_balance_gap_detected": True,
            "execution_positions_snapshot_gap_detected": False,
            "execution_fills_gap_detected": True,
            "execution_diagnostics_reason": "missing_fills",
            "execution_diagnostics_root_source": "ops",
            "execution_diagnostics_report_path": "data/reports/diagnostics.md",
        }
    )

    assert normalized["overall_status"] == "degraded"
    assert normalized["balance_gap_detected"] is True
    assert normalized["positions_snapshot_gap_detected"] is False
    assert normalized["fills_gap_detected"] is True
    assert normalized["report_path"] == "data/reports/diagnostics.md"
    assert execution_diagnostics_flat_fields(normalized) == {
        "execution_diagnostics_status": "degraded",
        "execution_diagnostics_reason": "missing_fills",
        "execution_diagnostics_root_source": "ops",
        "execution_balance_gap_detected": True,
        "execution_positions_snapshot_gap_detected": False,
        "execution_fills_gap_detected": True,
        "execution_diagnostics_report_path": "data/reports/diagnostics.md",
    }


def test_execution_history_normalizers_accept_prefixed_fields() -> None:
    gap = normalize_execution_gap_history_summary(
        {
            "execution_gap_history_entry_count": 4,
            "execution_gap_history_latest_status": "ok",
            "execution_gap_history_latest_diagnostics_status": "ok",
            "execution_gap_history_report_path": "data/reports/gap.md",
        }
    )
    state = normalize_execution_state_comparison_summary(
        {
            "execution_state_comparison_entry_count": 3,
            "execution_state_comparison_latest_status": "ok",
            "execution_state_comparison_latest_diagnostics_status": "degraded",
            "execution_state_comparison_latest_status_match": False,
            "execution_state_comparison_mismatching_count": 2,
            "execution_state_comparison_report_path": "data/reports/state.md",
        }
    )

    assert execution_gap_history_flat_fields(gap) == {
        "execution_gap_history_entry_count": 4,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "ok",
        "execution_gap_history_report_path": "data/reports/gap.md",
    }
    assert execution_state_comparison_flat_fields(state) == {
        "execution_state_comparison_entry_count": 3,
        "execution_state_comparison_latest_status": "ok",
        "execution_state_comparison_latest_diagnostics_status": "degraded",
        "execution_state_comparison_latest_status_match": False,
        "execution_state_comparison_mismatching_count": 2,
        "execution_state_comparison_report_path": "data/reports/state.md",
    }


def test_execution_snapshot_drift_prefers_state_comparison_aliases() -> None:
    normalized = normalize_execution_snapshot_drift_summary(
        {
            "execution_snapshot_drift_entry_count": 5,
            "execution_snapshot_drift_latest_status": "degraded",
            "execution_snapshot_drift_latest_diagnostics_status": "ok",
            "latest_execution_state_comparison_status_match": True,
            "execution_snapshot_drift_latest_status_match": False,
            "latest_execution_state_comparison_mismatching_count": 1,
            "execution_snapshot_drift_latest_mismatching_count": 7,
            "execution_snapshot_drift_mismatching_snapshot_count": 2,
            "execution_snapshot_drift_report_path": "data/reports/snapshot_drift.md",
        }
    )

    assert normalized["latest_status_match"] is True
    assert normalized["latest_mismatching_count"] == 1
    assert execution_snapshot_drift_flat_fields(normalized) == {
        "execution_snapshot_drift_entry_count": 5,
        "execution_snapshot_drift_latest_status": "degraded",
        "execution_snapshot_drift_latest_diagnostics_status": "ok",
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_latest_mismatching_count": 1,
        "execution_snapshot_drift_mismatching_snapshot_count": 2,
        "execution_snapshot_drift_report_path": "data/reports/snapshot_drift.md",
    }


def test_execution_drift_overview_defaults_reason_codes_to_list() -> None:
    normalized = normalize_execution_drift_overview_summary(
        {
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_reason_codes": "bad-shape",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 3,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 4,
            "report_path": "data/reports/drift.md",
        }
    )

    assert normalized["reason_codes"] == []
    assert execution_drift_overview_flat_fields(normalized) == {
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_reason_codes": [],
        "execution_drift_overview_lineage": None,
        "execution_drift_overview_diagnostics_alignment_match": False,
        "execution_drift_overview_state_comparison_mismatching_count": 3,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 4,
        "execution_drift_overview_report_path": "data/reports/drift.md",
    }


def test_summary_normalizers_reexports_execution_status_helpers() -> None:
    payload = {"execution_gap_history_entry_count": 2}

    assert summary_normalizers.normalize_execution_gap_history_summary(
        payload
    ) == normalize_execution_gap_history_summary(payload)
    assert summary_normalizers.execution_gap_history_flat_fields(
        payload
    ) == execution_gap_history_flat_fields(payload)
