from __future__ import annotations

from datetime import datetime
from typing import Any

from sis.research.strategy_lab.authoring.compiler.marker_defaults import (
    _marker_trade_control_defaults,
)
from sis.research.strategy_lab.authoring.compiler.row_values import _sizing_value
from sis.research.strategy_lab.authoring.compiler.signal_ids import _signal_id
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _marker_signal_base(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
    side: str,
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_signal.v1",
        "signal_id": _signal_id(spec, row, binding, side=side),
        "generated_at": generated_at,
        "strategy_id": spec.experiment.strategy_id,
        "strategy_family": spec.experiment.strategy_family,
        "strategy_version": spec.experiment.strategy_version,
        "trial_id": None,
        "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
        "ts_signal": row["ts"],
        "timeframe": spec.rules.timeframe,
        "execution_venue": binding.execution_venue,
        "execution_symbol": binding.execution_symbol,
        "real_market_symbol": binding.real_market_symbol,
        "side": side,
        "raw_score": None,
        "rank_score": None,
        "percentile_rank": None,
        "tail_bucket": "none",
        "confidence": 0.0,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
    }


def _close_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="close",
        ),
        **_marker_trade_control_defaults(),
        "reason_codes": [spec.rules.close_reason_code],
        "block_reasons": [],
    }


def _hold_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
    block_reason: str | None = "hold_rule",
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="none",
        ),
        **_marker_trade_control_defaults(),
        "reason_codes": [spec.rules.hold_reason_code],
        "block_reasons": [block_reason or "hold_rule"],
    }


def _reduce_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="reduce",
        ),
        **_marker_trade_control_defaults(),
        "reduce_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.reduce_fraction,
            column=spec.rules.exit.reduce_fraction_column,
        ),
        "reason_codes": [spec.rules.reduce_reason_code],
        "block_reasons": [],
    }


def _add_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="add",
        ),
        **_marker_trade_control_defaults(),
        "add_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.add_fraction,
            column=spec.rules.exit.add_fraction_column,
        ),
        "reason_codes": [spec.rules.add_reason_code],
        "block_reasons": [],
    }


def _rebalance_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    generated_at: datetime,
) -> dict[str, Any]:
    return {
        **_marker_signal_base(
            spec=spec,
            row=row,
            binding=binding,
            generated_at=generated_at,
            side="rebalance",
        ),
        **_marker_trade_control_defaults(),
        "rebalance_target_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_target_fraction,
            column=spec.rules.exit.rebalance_target_fraction_column,
        ),
        "rebalance_min_delta_fraction": _sizing_value(
            row,
            fixed=spec.rules.exit.rebalance_min_delta_fraction,
            column=spec.rules.exit.rebalance_min_delta_fraction_column,
        ),
        "reason_codes": [spec.rules.rebalance_reason_code],
        "block_reasons": [],
    }
