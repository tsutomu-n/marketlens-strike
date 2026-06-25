from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import polars as pl

from sis.research.strategy_lab.authoring.compiler.common import (
    _block_trade_row,
)
from sis.research.strategy_lab.authoring.compiler.cross_sectional import (
    _apply_cross_sectional_selection,
)
from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _entry_passes,
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
from sis.research.strategy_lab.authoring.compiler.marker_rows import (
    _add_signal_row,
    _close_signal_row,
    _hold_signal_row,
    _rebalance_signal_row,
    _reduce_signal_row,
)
from sis.research.strategy_lab.authoring.compiler.multi_leg_rows import _multi_leg_signal_rows
from sis.research.strategy_lab.authoring.compiler.portfolio import (
    _apply_portfolio_allocation,
    _apply_portfolio_exposure_limits,
    _apply_portfolio_turnover_budget,
)
from sis.research.strategy_lab.authoring.compiler.position import _apply_position_state_limits
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.authoring.confirmation import _apply_confirmation_panels
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.features import (
    _apply_condition_features,
    _apply_derived_features,
)
from sis.research.strategy_lab.authoring.validation import _resolve_path, validate_authoring_inputs
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    empty_signal_artifact_run_id,
    empty_strategy_signal_frame,
    file_sha256,
    signal_artifact_run_id,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame


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
        if spec.rules.close is not None and _entry_passes(row, spec.rules.close):
            rows.append(
                _close_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.reduce is not None and _entry_passes(row, spec.rules.reduce):
            rows.append(
                _reduce_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.add is not None and _entry_passes(row, spec.rules.add):
            rows.append(
                _add_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.rebalance is not None and _entry_passes(row, spec.rules.rebalance):
            rows.append(
                _rebalance_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                )
            )
            continue
        if spec.rules.hold is not None and _entry_passes(row, spec.rules.hold):
            rows.append(
                _hold_signal_row(
                    spec=spec,
                    row=row,
                    binding=binding,
                    generated_at=generated_at,
                    block_reason="hold_rule",
                )
            )
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
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
                    block_reason=event_block_reason,
                )
            )
            continue
        data_guard_block_reason = _data_guard_block_reason(row, spec)
        if data_guard_block_reason is not None:
            rows.append(
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
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
                _block_trade_row(
                    _trade_signal_row(
                        spec=spec,
                        row=row,
                        binding=binding,
                        side=signal_side,
                        generated_at=generated_at,
                        raw_score=raw_score,
                        rank=rank,
                    ),
                    spec=spec,
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

    if spec.rules.portfolio.max_signals_per_timestamp is not None:
        grouped: dict[Any, list[dict[str, Any]]] = {}
        passthrough: list[dict[str, Any]] = []
        for item in rows:
            if item["side"] == "none":
                passthrough.append(item)
                continue
            grouped.setdefault(item["ts_signal"], []).append(item)
        limited: list[dict[str, Any]] = passthrough[:]
        limit = spec.rules.portfolio.max_signals_per_timestamp
        for timestamp_rows in grouped.values():
            limited.extend(
                sorted(
                    timestamp_rows,
                    key=lambda item: (
                        item.get("rank_score") if item.get("rank_score") is not None else -1.0
                    ),
                    reverse=True,
                )[:limit]
            )
        rows = limited
    rows = _apply_portfolio_allocation(rows, spec)
    rows = _apply_portfolio_turnover_budget(rows, spec)
    rows = _apply_portfolio_exposure_limits(rows, spec)
    rows = sorted(rows, key=lambda item: (item["ts_signal"], item["signal_id"]))

    frame = (
        empty_strategy_signal_frame()
        if not rows
        else validate_strategy_signal_frame(
            pl.DataFrame(rows), symbol_bindings=spec.experiment.symbol_bindings
        )
    )
    feature_hash = file_sha256(feature_path)
    run_id = (
        empty_signal_artifact_run_id(
            generator_id="strategy_authoring",
            strategy_id=spec.experiment.strategy_id,
            strategy_family=spec.experiment.strategy_family,
            strategy_version=spec.experiment.strategy_version,
            symbol_bindings=spec.experiment.symbol_bindings,
            feature_panel_sha256=feature_hash,
        )
        if frame.is_empty()
        else signal_artifact_run_id(frame)
    )
    manifest = StrategySignalManifest(
        schema_version="strategy_signal_manifest.v1",
        generated_at=generated_at,
        generator_id="strategy_authoring",
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        symbol_bindings=spec.experiment.symbol_bindings,
        feature_panel_sha256=feature_hash,
        signal_count=frame.height,
        signal_artifact_run_id=run_id,
        generator_parameters={
            "authoring_schema_version": spec.schema_version,
            "reason_code": spec.rules.reason_code,
        },
    )
    return frame, manifest
