from __future__ import annotations

import html
from typing import Any, Iterable, Mapping


def escape_html_value(value: object) -> str:
    return html.escape("" if value is None else str(value))


def venue_decision_rows(items: Iterable[Mapping[str, Any]]) -> str:
    return "\n".join(
        (
            "<tr>"
            f"<td>{escape_html_value(item.get('venue'))}</td>"
            f"<td>{escape_html_value(item.get('decision'))}</td>"
            f"<td>{escape_html_value(item.get('main_blocker'))}</td>"
            "</tr>"
        )
        for item in items
        if isinstance(item, dict)
    )


def diagnostics_rows(items: Iterable[Any]) -> str:
    return "\n".join(
        (
            "<tr>"
            f"<td>{escape_html_value(item.symbol)}</td>"
            f"<td>{item.rows}</td>"
            f"<td>{item.market_open_rows}</td>"
            f"<td>{item.tradable_rate:.4f}</td>"
            f"<td>{item.stale_rate:.4f}</td>"
            f"<td>{item.missing_mark_price_rate:.4f}</td>"
            f"<td>{item.missing_index_price_rate:.4f}</td>"
            f"<td>{escape_html_value(item.oracle_age_p90_ms)}</td>"
            f"<td>{escape_html_value(item.spread_p90_bps)}</td>"
            "</tr>"
        )
        for item in items
    )


def cost_rows(rows: Iterable[Mapping[str, Any]]) -> str:
    return "\n".join(
        (
            "<tr>"
            f"<td>{escape_html_value(row.get('venue'))}</td>"
            f"<td>{escape_html_value(row.get('symbol'))}</td>"
            f"<td>{escape_html_value(row.get('stale_rate'))}</td>"
            f"<td>{escape_html_value(row.get('tradable_rate'))}</td>"
            f"<td>{escape_html_value(row.get('spread_p90_bps'))}</td>"
            f"<td>{escape_html_value(row.get('holding_cost_4h_bps'))}</td>"
            f"<td>{escape_html_value(row.get('notes'))}</td>"
            "</tr>"
        )
        for row in rows
    )


def backtest_rows(rows: Iterable[Mapping[str, Any]]) -> str:
    return "\n".join(
        (
            "<tr>"
            f"<td>{escape_html_value(row.get('venue'))}</td>"
            f"<td>{escape_html_value(row.get('canonical_symbol'))}</td>"
            f"<td>{escape_html_value(row.get('trade_count'))}</td>"
            f"<td>{escape_html_value(row.get('avg_trade_return'))}</td>"
            f"<td>{escape_html_value(row.get('cost_drag_bps'))}</td>"
            f"<td>{escape_html_value(row.get('stale_rejected_count'))}</td>"
            f"<td>{escape_html_value(row.get('halt_rejected_count'))}</td>"
            "</tr>"
        )
        for row in rows
    )


def list_items(items: Iterable[object]) -> str:
    return "".join(f"<li>{escape_html_value(item)}</li>" for item in items) or "<li>none</li>"


def validation_items(issues: Iterable[Any]) -> str:
    return (
        "".join(
            f"<li>{escape_html_value(issue.path)}: {escape_html_value(issue.message)}</li>"
            for issue in issues
        )
        or "<li>none</li>"
    )


def escaped_lines_pre(lines: Iterable[str]) -> str:
    return html.escape("\n".join(lines))
