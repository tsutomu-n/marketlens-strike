from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import read_json, write_json


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
    payload = (
        read_json(execution_venue_comparison_summary_path)
        if execution_venue_comparison_summary_path.exists()
        else {}
    )
    if not isinstance(payload, dict):
        payload = {}
    venues = payload.get("venues")
    if not isinstance(venues, list):
        venues = []

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

    registry_gap_detected = any(row.get("registry_exists") is not True for row in rows) if rows else True
    balance_gap_detected = any(row.get("balance_snapshot_exists") is not True for row in rows) if rows else True
    fills_gap_detected = any(row.get("fills_snapshot_exists") is not True for row in rows) if rows else True
    order_status_gap_detected = (
        any(row.get("order_status_snapshot_exists") is not True for row in rows) if rows else True
    )
    currency_mismatch_detected = len(currencies) > 1

    summary = {
        "overall_status": (
            "ok"
            if rows
            and not registry_gap_detected
            and not balance_gap_detected
            and not fills_gap_detected
            and not order_status_gap_detected
            and not currency_mismatch_detected
            else "degraded"
        ),
        "venue_count": len(rows),
        "registry_gap_detected": registry_gap_detected,
        "balance_gap_detected": balance_gap_detected,
        "fills_gap_detected": fills_gap_detected,
        "execution_diagnostics_status": (
            "ok"
            if rows
            and not registry_gap_detected
            and not balance_gap_detected
            and not fills_gap_detected
            and not order_status_gap_detected
            and not currency_mismatch_detected
            else "degraded"
        ),
        "execution_balance_gap_detected": balance_gap_detected,
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
        "recommended_read_order": [
            "docs/ACCEPTANCE_AUDIT.md",
            "docs/IMPLEMENTATION_STATUS.md",
            "data/ops/execution_venue_diagnostics_summary.json",
            "data/ops/execution_venue_comparison_summary.json",
            "data/ops/execution_snapshot_summary.json",
            "data/ops/current_state_index.json",
            "data/ops/readiness_snapshot.json",
        ],
    }

    lines = [
        "# Execution Venue Diagnostics",
        "",
        "## Overview",
        "",
        f"- overall_status: {summary['overall_status']}",
        f"- venue_count: {summary['venue_count']}",
        f"- registry_gap_detected: {summary['registry_gap_detected']}",
        f"- balance_gap_detected: {summary['balance_gap_detected']}",
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
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")

    text = "\n".join(lines)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(summary_path, summary)
    return text
