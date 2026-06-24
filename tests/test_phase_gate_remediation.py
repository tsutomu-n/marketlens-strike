from __future__ import annotations

from sis.reports.phase_gate_remediation import (
    artifact_recovery_commands,
    execution_drift_classifications,
    remediation_execute_expected_outputs,
    remediation_order,
    remediation_postcheck_commands,
    remediation_postcheck_pass_signals,
    remediation_preflight_commands,
    remediation_preflight_expected_outputs,
    remediation_signal_snapshot_before,
    remediation_signal_snapshot_target,
    remediation_success_criteria,
)


def test_execution_drift_classifications_include_lineage_for_empty_snapshot() -> None:
    classifications = execution_drift_classifications(
        {
            "execution_snapshot_reason": "trade_xyz_live_execution_snapshot_not_connected",
            "execution_snapshot_root_source": "execution_snapshot_summary.venues=[]",
            "execution_comparison_reason": "source_execution_snapshot_empty",
            "execution_comparison_root_source": "execution_snapshot_summary.venues=[]",
            "execution_diagnostics_reason": "source_execution_snapshot_empty",
            "execution_diagnostics_root_source": "execution_snapshot_summary.venues=[]",
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_reason_codes": [
                "trade_xyz_live_execution_snapshot_not_connected"
            ],
            "execution_balance_gap_detected": True,
            "execution_fills_gap_detected": True,
            "execution_comparison_all_registries_present": False,
        }
    )

    by_signal = {item["signal"]: item for item in classifications}
    assert by_signal["execution_drift_overview_status"]["classification"] == (
        "LIVE_READINESS_BLOCKER"
    )
    assert by_signal["execution_drift_overview_status"]["root_source"] == (
        "execution_snapshot_summary.venues=[]"
    )
    assert by_signal["execution_drift_overview_status"]["derived_from"] == (
        "trade_xyz_live_execution_snapshot_not_connected"
    )
    assert by_signal["execution_comparison_all_registries_present"]["derived_from"] == (
        "source_execution_snapshot_empty"
    )
    assert by_signal["execution_balance_gap_detected"]["recommended_next_action"] == (
        "decide_read_only_execution_state_collector_scope"
    )


def test_artifact_recovery_commands_map_known_and_unknown_artifacts() -> None:
    commands = artifact_recovery_commands(
        [
            "latest_trade_xyz_quote_path",
            "latest_evidence_card_path",
            "unexpected_artifact",
        ]
    )

    assert commands["latest_trade_xyz_quote_path"] == [
        "uv run sis collect-trade-xyz-quotes --no-normalize"
    ]
    assert commands["latest_evidence_card_path"] == [
        "uv run sis check-go-no-go",
        "uv run sis build-evidence-card",
    ]
    assert commands["unexpected_artifact"] == ["uv run sis refresh-operations-artifacts"]


def test_remediation_order_and_metadata_for_phase_gate_blockers() -> None:
    summary = {
        "strict_validation_issue_count": "2",
        "diagnostics_all_available": False,
        "execution_drift_overview_status": "degraded",
        "execution_drift_classification_counts": {"P2_BLOCKER": 1},
        "phase2_entry_allowed": False,
        "phase_gate_strict_validation_issue_count": 2,
        "diagnostics_symbols": ["SP500"],
    }
    recovery_commands = artifact_recovery_commands(["latest_trade_xyz_summary_path"])

    order = remediation_order(summary, ["latest_trade_xyz_summary_path"], recovery_commands)

    assert [item["reason"] for item in order] == [
        "missing_required_artifacts",
        "strict_validation_failed",
        "diagnostics_unavailable",
        "execution_drift_unresolved",
        "phase_gate_not_cleared",
    ]
    assert order[0]["commands"] == [
        "uv run sis collect-trade-xyz-quotes --write-summary --write-report"
    ]
    assert remediation_success_criteria("strict_validation_failed") == [
        "strict_validation_issue_count == 0",
        "phase_gate_strict_validation_issue_count == 0",
    ]
    assert remediation_preflight_commands("phase_gate_not_cleared") == ["uv run sis check-go-no-go"]
    assert remediation_postcheck_commands("phase_gate_not_cleared") == [
        "uv run sis build-evidence-card",
        "uv run sis phase-gate-review",
    ]
    assert "phase gate summary lists blockers" in remediation_preflight_expected_outputs(
        "phase_gate_not_cleared"
    )
    assert "evidence card is regenerated" in remediation_execute_expected_outputs(
        "phase_gate_not_cleared"
    )
    assert "phase2_entry_allowed == True" in remediation_postcheck_pass_signals(
        "phase_gate_not_cleared"
    )
    assert remediation_signal_snapshot_before("strict_validation_failed", summary) == {
        "strict_validation_issue_count": "2",
        "phase_gate_strict_validation_issue_count": 2,
    }
    assert remediation_signal_snapshot_target("strict_validation_failed") == {
        "strict_validation_issue_count": 0,
        "phase_gate_strict_validation_issue_count": 0,
    }


def test_remediation_order_skips_live_readiness_only_execution_drift() -> None:
    summary = {
        "strict_validation_issue_count": 0,
        "diagnostics_all_available": True,
        "execution_drift_overview_status": "degraded",
        "execution_drift_classification_counts": {
            "P2_BLOCKER": 0,
            "LIVE_READINESS_BLOCKER": 3,
        },
        "phase2_entry_allowed": True,
    }

    order = remediation_order(summary, [], {})

    assert [item["reason"] for item in order] == []
