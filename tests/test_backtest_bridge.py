from datetime import datetime, timezone

import polars as pl
import pytest

from sis.backtest.signals import load_research_signals
from sis.backtest.bridge import (
    BacktestMetrics,
    run_backtest_bridge,
    run_backtest_bridge_with_decisions,
    write_backtest_metrics_summary_json,
    write_backtest_report,
)


def test_backtest_bridge_runs_virtual_execution_from_quotes(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "exec_buy_price": 100.0,
                "exec_sell_price": 99.9,
                "mark_price": None,
                "mid_price": 100.0,
                "oracle_price": 100.0,
                "index_price": None,
                "spread_bps": 1.0,
                "oracle_ts_ms": 1779415479000,
                "market_status": "open",
                "is_tradable": True,
            },
            {
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "exec_buy_price": 105.0,
                "exec_sell_price": 104.9,
                "mark_price": None,
                "mid_price": 105.0,
                "oracle_price": 105.0,
                "index_price": None,
                "spread_bps": 1.0,
                "oracle_ts_ms": 1779429879000,
                "market_status": "open",
                "is_tradable": True,
            },
        ]
    ).write_parquet(quotes_path)

    metrics = run_backtest_bridge(quotes_path)

    assert len(metrics) == 1
    assert metrics[0].trade_count == 1
    assert metrics[0].total_return > 0
    assert metrics[0].cost_drag_bps == 1.0


def test_backtest_bridge_uses_cost_matrix_when_available(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    cost_matrix_path = tmp_path / "venue_cost_matrix.csv"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "exec_buy_price": None,
                "exec_sell_price": None,
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
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "exec_buy_price": None,
                "exec_sell_price": None,
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
    ).write_parquet(quotes_path)
    cost_matrix_path.write_text(
        "venue,symbol,open_fee_bps,close_fee_bps,spread_p50_bps,holding_cost_4h_bps\n"
        "gtrade,SPY,5,5,9,3\n",
        encoding="utf-8",
    )

    metrics = run_backtest_bridge(quotes_path, cost_matrix_path=cost_matrix_path)

    assert metrics[0].cost_drag_bps == 15.0


def test_backtest_report_writes_metrics_table(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    report_path = tmp_path / "backtest_report.md"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "exec_buy_price": None,
                "exec_sell_price": None,
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
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "exec_buy_price": None,
                "exec_sell_price": None,
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
    ).write_parquet(quotes_path)

    metrics = run_backtest_bridge(quotes_path)
    write_backtest_report(
        metrics,
        report_path,
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
        },
        execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
            "report_path": "data/reports/execution_snapshot.md",
        },
        execution_comparison_summary={
            "all_registries_present": True,
            "report_path": "data/reports/execution_venue_comparison.md",
        },
        execution_diagnostics_summary={
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
            "report_path": "data/reports/execution_venue_diagnostics.md",
        },
        execution_gap_history_summary={
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "report_path": "data/reports/execution_gap_history.md",
        },
        execution_state_comparison_summary={
            "entry_count": 4,
            "latest_status_match": False,
            "mismatching_count": 1,
            "report_path": "data/reports/execution_state_comparison_history.md",
        },
        execution_snapshot_drift_summary={
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_snapshot_drift_history.md",
        },
    )

    text = report_path.read_text(encoding="utf-8")
    assert "Backtest Bridge Report" in text
    assert "SPY" in text
    assert "Audit Summary" in text
    assert "overall_status: ok" in text
    assert "Phase Gate Summary" in text
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "Execution Snapshot" in text
    assert "Execution Venue Comparison" in text
    assert "all_registries_present: True" in text
    assert "Execution Venue Diagnostics" in text
    assert "balance_gap_detected: True" in text
    assert "Execution Gap History" in text
    assert "entry_count: 4" in text
    assert "Execution State Comparison History" in text
    assert "mismatching_count: 1" in text
    assert "Execution Snapshot Drift History" in text
    assert "mismatching_snapshot_count: 1" in text


def test_backtest_bridge_uses_research_signal_csv(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    signals_path = tmp_path / "signals.csv"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "exec_buy_price": 100.0,
                "exec_sell_price": 99.9,
                "mark_price": None,
                "mid_price": 100.0,
                "oracle_price": 100.0,
                "index_price": None,
                "spread_bps": 1.0,
                "oracle_ts_ms": 1779415479000,
                "market_status": "open",
                "is_tradable": True,
            },
            {
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "exec_buy_price": 105.0,
                "exec_sell_price": 104.9,
                "mark_price": None,
                "mid_price": 105.0,
                "oracle_price": 105.0,
                "index_price": None,
                "spread_bps": 1.0,
                "oracle_ts_ms": 1779429879000,
                "market_status": "open",
                "is_tradable": True,
            },
        ]
    ).write_parquet(quotes_path)
    signals_path.write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength\n"
        "2026-05-22T00:00:00+00:00,XAU,long,4h,1.0\n",
        encoding="utf-8",
    )

    metrics = run_backtest_bridge(quotes_path, signals_path)

    assert len(metrics) == 1
    assert metrics[0].trade_count == 1
    assert metrics[0].exposure_ratio == 1.0
    assert metrics[0].total_return > 0


