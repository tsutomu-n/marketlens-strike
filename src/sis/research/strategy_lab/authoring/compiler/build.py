from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from sis.research.strategy_lab.authoring.compiler.build_outputs import (
    _build_signal_frame_and_manifest,
)
from sis.research.strategy_lab.authoring.compiler.build_signal_rows import (
    _build_signal_rows,
)
from sis.research.strategy_lab.authoring.compiler.cross_sectional import (
    _apply_cross_sectional_selection,
)
from sis.research.strategy_lab.authoring.compiler.guards import (
    _apply_reward_risk_gate,
    _apply_stop_target_width_gate,
    _apply_temporal_selection,
)
from sis.research.strategy_lab.authoring.compiler.portfolio import (
    _apply_portfolio_allocation,
    _apply_portfolio_exposure_limits,
    _apply_portfolio_signal_limit,
    _apply_portfolio_turnover_budget,
)
from sis.research.strategy_lab.authoring.compiler.position import _apply_position_state_limits
from sis.research.strategy_lab.authoring.confirmation import _apply_confirmation_panels
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.features import (
    _apply_condition_features,
    _apply_derived_features,
)
from sis.research.strategy_lab.authoring.validation import _resolve_path, validate_authoring_inputs
from sis.research.strategy_lab.signal_artifact import StrategySignalManifest


def build_authoring_signals(
    spec: StrategyAuthoringSpec, *, data_dir: Path
) -> tuple[pl.DataFrame, StrategySignalManifest]:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    if errors:
        raise StrategyAuthoringValidationError("; ".join(errors))
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    feature = _apply_condition_features(
        _apply_derived_features(
            _apply_confirmation_panels(pl.read_parquet(feature_path), spec, data_dir=data_dir),
            spec,
        ),
        spec,
    )
    generated_at = datetime.now(timezone.utc)
    rows = _build_signal_rows(spec=spec, feature=feature, generated_at=generated_at)
    rows = [_apply_stop_target_width_gate(row, spec) for row in rows]
    rows = [_apply_reward_risk_gate(row, spec) for row in rows]
    rows = _apply_cross_sectional_selection(rows, spec)
    rows = _apply_temporal_selection(rows, spec)
    rows = _apply_position_state_limits(rows, spec)

    rows = _apply_portfolio_signal_limit(rows, spec)
    rows = _apply_portfolio_allocation(rows, spec)
    rows = _apply_portfolio_turnover_budget(rows, spec)
    rows = _apply_portfolio_exposure_limits(rows, spec)
    rows = sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"]))

    return _build_signal_frame_and_manifest(
        rows=rows,
        spec=spec,
        feature_path=feature_path,
        generated_at=generated_at,
    )
