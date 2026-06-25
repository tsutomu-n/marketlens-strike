from __future__ import annotations

from typing import Any

from sis.research.strategy_lab.authoring.compiler.signal_selection import _entry_passes
from sis.research.strategy_lab.authoring.contracts.multi_leg import RegimeOverride
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _matching_regime_override(
    row: dict[str, Any], spec: StrategyAuthoringSpec
) -> RegimeOverride | None:
    for regime in spec.rules.regime_overrides:
        if _entry_passes(row, regime.when):
            return regime
    return None


def _regime_value(
    regime: RegimeOverride | None, field_name: str, default: float | None
) -> float | None:
    if regime is None:
        return default
    value = getattr(regime, field_name)
    return value if value is not None else default


def _exit_override(
    overrides: dict[str, float | None] | None, field_name: str, default: float | None
) -> float | None:
    if overrides is None:
        return default
    value = overrides.get(field_name)
    return value if value is not None else default


def _exit_override_column(
    overrides: dict[str, float | None] | None, field_name: str, default: str | None
) -> str | None:
    if overrides is not None and field_name in overrides:
        return None
    return default


def _override_value(overrides: dict[str, Any] | None, field_name: str, default: Any) -> Any:
    if overrides is None:
        return default
    value = overrides.get(field_name)
    return value if value is not None else default


def _override_column(
    overrides: dict[str, Any] | None, field_name: str, default: str | None
) -> str | None:
    if overrides is not None and field_name in overrides:
        return None
    return default
