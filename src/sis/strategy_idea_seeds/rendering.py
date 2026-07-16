from __future__ import annotations

from sis.strategy_idea_seeds.common.models import StrategyIdeaSeedSet


def render_seed_set_markdown(seed_set: StrategyIdeaSeedSet) -> str:
    lines = [
        "# Strategy Idea Seed Set",
        "",
        "- status: `UNVERIFIED_SEED`",
        f"- seed_count: `{seed_set.seed_count}`",
        f"- data_required_count: `{seed_set.data_required_count}`",
        f"- semantic_hash: `{seed_set.semantic_hash}`",
        "- backtest/profit/paper/live permissions: `false`",
        "",
    ]
    if not seed_set.seeds:
        lines.extend(
            [
                "## Result",
                "",
                "Materialized Seedは0件です。全Generation AttemptとReasonはLedgerを確認してください。",
                "",
            ]
        )
        return "\n".join(lines)
    for seed in seed_set.seeds:
        intent = seed.profit_intent
        lines.extend(
            [
                f"## {seed.title}",
                "",
                f"- seed_record_id: `{seed.seed_record_id}`",
                f"- data_readiness: `{seed.data_readiness}`",
                f"- mechanism: `{intent.mechanism_class}`",
                f"- direction: `{intent.direction_hint}`",
                f"- capture: `{intent.capture_archetype}`",
                f"- horizon: `{intent.horizon_hint}`",
                f"- required_sources: `{', '.join(item.source_key for item in seed.required_sources)}`",
                f"- known_gaps: `{', '.join(seed.known_gaps) or 'none'}`",
                "",
                seed.hypothesis,
                "",
                f"Falsification: {seed.falsification_question}",
                "",
            ]
        )
    return "\n".join(lines)
