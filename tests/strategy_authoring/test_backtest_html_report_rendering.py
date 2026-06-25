from __future__ import annotations

from html.parser import HTMLParser

from sis.backtest.html_report_rendering import render_strategy_backtest_html


def _view_model() -> dict:
    return {
        "created_at": "2026-01-04T00:00:00+00:00",
        "summary": {
            "strategy_id": "html-render-demo",
            "trade_count": 1,
            "total_return": 0.01,
            "max_drawdown": -0.02,
            "net_pnl_usd": 100.0,
        },
        "result_label": {
            "code": "needs_more_validation",
            "label": "要追加検証",
            "description": "追加検証が必要です。",
            "reasons": ["<unsafe reason>"],
            "next_checks": ["benchmark を確認する。"],
        },
        "visual_data": {
            "trades": [
                {
                    "ts_signal": "2026-01-01T00:00:00+00:00",
                    "date": "2026-01-01",
                    "canonical_symbol": '<img src=x onerror="alert(1)">',
                    "side": "long",
                    "signal_return": 0.01,
                    "cost_drag_bps": 1.0,
                    "signal_id": "<script>alert(1)</script>",
                }
            ],
            "equity_curve": [
                {
                    "date": "2026-01-01",
                    "cumulative_return": 0.01,
                    "drawdown": 0.0,
                }
            ],
            "benchmark_curve": [
                {
                    "date": "2026-01-01",
                    "strategy_return": 0.01,
                    "benchmark_return": 0.005,
                    "active_return": 0.005,
                }
            ],
            "periods": [{"period": "2026-01-01", "trade_count": 1, "total_return": 0.01}],
            "stress_scenarios": [
                {
                    "scenario_id": "base",
                    "stressed_total_return": 0.01,
                    "total_additional_bps_per_trade": 0.0,
                }
            ],
            "rolling_stability_summary": {"window_count": 1},
            "regime_split_summary": {"dimension_count": 1},
            "comparison_diagnostics": {"threshold_failures": []},
        },
    }


def test_render_strategy_backtest_html_includes_interactive_sections_and_boundaries() -> None:
    html = render_strategy_backtest_html(_view_model())

    HTMLParser().feed(html)
    assert "Strategy Backtest Visual Report" in html
    assert "累積損益" in html
    assert "Benchmark 比較" in html
    assert "期間で絞る" in html
    assert "Diagnostics" in html
    assert "report-data" in html
    assert "renderLineChart" in html
    assert "paper / live 実行許可ではありません" in html


def test_render_strategy_backtest_html_escapes_embedded_json_and_runtime_rows() -> None:
    html = render_strategy_backtest_html(_view_model())

    assert '<img src=x onerror="alert(1)">' not in html
    assert "<script>alert(1)</script>" not in html
    assert "\\u003cimg src=x" in html
    assert "const escapeHtml" in html
    assert "escapeHtml(row.canonical_symbol)" in html
    assert "escapeHtml(row.signal_id)" in html
