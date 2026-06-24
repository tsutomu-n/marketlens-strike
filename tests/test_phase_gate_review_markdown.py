from sis.reports.phase_gate_review_markdown import render_phase_gate_review_markdown


def _phase_gate_summary() -> dict[str, object]:
    return {
        "current_phase": "Phase 1",
        "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
        "individual_stock_decision": "disabled_index_only",
        "index_only_decision": "enabled",
        "strict_validation_passed": False,
        "strict_validation_issue_count": 1,
        "checked_files": 7,
        "phase_gate_strict_validation_issues": [
            {"path": "data/research/backtest_metrics_summary.json", "message": "missing field"}
        ],
        "latest_manifest_status": "completed",
        "phase2_entry_allowed": False,
        "phase2_entry_reason": "remain_in_phase1_until_live_evidence_gate_clears",
        "read_only_collector_gate_passed": True,
        "read_only_collector_blockers": [],
        "latest_gtrade_backend_manifest_path": "data/registry/gtrade_backend_manifest.json",
        "latest_ostium_constraint_path": "data/registry/ostium_constraints.json",
        "execution_overall_status": "ok",
        "execution_venue_count": 2,
        "execution_comparison_all_registries_present": True,
        "execution_diagnostics_status": "degraded",
        "execution_balance_gap_detected": True,
        "execution_fills_gap_detected": False,
        "execution_gap_history_entry_count": 4,
        "execution_gap_history_latest_status": "ok",
        "execution_gap_history_latest_diagnostics_status": "degraded",
        "execution_state_comparison_entry_count": 4,
        "execution_state_comparison_latest_status_match": False,
        "execution_state_comparison_mismatching_count": 1,
        "execution_snapshot_drift_entry_count": 3,
        "execution_snapshot_drift_latest_status_match": True,
        "execution_snapshot_drift_mismatching_snapshot_count": 1,
        "execution_drift_overview_status": "degraded",
        "execution_drift_overview_diagnostics_alignment_match": False,
        "execution_drift_overview_state_comparison_mismatching_count": 1,
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 1,
        "execution_drift_classification_counts": {
            "P2_BLOCKER": 1,
            "LIVE_READINESS_BLOCKER": 2,
        },
        "timeline_latest_execution_overall_status": "ok",
        "timeline_latest_execution_venue_count": 2,
        "timeline_latest_execution_comparison_all_registries_present": True,
        "quick_navigation": {
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
            "go_no_go_report": "data/research/go_no_go_report.md",
        },
        "related_reports": {
            "phase_gate_review_report": "data/reports/phase_gate_review.md",
            "operations_dashboard_report": "data/reports/operations_dashboard.md",
        },
        "latest_manifest_path": "logs/live_evidence/manifests/live_evidence_1.json",
        "latest_evidence_card_path": "data/evidence/evidence_card_1.json",
        "latest_execution_snapshot_summary_path": "data/ops/execution_snapshot_summary.json",
        "latest_execution_venue_comparison_summary_path": (
            "data/ops/execution_venue_comparison_summary.json"
        ),
        "latest_execution_venue_diagnostics_summary_path": (
            "data/ops/execution_venue_diagnostics_summary.json"
        ),
        "latest_execution_gap_history_summary_path": "data/ops/execution_gap_history_summary.json",
        "latest_execution_state_comparison_history_summary_path": (
            "data/ops/execution_state_comparison_history_summary.json"
        ),
        "latest_execution_snapshot_drift_history_summary_path": (
            "data/ops/execution_snapshot_drift_history_summary.json"
        ),
        "latest_execution_drift_overview_summary_path": (
            "data/ops/execution_drift_overview_summary.json"
        ),
        "required_artifact_paths": {
            "execution_snapshot_summary": "data/ops/execution_snapshot_summary.json",
            "go_no_go_report": "data/research/go_no_go_report.md",
        },
        "missing_required_artifact_paths": ["go_no_go_report"],
        "artifact_recovery_commands": {
            "go_no_go_report": ["uv run sis check-go-no-go"],
        },
        "remediation_order": [
            {
                "priority": 3,
                "reason": "execution_drift_unresolved",
                "commands": ["uv run sis phase-gate-review"],
            }
        ],
        "remediation_success_criteria": {
            "execution_drift_unresolved": ["execution_drift_overview_status == ok"],
        },
        "remediation_preflight_commands": {
            "execution_drift_unresolved": ["uv run sis monitoring-status"],
        },
        "remediation_postcheck_commands": {
            "execution_drift_unresolved": ["uv run sis phase-gate-review"],
        },
        "remediation_preflight_expected_outputs": {
            "execution_drift_unresolved": ["monitoring output shows current mismatch counts"],
        },
        "remediation_execute_expected_outputs": {
            "execution_drift_unresolved": ["execution_drift_overview_status == ok"],
        },
        "remediation_postcheck_pass_signals": {
            "execution_drift_unresolved": ["phase-gate-review prints phase2_entry_allowed"],
        },
        "remediation_signal_snapshots_before": {
            "execution_drift_unresolved": {"execution_drift_overview_status": "degraded"},
        },
        "remediation_signal_snapshots_target": {
            "execution_drift_unresolved": {"execution_drift_overview_status": "ok"},
        },
        "remediation_signal_snapshot_diffs": {
            "execution_drift_unresolved": {
                "execution_drift_overview_status": {
                    "previous": "degraded",
                    "current": "degraded",
                    "target": "ok",
                    "trend": "unchanged",
                    "target_matched": False,
                }
            },
        },
        "remediation_recommendations": {
            "execution_drift_unresolved": {
                "status": "retry",
                "why": "target not met",
                "commands": ["uv run sis phase-gate-review"],
            }
        },
        "diagnostics": [
            {
                "symbol": "SP500",
                "available": True,
                "items": [
                    {
                        "rows": 120,
                        "tradable_rate": 1.0,
                        "stale_rate": 0.0,
                        "l2_only_rate": 0.0,
                        "fee_mode_unknown_rate": 0.0,
                        "missing_mark_price_rate": 0.0,
                        "missing_index_price_rate": 0.0,
                        "spread_p90_bps": 5.0,
                    }
                ],
            }
        ],
        "venue_decisions": [
            {
                "venue": "trade_xyz",
                "decision": "CONDITIONAL_GO_NEEDS_LIVE_WINDOW",
                "main_blocker": "execution_drift_unresolved",
            }
        ],
        "execution_drift_classifications": [
            {
                "signal": "execution_drift_overview_status",
                "observed": "degraded",
                "expected": "ok",
                "classification": "LIVE_READINESS_BLOCKER",
                "reason": "execution drift unresolved",
                "root_source": "execution_drift_overview_summary.json",
                "derived_from": "diagnostics_alignment_match",
                "recommended_next_action": "uv run sis phase-gate-review",
            }
        ],
        "next_actions": ["run_pr12_fresh_read_only_smoke"],
        "recommended_read_order": [
            "data/ops/execution_snapshot_summary.json",
            "data/reports/phase_gate_review.md",
        ],
    }


