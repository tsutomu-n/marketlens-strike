from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.build_outputs import (
    _build_signal_frame_and_manifest,
)
from sis.research.strategy_lab.authoring.compiler.cross_sectional import (
    _apply_cross_sectional_selection,
)
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _rank_score,
    _score,
    _selected_side,
)
from sis.research.strategy_lab.authoring.compiler.guards import (
    _apply_reward_risk_gate,
    _apply_stop_target_width_gate,
    _apply_temporal_selection,
)
from sis.research.strategy_lab.authoring.compiler.guard_block_reasons import (
    _data_guard_block_reason,
    _event_window_block_reason,
    _feature_timestamp,
    _risk_throttle_block_reason,
)
from sis.research.strategy_lab.authoring.compiler.marker_dispatch import _marker_rule_signal_row
from sis.research.strategy_lab.authoring.compiler.marker_rows import _hold_signal_row
from sis.research.strategy_lab.authoring.compiler.multi_leg_rows import _multi_leg_signal_rows
from sis.research.strategy_lab.authoring.compiler.portfolio import (
    _apply_portfolio_allocation,
    _apply_portfolio_exposure_limits,
    _apply_portfolio_signal_limit,
    _apply_portfolio_turnover_budget,
)
from sis.research.strategy_lab.authoring.compiler.position import _apply_position_state_limits
from sis.research.strategy_lab.authoring.compiler.trade_block_rows import _blocked_trade_signal_row
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
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
    bindings = {binding.real_market_symbol: binding for binding in spec.experiment.symbol_bindings}
    rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)
    risk_throttle_cooldown_until_by_symbol: dict[str, datetime] = {}
    for row in feature.sort(["canonical_symbol", "ts"]).to_dicts():
        symbol = str(row.get("canonical_symbol") or "").upper()
        if (
            spec.rules.multi_leg.enabled
            and symbol != spec.rules.multi_leg.anchor_real_market_symbol
        ):
            continue
        binding = bindings.get(symbol)
        if binding is None:
            continue
        marker_row = _marker_rule_signal_row(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
        )
        if marker_row is not None:
            rows.append(marker_row)
            continue
        signal_side, block_reason = _selected_side(row, spec.rules)
        if signal_side is None:
            continue
        if signal_side == "none":
            rows.append(
                _hold_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                    block_reason=block_reason,
                )
            )
            continue
        raw_score = _score(row, spec.rules.score)
        rank = _rank_score(raw_score)
        event_block_reason = _event_window_block_reason(row, spec)
        if event_block_reason is not None:
            rows.append(
                _blocked_trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                    block_reason=event_block_reason,
                )
            )
            continue
        data_guard_block_reason = _data_guard_block_reason(row, spec)
        if data_guard_block_reason is not None:
            rows.append(
                _blocked_trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                    block_reason=data_guard_block_reason,
                )
            )
            continue
        ts_signal = _feature_timestamp(row)
        cooldown_until = risk_throttle_cooldown_until_by_symbol.get(symbol)
        if cooldown_until is not None and ts_signal < cooldown_until:
            risk_throttle_block_reason = "risk_throttle_cooldown"
        else:
            risk_throttle_block_reason = _risk_throttle_block_reason(row, spec)
        if risk_throttle_block_reason is not None:
            if (
                risk_throttle_block_reason != "risk_throttle_cooldown"
                and spec.rules.risk_throttle.cooldown_minutes is not None
            ):
                risk_throttle_cooldown_until_by_symbol[symbol] = ts_signal + timedelta(
                    minutes=spec.rules.risk_throttle.cooldown_minutes
                )
            rows.append(
                _blocked_trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                    block_reason=risk_throttle_block_reason,
                )
            )
            continue
        if spec.rules.multi_leg.enabled:
            rows.extend(
                _multi_leg_signal_rows(
                    spec=spec,
                    row=row,
                    bindings=bindings,
                    base_side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
        else:
            rows.append(
                _trade_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    side=signal_side,
                    generated_at=generated_at,
                    raw_score=raw_score,
                    rank=rank,
                )
            )
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
