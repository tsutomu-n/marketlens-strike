from __future__ import annotations

from pathlib import Path

from sis.reports.doc_paths import recommended_read_order
from sis.reports.loaders import safe_read_json_dict
from sis.storage.jsonl_store import write_json


def _quick_navigation(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_venue_diagnostics_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
    }


def _related_reports(out_path: Path | None) -> dict[str, str]:
    if out_path is None:
        return {}
    reports_dir = out_path.parent
    return {
        "execution_venue_diagnostics_report": str(out_path),
        "execution_snapshot_report": str(reports_dir / "execution_snapshot.md"),
        "execution_venue_comparison_report": str(reports_dir / "execution_venue_comparison.md"),
        "execution_gap_history_report": str(reports_dir / "execution_gap_history.md"),
        "execution_state_comparison_report": str(
            reports_dir / "execution_state_comparison_history.md"
        ),
        "execution_snapshot_drift_report": str(reports_dir / "execution_snapshot_drift_history.md"),
        "execution_drift_overview_report": str(reports_dir / "execution_drift_overview.md"),
        "operations_dashboard_report": str(reports_dir / "operations_dashboard.md"),
        "current_state_index_report": str(reports_dir / "current_state_index.md"),
        "readiness_snapshot_report": str(reports_dir / "readiness_snapshot.md"),
    }


