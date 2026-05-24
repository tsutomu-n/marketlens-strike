from typer.testing import CliRunner
from datetime import datetime, timezone

from sis.cli import app
from sis.ops.manifest_chain import latest_operation_manifest
from sis.storage.jsonl_store import read_jsonl


runner = CliRunner()


def test_help_smoke() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "probe" in result.stdout
    assert "build-backtest" in result.stdout
    assert "ingest-research-data" in result.stdout
    assert "build-feature-panel" in result.stdout
    assert "build-signals" in result.stdout
    assert "paper-step" in result.stdout
    assert "estimate-order" in result.stdout
    assert "balance-status" in result.stdout
    assert "fill-status" in result.stdout
    assert "execution-snapshot" in result.stdout
    assert "execution-gap-history" in result.stdout
    assert "execution-state-comparison-history" in result.stdout
    assert "execution-snapshot-drift-history" in result.stdout
    assert "execution-drift-overview" in result.stdout
    assert "order-status" in result.stdout
    assert "cancel-order" in result.stdout
    assert "close-position" in result.stdout
    assert "reconcile-positions" in result.stdout
    assert "healthcheck" in result.stdout
    assert "kill-switch" in result.stdout
    assert "schedule-run" in result.stdout
    assert "render-alert" in result.stdout
    assert "weekly-review" in result.stdout
    assert "daemon-manifest" in result.stdout
    assert "daemon-dry-run" in result.stdout
    assert "export-state" in result.stdout
    assert "restore-state" in result.stdout
    assert "lifecycle-report" in result.stdout
    assert "monitoring-status" in result.stdout
    assert "comparison-report" in result.stdout
    assert "ops-review" in result.stdout
    assert "operations-dashboard" in result.stdout
    assert "paper-operations-runbook" in result.stdout
    assert "paper-cycle-history" in result.stdout
    assert "operations-bundle" in result.stdout
    assert "operations-timeline" in result.stdout
    assert "operations-audit-pack" in result.stdout
    assert "audit-timeline" in result.stdout
    assert "audit-dashboard" in result.stdout
    assert "audit-bundle" in result.stdout
    assert "audit-bundle-history" in result.stdout
    assert "phase-gate-review" in result.stdout
    assert "paper-operations-cycle" in result.stdout
    assert "refresh-operations-artifacts" in result.stdout
    assert "log-quotes" in result.stdout


def test_check_timeframe_cli_blocks_scalping() -> None:
    result = runner.invoke(app, ["check-timeframe", "1m"])
    assert result.exit_code == 2
    assert "BLOCK_SCALPING_TIMEFRAME" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_implementation_status_reports_complete_scope() -> None:
    result = runner.invoke(app, ["implementation-status"])
    assert result.exit_code == 0
    assert "Backtest bridge" in result.stdout
    assert "Ostium liquidation reference" in result.stdout
    assert "PARTIAL" not in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_diagnose_quotes_exits_when_no_quotes() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["diagnose-quotes"], env={"SIS_DATA_DIR": "tmp_data"})
        assert result.exit_code == 2
        assert "No quote rows found for diagnostics." in result.stdout


