from __future__ import annotations

from sis.reports.execution_venue_diagnostics import build_execution_venue_diagnostics_report
from sis.storage.jsonl_store import read_json, write_json


def test_build_execution_venue_diagnostics_report(tmp_path) -> None:
    comparison_summary = tmp_path / "execution_venue_comparison_summary.json"
    write_json(
        comparison_summary,
        {
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
                    "balance_equity": 1000.0,
                    "balance_currency": "USD",
                },
                {
                    "venue": "ostium",
                    "registry_exists": True,
                    "balance_snapshot_exists": False,
                    "fills_snapshot_exists": False,
                    "order_status_snapshot_exists": True,
                    "positions_count": 2,
                    "fills_count": 0,
                    "order_status_count": 2,
                    "balance_equity": 995.0,
                    "balance_currency": "USD",
                },
            ]
        },
    )

    report = build_execution_venue_diagnostics_report(
        execution_venue_comparison_summary_path=comparison_summary,
        out_path=tmp_path / "execution_venue_diagnostics.md",
        summary_path=tmp_path / "execution_venue_diagnostics_summary.json",
    )

    assert "Execution Venue Diagnostics" in report
    assert "balance_gap_detected: True" in report
    assert "fills_gap_detected: True" in report
    assert "equity_span: 5.0" in report
    summary = read_json(tmp_path / "execution_venue_diagnostics_summary.json")
    assert isinstance(summary, dict)
    assert summary["overall_status"] == "degraded"
    assert summary["execution_diagnostics_status"] == "degraded"
    assert summary["execution_balance_gap_detected"] is True
    assert summary["execution_fills_gap_detected"] is True
    assert summary["execution_diagnostics_report_path"] == str(
        tmp_path / "execution_venue_diagnostics.md"
    )
    assert summary["positions_count_span"] == 2
    assert summary["shared_balance_currency"] == "USD"
