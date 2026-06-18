from __future__ import annotations

from sis.strategy_inputs.models import StrategyInputContractValidation, StrategyIntakeDecision


def render_input_contract_validation_markdown(
    validation: StrategyInputContractValidation,
) -> str:
    lines = [
        f"# Strategy Input Contract Validation: {validation.contract_id}",
        "",
        "## Summary",
        "",
        f"- validation_status: `{validation.validation_status.value}`",
        f"- strict: `{str(validation.strict).lower()}`",
        f"- missing_required_count: `{validation.summary.missing_required_count}`",
        f"- invalid_required_count: `{validation.summary.invalid_required_count}`",
        f"- boundary_violation_count: `{validation.summary.boundary_violation_count}`",
        f"- warning_count: `{validation.summary.warning_count}`",
        f"- column_check_failure_count: `{validation.summary.column_check_failure_count}`",
        f"- timestamp_violation_count: `{validation.summary.timestamp_violation_count}`",
        "",
        "## Boundary",
        "",
        "- permits_live_order: `false`",
        "- live_conversion_allowed: `false`",
        "- wallet_used: `false`",
        "- signing_used: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Source Results",
        "",
        "| source_id | status | path | hash_matches | missing_columns | timestamp_check | error |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in validation.source_results:
        lines.append(
            "| "
            f"`{result.source_id}` | "
            f"`{result.status.value}` | "
            f"`{result.path}` | "
            f"`{result.hash_matches}` | "
            f"`{', '.join(result.missing_columns)}` | "
            f"`{result.timestamp_check_passed}` | "
            f"`{result.error or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Readiness Notice",
            "",
            "この artifact は入力データ契約の検証結果です。paper / live 実行許可ではありません。",
            "",
        ]
    )
    return "\n".join(lines)


def render_strategy_intake_decision_markdown(decision: StrategyIntakeDecision) -> str:
    lines = [
        f"# Strategy Intake Decision: {decision.idea_id}",
        "",
        "## Summary",
        "",
        f"- decision: `{decision.decision.value}`",
        f"- required_action_count: `{len(decision.required_actions)}`",
        f"- boundary_violation_count: `{decision.summary.boundary_violation_count}`",
        "",
        "## Required Actions",
        "",
    ]
    if decision.required_actions:
        lines.extend(f"- {action}" for action in decision.required_actions)
    else:
        lines.append("- なし。")
    lines.extend(
        [
            "",
            "## Input Contracts",
            "",
            "| contract_id | validation_status |",
            "|---|---|",
        ]
    )
    for ref in decision.input_contract_refs:
        lines.append(f"| `{ref.contract_id}` | `{ref.validation_status.value}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- permits_live_order: `false`",
            "- live_conversion_allowed: `false`",
            "- wallet_used: `false`",
            "- signing_used: `false`",
            "- exchange_write_used: `false`",
            "",
            "## Readiness Notice",
            "",
            "`READY_FOR_AUTHORING_DRAFT` は authoring draft 候補であり、paper / live 実行許可ではありません。",
            "",
        ]
    )
    return "\n".join(lines)
