from __future__ import annotations

from collections.abc import Mapping

import typer


def healthcheck_base_status_lines(payload: Mapping[str, object]) -> list[str]:
    return [
        f"status={payload.get('status')}",
        f"kill_switch_enabled={payload.get('kill_switch_enabled')}",
        f"decision_summary_exists={payload.get('decision_summary_exists')}",
    ]


def healthcheck_risk_limit_lines(
    *,
    daily_loss_allowed: object,
    daily_loss_reason: object,
    exposure_allowed: object,
    exposure_reason: object,
) -> list[str]:
    return [
        f"daily_loss_allowed={daily_loss_allowed}",
        f"daily_loss_reason={daily_loss_reason}",
        f"exposure_allowed={exposure_allowed}",
        f"exposure_reason={exposure_reason}",
    ]


def healthcheck_artifact_status_lines(*, reconciliation_store_present: object) -> list[str]:
    return [
        f"reconciliation_store_present={reconciliation_store_present}",
    ]


def monitoring_base_status_lines(payload: Mapping[str, object]) -> list[str]:
    return [
        f"status={payload.get('status')}",
        f"decision_summary_exists={payload.get('decision_summary_exists')}",
        f"weekly_review_exists={payload.get('weekly_review_exists')}",
        f"daily_pnl_exists={payload.get('daily_pnl_exists')}",
        f"operation_chain_exists={payload.get('operation_chain_exists')}",
    ]


def execution_drift_status_lines(payload: Mapping[str, object]) -> list[str]:
    return [
        f"execution_drift_overview_status={payload.get('execution_drift_overview_status')}",
        (
            "execution_drift_overview_diagnostics_alignment_match="
            f"{payload.get('execution_drift_overview_diagnostics_alignment_match')}"
        ),
        (
            "execution_drift_overview_state_comparison_mismatching_count="
            f"{payload.get('execution_drift_overview_state_comparison_mismatching_count')}"
        ),
        (
            "execution_drift_overview_snapshot_drift_mismatching_snapshot_count="
            f"{payload.get('execution_drift_overview_snapshot_drift_mismatching_snapshot_count')}"
        ),
    ]


def readiness_status_lines(payload: Mapping[str, object]) -> list[str]:
    return [
        f"readiness_next_phase_candidate={payload.get('readiness_next_phase_candidate')}",
        f"readiness_execution_ready={payload.get('readiness_execution_ready')}",
    ]


def echo_healthcheck_base_status(payload: Mapping[str, object]) -> None:
    for line in healthcheck_base_status_lines(payload):
        typer.echo(line)


def echo_healthcheck_risk_limits(
    *,
    daily_loss_allowed: object,
    daily_loss_reason: object,
    exposure_allowed: object,
    exposure_reason: object,
) -> None:
    for line in healthcheck_risk_limit_lines(
        daily_loss_allowed=daily_loss_allowed,
        daily_loss_reason=daily_loss_reason,
        exposure_allowed=exposure_allowed,
        exposure_reason=exposure_reason,
    ):
        typer.echo(line)


def echo_healthcheck_artifact_status(*, reconciliation_store_present: object) -> None:
    for line in healthcheck_artifact_status_lines(
        reconciliation_store_present=reconciliation_store_present
    ):
        typer.echo(line)


def echo_monitoring_base_status(payload: Mapping[str, object]) -> None:
    for line in monitoring_base_status_lines(payload):
        typer.echo(line)


def echo_execution_drift_status(payload: Mapping[str, object]) -> None:
    for line in execution_drift_status_lines(payload):
        typer.echo(line)


def echo_readiness_status(payload: Mapping[str, object]) -> None:
    for line in readiness_status_lines(payload):
        typer.echo(line)
