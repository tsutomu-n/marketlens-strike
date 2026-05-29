from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order
from sis.storage.jsonl_store import write_json

EMPTY_SNAPSHOT_REASON = "trade_xyz_live_execution_snapshot_not_connected"
EMPTY_SNAPSHOT_ROOT_SOURCE = "execution_snapshot_summary.venues=[]"
EMPTY_SNAPSHOT_NEXT_ACTION = "decide_read_only_execution_state_collector_scope"
UNAVAILABLE_SNAPSHOT_REASON = "read_only_execution_state_collector_not_implemented"
UNAVAILABLE_SNAPSHOT_ROOT_SOURCE = "execution_read_only_surfaces_summary.venues[].collector_status"


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_report": str(out_path),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_report": str(out_path),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
    }


def build_execution_snapshot_report(
    *,
    venue_snapshots: list[dict],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    required_flags = (
        "registry_exists",
        "balance_snapshot_exists",
        "positions_snapshot_exists",
        "fills_snapshot_exists",
        "order_status_snapshot_exists",
    )
    overall_status = (
        "ok"
        if venue_snapshots
        and all(
            all(snapshot.get(flag) is True for flag in required_flags)
            for snapshot in venue_snapshots
        )
        else "degraded"
    )
    if venue_snapshots and not any(snapshot.get("registry_exists") for snapshot in venue_snapshots):
        overall_status = "degraded"
    empty_snapshot = len(venue_snapshots) == 0
    unavailable_reason = next(
        (
            snapshot.get("collector_reason")
            for snapshot in venue_snapshots
            if snapshot.get("collector_status") in {"not_connected", "unavailable"}
            and isinstance(snapshot.get("collector_reason"), str)
        ),
        None,
    )
    snapshot_reason = (
        EMPTY_SNAPSHOT_REASON
        if empty_snapshot
        else unavailable_reason
        or (UNAVAILABLE_SNAPSHOT_REASON if overall_status == "degraded" else None)
    )
    reason_codes = [snapshot_reason] if isinstance(snapshot_reason, str) else []
    root_source = (
        EMPTY_SNAPSHOT_ROOT_SOURCE
        if empty_snapshot
        else UNAVAILABLE_SNAPSHOT_ROOT_SOURCE
        if snapshot_reason
        else None
    )

    summary = {
        "overall_status": overall_status,
        "venue_count": len(venue_snapshots),
        "execution_overall_status": overall_status,
        "execution_venue_count": len(venue_snapshots),
        "snapshot_reason": snapshot_reason,
        "execution_snapshot_reason": snapshot_reason,
        "execution_snapshot_reason_codes": reason_codes,
        "execution_snapshot_root_source": root_source,
        "execution_snapshot_next_action": EMPTY_SNAPSHOT_NEXT_ACTION if snapshot_reason else None,
        "execution_snapshot_empty": empty_snapshot,
        "execution_report_path": str(out_path) if out_path is not None else None,
        "venues": venue_snapshots,
        "recommended_read_order": recommended_read_order(
            [
                "data/ops/execution_snapshot_summary.json",
                "data/ops/current_state_index.json",
                "data/ops/operations_dashboard_summary.json",
                "data/ops/phase_gate_review_summary.json",
            ]
        ),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }

    lines = ["# Execution Snapshot", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(
        [
            "## Overview",
            "",
            f"- overall_status: {summary['overall_status']}",
            f"- venue_count: {summary['venue_count']}",
            f"- snapshot_reason: {summary['snapshot_reason']}",
            f"- execution_snapshot_root_source: {summary['execution_snapshot_root_source']}",
            f"- execution_snapshot_next_action: {summary['execution_snapshot_next_action']}",
            "",
        ]
    )

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
                f"- positions_snapshot_exists: {snapshot.get('positions_snapshot_exists')}",
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
