from __future__ import annotations

from sis.strategy_live_observation.models import StrategyLiveObservationManifest


def render_live_observation_markdown(manifest: StrategyLiveObservationManifest) -> str:
    summary = manifest.summary
    lines = [
        f"# Strategy Live Observation: {manifest.strategy_id}",
        "",
        "## Summary",
        "",
        f"- observation_id: `{manifest.observation_id}`",
        f"- ingest_status: `{manifest.ingest_status.value}`",
        f"- canary_status: `{summary.canary_status}`",
        f"- blocked_reasons: `{', '.join(summary.blocked_reasons) or 'none'}`",
        f"- canonical_symbol: `{summary.canonical_symbol or 'none'}`",
        f"- notional_usd: `{_optional_number(summary.notional_usd)}`",
        f"- leverage: `{_optional_number(summary.leverage)}`",
        f"- actual_fill_observed: `{str(summary.actual_fill_observed).lower()}`",
        f"- rejection_observed: `{str(summary.rejection_observed).lower()}`",
        f"- cancel_observed: `{str(summary.cancel_observed).lower()}`",
        f"- close_submitted: `{str(summary.close_submitted).lower()}`",
        f"- position_reconciliation_status: `{summary.position_reconciliation_status}`",
        f"- max_loss_breach_observed: `{str(summary.max_loss_breach_observed).lower()}`",
        "",
        "## Actions",
        "",
        f"- schedule_cancel_status: `{summary.schedule_cancel_status or 'none'}`",
        f"- order_submit_status: `{summary.order_submit_status or 'none'}`",
        f"- order_status: `{summary.order_status or 'none'}`",
        f"- cancel_status: `{summary.cancel_status or 'none'}`",
        f"- close_status: `{summary.close_status or 'none'}`",
        "",
        "## Account Snapshot",
        "",
        f"- account_snapshot_present: `{str(summary.account_snapshot_present).lower()}`",
        f"- account_equity: `{_optional_number(summary.account_equity)}`",
        f"- account_available_cash: `{_optional_number(summary.account_available_cash)}`",
        "",
        "## Source Artifacts",
        "",
        "| artifact | path | sha256 | schema_version |",
        "|---|---|---|---|",
    ]
    for artifact in manifest.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This command reads existing micro live canary evidence only.",
            "- It does not submit live orders, permit scale-up, use wallet, signing, or exchange write.",
            "- This is separate from paper runtime observation.",
            "",
        ]
    )
    return "\n".join(lines)


def _optional_number(value: float | int | None) -> str:
    return "none" if value is None else str(value)
