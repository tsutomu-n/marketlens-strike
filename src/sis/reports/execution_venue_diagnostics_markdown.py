from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def execution_venue_diagnostics_report_lines(*, summary: Mapping[str, Any]) -> list[str]:
    lines = ["# Execution Venue Diagnostics", ""]
    quick_navigation = summary["quick_navigation"]
    if quick_navigation:
        lines.extend(["## Quick Navigation", ""])
        lines.extend(f"- {key}: {value}" for key, value in quick_navigation.items())
        lines.append("")
    related_reports = summary["related_reports"]
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
    lines.extend(f"- {item}" for item in summary["recommended_read_order"])
    lines.append("")
    return lines
