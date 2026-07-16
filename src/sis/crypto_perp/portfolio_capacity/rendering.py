from __future__ import annotations

from sis.crypto_perp.portfolio_capacity.models import (
    PortfolioCapacityCase,
    PortfolioCapacityResult,
    VectorbtDifferentialResult,
)


def render_portfolio_capacity_report(
    case: PortfolioCapacityCase,
    result: PortfolioCapacityResult,
    vectorbt: VectorbtDifferentialResult | None = None,
) -> str:
    lines = [
        "# Crypto Perp Portfolio Capacity",
        "",
        f"- case_id: `{case.case_id}`",
        f"- result_id: `{result.result_id}`",
        f"- pack_id: `{case.pack_id}`",
        f"- row_set_id: `{case.row_set_id}`",
        f"- evidence_basis: `{case.evidence_basis}`",
        f"- action_policy: `{case.policy.action_policy}`",
        f"- metric_scenario: `{case.policy.metric_scenario}`",
        f"- same_timestamp_cash_policy: `{case.policy.same_timestamp_cash_policy}`",
        f"- max_open_positions: `{case.policy.max_open_positions}`",
        f"- run_status: `{result.run_status}`",
        "- actual_cash_used: `false`",
        "- profit_proven: `false`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Account path estimate",
        "",
        f"- initial_cash_usd: `{result.initial_cash_usd}`",
        f"- final_available_cash_usd: `{result.final_available_cash_usd}`",
        f"- final_reserved_cash_usd: `{result.final_reserved_cash_usd}`",
        f"- simulated_account_pnl_estimate_usd: `{result.simulated_account_pnl_estimate_usd}`",
        f"- economic_result_estimate_usd: `{result.economic_result_estimate_usd}`",
        f"- settled_cash_drawdown_estimate_usd: `{result.settled_cash_drawdown_estimate_usd}`",
        "",
        "## Capacity",
        "",
        f"- accepted_trade_count: `{result.accepted_trade_count}`",
        f"- rejected_trade_count: `{result.rejected_trade_count}`",
        f"- skipped_trade_count: `{result.skipped_trade_count}`",
        f"- peak_open_positions: `{result.peak_open_positions}`",
        f"- peak_reserved_cash_usd: `{result.peak_reserved_cash_usd}`",
        f"- peak_capital_utilization: `{result.peak_capital_utilization}`",
        f"- rejected_counterfactual_estimate_usd: `{result.rejected_counterfactual_estimate_usd}`",
        "",
        "## Accepted actions",
        "",
    ]
    if result.accepted_action_counts:
        lines.extend(
            f"- {action}: `{count}`"
            for action, count in sorted(result.accepted_action_counts.items())
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Rejections", ""])
    if result.rejected_reason_counts:
        lines.extend(
            f"- {reason}: `{count}`"
            for reason, count in sorted(result.rejected_reason_counts.items())
        )
    else:
        lines.append("- none")
    if vectorbt is not None:
        lines.extend(
            [
                "",
                "## VectorBT differential",
                "",
                f"- run_status: `{vectorbt.run_status}`",
                f"- decision: `{vectorbt.decision}`",
                f"- vectorbt_version: `{vectorbt.vectorbt_version}`",
                f"- reference_gross_and_fixed_cost_usd: `{vectorbt.reference_gross_and_fixed_cost_usd}`",
                f"- vectorbt_total_profit_usd: `{vectorbt.vectorbt_total_profit_usd}`",
                f"- absolute_difference_usd: `{vectorbt.absolute_difference_usd}`",
            ]
        )
    lines.extend(["", "## Known limits", ""])
    lines.extend(f"- `{limit}`" for limit in result.known_limits)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This result is a BAR_PROXY portfolio-capacity estimate. It does not model mark-to-market, liquidation, partial fills, actual exchange cash, or live execution.",
        ]
    )
    return "\n".join(lines)
