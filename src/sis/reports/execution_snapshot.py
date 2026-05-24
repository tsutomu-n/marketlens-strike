from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import write_json


def build_execution_snapshot_report(
    *,
    venue_snapshots: list[dict],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    overall_status = "ok" if venue_snapshots else "degraded"
    if venue_snapshots and not any(snapshot.get("registry_exists") for snapshot in venue_snapshots):
        overall_status = "degraded"

    summary = {
        "overall_status": overall_status,
        "venue_count": len(venue_snapshots),
        "execution_overall_status": overall_status,
        "execution_venue_count": len(venue_snapshots),
        "execution_report_path": str(out_path) if out_path is not None else None,
        "venues": venue_snapshots,
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/current_state_index.json",
            "data/ops/operations_dashboard_summary.json",
            "data/ops/phase_gate_review_summary.json",
        ],
    }

    lines = [
        "# Execution Snapshot",
        "",
        "## Overview",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- venue_count: {summary['venue_count']}",
        "",
    ]

    for snapshot in venue_snapshots:
        venue = snapshot.get("venue")
        balance = snapshot.get("balance", {})
        latest_order = snapshot.get("latest_order_status") or {}
        latest_fill = snapshot.get("latest_fill") or {}
        lines.extend(
            [
                f"## Venue: {venue}",
                "",
                f"- registry_exists: {snapshot.get('registry_exists')}",
                f"- balance_snapshot_exists: {snapshot.get('balance_snapshot_exists')}",
                f"- fills_snapshot_exists: {snapshot.get('fills_snapshot_exists')}",
                f"- order_status_snapshot_exists: {snapshot.get('order_status_snapshot_exists')}",
                f"- positions_count: {snapshot.get('positions_count')}",
                f"- fills_count: {snapshot.get('fills_count')}",
                f"- order_status_count: {snapshot.get('order_status_count')}",
                f"- balance_currency: {balance.get('currency')}",
                f"- balance_equity: {balance.get('equity')}",
                f"- latest_order_id: {latest_order.get('order_id')}",
                f"- latest_order_status: {latest_order.get('status')}",
                f"- latest_fill_id: {latest_fill.get('fill_id')}",
                f"- latest_fill_status: {latest_fill.get('status')}",
                "",
            ]
        )

    lines.extend(["## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
