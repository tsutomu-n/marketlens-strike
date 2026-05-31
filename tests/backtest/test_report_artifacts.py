from __future__ import annotations

from sis.backtest.engine.report import render_backtest_html, render_backtest_markdown


def test_report_renderers_include_required_rev3_sections() -> None:
    metrics = {"net_return_after_cost": 0.01, "trade_count": 2}
    artifacts = {"metrics": "metrics.json"}

    markdown = render_backtest_markdown(metrics=metrics, artifacts=artifacts, warnings=["warn"])
    html = render_backtest_html(markdown)

    for section in [
        "Run Summary",
        "Scope and Non-Scope",
        "Config Summary",
        "Data Manifest",
        "Data Quality",
        "Strategy Summary",
        "Performance Summary",
        "Benchmark Comparison",
        "Scenario Sensitivity",
        "Split Validation",
        "Parameter Sweep",
        "Trade List Summary",
        "Blocked Events",
        "Session / Market Status Breakdown",
        "Cost Breakdown",
        "Open Position at End",
        "Warnings / Known Limitations",
        "Artifact Paths",
    ]:
        assert f"## {section}" in markdown
    assert html.startswith("<!doctype html>")
    assert "<h2>Run Summary</h2>" in html
