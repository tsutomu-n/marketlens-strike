from __future__ import annotations

from sis.strategy_runtime_observation.models import StrategyRuntimeObservationManifest


def render_runtime_observation_markdown(manifest: StrategyRuntimeObservationManifest) -> str:
    summary = manifest.summary
    lines = [
        f"# Strategy Runtime Observation: {manifest.strategy_id}",
        "",
        f"- ingest_status: `{manifest.ingest_status.value}`",
        f"- session_id: `{manifest.session_id}`",
        f"- source_stage: `{manifest.source_stage.value}`",
        f"- runtime_observation_ledger_path: `{manifest.runtime_observation_ledger_path}`",
        f"- runtime_observation_ledger_sha256: `{manifest.runtime_observation_ledger_sha256}`",
        f"- includes_live_order: `{str(manifest.includes_live_order).lower()}`",
        f"- includes_wallet: `{str(manifest.includes_wallet).lower()}`",
        f"- includes_signing: `{str(manifest.includes_signing).lower()}`",
        f"- includes_exchange_write: `{str(manifest.includes_exchange_write).lower()}`",
        "",
        "## Summary",
        "",
        f"- ledger_entry_count: `{summary.ledger_entry_count}`",
        f"- paper_order_count: `{summary.paper_order_count}`",
        f"- paper_fill_count: `{summary.paper_fill_count}`",
        f"- blocked_count: `{summary.blocked_count}`",
        f"- no_fill_count: `{summary.no_fill_count}`",
        f"- unique_intent_count: `{summary.unique_intent_count}`",
        f"- unique_symbol_count: `{summary.unique_symbol_count}`",
        f"- first_observed_at: `{summary.first_observed_at or 'none'}`",
        f"- last_observed_at: `{summary.last_observed_at or 'none'}`",
        f"- max_observed_spread_bps: `{summary.max_observed_spread_bps if summary.max_observed_spread_bps is not None else 'none'}`",
        f"- max_observed_quote_age_ms: `{summary.max_observed_quote_age_ms if summary.max_observed_quote_age_ms is not None else 'none'}`",
        f"- pnl_available: `{str(summary.pnl_available).lower()}`",
        f"- pnl_unavailable_reason: `{summary.pnl_unavailable_reason or 'none'}`",
        f"- realized_pnl_usd_total: `{_optional_number(summary.realized_pnl_usd_total)}`",
        f"- gross_pnl_usd_total: `{_optional_number(summary.gross_pnl_usd_total)}`",
        f"- fee_usd_total: `{_optional_number(summary.fee_usd_total)}`",
        f"- slippage_usd_total: `{_optional_number(summary.slippage_usd_total)}`",
        f"- avg_slippage_bps: `{_optional_number(summary.avg_slippage_bps)}`",
        f"- max_abs_slippage_bps: `{_optional_number(summary.max_abs_slippage_bps)}`",
        f"- avg_fill_price_drift_bps: `{_optional_number(summary.avg_fill_price_drift_bps)}`",
        f"- max_abs_fill_price_drift_bps: `{_optional_number(summary.max_abs_fill_price_drift_bps)}`",
        f"- filled_notional_usd_total: `{_optional_number(summary.filled_notional_usd_total)}`",
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
            "## Block Reasons",
            "",
            "| reason | count |",
            "|---|---:|",
        ]
    )
    for reason, count in sorted(summary.block_reasons.items()):
        lines.append(f"| `{reason}` | `{count}` |")
    if not summary.block_reasons:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Order Lifecycle",
            "",
            "| lifecycle | count |",
            "|---|---:|",
        ]
    )
    for lifecycle, count in sorted(summary.order_lifecycle_counts.items()):
        lines.append(f"| `{lifecycle}` | `{count}` |")
    if not summary.order_lifecycle_counts:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact ingests paper runtime observations only.",
            "- It does not submit orders, permit live execution, use wallet, signing, or exchange write.",
            "- It is input for Drift Review and future Strategy Input Contract updates.",
            "",
        ]
    )
    return "\n".join(lines)


def _optional_number(value: float | None) -> str:
    return "none" if value is None else str(value)
