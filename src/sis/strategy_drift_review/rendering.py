from __future__ import annotations

from sis.strategy_drift_review.models import PaperVsBacktestDriftReview


def _optional(value: object) -> str:
    return "not_available" if value is None else str(value)


def render_drift_review_markdown(review: PaperVsBacktestDriftReview) -> str:
    lines = [
        f"# Paper vs Backtest Drift Review: {review.strategy_id}",
        "",
        f"- review_status: `{review.review_status.value}`",
        f"- recommended_action: `{review.recommended_action.value}`",
        f"- paper_execution_allowed: `{str(review.paper_execution_allowed).lower()}`",
        f"- live_allowed: `{str(review.live_allowed).lower()}`",
        "",
        "## Backtest Summary",
        "",
    ]
    if review.backtest_summary is None:
        lines.append("- status: `missing`")
    else:
        backtest = review.backtest_summary
        lines.extend(
            [
                f"- backtest_passed: `{str(backtest.backtest_passed).lower()}`",
                f"- signals_considered: `{backtest.signals_considered}`",
                f"- executed_count: `{backtest.executed_count}`",
                f"- blocked_count: `{backtest.blocked_count}`",
                f"- trade_count: `{backtest.trade_count}`",
                f"- total_return: `{backtest.total_return}`",
                f"- max_drawdown: `{_optional(backtest.max_drawdown)}`",
                f"- win_rate: `{_optional(backtest.win_rate)}`",
            ]
        )

    lines.extend(["", "## Runtime Summary", ""])
    if review.runtime_summary is None:
        lines.append("- status: `missing`")
    else:
        runtime = review.runtime_summary
        lines.extend(
            [
                f"- ingest_status: `{runtime.ingest_status}`",
                f"- session_id: `{runtime.session_id}`",
                f"- source_stage: `{runtime.source_stage}`",
                f"- ledger_entry_count: `{runtime.ledger_entry_count}`",
                f"- paper_fill_count: `{runtime.paper_fill_count}`",
                f"- blocked_count: `{runtime.blocked_count}`",
                f"- no_fill_count: `{runtime.no_fill_count}`",
                f"- max_observed_spread_bps: `{_optional(runtime.max_observed_spread_bps)}`",
                f"- max_observed_quote_age_ms: `{_optional(runtime.max_observed_quote_age_ms)}`",
                f"- pnl_available: `{str(runtime.pnl_available).lower()}`",
                f"- pnl_unavailable_reason: `{runtime.pnl_unavailable_reason or 'none'}`",
                f"- realized_pnl_usd_total: `{_optional(runtime.realized_pnl_usd_total)}`",
                f"- gross_pnl_usd_total: `{_optional(runtime.gross_pnl_usd_total)}`",
                f"- fee_usd_total: `{_optional(runtime.fee_usd_total)}`",
                f"- slippage_usd_total: `{_optional(runtime.slippage_usd_total)}`",
                f"- avg_slippage_bps: `{_optional(runtime.avg_slippage_bps)}`",
                f"- max_abs_slippage_bps: `{_optional(runtime.max_abs_slippage_bps)}`",
                f"- avg_fill_price_drift_bps: `{_optional(runtime.avg_fill_price_drift_bps)}`",
                f"- max_abs_fill_price_drift_bps: `{_optional(runtime.max_abs_fill_price_drift_bps)}`",
                f"- filled_notional_usd_total: `{_optional(runtime.filled_notional_usd_total)}`",
            ]
        )

    metrics = review.drift_metrics
    lines.extend(
        [
            "",
            "## Drift Metrics",
            "",
            f"- runtime_to_backtest_trade_count_ratio: `{_optional(metrics.runtime_to_backtest_trade_count_ratio)}`",
            f"- runtime_blocked_rate: `{_optional(metrics.runtime_blocked_rate)}`",
            f"- runtime_no_fill_rate: `{_optional(metrics.runtime_no_fill_rate)}`",
            f"- max_observed_spread_bps: `{_optional(metrics.max_observed_spread_bps)}`",
            f"- max_observed_quote_age_ms: `{_optional(metrics.max_observed_quote_age_ms)}`",
            f"- pnl_drift_available: `{str(metrics.pnl_drift_available).lower()}`",
            f"- backtest_total_return: `{_optional(metrics.backtest_total_return)}`",
            f"- runtime_return_on_filled_notional: `{_optional(metrics.runtime_return_on_filled_notional)}`",
            f"- runtime_vs_backtest_return_drift: `{_optional(metrics.runtime_vs_backtest_return_drift)}`",
            f"- runtime_realized_pnl_usd_total: `{_optional(metrics.runtime_realized_pnl_usd_total)}`",
            f"- runtime_fee_usd_total: `{_optional(metrics.runtime_fee_usd_total)}`",
            f"- runtime_slippage_usd_total: `{_optional(metrics.runtime_slippage_usd_total)}`",
            f"- runtime_avg_slippage_bps: `{_optional(metrics.runtime_avg_slippage_bps)}`",
            f"- runtime_max_abs_slippage_bps: `{_optional(metrics.runtime_max_abs_slippage_bps)}`",
            f"- runtime_avg_fill_price_drift_bps: `{_optional(metrics.runtime_avg_fill_price_drift_bps)}`",
            f"- runtime_max_abs_fill_price_drift_bps: `{_optional(metrics.runtime_max_abs_fill_price_drift_bps)}`",
            "",
            "## Source Artifacts",
            "",
            "| artifact | path | sha256 | schema_version |",
            "|---|---|---|---|",
        ]
    )
    for artifact in review.source_artifacts:
        lines.append(
            f"| `{artifact.artifact_key}` | `{artifact.path}` | `{artifact.sha256}` | `{artifact.schema_version or ''}` |"
        )

    lines.extend(["", "## Order Lifecycle", "", "| lifecycle | count |", "|---|---:|"])
    if review.runtime_summary is not None and review.runtime_summary.order_lifecycle_counts:
        for lifecycle, count in sorted(review.runtime_summary.order_lifecycle_counts.items()):
            lines.append(f"| `{lifecycle}` | `{count}` |")
    else:
        lines.append("| none | 0 |")

    lines.extend(
        [
            "",
            "## Conditions",
            "",
            "| condition | passed | observed | required | severity |",
            "|---|---:|---|---|---|",
        ]
    )
    for condition in [
        *review.passed_conditions,
        *review.failed_conditions,
        *review.warning_conditions,
    ]:
        lines.append(
            f"| `{condition.condition_id}` | `{str(condition.passed).lower()}` | `{condition.observed}` | `{condition.required}` | `{condition.severity}` |"
        )

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact compares paper runtime observation with a backtest result for human review.",
            "- It does not run paper orders.",
            "- It does not permit live execution, wallet use, signing, or exchange write.",
            "- If pnl_drift_available is false, this is a limited fill/block/spread review.",
            "",
        ]
    )
    return "\n".join(lines)
