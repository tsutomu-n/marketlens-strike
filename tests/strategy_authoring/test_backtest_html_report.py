from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path

from jsonschema import validate
from typer.testing import CliRunner

from sis.backtest.html_report import build_strategy_backtest_html_report
from sis.cli import app


runner = CliRunner()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_metrics(path: Path) -> None:
    _write_json(
        path,
        {
            "schema_version": "strategy_authoring_backtest_result.v1",
            "strategy_id": "html_report_demo",
            "paper_only": True,
            "live_order_submitted": False,
            "summary": {
                "executed_count": 3,
                "executed_signal_results": [
                    {
                        "signal_id": "a",
                        "ts_signal": "2026-01-01T00:00:00+00:00",
                        "venue": "trade_xyz",
                        "canonical_symbol": "XYZ100",
                        "side": "long",
                        "timeframe": "4h",
                        "signal_return": 0.01,
                        "exit_reason": "fixed_horizon",
                        "cost_drag_bps": 1.0,
                        "notional_usd": 1000.0,
                    },
                    {
                        "signal_id": "b",
                        "ts_signal": "2026-01-02T00:00:00+00:00",
                        "venue": "trade_xyz",
                        "canonical_symbol": "XYZ100",
                        "side": "long",
                        "timeframe": "4h",
                        "signal_return": 0.015,
                        "exit_reason": "fixed_horizon",
                        "cost_drag_bps": 1.0,
                        "notional_usd": 1000.0,
                    },
                    {
                        "signal_id": "c",
                        "ts_signal": "2026-01-03T00:00:00+00:00",
                        "venue": "trade_xyz",
                        "canonical_symbol": "XYZ100",
                        "side": "long",
                        "timeframe": "4h",
                        "signal_return": 0.02,
                        "exit_reason": "fixed_horizon",
                        "cost_drag_bps": 1.0,
                        "notional_usd": 1000.0,
                    },
                ],
                "executed_signal_summary": {"win_rate": 1.0},
                "aggregate_metrics": {
                    "trade_count": 3,
                    "total_return": 0.045,
                    "max_drawdown": 0.0,
                    "cost_drag_bps": 3.0,
                },
                "capital": {
                    "initial_capital_usd": 10000.0,
                    "net_pnl_usd": 450.0,
                    "ending_equity_usd": 10450.0,
                    "max_drawdown_loss_usd": 0.0,
                },
                "backtest_passed": True,
            },
        },
    )


def _write_supporting_artifacts(data_dir: Path) -> None:
    _write_json(
        data_dir / "research/backtest_pack/strategy_backtest_pack_validation.json",
        {
            "schema_version": "strategy_backtest_pack_validation.v1",
            "decision": "PASS",
            "summary": {"failed_count": 0},
        },
    )
    _write_json(
        data_dir / "research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json",
        {
            "schema_version": "strategy_backtest_benchmark_relative.v1",
            "summary": {"active_total_return": 0.01, "information_ratio": 1.2},
            "comparisons": [
                {
                    "ts_signal": "2026-01-01T00:00:00+00:00",
                    "strategy_return": 0.01,
                    "benchmark_return": 0.005,
                    "active_return": 0.005,
                },
                {
                    "ts_signal": "2026-01-02T00:00:00+00:00",
                    "strategy_return": 0.015,
                    "benchmark_return": 0.004,
                    "active_return": 0.011,
                },
            ],
        },
    )
    _write_json(
        data_dir / "research/backtest_stress/strategy_backtest_stress.json",
        {
            "schema_version": "strategy_backtest_stress.v1",
            "summary": {"worst_stressed_total_return": 0.01},
            "scenarios": [
                {
                    "scenario_id": "base",
                    "stressed_total_return": 0.045,
                    "stressed_max_drawdown": 0.0,
                    "total_additional_bps_per_trade": 0.0,
                },
                {
                    "scenario_id": "severe",
                    "stressed_total_return": 0.01,
                    "stressed_max_drawdown": -0.01,
                    "total_additional_bps_per_trade": 25.0,
                },
            ],
        },
    )
    _write_json(
        data_dir / "research/backtest_data_availability/backtest_data_availability_ledger.json",
        {
            "schema_version": "backtest_data_availability_ledger.v1",
            "status": "pass",
            "summary": {"total_gap_count": 0},
        },
    )
    _write_json(
        data_dir / "research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json",
        {
            "schema_version": "strategy_backtest_no_lookahead_diff.v1",
            "summary": {"failed_count": 0, "coverage_status": "runtime_replay_verified"},
        },
    )
    _write_json(
        data_dir / "research/backtest_rolling_stability/strategy_backtest_rolling_stability.json",
        {
            "schema_version": "strategy_backtest_rolling_stability.v1",
            "summary": {"window_count": 1},
        },
    )
    _write_json(
        data_dir / "research/backtest_regime_split/strategy_backtest_regime_split.json",
        {"schema_version": "strategy_backtest_regime_split.v1", "summary": {"dimension_count": 1}},
    )
    _write_json(
        data_dir / "research/backtest_compare/strategy_backtest_comparison.json",
        {
            "schema_version": "strategy_backtest_comparison.v1",
            "comparison_diagnostics": {"threshold_failures": []},
        },
    )


