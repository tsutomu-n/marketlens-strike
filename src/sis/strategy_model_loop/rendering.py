from __future__ import annotations

from sis.strategy_model_loop.models import StrategyModelRun, StrategyOptimizerTrialLedger


def render_optimizer_trial_ledger_markdown(ledger: StrategyOptimizerTrialLedger) -> str:
    summary = ledger.summary
    lines = [
        f"# Strategy Optimizer Trial Ledger: {ledger.strategy_id}",
        "",
        f"- ledger_id: `{ledger.ledger_id}`",
        f"- trial_count: `{summary.trial_count}`",
        f"- complete_count: `{summary.complete_count}`",
        f"- failed_count: `{summary.failed_count}`",
        f"- pruned_count: `{summary.pruned_count}`",
        f"- running_count: `{summary.running_count}`",
        f"- success_only_reporting: `{str(summary.success_only_reporting).lower()}`",
        f"- best_trial_id: `{ledger.best_trial_id or 'none'}`",
        f"- auto_applied: `{str(ledger.auto_applied).lower()}`",
        f"- direct_spec_edit_allowed: `{str(ledger.direct_spec_edit_allowed).lower()}`",
        "",
        "## Trials",
        "",
        "| trial_id | status | objective_value | failure_reason |",
        "|---|---|---:|---|",
    ]
    for trial in ledger.trials:
        objective = "" if trial.objective_value is None else str(trial.objective_value)
        lines.append(
            f"| `{trial.trial_id}` | `{trial.status.value}` | {objective} | `{trial.failure_reason or ''}` |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This artifact records model / optimizer trials only.",
            "- It does not edit Strategy Authoring YAML, run paper orders, permit live execution, use wallet, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)


def render_strategy_model_run_markdown(model_run: StrategyModelRun) -> str:
    lines = [
        f"# Strategy Model Run: {model_run.strategy_id}",
        "",
        f"- model_run_id: `{model_run.model_run_id}`",
        f"- training_data_path: `{model_run.training_data.path}`",
        f"- training_data_sha256: `{model_run.training_data.sha256}`",
        f"- label_definition: `{model_run.label_definition}`",
        f"- split: `{model_run.split}`",
        f"- seed: `{model_run.seed if model_run.seed is not None else 'none'}`",
        f"- search_space_hash: `{model_run.search_space_hash}`",
        f"- optimizer_trial_ledger_path: `{model_run.optimizer_trial_ledger_path}`",
        f"- best_trial_id: `{model_run.best_trial_id or 'none'}`",
        f"- output_route: `{model_run.output_route.value}`",
        f"- auto_applied: `{str(model_run.auto_applied).lower()}`",
        f"- direct_spec_edit_allowed: `{str(model_run.direct_spec_edit_allowed).lower()}`",
        "",
        "## Limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in model_run.limitations)
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Model / optimizer output is routed only to Idea Intake or Revision Request.",
            "- This artifact does not edit Strategy Authoring YAML, run paper orders, permit live execution, use wallet, signing, or exchange write.",
            "",
        ]
    )
    return "\n".join(lines)
