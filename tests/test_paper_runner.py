from __future__ import annotations

from datetime import datetime, timezone

import polars as pl

from sis.paper.runner import run_paper_step
from sis.state.store import StateStore


def _write_inputs(data_dir) -> None:
    (data_dir / "normalized").mkdir(parents=True, exist_ok=True)
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
    (data_dir / "research").mkdir(parents=True, exist_ok=True)
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


def test_run_paper_step_writes_stateful_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_inputs(data_dir)
    (data_dir / "ops").mkdir(parents=True, exist_ok=True)
    (data_dir / "ops/audit_dashboard_summary.json").write_text(
        '{"overall_status":"ok","timeline_latest_operation":"audit_bundle_snapshot","timeline_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"timeline_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":"True"}}',
        encoding="utf-8",
    )
    (data_dir / "ops/audit_bundle_manifest.json").write_text(
        '{"bundle_history_snapshot_count":3,"bundle_history_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"bundle_history_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":"True"}}',
        encoding="utf-8",
    )
    (data_dir / "ops/operations_bundle_manifest.json").write_text(
        '{"cycle_history_latest_execution_summary":{"execution_overall_status":"ok","execution_venue_count":2},"cycle_history_latest_execution_comparison_summary":{"execution_comparison_all_registries_present":"True"}}',
        encoding="utf-8",
    )
    (data_dir / "ops/phase_gate_review_summary.json").write_text(
        '{"decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false,"phase2_entry_reason":"remain_in_phase1_until_live_evidence_gate_clears","strict_validation_passed":true,"strict_validation_issue_count":2,"checked_files":7}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_drift_overview_summary.json").write_text(
        '{"execution_drift_overview_status":"degraded","execution_drift_overview_diagnostics_alignment_match":false,"execution_drift_overview_state_comparison_mismatching_count":1,"execution_drift_overview_snapshot_drift_mismatching_snapshot_count":1}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_summary.json").write_text(
        '{"execution_overall_status":"ok","execution_venue_count":2,"execution_report_path":"data/reports/execution_snapshot.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_comparison_summary.json").write_text(
        '{"execution_comparison_all_registries_present":true,"execution_comparison_report_path":"data/reports/execution_venue_comparison.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_venue_diagnostics_summary.json").write_text(
        '{"execution_diagnostics_status":"degraded","execution_balance_gap_detected":true,"execution_fills_gap_detected":false,"execution_diagnostics_report_path":"data/reports/execution_venue_diagnostics.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_gap_history_summary.json").write_text(
        '{"execution_gap_history_entry_count":4,"execution_gap_history_latest_status":"ok","execution_gap_history_latest_diagnostics_status":"degraded","execution_gap_history_report_path":"data/reports/execution_gap_history.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_state_comparison_history_summary.json").write_text(
        '{"execution_state_comparison_entry_count":4,"execution_state_comparison_latest_status_match":false,"execution_state_comparison_mismatching_count":1,"execution_state_comparison_report_path":"data/reports/execution_state_comparison_history.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/execution_snapshot_drift_history_summary.json").write_text(
        '{"execution_snapshot_drift_entry_count":3,"execution_snapshot_drift_latest_status_match":true,"execution_snapshot_drift_mismatching_snapshot_count":1,"execution_snapshot_drift_report_path":"data/reports/execution_snapshot_drift_history.md"}',
        encoding="utf-8",
    )
    (data_dir / "ops/readiness_snapshot.json").write_text(
        '{"readiness_next_phase_candidate":"Stay Phase 1","readiness_execution_ready":false,"phase_gate_decision":"CONDITIONAL_GO_NEEDS_LIVE_WINDOW","phase2_entry_allowed":false}',
        encoding="utf-8",
    )
    state_path = data_dir / "state/marketlens.sqlite"

    summary = run_paper_step(data_dir, state_path=state_path)

    assert summary.orders_count == 1
    assert summary.fills_count == 1
    assert summary.open_positions == 1
    assert summary.orders_path.exists()
    assert summary.fills_path.exists()
    assert summary.positions_path.exists()
    assert summary.daily_pnl_path.exists()
    assert summary.report_path.exists()
    report_text = summary.report_path.read_text(encoding="utf-8")
    assert "Audit Summary" in report_text
    assert "overall_status: ok" in report_text
    assert "Phase Gate Summary" in report_text
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in report_text
    assert "Readiness Summary" in report_text
    assert "next_phase_candidate: Stay Phase 1" in report_text
    assert "Audit Timeline Latest Execution" in report_text
    assert "Audit Bundle History Latest Execution" in report_text
    assert "Cycle History Latest Execution" in report_text
    assert "Execution Gap History" in report_text
    assert "entry_count: 4" in report_text
    assert "Execution State Comparison History" in report_text
    assert "mismatching_count: 1" in report_text
    assert "Execution Snapshot Drift History" in report_text
    assert "mismatching_snapshot_count: 1" in report_text
    assert "Execution Drift Overview" in report_text
    assert "overall_status: degraded" in report_text

    store = StateStore(state_path)
    payload = store.get_json("paper_last_run")
    assert isinstance(payload, dict)
    assert payload["orders_count"] == 1
    assert payload["audit"]["overall_status"] == "ok"
    assert payload["audit_summary"]["overall_status"] == "ok"
    assert payload["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        payload["timeline_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert payload["timeline_latest_execution_overall_status"] == "ok"
    assert payload["timeline_latest_execution_venue_count"] == 2
    assert payload["timeline_latest_execution_comparison_all_registries_present"] is True
    assert payload["bundle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert (
        payload["bundle_history_latest_execution_comparison_summary"][
            "execution_comparison_all_registries_present"
        ]
        is True
    )
    assert payload["bundle_history_latest_execution_overall_status"] == "ok"
    assert payload["bundle_history_latest_execution_venue_count"] == 2
    assert payload["bundle_history_latest_execution_comparison_all_registries_present"] is True
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
    assert payload["phase_gate"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert payload["phase_gate_summary"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert payload["phase_gate"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert payload["phase_gate"]["phase2_entry_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert payload["phase_gate"]["phase_gate_strict_validation_passed"] is True
    assert payload["phase_gate"]["phase_gate_strict_validation_issue_count"] == 2
    assert payload["phase_gate"]["phase_gate_checked_files"] == 7
    assert payload["phase_gate"]["strict_validation_issue_count"] == 2
    assert payload["phase_gate"]["checked_files"] == 7
    assert payload["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert payload["phase2_entry_allowed"] is False
    assert payload["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert payload["phase_gate_strict_validation_passed"] is True
    assert payload["phase_gate_strict_validation_issue_count"] == 2
    assert payload["phase_gate_checked_files"] == 7
    assert payload["strict_validation_passed"] is True
    assert payload["readiness_summary"]["next_phase_candidate"] == "Stay Phase 1"
    assert payload["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert payload["readiness_summary"]["readiness_execution_ready"] is False
    assert payload["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert payload["readiness_execution_ready"] is False
    assert payload["execution_summary"]["execution_overall_status"] == "ok"
    assert payload["execution_summary"]["execution_venue_count"] == 2
    assert payload["execution_summary"]["report_path"] == str(data_dir / "reports/execution_snapshot.md")
    assert payload["execution_overall_status"] == "ok"
    assert payload["execution_venue_count"] == 2
    assert payload["execution_report_path"] == str(data_dir / "reports/execution_snapshot.md")
    assert payload["execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert (
        payload["execution_comparison_summary"]["report_path"]
        == str(data_dir / "reports/execution_venue_comparison.md")
    )
    assert payload["execution_comparison_all_registries_present"] is True
    assert payload["execution_comparison_report_path"] == str(
        data_dir / "reports/execution_venue_comparison.md"
    )
    assert payload["execution_diagnostics_summary"]["execution_diagnostics_status"] == "degraded"
    assert payload["execution_diagnostics_summary"]["execution_balance_gap_detected"] is True
    assert payload["execution_diagnostics_summary"]["execution_fills_gap_detected"] is False
    assert (
        payload["execution_diagnostics_summary"]["report_path"]
        == str(data_dir / "reports/execution_venue_diagnostics.md")
    )
    assert payload["execution_diagnostics_status"] == "degraded"
    assert payload["execution_balance_gap_detected"] is True
    assert payload["execution_fills_gap_detected"] is False
    assert payload["execution_diagnostics_report_path"] == str(
        data_dir / "reports/execution_venue_diagnostics.md"
    )
    assert payload["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert payload["execution_gap_history_summary"]["execution_gap_history_latest_status"] == "ok"
    assert (
        payload["execution_gap_history_summary"]["execution_gap_history_latest_diagnostics_status"]
        == "degraded"
    )
    assert payload["execution_gap_history_report_path"] == str(
        data_dir / "reports/execution_gap_history.md"
    )
    assert (
        payload["execution_state_comparison_summary"]["execution_state_comparison_latest_status_match"]
        is False
    )
    assert payload["execution_state_comparison_mismatching_count"] == 1
    assert (
        payload["execution_state_comparison_report_path"]
        == str(data_dir / "reports/execution_state_comparison_history.md")
    )
    assert payload["execution_snapshot_drift_summary"]["execution_snapshot_drift_entry_count"] == 3
    assert payload["execution_snapshot_drift_summary"]["execution_snapshot_drift_latest_status_match"] is True
    assert payload["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert (
        payload["execution_snapshot_drift_report_path"]
        == str(data_dir / "reports/execution_snapshot_drift_history.md")
    )
    assert payload["execution_drift_overview_summary"]["overall_status"] == "degraded"
    assert payload["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert payload["execution_drift_overview_summary"]["execution_drift_overview_diagnostics_alignment_match"] is False
    assert payload["execution_drift_overview_status"] == "degraded"
    assert payload["execution_drift_overview_diagnostics_alignment_match"] is False
    assert payload["execution_drift_overview_state_comparison_mismatching_count"] == 1
    assert payload["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] == 1
    assert store.get_json("paper_positions")


def test_run_paper_step_restores_existing_positions(tmp_path) -> None:
    data_dir = tmp_path / "data"
    _write_inputs(data_dir)
    state_path = data_dir / "state/marketlens.sqlite"
    store = StateStore(state_path)
    store.set_json(
        "paper_positions",
        [
            {
                "venue": "gtrade",
                "canonical_symbol": "QQQ",
                "side": "long",
                "quantity": 1.0,
                "avg_entry_price": 99.0,
                "opened_at": "2026-05-21T00:00:00+00:00",
                "updated_at": "2026-05-21T00:00:00+00:00",
                "realized_pnl": 0.0,
            }
        ],
    )

    summary = run_paper_step(data_dir, state_path=state_path)

    assert summary.open_positions == 1
    positions = pl.read_parquet(summary.positions_path)
    assert positions.height == 1
    assert positions["quantity"][0] == 2.0
