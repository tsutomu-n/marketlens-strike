from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.research.strategy_lab.authoring.io import load_authoring_spec
from sis.strategy_review.manifest import SourceArtifact
from sis.strategy_review.provenance import repo_relative_path
from sis.strategy_review.sections import ReviewSection
from sis.strategy_review.source_artifacts import (
    invalid_optional_artifact,
    present_optional_artifact,
)


def _condition_count(value: Any) -> int:
    total = 0
    for field_name in ("all", "any", "none"):
        items = getattr(value, field_name, None)
        if isinstance(items, list):
            total += len(items)
    return total


def _configured_field_names(model: Any) -> list[str]:
    if not hasattr(model, "model_dump"):
        return []
    values = model.model_dump(exclude_none=True, exclude_defaults=True)
    return sorted(str(key) for key, value in values.items() if value not in (False, [], {}, None))


def strategy_definition_summary(path: Path) -> tuple[SourceArtifact, ReviewSection]:
    try:
        spec = load_authoring_spec(path)
    except Exception as exc:
        return (
            invalid_optional_artifact("authoring_spec", path, exc),
            ReviewSection(
                section_id="strategy_definition",
                title="Strategy Definition",
                status="invalid",
                markdown=f"- status: `invalid`\n- path: `{repo_relative_path(path)}`\n- error: `{exc}`",
                source_artifact_keys=("authoring_spec",),
            ),
        )

    first_binding = spec.experiment.symbol_bindings[0]
    exit_fields = _configured_field_names(spec.rules.exit)
    summary: dict[str, Any] = {
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "execution_venue": first_binding.execution_venue,
        "execution_symbol": first_binding.execution_symbol,
        "real_market_symbol": first_binding.real_market_symbol,
        "run_profile_id": spec.experiment.run_profile_id,
        "side": spec.rules.side,
        "timeframe": spec.rules.timeframe,
        "entry_rule_count": _condition_count(spec.rules.entry),
        "hold_rule_count": _condition_count(spec.rules.hold) if spec.rules.hold is not None else 0,
        "exit_rule_fields": exit_fields,
        "position_weight": spec.rules.sizing.position_weight,
        "notional_usd": spec.rules.sizing.notional_usd,
        "split_method": spec.backtest.split_method,
        "label_horizon_minutes": spec.backtest.label_horizon_minutes,
        "primary_metric": spec.backtest.primary_metric,
    }
    markdown = "\n".join(
        [
            "- status: `present`",
            f"- strategy_id: `{summary['strategy_id']}`",
            f"- strategy_family: `{summary['strategy_family']}`",
            f"- strategy_version: `{summary['strategy_version']}`",
            f"- execution_venue: `{summary['execution_venue']}`",
            f"- execution_symbol: `{summary['execution_symbol']}`",
            f"- real_market_symbol: `{summary['real_market_symbol']}`",
            f"- run_profile_id: `{summary['run_profile_id']}`",
            f"- side: `{summary['side']}`",
            f"- timeframe: `{summary['timeframe']}`",
            f"- entry_rule_count: `{summary['entry_rule_count']}`",
            f"- hold_rule_count: `{summary['hold_rule_count']}`",
            f"- exit_rule_fields: `{', '.join(exit_fields) if exit_fields else 'none'}`",
            f"- sizing.position_weight: `{summary['position_weight']}`",
            f"- sizing.notional_usd: `{summary['notional_usd']}`",
            f"- backtest.split_method: `{summary['split_method']}`",
            f"- backtest.label_horizon_minutes: `{summary['label_horizon_minutes']}`",
            f"- backtest.primary_metric: `{summary['primary_metric']}`",
        ]
    )
    return (
        present_optional_artifact(
            "authoring_spec",
            path,
            summary,
            payload=spec.model_dump(mode="json"),
        ),
        ReviewSection(
            section_id="strategy_definition",
            title="Strategy Definition",
            status="present",
            markdown=markdown,
            source_artifact_keys=("authoring_spec",),
        ),
    )


def not_configured_strategy_definition_section() -> ReviewSection:
    return ReviewSection(
        section_id="strategy_definition",
        title="Strategy Definition",
        status="not_configured",
        markdown="- status: `not_configured`\n- reason: `authoring spec path was not provided or derivable`",
    )