def test_render_phase_gate_review_markdown_includes_core_sections() -> None:
    text = render_phase_gate_review_markdown(_phase_gate_summary())

    assert "# Phase Gate Review" in text
    assert "## Executive Summary" in text
    assert "decision: CONDITIONAL_GO_NEEDS_LIVE_WINDOW" in text
    assert "execution_drift_live_readiness_blocker_count: 2" in text
    assert "## Quick Navigation" in text
    assert "- phase_gate_review_report: data/reports/phase_gate_review.md" in text
    assert "## Required Artifacts" in text
    assert "- go_no_go_report: data/research/go_no_go_report.md" in text
    assert "- missing_required_artifact_paths:" in text
    assert "  - go_no_go_report" in text
    assert "## Recovery Commands" in text
    assert "  - `uv run sis check-go-no-go`" in text
    assert "## Remediation Command Flow" in text
    assert "## Remediation Signal Diffs" in text
    assert "target_matched=False" in text
    assert "## Diagnostics" in text
    assert "| SP500 | True | 120 | 1.0 | 0.0 |" in text
    assert "## Venue Decisions" in text
    assert "| trade_xyz | CONDITIONAL_GO_NEEDS_LIVE_WINDOW | execution_drift_unresolved |" in text
    assert "## Execution Drift Classification" in text
    assert "LIVE_READINESS_BLOCKER" in text
    assert "## Next Actions" in text
    assert "- run_pr12_fresh_read_only_smoke" in text
    assert "## Stop Conditions" in text
    assert "## Recommended Read Order" in text
