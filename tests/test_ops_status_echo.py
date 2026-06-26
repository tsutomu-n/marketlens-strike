from sis.commands.ops_status_echo import (
    execution_drift_status_lines,
    healthcheck_artifact_status_lines,
    healthcheck_base_status_lines,
    healthcheck_risk_limit_lines,
    monitoring_base_status_lines,
    readiness_status_lines,
)


def test_healthcheck_base_status_lines_preserve_cli_order() -> None:
    assert healthcheck_base_status_lines(
        {
            "status": "degraded",
            "kill_switch_enabled": True,
            "decision_summary_exists": False,
        }
    ) == [
        "status=degraded",
        "kill_switch_enabled=True",
        "decision_summary_exists=False",
    ]


def test_healthcheck_base_status_lines_match_missing_value_echo_behavior() -> None:
    assert healthcheck_base_status_lines({}) == [
        "status=None",
        "kill_switch_enabled=None",
        "decision_summary_exists=None",
    ]


def test_healthcheck_risk_limit_lines_preserve_cli_order() -> None:
    assert healthcheck_risk_limit_lines(
        daily_loss_allowed=False,
        daily_loss_reason="BLOCK_DAILY_LOSS_LIMIT",
        exposure_allowed=True,
        exposure_reason=None,
    ) == [
        "daily_loss_allowed=False",
        "daily_loss_reason=BLOCK_DAILY_LOSS_LIMIT",
        "exposure_allowed=True",
        "exposure_reason=None",
    ]


def test_healthcheck_artifact_status_lines_preserve_cli_label() -> None:
    assert healthcheck_artifact_status_lines(reconciliation_store_present=True) == [
        "reconciliation_store_present=True",
    ]


def test_healthcheck_artifact_status_lines_match_none_echo_behavior() -> None:
    assert healthcheck_artifact_status_lines(reconciliation_store_present=None) == [
        "reconciliation_store_present=None",
    ]


def test_monitoring_base_status_lines_preserve_cli_order() -> None:
    assert monitoring_base_status_lines(
        {
            "status": "ok",
            "decision_summary_exists": True,
            "weekly_review_exists": False,
            "daily_pnl_exists": True,
            "operation_chain_exists": False,
        }
    ) == [
        "status=ok",
        "decision_summary_exists=True",
        "weekly_review_exists=False",
        "daily_pnl_exists=True",
        "operation_chain_exists=False",
    ]


def test_monitoring_base_status_lines_match_missing_value_echo_behavior() -> None:
    assert monitoring_base_status_lines({}) == [
        "status=None",
        "decision_summary_exists=None",
        "weekly_review_exists=None",
        "daily_pnl_exists=None",
        "operation_chain_exists=None",
    ]


def test_execution_drift_status_lines_preserve_cli_order() -> None:
    assert execution_drift_status_lines(
        {
            "execution_drift_overview_status": "degraded",
            "execution_drift_overview_diagnostics_alignment_match": False,
            "execution_drift_overview_state_comparison_mismatching_count": 1,
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count": 2,
        }
    ) == [
        "execution_drift_overview_status=degraded",
        "execution_drift_overview_diagnostics_alignment_match=False",
        "execution_drift_overview_state_comparison_mismatching_count=1",
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=2",
    ]


def test_execution_drift_status_lines_match_missing_value_echo_behavior() -> None:
    assert execution_drift_status_lines({}) == [
        "execution_drift_overview_status=None",
        "execution_drift_overview_diagnostics_alignment_match=None",
        "execution_drift_overview_state_comparison_mismatching_count=None",
        "execution_drift_overview_snapshot_drift_mismatching_snapshot_count=None",
    ]


def test_readiness_status_lines_preserve_cli_order() -> None:
    assert readiness_status_lines(
        {
            "readiness_next_phase_candidate": "Stay Phase 1",
            "readiness_execution_ready": False,
        }
    ) == [
        "readiness_next_phase_candidate=Stay Phase 1",
        "readiness_execution_ready=False",
    ]
