from __future__ import annotations

from typing import Any


def detail_markdown_lines(data: Any) -> list[str]:
    lines = [
        "## Artifact Summary",
        "",
        f"- sidecar_metadata_rows: `{data.row_counts['sidecar_metadata']}`",
        f"- sidecar_pricing_rows: `{data.row_counts['sidecar_pricing']}`",
        f"- raw_quote_rows: `{data.row_counts['raw_quotes']}`",
        f"- normalized_quotes: `{data.artifacts.normalized_quotes}`",
        f"- cost_matrix: `{data.artifacts.cost_matrix}`",
        f"- backtest_metrics: `{data.artifacts.backtest_metrics}`",
        f"- go_no_go_report: `{data.artifacts.go_no_go_report}`",
        f"- evidence_card: `{data.artifacts.evidence_card}`",
        "",
        "## Venue Decisions",
        "",
        "| Venue | Decision | Main Blocker |",
        "|---|---|---|",
    ]
    for item in data.venue_decisions:
        if not isinstance(item, dict):
            continue
        lines.append(
            f"| {item.get('venue', '')} | {item.get('decision', '')} | {item.get('main_blocker', '') or ''} |"
        )
    lines.extend(
        [
            "",
            "## GTrade Diagnostics",
            "",
            (
                "| Symbol | Rows | Open Rows | Tradable Rate | Stale Rate | Missing Mark | "
                "Missing Index | Oracle p90 ms | Spread p90 bps |"
            ),
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for item in data.quote_diagnostics:
        lines.append(
            f"| {item.symbol} | {item.rows} | {item.market_open_rows} | {item.tradable_rate:.4f} | {item.stale_rate:.4f} | "
            f"{item.missing_mark_price_rate:.4f} | {item.missing_index_price_rate:.4f} | {item.oracle_age_p90_ms} | {item.spread_p90_bps} |"
        )
    lines.extend(
        [
            "",
            "## Cost Matrix Snapshot",
            "",
            "| Venue | Symbol | Stale Rate | Tradable Rate | Spread p90 bps | Holding 4h bps | Notes |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in data.cost_rows:
        lines.append(
            f"| {row.get('venue', '')} | {row.get('symbol', '')} | {row.get('stale_rate', '')} | "
            f"{row.get('tradable_rate', '')} | {row.get('spread_p90_bps', '')} | {row.get('holding_cost_4h_bps', '')} | {row.get('notes', '')} |"
        )
    lines.extend(
        [
            "",
            "## Backtest Snapshot",
            "",
            (
                "| Venue | Symbol | Trade Count | Avg Trade Return | Cost Drag bps | "
                "Stale Rejected | Halt Rejected |"
            ),
            "|---|---|---|---|---|---|---|",
        ]
    )
    for row in data.backtest_metrics:
        lines.append(
            f"| {row.get('venue', '')} | {row.get('canonical_symbol', '')} | {row.get('trade_count', '')} | "
            f"{row.get('avg_trade_return', '')} | {row.get('cost_drag_bps', '')} | {row.get('stale_rejected_count', '')} | "
            f"{row.get('halt_rejected_count', '')} |"
        )
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- checked_files: `{data.validation.checked_files}`",
            f"- issue_count: `{len(data.validation.issues)}`",
        ]
    )
    for issue in data.validation.issues:
        lines.append(f"- {issue.path}: {issue.message}")
    lines.extend(["", "## Blockers", ""])
    if data.blockers:
        lines.extend(f"- {item}" for item in data.blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    if data.next_actions:
        lines.extend(f"- {item}" for item in data.next_actions)
    else:
        lines.append("- none")
    lines.extend(["", "## Log Tail", "", "```text"])
    lines.extend(data.log_tail)
    lines.extend(["```", ""])
    return lines
