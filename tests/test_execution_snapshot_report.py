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
                "positions_snapshot_exists": True,
                "fills_snapshot_exists": True,
                "order_status_snapshot_exists": True,
                "positions_count": 0,
                "fills_count": 1,
                "order_status_count": 1,
                "balance": {"currency": "USD", "equity": 1200.0},
                "latest_fill_id": "fill-1",
                "latest_fill_status": "filled",
                "latest_fill": {"hash": "fill-1", "status": "filled"},
                "latest_order_status": {"order_id": "ord-1", "status": "working"},
            }
        ],
        out_path=tmp_path / "execution_snapshot.md",
        summary_path=tmp_path / "execution_snapshot_summary.json",
    )

    assert "Execution Snapshot" in report
    assert "## Venue: gtrade" in report
    assert "positions_snapshot_exists: True" in report
    assert "balance_equity: 1200.0" in report
    assert "latest_fill_id: fill-1" in report
    summary = read_json(tmp_path / "execution_snapshot_summary.json")
    assert isinstance(summary, dict)
    assert summary["overall_status"] == "ok"
    assert summary["execution_overall_status"] == "ok"
    assert summary["execution_venue_count"] == 1
    assert summary["execution_report_path"] == str(tmp_path / "execution_snapshot.md")
    assert summary["recommended_read_order"][0] == "docs/CURRENT_STATE.md"


def test_build_execution_snapshot_report_marks_empty_trade_xyz_snapshot_reason(tmp_path) -> None:
    report = build_execution_snapshot_report(
        venue_snapshots=[],
        out_path=tmp_path / "execution_snapshot.md",
        summary_path=tmp_path / "execution_snapshot_summary.json",
    )

    assert "snapshot_reason: trade_xyz_live_execution_snapshot_not_connected" in report
    summary = read_json(tmp_path / "execution_snapshot_summary.json")
    assert isinstance(summary, dict)
    assert summary["overall_status"] == "degraded"
    assert summary["venue_count"] == 0
    assert summary["execution_snapshot_empty"] is True
    assert summary["execution_snapshot_reason"] == "trade_xyz_live_execution_snapshot_not_connected"
    assert summary["execution_snapshot_reason_codes"] == [
        "trade_xyz_live_execution_snapshot_not_connected"
    ]
    assert summary["execution_snapshot_root_source"] == "execution_snapshot_summary.venues=[]"
    assert (
        summary["execution_snapshot_next_action"]
        == "decide_read_only_execution_state_collector_scope"
    )


def test_build_execution_snapshot_report_marks_unavailable_read_only_collector(
    tmp_path,
) -> None:
    report = build_execution_snapshot_report(
        venue_snapshots=[
            {
                "venue": "trade_xyz",
                "registry_exists": True,
                "balance_snapshot_exists": False,
                "positions_snapshot_exists": False,
                "fills_snapshot_exists": False,
                "order_status_snapshot_exists": False,
                "collector_status": "not_connected",
                "collector_reason": "read_only_execution_state_collector_not_implemented",
                "next_action": "connect_trade_xyz_read_only_execution_state_collector",
            }
        ],
        out_path=tmp_path / "execution_snapshot.md",
        summary_path=tmp_path / "execution_snapshot_summary.json",
    )

    assert "snapshot_reason: read_only_execution_state_collector_not_implemented" in report
    assert "## Venue: trade_xyz" in report
    summary = read_json(tmp_path / "execution_snapshot_summary.json")
    assert isinstance(summary, dict)
    assert summary["overall_status"] == "degraded"
    assert summary["venue_count"] == 1
    assert summary["execution_snapshot_empty"] is False
    assert summary["execution_snapshot_reason"] == (
        "read_only_execution_state_collector_not_implemented"
    )
    assert summary["execution_snapshot_root_source"] == (
        "execution_read_only_surfaces_summary.venues[].collector_status"
    )
    assert (
        summary["execution_snapshot_next_action"]
        == "connect_trade_xyz_read_only_execution_state_collector"
    )


def test_build_execution_snapshot_report_accepts_scalar_latest_order_status(tmp_path) -> None:
    report = build_execution_snapshot_report(
        venue_snapshots=[
            {
                "venue": "trade_xyz",
                "registry_exists": True,
                "balance_snapshot_exists": True,
                "positions_snapshot_exists": True,
                "fills_snapshot_exists": True,
                "order_status_snapshot_exists": True,
                "positions_count": 1,
                "fills_count": 1,
                "order_status_count": 1,
                "balance": {"currency": "USD", "equity": 1200.5},
                "latest_order_id": "42",
                "latest_order_status": "open",
                "latest_order_status_snapshot": {"oid": 42, "status": "open"},
                "latest_fill": {"fill_id": "fill-1", "status": "filled"},
            }
        ],
        out_path=tmp_path / "execution_snapshot.md",
        summary_path=tmp_path / "execution_snapshot_summary.json",
    )

    assert "latest_order_id: 42" in report
    assert "latest_order_status: open" in report
    assert "latest_fill_id: fill-1" in report
    assert "latest_fill_status: filled" in report
    summary = read_json(tmp_path / "execution_snapshot_summary.json")
    assert isinstance(summary, dict)
    assert summary["overall_status"] == "ok"