def _numeric_values(rows: list[dict[str, object]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int | float):
            values.append(float(value))
    return values


def _int_values(rows: list[dict[str, object]], key: str) -> list[int]:
    values: list[int] = []
    for row in rows:
        value = row.get(key)
        if isinstance(value, int):
            values.append(value)
        elif isinstance(value, float) and value.is_integer():
            values.append(int(value))
    return values


def build_execution_venue_diagnostics_report(
    *,
    execution_venue_comparison_summary_path: Path,
    out_path: Path | None = None,
    summary_path: Path | None = None,
) -> str:
    payload = safe_read_json_dict(execution_venue_comparison_summary_path)
    venues = payload.get("venues")
    if not isinstance(venues, list):
        venues = []
    source_snapshot_empty = payload.get("source_snapshot_empty") is True
    source_snapshot_reason = payload.get("source_snapshot_reason")
    source_snapshot_reason_codes = payload.get("source_snapshot_reason_codes")
    if not isinstance(source_snapshot_reason_codes, list):
        source_snapshot_reason_codes = (
            [source_snapshot_reason] if isinstance(source_snapshot_reason, str) else []
        )
    source_snapshot_root_source = payload.get("source_snapshot_root_source")

    rows = [row for row in venues if isinstance(row, dict)]
    currencies = sorted(
        {
            str(row.get("balance_currency"))
            for row in rows
            if isinstance(row.get("balance_currency"), str) and row.get("balance_currency")
        }
    )
    equity_values = _numeric_values(rows, "balance_equity")
    position_counts = _int_values(rows, "positions_count")
    fills_counts = _int_values(rows, "fills_count")
    order_status_counts = _int_values(rows, "order_status_count")

    registry_gap_detected = (
        any(row.get("registry_exists") is not True for row in rows) if rows else True
    )
    balance_gap_detected = (
        any(row.get("balance_snapshot_exists") is not True for row in rows) if rows else True
    )
    positions_snapshot_gap_detected = (
        any(row.get("positions_snapshot_exists") is not True for row in rows) if rows else True
    )
    fills_gap_detected = (
        any(row.get("fills_snapshot_exists") is not True for row in rows) if rows else True
    )
    order_status_gap_detected = (
        any(row.get("order_status_snapshot_exists") is not True for row in rows) if rows else True
    )
    currency_mismatch_detected = len(currencies) > 1
    quick_navigation = _quick_navigation(out_path)
    related_reports = _related_reports(out_path)
    recommended_read_order_items = recommended_read_order(
        [
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/current_state_index.json",
            "data/ops/readiness_snapshot.json",
        ]
    )

    summary = {
        "overall_status": (
            "ok"
            if rows
            and not registry_gap_detected
            and not balance_gap_detected
            and not positions_snapshot_gap_detected
            and not fills_gap_detected
            and not order_status_gap_detected
            and not currency_mismatch_detected
            else "degraded"
        ),
        "venue_count": len(rows),
        "diagnostics_reason": "source_execution_snapshot_empty" if source_snapshot_empty else None,
        "diagnostics_root_source": source_snapshot_root_source if source_snapshot_empty else None,
        "source_snapshot_empty": source_snapshot_empty,
        "source_snapshot_reason": source_snapshot_reason,
        "source_snapshot_reason_codes": source_snapshot_reason_codes,
        "source_snapshot_root_source": source_snapshot_root_source,
        "registry_gap_detected": registry_gap_detected,
        "balance_gap_detected": balance_gap_detected,
        "positions_snapshot_gap_detected": positions_snapshot_gap_detected,
        "fills_gap_detected": fills_gap_detected,
        "execution_diagnostics_status": (
            "ok"
            if rows
            and not registry_gap_detected
            and not balance_gap_detected
            and not positions_snapshot_gap_detected
            and not fills_gap_detected
            and not order_status_gap_detected
            and not currency_mismatch_detected
            else "degraded"
        ),
        "execution_balance_gap_detected": balance_gap_detected,
        "execution_positions_snapshot_gap_detected": positions_snapshot_gap_detected,
        "execution_fills_gap_detected": fills_gap_detected,
        "execution_diagnostics_report_path": str(out_path) if out_path is not None else None,
        "order_status_gap_detected": order_status_gap_detected,
        "currency_mismatch_detected": currency_mismatch_detected,
        "shared_balance_currency": currencies[0] if len(currencies) == 1 else None,
        "equity_span": (
            max(equity_values) - min(equity_values) if len(equity_values) >= 2 else None
        ),
        "positions_count_span": (
            max(position_counts) - min(position_counts) if len(position_counts) >= 2 else None
        ),
        "fills_count_span": (
            max(fills_counts) - min(fills_counts) if len(fills_counts) >= 2 else None
        ),
        "order_status_count_span": (
            max(order_status_counts) - min(order_status_counts)
            if len(order_status_counts) >= 2
            else None
        ),
        "artifacts": {
            "execution_venue_comparison_summary": str(execution_venue_comparison_summary_path),
        },
        "recommended_read_order": recommended_read_order_items,
        "quick_navigation": quick_navigation,
        "related_reports": related_reports,
    }

    lines = ["# Execution Venue Diagnostics", ""]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    if related_reports:
        lines.extend(["## Related Reports", ""])
        lines.extend(f"- {key}: {value}" for key, value in related_reports.items())
        lines.append("")
    lines.extend(
        [
            "## Overview",
            "",
            f"- overall_status: {summary['overall_status']}",
            f"- venue_count: {summary['venue_count']}",
            f"- diagnostics_reason: {summary['diagnostics_reason']}",
            f"- diagnostics_root_source: {summary['diagnostics_root_source']}",
            f"- registry_gap_detected: {summary['registry_gap_detected']}",
            f"- balance_gap_detected: {summary['balance_gap_detected']}",
            f"- positions_snapshot_gap_detected: {summary['positions_snapshot_gap_detected']}",
            f"- fills_gap_detected: {summary['fills_gap_detected']}",
            f"- order_status_gap_detected: {summary['order_status_gap_detected']}",
            f"- currency_mismatch_detected: {summary['currency_mismatch_detected']}",
            f"- shared_balance_currency: {summary['shared_balance_currency']}",
            f"- equity_span: {summary['equity_span']}",
            f"- positions_count_span: {summary['positions_count_span']}",
            f"- fills_count_span: {summary['fills_count_span']}",
            f"- order_status_count_span: {summary['order_status_count_span']}",
            "",
            "## Recommended Read Order",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in recommended_read_order_items)
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