def test_market_session_cli_for_qqq() -> None:
    result = runner.invoke(app, ["market-session", "--venue", "gtrade", "--symbol", "QQQ"])
    assert result.exit_code == 0
    assert "symbol=QQQ" in result.stdout
    assert "calendar=XNYS" in result.stdout
    assert "next_open_jst=" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_next_live_window_cli_for_xau() -> None:
    result = runner.invoke(app, ["next-live-window", "--venue", "gtrade", "--symbol", "XAU"])
    assert result.exit_code == 0
    assert "symbol=XAU" in result.stdout
    assert "calendar=GTRADE_COMMODITY" in result.stdout
    assert "recommended_start_jst=" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_estimate_order_cli_for_gtrade(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry = data_dir / "registry/gtrade_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text('[{"canonical_symbol":"QQQ","opening_fee_bps":5}]', encoding="utf-8")

    result = runner.invoke(
        app,
        ["estimate-order", "--venue", "gtrade", "--symbol", "QQQ", "--side", "long"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "estimated_cost_bps=5.0" in result.stdout
    assert "price_reference=mark" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_balance_status_cli_for_gtrade(tmp_path) -> None:
    data_dir = tmp_path / "data"
    execution = data_dir / "execution"
    registry = data_dir / "registry/gtrade_instrument_registry.json"
    execution.mkdir(parents=True, exist_ok=True)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text("[]", encoding="utf-8")
    (execution / "gtrade_balance.json").write_text(
        '{"currency":"USD","equity":1500.0,"available_cash":1200.0}',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["balance-status", "--venue", "gtrade"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "venue=gtrade" in result.stdout
    assert "equity=1500.0" in result.stdout
    assert "available_cash=1200.0" in result.stdout
    assert "balance_snapshot_exists=True" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_fill_status_cli_for_gtrade(tmp_path) -> None:
    data_dir = tmp_path / "data"
    execution = data_dir / "execution"
    registry = data_dir / "registry/gtrade_instrument_registry.json"
    execution.mkdir(parents=True, exist_ok=True)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text("[]", encoding="utf-8")
    (execution / "gtrade_fills.json").write_text(
        '[{"fill_id":"fill-1","order_id":"ord-1","canonical_symbol":"QQQ","side":"long","quantity":1,"price":100.5,"status":"filled","ts_fill":"2026-05-24T00:00:00+00:00"}]',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["fill-status", "--venue", "gtrade", "--limit", "10"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "venue=gtrade" in result.stdout
    assert "fills_count=1" in result.stdout
    assert "fill_1_id=fill-1" in result.stdout
    assert "fill_1_symbol=QQQ" in result.stdout
    assert "fill_1_price=100.5" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_execution_snapshot_cli_for_gtrade(tmp_path) -> None:
    data_dir = tmp_path / "data"
    execution = data_dir / "execution"
    registry = data_dir / "registry/gtrade_instrument_registry.json"
    execution.mkdir(parents=True, exist_ok=True)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text("[]", encoding="utf-8")
    (execution / "gtrade_balance.json").write_text(
        '{"currency":"USD","equity":1500.0,"available_cash":1200.0}',
        encoding="utf-8",
    )
    (execution / "gtrade_order_status.json").write_text(
        '[{"order_id":"ord-1","canonical_symbol":"QQQ","side":"long","quantity":1,"status":"working"}]',
        encoding="utf-8",
    )
    (execution / "gtrade_fills.json").write_text(
        '[{"fill_id":"fill-1","order_id":"ord-1","canonical_symbol":"QQQ","side":"long","quantity":1,"price":100.5,"status":"filled","ts_fill":"2026-05-24T00:00:00+00:00"}]',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["execution-snapshot", "--venue", "gtrade", "--fills-limit", "5", "--order-limit", "5"],
        env={"SIS_DATA_DIR": str(data_dir)},
    )

    assert result.exit_code == 0
    assert "Execution Snapshot" in result.stdout
    assert "## Venue: gtrade" in result.stdout
    assert "balance_equity: 1500.0" in result.stdout
    assert "latest_fill_id: fill-1" in result.stdout
    assert "latest_order_id: ord-1" in result.stdout
    assert (data_dir / "reports/execution_snapshot.md").exists()
    assert (data_dir / "ops/execution_snapshot_summary.json").exists()


def test_execution_venue_comparison_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"overall_status":"ok","venue_count":2,"venues":[{"venue":"gtrade","registry_exists":true,"balance_snapshot_exists":true,"fills_snapshot_exists":true,"order_status_snapshot_exists":true,"positions_count":0,"fills_count":1,"order_status_count":1,"balance":{"equity":1000,"currency":"USD"}},{"venue":"ostium","registry_exists":true,"balance_snapshot_exists":false,"fills_snapshot_exists":false,"order_status_snapshot_exists":true,"positions_count":1,"fills_count":0,"order_status_count":1,"balance":{"equity":null,"currency":"USD"}}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-venue-comparison"], env=env)

    assert result.exit_code == 0
    assert "Execution Venue Comparison" in result.stdout
    assert "all_registries_present: True" in result.stdout
    assert (data_dir / "reports/execution_venue_comparison.md").exists()
    assert (data_dir / "ops/execution_venue_comparison_summary.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_execution_venue_diagnostics_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"venues":[{"venue":"gtrade","registry_exists":true,"balance_snapshot_exists":true,"fills_snapshot_exists":true,"order_status_snapshot_exists":true,"positions_count":0,"fills_count":1,"order_status_count":1,"balance_equity":1000.0,"balance_currency":"USD"},{"venue":"ostium","registry_exists":true,"balance_snapshot_exists":false,"fills_snapshot_exists":false,"order_status_snapshot_exists":true,"positions_count":2,"fills_count":0,"order_status_count":2,"balance_equity":995.0,"balance_currency":"USD"}]}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["execution-venue-diagnostics"], env=env)

    assert result.exit_code == 0
    assert "Execution Venue Diagnostics" in result.stdout
    assert "balance_gap_detected: True" in result.stdout
    assert (data_dir / "reports/execution_venue_diagnostics.md").exists()
    assert (data_dir / "ops/execution_venue_diagnostics_summary.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_kill_switch_and_healthcheck_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
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
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        encoding="utf-8",
    )

    enable = runner.invoke(app, ["kill-switch", "--enable", "--reason", "test"], env=env)
    assert enable.exit_code == 0
    assert "enabled=True" in enable.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in enable.stdout

    health = runner.invoke(app, ["healthcheck", "--current-pnl", "-150", "--daily-loss-limit", "100"], env=env)
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
    assert "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field" in health.stdout
    assert "execution_drift_overview_status=degraded" in health.stdout
    assert "readiness_next_phase_candidate=Stay Phase 1" in health.stdout
    assert "daily_loss_allowed=False" in health.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in health.stdout


def test_order_status_cancel_and_close_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    registry = data_dir / "registry/gtrade_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text("[]", encoding="utf-8")
    execution_dir = data_dir / "execution"
    execution_dir.mkdir(parents=True, exist_ok=True)
    (execution_dir / "gtrade_order_status.json").write_text(
        '[{"order_id":"ord-1","canonical_symbol":"QQQ","side":"long","quantity":1,"status":"working"}]',
        encoding="utf-8",
    )
    env = {"SIS_DATA_DIR": str(data_dir)}

    status = runner.invoke(app, ["order-status", "--venue", "gtrade", "--order-id", "ord-1"], env=env)
    cancel = runner.invoke(app, ["cancel-order", "--venue", "gtrade", "--order-id", "ord-1"], env=env)
    close = runner.invoke(app, ["close-position", "--venue", "gtrade", "--symbol", "QQQ", "--side", "long"], env=env)

    assert status.exit_code == 0
    assert "status=working" in status.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in status.stdout
    assert cancel.exit_code == 0
    assert "status=blocked_read_only" in cancel.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in cancel.stdout
    assert close.exit_code == 0
    assert "status=blocked_read_only" in close.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in close.stdout


def test_paper_report_cli_includes_audit_summary(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)
    from sis.state.store import StateStore
    import polars as pl

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
    assert "Execution Drift Overview" in result.stdout
    assert "overall_status: degraded" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
        ["schedule-run", "--run-type", "paper", "--command", "uv run sis paper-step", "--every-minutes", "30"],
        env=env,
    )
    alert = runner.invoke(
        app,
        ["render-alert", "--level", "warn", "--title", "Stale", "--body", "recollect"],
        env=env,
    )
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)
    import polars as pl
    pl.DataFrame([{"venue": "gtrade", "canonical_symbol": "QQQ", "trade_count": 1}]).write_json(
        data_dir / "research/backtest_metrics.json"
    )
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 1.0, "fills_count": 1, "open_positions": 1}]).write_parquet(
        data_dir / "paper/daily_pnl.parquet"
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
    weekly = runner.invoke(app, ["weekly-review"], env=env)

    assert schedule.exit_code == 0
    assert "run_type=paper" in schedule.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in schedule.stdout
    assert '"overall_status": "ok"' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase2_entry_allowed": false' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"balance_gap_detected": true' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"next_phase_candidate": "Stay Phase 1"' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"balance_gap_detected": true' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"next_phase_candidate": "Stay Phase 1"' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert alert.exit_code == 0
    assert "[WARN] Stale" in alert.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in alert.stdout
    assert weekly.exit_code == 0
    assert "Weekly Strategy Review" in weekly.stdout
    assert "Paper Last Run Audit" in weekly.stdout
    assert "Paper Last Run Phase Gate" in weekly.stdout
    assert "Paper Last Run Execution Drift Overview" in weekly.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in weekly.stdout


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
    (data_dir / "reports/weekly_strategy_review.md").write_text("# Weekly Strategy Review\n\n- sample\n", encoding="utf-8")
    lifecycle = runner.invoke(app, ["lifecycle-report"], env=env)

    assert daemon.exit_code == 0
    assert "mode=paper" in daemon.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in daemon.stdout
    assert export_.exit_code == 0
    assert "state_snapshot.json" in export_.stdout
    assert "audit_overall_status=ok" in export_.stdout
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in export_.stdout
    assert "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears" in export_.stdout
    assert "phase_gate_strict_validation_passed=True" in export_.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in export_.stdout
    assert restore.exit_code == 0
    assert "restored=true" in restore.stdout
    assert "audit_latest_operation=audit_bundle_snapshot" in restore.stdout
    assert "phase_gate_decision=CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in restore.stdout
    assert "phase_gate_reason=remain_in_phase1_until_live_evidence_gate_clears" in restore.stdout
    assert "phase_gate_strict_validation_passed=True" in restore.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in restore.stdout
    assert lifecycle.exit_code == 0
    assert "Strategy Lifecycle Report" in lifecycle.stdout
    assert "Paper Last Run Audit" in lifecycle.stdout
    assert "Paper Last Run Phase Gate" in lifecycle.stdout
    assert "Paper Last Run Execution Drift Overview" in lifecycle.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in lifecycle.stdout


def test_daemon_dry_run_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
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
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase_gate_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
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

    result = runner.invoke(
        app,
        ["daemon-dry-run", "--mode", "paper", "--command", "uv run sis paper-step", "--every-minutes", "30"],
        env=env,
    )

    assert result.exit_code == 0
    assert "status=planned" in result.stdout
    assert "operation_chain=" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "ops/operation_manifests.jsonl").exists()
    assert '"overall_status": "ok"' in (data_dir / "ops/daemon_dry_run.json").read_text(encoding="utf-8")
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/daemon_dry_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/daemon_dry_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase2_entry_allowed": false' in (data_dir / "ops/daemon_dry_run.json").read_text(encoding="utf-8")
    assert '"decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"balance_gap_detected": true' in (data_dir / "ops/daemon_dry_run.json").read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in (data_dir / "ops/daemon_dry_run.json").read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in (
        data_dir / "ops/daemon_dry_run.json"
    ).read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in (data_dir / "ops/daemon_dry_run.json").read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in (
        data_dir / "ops/scheduled_run.json"
    ).read_text(encoding="utf-8")
    assert '"readiness_execution_ready": false' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"next_phase_candidate": "Stay Phase 1"' in (data_dir / "ops/daemon_dry_run.json").read_text(encoding="utf-8")
    assert '"balance_gap_detected": true' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")
    assert '"next_phase_candidate": "Stay Phase 1"' in (data_dir / "ops/scheduled_run.json").read_text(encoding="utf-8")


def test_monitoring_status_and_comparison_report_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "research/decision_summary.json").write_text('{"mode":"signal_driven","executed_count":1}', encoding="utf-8")
    (data_dir / "reports/weekly_strategy_review.md").write_text("# Weekly Strategy Review\n", encoding="utf-8")
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
    import polars as pl
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
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 2.0}]).write_parquet(data_dir / "paper/daily_pnl.parquet")
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
    assert "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field" in monitoring.stdout
    assert "execution_drift_overview_status=degraded" in monitoring.stdout
    assert "readiness_next_phase_candidate=Stay Phase 1" in monitoring.stdout
    assert "operation_chain_exists=False" in monitoring.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in monitoring.stdout
    assert comparison.exit_code == 0
    assert "Paper vs Backtest Comparison" in comparison.stdout
    assert "Paper Last Run Audit" in comparison.stdout
    assert "Paper Last Run Phase Gate" in comparison.stdout
    assert "Paper Last Run Execution Drift Overview" in comparison.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in comparison.stdout


