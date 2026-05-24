from __future__ import annotations

from sis.reports.execution_snapshot import build_execution_snapshot_report
from sis.storage.jsonl_store import read_json


def test_build_execution_snapshot_report(tmp_path) -> None:
    report = build_execution_snapshot_report(
        venue_snapshots=[
            {
                "venue": "gtrade",
                "registry_exists": True,
                "balance_snapshot_exists": True,
                "fills_snapshot_exists": True,
                "order_status_snapshot_exists": True,
                "positions_count": 0,
                "fills_count": 1,
                "order_status_count": 1,
                "balance": {"currency": "USD", "equity": 1200.0},
                "latest_fill": {"fill_id": "fill-1", "status": "filled"},
                "latest_order_status": {"order_id": "ord-1", "status": "working"},
            }
        ],
        out_path=tmp_path / "execution_snapshot.md",
        summary_path=tmp_path / "execution_snapshot_summary.json",
    )

    assert "Execution Snapshot" in report
    assert "## Venue: gtrade" in report
    assert "balance_equity: 1200.0" in report
    assert "latest_fill_id: fill-1" in report
    summary = read_json(tmp_path / "execution_snapshot_summary.json")
    assert isinstance(summary, dict)
    assert summary["overall_status"] == "ok"
    assert summary["execution_overall_status"] == "ok"
    assert summary["execution_venue_count"] == 1
    assert summary["execution_report_path"] == str(tmp_path / "execution_snapshot.md")
    assert summary["recommended_read_order"][0] == "docs/ACCEPTANCE_AUDIT.md"