def _build_report(data_dir: Path, *, min_trade_count_for_candidate: int = 30):
    return build_strategy_backtest_html_report(
        metrics_path=data_dir / "research/strategy_backtest_metrics.json",
        validation_path=data_dir / "research/backtest_pack/strategy_backtest_pack_validation.json",
        benchmark_relative_path=data_dir
        / "research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json",
        stress_path=data_dir / "research/backtest_stress/strategy_backtest_stress.json",
        rolling_stability_path=data_dir
        / "research/backtest_rolling_stability/strategy_backtest_rolling_stability.json",
        regime_split_path=data_dir
        / "research/backtest_regime_split/strategy_backtest_regime_split.json",
        data_availability_path=data_dir
        / "research/backtest_data_availability/backtest_data_availability_ledger.json",
        no_lookahead_path=data_dir
        / "research/backtest_no_lookahead/strategy_backtest_no_lookahead_diff.json",
        comparison_path=data_dir / "research/backtest_compare/strategy_backtest_comparison.json",
        out_dir=data_dir / "research/backtest_html_report",
        reports_dir=data_dir / "reports",
        min_trade_count_for_candidate=min_trade_count_for_candidate,
    )


def test_build_strategy_backtest_html_report_writes_manifest_and_interactive_html(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")
    _write_supporting_artifacts(data_dir)

    result = _build_report(data_dir, min_trade_count_for_candidate=3)

    schema = json.loads(
        Path("schemas/strategy_backtest_html_report.v1.schema.json").read_text(encoding="utf-8")
    )
    validate(instance=result.payload, schema=schema)
    assert result.payload["result_label"]["code"] == "paper_observation_candidate"
    assert result.payload["paper_observation_candidate_is_permission"] is False
    assert result.payload["paper_only"] is True
    assert result.payload["permits_live_order"] is False
    assert result.payload["wallet_used"] is False
    assert result.payload["exchange_write_used"] is False
    assert result.payload["visual_data"]["periods"][0]["period"] == "2026-01-01"
    assert result.payload["visual_data"]["equity_curve"][-1]["pnl_usd"] > 0
    assert result.payload["html_report_hash"].startswith("sha256:")
    assert result.manifest_path.exists()
    assert result.html_report_path.exists()

    html = result.html_report_path.read_text(encoding="utf-8")
    HTMLParser().feed(html)
    assert "Strategy Backtest Visual Report" in html
    assert "累積損益" in html
    assert "期間で絞る" in html
    assert "Diagnostics" in html
    assert "report-data" in html
    assert "renderLineChart" in html
    assert "paper / live 実行許可ではありません" in html


def test_strategy_backtest_html_report_labels_small_samples_as_insufficient(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")
    _write_supporting_artifacts(data_dir)

    result = _build_report(data_dir)

    assert result.payload["result_label"]["code"] == "insufficient_evidence"
    assert result.payload["result_label"]["label"] == "検証不足"
    assert result.payload["min_trade_count_for_candidate"] == 30


def test_strategy_backtest_html_report_derives_missing_active_return(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")
    _write_supporting_artifacts(data_dir)
    benchmark_path = (
        data_dir / "research/backtest_benchmark_relative/strategy_backtest_benchmark_relative.json"
    )
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    for row in benchmark["comparisons"]:
        row.pop("active_return")
    _write_json(benchmark_path, benchmark)

    result = _build_report(data_dir, min_trade_count_for_candidate=3)

    curve = result.payload["visual_data"]["benchmark_curve"]
    assert abs(curve[0]["active_return"] - 0.005) < 1e-12
    assert abs(curve[1]["active_return"] - 0.016055) < 1e-12


def test_strategy_backtest_html_report_escapes_artifact_strings(tmp_path) -> None:
    data_dir = tmp_path / "data"
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    _write_metrics(metrics_path)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    first_trade = metrics["summary"]["executed_signal_results"][0]
    first_trade["canonical_symbol"] = '<img src=x onerror="alert(1)">'
    first_trade["signal_id"] = "<script>alert(1)</script>"
    _write_json(metrics_path, metrics)
    _write_supporting_artifacts(data_dir)

    result = _build_report(data_dir, min_trade_count_for_candidate=3)

    html = result.html_report_path.read_text(encoding="utf-8")
    assert '<img src=x onerror="alert(1)">' not in html
    assert "<script>alert(1)</script>" not in html
    assert "\\u003cimg src=x" in html
    assert "const escapeHtml" in html
    assert "escapeHtml(row.canonical_symbol)" in html
    assert "function chartDomain" in html


def test_strategy_backtest_html_report_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))
    _write_metrics(data_dir / "research/strategy_backtest_metrics.json")
    _write_supporting_artifacts(data_dir)

    result = runner.invoke(
        app,
        ["strategy-backtest-html-report", "--min-trade-count-for-candidate", "3"],
    )

    assert result.exit_code == 0, result.stdout
    assert "backtest_html_report=" in result.stdout
    assert "backtest_html_report_manifest=" in result.stdout
    assert "result_label=paper観察候補" in result.stdout
    assert (data_dir / "reports/strategy_backtest_html_report.html").exists()
    assert (data_dir / "research/backtest_html_report/strategy_backtest_html_report.json").exists()
