from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sis.reports.live_evidence_html_rows import (
    backtest_rows,
    cost_rows,
    diagnostics_rows,
    escaped_lines_pre,
    list_items,
    validation_items,
    venue_decision_rows,
)


def test_venue_decision_rows_escape_values_and_preserve_column_order() -> None:
    rows = venue_decision_rows(
        [
            {
                "venue": "<script>alert(1)</script>",
                "decision": "BLOCK",
                "main_blocker": "x < y",
            }
        ]
    )

    assert rows == (
        "<tr><td>&lt;script&gt;alert(1)&lt;/script&gt;</td><td>BLOCK</td><td>x &lt; y</td></tr>"
    )
    assert "<script>alert(1)</script>" not in rows


def test_diagnostics_rows_escape_nullable_values_and_format_rates() -> None:
    rows = diagnostics_rows(
        [
            SimpleNamespace(
                symbol="SPY <ETF>",
                rows=1,
                market_open_rows=1,
                tradable_rate=1.0,
                stale_rate=0.0,
                missing_mark_price_rate=0.25,
                missing_index_price_rate=0.5,
                oracle_age_p90_ms=None,
                spread_p90_bps="<wide>",
            )
        ]
    )

    assert rows == (
        "<tr>"
        "<td>SPY &lt;ETF&gt;</td>"
        "<td>1</td>"
        "<td>1</td>"
        "<td>1.0000</td>"
        "<td>0.0000</td>"
        "<td>0.2500</td>"
        "<td>0.5000</td>"
        "<td></td>"
        "<td>&lt;wide&gt;</td>"
        "</tr>"
    )


def test_cost_and_backtest_rows_escape_values_and_preserve_column_order() -> None:
    assert cost_rows(
        [
            {
                "venue": "trade_xyz",
                "symbol": "SPY <ETF>",
                "stale_rate": "0",
                "tradable_rate": "1",
                "spread_p90_bps": "2",
                "holding_cost_4h_bps": "0.5",
                "notes": "x < y",
            }
        ]
    ) == (
        "<tr>"
        "<td>trade_xyz</td>"
        "<td>SPY &lt;ETF&gt;</td>"
        "<td>0</td>"
        "<td>1</td>"
        "<td>2</td>"
        "<td>0.5</td>"
        "<td>x &lt; y</td>"
        "</tr>"
    )

    assert backtest_rows(
        [
            {
                "venue": "trade_xyz",
                "canonical_symbol": "SPY <ETF>",
                "trade_count": 2,
                "avg_trade_return": 0.1,
                "cost_drag_bps": 1.5,
                "stale_rejected_count": 0,
                "halt_rejected_count": 0,
            }
        ]
    ) == (
        "<tr>"
        "<td>trade_xyz</td>"
        "<td>SPY &lt;ETF&gt;</td>"
        "<td>2</td>"
        "<td>0.1</td>"
        "<td>1.5</td>"
        "<td>0</td>"
        "<td>0</td>"
        "</tr>"
    )


def test_list_validation_and_pre_helpers_escape_values_and_render_empty_lists() -> None:
    assert list_items([]) == "<li>none</li>"
    assert list_items(["unsafe <blocker>"]) == "<li>unsafe &lt;blocker&gt;</li>"
    assert validation_items([]) == "<li>none</li>"
    assert (
        validation_items([SimpleNamespace(path=Path("bad<path>.json"), message="x < y")])
        == "<li>bad&lt;path&gt;.json: x &lt; y</li>"
    )
    assert escaped_lines_pre(["tail <line>"]) == "tail &lt;line&gt;"
