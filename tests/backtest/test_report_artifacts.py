from __future__ import annotations

from sis.backtest.engine.report import render_backtest_html, render_backtest_markdown


def test_report_renderers_include_required_rev3_sections() -> None:
    metrics = {"net_return_after_cost": 0.01, "trade_count": 2}
    artifacts = {"metrics": "metrics.json"}

    markdown = render_backtest_markdown(
        metrics=metrics,
        artifacts=artifacts,
        data_quality={"status": "warn", "unknown_fee_mode_count": 1},
        benchmark_results={"cash_only": {"status": "available"}},
        scenario_summary={"scenario_method": "cost_derived_v0"},
        split_summary={"oos_validation_done": True},
        parameter_summary={"best_parameter_is_in_sample_only": True},
        run_meta={"funding_policy": "nullable_zero_v0"},
        warnings=["warn"],
    )
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
    assert "_v0.1 artifact-backed section._" not in markdown
    assert "`unknown_fee_mode_count`: 1" in markdown
    assert "`scenario_method`: cost_derived_v0" in markdown