def test_build_backtest_cli_includes_audit_summary(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    from sis.state.store import StateStore
    import polars as pl

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
    assert "Phase Gate Summary" in (data_dir / "research/backtest_report.md").read_text(encoding="utf-8")
    assert "Execution Venue Comparison" in (data_dir / "research/backtest_report.md").read_text(encoding="utf-8")
    assert "Execution Venue Diagnostics" in (data_dir / "research/backtest_report.md").read_text(encoding="utf-8")
    assert '"phase_gate"' in (data_dir / "research/decision_summary.json").read_text(encoding="utf-8")
    assert (data_dir / "research/backtest_metrics_summary.json").exists()
    assert '"phase_gate"' in (data_dir / "research/backtest_metrics_summary.json").read_text(encoding="utf-8")
    assert '"execution"' in (data_dir / "research/backtest_metrics_summary.json").read_text(encoding="utf-8")
    assert '"execution_comparison"' in (data_dir / "research/backtest_metrics_summary.json").read_text(encoding="utf-8")
    assert '"execution_diagnostics"' in (data_dir / "research/backtest_metrics_summary.json").read_text(encoding="utf-8")
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
    (data_dir / "registry/gtrade_instrument_registry.json").write_text('[{"venue":"gtrade","canonical_symbol":"SPY"}]', encoding="utf-8")
    (data_dir / "registry/ostium_instrument_registry.json").write_text(
        '[{"venue":"ostium","canonical_symbol":"SPX_EQUIV","venue_symbol":"US500-USD","active":true,"opening_fee_bps":3,"max_open_interest":"1000000","rollover_fee_per_block":"1e-10","max_leverage":50}]',
        encoding="utf-8",
    )
    (data_dir / "raw/sidecar/ostium/positions_all_2026-05-22.json").write_text(
        '{"positions":[{"venue_symbol":"US500-USD","side":"long","entry_px":"100","liquidation_px":"80"}]}',
        encoding="utf-8",
    )
    (data_dir / "raw/quotes/gtrade/2026-05-22.jsonl").write_text('{"venue":"gtrade"}\n', encoding="utf-8")
    (data_dir / "normalized/quotes.parquet").write_bytes(b"placeholder")
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,stale_rate,tradable_rate,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps\n"
        "gtrade,SPY,0,0,2,0,0,0\n",
        encoding="utf-8",
    )
    (data_dir / "research/backtest_metrics.json").write_text('[{"trade_count":1,"avg_trade_return":0.1}]', encoding="utf-8")
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

    result = runner.invoke(app, ["build-evidence-card"], env=env)

    assert result.exit_code == 0
    evidence_cards = sorted((data_dir / "evidence").glob("evidence_card_*.json"))
    assert evidence_cards
    payload = json.loads(evidence_cards[-1].read_text(encoding="utf-8"))
    assert payload["audit_summary"]["overall_status"] == "ok"
    assert payload["phase_gate_summary"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert payload["execution_summary"]["overall_status"] == "ok"
    assert payload["execution_summary"]["venue_count"] == 2
    assert payload["execution_comparison_summary"]["all_registries_present"] is True
    assert payload["execution_diagnostics_summary"]["balance_gap_detected"] is True
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_normalize_and_build_cost_matrix_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    raw_quote = data_dir / "raw/quotes/gtrade/2026-05-22.jsonl"
    raw_quote.parent.mkdir(parents=True, exist_ok=True)
    raw_quote.write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.0,"index_price":100.0,"spread_bps":2.0,"market_status":"open","is_tradable":true,"source":"test","raw_payload_sha256":"a"}',
                '{"ts_client":"2026-05-22T00:05:00+00:00","venue":"gtrade","canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"mark_price":100.5,"index_price":100.5,"spread_bps":3.0,"market_status":"open","is_tradable":false,"source":"test","raw_payload_sha256":"b"}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    normalize = runner.invoke(app, ["normalize-quotes"], env=env)
    build = runner.invoke(app, ["build-cost-matrix"], env=env)

    assert normalize.exit_code == 0
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in normalize.stdout
    assert (data_dir / "normalized/quotes.parquet").exists()
    assert build.exit_code == 0
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in build.stdout
    assert (data_dir / "research/venue_cost_matrix.csv").exists()


