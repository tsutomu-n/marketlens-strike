from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def quote_diagnostics_report_lines(
    *,
    diagnostics: Sequence[Any],
    summary: Mapping[str, Any],
    venue: str | None,
    symbol: str | None,
) -> list[str]:
    lines = ["# Quote Diagnostics Report", ""]
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
            "## Summary",
            "",
            f"- diagnostic_count: {summary['diagnostic_count']}",
            f"- row_count: {summary['row_count']}",
            f"- venues: {summary['venues']}",
            f"- symbols: {summary['symbols']}",
            f"- filter_venue: {venue}",
            f"- filter_symbol: {symbol}",
            "",
            "## Diagnostics",
            "",
        ]
    )
    if diagnostics:
        for item in diagnostics:
            lines.append(f"- venue={item.venue} symbol={item.symbol}")
            lines.append(f"  - stale_threshold_ms: {item.stale_threshold_ms}")
            lines.append(f"  - rows: {item.rows}")
            lines.append(f"  - market_open_rows: {item.market_open_rows}")
            lines.append(f"  - tradable_rate: {item.tradable_rate:.4f}")
            lines.append(f"  - stale_rate: {item.stale_rate:.4f}")
            lines.append(f"  - missing_mark_price_rate: {item.missing_mark_price_rate:.4f}")
            lines.append(f"  - missing_index_price_rate: {item.missing_index_price_rate:.4f}")
            lines.append(f"  - missing_oracle_price_rate: {item.missing_oracle_price_rate:.4f}")
            lines.append(f"  - missing_funding_rate: {item.missing_funding_rate:.4f}")
            lines.append(f"  - missing_open_interest_rate: {item.missing_open_interest_rate:.4f}")
            lines.append(f"  - missing_spread_rate: {item.missing_spread_rate:.4f}")
            lines.append(f"  - l2_only_rate: {item.l2_only_rate:.4f}")
            lines.append(f"  - fee_mode_unknown_rate: {item.fee_mode_unknown_rate:.4f}")
            lines.append(f"  - block_reason_distribution: {item.block_reason_distribution}")
            lines.append(f"  - oracle_age_p50_ms: {item.oracle_age_p50_ms}")
            lines.append(f"  - oracle_age_p90_ms: {item.oracle_age_p90_ms}")
            lines.append(f"  - spread_p50_bps: {item.spread_p50_bps}")
            lines.append(f"  - spread_p90_bps: {item.spread_p90_bps}")
    else:
        lines.append("- diagnostics: none")
    return lines
