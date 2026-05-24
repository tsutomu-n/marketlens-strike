from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import read_json, write_json


def build_execution_venue_comparison_report(
    *,
    execution_snapshot_summary_path: Path,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    payload = read_json(execution_snapshot_summary_path) if execution_snapshot_summary_path.exists() else {}
    if not isinstance(payload, dict):
        payload = {}
    venues = payload.get("venues")
    if not isinstance(venues, list):
        venues = []

    comparison_rows: list[dict[str, object]] = []
    for snapshot in venues:
        if not isinstance(snapshot, dict):
            continue
        balance = snapshot.get("balance")
        if not isinstance(balance, dict):
            balance = {}
        comparison_rows.append(
            {
                "venue": snapshot.get("venue"),
                "registry_exists": snapshot.get("registry_exists"),
                "balance_snapshot_exists": snapshot.get("balance_snapshot_exists"),
                "fills_snapshot_exists": snapshot.get("fills_snapshot_exists"),
                "order_status_snapshot_exists": snapshot.get("order_status_snapshot_exists"),
                "positions_count": snapshot.get("positions_count"),
                "fills_count": snapshot.get("fills_count"),
                "order_status_count": snapshot.get("order_status_count"),
                "balance_equity": balance.get("equity"),
                "balance_currency": balance.get("currency"),
            }
        )

    summary = {
        "overall_status": payload.get("overall_status"),
        "venue_count": len(comparison_rows),
        "venues": comparison_rows,
        "all_registries_present": all(bool(row.get("registry_exists")) for row in comparison_rows) if comparison_rows else False,
        "execution_comparison_all_registries_present": (
            all(bool(row.get("registry_exists")) for row in comparison_rows) if comparison_rows else False
        ),
        "execution_comparison_report_path": str(out_path) if out_path is not None else None,
        "all_balance_snapshots_present": all(bool(row.get("balance_snapshot_exists")) for row in comparison_rows) if comparison_rows else False,
        "all_fill_snapshots_present": all(bool(row.get("fills_snapshot_exists")) for row in comparison_rows) if comparison_rows else False,
        "all_order_status_snapshots_present": all(bool(row.get("order_status_snapshot_exists")) for row in comparison_rows) if comparison_rows else False,
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/current_state_index.json",
            "data/ops/readiness_snapshot.json",
        ],
    }

    lines = [
        "# Execution Venue Comparison",
        "",
        "## Overview",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- venue_count: {summary['venue_count']}",
        f"- all_registries_present: {summary['all_registries_present']}",
        f"- all_balance_snapshots_present: {summary['all_balance_snapshots_present']}",
        f"- all_fill_snapshots_present: {summary['all_fill_snapshots_present']}",
        f"- all_order_status_snapshots_present: {summary['all_order_status_snapshots_present']}",
        "",
        "## Venue Comparison",
        "",
        "| venue | registry_exists | balance_snapshot_exists | fills_snapshot_exists | order_status_snapshot_exists | positions_count | fills_count | order_status_count | balance_equity | balance_currency |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in comparison_rows:
        lines.append(
            "| {venue} | {registry_exists} | {balance_snapshot_exists} | {fills_snapshot_exists} | {order_status_snapshot_exists} | {positions_count} | {fills_count} | {order_status_count} | {balance_equity} | {balance_currency} |".format(
                **row
            )
        )

    lines.extend(["", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
