import json

from sis.reports.evidence import build_evidence_card
from sis.storage.jsonl_store import write_json


def test_evidence_card_reflects_current_go_no_go_report(tmp_path) -> None:
    data_dir = tmp_path / "data"
    write_json(
        data_dir / "registry/gtrade_instrument_registry.json",
        [{"venue": "gtrade", "canonical_symbol": "SPY"}],
    )
    write_json(
        data_dir / "registry/ostium_instrument_registry.json",
        [
            {
                "venue": "ostium",
                "canonical_symbol": "SPX_EQUIV",
                "venue_symbol": "US500-USD",
                "active": True,
                "opening_fee_bps": 3,
                "max_open_interest": "1000000",
                "rollover_fee_per_block": "1e-10",
                "max_leverage": 50,
            }
        ],
    )
    write_json(
        data_dir / "raw/sidecar/ostium/positions_all_2026-05-22.json",
        {
            "positions": [
                {
                    "venue_symbol": "US500-USD",
                    "side": "long",
                    "entry_px": "100",
                    "liquidation_px": "80",
                }
            ]
        },
    )
    (data_dir / "raw/quotes/gtrade").mkdir(parents=True)
    (data_dir / "raw/quotes/gtrade/2026-05-22.jsonl").write_text('{"venue":"gtrade"}\n')
    (data_dir / "normalized").mkdir(parents=True)
    (data_dir / "normalized/quotes.parquet").write_bytes(b"placeholder")
    (data_dir / "research").mkdir(parents=True)
    (data_dir / "research/venue_cost_matrix.csv").write_text(
        "\n".join(
            [
                "venue,symbol,stale_rate,tradable_rate,spread_p90_bps,holding_cost_4h_bps,holding_cost_24h_bps,holding_cost_72h_bps",
                "gtrade,SPY,0,0,2,0,0,0",
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        data_dir / "research/backtest_metrics.json",
        [{"trade_count": 1, "avg_trade_return": 0.1}],
    )
    (data_dir / "research/backtest_report.md").write_text("# Backtest\n", encoding="utf-8")
    (data_dir / "research/go_no_go_report.md").write_text("# Go/No-Go\n", encoding="utf-8")

    card_path = build_evidence_card(
        data_dir,
        data_dir / "evidence",
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
        timeline_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        timeline_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": "True",
        },
        bundle_history_latest_execution_summary={
            "execution_overall_status": "warn",
            "execution_venue_count": 1,
        },
        bundle_history_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": "False",
        },
        cycle_history_latest_execution_summary={
            "execution_overall_status": "ok",
            "execution_venue_count": 2,
        },
        cycle_history_latest_execution_comparison_summary={
            "execution_comparison_all_registries_present": "True",
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
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
            "report_path": "data/reports/execution_drift_overview.md",
        },
    )

    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert card["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert card["venue_decisions"]
    assert {item["venue"] for item in card["venue_decisions"]} == {"gtrade", "ostium"}
    assert card["blockers"] == ["tradable_rate at or above threshold"]
    assert card["audit_summary"]["overall_status"] == "ok"
    assert card["phase_gate_summary"]["decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert card["phase_gate_summary"]["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert card["phase_gate_summary"]["phase2_entry_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert card["phase_gate_summary"]["phase_gate_strict_validation_passed"] is True
    assert card["phase_gate_decision"] == "CONDITIONAL_GO_NEEDS_LIVE_WINDOW"
    assert card["phase2_entry_allowed"] is False
    assert card["phase_gate_reason"] == "remain_in_phase1_until_live_evidence_gate_clears"
    assert card["phase_gate_strict_validation_passed"] is True
    assert card["strict_validation_passed"] is True
    assert card["readiness_summary"]["next_phase_candidate"] == "Stay Phase 1"
    assert card["readiness_summary"]["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert card["readiness_summary"]["readiness_execution_ready"] is False
    assert card["readiness_next_phase_candidate"] == "Stay Phase 1"
    assert card["readiness_execution_ready"] is False
    assert card["timeline_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert card["timeline_latest_execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert card["timeline_latest_execution_overall_status"] == "ok"
    assert card["timeline_latest_execution_venue_count"] == 2
    assert card["timeline_latest_execution_comparison_all_registries_present"] is True
    assert card["bundle_history_latest_execution_summary"]["execution_overall_status"] == "warn"
    assert card["bundle_history_latest_execution_comparison_summary"]["execution_comparison_all_registries_present"] is False
    assert card["bundle_history_latest_execution_overall_status"] == "warn"
    assert card["bundle_history_latest_execution_venue_count"] == 1
    assert card["bundle_history_latest_execution_comparison_all_registries_present"] is False
    assert card["cycle_history_latest_execution_summary"]["execution_overall_status"] == "ok"
    assert card["cycle_history_latest_execution_comparison_summary"]["execution_comparison_all_registries_present"] is True
    assert card["cycle_history_latest_execution_overall_status"] == "ok"
    assert card["cycle_history_latest_execution_venue_count"] == 2
    assert card["cycle_history_latest_execution_comparison_all_registries_present"] is True
    assert card["execution_summary"]["overall_status"] == "ok"
    assert card["execution_summary"]["venue_count"] == 2
    assert card["execution_comparison_summary"]["all_registries_present"] is True
    assert card["execution_diagnostics_summary"]["balance_gap_detected"] is True
    assert card["execution_gap_history_summary"]["execution_gap_history_entry_count"] == 4
    assert card["execution_gap_history_entry_count"] == 4
    assert card["execution_state_comparison_summary"]["execution_state_comparison_mismatching_count"] == 1
    assert card["execution_state_comparison_mismatching_count"] == 1
    assert card["execution_snapshot_drift_summary"]["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert card["execution_snapshot_drift_mismatching_snapshot_count"] == 1
    assert card["execution_drift_overview_summary"]["overall_status"] == "degraded"
    assert card["execution_drift_overview_summary"]["execution_drift_overview_status"] == "degraded"
    assert card["execution_drift_overview_summary"]["execution_drift_overview_diagnostics_alignment_match"] is False
    assert card["execution_drift_overview_status"] == "degraded"
    assert card["execution_drift_overview_diagnostics_alignment_match"] is False
    assert card["execution_drift_overview_state_comparison_mismatching_count"] == 1
    assert card["execution_drift_overview_snapshot_drift_mismatching_snapshot_count"] == 1
    assert card["quick_navigation"]["evidence_card_report"] == str(card_path)
    assert card["quick_navigation"]["phase_gate_review_report"] == str(
        data_dir / "reports/phase_gate_review.md"
    )
    assert (
        card["related_reports"]["execution_snapshot_report"]
        == "data/reports/execution_snapshot.md"
    )
    assert (
        card["related_reports"]["paper_vs_backtest_comparison_report"]
        == str(data_dir / "reports/paper_vs_backtest_comparison.md")
    )
    assert "Liquidation reference complete" in [
        item["criterion"] for item in card["criteria"]
    ]
    assert next(
        item["result"]
        for item in card["criteria"]
        if item["criterion"] == "Liquidation reference complete"
    ) == "PASS"
    assert "Ostium liquidation reference requires real open position data" not in json.dumps(card)
