from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from sis.execution.base import AdapterActionResult, AdapterFillSnapshot, AdapterOrderStatus
from sis.state.reconciliation import ReconciliationResult
from sis.storage.jsonl_store import write_json


def _recommended_read_order() -> list[str]:
    return [
        "docs/ACCEPTANCE_AUDIT.md",
        "docs/IMPLEMENTATION_STATUS.md",
        "data/reports/execution_snapshot.md",
        "data/ops/current_state_index.json",
        "data/ops/readiness_snapshot.json",
        "data/ops/phase_gate_review_summary.json",
    ]


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_adapter_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_venue_diagnostics_report": str(reports_dir / "execution_venue_diagnostics.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "phase_gate_review_report": str(reports_dir / "phase_gate_review.md"),
        "paper_operations_runbook_report": str(reports_dir / "paper_operations_runbook.md"),
        "remediation_scoreboard_report": str(reports_dir / "remediation_scoreboard.md"),
    }


def _write_report(
    *,
    title: str,
    summary: dict[str, object],
    detail_lines: list[str],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    lines = [f"# {title}", ""]
    if summary["quick_navigation"]:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["quick_navigation"].items())
        lines.append("")
    if summary["related_reports"]:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in summary["related_reports"].items())
        lines.append("")
    lines.extend(["## Overview", "", *detail_lines, "", "## Recommended Read Order", ""])
    lines.extend(f"- {item}" for item in _recommended_read_order())
    lines.append("")
    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text