def test_backtest_bridge_writes_decision_artifacts_for_signal_mode(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    signals_path = tmp_path / "signals.csv"
    decision_log_path = tmp_path / "decision_logs" / "backtest.jsonl"
    decision_summary_path = tmp_path / "decision_summary.json"
    pl.DataFrame(
        [
            {
                "ts_client": datetime(2026, 5, 22, 0, 0, tzinfo=timezone.utc).isoformat(),
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
                "ts_client": datetime(2026, 5, 22, 4, 0, tzinfo=timezone.utc).isoformat(),
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
    ).write_parquet(quotes_path)
    signals_path.write_text(
        "ts_signal,canonical_symbol,side,timeframe,signal_strength\n"
        "2026-05-22T00:00:00+00:00,QQQ,long,4h,1.0\n",
        encoding="utf-8",
    )

    metrics, records, summary = run_backtest_bridge_with_decisions(
        quotes_path,
        signals_path,
        decision_log_path=decision_log_path,
        decision_summary_path=decision_summary_path,
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
        },
        readiness_summary={
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
        },
        execution_drift_overview_summary={
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        },
        execution_summary={"execution_overall_status": "ok", "execution_venue_count": 2},
        execution_comparison_summary={"execution_comparison_all_registries_present": True},
        execution_diagnostics_summary={
            "execution_diagnostics_status": "degraded",
            "execution_balance_gap_detected": True,
            "execution_fills_gap_detected": False,
        },
        execution_gap_history_summary={
            "execution_gap_history_entry_count": 4,
            "execution_gap_history_latest_status": "ok",
            "execution_gap_history_latest_execution_diagnostics_status": "degraded",
        },
        execution_state_comparison_summary={
            "execution_state_comparison_entry_count": 4,
            "execution_state_comparison_latest_status_match": False,
            "execution_state_comparison_mismatching_count": 1,
        },
        execution_snapshot_drift_summary={
            "execution_snapshot_drift_entry_count": 3,
            "execution_snapshot_drift_latest_execution_state_comparison_status_match": True,
            "execution_snapshot_drift_mismatching_snapshot_count": 1,
        },
        timeline_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        timeline_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": True,
        },
        bundle_history_latest_execution_summary={
            "execution_overall_status": "warn",
            "execution_venue_count": 1,
        },
        bundle_history_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": False,
        },
        cycle_history_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        cycle_history_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": True,
        },
    )

    assert len(metrics) == 1
    assert len(records) == 1
    assert summary["executed_count"] == 1
    assert decision_log_path.exists()
    assert decision_summary_path.exists()
    assert '"action":"enter_long"' in decision_log_path.read_text(encoding="utf-8")
    assert '"mode": "signal_driven"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"audit"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"phase_gate"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"readiness_summary"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"next_phase_candidate": "Stay Phase 1"' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_drift_overview_summary"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"execution_drift_overview_status": "degraded"' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"overall_status": "degraded"' in decision_summary_path.read_text(encoding="utf-8")
    assert (
        '"execution_drift_overview_state_comparison_mismatching_count": 1'
        in decision_summary_path.read_text(encoding="utf-8")
    )
    assert '"execution_summary"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"execution_overall_status": "ok"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"execution_gap_history_summary"' in decision_summary_path.read_text(encoding="utf-8")
    assert '"execution_gap_history_entry_count": 4' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_state_comparison_summary"' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_state_comparison_mismatching_count": 1' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"execution_snapshot_drift_summary"' in decision_summary_path.read_text(encoding="utf-8")
    assert (
        '"execution_snapshot_drift_mismatching_snapshot_count": 1'
        in decision_summary_path.read_text(encoding="utf-8")
    )
    assert '"timeline_latest_execution_summary"' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"bundle_history_latest_execution_summary"' in decision_summary_path.read_text(
        encoding="utf-8"
    )
    assert '"cycle_history_latest_execution_summary"' in decision_summary_path.read_text(
        encoding="utf-8"
    )


