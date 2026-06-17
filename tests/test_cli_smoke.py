from typer.testing import CliRunner
from datetime import datetime, timezone
import os
import time

import polars as pl

from sis.cli import app
from sis.ops.manifest_chain import latest_operation_manifest
from sis.storage.jsonl_store import read_json
from sis.storage.jsonl_store import read_jsonl
from support.cli import invoke_cli
from support.cli import normalized_stdout


runner = CliRunner()


def test_help_smoke() -> None:
    result = invoke_cli(["--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "probe" in stdout
    assert "collect-trade-xyz-quotes" in stdout
    assert "normalize-trade-xyz-ws-quotes" in stdout
    assert "build-trade-xyz-quote-coverage" in stdout
    assert "build-trade-xyz-reference-data" in stdout
    assert "collect-trade-xyz-real-market-reference" in stdout
    assert "collect-trade-xyz-signal-candles" in stdout
    assert "collect-trade-xyz-account-fee" in stdout
    assert "build-trade-xyz-session-state" in stdout
    assert "collect-trade-xyz-funding-history" in stdout
    assert "build-trade-xyz-funding-events-from-history" in stdout
    assert "build-trade-xyz-data-readiness" in stdout
    assert "trade-xyz-collection-status" in stdout
    assert "check-trade-xyz-historical-archive-preflight" in stdout
    assert "build-trade-xyz-data-bundle" in stdout
    assert "collect-trade-xyz-data-cycle" in stdout
    assert "bot-preview" in stdout
    assert "build-backtest" in stdout
    assert "ingest-research-data" in stdout
    assert "alpaca-smoke" in stdout
    assert "build-feature-panel" in stdout
    assert "build-signals" in stdout
    assert "strategy-author-init" in stdout
    assert "strategy-author-validate" in stdout
    assert "strategy-author-explain" in stdout
    assert "strategy-author-run" in stdout
    assert "strategy-author-bundle-run" in stdout
    assert "strategy-author-train-model" in stdout
    assert "strategy-backtest-compare" in stdout
    assert "strategy-backtest-suite" in stdout
    assert "strategy-backtest-adapter-spike" in stdout
    assert "strategy-backtest-adapter-contract" in stdout
    assert "strategy-backtest-adapter-selection" in stdout
    assert "strategy-backtest-external-run" in stdout
    assert "strategy-backtest-framework-smoke" in stdout
    assert "strategy-backtest-pack" in stdout
    assert "strategy-backtest-pack-validate" in stdout
    assert "strategy-backtest-acceptance" in stdout
    assert "strategy-review-build" in stdout
    assert "strategy-lifecycle-review" in stdout
    assert "strategy-paper-observation-cycle" in stdout
    assert "strategy-paper-observation-status" in stdout
    assert "paper-step" in stdout
    assert "estimate-order" in stdout
    assert "balance-status" in stdout
    assert "bitget-demo-smoke" in stdout
    assert "fill-status" in stdout
    assert "execution-snapshot" in stdout
    assert "execution-read-only-surfaces" in stdout
    assert "execution-gap-history" in stdout
    assert "execution-state-comparison-history" in stdout
    assert "execution-snapshot-drift-history" in stdout
    assert "execution-drift-overview" in stdout
    assert "order-status" in stdout
    assert "cancel-order" in stdout
    assert "close-position" in stdout
    assert "reconcile-positions" in stdout
    assert "healthcheck" in stdout
    assert "kill-switch" in stdout
    assert "schedule-run" in stdout
    assert "render-alert" in stdout
    assert "notification-outbox" in stdout
    assert "weekly-review" in stdout
    assert "daemon-manifest" in stdout
    assert "daemon-dry-run" in stdout
    assert "daemon-run" in stdout
    assert "export-state" in stdout
    assert "restore-state" in stdout
    assert "lifecycle-report" in stdout
    assert "monitoring-status" in stdout
    assert "comparison-report" in stdout
    assert "ops-review" in stdout
    assert "operations-dashboard" in stdout
    assert "paper-operations-runbook" in stdout
    assert "remediation-planner" in stdout
    assert "remediation-execution-plan" in stdout
    assert "remediation-session" in stdout
    assert "remediation-session-checkpoint" in stdout
    assert "remediation-scoreboard" in stdout
    assert "remediation-evaluator" in stdout
    assert "remediation-evidence" in stdout
    assert "remediation-command-results" in stdout
    assert "remediation-evidence-ingest" in stdout
    assert "paper-cycle-history" in stdout
    assert "operations-bundle" in stdout
    assert "operations-timeline" in stdout
    assert "operations-audit-pack" in stdout
    assert "audit-timeline" in stdout
    assert "audit-dashboard" in stdout
    assert "audit-bundle" in stdout
    assert "audit-bundle-history" in stdout
    assert "phase-gate-review" in stdout
    assert "paper-operations-cycle" in stdout
    assert "refresh-operations-artifacts" in stdout


def test_check_timeframe_cli_blocks_scalping() -> None:
    result = runner.invoke(app, ["check-timeframe", "1m"])
    assert result.exit_code == 2
    assert "BLOCK_SCALPING_TIMEFRAME" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_paper_from_intents_help_exposes_observation_ledger_path() -> None:
    result = invoke_cli(["paper-from-intents", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--observation-ledger-path" in stdout


def test_build_paper_intent_preview_help_describes_inputs() -> None:
    result = invoke_cli(["build-paper-intent-preview", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--source-pack" in stdout
    assert "PaperCandidatePack JSON path" in stdout
    assert "--promotion-decision" in stdout
    assert "PromotionDecision JSON path" in stdout


def test_promotion_decision_help_describes_decision_boundary() -> None:
    result = invoke_cli(["promotion-decision", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--source-pack" in stdout
    assert "PaperCandidatePack JSON path" in stdout
    assert "--decision" in stdout
    assert "hold, reject, or promote" in stdout
    assert "remains paper-only" in stdout


def test_build_paper_candidate_pack_help_describes_selection_inputs() -> None:
    result = invoke_cli(["build-paper-candidate-pack", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--trial-ledger" in stdout
    assert "Trial ledger JSONL path" in stdout
    assert "--trial-group-id" in stdout
    assert "strategy signal artifact" in stdout
    assert "run_id" in stdout
    assert "TrialRecord.metrics.selected_signal_ids" in stdout


def test_ingest_research_data_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["ingest-research-data", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "read-only market and macro research panels" in stdout
    assert "data/research/raw/yfinance_ohlcv.parquet" in stdout
    assert "data/research/market_panel.parquet" in stdout
    assert "data/research/raw/fred_macro.parquet" in stdout
    assert "data/research/macro_panel.parquet" in stdout
    assert "Yahoo Finance" in stdout
    assert "FRED/FRED" in stdout
    assert "Submits no live orders" in stdout


def test_build_feature_panel_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["build-feature-panel", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "Strategy Lab feature panel" in stdout
    assert "data/research/market_panel.parquet" in stdout
    assert "data/research/macro_panel.parquet" in stdout
    assert "data/research/event_calendar.parquet" in stdout
    assert "data/research/feature_panel.parquet" in stdout
    assert "Submits no live orders" in stdout


def test_build_event_calendar_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["build-event-calendar", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "event-calendar CSV" in stdout
    assert "--csv-path" in stdout
    assert "data/research/event_calendar.csv" in stdout
    assert "data/research/event_calendar.parquet" in stdout
    assert "required event window columns" in stdout
    assert "empty event-calendar parquet" in stdout
    assert "Submits no live orders" in stdout


def test_check_research_quality_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["check-research-quality", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "JSON report" in stdout
    assert "data/research/market_panel.parquet" in stdout
    assert "data/research/macro_panel.parquet" in stdout
    assert "data/research/event_calendar.parquet" in stdout
    assert "data/research/feature_panel.parquet" in stdout
    assert "data/research/signals.csv" in stdout
    assert "data/research/research_quality_report.json" in stdout
    assert "future-leak review status" in stdout
    assert "Submits no live orders" in stdout


def test_build_cost_matrix_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["build-cost-matrix", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "venue cost matrix" in stdout
    assert "data/normalized/quotes.parquet" in stdout
    assert "data/research/venue_cost_matrix.csv" in stdout
    assert "data/reports/venue_cost_matrix.md" in stdout
    assert "data/ops/venue_cost_matrix_summary.json" in stdout
    assert "initial" in stdout
    assert "metadata matrix" in stdout
    assert "Submits no live orders" in stdout


def test_alpaca_smoke_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["alpaca-smoke", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "read-only Alpaca market-data connectivity smoke" in stdout
    assert "latest or bounded historical stock bars" in stdout
    assert "data/ops/alpaca_live_smoke_summary.json" in stdout
    assert "data/reports/alpaca_live_smoke.md" in stdout
    assert "data/raw/real_market/alpaca" in stdout
    assert "pass, blocked, or failed outcomes" in stdout
    assert "does not submit orders" in stdout
    assert "prove production live trading readiness" in stdout


def test_diagnose_quotes_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["diagnose-quotes", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "Diagnose local quote rows" in stdout
    assert "data/raw/quotes" in stdout
    assert "venue/symbol" in stdout
    assert "stale/tradable/missing-field rates" in stdout
    assert "data/reports/quote_diagnostics.md" in stdout
    assert "data/ops/quote_diagnostics_summary.json" in stdout
    assert "latest venue file" in stdout
    assert "Performs no external API calls" in stdout
    assert "submits no orders" in stdout
    assert "--venue" in stdout
    assert "Optional venue filter" in stdout
    assert "--symbol" in stdout
    assert "Optional canonical symbol filter" in stdout


def test_build_signals_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["build-signals", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "Strategy Lab signal artifacts" in stdout
    assert "data/research/feature_panel.parquet" in stdout
    assert "data/research/strategy_signals.parquet" in stdout
    assert "data/research/strategy_signal_manifest.json" in stdout
    assert "data/research/strategy_signals.jsonl" in stdout
    assert "data/research/signals.csv" in stdout
    assert "Submits no live orders" in stdout
    assert "--generator-id" in stdout
    assert "registered_generator_ids" in stdout


def test_strategy_preview_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["strategy-preview", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "preview report" in stdout
    assert "data/research/feature_panel.parquet" in stdout
    assert "data/research/strategy_signals.parquet" in stdout
    assert "data/research/strategy_signal_manifest.json" in stdout
    assert "data/research/strategy_signals.jsonl" in stdout
    assert "data/research/signals.csv" in stdout
    assert "data/reports/strategy_signals_preview.md" in stdout
    assert "Submits no live orders" in stdout
    assert "--generator-id" in stdout
    assert "registered_generator_ids" in stdout


def test_strategy_experiment_run_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["strategy-experiment-run", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "paper-only signal artifacts" in stdout
    assert "data/research/strategy_signals.parquet" in stdout
    assert "data/research/strategy_signal_manifest.json" in stdout
    assert "data/research/signals.csv" in stdout
    assert "data/reports/strategy_experiment_run.md" in stdout
    assert "Submits no live orders" in stdout
    assert "--spec" in stdout
    assert "registered generator" in stdout
    assert "IDs; no arbitrary Python" in stdout
    assert "--max-variants" in stdout
    assert "exits with" in stdout
    assert "code 2 when exceeded" in stdout


def test_evaluate_strategy_lab_help_describes_io_and_boundary() -> None:
    result = invoke_cli(["evaluate-strategy-lab", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "paper-only trial ledger" in stdout
    assert "data/research/strategy_signals.parquet" in stdout
    assert "data/research/trial_ledger.jsonl" in stdout
    assert "data/reports/strategy_trial_report.md" in stdout
    assert "--candidate-limit" in stdout
    assert "TrialRecord.metrics.selected_signal_ids" in stdout
    assert "--split-method" in stdout
    assert "not a walk-forward PnL" in stdout
    assert "engine." in stdout


def test_strategy_paper_observation_cycle_help_smoke() -> None:
    result = invoke_cli(["strategy-paper-observation-cycle", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--session-id" in stdout
    assert "--smoke" in stdout


def test_strategy_paper_observation_append_help_smoke() -> None:
    result = invoke_cli(["strategy-paper-observation-append", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--session-manifest" in stdout
    assert "--state-path" in stdout


def test_strategy_paper_observation_status_help_smoke() -> None:
    result = invoke_cli(["strategy-paper-observation-status", "--help"])
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "--canonical-review-path" in stdout
    assert "--sessions-root" in stdout


def test_implementation_status_reports_complete_scope() -> None:
    result = runner.invoke(app, ["implementation-status"])
    assert result.exit_code == 0
    assert "PR-03" in result.stdout
    assert "PR-08" in result.stdout
    assert "PARTIAL" not in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_diagnose_quotes_exits_when_no_quotes() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["diagnose-quotes"], env={"SIS_DATA_DIR": "tmp_data"})
        assert result.exit_code == 2
        assert "No quote rows found for diagnostics." in result.stdout


def test_alpaca_smoke_cli_writes_failure_summary_without_credentials(tmp_path, monkeypatch) -> None:
    for key in (
        "APCA_API_KEY_ID",
        "APCA_API_SECRET_KEY",
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY",
        "SIS_ALPACA_API_KEY",
        "SIS_ALPACA_SECRET_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    data_dir = tmp_path / "data"
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        ["alpaca-smoke", "--symbol", "NVDA", "--timeframe", "15m"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 2
    assert "status=failed" in result.stdout
    assert "provider_connectivity_status=failed" in result.stdout
    assert "data_availability_status=unknown" in result.stdout
    assert "live_suitability_reasons=BLOCK_ALPACA_PROVIDER_UNAVAILABLE" in result.stdout
    assert "error_class=AlpacaProviderUnavailable" in result.stdout
    assert "start=None" in result.stdout
    assert "end=None" in result.stdout
    assert (data_dir / "ops/alpaca_live_smoke_summary.json").exists()
    assert (data_dir / "reports/alpaca_live_smoke.md").exists()


def test_diagnose_quotes_cli_writes_report_and_summary(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_quote = data_dir / "raw/quotes/trade_xyz/2026-05-22.jsonl"
    raw_quote.parent.mkdir(parents=True, exist_ok=True)
    raw_quote.write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"trade_xyz","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.0,"index_price":100.0,"spread_bps":2.0,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"a","oracle_ts_ms":1747872000000}',
                '{"ts_client":"2026-05-22T00:05:00+00:00","venue":"trade_xyz","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.5,"index_price":100.5,"spread_bps":3.0,"market_status":"open","is_tradable":false,"source":"test","raw_payload_sha256":"b","oracle_ts_ms":1747872300000}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app, ["diagnose-quotes", "--venue", "trade_xyz", "--symbol", "SPY"], env=env
    )

    assert result.exit_code == 0
    assert "venue=trade_xyz symbol=SPY" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/quote_diagnostics.md").exists()
    assert (data_dir / "ops/quote_diagnostics_summary.json").exists()
    report = (data_dir / "reports/quote_diagnostics.md").read_text(encoding="utf-8")
    assert "## Quick Navigation" in report
    summary = read_json(data_dir / "ops/quote_diagnostics_summary.json")
    assert summary["row_count"] == 2


def test_market_session_cli_for_qqq() -> None:
    result = runner.invoke(app, ["market-session", "--venue", "trade_xyz", "--symbol", "QQQ"])
    assert result.exit_code == 0
    assert "symbol=QQQ" in result.stdout
    assert "calendar=XNYS" in result.stdout
    assert "next_open_jst=" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_next_live_window_cli_rejects_xau() -> None:
    result = runner.invoke(app, ["next-live-window", "--venue", "trade_xyz", "--symbol", "XAU"])
    assert result.exit_code != 0
    assert "Unsupported symbol" in result.output


def test_execution_venue_comparison_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2,"venues":[{"venue":"gtrade","registry_exists":true,"balance_snapshot_exists":true,"positions_snapshot_exists":true,"fills_snapshot_exists":true,"order_status_snapshot_exists":true,"positions_count":0,"fills_count":1,"order_status_count":1,"balance":{"equity":1000,"currency":"USD"}},{"venue":"ostium","registry_exists":true,"balance_snapshot_exists":false,"positions_snapshot_exists":false,"fills_snapshot_exists":false,"order_status_snapshot_exists":true,"positions_count":1,"fills_count":0,"order_status_count":1,"balance":{"equity":null,"currency":"USD"}}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-venue-comparison"], env=env)

    assert result.exit_code == 0
    assert "Execution Venue Comparison" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "execution_venue_comparison_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_drift_overview_report:" in result.stdout
    assert "all_registries_present: True" in result.stdout
    assert "all_positions_snapshots_present: False" in result.stdout
    assert (data_dir / "reports/execution_venue_comparison.md").exists()
    assert (data_dir / "ops/execution_venue_comparison_summary.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_execution_venue_diagnostics_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"venues":[{"venue":"gtrade","registry_exists":true,"balance_snapshot_exists":true,"positions_snapshot_exists":true,"fills_snapshot_exists":true,"order_status_snapshot_exists":true,"positions_count":0,"fills_count":1,"order_status_count":1,"balance_equity":1000.0,"balance_currency":"USD"},{"venue":"ostium","registry_exists":true,"balance_snapshot_exists":false,"positions_snapshot_exists":false,"fills_snapshot_exists":false,"order_status_snapshot_exists":true,"positions_count":2,"fills_count":0,"order_status_count":2,"balance_equity":995.0,"balance_currency":"USD"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-venue-diagnostics"], env=env)

    assert result.exit_code == 0
    assert "Execution Venue Diagnostics" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "execution_venue_diagnostics_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_drift_overview_report:" in result.stdout
    assert "balance_gap_detected: True" in result.stdout
    assert "positions_snapshot_gap_detected: True" in result.stdout
    assert (data_dir / "reports/execution_venue_diagnostics.md").exists()
    assert (data_dir / "ops/execution_venue_diagnostics_summary.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_kill_switch_and_healthcheck_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot","timeline_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"timeline_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":true}}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3,"bundle_history_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"bundle_history_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":true}}',
        encoding="utf-8",
    )
    (data_dir / "ops/operations_bundle_manifest.json").write_text(
        '{"cycle_history_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"cycle_history_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":true},"cycle_history_latest_execution_overall_status":"ok","cycle_history_latest_execution_venue_count":2,"cycle_history_latest_execution_comparison_all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":2,"latest_status_match":true,"mismatching_count":0}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )

    enable = runner.invoke(app, ["kill-switch", "--enable", "--reason", "test"], env=env)
    assert enable.exit_code == 0
    assert "enabled=True" in enable.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in enable.stdout
    assert (data_dir / "reports/ops_kill_switch.md").exists()
    assert read_json(data_dir / "ops/ops_kill_switch_summary.json")["enabled"] is True

    health = runner.invoke(
        app, ["healthcheck", "--current-pnl", "-150", "--daily-loss-limit", "100"], env=env
    )
    assert health.exit_code == 0
    assert "kill_switch_enabled=True" in health.stdout
    assert "audit_overall_status=ok" in health.stdout
    assert "audit_latest_operation=audit_bundle_snapshot" in health.stdout
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in health.stdout
    assert "phase2_entry_allowed=False" in health.stdout
    assert "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears" in health.stdout
    assert "phase_gate_strict_validation_passed=True" in health.stdout
    assert "phase_gate_strict_validation_issue_count=2" in health.stdout
    assert "phase_gate_checked_files=7" in health.stdout
    assert "phase_gate_review_report_path=data/reports/phase_gate_review.md" in health.stdout
    assert (
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"
        in health.stdout
    )
    assert "execution_drift_overview_status=degraded" in health.stdout
    assert "readiness_next_phase_candidate=Stay Phase 1" in health.stdout
    assert "daily_loss_allowed=False" in health.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in health.stdout
    assert (data_dir / "reports/ops_healthcheck.md").exists()
    health_summary = read_json(data_dir / "ops/ops_healthcheck_summary.json")
    assert health_summary["status"] == "degraded"
    assert health_summary["daily_loss_allowed"] is False


def test_paper_report_cli_includes_audit_summary(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)
    from sis.state.store import StateStore

    pl.DataFrame(
        [
            {
                "ts_fill": "2026-05-24T00:00:00+00:00",
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "side": "long",
                "action": "enter_long",
                "quantity": 1.0,
                "price": 100.0,
                "notional": 100.0,
                "strategy_name": "qqq_trend_rates_vix",
            }
        ]
    ).write_parquet(data_dir / "paper/fills.parquet")
    pl.DataFrame(
        [
            {
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "side": "long",
                "quantity": 1.0,
                "avg_entry_price": 100.0,
                "opened_at": "2026-05-24T00:00:00+00:00",
                "updated_at": "2026-05-24T00:00:00+00:00",
                "realized_pnl": 0.0,
            }
        ]
    ).write_parquet(data_dir / "paper/positions.parquet")
    StateStore(data_dir / "state/marketlens.sqlite").set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "readiness_summary": {
                "next_phase_candidate": "Stay Phase 1",
                "execution_ready": False,
            },
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "execution_gap_history_summary": {
                "entry_count": 4,
                "latest_status": "ok",
                "latest_execution_diagnostics_status": "degraded",
                "report_path": "data/reports/execution_gap_history.md",
            },
            "execution_state_comparison_summary": {
                "entry_count": 4,
                "latest_status_match": False,
                "mismatching_count": 1,
                "report_path": "data/reports/execution_state_comparison_history.md",
            },
            "execution_snapshot_drift_summary": {
                "entry_count": 3,
                "latest_execution_state_comparison_status_match": True,
                "mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_snapshot_drift_history.md",
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    )

    result = runner.invoke(app, ["paper-report"], env=env)

    assert result.exit_code == 0
    assert "Daily Paper Report" in result.stdout
    assert "Audit Summary" in result.stdout
    assert "overall_status: ok" in result.stdout
    assert "Phase Gate Summary" in result.stdout
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "Readiness Summary" in result.stdout
    assert "next_phase_candidate: Stay Phase 1" in result.stdout
    assert "Audit Timeline Latest Execution" in result.stdout
    assert "Audit Bundle History Latest Execution" in result.stdout
    assert "Cycle History Latest Execution" in result.stdout
    assert "Execution Gap History" in result.stdout
    assert "entry_count: 4" in result.stdout
    assert "Execution State Comparison History" in result.stdout
    assert "mismatching_count: 1" in result.stdout
    assert "Execution Snapshot Drift History" in result.stdout
    assert "mismatching_snapshot_count: 1" in result.stdout
    assert "Execution Drift Overview" in result.stdout
    assert "overall_status: degraded" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_schedule_alert_and_weekly_review_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore

    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot"}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    schedule = runner.invoke(
        app,
        [
            "schedule-run",
            "--run-type",
            "paper",
            "--command",
            "uv run sis paper-step",
            "--every-minutes",
            "30",
        ],
        env=env,
    )
    alert = runner.invoke(
        app,
        ["render-alert", "--level", "warn", "--title", "Stale", "--body", "recollect"],
        env=env,
    )
    notification = runner.invoke(
        app,
        ["notification-outbox", "--level", "warn", "--title", "Stale", "--body", "recollect"],
        env=env,
    )
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)

    pl.DataFrame([{"venue": "gtrade", "canonical_symbol": "QQQ", "trade_count": 1}]).write_json(
        data_dir / "research/backtest_metrics.json"
    )
    pl.DataFrame(
        [{"date": "2026-05-24", "realized_pnl": 1.0, "fills_count": 1, "open_positions": 1}]
    ).write_parquet(data_dir / "paper/daily_pnl.parquet")
    StateStore(data_dir / "state/marketlens.sqlite").set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    )
    weekly = runner.invoke(app, ["weekly-review"], env=env)

    assert schedule.exit_code == 0
    assert "run_type=paper" in schedule.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in schedule.stdout
    assert '"overall_status": "ok"' in (data_dir / "ops/scheduled_run.json").read_text(
        encoding="utf-8"
    )
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase2_entry_allowed": false' in (data_dir / "ops/scheduled_run.json").read_text(
        encoding="utf-8"
    )
    assert '"balance_gap_detected": true' in (data_dir / "ops/scheduled_run.json").read_text(
        encoding="utf-8"
    )
    assert '"execution_drift_overview_status": "degraded"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in (data_dir / "ops/scheduled_run.json").read_text(
        encoding="utf-8"
    )
    assert '"next_phase_candidate": "Stay Phase 1"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"balance_gap_detected": true' in (data_dir / "ops/scheduled_run.json").read_text(
        encoding="utf-8"
    )
    assert '"next_phase_candidate": "Stay Phase 1"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert (data_dir / "reports/ops_scheduled_run.md").exists()
    schedule_summary = read_json(data_dir / "ops/ops_scheduled_run_summary.json")
    assert schedule_summary["run_type"] == "paper"
    assert alert.exit_code == 0
    assert "[WARN] Stale" in alert.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in alert.stdout
    assert (data_dir / "reports/ops_alert.md").exists()
    alert_summary = read_json(data_dir / "ops/ops_alert_summary.json")
    assert alert_summary["level"] == "warn"
    assert notification.exit_code == 0
    assert "status=queued" in notification.stdout
    assert "outbox_path=" in notification.stdout
    assert "notification_outbox_report_path=" in notification.stdout
    assert "notification_outbox_summary_path=" in notification.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in notification.stdout
    assert (data_dir / "notifications/outbox.jsonl").exists()
    assert (data_dir / "notifications/latest_notification.json").exists()
    assert (data_dir / "reports/notification_outbox.md").exists()
    notification_summary = read_json(data_dir / "ops/notification_outbox_summary.json")
    assert notification_summary["status"] == "queued"
    assert notification_summary["sink"] == "local_outbox"
    latest_notification = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest_notification is not None
    assert latest_notification["operation"] == "notification_outbox"
    assert weekly.exit_code == 0
    assert "Weekly Strategy Review" in weekly.stdout
    assert "## Quick Navigation" in weekly.stdout
    assert "weekly_review_report:" in weekly.stdout
    assert "## Related Reports" in weekly.stdout
    assert "execution_drift_overview_report:" in weekly.stdout
    assert "Paper Last Run Audit" in weekly.stdout
    assert "Paper Last Run Phase Gate" in weekly.stdout
    assert "Paper Last Run Execution Drift Overview" in weekly.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in weekly.stdout


def test_daemon_manifest_state_export_restore_and_lifecycle_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore

    store = StateStore(data_dir / "state/marketlens.sqlite")
    store.set_json("paper_positions", [{"venue": "gtrade"}])
    store.set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {"overall_status": "ok", "latest_operation": "audit_bundle_snapshot"},
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    )

    daemon = runner.invoke(app, ["daemon-manifest", "--mode", "paper"], env=env)
    export_ = runner.invoke(app, ["export-state"], env=env)
    restore = runner.invoke(
        app,
        ["restore-state", "--snapshot-path", str(data_dir / "state/state_snapshot.json")],
        env=env,
    )
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/decision_summary.json").write_text(
        '{"mode":"signal_driven","signals_considered":2,"executed_count":1,"blocked_count":1}',
        encoding="utf-8",
    )
    (data_dir / "reports/weekly_strategy_review.md").write_text(
        "# Weekly Strategy Review\n\n- sample\n", encoding="utf-8"
    )
    lifecycle = runner.invoke(app, ["lifecycle-report"], env=env)

    assert daemon.exit_code == 0
    assert "mode=paper" in daemon.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in daemon.stdout
    assert (data_dir / "reports/daemon_manifest.md").exists()
    assert (data_dir / "ops/daemon_manifest_summary.json").exists()
    assert read_json(data_dir / "ops/daemon_manifest_summary.json")["mode"] == "paper"
    assert export_.exit_code == 0
    assert "state_snapshot.json" in export_.stdout
    assert "audit_overall_status=ok" in export_.stdout
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in export_.stdout
    assert "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears" in export_.stdout
    assert "phase_gate_strict_validation_passed=True" in export_.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in export_.stdout
    assert (data_dir / "reports/state_export.md").exists()
    assert (data_dir / "ops/state_export_summary.json").exists()
    assert read_json(data_dir / "ops/state_export_summary.json")["audit_overall_status"] == "ok"
    assert restore.exit_code == 0
    assert "restored=true" in restore.stdout
    assert "audit_latest_operation=audit_bundle_snapshot" in restore.stdout
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in restore.stdout
    assert "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears" in restore.stdout
    assert "phase_gate_strict_validation_passed=True" in restore.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in restore.stdout
    assert (data_dir / "reports/state_restore.md").exists()
    assert (data_dir / "ops/state_restore_summary.json").exists()
    assert read_json(data_dir / "ops/state_restore_summary.json")["restored"] is True
    assert lifecycle.exit_code == 0
    assert "Strategy Lifecycle Report" in lifecycle.stdout
    assert "## Quick Navigation" in lifecycle.stdout
    assert "strategy_lifecycle_report:" in lifecycle.stdout
    assert "## Related Reports" in lifecycle.stdout
    assert "weekly_review_report:" in lifecycle.stdout
    assert "Paper Last Run Audit" in lifecycle.stdout
    assert "Paper Last Run Phase Gate" in lifecycle.stdout
    assert "Paper Last Run Execution Drift Overview" in lifecycle.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in lifecycle.stdout


def test_daemon_run_cli_bounded(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}

    result = runner.invoke(
        app,
        [
            "daemon-run",
            "--mode",
            "paper",
            "--command",
            "uv run python -c \"print('daemon-ok')\"",
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "status=completed" in result.stdout
    assert "cycles_completed=1" in result.stdout
    assert "daemon_loop_path=" in result.stdout
    assert "daemon_loop_report_path=" in result.stdout
    assert "daemon_loop_summary_path=" in result.stdout
    assert "daemon_loop_events_path=" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    snapshot = read_json(data_dir / "ops/daemon_loop.json")
    summary = read_json(data_dir / "ops/daemon_loop_summary.json")
    events = read_jsonl(data_dir / "ops/daemon_loop_events.jsonl")
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert (data_dir / "reports/daemon_manifest.md").exists()
    assert (data_dir / "ops/daemon_manifest_summary.json").exists()
    assert (data_dir / "reports/daemon_loop.md").exists()
    assert snapshot["status"] == "completed"
    assert summary["status"] == "completed"
    assert snapshot["cycles_requested"] == 1
    assert snapshot["cycles_completed"] == 1
    assert [event["stdout"] for event in events] == ["daemon-ok\n"]
    assert latest is not None
    assert latest["operation"] == "daemon_loop"
    assert latest["status"] == "completed"


def test_monitoring_status_and_comparison_report_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore

    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/decision_summary.json").write_text(
        '{"mode":"signal_driven","executed_count":1}', encoding="utf-8"
    )
    (data_dir / "reports/weekly_strategy_review.md").write_text(
        "# Weekly Strategy Review\n", encoding="utf-8"
    )
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot","audit_entry_count":4,"audit_bundle_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3,"bundle_history_ok_count":3}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )

    StateStore(data_dir / "state/marketlens.sqlite").set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "execution_drift_overview_summary": {
                "overall_status": "degraded",
                "diagnostics_alignment_match": False,
                "state_comparison_mismatching_count": 1,
                "snapshot_drift_mismatching_snapshot_count": 1,
                "report_path": "data/reports/execution_drift_overview.md",
            },
        },
    )
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 2.0}]).write_parquet(
        data_dir / "paper/daily_pnl.parquet"
    )
    pl.DataFrame([{"canonical_symbol": "QQQ", "avg_trade_return": 0.05}]).write_json(
        data_dir / "research/backtest_metrics.json"
    )

    monitoring = runner.invoke(app, ["monitoring-status"], env=env)
    comparison = runner.invoke(app, ["comparison-report"], env=env)

    assert monitoring.exit_code == 0
    assert "status=ok" in monitoring.stdout
    assert "audit_overall_status=ok" in monitoring.stdout
    assert "audit_latest_operation=audit_bundle_snapshot" in monitoring.stdout
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in monitoring.stdout
    assert "phase2_entry_allowed=False" in monitoring.stdout
    assert "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears" in monitoring.stdout
    assert "phase_gate_strict_validation_passed=True" in monitoring.stdout
    assert "phase_gate_strict_validation_issue_count=2" in monitoring.stdout
    assert "phase_gate_checked_files=7" in monitoring.stdout
    assert "phase_gate_review_report_path=data/reports/phase_gate_review.md" in monitoring.stdout
    assert (
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"
        in monitoring.stdout
    )
    assert "execution_drift_overview_status=degraded" in monitoring.stdout
    assert "readiness_next_phase_candidate=Stay Phase 1" in monitoring.stdout
    assert "operation_chain_exists=False" in monitoring.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in monitoring.stdout
    assert comparison.exit_code == 0
    assert "Paper vs Backtest Comparison" in comparison.stdout
    assert "## Quick Navigation" in comparison.stdout
    assert "paper_vs_backtest_comparison_report:" in comparison.stdout
    assert "## Related Reports" in comparison.stdout
    assert "current_state_index_report:" in comparison.stdout
    assert "Paper Last Run Audit" in comparison.stdout
    assert "Paper Last Run Phase Gate" in comparison.stdout
    assert "Paper Last Run Execution Drift Overview" in comparison.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in comparison.stdout


def test_build_backtest_cli_includes_audit_summary(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore

    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "venue_symbol": "QQQ/USD",
                "exec_buy_price": 100.0,
                "exec_sell_price": 99.9,
                "mark_price": 100.0,
                "mid_price": None,
                "oracle_price": None,
                "index_price": 100.0,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779415479000,
                "market_status": "open",
                "is_tradable": True,
            },
            {
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc),
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "venue_symbol": "QQQ/USD",
                "exec_buy_price": 101.0,
                "exec_sell_price": 100.9,
                "mark_price": 101.0,
                "mid_price": None,
                "oracle_price": None,
                "index_price": 101.0,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779429879000,
                "market_status": "open",
                "is_tradable": True,
            },
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")
    (data_dir / "research/signals.csv").write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength,strategy_name,reason\n"
        "2026-05-22T00:00:00+00:00,QQQ,long,4h,1.0,qqq_trend_rates_vix,test\n",
        encoding="utf-8",
    )
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,open_fee_bps,close_fee_bps,spread_p50_bps,holding_cost_4h_bps\n"
        "gtrade,QQQ,5,5,2,1\n",
        encoding="utf-8",
    )
    StateStore(data_dir / "state/marketlens.sqlite").set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "warn",
                "execution_venue_count": 1,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": False,
            },
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
        },
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["build-backtest"], env=env)

    assert result.exit_code == 0
    assert "Audit Summary" in (data_dir / "research/backtest_report.md").read_text(encoding="utf-8")
    assert '"audit"' in (data_dir / "research/decision_summary.json").read_text(encoding="utf-8")
    assert "Phase Gate Summary" in (data_dir / "research/backtest_report.md").read_text(
        encoding="utf-8"
    )
    assert "Execution Venue Comparison" in (data_dir / "research/backtest_report.md").read_text(
        encoding="utf-8"
    )
    assert "Execution Venue Diagnostics" in (data_dir / "research/backtest_report.md").read_text(
        encoding="utf-8"
    )
    assert "Execution Gap History" in (data_dir / "research/backtest_report.md").read_text(
        encoding="utf-8"
    )
    assert "Execution State Comparison History" in (
        data_dir / "research/backtest_report.md"
    ).read_text(encoding="utf-8")
    assert "Execution Snapshot Drift History" in (
        data_dir / "research/backtest_report.md"
    ).read_text(encoding="utf-8")
    assert '"phase_gate"' in (data_dir / "research/decision_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"execution_summary"' in (data_dir / "research/decision_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"execution_gap_history_summary"' in (
        data_dir / "research/decision_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_state_comparison_summary"' in (
        data_dir / "research/decision_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_snapshot_drift_summary"' in (
        data_dir / "research/decision_summary.json"
    ).read_text(encoding="utf-8")
    assert '"timeline_latest_execution_summary"' in (
        data_dir / "research/decision_summary.json"
    ).read_text(encoding="utf-8")
    assert '"bundle_history_latest_execution_summary"' in (
        data_dir / "research/decision_summary.json"
    ).read_text(encoding="utf-8")
    assert '"cycle_history_latest_execution_summary"' in (
        data_dir / "research/decision_summary.json"
    ).read_text(encoding="utf-8")
    assert (data_dir / "research/backtest_metrics_summary.json").exists()
    assert '"phase_gate"' in (data_dir / "research/backtest_metrics_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"execution"' in (data_dir / "research/backtest_metrics_summary.json").read_text(
        encoding="utf-8"
    )
    assert '"execution_comparison"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_diagnostics"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_gap_history_summary"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_state_comparison_summary"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_snapshot_drift_summary"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"timeline_latest_execution_summary"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"bundle_history_latest_execution_summary"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert '"cycle_history_latest_execution_summary"' in (
        data_dir / "research/backtest_metrics_summary.json"
    ).read_text(encoding="utf-8")
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_check_go_no_go_cli_includes_audit_summary_in_markdown(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore

    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "registry").mkdir(parents=True, exist_ok=True)
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (data_dir / "raw/sidecar/ostium").mkdir(parents=True, exist_ok=True)
    (data_dir / "normalized/quotes.parquet").write_bytes(b"PAR1")
    (data_dir / "research/backtest_report.md").write_text("# Backtest\n", encoding="utf-8")
    (data_dir / "research/backtest_metrics.json").write_text(
        '[{"venue":"gtrade","canonical_symbol":"QQQ","trade_count":1,"avg_trade_return":0.01}]',
        encoding="utf-8",
    )
    (data_dir / "research/signals.csv").write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength\n"
        "2026-05-22T00:00:00+00:00,QQQ,long,4h,1.0\n",
        encoding="utf-8",
    )
    (data_dir / "registry/gtrade_instrument_registry.json").write_text("[]", encoding="utf-8")
    (data_dir / "registry/ostium_instrument_registry.json").write_text(
        '[{"venue":"ostium","active":true,"venue_symbol":"SPX/USD","opening_fee_bps":3.0,"max_open_interest":"1","rollover_fee_per_block":"1","max_leverage":100}]',
        encoding="utf-8",
    )
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,stale_rate,tradable_rate,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps\n"
        "gtrade,QQQ,0.01,1.0,2,1,2,3\n"
        "ostium,SPX_EQUIV,0.01,1.0,2,1,2,3\n",
        encoding="utf-8",
    )
    StateStore(data_dir / "state/marketlens.sqlite").set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "warn",
                "execution_venue_count": 1,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": False,
            },
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
        },
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["check-go-no-go"], env=env)

    assert result.exit_code == 0
    text = (data_dir / "research/go_no_go_report.md").read_text(encoding="utf-8")
    assert "## Audit Summary" in text
    assert "overall_status: ok" in text
    assert "## Phase Gate Summary" in text
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "## Execution Snapshot" in text
    assert "venue_count: 2" in text
    assert "## Execution Venue Comparison" in text
    assert "all_registries_present: True" in text
    assert "## Execution Venue Diagnostics" in text
    assert "balance_gap_detected: True" in text
    assert "## Execution Gap History" in text
    assert "entry_count: 4" in text
    assert "## Execution State Comparison History" in text
    assert "mismatching_count: 1" in text
    assert "## Execution Snapshot Drift History" in text
    assert "mismatching_snapshot_count: 1" in text
    assert "## Quick Navigation" in text
    assert "go_no_go_report:" in text
    assert "## Related Reports" in text
    assert "execution_snapshot_report:" in text
    assert "## Audit Timeline Latest Execution" in text
    assert "## Audit Bundle History Latest Execution" in text
    assert "## Cycle History Latest Execution" in text
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_build_evidence_card_cli_includes_audit_summary(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    import json
    from sis.state.store import StateStore

    (data_dir / "registry").mkdir(parents=True, exist_ok=True)
    (data_dir / "raw/quotes/gtrade").mkdir(parents=True, exist_ok=True)
    (data_dir / "raw/sidecar/ostium").mkdir(parents=True, exist_ok=True)
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "registry/gtrade_instrument_registry.json").write_text(
        '[{"venue":"gtrade","canonical_symbol":"SPY"}]', encoding="utf-8"
    )
    (data_dir / "registry/ostium_instrument_registry.json").write_text(
        '[{"venue":"ostium","canonical_symbol":"SPX_EQUIV","venue_symbol":"US500-USD","active":true,"opening_fee_bps":3,"max_open_interest":"1000000","rollover_fee_per_block":"1e-10","max_leverage":50}]',
        encoding="utf-8",
    )
    (data_dir / "raw/sidecar/ostium/positions_all_2026-05-22.json").write_text(
        '{"positions":[{"venue_symbol":"US500-USD","side":"long","entry_px":"100","liquidation_px":"80"}]}',
        encoding="utf-8",
    )
    (data_dir / "raw/quotes/gtrade/2026-05-22.jsonl").write_text(
        '{"venue":"gtrade"}\n', encoding="utf-8"
    )
    (data_dir / "normalized/quotes.parquet").write_bytes(b"placeholder")
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,stale_rate,tradable_rate,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps\n"
        "gtrade,SPY,0,0,2,0,0,0\n",
        encoding="utf-8",
    )
    (data_dir / "research/backtest_metrics.json").write_text(
        '[{"trade_count":1,"avg_trade_return":0.1}]', encoding="utf-8"
    )
    (data_dir / "research/backtest_report.md").write_text("# Backtest\n", encoding="utf-8")
    (data_dir / "research/go_no_go_report.md").write_text("# Go/No-Go\n", encoding="utf-8")
    StateStore(data_dir / "state/marketlens.sqlite").set_json(
        "paper_last_run",
        {
            "orders_count": 1,
            "audit": {
                "overall_status": "ok",
                "latest_operation": "audit_bundle_snapshot",
                "bundle_history_snapshot_count": 3,
            },
            "phase_gate": {
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "phase2_entry_allowed": False,
                "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
                "strict_validation_passed": True,
            },
            "timeline_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "timeline_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
            "bundle_history_latest_execution_summary": {
                "execution_overall_status": "warn",
                "execution_venue_count": 1,
            },
            "bundle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": False,
            },
            "cycle_history_latest_execution_summary": {
                "execution_overall_status": "ok",
                "execution_venue_count": 2,
            },
            "cycle_history_latest_execution_comparison_summary": {
                "execution_comparison_all_registries_present": True,
            },
        },
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["build-evidence-card"], env=env)

    assert result.exit_code == 0
    evidence_cards = sorted((data_dir / "evidence").glob("evidence_card_*.json"))
    assert evidence_cards
    payload = json.loads(evidence_cards[-1].read_text(encoding="utf-8"))
    assert payload["audit_summary"]["overall_status"] == "ok"
    assert payload["phase_gate_summary"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert payload["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        payload["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert payload["bundle_history_latest_execution_summary"]["execution_overall_status"] == "warn"
    assert (
        payload["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is False
    )
    assert payload["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        payload["cycle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert payload["cycle_history_latest_execution_overall_status"] == "ok"
    assert payload["cycle_history_latest_execution_venue_count"] == 2
    assert payload["cycle_history_latest_execution_comparison_all_registries_present"] is True
    assert payload["execution_summary"]["overall_status"] == "ok"
    assert payload["execution_summary"]["venue_count"] == 2
    assert payload["execution_comparison_summary"]["all_registries_present"] is True
    assert payload["execution_diagnostics_summary"]["balance_gap_detected"] is True
    assert payload["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert (
        payload["execution_state_comparison_summary"][
            "execution_state_comparison_mismatching_count"
        ]
        == 1
    )
    assert (
        payload["execution_snapshot_drift_summary"][
            "execution_snapshot_drift_mismatching_snapshot_count"
        ]
        == 1
    )
    assert payload["quick_navigation"]["evidence_card_report"].endswith(".json")
    assert payload["quick_navigation"]["phase_gate_review_report"] == str(
        data_dir / "reports/phase_gate_review.md"
    )
    assert payload["related_reports"]["execution_snapshot_report"] == str(
        data_dir / "reports/execution_snapshot.md"
    )
    assert payload["related_reports"]["paper_vs_backtest_comparison_report"] == str(
        data_dir / "reports/paper_vs_backtest_comparison.md"
    )
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_normalize_and_build_cost_matrix_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_quote = data_dir / "raw/quotes/trade_xyz/2026-05-22.jsonl"
    raw_quote.parent.mkdir(parents=True, exist_ok=True)
    raw_quote.write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"trade_xyz","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.0,"index_price":100.0,"spread_bps":2.0,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"a"}',
                '{"ts_client":"2026-05-22T00:05:00+00:00","venue":"trade_xyz","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.5,"index_price":100.5,"spread_bps":3.0,"market_status":"open","is_tradable":false,"source":"test","raw_payload_sha256":"b"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    normalize = runner.invoke(app, ["normalize-quotes"], env=env)
    build = runner.invoke(app, ["build-cost-matrix"], env=env)

    assert normalize.exit_code == 0
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in normalize.stdout
    assert (data_dir / "normalized/quotes.parquet").exists()
    assert build.exit_code == 0
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in build.stdout
    assert (data_dir / "research/venue_cost_matrix.csv").exists()
    assert (data_dir / "reports/venue_cost_matrix.md").exists()
    assert (data_dir / "ops/venue_cost_matrix_summary.json").exists()
    report = (data_dir / "reports/venue_cost_matrix.md").read_text(encoding="utf-8")
    assert "## Quick Navigation" in report
    summary = read_json(data_dir / "ops/venue_cost_matrix_summary.json")
    assert summary["row_count"] == 1


def test_collect_trade_xyz_quotes_cli(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"NVDA","venue_symbol":"NVDA","asset_class":"equity",'
            '"dex":"xyz","coin":"xyz:NVDA","asset_id":130002,"real_market_symbol":"NVDA",'
            '"api_readable":true,"api_orderable":true,"active":true}]'
        ),
        encoding="utf-8",
    )

    class FakeTradeXyzClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def all_mids(self):
            return {"xyz:NVDA": "1000.0"}

        def l2_book(self, _coin):
            return {
                "levels": [
                    [{"px": "99.9", "sz": "10"}],
                    [{"px": "100.1", "sz": "12"}],
                ]
            }

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", FakeTradeXyzClient)

    result = runner.invoke(app, ["collect-trade-xyz-quotes"], env=env)

    assert result.exit_code == 0
    assert "quote_count=1" in result.stdout
    assert "raw_quotes_path=" in result.stdout
    assert "normalized_quotes_path=" in result.stdout
    assert "duckdb_path=" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "raw/quotes/trade_xyz").exists()
    assert (data_dir / "normalized/quotes.parquet").exists()
    assert (data_dir / "normalized/sis.duckdb").exists()
    rows = list(read_jsonl(next((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))))
    assert len(rows) == 1
    assert rows[0]["venue"] == "trade_xyz"


def test_collect_trade_xyz_quotes_cli_no_normalize(tmp_path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"NVDA","venue_symbol":"NVDA","asset_class":"equity",'
            '"dex":"xyz","coin":"xyz:NVDA","asset_id":130002,"real_market_symbol":"NVDA",'
            '"api_readable":true,"api_orderable":true,"active":true}]'
        ),
        encoding="utf-8",
    )

    class FakeTradeXyzClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def all_mids(self):
            return {"xyz:NVDA": "1000.0"}

        def l2_book(self, _coin):
            return {
                "levels": [
                    [{"px": "99.9", "sz": "10"}],
                    [{"px": "100.1", "sz": "12"}],
                ]
            }

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", FakeTradeXyzClient)

    result = runner.invoke(app, ["collect-trade-xyz-quotes", "--no-normalize"], env=env)

    assert result.exit_code == 0
    assert "quote_count=1" in result.stdout
    assert "normalized_quotes_path=" not in result.stdout
    assert (data_dir / "normalized/quotes.parquet").exists() is False


def test_normalize_trade_xyz_ws_quotes_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"NVDA","venue_symbol":"xyz:NVDA",'
            '"asset_class":"equity","dex":"xyz","coin":"xyz:NVDA","asset_id":130002,'
            '"real_market_symbol":"NVDA","fee_mode":"standard","taker_fee_bps":9.0,'
            '"maker_fee_bps":3.0,"api_readable":true,"api_orderable":true,"active":true}]'
        ),
        encoding="utf-8",
    )
    raw_root = data_dir / "raw/ws/trade_xyz"
    bbo_path = raw_root / "date=2026-06-02/subscription=bbo/symbol=NVDA/part-000001.jsonl"
    bbo_path.parent.mkdir(parents=True, exist_ok=True)
    bbo_path.write_text(
        (
            '{"subscription":"bbo","channel":"bbo","message_kind":"data",'
            '"recv_ts_ms":1780394603762,"source_ts_ms":1780394603466,'
            '"canonical_symbol":"NVDA","venue_symbol":"xyz:NVDA","coin":"xyz:NVDA",'
            '"payload_sha256":"sha256:bbo","payload":{"channel":"bbo","data":'
            '{"coin":"xyz:NVDA","time":1780394603466,"bbo":'
            '[{"px":"100.0","sz":"1.5"},{"px":"100.2","sz":"2.0"}]}}}\n'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["normalize-trade-xyz-ws-quotes"], env=env)

    assert result.exit_code == 0
    assert "quote_count=1" in result.stdout
    assert "normalized_ws_quotes_path=" in result.stdout
    assert "duckdb_path=" in result.stdout
    assert "manifest_path=" in result.stdout
    frame = pl.read_parquet(data_dir / "normalized/trade_xyz_ws_quotes.parquet")
    assert frame.get_column("source").to_list() == ["trade_xyz_ws_bbo"]
    assert frame.get_column("taker_fee_bps").to_list() == [9.0]
    manifest = read_json(data_dir / "normalized/trade_xyz_ws_quotes.manifest.json")
    assert isinstance(manifest, dict)
    assert manifest["quote_count_written"] == 1
    assert manifest["bbo_quote_count"] == 1


def test_collect_trade_xyz_data_cycle_cli_collects_and_rebuilds_readiness(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"NVDA","venue_symbol":"NVDA","asset_class":"equity",'
            '"dex":"xyz","coin":"xyz:NVDA","asset_id":130002,"real_market_symbol":"NVDA",'
            '"fee_mode":"standard","taker_fee_bps":9.0,"maker_fee_bps":3.0,'
            '"external_session":"xnys_regular","internal_session":"trade_xyz_internal",'
            '"api_readable":true,"api_orderable":true,"active":true}]'
        ),
        encoding="utf-8",
    )

    class FakeTradeXyzClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def all_mids(self):
            return {"xyz:NVDA": "1000.0"}

        def meta(self):
            return {"universe": [{"name": "xyz:NVDA"}]}

        def perp_dexs(self):
            return ["xyz"]

        def meta_and_asset_ctxs(self):
            return (
                {"universe": [{"name": "xyz:NVDA"}]},
                [
                    {
                        "markPx": "1000.0",
                        "oraclePx": "1000.0",
                        "oracleTs": "1770000000000",
                        "funding": "0.00001",
                        "openInterest": "10000",
                    }
                ],
            )

        def l2_book(self, _coin):
            return {
                "levels": [
                    [{"px": "999.9", "sz": "10"}],
                    [{"px": "1000.1", "sz": "12"}],
                ]
            }

        def funding_history(self, coin, *, start_time_ms, end_time_ms=None):
            return [
                {
                    "coin": coin,
                    "fundingRate": "0.00001",
                    "premium": "0.00002",
                    "time": start_time_ms,
                }
            ]

        def candle_snapshot(self, coin, interval, start_ms, end_ms):
            return [
                {
                    "t": start_ms,
                    "T": start_ms + 1_799_999,
                    "s": coin,
                    "i": interval,
                    "o": "1000.0",
                    "h": "1001.0",
                    "l": "999.0",
                    "c": "1000.5",
                    "v": "10.0",
                    "n": 1,
                }
            ]

    monkeypatch.setattr("sis.commands.quotes.TradeXyzClient", FakeTradeXyzClient)

    result = runner.invoke(
        app,
        [
            "collect-trade-xyz-data-cycle",
            "--symbols",
            "NVDA",
            "--duration-minutes",
            "1",
            "--interval-seconds",
            "60",
            "--skip-real-market-reference",
            "--signal-candle-request-delay-seconds",
            "0",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "quote_count=1" in result.stdout
    assert "bundle_manifest_path=" in result.stdout
    assert "readiness_decision=NOT_READY" in result.stdout
    assert (data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json").exists()
    assert (data_dir / "manifests/trade_xyz_data_readiness_manifest.json").exists()
    bundle = read_json(data_dir / "manifests/trade_xyz_data_collection_bundle_manifest.json")
    assert bundle["status"] == "completed"
    assert bundle["steps"][0]["name"] == "quote_coverage"


def test_collect_trade_xyz_data_cycle_cli_dry_run(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"NVDA","venue_symbol":"NVDA","asset_class":"equity",'
            '"dex":"xyz","coin":"xyz:NVDA","asset_id":130002,"real_market_symbol":"NVDA",'
            '"api_readable":true,"api_orderable":true,"active":true}]'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["collect-trade-xyz-data-cycle", "--symbols", "NVDA", "--dry-run"],
        env=env,
    )

    assert result.exit_code == 0
    assert "dry_run=true" in result.stdout
    assert "symbols=NVDA" in result.stdout
    assert "registry_refresh=enabled" in result.stdout
    assert "collect_command=uv run sis collect-trade-xyz-quotes" in result.stdout
    assert "request_delay_seconds=1.5" in result.stdout
    assert (
        "follow_up_command=uv run sis build-trade-xyz-data-bundle --auto-funding-window"
        in result.stdout
    )


def test_trade_xyz_collection_status_cli_writes_ops_status(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "raw/quotes/trade_xyz").mkdir(parents=True)
    (data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl").write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    (data_dir / "manifests").mkdir(parents=True)
    (data_dir / "manifests/trade_xyz_quote_coverage_manifest.json").write_text(
        (
            '{"schema_version":"trade_xyz_quote_coverage_manifest.v1",'
            '"coverage_passed":false,"traceable_only":true,"row_count":0,"raw_row_count":0,'
            '"excluded_missing_raw_payload_ref_count":0,'
            '"per_symbol":{"NVDA":{"coverage_status":"insufficient","row_count":0,'
            '"raw_row_count":0,"span_days":0.0,"min_days_required":30.0,'
            '"insufficient_reasons":["span_days_below_min"],"missing_rates":{}}}}'
        ),
        encoding="utf-8",
    )
    (data_dir / "manifests/trade_xyz_data_readiness_manifest.json").write_text(
        '{"decision":"NOT_READY","backtest_data_ready":false,"fail_count":1,"known_gap_count":2}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["trade-xyz-collection-status"], env=env)

    assert result.exit_code == 0
    assert "status_path=" in result.stdout
    assert "decision=COLLECT_MORE_QUOTES" in result.stdout
    assert "fail_count=" in result.stdout
    assert "known_gap_count=" in result.stdout
    assert "failing_requirements=" in result.stdout
    assert "known_gap_requirements=" in result.stdout
    assert "funding_events_status=" in result.stdout
    assert "funding_events_skipped=" in result.stdout
    assert "oracle_timestamp_provenance_status=" in result.stdout
    assert "oracle_ts_missing_rate=" in result.stdout
    assert "signal_candles_status=" in result.stdout
    assert "signal_candles_missing_symbols=" in result.stdout
    assert "signal_candles_missing_intervals=" in result.stdout
    assert "signal_candles_request_error_count=" in result.stdout
    assert "latest_file_stale=False" in result.stdout
    assert "cycle_lock_stale=False" in result.stdout
    assert "supervisor_lock_stale=False" in result.stdout
    assert "aws_cli_available=" in result.stdout
    assert "aws_command_source=" in result.stdout
    assert "lz4_available=" in result.stdout
    assert "historical_archive_bulk_plan_exists=False" in result.stdout
    assert "historical_archive_bulk_execution_status=None" in result.stdout
    assert "historical_archive_bulk_normalization_status=None" in result.stdout
    assert "account_fee_user_address_configured=False" in result.stdout
    assert "account_fee_manifest_exists=False" in result.stdout
    assert "account_fee_manifest_status=None" in result.stdout
    assert "account_fee_manifest_user_matches_env=None" in result.stdout
    assert "account_fee_user_taker_fee_bps=None" in result.stdout
    assert "account_fee_user_maker_fee_bps=None" in result.stdout
    assert "progress_status=" in result.stdout
    assert "coverage_completion_ratio_by_span=" in result.stdout
    assert "next_command=uv run sis collect-trade-xyz-data-cycle" in result.stdout
    assert "next_action_1_key=collect_trade_xyz_data_cycle" in result.stdout
    assert "next_action_2_key=historical_archive_backfill" in result.stdout
    assert "next_action_2_preflight_command=" in result.stdout
    assert (
        "next_action_2_dry_run_command=uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10"
        in result.stdout
    )
    assert (
        "next_action_2_execute_command=uv run sis execute-trade-xyz-historical-archive-bulk --execute --acknowledge-requester-pays --max-objects 10"
        in result.stdout
    )
    assert (
        "next_action_2_follow_up_command=uv run sis normalize-trade-xyz-historical-archive-bulk"
        in result.stdout
    )
    payload = read_json(data_dir / "ops/trade_xyz_collection_status.json")
    assert payload["decision"] == "COLLECT_MORE_QUOTES"
    assert "readiness_requirement_details" in payload
    assert payload["account_fee_prerequisites"]["configured"] is False
    assert payload["account_fee_artifact"]["exists"] is False
    assert payload["account_fee_artifact"]["status"] is None
    assert payload["account_fee_artifact"]["matches_configured_user"] is None
    assert payload["historical_archive_artifacts"]["bulk_plan"]["exists"] is False
    assert payload["historical_archive_artifacts"]["bulk_execution"]["exists"] is False
    assert payload["historical_archive_artifacts"]["bulk_normalization"]["exists"] is False
    assert payload["latest_file_stale"] is False
    assert payload["raw_quote_inventory"]["latest_file_age_seconds"] is not None
    assert payload["raw_quote_inventory"]["traceable_row_count"] == 1
    assert payload["coverage_refresh"]["status"] == "completed"
    assert payload["readiness_refresh"]["status"] == "completed"
    assert payload["coverage"]["row_count"] == 1
    assert (data_dir / "reports/trade_xyz_collection_status.md").exists()


def test_collect_trade_xyz_historical_l2_archive_cli_dry_run(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}

    result = runner.invoke(
        app,
        [
            "collect-trade-xyz-historical-l2-archive",
            "--coin",
            "xyz:XYZ100",
            "--date",
            "2026-05-01",
            "--hour",
            "9",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "status=planned" in result.stdout
    assert (
        "s3_uri=s3://hyperliquid-archive/market_data/20260501/9/l2Book/xyz:XYZ100.lz4"
        in result.stdout
    )
    payload = read_json(data_dir / "manifests/trade_xyz_historical_l2_archive_manifest.json")
    assert payload["dry_run"] is True
    assert payload["requester_pays_acknowledged"] is False


def test_collect_trade_xyz_historical_asset_ctxs_archive_cli_dry_run(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}

    result = runner.invoke(
        app,
        [
            "collect-trade-xyz-historical-asset-ctxs-archive",
            "--date",
            "2026-05-01",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "status=planned" in result.stdout
    assert "s3_uri=s3://hyperliquid-archive/asset_ctxs/20260501.csv.lz4" in result.stdout
    payload = read_json(
        data_dir / "manifests/trade_xyz_historical_asset_ctxs_archive_manifest.json"
    )
    assert payload["dry_run"] is True
    assert payload["requester_pays_acknowledged"] is False


def test_normalize_trade_xyz_historical_archive_quotes_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    l2_path = data_dir / "raw/historical_archive/hyperliquid/example.jsonl"
    ctx_path = data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"XYZ100","venue_symbol":"XYZ100",'
            '"asset_class":"basket_index","dex":"xyz","coin":"xyz:XYZ100","asset_id":100,'
            '"fee_mode":"standard","taker_fee_bps":9.0,"maker_fee_bps":3.0,"active":true}]'
        ),
        encoding="utf-8",
    )
    l2_path.parent.mkdir(parents=True, exist_ok=True)
    l2_path.write_text(
        (
            '{"coin":"xyz:XYZ100","time":1770000000000,'
            '"levels":[[{"px":"99.9","sz":"10"}],[{"px":"100.1","sz":"12"}]]}\n'
        ),
        encoding="utf-8",
    )
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(
        "coin,markPx,oraclePx,funding,openInterest,oracleTs\n"
        "xyz:XYZ100,100.2,100.1,-0.00001,1234,1770000000000\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "normalize-trade-xyz-historical-archive-quotes",
            "--l2-jsonl-path",
            str(l2_path),
            "--asset-ctxs-path",
            str(ctx_path),
            "--coin",
            "xyz:XYZ100",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "rows_written=1" in result.stdout
    assert "asset_ctx_matched=True" in result.stdout
    payload = read_json(
        data_dir / "manifests/trade_xyz_historical_archive_quote_normalization_manifest.json"
    )
    assert payload["rows_written"] == 1


def test_plan_trade_xyz_historical_archive_bulk_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"

    result = runner.invoke(
        app,
        [
            "plan-trade-xyz-historical-archive-bulk",
            "--coins",
            "xyz:XYZ100,xyz:SP500",
            "--start-date",
            "2026-05-01",
            "--end-date",
            "2026-05-02",
            "--hours",
            "0,12",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "estimated_l2_object_count=8" in result.stdout
    assert "estimated_asset_ctx_object_count=2" in result.stdout
    assert "requester_pays_ack_required=True" in result.stdout
    payload = read_json(data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json")
    assert payload["estimated_total_object_count"] == 10


def test_execute_trade_xyz_historical_archive_bulk_cli_dry_run(tmp_path) -> None:
    data_dir = tmp_path / "data"
    plan_dir = data_dir / "manifests"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / "trade_xyz_historical_archive_bulk_plan_manifest.json"
    plan_path.write_text(
        (
            '{"schema_version":"trade_xyz_historical_archive_bulk_plan_manifest.v1",'
            '"l2_objects":[{"destination":"'
            + str(data_dir / "raw/historical_archive/example.lz4")
            + '","download_command":["aws","s3","cp","s3://bucket/key","'
            + str(data_dir / "raw/historical_archive/example.lz4")
            + '","--request-payer","requester"]}],'
            '"asset_ctx_objects":[]}'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "execute-trade-xyz-historical-archive-bulk",
            "--plan-path",
            str(plan_path),
            "--max-objects",
            "1",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "status=planned" in result.stdout
    assert "selected_object_count=1" in result.stdout
    assert "downloaded_object_count=0" in result.stdout


def test_check_trade_xyz_historical_archive_preflight_cli_records_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"

    result = runner.invoke(
        app,
        ["check-trade-xyz-historical-archive-preflight"],
        env={"SIS_DATA_DIR": str(data_dir), "SIS_AWS_COMMAND": "false"},
    )

    assert result.exit_code == 0
    assert "status=fail" in result.stdout
    assert "return_code=1" in result.stdout
    payload = read_json(data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json")
    assert payload["status"] == "fail"
    assert payload["aws_command_source"] == "SIS_AWS_COMMAND"


def test_normalize_trade_xyz_historical_archive_bulk_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    l2_path = (
        data_dir
        / "raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl"
    )
    ctx_path = data_dir / "raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"XYZ100","venue_symbol":"XYZ100",'
            '"asset_class":"basket_index","dex":"xyz","coin":"xyz:XYZ100","asset_id":100,'
            '"fee_mode":"standard","taker_fee_bps":9.0,"maker_fee_bps":3.0,"active":true}]'
        ),
        encoding="utf-8",
    )
    l2_path.parent.mkdir(parents=True, exist_ok=True)
    l2_path.write_text(
        (
            '{"coin":"xyz:XYZ100","time":1770000000000,'
            '"levels":[[{"px":"99.9","sz":"10"}],[{"px":"100.1","sz":"12"}]]}\n'
        ),
        encoding="utf-8",
    )
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(
        "coin,markPx,oraclePx,funding,openInterest,oracleTs\n"
        "xyz:XYZ100,100.2,100.1,-0.00001,1234,1770000000000\n",
        encoding="utf-8",
    )
    plan_path = data_dir / "manifests/trade_xyz_historical_archive_bulk_plan_manifest.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        (
            '{"schema_version":"trade_xyz_historical_archive_bulk_plan_manifest.v1",'
            '"l2_objects":[{"date":"2026-05-01","hour":9,"coin":"xyz:XYZ100",'
            '"decompressed_path":"' + str(l2_path) + '"}],'
            '"asset_ctx_objects":[{"date":"2026-05-01","decompressed_path":"'
            + str(ctx_path)
            + '"}]}'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "normalize-trade-xyz-historical-archive-bulk",
            "--plan-path",
            str(plan_path),
            "--registry-path",
            str(registry_path),
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "normalized_file_count=1" in result.stdout
    assert "rows_written=1" in result.stdout
    payload = read_json(
        data_dir / "manifests/trade_xyz_historical_archive_bulk_quote_normalization_manifest.json"
    )
    assert payload["normalized_file_count"] == 1
    assert (
        data_dir / "raw/quotes/trade_xyz/historical_archive_20260501_9_xyz_XYZ100.jsonl"
    ).exists()


def test_trade_xyz_collection_status_cli_can_fail_on_stale(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    old_time = time.time() - 7200
    os.utime(raw_path, (old_time, old_time))

    result = runner.invoke(
        app,
        ["trade-xyz-collection-status", "--stale-after-minutes", "1", "--fail-on-stale"],
        env=env,
    )

    assert result.exit_code == 2
    assert "latest_file_stale=True" in result.stdout
    payload = read_json(data_dir / "ops/trade_xyz_collection_status.json")
    assert payload["latest_file_stale"] is True


def test_trade_xyz_collection_status_cli_can_fail_on_lock_stale(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    cycle_lock = tmp_path / ".tmp/trade_xyz_data_cycle.lock"
    cycle_lock.mkdir(parents=True)
    (cycle_lock / "pid").write_text("99999999\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["trade-xyz-collection-status", "--fail-on-lock-stale"],
        env=env,
    )

    assert result.exit_code == 2
    assert "cycle_lock_stale=True" in result.stdout
    payload = read_json(data_dir / "ops/trade_xyz_collection_status.json")
    assert payload["locks"]["cycle"]["stale"] is True


def test_trade_xyz_collection_status_cli_can_fail_on_progress_warning(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    (data_dir / "ops").mkdir(parents=True)
    (data_dir / "ops/trade_xyz_collection_status.json").write_text(
        (
            '{"generated_at":"2026-05-31T00:00:00+00:00",'
            '"raw_quote_inventory":{"row_count":1,"traceable_row_count":1}}'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "trade-xyz-collection-status",
            "--no-refresh-coverage",
            "--no-refresh-readiness",
            "--interval-seconds",
            "1",
            "--stale-after-minutes",
            "-1",
            "--fail-on-progress-warning",
        ],
        env=env,
    )

    assert result.exit_code == 2
    assert "progress_status=warning" in result.stdout
    payload = read_json(data_dir / "ops/trade_xyz_collection_status.json")
    assert "latest_file_stale" in payload["progress_since_previous_status"]["warnings"]


def test_trade_xyz_collection_status_cli_can_fail_on_archive_preflight(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    (data_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (data_dir / "manifests/trade_xyz_historical_archive_preflight_manifest.json").write_text(
        (
            '{"schema_version":"trade_xyz_historical_archive_preflight_manifest.v1",'
            '"status":"fail","return_code":255,"aws_command_source":"fixture"}'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["trade-xyz-collection-status", "--fail-on-archive-preflight"],
        env=env,
    )

    assert result.exit_code == 2
    assert "next_action_2_blocked_by=aws_preflight_failed" in result.stdout
    assert "next_action_2_preflight_status=fail" in result.stdout


def test_trade_xyz_collection_status_cli_can_fail_on_account_fee_missing(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    (data_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (data_dir / "manifests/fee_manifest.json").write_text(
        (
            '{"schema_version":"fee_manifest.v1","fee_snapshot_count":1,'
            '"unresolved_symbol_count":0,'
            '"account_specific_fee_status":"not_collected_no_wallet_or_user_context"}'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["trade-xyz-collection-status", "--fail-on-account-fee-missing"],
        env=env,
    )

    assert result.exit_code == 2
    assert "known_gap_requirements=account_specific_fee" in result.stdout
    assert "account_fee_user_address_configured=False" in result.stdout
    assert "account_fee_manifest_exists=False" in result.stdout


def test_trade_xyz_collection_status_cli_account_fee_flag_checks_artifact_directly(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_path = data_dir / "raw/quotes/trade_xyz/2026-05-31.jsonl"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        (
            '{"ts_client":"2026-05-31T00:00:00+00:00","venue":"trade_xyz",'
            '"canonical_symbol":"NVDA","venue_symbol":"NVDA","source":"test",'
            '"raw_payload_sha256":"a","raw_payload_ref":"fixture://row0"}\n'
        ),
        encoding="utf-8",
    )
    (data_dir / "manifests").mkdir(parents=True, exist_ok=True)
    (data_dir / "manifests/trade_xyz_data_readiness_manifest.json").write_text(
        (
            '{"decision":"NOT_READY","backtest_data_ready":false,'
            '"fail_count":1,"known_gap_count":0,'
            '"requirements":[{"key":"quote_coverage","status":"fail"}]}'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "trade-xyz-collection-status",
            "--no-refresh-readiness",
            "--fail-on-account-fee-missing",
        ],
        env=env,
    )

    assert result.exit_code == 2
    assert "known_gap_requirements=" in result.stdout
    assert "account_fee_manifest_exists=False" in result.stdout
    assert "account_fee_manifest_status=None" in result.stdout


def test_collect_trade_xyz_quotes_cli_exits_when_registry_missing(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["collect-trade-xyz-quotes"],
        env={"SIS_DATA_DIR": str(tmp_path / "data")},
    )

    assert result.exit_code == 2
    assert "trade_xyz registry not found" in result.stdout
    assert "probe trade-xyz" in result.stdout


def test_collect_trade_xyz_quotes_cli_exits_when_no_active_instruments(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"NVDA","venue_symbol":"NVDA","asset_class":"equity",'
            '"dex":"xyz","coin":"xyz:NVDA","asset_id":130002,"real_market_symbol":"NVDA",'
            '"api_readable":true,"api_orderable":true,"active":false}]'
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["collect-trade-xyz-quotes"], env=env)

    assert result.exit_code == 2
    assert "no active trade_xyz instruments found in registry" in result.stdout


def test_bot_preview_cli_writes_hold_outputs(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "raw/quotes/trade_xyz").mkdir(parents=True, exist_ok=True)
    (data_dir / "raw/quotes/trade_xyz/2026-05-27.jsonl").write_text(
        '{"venue":"trade_xyz","canonical_symbol":"SP500"}\n',
        encoding="utf-8",
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"phase_gate_decision":"READ_ONLY_GO","phase2_entry_allowed":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/trade_xyz_quote_collection_summary.json").write_text(
        '{"venue":"trade_xyz","row_count":1,"collected_symbols":["SP500"]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["bot-preview"], env=env)

    assert result.exit_code == 0
    assert "decision=HOLD" in result.stdout
    assert "BOT_ORDER_LOGIC_NOT_IMPLEMENTED" in result.stdout
    assert (data_dir / "bot/bot_decision.json").exists()
    assert (data_dir / "reports/bot_orders_preview.md").exists()
    payload = read_json(data_dir / "bot/bot_decision.json")
    assert payload["decision"] == "HOLD"
    assert payload["reason_codes"] == ["BOT_ORDER_LOGIC_NOT_IMPLEMENTED"]


def test_bot_preview_cli_fail_on_not_ready_exits_2(tmp_path) -> None:
    data_dir = tmp_path / "data"
    result = runner.invoke(
        app,
        ["bot-preview", "--fail-on-not-ready"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 2
    assert "MISSING_PHASE_GATE_SUMMARY" in result.stdout
    assert (data_dir / "bot/bot_decision.json").exists()


def test_build_event_calendar_and_check_research_quality_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "research").mkdir(parents=True, exist_ok=True)

    csv_path = data_dir / "research/event_calendar.csv"
    csv_path.write_text(
        "event_ts,event_name,event_class,importance,before_minutes,after_minutes,action\n"
        "2026-01-20T18:00:00+00:00,FOMC,central_bank,high,180,120,BLOCK\n",
        encoding="utf-8",
    )
    pl.DataFrame(
        [
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "symbol": "QQQ",
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.5,
                "volume": 1000,
                "provider_symbol": "QQQ",
                "interval": "1d",
                "adjustment": "none",
            }
        ]
    ).write_parquet(data_dir / "research/market_panel.parquet")
    pl.DataFrame(
        [
            {
                "date": datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
                "series_id": "DGS10",
                "value": 4.0,
                "provider": "fake",
                "vintage_mode": "latest",
                "realtime_start": None,
                "realtime_end": None,
            }
        ]
    ).write_parquet(data_dir / "research/macro_panel.parquet")
    pl.DataFrame(
        [
            {
                "ts": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "canonical_symbol": "QQQ",
                "close": 100.5,
                "dgs10": 4.0,
                "vix_level": 20.0,
                "trade_allowed": True,
            }
        ]
    ).write_parquet(data_dir / "research/feature_panel.parquet")
    (data_dir / "research/signals.csv").write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength,strategy_name,reason\n"
        "2026-01-01T00:00:00+00:00,QQQ,long,4h,1.0,qqq_trend_rates_vix,test\n",
        encoding="utf-8",
    )

    event_calendar = runner.invoke(app, ["build-event-calendar"], env=env)
    quality = runner.invoke(app, ["check-research-quality"], env=env)

    assert event_calendar.exit_code == 0
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in event_calendar.stdout
    assert (data_dir / "research/event_calendar.parquet").exists()
    assert quality.exit_code == 0
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in quality.stdout
    assert (data_dir / "research/research_quality_report.json").exists()


def test_check_halt_policy_and_validate_artifacts_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry_dir = data_dir / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / "gtrade_instrument_registry.json").write_text(
        '[{"venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","asset_class":"index","pair_index":86,"api_readable":true,"api_orderable":true,"active":true,"notes":[]}]',
        encoding="utf-8",
    )
    (registry_dir / "ostium_instrument_registry.json").write_text(
        '[{"venue":"ostium","canonical_symbol":"SPY","venue_symbol":"SPY/USD","asset_class":"index","pair_index":86,"api_readable":true,"api_orderable":true,"active":true,"notes":[]}]',
        encoding="utf-8",
    )
    quote_path = data_dir / "raw/quotes/gtrade/2026-05-22.jsonl"
    quote_path.parent.mkdir(parents=True, exist_ok=True)
    quote_path.write_text(
        '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.0,"index_price":100.0,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"abc"}\n',
        encoding="utf-8",
    )
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/backtest_metrics.json").write_text(
        '[{"timeframe":"4h","trade_count":10,"avg_trade_return":0.1}]',
        encoding="utf-8",
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    evidence_path = data_dir / "evidence/evidence_card_20260522_000000.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        '{"run_id":"20260522_000000","created_at":"2026-05-22T00:00:00+00:00","scope":{"venues":["gtrade"],"symbols":["SPY"],"timeframes":["4h"],"scalping_policy":"prohibited_by_default"},"data":{},"decision":"GO","criteria":[],"blockers":[],"next_actions":[]}',
        encoding="utf-8",
    )

    halt = runner.invoke(app, ["check-halt-policy"], env=env)
    validate = runner.invoke(app, ["validate-artifacts"], env=env)

    assert halt.exit_code == 0
    assert "trade_xyz_max_age_ms=" in halt.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in halt.stdout
    assert validate.exit_code == 0
    assert "checked_files=6" in validate.stdout
    assert "issues=0" in validate.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in validate.stdout


def test_phase_gate_review_cli(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    env = {"SIS_DATA_DIR": str(tmp_path / "data")}
    data_dir = tmp_path / "data"
    (data_dir / "registry").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "evidence").mkdir(parents=True, exist_ok=True)
    (data_dir / "raw/quotes/gtrade").mkdir(parents=True, exist_ok=True)
    (data_dir / "registry/gtrade_instrument_registry.json").write_text(
        '[{"venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","asset_class":"index","pair_index":86,"api_readable":true,"api_orderable":true,"active":true,"notes":[]}]',
        encoding="utf-8",
    )
    (data_dir / "registry/ostium_instrument_registry.json").write_text(
        '[{"venue":"ostium","canonical_symbol":"SPY","venue_symbol":"SPY/USD","asset_class":"index","pair_index":86,"api_readable":true,"api_orderable":true,"active":true,"notes":[]}]',
        encoding="utf-8",
    )
    (data_dir / "raw/quotes/gtrade/2026-05-22.jsonl").write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"QQQ","venue_symbol":"QQQ/USD","mark_price":100.0,"index_price":100.0,"spread_bps":2.0,"oracle_ts_ms":1779407999000,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"qqq"}',
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","mark_price":101.0,"index_price":101.0,"spread_bps":2.0,"oracle_ts_ms":1779407999000,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"spy"}',
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"XAU","venue_symbol":"XAU/USD","mark_price":102.0,"index_price":102.0,"spread_bps":3.0,"oracle_ts_ms":1779407999000,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"xau"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (data_dir / "research/backtest_metrics.json").write_text(
        '[{"timeframe":"4h","trade_count":10,"avg_trade_return":0.1}]',
        encoding="utf-8",
    )
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"entry_count":2,"latest_status_match":true,"mismatching_count":0}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "evidence/evidence_card_20260522_000000.json").write_text(
        '{"run_id":"20260522_000000","created_at":"2026-05-22T00:00:00+00:00","scope":{"venues":["gtrade"],"symbols":["QQQ","SPY","XAU"],"timeframes":["4h"],"scalping_policy":"prohibited_by_default"},"data":{},"decision":"GO","venue_decisions":[{"venue":"gtrade","decision":"GO","main_blocker":null}],"criteria":[],"blockers":[],"next_actions":["proceed_to_phase2"]}',
        encoding="utf-8",
    )
    manifest_path = tmp_path / "logs/live_evidence/manifests/live_evidence_20260522_2308.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        '{"run_id":"20260522_2308","status":"completed","decision":"GO","artifacts":{"evidence_card":"data/evidence/evidence_card_20260522_000000.json"}}',
        encoding="utf-8",
    )
    gtrade_backend_manifest_path = (
        data_dir / "raw/sidecar/gtrade-backend/manifests/2026-05-22/backend_r1.json"
    )
    gtrade_backend_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    gtrade_backend_manifest_path.write_text(
        '{"status":"completed","backend_ws_path":"data/raw/sidecar/gtrade-backend/backend-ws/r1.jsonl","rest_snapshot_paths":["data/raw/sidecar/gtrade-backend/rest/r1_trading_variables.json","data/raw/sidecar/gtrade-backend/rest/r1_open_trades.json"],"event_count":10,"reconnect_count":0,"deep_reorg_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/ostium_constraints_r1.json").write_text(
        '{"constraint_status":"pass","failures":[],"python_sdk":{"available":true,"version":"3.2.1"}}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["phase-gate-review"], env=env)

    assert result.exit_code == 0
    assert "Phase Gate Review" in result.stdout
    assert "phase2_entry_allowed: False" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_comparison_all_registries_present: True" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_gap_history_latest_status: ok" in result.stdout
    assert "execution_gap_history_latest_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "## Required Artifacts" in result.stdout
    assert "missing_required_artifact_paths:" in result.stdout
    assert "latest_trade_xyz_registry_path" in result.stdout
    assert "latest_trade_xyz_quote_path" in result.stdout
    assert "latest_trade_xyz_summary_path" in result.stdout
    assert "## Recovery Commands" in result.stdout
    assert "`uv run sis probe trade-xyz`" in result.stdout
    assert "`uv run sis collect-trade-xyz-quotes --write-summary --write-report`" in result.stdout
    assert "## Remediation Order" in result.stdout
    assert "priority_1: missing_required_artifacts" in result.stdout
    assert "priority_2: strict_validation_failed" in result.stdout
    assert "priority_4: execution_drift_unresolved" in result.stdout
    assert "## Remediation Success Criteria" in result.stdout
    assert "execution_drift_overview_status == ok" in result.stdout
    assert "## Remediation Command Flow" in result.stdout
    assert "`uv run sis phase-gate-review`" in result.stdout
    assert "## Remediation Verification Signals" in result.stdout
    assert "preflight_expected_output:" in result.stdout
    assert "postcheck_pass_signal:" in result.stdout
    assert "## Remediation Signal Snapshots" in result.stdout
    assert "target:" in result.stdout
    assert "## Remediation Signal Diffs" in result.stdout
    assert "## Remediation Recommendations" in result.stdout
    assert "## Stop Conditions" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "phase_gate_review_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "go_no_go_report:" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/phase_gate_review.md").exists()
    assert (data_dir / "ops/phase_gate_review_summary.json").exists()


def test_ops_review_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        '{"operation":"daemon_dry_run","status":"planned","scheduled_for":"2026-05-24T12:30:00+00:00","command":"uv run sis paper-step","artifacts":["a.json"],"notes":["dry_run"]}\n',
        encoding="utf-8",
    )
    (data_dir / "ops/monitoring_status.json").write_text('{"status":"ok"}', encoding="utf-8")
    (data_dir / "ops/daemon_dry_run.json").write_text('{"status":"planned"}', encoding="utf-8")
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot"}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["ops-review"], env=env)

    assert result.exit_code == 0
    assert "Ops Review Report" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "audit_latest_operation: audit_bundle_snapshot" in result.stdout
    assert "execution_drift_overview_status: degraded" in result.stdout
    assert "readiness_next_phase_candidate: Stay Phase 1" in result.stdout
    assert "phase_gate_strict_validation_passed: None" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "ops_review_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "operations_dashboard_report:" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/ops_review_report.md").exists()
    assert (data_dir / "ops/ops_review_summary.json").exists()


def test_operations_dashboard_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/monitoring_status.json").write_text(
        '{"status":"ok","decision_summary_exists":true,"daily_pnl_exists":false,"operation_chain_exists":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/ops_review_summary.json").write_text(
        '{"operations_count":1,"latest_operation":"daemon_dry_run","latest_status":"planned","latest_scheduled_for":"2026-05-24T12:30:00+00:00"}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot","audit_entry_count":4,"audit_bundle_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3,"bundle_history_ok_count":3}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        encoding="utf-8",
    )
    (data_dir / "research/decision_summary.json").write_text(
        '{"mode":"signal_driven","executed_count":1,"blocked_count":0}',
        encoding="utf-8",
    )
    (data_dir / "reports/paper_vs_backtest_comparison.md").write_text(
        "# comparison\n", encoding="utf-8"
    )
    (data_dir / "reports/weekly_strategy_review.md").write_text("# weekly\n", encoding="utf-8")
    (data_dir / "reports/strategy_lifecycle_report.md").write_text(
        "# lifecycle\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["operations-dashboard"], env=env)

    assert result.exit_code == 0
    assert "Operations Dashboard" in result.stdout
    assert "Recommended Read Order" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "operations_dashboard_report:" in result.stdout
    assert "phase_gate_review_report: data/reports/phase_gate_review.md" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "current_state_index_report:" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_comparison_all_registries_present: True" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "audit_latest_operation: audit_bundle_snapshot" in result.stdout
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/operations_dashboard.md").exists()
    assert (data_dir / "ops/operations_dashboard_summary.json").exists()
    assert '"recommended_read_order"' in (
        data_dir / "ops/operations_dashboard_summary.json"
    ).read_text(encoding="utf-8")


def test_paper_operations_runbook_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/scheduled_run.json").write_text(
        '{"run_type":"paper","scheduled_for":"2026-05-24T12:30:00+00:00","command":"uv run sis paper-step"}',
        encoding="utf-8",
    )
    (data_dir / "ops/daemon_manifest.json").write_text(
        '{"mode":"paper","command":"uv run sis paper-step","state_store_path":"data/state/marketlens.sqlite"}',
        encoding="utf-8",
    )
    (data_dir / "ops/monitoring_status.json").write_text('{"status":"ok"}', encoding="utf-8")
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"all_registries_present":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/operations_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"timeline_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":true},"bundle_history_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"bundle_history_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":true},"cycle_history_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"cycle_history_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":true},"timeline_latest_remediation_planner_status":"stalled","timeline_latest_remediation_planner_next_best_command":"uv run sis validate-artifacts --strict","timeline_latest_remediation_planner_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_execution_plan_status":"stalled","timeline_latest_remediation_execution_plan_next_action_command":"uv run sis diagnose-quotes","timeline_latest_remediation_execution_plan_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_session_status":"ready_for_dry_run","timeline_latest_remediation_session_next_pending_command":"uv run sis monitoring-status","timeline_latest_remediation_session_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_checkpoint_status":"retry_pending","timeline_latest_remediation_checkpoint_next_action_command":"uv run sis phase-gate-review","timeline_latest_remediation_checkpoint_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_scoreboard_status":"retrying","timeline_latest_remediation_scoreboard_next_action_command":"uv run sis phase-gate-review","timeline_latest_remediation_scoreboard_feedback_priority_reason":"evaluation_failed"}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["paper-operations-runbook"], env=env)

    assert result.exit_code == 0
    assert "Scheduled Paper Operations Runbook" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_comparison_all_registries_present: True" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_balance_gap_detected: True" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_gap_history_latest_status: ok" in result.stdout
    assert "execution_gap_history_latest_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "readiness_next_phase_candidate: Stay Phase 1" in result.stdout
    assert "readiness_execution_ready: False" in result.stdout
    assert "phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "phase_gate_checked_files: 7" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "## Required Artifacts" in result.stdout
    assert "missing_required_artifact_paths: none" in result.stdout
    assert "## Recovery Commands" in result.stdout
    assert "recovery_commands: none" in result.stdout
    assert "## Remediation Order" in result.stdout
    assert "priority_2: strict_validation_failed" in result.stdout
    assert "## Remediation Success Criteria" in result.stdout
    assert "phase_gate_strict_validation_issue_count == 0" in result.stdout
    assert "## Remediation Command Flow" in result.stdout
    assert "`uv run sis validate-artifacts --strict`" in result.stdout
    assert "`uv run sis paper-operations-runbook`" in result.stdout
    assert "## Remediation Verification Signals" in result.stdout
    assert "execute_expected_output:" in result.stdout
    assert "postcheck_pass_signal:" in result.stdout
    assert "## Remediation Signal Snapshots" in result.stdout
    assert "before:" in result.stdout
    assert "## Remediation Signal Diffs" in result.stdout
    assert "## Remediation Recommendations" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "Latest Execution Lineage" in result.stdout
    assert "timeline_latest_execution_overall_status: ok" in result.stdout
    assert "bundle_history_latest_execution_overall_status: ok" in result.stdout
    assert "cycle_history_latest_execution_overall_status: ok" in result.stdout
    assert "timeline_latest_remediation_planner_status: stalled" in result.stdout
    assert (
        "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status"
        in result.stdout
    )
    assert (
        "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed"
        in result.stdout
    )
    assert "## Quick Navigation" in result.stdout
    assert "paper_operations_runbook_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "paper_operations_runbook_report:" in result.stdout
    assert "phase_gate_review_report: data/reports/phase_gate_review.md" in result.stdout
    assert "Review `data/reports/remediation_scoreboard.md`" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/paper_operations_runbook.md").exists()
    assert (data_dir / "ops/paper_operations_runbook_summary.json").exists()
    assert '"execution_summary"' in (
        data_dir / "ops/paper_operations_runbook_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_gap_history_summary"' in (
        data_dir / "ops/paper_operations_runbook_summary.json"
    ).read_text(encoding="utf-8")
    assert '"execution_state_comparison_summary"' in (
        data_dir / "ops/paper_operations_runbook_summary.json"
    ).read_text(encoding="utf-8")


def test_remediation_planner_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_planner_summary.json").write_text(
        '{"planner_status":"regressed","planned_step_count":3,"next_best_command":"uv run sis refresh-operations-artifacts","recommended_command_chain":["uv run sis refresh-operations-artifacts","uv run sis phase-gate-review"],"entries":[{"source":"paper_operations_runbook","priority":2,"reason":"strict_validation_failed","status":"regressed","why":"signals regressed away from target","commands":["uv run sis validate-artifacts --strict"]}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        '{"run_id":"20260524_010203","created_at":"2026-05-24T01:02:03+00:00","operation":"remediation_planner_dry_run","mode":"ops","command":"uv run sis remediation-planner","status":"regressed","scheduled_for":null,"parent_run_id":null,"artifacts":["data/ops/remediation_planner_summary.json"],"notes":["planner_status=regressed","rerun_trend=regressed","planned_step_count=3","next_best_command=uv run sis refresh-operations-artifacts"]}\n',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"remediation_order":[{"priority":4,"reason":"execution_drift_unresolved","commands":["uv run sis refresh-operations-artifacts"]}],"remediation_recommendations":{"execution_drift_unresolved":{"status":"improving","why":"signals changed but target is not fully matched yet","commands":["uv run sis refresh-operations-artifacts"]}}}',
        encoding="utf-8",
    )
    (data_dir / "ops/paper_operations_runbook_summary.json").write_text(
        '{"remediation_order":[{"priority":2,"reason":"strict_validation_failed","commands":["uv run sis validate-artifacts --strict"]}],"remediation_recommendations":{"strict_validation_failed":{"status":"stalled","why":"signals did not move toward target","commands":["uv run sis validate-artifacts --strict"]}}}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_evaluator_summary.json").write_text(
        '{"actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","source":"paper_operations_runbook","reason":"strict_validation_failed","evaluation_result":"fail","signal_evaluations":[{"signal":"validate-artifacts --strict reports the current issue count","observed_source":"stdout_stderr"}]}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_command_results_summary.json").write_text(
        '{"entries":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","observation_status":"observed"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-planner"], env=env)

    assert result.exit_code == 0
    assert "Remediation Planner Dry Run" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_planner_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_execution_plan_report:" in result.stdout
    assert "planner_status: stalled" in result.stdout
    assert "## Planner Rerun Diff" in result.stdout
    assert "- trend: improved" in result.stdout
    assert "source_confidence: high" in result.stdout
    assert "observed_sources: ['stdout_stderr']" in result.stdout
    assert "feedback_priority_reason: evaluation_failed" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/remediation_planner.md").exists()
    assert (data_dir / "ops/remediation_planner_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_planner_dry_run"
    assert latest["status"] == "stalled"
    assert "planner_status=stalled" in latest["notes"]
    assert "rerun_trend=improved" in latest["notes"]


def test_remediation_execution_plan_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"remediation_preflight_commands":{"execution_drift_unresolved":["uv run sis diagnose-quotes"]},"remediation_postcheck_commands":{"execution_drift_unresolved":["uv run sis phase-gate-review"]},"remediation_preflight_expected_outputs":{"execution_drift_unresolved":["diagnose-quotes prints per-symbol diagnostics rows"]},"remediation_execute_expected_outputs":{"execution_drift_unresolved":["execution_drift_overview_status == ok","execution_drift_overview_summary.json is regenerated"]},"remediation_postcheck_pass_signals":{"execution_drift_unresolved":["execution_drift_overview_status == ok"]}}',
        encoding="utf-8",
    )
    (data_dir / "ops/paper_operations_runbook_summary.json").write_text(
        '{"remediation_preflight_commands":{"strict_validation_failed":["uv run sis validate-artifacts --strict"]},"remediation_postcheck_commands":{"strict_validation_failed":["uv run sis paper-operations-runbook"]},"remediation_preflight_expected_outputs":{"strict_validation_failed":["validate-artifacts --strict reports the current issue count"]},"remediation_execute_expected_outputs":{"strict_validation_failed":["strict validation output reports issues=0"]},"remediation_postcheck_pass_signals":{"strict_validation_failed":["phase_gate_strict_validation_issue_count == 0"]}}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_planner_summary.json").write_text(
        '{"planner_status":"stalled","planner_rerun_diff":{"trend":"improved"},"phase_gate_summary_path":"'
        + str(data_dir / "ops/phase_gate_review_summary.json").replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(data_dir / "ops/paper_operations_runbook_summary.json").replace("\\", "\\\\")
        + '","entries":[{"source":"paper_operations_runbook","priority":2,"effective_priority":1,"reason":"strict_validation_failed","status":"stalled","why":"signals did not move toward target","commands":["uv run sis validate-artifacts --strict"],"observed_sources":["stdout_stderr"],"source_confidence":"high","source_policy":"direct_observation_priority","feedback_priority_reason":"verification_passed","signal_observed_sources":{"validate-artifacts --strict reports the current issue count":"stdout_stderr"}},{"source":"phase_gate_review","priority":4,"effective_priority":5,"reason":"execution_drift_unresolved","status":"improving","why":"signals changed but target is not fully matched yet","commands":["uv run sis refresh-operations-artifacts"],"observed_sources":["markdown_reports"],"source_confidence":"low","source_policy":"verify_before_execute","feedback_priority_reason":"evaluation_failed","signal_observed_sources":{"execution_drift_overview_status == ok":"markdown_reports","execution_drift_overview_summary.json is regenerated":"stdout_stderr"}}],"planner_entry_diffs":{"paper_operations_runbook:strict_validation_failed":{"trend":"regressed"},"phase_gate_review:execution_drift_unresolved":{"trend":"improved"}}}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-execution-plan"], env=env)

    assert result.exit_code == 0
    assert "Remediation Execution Plan Dry Run" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_execution_plan_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_session_report:" in result.stdout
    assert "execution_plan_status: stalled" in result.stdout
    assert "next_action_command: uv run sis diagnose-quotes" in result.stdout
    assert "source_confidence: low" in result.stdout
    assert "execute_signal_confidence: low" in result.stdout
    assert "observed_sources: ['stdout_stderr']" in result.stdout
    assert "feedback_priority_reason: evaluation_failed" in result.stdout
    assert (data_dir / "reports/remediation_execution_plan.md").exists()
    assert (data_dir / "ops/remediation_execution_plan_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_execution_plan_dry_run"
    assert latest["status"] == "stalled"
    assert "execution_plan_status=stalled" in latest["notes"]


def test_remediation_session_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_execution_plan_summary.json").write_text(
        '{"execution_plan_status":"stalled","planner_status":"stalled","planner_rerun_trend":"improved","planned_reason_count":2,"planned_action_count":2,"next_action_command":"uv run sis validate-artifacts --strict","entries":[{"source":"paper_operations_runbook","priority":2,"reason":"strict_validation_failed","recommendation_status":"stalled","entry_trend":"regressed","observed_sources":["stdout_stderr"],"signal_observed_sources":{"validate-artifacts --strict reports the current issue count":"stdout_stderr"}}],"actions":[{"source":"paper_operations_runbook","priority":2,"effective_priority":2,"reason":"strict_validation_failed","stage":"preflight","sequence":1,"command":"uv run sis validate-artifacts --strict","recommendation_status":"stalled","entry_trend":"regressed","observed_sources":["stdout_stderr"],"source_confidence":"high","source_policy":"direct_observation_priority","stage_signal_confidence":"low","signal_observed_sources":{"validate-artifacts --strict reports the current issue count":"stdout_stderr"},"verification":["validate-artifacts --strict reports the current issue count"]},{"source":"phase_gate_review","priority":2,"effective_priority":2,"reason":"execution_drift_unresolved","stage":"preflight","sequence":1,"command":"uv run sis monitoring-status","recommendation_status":"improving","entry_trend":"improved","observed_sources":["markdown_reports"],"source_confidence":"low","source_policy":"verify_before_execute","stage_signal_confidence":"low","signal_observed_sources":{"monitoring-status prints execution_drift_overview_status":"markdown_reports"},"verification":["monitoring-status prints execution_drift_overview_status"]}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_command_results_summary.json").write_text(
        '{"entries":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","observation_status":"observed"},{"action_key":"priority_2_phase_gate_review_execution_drift_unresolved_preflight_1","observation_status":"observed"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_evaluator_summary.json").write_text(
        '{"actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","evaluation_result":"pass"},{"action_key":"priority_2_phase_gate_review_execution_drift_unresolved_preflight_1","evaluation_result":"fail"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-session"], env=env)

    assert result.exit_code == 0
    assert "Remediation Session Dry Run" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_session_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_scoreboard_report:" in result.stdout
    assert "session_status: ready_for_dry_run" in result.stdout
    assert "next_pending_command: uv run sis monitoring-status" in result.stdout
    assert "next_pending_stage_signal_confidence: low" in result.stdout
    assert "next_pending_feedback_priority_reason: evaluation_failed" in result.stdout
    assert "observed_sources: ['markdown_reports']" in result.stdout
    assert (data_dir / "reports/remediation_session.md").exists()
    assert (data_dir / "ops/remediation_session_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_session_dry_run"
    assert latest["status"] == "ready_for_dry_run"
    assert "session_status=ready_for_dry_run" in latest["notes"]
    assert "next_pending_feedback_priority_reason=evaluation_failed" in latest["notes"]


def test_remediation_session_checkpoint_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_session_summary.json").write_text(
        '{"actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","source":"paper_operations_runbook","priority":2,"effective_priority":2,"reason":"strict_validation_failed","stage":"preflight","sequence":1,"command":"uv run sis validate-artifacts --strict","suggested_result":"needs_attention","evidence_status":"evidence_missing","observed_sources":["stdout_stderr"],"signal_observed_sources":{"validate-artifacts --strict reports the current issue count":"stdout_stderr"},"stage_signal_confidence":"low","verification":["validate-artifacts --strict reports the current issue count"],"operator_notes":[]},{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_post_check_1","source":"paper_operations_runbook","priority":2,"effective_priority":2,"reason":"strict_validation_failed","stage":"post_check","sequence":1,"command":"uv run sis paper-operations-runbook","suggested_result":"pass","evidence_status":"evidence_missing","observed_sources":["phase_gate_review"],"signal_observed_sources":{"phase_gate_strict_validation_issue_count == 0":"phase_gate_review"},"stage_signal_confidence":"high","verification":["phase_gate_strict_validation_issue_count == 0"],"operator_notes":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "remediation-session-checkpoint",
            "--action-key",
            "priority_2_paper_operations_runbook_strict_validation_failed_preflight_1",
            "--result",
            "retry",
            "--note",
            "strict validation still failing on first retry",
            "--evidence-path",
            "data/ops/validate_artifacts_strict.log",
            "--observed-signal",
            "validate-artifacts --strict reports the current issue count",
            "--stdout-summary",
            "issues=2 checked_files=7",
            "--stderr-summary",
            "",
            "--exit-code",
            "1",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "Remediation Session Checkpoint" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_session_checkpoint_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_evaluator_report:" in result.stdout
    assert "checkpoint_status: retry_pending" in result.stdout
    assert "updated_result: retry" in result.stdout
    assert "next_action_observed_sources: ['stdout_stderr']" in result.stdout
    assert "next_action_stage_signal_confidence: low" in result.stdout
    assert (data_dir / "reports/remediation_session_checkpoint.md").exists()
    assert (data_dir / "ops/remediation_session_checkpoint_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_session_checkpoint"
    assert latest["status"] == "retry_pending"
    assert "checkpoint_status=retry_pending" in latest["notes"]


def test_remediation_command_results_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_session_checkpoint_summary.json").write_text(
        '{"actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","source":"paper_operations_runbook","reason":"strict_validation_failed","stage":"preflight","command":"uv run sis validate-artifacts --strict","checkpoint_status":"retry","observed_sources":["stdout_stderr"],"signal_observed_sources":{"validate-artifacts --strict reports the current issue count":"stdout_stderr"},"evidence_paths":["data/ops/validate_artifacts_strict.log"],"observed_signals":["validate-artifacts --strict reports the current issue count"]},{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_post_check_1","source":"paper_operations_runbook","reason":"strict_validation_failed","stage":"post_check","command":"uv run sis paper-operations-runbook","checkpoint_status":"pending","evidence_paths":[],"observed_signals":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-command-results"], env=env)

    assert result.exit_code == 0
    assert "Remediation Command Results" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_command_results_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_scoreboard_report:" in result.stdout
    assert "command_results_status: partially_observed" in result.stdout
    assert "observed_sources: ['stdout_stderr']" in result.stdout
    assert (data_dir / "reports/remediation_command_results.md").exists()
    assert (data_dir / "ops/remediation_command_results_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_command_results"
    assert latest["status"] == "partially_observed"
    assert "command_results_status=partially_observed" in latest["notes"]


def test_remediation_evidence_ingest_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_session_summary.json").write_text(
        '{"actions":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","source":"phase_gate_review","priority":1,"reason":"missing_required_artifacts","stage":"preflight","sequence":1,"command":"uv run sis implementation-status","suggested_result":"pass","evidence_status":"evidence_missing","verification":["implementation-status exits 0"],"operator_notes":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "remediation-evidence-ingest",
            "--action-key",
            "priority_1_phase_gate_review_missing_required_artifacts_preflight_1",
            "--result",
            "pass",
            "--evidence-path",
            "docs/CODE_STATUS.md",
            "--stdout-summary",
            "implementation status regenerated",
            "--exit-code",
            "0",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert "Remediation Command Results" in result.stdout
    assert "command_results_status: fully_observed" in result.stdout
    assert (data_dir / "reports/remediation_session_checkpoint.md").exists()
    assert (data_dir / "reports/remediation_command_results.md").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_evidence_ingest"
    assert latest["status"] == "completed"
    assert "exit_code=0" in latest["notes"]


def test_remediation_scoreboard_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_session_checkpoint_summary.json").write_text(
        '{"checkpoint_status":"retry_pending","pass_action_count":1,"fail_action_count":0,"retry_action_count":1,"pending_action_count":1,"next_action_command":"uv run sis validate-artifacts --strict","actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","priority":2,"effective_priority":2,"stage":"preflight","sequence":1,"command":"uv run sis validate-artifacts --strict","checkpoint_status":"retry","evidence_status":"needs_review","observed_sources":["stdout_stderr"],"stage_signal_confidence":"low","operator_notes":["strict validation still failing on first retry"]},{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_post_check_1","priority":2,"effective_priority":2,"stage":"post_check","sequence":1,"command":"uv run sis paper-operations-runbook","checkpoint_status":"pass","evidence_status":"evidence_recorded","observed_sources":["phase_gate_review"],"stage_signal_confidence":"high","operator_notes":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-scoreboard"], env=env)

    assert result.exit_code == 0
    assert "Remediation Scoreboard" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_scoreboard_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_evidence_report:" in result.stdout
    assert "scoreboard_status: retrying" in result.stdout
    assert "completion_rate: 0.5" in result.stdout
    assert "next_action_observed_sources: ['stdout_stderr']" in result.stdout
    assert "next_action_stage_signal_confidence: low" in result.stdout
    assert (data_dir / "reports/remediation_scoreboard.md").exists()
    assert (data_dir / "ops/remediation_scoreboard_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_scoreboard"
    assert latest["status"] == "retrying"
    assert "scoreboard_status=retrying" in latest["notes"]


def test_remediation_session_checkpoint_cli_uses_feedback_loop(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_session_summary.json").write_text(
        '{"actions":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","source":"phase_gate_review","priority":1,"effective_priority":1,"reason":"missing_required_artifacts","stage":"preflight","sequence":1,"command":"uv run sis implementation-status","suggested_result":"pass","evidence_status":"evidence_missing","observed_sources":["stdout_stderr"],"stage_signal_confidence":"high","verification":["implementation-status exits 0"],"operator_notes":[]},{"action_key":"priority_3_phase_gate_review_execution_drift_unresolved_post_check_1","source":"phase_gate_review","priority":3,"effective_priority":3,"reason":"execution_drift_unresolved","stage":"post_check","sequence":1,"command":"uv run sis phase-gate-review","suggested_result":"pass","evidence_status":"evidence_missing","observed_sources":["markdown_reports"],"stage_signal_confidence":"low","verification":["execution_drift_overview_status == ok"],"operator_notes":[]}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_command_results_summary.json").write_text(
        '{"entries":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","observation_status":"observed"},{"action_key":"priority_3_phase_gate_review_execution_drift_unresolved_post_check_1","observation_status":"observed"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_evaluator_summary.json").write_text(
        '{"actions":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","evaluation_result":"pass"},{"action_key":"priority_3_phase_gate_review_execution_drift_unresolved_post_check_1","evaluation_result":"fail"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-session-checkpoint"], env=env)

    assert result.exit_code == 0
    assert "next_action_command: uv run sis phase-gate-review" in result.stdout
    assert "feedback_priority_reason: evaluation_failed" in result.stdout


def test_remediation_scoreboard_cli_uses_feedback_loop(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/remediation_session_checkpoint_summary.json").write_text(
        '{"checkpoint_status":"in_progress","pass_action_count":0,"fail_action_count":0,"retry_action_count":0,"pending_action_count":2,"next_action_command":"uv run sis implementation-status","actions":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","priority":1,"effective_priority":1,"stage":"preflight","sequence":1,"command":"uv run sis implementation-status","checkpoint_status":"pending","evidence_status":"evidence_missing","observed_sources":["stdout_stderr"],"stage_signal_confidence":"high","operator_notes":[]},{"action_key":"priority_3_phase_gate_review_execution_drift_unresolved_post_check_1","priority":3,"effective_priority":3,"stage":"post_check","sequence":1,"command":"uv run sis phase-gate-review","checkpoint_status":"pending","evidence_status":"evidence_missing","observed_sources":["markdown_reports"],"stage_signal_confidence":"low","operator_notes":[]}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_command_results_summary.json").write_text(
        '{"entries":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","observation_status":"observed"},{"action_key":"priority_3_phase_gate_review_execution_drift_unresolved_post_check_1","observation_status":"observed"}]}',
        encoding="utf-8",
    )
    (data_dir / "ops/remediation_evaluator_summary.json").write_text(
        '{"actions":[{"action_key":"priority_1_phase_gate_review_missing_required_artifacts_preflight_1","evaluation_result":"pass"},{"action_key":"priority_3_phase_gate_review_execution_drift_unresolved_post_check_1","evaluation_result":"fail"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-scoreboard"], env=env)

    assert result.exit_code == 0
    assert "next_action_command: uv run sis phase-gate-review" in result.stdout
    assert "feedback_priority_reason: evaluation_failed" in result.stdout


def test_remediation_evaluator_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text('{"strict_validation_issue_count":0}', encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_2_phase_gate_review_strict_validation_failed_post_check_1","source":"phase_gate_review","command":"uv run sis phase-gate-review","verification":["strict_validation_issue_count == 0"],"checkpoint_status":"pending","evidence_status":"evidence_missing","operator_notes":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "Remediation Evaluator" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_evaluator_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_scoreboard_report:" in result.stdout
    assert "evaluator_status: auto_passed" in result.stdout
    assert (data_dir / "reports/remediation_evaluator.md").exists()
    assert (data_dir / "ops/remediation_evaluator_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_evaluator"
    assert latest["status"] == "auto_passed"
    assert "evaluator_status=auto_passed" in latest["notes"]


def test_remediation_evaluator_cli_uses_stdout_summary_signals(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_execute_1","source":"paper_operations_runbook","command":"uv run sis validate-artifacts --strict","verification":["validate-artifacts --strict reports the current issue count","strict validation output includes checked_files","strict validation output reports checked_files >= 1","strict validation output reports issues=0"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":["data/ops/validate_artifacts_strict.log"],"latest_exit_code":0,"latest_stdout_summary":"issues=0 checked_files=7","latest_stderr_summary":""}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "expected=>=1 observed=7" in result.stdout


def test_remediation_evaluator_cli_uses_monitoring_stdout_signals(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1","source":"paper_operations_runbook","command":"uv run sis monitoring-status","verification":["monitoring-status prints execution_diagnostics_status","monitoring output shows current balance/fills gap flags","monitoring-status prints execution_drift_overview_status","monitoring output shows current mismatch counts","phase-gate-review prints phase2_entry_allowed","phase gate output shows current readiness blockers","current gate decision is visible before regeneration"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":["data/ops/monitoring_status.log"],"latest_exit_code":0,"latest_stdout_summary":"execution_diagnostics_status=degraded execution_balance_gap_detected=True execution_fills_gap_detected=False execution_drift_overview_status=degraded execution_drift_overview_state_comparison_mismatching_count=1 execution_drift_overview_snapshot_drift_mismatching_snapshot_count=2 phase2_entry_allowed=False phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","latest_stderr_summary":""}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert (
        "signal=monitoring-status prints execution_diagnostics_status status=pass" in result.stdout
    )
    assert "signal=phase gate output shows current readiness blockers status=pass" in result.stdout


def test_remediation_evaluator_cli_uses_quote_diagnostics_and_go_no_go_stdout_signals(
    tmp_path,
) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_3_phase_gate_review_diagnostics_unavailable_preflight_1","source":"phase_gate_review","command":"uv run sis diagnose-quotes","verification":["diagnose-quotes prints per-symbol diagnostics rows","required symbols show quote diagnostics coverage"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":["data/ops/quote_diagnostics.log"],"latest_exit_code":0,"latest_stdout_summary":"venue=gtrade symbol=QQQ rows=120 tradable_rate=0.9000 stale_rate=0.0100","latest_stderr_summary":""},{"action_key":"priority_5_phase_gate_review_phase_gate_not_cleared_preflight_1","source":"phase_gate_review","command":"uv run sis check-go-no-go","verification":["check-go-no-go prints the current decision and blockers","current gate decision is visible before regeneration"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":["data/ops/check_go_no_go.log"],"latest_exit_code":0,"latest_stdout_summary":"decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW phase2_entry_reason=remain_in_phase1_until_live_evidence_gate_clears blocker_count=2","latest_stderr_summary":""}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "signal=diagnose-quotes prints per-symbol diagnostics rows status=pass" in result.stdout
    assert (
        "signal=check-go-no-go prints the current decision and blockers status=pass"
        in result.stdout
    )


def test_remediation_evaluator_cli_uses_operation_manifest_notes(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-25T00:00:00+00:00","operation":"monitoring_snapshot","mode":"manual","command":"uv run sis monitoring-status","status":"degraded","scheduled_for":null,"parent_run_id":null,"artifacts":[],"notes":["execution_diagnostics_status=degraded","execution_balance_gap_detected=True","execution_fills_gap_detected=False","execution_drift_overview_status=degraded","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=2"]}',
                '{"run_id":"r2","created_at":"2026-05-25T00:05:00+00:00","operation":"phase_gate_review","mode":"manual","command":"uv run sis phase-gate-review","status":"blocked","scheduled_for":null,"parent_run_id":null,"artifacts":[],"notes":["phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase_gate_checked_files=7"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '","operation_chain_path":"'
        + str(data_dir / "ops/operation_manifests.jsonl").replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1","source":"paper_operations_runbook","command":"uv run sis monitoring-status","verification":["monitoring-status prints execution_diagnostics_status","monitoring output shows current balance/fills gap flags","monitoring-status prints execution_drift_overview_status","monitoring output shows current mismatch counts","phase-gate-review prints phase2_entry_allowed","phase gate output shows current readiness blockers","strict validation output includes checked_files"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "operation_chain_path:" in result.stdout
    assert "signal=phase-gate-review prints phase2_entry_allowed status=pass" in result.stdout
    assert "expected=present observed=7" in result.stdout


def test_remediation_evaluator_cli_uses_timeline_summary_fallback(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    (data_dir / "ops/operations_timeline_summary.json").write_text(
        '{"latest_execution_diagnostics_status":"degraded","latest_execution_drift_overview_status":"degraded","latest_execution_drift_overview_state_comparison_mismatching_count":1,"latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count":2,"latest_phase2_entry_allowed":false,"latest_phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","latest_phase_gate_decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","latest_phase_gate_checked_files":7}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_timeline_summary.json").write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1","source":"paper_operations_runbook","command":"uv run sis monitoring-status","verification":["monitoring-status prints execution_diagnostics_status","monitoring-status prints execution_drift_overview_status","monitoring output shows current mismatch counts","phase-gate-review prints phase2_entry_allowed","phase gate output shows current readiness blockers","strict validation output includes checked_files"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "operations_timeline_summary_path:" in result.stdout
    assert "signal=monitoring output shows current mismatch counts status=pass" in result.stdout
    assert "expected=present observed=7" in result.stdout


def test_remediation_evaluator_cli_uses_dashboard_bundle_summary_fallback(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    (data_dir / "ops/operations_dashboard_summary.json").write_text(
        '{"execution_diagnostics_status":"degraded","execution_balance_gap_detected":true,"execution_fills_gap_detected":false,"execution_drift_overview_status":"degraded","execution_drift_overview_state_comparison_mismatching_count":1,"execution_drift_overview_snapshot_drift_mismatching_snapshot_count":2}',
        encoding="utf-8",
    )
    (data_dir / "ops/operations_bundle_manifest.json").write_text(
        '{"phase2_entry_allowed":false,"phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","phase_gate_decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase_gate_checked_files":7}',
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_3_paper_operations_runbook_execution_diagnostics_degraded_preflight_1","source":"paper_operations_runbook","command":"uv run sis monitoring-status","verification":["monitoring-status prints execution_diagnostics_status","monitoring output shows current balance/fills gap flags","monitoring-status prints execution_drift_overview_status","monitoring output shows current mismatch counts","phase-gate-review prints phase2_entry_allowed","phase gate output shows current readiness blockers","strict validation output includes checked_files"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "operations_dashboard_summary_path:" in result.stdout
    assert "operations_bundle_manifest_path:" in result.stdout
    assert (
        "signal=monitoring output shows current balance/fills gap flags status=pass"
        in result.stdout
    )
    assert "expected=present observed=7" in result.stdout


def test_remediation_evaluator_cli_uses_issue_previews_and_blocker_lists(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text(
        '{"phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}],"blockers":["stale_rate at or below threshold"],"next_actions":["collect more live quotes"]}',
        encoding="utf-8",
    )
    runbook_summary.write_text(
        '{"phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","source":"paper_operations_runbook","command":"uv run sis validate-artifacts --strict","verification":["strict validation preview lists current issues"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]},{"action_key":"priority_5_phase_gate_review_phase_gate_not_cleared_preflight_1","source":"phase_gate_review","command":"uv run sis check-go-no-go","verification":["phase gate summary lists blockers","phase gate summary lists next actions"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "signal=strict validation preview lists current issues status=pass" in result.stdout
    assert "signal=phase gate summary lists blockers status=pass" in result.stdout


def test_remediation_evaluator_cli_uses_markdown_report_fallback(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_report = data_dir / "reports/phase_gate_review.md"
    phase_gate_summary.write_text(
        '{"phase_gate_review_report_path":"' + str(phase_gate_report).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    runbook_summary.write_text("{}", encoding="utf-8")
    phase_gate_report.write_text(
        "\n".join(
            [
                "# Phase Gate Review",
                "",
                "## Executive Summary",
                "",
                "- phase2_entry_reason: stale_rate remains above threshold",
                "",
                "## Strict Validation",
                "",
                "- checked_files: 7",
                "",
                "| path | message |",
                "| --- | --- |",
                "| data/research/backtest_metrics_summary.json | missing field |",
                "",
                "## Next Actions",
                "",
                "- collect more live quotes",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_2_paper_operations_runbook_strict_validation_failed_preflight_1","source":"paper_operations_runbook","command":"uv run sis validate-artifacts --strict","verification":["strict validation preview lists current issues"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]},{"action_key":"priority_5_phase_gate_review_phase_gate_not_cleared_preflight_1","source":"phase_gate_review","command":"uv run sis check-go-no-go","verification":["phase gate summary lists blockers","phase gate summary lists next actions"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "phase_gate_review_report_path:" in result.stdout
    assert "signal=strict validation preview lists current issues status=pass" in result.stdout
    assert "signal=phase gate summary lists blockers status=pass" in result.stdout


def test_remediation_evaluator_cli_uses_ops_review_fallback(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    ops_review_summary = data_dir / "ops/ops_review_summary.json"
    ops_review_report = data_dir / "reports/ops_review_report.md"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    ops_review_summary.write_text(
        '{"execution_balance_gap_detected":false,"execution_fills_gap_detected":true,"execution_drift_overview_state_comparison_mismatching_count":1,"execution_drift_overview_snapshot_drift_mismatching_snapshot_count":2,"phase_gate_decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","phase_gate_checked_files":7}',
        encoding="utf-8",
    )
    ops_review_report.write_text(
        "\n".join(
            [
                "# Ops Review Report",
                "",
                "## Strict Validation Preview",
                "",
                "- data/research/backtest_metrics_summary.json: missing field",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"a1","source":"phase_gate_review","command":"uv run sis validate-artifacts --strict","verification":["strict validation preview lists current issues"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]},{"action_key":"a2","source":"phase_gate_review","command":"uv run sis monitoring-status","verification":["monitoring output shows current balance/fills gap flags","monitoring output shows current mismatch counts","phase gate output shows current readiness blockers"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "ops_review_summary_path:" in result.stdout
    assert "ops_review_report_path:" in result.stdout
    assert "signal=strict validation preview lists current issues status=pass" in result.stdout
    assert (
        "signal=monitoring output shows current balance/fills gap flags status=pass"
        in result.stdout
    )
    assert "signal=phase gate output shows current readiness blockers status=pass" in result.stdout


def test_remediation_evaluator_cli_uses_current_state_index_fallback(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    current_state_index = data_dir / "ops/current_state_index.json"
    current_state_report = data_dir / "reports/current_state_index.md"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    current_state_index.write_text(
        '{"execution_balance_gap_detected":false,"execution_fills_gap_detected":true,"execution_drift_overview_state_comparison_mismatching_count":1,"execution_drift_overview_snapshot_drift_mismatching_snapshot_count":2,"phase_gate_decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","phase_gate_checked_files":7,"live_evidence_status":"completed","live_evidence_decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW"}',
        encoding="utf-8",
    )
    current_state_report.write_text(
        "\n".join(
            [
                "# Current State Index",
                "",
                "## Strict Validation Preview",
                "",
                "- data/research/backtest_metrics_summary.json: missing field",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"a1","source":"phase_gate_review","command":"uv run sis validate-artifacts --strict","verification":["strict validation preview lists current issues"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]},{"action_key":"a2","source":"phase_gate_review","command":"uv run sis monitoring-status","verification":["monitoring output shows current balance/fills gap flags","monitoring output shows current mismatch counts","phase gate output shows current readiness blockers","phase-gate-review prints phase2_entry_allowed"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "current_state_index_summary_path:" in result.stdout
    assert "current_state_index_report_path:" in result.stdout
    assert "signal=strict validation preview lists current issues status=pass" in result.stdout
    assert "signal=phase-gate-review prints phase2_entry_allowed status=pass" in result.stdout


def test_remediation_evaluator_cli_uses_live_evidence_fallback(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    logs_summary_dir = tmp_path / "logs/live_evidence/summaries"
    live_reports_dir = tmp_path / "docs/live_evidence_reports"
    logs_summary_dir.mkdir(parents=True, exist_ok=True)
    live_reports_dir.mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    current_state_index = data_dir / "ops/current_state_index.json"
    live_evidence_summary = logs_summary_dir / "live_evidence_summary_run123.json"
    live_evidence_report = live_reports_dir / "live_evidence_report_run123.md"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    current_state_index.write_text(
        '{"artifacts":{"live_evidence_summary":"'
        + str(live_evidence_summary).replace("\\", "\\\\")
        + '"}}',
        encoding="utf-8",
    )
    live_evidence_summary.write_text(
        '{"status":"completed","decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","run_id":"run123","blockers":["stale_rate remains above threshold"],"next_actions":["collect more live quotes"],"phase_gate_summary":{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","checked_files":7},"execution_diagnostics_summary":{"overall_status":"degraded","balance_gap_detected":false,"fills_gap_detected":true}}',
        encoding="utf-8",
    )
    live_evidence_report.write_text(
        "\n".join(
            [
                "# Live Evidence Detailed Report",
                "",
                "## Phase Gate Summary",
                "",
                "- phase2_entry_allowed: `False`",
                "- phase_gate_reason: `remain_in_phase1_until_live_evidence_gate_clears`",
                "",
                "## Execution Venue Diagnostics",
                "",
                "- overall_status: `degraded`",
                "- balance_gap_detected: `False`",
                "- fills_gap_detected: `True`",
                "",
                "## Blockers",
                "",
                "- stale_rate remains above threshold",
                "",
                "## Next Actions",
                "",
                "- collect more live quotes",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"a1","source":"phase_gate_review","command":"uv run sis monitoring-status","verification":["monitoring output shows current balance/fills gap flags","phase gate summary lists blockers","phase gate summary lists next actions","phase-gate-review prints phase2_entry_allowed"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "evaluator_status: auto_passed" in result.stdout
    assert "live_evidence_summary_path:" in result.stdout
    assert "live_evidence_report_path:" in result.stdout
    assert "signal=phase gate summary lists blockers status=pass" in result.stdout
    assert "signal=phase gate summary lists next actions status=pass" in result.stdout


def test_remediation_evaluator_cli_reports_observed_sources(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    phase_gate_summary.write_text("{}", encoding="utf-8")
    runbook_summary.write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"a1","source":"phase_gate_review","command":"uv run sis validate-artifacts --strict","verification":["validate-artifacts --strict reports issues=0"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_signals":[],"evidence_paths":[],"latest_stdout_summary":"issues=0 checked_files=7"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evaluator"], env=env)

    assert result.exit_code == 0
    assert "## Fallback Field Sources" in result.stdout
    assert "observed_source=stdout_stderr" in result.stdout


def test_remediation_evidence_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    runbook_summary = data_dir / "ops/paper_operations_runbook_summary.json"
    planner_summary = data_dir / "ops/remediation_planner_summary.json"
    execution_plan_summary = data_dir / "ops/remediation_execution_plan_summary.json"
    session_summary = data_dir / "ops/remediation_session_summary.json"
    checkpoint_summary = data_dir / "ops/remediation_session_checkpoint_summary.json"
    evaluator_summary = data_dir / "ops/remediation_evaluator_summary.json"
    phase_gate_summary.write_text(
        '{"phase_gate_review_report_path":"'
        + str(data_dir / "reports/phase_gate_review.md").replace("\\", "\\\\")
        + '","required_artifact_paths":{"latest_manifest_path":"'
        + str(data_dir / "research/decision_summary.json").replace("\\", "\\\\")
        + '"},"missing_required_artifact_paths":[]}',
        encoding="utf-8",
    )
    runbook_summary.write_text("{}", encoding="utf-8")
    planner_summary.write_text(
        '{"phase_gate_summary_path":"'
        + str(phase_gate_summary).replace("\\", "\\\\")
        + '","runbook_summary_path":"'
        + str(runbook_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    execution_plan_summary.write_text(
        '{"remediation_planner_summary_path":"' + str(planner_summary).replace("\\", "\\\\") + '"}',
        encoding="utf-8",
    )
    session_summary.write_text(
        '{"remediation_execution_plan_summary_path":"'
        + str(execution_plan_summary).replace("\\", "\\\\")
        + '"}',
        encoding="utf-8",
    )
    checkpoint_summary.write_text(
        '{"remediation_session_summary_path":"'
        + str(session_summary).replace("\\", "\\\\")
        + '","actions":[{"action_key":"priority_2_phase_gate_review_strict_validation_failed_preflight_1","source":"phase_gate_review","command":"uv run sis validate-artifacts --strict","verification":["validate-artifacts --strict reports issues=0"],"checkpoint_status":"pass","evidence_status":"evidence_recorded","operator_notes":[],"observed_sources":["current_state_index"],"observed_signals":["validate-artifacts --strict reports issues=0"],"evidence_paths":["data/ops/validate_artifacts_strict.log"],"latest_exit_code":0}]}',
        encoding="utf-8",
    )
    evaluator_summary.write_text(
        '{"actions":[{"action_key":"priority_5_phase_gate_review_phase_gate_not_cleared_post_check_1","source":"phase_gate_review","reason":"phase_gate_not_cleared","stage":"post_check","command":"uv run sis phase-gate-review","evaluation_result":"manual_review","checkpoint_status":"pending","evidence_status":"evidence_missing","suggested_result":"pass","operator_notes":[],"observed_sources":["current_state_index"],"verification":["validate-artifacts --strict reports issues=0"],"signal_evaluations":[{"signal":"validate-artifacts --strict reports issues=0","status":"unsupported","expected":null,"observed":null,"observed_source":"stdout_stderr"}]}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["remediation-evidence"], env=env)

    assert result.exit_code == 0
    assert "Remediation Evidence" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "remediation_evidence_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "remediation_evaluator_report:" in result.stdout
    assert "evidence_status: manual_review_required" in result.stdout
    assert "observed_sources: ['current_state_index', 'stdout_stderr']" in result.stdout
    assert (data_dir / "reports/remediation_evidence.md").exists()
    assert (data_dir / "ops/remediation_evidence_summary.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "remediation_evidence"
    assert latest["status"] == "manual_review_required"
    assert "evidence_status=manual_review_required" in latest["notes"]


def test_paper_cycle_history_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-24T00:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"run_id":"r2","created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=2","fills=2","execution_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["paper-cycle-history"], env=env)

    assert result.exit_code == 0
    assert "Paper Cycle History Report" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "paper_cycle_history_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_drift_overview_report:" in result.stdout
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert (
        "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    )
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/paper_cycle_history_report.md").exists()
    assert (data_dir / "ops/paper_cycle_history_summary.json").exists()


def test_execution_gap_history_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["execution_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-gap-history"], env=env)

    assert result.exit_code == 0
    assert "Execution Gap History Report" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "execution_gap_history_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_state_comparison_report:" in result.stdout
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert (data_dir / "reports/execution_gap_history.md").exists()
    assert (data_dir / "ops/execution_gap_history_summary.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_execution_state_comparison_history_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","notes":["execution_diagnostics_status=ok","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","notes":["orders=1","fills=1","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-state-comparison-history"], env=env)

    assert result.exit_code == 0
    assert "Execution State Comparison History" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "execution_state_comparison_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_snapshot_drift_report:" in result.stdout
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: ok" in result.stdout
    assert "latest_status_match: False" in result.stdout
    assert (data_dir / "reports/execution_state_comparison_history.md").exists()
    assert (data_dir / "ops/execution_state_comparison_history_summary.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_execution_snapshot_drift_history_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["execution_diagnostics_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["execution_diagnostics_status=degraded","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-snapshot-drift-history"], env=env)

    assert result.exit_code == 0
    assert "Execution Snapshot Drift History" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "execution_snapshot_drift_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_drift_overview_report:" in result.stdout
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: ok" in result.stdout
    assert "latest_execution_state_comparison_status_match: False" in result.stdout
    assert (data_dir / "reports/execution_snapshot_drift_history.md").exists()
    assert (data_dir / "ops/execution_snapshot_drift_history_summary.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_execution_drift_overview_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"latest_execution_diagnostics_status":"degraded","latest_execution_gap_history_diagnostics_status":"degraded","latest_status_match":true,"mismatching_count":0}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":0}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-drift-overview"], env=env)

    assert result.exit_code == 0
    assert "Execution Drift Overview" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "execution_drift_overview_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "execution_snapshot_report:" in result.stdout
    assert "overall_status: ok" in result.stdout
    assert (data_dir / "reports/execution_drift_overview.md").exists()
    assert (data_dir / "ops/execution_drift_overview_summary.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_operations_bundle_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    write_paths = {
        data_dir / "ops/monitoring_status.json": '{"status":"ok"}',
        data_dir / "ops/ops_review_summary.json": '{"latest_status":"completed"}',
        data_dir / "ops/operations_dashboard_summary.json": '{"overall_status":"ok"}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir
        / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir
        / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir
        / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        data_dir
        / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir
        / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir / "ops/paper_operations_runbook_summary.json": '{"monitoring_status":"ok"}',
        data_dir / "ops/paper_cycle_history_summary.json": '{"cycle_count":2,"completed_count":2}',
        data_dir
        / "ops/phase_gate_review_summary.json": '{"decision":"GO","phase2_entry_allowed":true,"phase2_entry_reason":"decision_cleared_and_phase1_gate_complete","strict_validation_passed":true,"strict_validation_issue_count":0,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[]}',
    }
    for path, text in write_paths.items():
        path.write_text(text, encoding="utf-8")

    result = runner.invoke(app, ["operations-bundle"], env=env)

    assert result.exit_code == 0
    assert "Operations Bundle Manifest" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_balance_gap_detected: True" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_gap_history_latest_status: ok" in result.stdout
    assert "execution_gap_history_latest_diagnostics_status: degraded" in result.stdout
    assert "execution_state_comparison_entry_count: 4" in result.stdout
    assert "execution_state_comparison_latest_status_match: False" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "readiness_next_phase_candidate: Stay Phase 1" in result.stdout
    assert "readiness_execution_ready: False" in result.stdout
    assert "phase_gate_decision: GO" in result.stdout
    assert "phase_gate_reason: decision_cleared_and_phase1_gate_complete" in result.stdout
    assert "phase_gate_strict_validation_passed: True" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "issues: none" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "operations_bundle_report:" in result.stdout
    assert f"phase_gate_review_report: {data_dir / 'reports/phase_gate_review.md'}" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/operations_bundle_manifest.md").exists()
    assert (data_dir / "ops/operations_bundle_manifest.json").exists()
    assert '"recommended_read_order"' in (
        data_dir / "ops/operations_bundle_manifest.json"
    ).read_text(encoding="utf-8")
    assert '"phase_gate_strict_validation_passed": true' in (
        data_dir / "ops/operations_bundle_manifest.json"
    ).read_text(encoding="utf-8")
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "operations_snapshot"
    assert "execution_snapshot_drift_entry_count=3" in latest["notes"]
    assert "execution_snapshot_drift_latest_status_match=True" in latest["notes"]
    assert "execution_snapshot_drift_mismatching_snapshot_count=1" in latest["notes"]


def test_current_state_index_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir / "ops/operations_dashboard_summary.json": '{"overall_status":"ok"}',
        data_dir / "ops/operations_bundle_manifest.json": '{"overall_status":"ok","cycle_count":2}',
        data_dir
        / "ops/audit_dashboard_summary.json": '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot"}',
        data_dir / "ops/audit_bundle_manifest.json": '{"bundle_history_snapshot_count":3}',
        data_dir
        / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir
        / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir
        / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_gap_history_diagnostics_status":"degraded","latest_status_match":true,"mismatching_count":0}',
        data_dir
        / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":0}',
        data_dir
        / "research/backtest_metrics_summary.json": '{"total_trade_count":5,"symbols":["QQQ","SPY"]}',
        data_dir
        / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
    }
    for path, text in payloads.items():
        path.write_text(text, encoding="utf-8")

    result = runner.invoke(app, ["current-state-index"], env=env)

    assert result.exit_code == 0
    assert "Current State Index" in result.stdout
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in result.stdout
    assert "phase_gate_strict_validation_passed: True" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_balance_gap_detected: True" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_state_comparison_entry_count: 4" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "phase_gate_review_report: data/reports/phase_gate_review.md" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "phase_gate_review_report: data/reports/phase_gate_review.md" in result.stdout
    assert "## Restart Pointers" in result.stdout
    assert "current_state_index_report:" in result.stdout
    assert "remediation_scoreboard_report:" in result.stdout
    assert (data_dir / "reports/current_state_index.md").exists()
    assert (data_dir / "ops/current_state_index.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_readiness_snapshot_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir
        / "ops/current_state_index.json": '{"overall_status":"ok","research_quality_report_exists":true,"timeline_latest_remediation_planner_status":"stalled","timeline_latest_remediation_planner_next_best_command":"uv run sis validate-artifacts --strict","timeline_latest_remediation_planner_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_execution_plan_status":"stalled","timeline_latest_remediation_execution_plan_next_action_command":"uv run sis diagnose-quotes","timeline_latest_remediation_execution_plan_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_session_status":"ready_for_dry_run","timeline_latest_remediation_session_next_pending_command":"uv run sis monitoring-status","timeline_latest_remediation_session_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_checkpoint_status":"retry_pending","timeline_latest_remediation_checkpoint_next_action_command":"uv run sis phase-gate-review","timeline_latest_remediation_checkpoint_feedback_priority_reason":"evaluation_failed","timeline_latest_remediation_scoreboard_status":"retrying","timeline_latest_remediation_scoreboard_next_action_command":"uv run sis phase-gate-review","timeline_latest_remediation_scoreboard_feedback_priority_reason":"evaluation_failed"}',
        data_dir
        / "ops/phase_gate_review_summary.json": '{"decision":"GO","phase2_entry_allowed":true,"phase2_entry_reason":"decision_cleared_and_phase1_gate_complete","strict_validation_passed":true,"strict_validation_issue_count":0,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[]}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir
        / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir
        / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir
        / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_gap_history_diagnostics_status":"degraded","latest_status_match":true,"mismatching_count":0}',
        data_dir
        / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir / "ops/operations_dashboard_summary.json": '{"overall_status":"ok"}',
        data_dir / "research/backtest_metrics_summary.json": '{"total_trade_count":5}',
    }
    for path, text in payloads.items():
        path.write_text(text, encoding="utf-8")
    summaries_root = tmp_path / "logs/live_evidence/summaries"
    summaries_root.mkdir(parents=True, exist_ok=True)
    (summaries_root / "live_evidence_summary_20260522_2308.json").write_text(
        '{"run_id":"20260522_2308","status":"completed","decision":"GO"}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["readiness-snapshot"], env=env)

    assert result.exit_code == 0
    assert "Readiness Snapshot" in result.stdout
    assert "next_phase_candidate: Phase 2" in result.stdout
    assert "phase_gate_reason: decision_cleared_and_phase1_gate_complete" in result.stdout
    assert "phase_gate_strict_validation_passed: True" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "issues: none" in result.stdout
    assert "execution_ready: False" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_balance_gap_detected: True" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_state_comparison_entry_count: 4" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "timeline_latest_remediation_planner_status: stalled" in result.stdout
    assert (
        "timeline_latest_remediation_session_next_pending_command: uv run sis monitoring-status"
        in result.stdout
    )
    assert (
        "timeline_latest_remediation_scoreboard_feedback_priority_reason: evaluation_failed"
        in result.stdout
    )
    assert "## Quick Navigation" in result.stdout
    assert "phase_gate_review_report: data/reports/phase_gate_review.md" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "phase_gate_review_report: data/reports/phase_gate_review.md" in result.stdout
    assert "## Restart Pointers" in result.stdout
    assert "remediation_scoreboard_report:" in result.stdout
    assert "current_state_index_report:" in result.stdout
    assert (data_dir / "reports/readiness_snapshot.md").exists()
    assert (data_dir / "ops/readiness_snapshot.json").exists()
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout


def test_operations_timeline_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"daemon_dry_run","status":"planned","mode":"paper","notes":["dry_run","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=planned","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"paper_operations_cycle","status":"completed","mode":"paper","notes":["orders=1","fills=1","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=completed","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["operations-timeline"], env=env)

    assert result.exit_code == 0
    assert "Operations Timeline Report" in result.stdout
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_drift_overview_status: degraded" in result.stdout
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in result.stdout
    assert "latest_execution_gap_history_status: completed" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_state_comparison_status_match: False" in result.stdout
    assert "latest_execution_state_comparison_mismatching_count: 1" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "latest_phase2_entry_allowed: False" in result.stdout
    assert (
        "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears"
        in result.stdout
    )
    assert "latest_phase_gate_strict_validation_passed: False" in result.stdout
    assert "latest_phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "latest_phase_gate_checked_files: 7" in result.stdout
    assert (
        "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    )
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "operations_timeline_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "operations_dashboard_report:" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/operations_timeline_report.md").exists()
    assert (data_dir / "ops/operations_timeline_summary.json").exists()


def test_operations_audit_pack_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir / "ops/operations_bundle_manifest.json": '{"overall_status":"ok"}',
        data_dir
        / "ops/operations_timeline_summary.json": '{"latest_operation":"operations_snapshot","latest_status":"ok","latest_execution_gap_history_status":"ok","latest_execution_gap_history_diagnostics_status":"degraded","latest_readiness_execution_ready":false}',
        data_dir / "ops/paper_cycle_history_summary.json": '{"cycle_count":2,"completed_count":2}',
        data_dir / "ops/paper_operations_runbook_summary.json": '{"monitoring_status":"ok"}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir
        / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir
        / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir
        / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir
        / "ops/execution_drift_overview_summary.json": '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        data_dir
        / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir
        / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
    }
    for path, text in payloads.items():
        path.write_text(text, encoding="utf-8")

    result = runner.invoke(app, ["operations-audit-pack"], env=env)

    assert result.exit_code == 0
    assert "Operations Audit Pack" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_balance_gap_detected: True" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_gap_history_latest_status: ok" in result.stdout
    assert "execution_gap_history_latest_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "execution_drift_overview_status: degraded" in result.stdout
    assert "readiness_next_phase_candidate: Stay Phase 1" in result.stdout
    assert "readiness_execution_ready: False" in result.stdout
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "phase2_entry_allowed: False" in result.stdout
    assert "timeline_latest_execution_gap_history_status: ok" in result.stdout
    assert "timeline_latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "timeline_latest_readiness_execution_ready: False" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "## Quick Navigation" in result.stdout
    assert "operations_audit_pack_report:" in result.stdout
    assert f"phase_gate_review_report: {data_dir / 'reports/phase_gate_review.md'}" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/operations_audit_pack.md").exists()
    assert (data_dir / "ops/operations_audit_pack.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "operations_audit_snapshot"
    assert "execution_snapshot_drift_entry_count=3" in latest["notes"]
    assert "execution_snapshot_drift_latest_status_match=True" in latest["notes"]
    assert "execution_snapshot_drift_mismatching_snapshot_count=1" in latest["notes"]
    assert "execution_drift_overview_status=degraded" in latest["notes"]
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in latest["notes"]
    assert "phase2_entry_allowed=False" in latest["notes"]
    assert "execution_drift_overview_diagnostics_alignment_match=False" in latest["notes"]
    assert "execution_drift_overview_state_comparison_mismatching_count=1" in latest["notes"]
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1" in latest["notes"]


def test_audit_timeline_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_diagnostics_status=degraded","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["audit-timeline"], env=env)

    assert result.exit_code == 0
    assert "Audit Timeline Report" in result.stdout
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_drift_overview_status: degraded" in result.stdout
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in result.stdout
    assert "latest_execution_gap_history_status: ok" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_state_comparison_status_match: False" in result.stdout
    assert "latest_execution_state_comparison_mismatching_count: 1" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert "latest_readiness_execution_ready: False" in result.stdout
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "latest_phase2_entry_allowed: False" in result.stdout
    assert (
        "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears"
        in result.stdout
    )
    assert "latest_phase_gate_strict_validation_passed: False" in result.stdout
    assert "latest_phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "latest_phase_gate_checked_files: 7" in result.stdout
    assert (
        "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    )
    assert (
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"
        in result.stdout
    )
    assert "## Quick Navigation" in result.stdout
    assert "audit_timeline_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "audit_dashboard_report:" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/audit_timeline_report.md").exists()
    assert (data_dir / "ops/audit_timeline_summary.json").exists()


def test_audit_dashboard_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir
        / "ops/operations_bundle_manifest.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir
        / "ops/operations_audit_pack.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir
        / "ops/audit_timeline_summary.json": '{"audit_entry_count":4,"latest_operation":"operations_audit_snapshot","latest_status":"ok","operation_counts":{"operations_snapshot":2,"operations_audit_snapshot":2}}',
        data_dir / "ops/audit_bundle_history_summary.json": '{"snapshot_count":3,"ok_count":3}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir
        / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir
        / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir
        / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        data_dir
        / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir
        / "ops/execution_drift_overview_summary.json": '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        data_dir
        / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir
        / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
    }
    for path, text in payloads.items():
        path.write_text(text, encoding="utf-8")

    result = runner.invoke(app, ["audit-dashboard"], env=env)

    assert result.exit_code == 0
    assert "Audit Dashboard" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_comparison_all_registries_present: True" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_gap_history_latest_status: ok" in result.stdout
    assert "execution_gap_history_latest_diagnostics_status: degraded" in result.stdout
    assert "execution_state_comparison_entry_count: 4" in result.stdout
    assert "execution_state_comparison_latest_status_match: False" in result.stdout
    assert "execution_state_comparison_mismatching_count: 1" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "execution_drift_overview_status: degraded" in result.stdout
    assert "readiness_next_phase_candidate: Stay Phase 1" in result.stdout
    assert "readiness_execution_ready: False" in result.stdout
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "phase2_entry_allowed: False" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/audit_dashboard.md").exists()
    assert (data_dir / "ops/audit_dashboard_summary.json").exists()


def test_audit_bundle_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"created_at":"2026-05-24T00:00:00+00:00","operation":"operations_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","readiness_next_phase=Phase 2","readiness_execution_ready=True"]}',
                '{"created_at":"2026-05-24T01:00:00+00:00","operation":"operations_audit_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
                '{"created_at":"2026-05-24T02:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","readiness_next_phase=Phase 1","readiness_execution_ready=False"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    payloads = {
        data_dir
        / "ops/audit_dashboard_summary.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir
        / "ops/audit_timeline_summary.json": '{"audit_entry_count":5,"latest_operation":"audit_bundle_snapshot","latest_status":"ok","latest_execution_gap_history_status":"ok","latest_execution_gap_history_diagnostics_status":"degraded","latest_readiness_execution_ready":false}',
        data_dir
        / "ops/operations_audit_pack.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir
        / "ops/audit_bundle_history_summary.json": '{"snapshot_count":3,"ok_count":3,"latest_execution_gap_history_status":"ok","latest_execution_gap_history_diagnostics_status":"degraded","latest_readiness_execution_ready":false}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir
        / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir
        / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir
        / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir
        / "ops/execution_drift_overview_summary.json": '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        data_dir
        / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir
        / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true}',
    }
    for path, text in payloads.items():
        path.write_text(text, encoding="utf-8")

    result = runner.invoke(app, ["audit-bundle"], env=env)

    assert result.exit_code == 0
    assert "Audit Bundle Manifest" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "timeline_latest_execution_gap_history_status: ok" in result.stdout
    assert "timeline_latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "execution_drift_overview_status: degraded" in result.stdout
    assert "readiness_next_phase_candidate: Stay Phase 1" in result.stdout
    assert "readiness_execution_ready: False" in result.stdout
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "phase2_entry_allowed: False" in result.stdout
    assert "bundle_history_latest_execution_gap_history_status: ok" in result.stdout
    assert (
        "bundle_history_latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    )
    assert "## Quick Navigation" in result.stdout
    assert "audit_bundle_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/audit_bundle_manifest.md").exists()
    assert (data_dir / "ops/audit_bundle_manifest.json").exists()
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "audit_bundle_snapshot"
    assert "execution_snapshot_drift_entry_count=3" in latest["notes"]
    assert "execution_snapshot_drift_latest_status_match=True" in latest["notes"]
    assert "execution_snapshot_drift_mismatching_snapshot_count=1" in latest["notes"]
    assert "execution_drift_overview_status=degraded" in latest["notes"]
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in latest["notes"]
    assert "phase2_entry_allowed=False" in latest["notes"]
    assert "execution_drift_overview_diagnostics_alignment_match=False" in latest["notes"]
    assert "execution_drift_overview_state_comparison_mismatching_count=1" in latest["notes"]
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1" in latest["notes"]


def test_audit_bundle_history_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        "\n".join(
            [
                '{"run_id":"r1","created_at":"2026-05-24T00:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=ok","execution_drift_overview_diagnostics_alignment_match=True","execution_drift_overview_state_comparison_mismatching_count=0","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=0","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=ok","execution_state_comparison_latest_status_match=True","execution_state_comparison_mismatching_count=0","readiness_next_phase=Phase 2","readiness_execution_ready=True","phase_gate_decision=GO","phase2_entry_allowed=True","phase_gate_reason=decision_cleared_and_phase1_gate_complete","phase_gate_strict_validation_passed=True","phase_gate_strict_validation_issue_count=0","phase_gate_checked_files=7"]}',
                '{"run_id":"r2","created_at":"2026-05-24T01:00:00+00:00","operation":"audit_bundle_snapshot","status":"ok","notes":["overall_status=ok","execution_drift_overview_status=degraded","execution_drift_overview_diagnostics_alignment_match=False","execution_drift_overview_state_comparison_mismatching_count=1","execution_drift_overview_snapshot_drift_mismatching_snapshot_count=1","execution_gap_history_latest_status=ok","execution_gap_history_latest_diagnostics_status=degraded","execution_state_comparison_latest_status_match=False","execution_state_comparison_mismatching_count=1","readiness_next_phase=Phase 1","readiness_execution_ready=False","phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed=False","phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears","phase_gate_strict_validation_passed=False","phase_gate_strict_validation_issue_count=2","phase_gate_checked_files=7","phase_gate_review_report_path=data/reports/phase_gate_review.md","phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"]}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["audit-bundle-history"], env=env)

    assert result.exit_code == 0
    assert "Audit Bundle History Report" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "latest_execution_gap_history_status: ok" in result.stdout
    assert "latest_execution_drift_overview_status: degraded" in result.stdout
    assert "latest_execution_drift_overview_diagnostics_alignment_match: False" in result.stdout
    assert "latest_execution_drift_overview_state_comparison_mismatching_count: 1" in result.stdout
    assert (
        "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1"
        in result.stdout
    )
    assert "latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_state_comparison_status_match: False" in result.stdout
    assert "latest_execution_state_comparison_mismatching_count: 1" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert "latest_readiness_execution_ready: False" in result.stdout
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "latest_phase2_entry_allowed: False" in result.stdout
    assert (
        "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears"
        in result.stdout
    )
    assert "latest_phase_gate_strict_validation_passed: False" in result.stdout
    assert "latest_phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "latest_phase_gate_checked_files: 7" in result.stdout
    assert (
        "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    )
    assert (
        "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field"
        in result.stdout
    )
    assert "## Quick Navigation" in result.stdout
    assert "audit_bundle_history_report:" in result.stdout
    assert "## Related Reports" in result.stdout
    assert "audit_dashboard_report:" in result.stdout
    assert "recommended_read_order_1=docs/CURRENT_STATE.md" in result.stdout
    assert (data_dir / "reports/audit_bundle_history_report.md").exists()
    assert (data_dir / "ops/audit_bundle_history_summary.json").exists()
