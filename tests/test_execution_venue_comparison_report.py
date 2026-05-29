from __future__ import annotations

from sis.reports.execution_venue_comparison import build_execution_venue_comparison_report
from sis.storage.jsonl_store import read_json, write_json


def test_build_execution_venue_comparison_report(tmp_path) -> None:
    execution_snapshot = tmp_path / "execution_snapshot_summary.json"
    write_json(
        execution_snapshot,
        {
            "overall_status": "ok",
            "venue_count": 2,
            "venues": [
                {
                    "venue": "gtrade",
                    "registry_exists": True,
                    "balance_snapshot_exists": True,
                    "fills_snapshot_exists": True,
                    "order_status_snapshot_exists": True,
                    "positions_count": 0,
                    "fills_count": 1,
                    "order_status_count": 1,
                    "balance": {"equity": 1000, "currency": "USD"},
                },
                {
                    "venue": "ostium",
                    "registry_exists": True,
                    "balance_snapshot_exists": False,
                    "fills_snapshot_exists": False,
                    "order_status_snapshot_exists": True,
                    "positions_count": 1,
                    "fills_count": 0,
                    "order_status_count": 1,
                    "balance": {"equity": None, "currency": "USD"},
                },
            ],
        },
    )

    report = build_execution_venue_comparison_report(
        execution_snapshot_summary_path=execution_snapshot,
        out_path=tmp_path / "execution_venue_comparison.md",
        summary_path=tmp_path / "execution_venue_comparison_summary.json",
    )

    assert "Execution Venue Comparison" in report
    assert "all_registries_present: True" in report
    assert "gtrade" in report
    assert "ostium" in report
    summary = read_json(tmp_path / "execution_venue_comparison_summary.json")
    assert isinstance(summary, dict)
    assert summary["venue_count"] == 2
    assert summary["all_registries_present"] is True
    assert summary["execution_comparison_all_registries_present"] is True
    assert summary["execution_comparison_report_path"] == str(
        tmp_path / "execution_venue_comparison.md"
    )
    assert summary["all_balance_snapshots_present"] is False


def test_build_execution_venue_comparison_report_carries_empty_snapshot_reason(
    tmp_path,
) -> None:
    execution_snapshot = tmp_path / "execution_snapshot_summary.json"
    write_json(
        execution_snapshot,
        {
            "overall_status": "degraded",
            "venue_count": 0,
            "venues": [],
            "execution_snapshot_reason": "trade_xyz_live_execution_snapshot_not_connected",
            "execution_snapshot_reason_codes": ["trade_xyz_live_execution_snapshot_not_connected"],
            "execution_snapshot_root_source": "execution_snapshot_summary.venues=[]",
        },
    )

    report = build_execution_venue_comparison_report(
        execution_snapshot_summary_path=execution_snapshot,
        out_path=tmp_path / "execution_venue_comparison.md",
        summary_path=tmp_path / "execution_venue_comparison_summary.json",
    )

    assert "source_snapshot_empty: True" in report
    assert "source_snapshot_reason: trade_xyz_live_execution_snapshot_not_connected" in report
    summary = read_json(tmp_path / "execution_venue_comparison_summary.json")
    assert isinstance(summary, dict)
    assert summary["venue_count"] == 0
    assert summary["source_snapshot_empty"] is True
    assert summary["source_snapshot_reason"] == "trade_xyz_live_execution_snapshot_not_connected"
    assert summary["source_snapshot_reason_codes"] == [
        "trade_xyz_live_execution_snapshot_not_connected"
    ]
    assert summary["source_snapshot_root_source"] == "execution_snapshot_summary.venues=[]"
    assert summary["execution_comparison_reason"] == "source_execution_snapshot_empty"
    assert summary["execution_comparison_root_source"] == "execution_snapshot_summary.venues=[]"