def test_research_signal_loader_blocks_scalping_timeframes(tmp_path) -> None:
    signals_path = tmp_path / "signals.csv"
    signals_path.write_text(
        "ts_signal,canonical_symbol,side,timeframe\n2026-05-22T00:00:00+00:00,SPY,long,5m\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="BLOCK_SCALPING_TIMEFRAME"):
        load_research_signals(signals_path)


def test_write_backtest_metrics_summary_json_includes_current_state(tmp_path) -> None:
    metrics = [
        BacktestMetrics(
            venue="gtrade",
            canonical_symbol="QQQ",
            trade_count=2,
            avg_trade_return=0.03,
            total_return=0.06,
            annual_return=0.12,
            sharpe=1.1,
            max_drawdown=-0.01,
            win_rate=0.5,
            profit_factor=1.5,
            worst_trade=-0.02,
            cost_drag_bps=7.0,
            cost_source="matrix",
            stale_rejected_count=1,
            halt_rejected_count=0,
            exposure_ratio=1.0,
        )
    ]
    out = tmp_path / "backtest_metrics_summary.json"

    write_backtest_metrics_summary_json(
        metrics,
        out,
        audit_summary={
            "overall_status": "ok",
            "latest_operation": "audit_bundle_snapshot",
            "bundle_history_snapshot_count": 3,
        },
        phase_gate_summary={
            "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
            "phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears",
            "strict_validation_passed": True,
        },
        readiness_summary={
            "next_phase_candidate": "Stay Phase 1",
            "execution_ready": False,
            "phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
            "phase2_entry_allowed": False,
        },
        execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
            "report_path": "data/reports/execution_snapshot.md",
        },
        execution_comparison_summary={
            "all_registries_present": True,
            "report_path": "data/reports/execution_venue_comparison.md",
        },
        execution_diagnostics_summary={
            "overall_status": "degraded",
            "balance_gap_detected": True,
            "fills_gap_detected": False,
            "report_path": "data/reports/execution_venue_diagnostics.md",
        },
        execution_gap_history_summary={
            "entry_count": 4,
            "latest_status": "ok",
            "latest_execution_diagnostics_status": "degraded",
            "report_path": "data/reports/execution_gap_history.md",
        },
        execution_state_comparison_summary={
            "entry_count": 4,
            "latest_status_match": False,
            "mismatching_count": 1,
            "report_path": "data/reports/execution_state_comparison_history.md",
        },
        execution_snapshot_drift_summary={
            "entry_count": 3,
            "latest_execution_state_comparison_status_match": True,
            "mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_snapshot_drift_history.md",
        },
        execution_drift_overview_summary={
            "overall_status": "degraded",
            "diagnostics_alignment_match": False,
            "state_comparison_mismatching_count": 1,
            "snapshot_drift_mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_drift_overview.md",
        },
        timeline_latest_execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
        },
        timeline_latest_execution_comparison_summary={
            "all_registries_present": True,
        },
        bundle_history_latest_execution_summary={
            "overall_status": "warn",
            "venue_count": 1,
        },
        bundle_history_latest_execution_comparison_summary={
            "all_registries_present": False,
        },
        cycle_history_latest_execution_summary={
            "overall_status": "ok",
            "venue_count": 2,
        },
        cycle_history_latest_execution_comparison_summary={
            "all_registries_present": True,
        },
    )

    text = out.read_text(encoding="utf-8")
    assert '"total_trade_count": 2' in text
    assert '"audit"' in text
    assert '"phase_gate"' in text
    assert '"phase_gate_decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"' in text
    assert '"phase_gate_reason": "remain_in_phase1_until_live_evidence_gate_clears"' in text
    assert '"phase_gate_strict_validation_passed": true' in text
    assert '"phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears"' in text
    assert '"readiness_summary"' in text
    assert '"readiness_next_phase_candidate": "Stay Phase 1"' in text
    assert '"execution"' in text
    assert '"execution_comparison"' in text
    assert '"execution_diagnostics"' in text
    assert '"execution_gap_history_summary"' in text
    assert '"execution_gap_history_entry_count": 4' in text
    assert '"execution_state_comparison_summary"' in text
    assert '"execution_state_comparison_mismatching_count": 1' in text
    assert '"execution_snapshot_drift_summary"' in text
    assert '"execution_snapshot_drift_mismatching_snapshot_count": 1' in text
    assert '"execution_drift_overview_summary"' in text
    assert '"execution_drift_overview_status": "degraded"' in text
    assert '"execution_drift_overview_state_comparison_mismatching_count": 1' in text
    assert '"execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1' in text
    assert '"timeline_latest_execution_summary"' in text
    assert '"bundle_history_latest_execution_summary"' in text
    assert '"cycle_history_latest_execution_summary"' in text