def test_build_event_calendar_and_check_research_quality_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    import polars as pl

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
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in event_calendar.stdout
    assert (data_dir / "research/event_calendar.parquet").exists()
    assert quality.exit_code == 0
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in quality.stdout
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
    assert "gtrade_max_age_ms=" in halt.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in halt.stdout
    assert validate.exit_code == 0
    assert "checked_files=5" in validate.stdout
    assert "issues=0" in validate.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in validate.stdout


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
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
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

    result = runner.invoke(app, ["phase-gate-review"], env=env)

    assert result.exit_code == 0
    assert "Phase Gate Review" in result.stdout
    assert "phase2_entry_allowed: True" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_comparison_all_registries_present: True" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_gap_history_entry_count: 4" in result.stdout
    assert "execution_gap_history_latest_status: ok" in result.stdout
    assert "execution_gap_history_latest_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "execution_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
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
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
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
    (data_dir / "reports/paper_vs_backtest_comparison.md").write_text("# comparison\n", encoding="utf-8")
    (data_dir / "reports/weekly_strategy_review.md").write_text("# weekly\n", encoding="utf-8")
    (data_dir / "reports/strategy_lifecycle_report.md").write_text("# lifecycle\n", encoding="utf-8")

    result = runner.invoke(app, ["operations-dashboard"], env=env)

    assert result.exit_code == 0
    assert "Operations Dashboard" in result.stdout
    assert "Recommended Read Order" in result.stdout
    assert "execution_overall_status: ok" in result.stdout
    assert "execution_comparison_all_registries_present: True" in result.stdout
    assert "execution_diagnostics_status: degraded" in result.stdout
    assert "execution_snapshot_drift_entry_count: 3" in result.stdout
    assert "execution_snapshot_drift_latest_status_match: True" in result.stdout
    assert "audit_latest_operation: audit_bundle_snapshot" in result.stdout
    assert "phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "reports/operations_dashboard.md").exists()
    assert (data_dir / "ops/operations_dashboard_summary.json").exists()
    assert '"recommended_read_order"' in (data_dir / "ops/operations_dashboard_summary.json").read_text(encoding="utf-8")


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
    (data_dir / "ops/operations_dashboard_summary.json").write_text('{"overall_status":"ok"}', encoding="utf-8")

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
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "reports/paper_operations_runbook.md").exists()
    assert (data_dir / "ops/paper_operations_runbook_summary.json").exists()


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
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
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
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert (data_dir / "reports/execution_gap_history.md").exists()
    assert (data_dir / "ops/execution_gap_history_summary.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: ok" in result.stdout
    assert "latest_status_match: False" in result.stdout
    assert (data_dir / "reports/execution_state_comparison_history.md").exists()
    assert (data_dir / "ops/execution_state_comparison_history_summary.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
    assert "latest_execution_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: ok" in result.stdout
    assert "latest_execution_state_comparison_status_match: False" in result.stdout
    assert (data_dir / "reports/execution_snapshot_drift_history.md").exists()
    assert (data_dir / "ops/execution_snapshot_drift_history_summary.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
    assert "overall_status: ok" in result.stdout
    assert (data_dir / "reports/execution_drift_overview.md").exists()
    assert (data_dir / "ops/execution_drift_overview_summary.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
        data_dir / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        data_dir / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir / "ops/paper_operations_runbook_summary.json": '{"monitoring_status":"ok"}',
        data_dir / "ops/paper_cycle_history_summary.json": '{"cycle_count":2,"completed_count":2}',
        data_dir / "ops/phase_gate_review_summary.json": '{"decision":"GO","phase2_entry_allowed":true,"phase2_entry_reason":"decision_cleared_and_phase1_gate_complete","strict_validation_passed":true,"strict_validation_issue_count":0,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[]}',
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
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "reports/operations_bundle_manifest.md").exists()
    assert (data_dir / "ops/operations_bundle_manifest.json").exists()
    assert '"recommended_read_order"' in (data_dir / "ops/operations_bundle_manifest.json").read_text(encoding="utf-8")
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
        data_dir / "ops/audit_dashboard_summary.json": '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot"}',
        data_dir / "ops/audit_bundle_manifest.json": '{"bundle_history_snapshot_count":3}',
        data_dir / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_gap_history_diagnostics_status":"degraded","latest_status_match":true,"mismatching_count":0}',
        data_dir / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":0}',
        data_dir / "research/backtest_metrics_summary.json": '{"total_trade_count":5,"symbols":["QQQ","SPY"]}',
        data_dir / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
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
    assert (data_dir / "reports/current_state_index.md").exists()
    assert (data_dir / "ops/current_state_index.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


def test_readiness_snapshot_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir / "ops/current_state_index.json": '{"overall_status":"ok","research_quality_report_exists":true}',
        data_dir / "ops/phase_gate_review_summary.json": '{"decision":"GO","phase2_entry_allowed":true,"phase2_entry_reason":"decision_cleared_and_phase1_gate_complete","strict_validation_passed":true,"strict_validation_issue_count":0,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[]}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_gap_history_diagnostics_status":"degraded","latest_status_match":true,"mismatching_count":0}',
        data_dir / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_status":"ok","latest_execution_diagnostics_status":"degraded","latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
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
    assert (data_dir / "reports/readiness_snapshot.md").exists()
    assert (data_dir / "ops/readiness_snapshot.json").exists()
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout


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
    assert "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in result.stdout
    assert "latest_phase_gate_strict_validation_passed: False" in result.stdout
    assert "latest_phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "latest_phase_gate_checked_files: 7" in result.stdout
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "- data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "reports/operations_timeline_report.md").exists()
    assert (data_dir / "ops/operations_timeline_summary.json").exists()


def test_operations_audit_pack_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir / "ops/operations_bundle_manifest.json": '{"overall_status":"ok"}',
        data_dir / "ops/operations_timeline_summary.json": '{"latest_operation":"operations_snapshot","latest_status":"ok","latest_execution_gap_history_status":"ok","latest_execution_gap_history_diagnostics_status":"degraded","latest_readiness_execution_ready":false}',
        data_dir / "ops/paper_cycle_history_summary.json": '{"cycle_count":2,"completed_count":2}',
        data_dir / "ops/paper_operations_runbook_summary.json": '{"monitoring_status":"ok"}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir / "ops/execution_drift_overview_summary.json": '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        data_dir / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
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
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
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
    assert "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in result.stdout
    assert "latest_phase_gate_strict_validation_passed: False" in result.stdout
    assert "latest_phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "latest_phase_gate_checked_files: 7" in result.stdout
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "reports/audit_timeline_report.md").exists()
    assert (data_dir / "ops/audit_timeline_summary.json").exists()


def test_audit_dashboard_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    payloads = {
        data_dir / "ops/operations_bundle_manifest.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir / "ops/operations_audit_pack.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir / "ops/audit_timeline_summary.json": '{"audit_entry_count":4,"latest_operation":"operations_audit_snapshot","latest_status":"ok","operation_counts":{"operations_snapshot":2,"operations_audit_snapshot":2}}',
        data_dir / "ops/audit_bundle_history_summary.json": '{"snapshot_count":3,"ok_count":3}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir / "ops/execution_state_comparison_history_summary.json": '{"entry_count":4,"latest_status_match":false,"mismatching_count":1}',
        data_dir / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir / "ops/execution_drift_overview_summary.json": '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        data_dir / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7,"phase_gate_review_report_path":"data/reports/phase_gate_review.md","phase_gate_strict_validation_issues":[{"path":"data/research/backtest_metrics_summary.json","message":"missing field"}]}',
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
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
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
        data_dir / "ops/audit_dashboard_summary.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir / "ops/audit_timeline_summary.json": '{"audit_entry_count":5,"latest_operation":"audit_bundle_snapshot","latest_status":"ok","latest_execution_gap_history_status":"ok","latest_execution_gap_history_diagnostics_status":"degraded","latest_readiness_execution_ready":false}',
        data_dir / "ops/operations_audit_pack.json": '{"overall_status":"ok","cycle_count":2,"completed_cycle_count":2}',
        data_dir / "ops/audit_bundle_history_summary.json": '{"snapshot_count":3,"ok_count":3,"latest_execution_gap_history_status":"ok","latest_execution_gap_history_diagnostics_status":"degraded","latest_readiness_execution_ready":false}',
        data_dir / "ops/execution_snapshot_summary.json": '{"overall_status":"ok","venue_count":2}',
        data_dir / "ops/execution_venue_comparison_summary.json": '{"all_registries_present":true}',
        data_dir / "ops/execution_venue_diagnostics_summary.json": '{"overall_status":"degraded","balance_gap_detected":true,"fills_gap_detected":false}',
        data_dir / "ops/execution_gap_history_summary.json": '{"entry_count":4,"latest_status":"ok","latest_execution_diagnostics_status":"degraded"}',
        data_dir / "ops/execution_snapshot_drift_history_summary.json": '{"entry_count":3,"latest_execution_state_comparison_status_match":true,"mismatching_snapshot_count":1}',
        data_dir / "ops/execution_drift_overview_summary.json": '{"overall_status":"degraded","diagnostics_alignment_match":false,"state_comparison_mismatching_count":1,"snapshot_drift_mismatching_snapshot_count":1}',
        data_dir / "ops/readiness_snapshot.json": '{"next_phase_candidate":"Stay Phase 1","execution_ready":false}',
        data_dir / "ops/phase_gate_review_summary.json": '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true}',
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
    assert "bundle_history_latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
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
    assert "latest_execution_drift_overview_snapshot_drift_mismatching_snapshot_count: 1" in result.stdout
    assert "latest_execution_gap_history_diagnostics_status: degraded" in result.stdout
    assert "latest_execution_state_comparison_status_match: False" in result.stdout
    assert "latest_execution_state_comparison_mismatching_count: 1" in result.stdout
    assert "latest_readiness_next_phase: Phase 1" in result.stdout
    assert "latest_readiness_execution_ready: False" in result.stdout
    assert "latest_phase_gate_decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in result.stdout
    assert "latest_phase2_entry_allowed: False" in result.stdout
    assert "latest_phase_gate_reason: remain_in_phase1_until_live_evidence_gate_clears" in result.stdout
    assert "latest_phase_gate_strict_validation_passed: False" in result.stdout
    assert "latest_phase_gate_strict_validation_issue_count: 2" in result.stdout
    assert "latest_phase_gate_checked_files: 7" in result.stdout
    assert "latest_phase_gate_review_report_path: data/reports/phase_gate_review.md" in result.stdout
    assert "phase_gate_issue_1=data/research/backtest_metrics_summary.json: missing field" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "reports/audit_bundle_history_report.md").exists()
    assert (data_dir / "ops/audit_bundle_history_summary.json").exists()


def test_refresh_operations_artifacts_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "paper").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/operation_manifests.jsonl").write_text(
        '{"operation":"daemon_dry_run","status":"planned","scheduled_for":"2026-05-24T12:30:00+00:00","command":"uv run sis paper-step","artifacts":["a.json"],"notes":["dry_run"]}\n',
        encoding="utf-8",
    )
    (data_dir / "ops/daemon_dry_run.json").write_text('{"status":"planned"}', encoding="utf-8")
    (data_dir / "registry").mkdir(parents=True, exist_ok=True)
    (data_dir / "registry/gtrade_instrument_registry.json").write_text("[]", encoding="utf-8")
    (data_dir / "registry/ostium_instrument_registry.json").write_text("[]", encoding="utf-8")
    (data_dir / "research/decision_summary.json").write_text(
        '{"mode":"signal_driven","executed_count":1,"blocked_count":0}',
        encoding="utf-8",
    )
    import polars as pl
    pl.DataFrame([{"canonical_symbol": "QQQ", "avg_trade_return": 0.05}]).write_json(
        data_dir / "research/backtest_metrics.json"
    )
    pl.DataFrame([{"date": "2026-05-24", "realized_pnl": 2.0, "fills_count": 1, "open_positions": 1}]).write_parquet(
        data_dir / "paper/daily_pnl.parquet"
    )

    result = runner.invoke(app, ["refresh-operations-artifacts"], env=env)

    assert result.exit_code == 0
    assert "monitoring_status=ok" in result.stdout
    assert "execution_snapshot_path=" in result.stdout
    assert "execution_comparison_path=" in result.stdout
    assert "execution_diagnostics_path=" in result.stdout
    assert "execution_gap_history_path=" in result.stdout
    assert "execution_state_comparison_history_path=" in result.stdout
    assert "execution_snapshot_drift_history_path=" in result.stdout
    assert "execution_drift_overview_path=" in result.stdout
    assert "Operations Dashboard" in result.stdout
    assert "runbook_path=" in result.stdout
    assert "phase_gate_review_path=" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert "readiness_snapshot_path=" in result.stdout
    assert (data_dir / "reports/weekly_strategy_review.md").exists()
    assert (data_dir / "reports/paper_vs_backtest_comparison.md").exists()
    assert (data_dir / "reports/strategy_lifecycle_report.md").exists()
    assert (data_dir / "ops/monitoring_status.json").exists()
    assert (data_dir / "reports/ops_review_report.md").exists()
    assert (data_dir / "reports/operations_dashboard.md").exists()
    assert (data_dir / "reports/paper_operations_runbook.md").exists()
    assert (data_dir / "reports/phase_gate_review.md").exists()
    assert (data_dir / "reports/execution_gap_history.md").exists()
    assert (data_dir / "reports/execution_state_comparison_history.md").exists()
    assert (data_dir / "reports/execution_snapshot_drift_history.md").exists()
    assert (data_dir / "reports/execution_drift_overview.md").exists()
    assert (data_dir / "reports/paper_cycle_history_report.md").exists()
    assert (data_dir / "reports/operations_bundle_manifest.md").exists()
    assert (data_dir / "reports/operations_timeline_report.md").exists()
    assert (data_dir / "reports/operations_audit_pack.md").exists()
    assert (data_dir / "reports/audit_timeline_report.md").exists()
    assert (data_dir / "reports/audit_dashboard.md").exists()
    assert (data_dir / "reports/audit_bundle_manifest.md").exists()
    assert (data_dir / "reports/audit_bundle_history_report.md").exists()
    assert (data_dir / "reports/execution_snapshot.md").exists()
    assert (data_dir / "reports/execution_venue_comparison.md").exists()
    assert (data_dir / "reports/execution_venue_diagnostics.md").exists()
    assert (data_dir / "reports/current_state_index.md").exists()
    assert (data_dir / "reports/readiness_snapshot.md").exists()
    assert (data_dir / "ops/execution_snapshot_summary.json").exists()
    assert (data_dir / "ops/execution_venue_comparison_summary.json").exists()
    assert (data_dir / "ops/execution_venue_diagnostics_summary.json").exists()
    assert (data_dir / "ops/execution_gap_history_summary.json").exists()
    assert (data_dir / "ops/execution_state_comparison_history_summary.json").exists()
    assert (data_dir / "ops/execution_snapshot_drift_history_summary.json").exists()
    assert (data_dir / "ops/execution_drift_overview_summary.json").exists()
    assert (data_dir / "ops/current_state_index.json").exists()
    assert (data_dir / "ops/readiness_snapshot.json").exists()


def test_paper_operations_cycle_cli(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "registry").mkdir(parents=True, exist_ok=True)
    (data_dir / "registry/gtrade_instrument_registry.json").write_text("[]", encoding="utf-8")
    (data_dir / "registry/ostium_instrument_registry.json").write_text("[]", encoding="utf-8")
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot"}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3}',
        encoding="utf-8",
    )
    import polars as pl
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc),
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "venue_symbol": "QQQ/USD",
                "exec_buy_price": 100.0,
                "exec_sell_price": 99.9,
                "mark_price": 100.5,
                "index_price": 100.4,
                "mid_price": None,
                "oracle_price": None,
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
                "index_price": 101.0,
                "mid_price": None,
                "oracle_price": None,
                "spread_bps": 2.0,
                "oracle_ts_ms": 1779429879000,
                "market_status": "open",
                "is_tradable": True,
            }
        ]
    ).write_parquet(data_dir / "normalized/quotes.parquet")
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "venue,symbol,open_fee_bps,close_fee_bps,spread_p50_bps,holding_cost_4h_bps\n"
        "gtrade,QQQ,5,5,2,1\n",
        encoding="utf-8",
    )
    (data_dir / "research/signals.csv").write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength,strategy_name,reason\n"
        "2026-05-22T00:00:00+00:00,QQQ,long,4h,1.0,qqq_trend_rates_vix,test\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["paper-operations-cycle"], env=env)

    assert result.exit_code == 0
    assert "orders=1" in result.stdout
    assert "fills=1" in result.stdout
    assert "monitoring_status=ok" in result.stdout
    assert "execution_snapshot_path=" in result.stdout
    assert "execution_comparison_path=" in result.stdout
    assert "execution_diagnostics_path=" in result.stdout
    assert "execution_gap_history_path=" in result.stdout
    assert "execution_state_comparison_history_path=" in result.stdout
    assert "execution_snapshot_drift_history_path=" in result.stdout
    assert "execution_drift_overview_path=" in result.stdout
    assert "cycle_manifest_path=" in result.stdout
    assert "phase_gate_review_path=" in result.stdout
    assert "current_state_index_path=" in result.stdout
    assert "readiness_snapshot_path=" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
    assert (data_dir / "paper/orders.parquet").exists()
    assert (data_dir / "reports/operations_dashboard.md").exists()
    assert (data_dir / "reports/execution_state_comparison_history.md").exists()
    assert (data_dir / "reports/execution_snapshot_drift_history.md").exists()
    assert (data_dir / "reports/execution_drift_overview.md").exists()
    assert (data_dir / "reports/paper_operations_runbook.md").exists()
    assert (data_dir / "reports/phase_gate_review.md").exists()
    assert (data_dir / "reports/execution_snapshot.md").exists()
    assert (data_dir / "reports/execution_venue_comparison.md").exists()
    assert (data_dir / "reports/execution_venue_diagnostics.md").exists()
    assert (data_dir / "reports/execution_gap_history.md").exists()
    assert (data_dir / "reports/current_state_index.md").exists()
    assert (data_dir / "reports/readiness_snapshot.md").exists()
    assert (data_dir / "ops/paper_operations_cycle_summary.json").exists()
    assert (data_dir / "ops/execution_snapshot_summary.json").exists()
    assert (data_dir / "ops/execution_venue_comparison_summary.json").exists()
    assert (data_dir / "ops/execution_venue_diagnostics_summary.json").exists()
    assert (data_dir / "ops/execution_gap_history_summary.json").exists()
    assert (data_dir / "ops/execution_snapshot_drift_history_summary.json").exists()
    assert (data_dir / "ops/execution_drift_overview_summary.json").exists()
    assert (data_dir / "ops/current_state_index.json").exists()
    assert (data_dir / "ops/readiness_snapshot.json").exists()
    assert (data_dir / "reports/paper_cycle_history_report.md").exists()
    assert (data_dir / "reports/operations_bundle_manifest.md").exists()
    assert (data_dir / "reports/operations_timeline_report.md").exists()
    assert (data_dir / "reports/operations_audit_pack.md").exists()
    assert (data_dir / "reports/audit_timeline_report.md").exists()
    assert (data_dir / "reports/audit_dashboard.md").exists()
    assert (data_dir / "reports/audit_bundle_manifest.md").exists()
    assert (data_dir / "reports/audit_bundle_history_report.md").exists()
    assert '"overall_status": "ok"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"phase_gate_decision": null' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"phase_gate_strict_validation_passed": null' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"execution_drift_overview_summary"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"readiness_summary"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"phase_gate_review"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"readiness_snapshot"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"execution_venue_comparison"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"execution_venue_diagnostics"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"execution_state_comparison_history_summary"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"execution_snapshot_drift_history_summary"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"execution_drift_overview_summary"' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"phase_gate": {' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    assert '"phase2_entry_reason": null' in (data_dir / "ops/paper_operations_cycle_summary.json").read_text(encoding="utf-8")
    entries = list(read_jsonl(data_dir / "ops/operation_manifests.jsonl"))
    cycle_entry = next(item for item in reversed(entries) if item.get("operation") == "paper_operations_cycle")
    notes = cycle_entry.get("notes", [])
    assert "execution_diagnostics_status=degraded" in notes
    assert "execution_gap_history_entry_count=0" in notes
    assert "execution_gap_history_latest_status=None" in notes
    assert "execution_snapshot_drift_entry_count=0" in notes
    assert "execution_snapshot_drift_latest_status_match=None" in notes
    assert "execution_snapshot_drift_mismatching_snapshot_count=0" in notes
    assert "execution_drift_overview_status=None" in notes
    assert "execution_drift_overview_diagnostics_alignment_match=None" in notes
    assert "execution_drift_overview_state_comparison_mismatching_count=None" in notes
    assert "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=None" in notes
    assert "execution_gap_history_latest_diagnostics_status=None" in notes
    assert "execution_state_comparison_entry_count=0" in notes
    assert "execution_state_comparison_latest_status_match=None" in notes
    assert "execution_state_comparison_mismatching_count=0" in notes
    assert "readiness_next_phase=None" in notes
    assert "readiness_execution_ready=None" in notes
    latest = latest_operation_manifest(data_dir / "ops/operation_manifests.jsonl")
    assert latest is not None
    assert latest["operation"] == "audit_bundle_snapshot"
    assert latest["status"] == "ok"


def test_reconcile_positions_cli_records_result(tmp_path) -> None:
    data_dir = tmp_path / "data"
    env = {"SIS_DATA_DIR": str(data_dir)}
    registry = data_dir / "registry/ostium_instrument_registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text('[{"canonical_symbol":"SPY","venue_symbol":"US500-USD","opening_fee_bps":3}]', encoding="utf-8")
    positions_root = data_dir / "raw/sidecar/ostium"
    positions_root.mkdir(parents=True, exist_ok=True)
    (positions_root / "positions_2026-05-24.json").write_text(
        '{"positions":[{"venue_symbol":"US500-USD","side":"long","size":"2","entry_px":"100","liquidation_px":"80"}]}',
        encoding="utf-8",
    )
    state_dir = data_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    from sis.state.store import StateStore

    StateStore(state_dir / "marketlens.sqlite").set_json(
        "paper_positions",
        [
            {
                "venue": "ostium",
                "canonical_symbol": "SPY",
                "side": "long",
                "quantity": 2.0,
                "avg_entry_price": 100.0,
                "opened_at": "2026-05-21T00:00:00+00:00",
                "updated_at": "2026-05-21T00:00:00+00:00",
                "realized_pnl": 0.0,
            }
        ],
    )

    result = runner.invoke(app, ["reconcile-positions", "--venue", "ostium"], env=env)

    assert result.exit_code == 0
    assert "matched=1" in result.stdout
    assert "missing_in_adapter=0" in result.stdout
    assert "recommended_read_order_1=docs/ACCEPTANCE_AUDIT.md" in result.stdout
