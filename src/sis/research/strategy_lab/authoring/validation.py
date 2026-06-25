from __future__ import annotations

from pathlib import Path

import polars as pl

from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.required_columns import (
    _all_conditions as _all_conditions,
    _prefixed_confirmation_columns as _prefixed_confirmation_columns,
    _required_columns as _required_columns,
)


def _resolve_path(raw: str, data_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return data_dir.parent / path
    return path


def validate_authoring_inputs(spec: StrategyAuthoringSpec, *, data_dir: Path) -> list[str]:
    errors: list[str] = []
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        errors.append(f"feature_panel_path not found: {feature_path}")
        return errors
    try:
        feature = pl.read_parquet(feature_path, n_rows=1)
    except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
        errors.append(f"feature_panel_path is not readable parquet: {exc}")
        return errors
    available_columns = set(feature.columns)
    for panel in spec.data.confirmation_panels:
        panel_path = _resolve_path(panel.path, data_dir)
        if not panel_path.exists():
            errors.append(f"confirmation panel not found: {panel_path}")
            continue
        try:
            panel_frame = pl.read_parquet(panel_path, n_rows=1)
        except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
            errors.append(f"confirmation panel is not readable parquet: {panel_path}: {exc}")
            continue
        required_panel_columns = {"ts", "canonical_symbol"}
        missing_panel_columns = sorted(required_panel_columns.difference(panel_frame.columns))
        if missing_panel_columns:
            errors.append(
                f"confirmation panel missing columns: {panel_path}: {missing_panel_columns}"
            )
            continue
        available_columns.update(_prefixed_confirmation_columns(panel, set(panel_frame.columns)))
    missing = sorted(_required_columns(spec).difference(available_columns))
    if missing:
        errors.append(f"feature panel missing columns: {missing}")
    generated: set[str] = set()
    base_columns = available_columns
    for derived in spec.rules.derived_features:
        available = base_columns.union(generated)
        missing_inputs = sorted(set(derived.columns).difference(available))
        if missing_inputs:
            errors.append(f"derived feature {derived.name} missing input columns: {missing_inputs}")
        generated.add(derived.name)
    binding_symbols = {binding.real_market_symbol for binding in spec.experiment.symbol_bindings}
    if spec.rules.multi_leg.enabled:
        symbols = {str(spec.rules.multi_leg.anchor_real_market_symbol)}
        leg_symbols = {leg.real_market_symbol for leg in spec.rules.multi_leg.legs}
        missing_bindings = sorted(leg_symbols.union(symbols).difference(binding_symbols))
        if missing_bindings:
            errors.append(f"multi_leg symbols missing symbol_bindings: {missing_bindings}")
    else:
        symbols = binding_symbols
    if "canonical_symbol" in feature.columns:
        full = pl.read_parquet(feature_path, columns=["canonical_symbol"])
        observed = {str(value).upper() for value in full.get_column("canonical_symbol").to_list()}
        missing_symbols = sorted(symbols.difference(observed))
        if missing_symbols:
            errors.append(f"feature panel missing real_market_symbol rows: {missing_symbols}")
    return errors