def build_balance_status_report(
    *,
    venue: str,
    balance: dict[str, object],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": venue,
        "balance": balance,
        "mode": balance.get("mode"),
        "currency": balance.get("currency"),
        "equity": balance.get("equity"),
        "available_cash": balance.get("available_cash"),
        "balance_snapshot_exists": balance.get("balance_snapshot_exists"),
        "balance_status_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Execution Balance Status",
        summary=summary,
        detail_lines=[
            f"- venue: {summary['venue']}",
            f"- mode: {summary['mode']}",
            f"- currency: {summary['currency']}",
            f"- equity: {summary['equity']}",
            f"- available_cash: {summary['available_cash']}",
            f"- balance_snapshot_exists: {summary['balance_snapshot_exists']}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_fill_status_report(
    *,
    venue: str,
    fills: list[AdapterFillSnapshot],
    limit: int,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    rows = [asdict(fill) for fill in fills]
    summary = {
        "venue": venue,
        "fills_count": len(rows),
        "limit": limit,
        "fills": rows,
        "latest_fill_id": rows[0]["fill_id"] if rows else None,
        "latest_fill_status": rows[0]["status"] if rows else None,
        "fill_status_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    detail_lines = [
        f"- venue: {summary['venue']}",
        f"- fills_count: {summary['fills_count']}",
        f"- limit: {summary['limit']}",
        f"- latest_fill_id: {summary['latest_fill_id']}",
        f"- latest_fill_status: {summary['latest_fill_status']}",
    ]
    for index, row in enumerate(rows, start=1):
        detail_lines.extend(
            [
                f"- fill_{index}_id: {row['fill_id']}",
                f"- fill_{index}_order_id: {row['order_id']}",
                f"- fill_{index}_symbol: {row['canonical_symbol']}",
                f"- fill_{index}_side: {row['side']}",
                f"- fill_{index}_quantity: {row['quantity']}",
                f"- fill_{index}_price: {row['price']}",
                f"- fill_{index}_status: {row['status']}",
                f"- fill_{index}_ts_fill: {row['ts_fill']}",
            ]
        )
    return _write_report(
        title="Execution Fill Status",
        summary=summary,
        detail_lines=detail_lines,
        out_path=out_path,
        summary_path=summary_path,
    )


def build_order_status_report(
    *,
    status: AdapterOrderStatus,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": status.venue,
        "order_id": status.order_id,
        "symbol": status.canonical_symbol,
        "side": status.side,
        "quantity": status.quantity,
        "status": status.status,
        "notes": status.notes,
        "order_status_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title="Execution Order Status",
        summary=summary,
        detail_lines=[
            f"- venue: {summary['venue']}",
            f"- order_id: {summary['order_id']}",
            f"- status: {summary['status']}",
            f"- symbol: {summary['symbol']}",
            f"- side: {summary['side']}",
            f"- quantity: {summary['quantity']}",
            f"- notes: {','.join(status.notes)}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_action_status_report(
    *,
    title: str,
    report_key: str,
    result: AdapterActionResult,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": result.venue,
        "action": result.action,
        "target": result.target,
        "success": result.success,
        "status": result.status,
        "notes": result.notes,
        report_key: str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    return _write_report(
        title=title,
        summary=summary,
        detail_lines=[
            f"- venue: {summary['venue']}",
            f"- action: {summary['action']}",
            f"- target: {summary['target']}",
            f"- success: {summary['success']}",
            f"- status: {summary['status']}",
            f"- notes: {','.join(result.notes)}",
        ],
        out_path=out_path,
        summary_path=summary_path,
    )


def build_reconcile_positions_report(
    *,
    venue: str,
    result: ReconciliationResult,
    run_id: str,
    state_store_path: str,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    summary = {
        "venue": venue,
        "run_id": run_id,
        "matched": result.matched,
        "missing_in_adapter": result.missing_in_adapter,
        "missing_in_internal": result.missing_in_internal,
        "missing_in_adapter_count": len(result.missing_in_adapter),
        "missing_in_internal_count": len(result.missing_in_internal),
        "state_store_path": state_store_path,
        "reconcile_positions_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    detail_lines = [
        f"- venue: {summary['venue']}",
        f"- run_id: {summary['run_id']}",
        f"- matched: {summary['matched']}",
        f"- missing_in_adapter_count: {summary['missing_in_adapter_count']}",
        f"- missing_in_internal_count: {summary['missing_in_internal_count']}",
        f"- state_store_path: {summary['state_store_path']}",
    ]
    for index, item in enumerate(result.missing_in_adapter, start=1):
        detail_lines.append(f"- missing_in_adapter_{index}: {item}")
    for index, item in enumerate(result.missing_in_internal, start=1):
        detail_lines.append(f"- missing_in_internal_{index}: {item}")
    return _write_report(
        title="Execution Position Reconciliation",
        summary=summary,
        detail_lines=detail_lines,
        out_path=out_path,
        summary_path=summary_path,
    )


def build_execution_read_only_surfaces_report(
    *,
    venue_surfaces: list[dict[str, object]],
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    venues = [dict(item) for item in venue_surfaces]
    venue_count = len(venues)
    with_balance_snapshot_count = sum(bool(item.get("balance_snapshot_exists")) for item in venues)
    with_positions_snapshot_count = sum(bool(item.get("positions_snapshot_exists")) for item in venues)
    with_fills_snapshot_count = sum(bool(item.get("fills_snapshot_exists")) for item in venues)
    with_order_status_snapshot_count = sum(bool(item.get("order_status_snapshot_exists")) for item in venues)
    reconciled_venue_count = sum(item.get("reconcile_matched") is not None for item in venues)
    summary = {
        "venue_count": venue_count,
        "venues": venues,
        "with_balance_snapshot_count": with_balance_snapshot_count,
        "with_positions_snapshot_count": with_positions_snapshot_count,
        "with_fills_snapshot_count": with_fills_snapshot_count,
        "with_order_status_snapshot_count": with_order_status_snapshot_count,
        "reconciled_venue_count": reconciled_venue_count,
        "execution_read_only_surfaces_report_path": str(out_path) if out_path is not None else None,
        "recommended_read_order": _recommended_read_order(),
        "quick_navigation": _quick_navigation(out_path),
        "related_reports": _related_reports(out_path),
    }
    detail_lines = [
        f"- venue_count: {venue_count}",
        f"- with_balance_snapshot_count: {with_balance_snapshot_count}",
        f"- with_positions_snapshot_count: {with_positions_snapshot_count}",
        f"- with_fills_snapshot_count: {with_fills_snapshot_count}",
        f"- with_order_status_snapshot_count: {with_order_status_snapshot_count}",
        f"- reconciled_venue_count: {reconciled_venue_count}",
    ]
    for item in venues:
        venue = item.get("venue")
        detail_lines.extend(
            [
                f"- venue_{venue}_balance_snapshot_exists: {item.get('balance_snapshot_exists')}",
                f"- venue_{venue}_positions_snapshot_exists: {item.get('positions_snapshot_exists')}",
                f"- venue_{venue}_fills_snapshot_exists: {item.get('fills_snapshot_exists')}",
                f"- venue_{venue}_order_status_snapshot_exists: {item.get('order_status_snapshot_exists')}",
                f"- venue_{venue}_equity: {item.get('equity')}",
                f"- venue_{venue}_fills_count: {item.get('fills_count')}",
                f"- venue_{venue}_latest_fill_id: {item.get('latest_fill_id')}",
                f"- venue_{venue}_order_status_count: {item.get('order_status_count')}",
                f"- venue_{venue}_latest_order_id: {item.get('latest_order_id')}",
                f"- venue_{venue}_latest_order_status: {item.get('latest_order_status')}",
                f"- venue_{venue}_positions_count: {item.get('positions_count')}",
                f"- venue_{venue}_reconcile_matched: {item.get('reconcile_matched')}",
                (
                    f"- venue_{venue}_reconcile_missing_in_adapter_count: "
                    f"{item.get('reconcile_missing_in_adapter_count')}"
                ),
                (
                    f"- venue_{venue}_reconcile_missing_in_internal_count: "
                    f"{item.get('reconcile_missing_in_internal_count')}"
                ),
            ]
        )
    return _write_report(
        title="Execution Read Only Surfaces",
        summary=summary,
        detail_lines=detail_lines,
        out_path=out_path,
        summary_path=summary_path,
    )
