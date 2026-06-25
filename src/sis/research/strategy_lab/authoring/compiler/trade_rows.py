from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sis.research.strategy_lab.authoring.compiler.common import (
    _matching_regime_override,
    _signal_notional_usd,
    _signal_position_weight,
)
from sis.research.strategy_lab.authoring.compiler.row_values import (
    _exit_bps,
    _minutes_value,
    _optional_float_from_row,
)
from sis.research.strategy_lab.authoring.compiler.signal_ids import _signal_id
from sis.research.strategy_lab.authoring.compiler.signal_selection import _tail_bucket
from sis.research.strategy_lab.authoring.compiler.trade_execution_fields import (
    _trade_execution_fields,
)
from sis.research.strategy_lab.authoring.compiler.trade_exit_fields import _trade_exit_fields
from sis.research.strategy_lab.authoring.compiler.trade_order_fields import _trade_order_fields
from sis.research.strategy_lab.authoring.contracts.base import _stable_digest
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.specs import SymbolBinding


def _trade_signal_row(
    *,
    spec: StrategyAuthoringSpec,
    row: dict[str, Any],
    binding: SymbolBinding,
    side: Literal["long", "short"],
    generated_at: datetime,
    raw_score: float | None,
    rank: float | None,
    position_weight: float | None = None,
    notional_usd: float | None = None,
    exit_overrides: dict[str, float | None] | None = None,
    order_overrides: dict[str, Any] | None = None,
    execution_overrides: dict[str, Any] | None = None,
    multi_leg_group_id: str | None = None,
    multi_leg_leg_index: int | None = None,
    multi_leg_leg_count: int | None = None,
    multi_leg_anchor_real_market_symbol: str | None = None,
    reason_codes: list[str] | None = None,
) -> dict[str, Any]:
    regime = _matching_regime_override(row, spec)
    effective_reason_codes = reason_codes or [spec.rules.reason_code]
    if regime is not None:
        effective_reason_codes = [*effective_reason_codes, f"regime:{regime.name}"]
    order_fields = _trade_order_fields(
        row=row, order=spec.rules.order, order_overrides=order_overrides
    )
    execution_fields = _trade_execution_fields(
        row=row,
        execution=spec.rules.execution,
        regime=regime,
        execution_overrides=execution_overrides,
    )
    reduce_only = bool(order_fields["entry_reduce_only"])
    exit_fields = _trade_exit_fields(
        row=row,
        exit_rules=spec.rules.exit,
        reduce_only=reduce_only,
        regime=regime,
        exit_overrides=exit_overrides,
    )
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
        "multi_leg_group_id": multi_leg_group_id,
        "multi_leg_leg_index": multi_leg_leg_index,
        "multi_leg_leg_count": multi_leg_leg_count,
        "multi_leg_anchor_real_market_symbol": multi_leg_anchor_real_market_symbol,
        "side": side,
        "raw_score": raw_score,
        "rank_score": rank,
        "percentile_rank": rank,
        "tail_bucket": _tail_bucket(rank),
        "confidence": spec.rules.confidence,
        "source_confidence": row.get("source_confidence"),
        "venue_quality_score": row.get("venue_quality_score"),
        "feature_snapshot_ref": None,
        "quote_ref": None,
        "tracking_ref": None,
        **exit_fields,
        "bracket_type": spec.rules.bracket.bracket_type if spec.rules.bracket.enabled else "none",
        "bracket_time_stop_minutes": _minutes_value(
            row,
            fixed=spec.rules.bracket.time_stop_minutes if spec.rules.bracket.enabled else None,
            column=(
                spec.rules.bracket.time_stop_minutes_column if spec.rules.bracket.enabled else None
            ),
        ),
        "bracket_break_even_after_bps": _exit_bps(
            row,
            fixed=spec.rules.bracket.break_even_after_bps if spec.rules.bracket.enabled else None,
            column=(
                spec.rules.bracket.break_even_after_bps_column
                if spec.rules.bracket.enabled
                else None
            ),
        ),
        "bracket_break_even_after_partial_take_profit": (
            spec.rules.bracket.break_even_after_partial_take_profit
            if spec.rules.bracket.enabled
            else False
        ),
        **order_fields,
        **execution_fields,
        "position_weight": position_weight
        if position_weight is not None
        else _signal_position_weight(row, spec),
        "notional_usd": notional_usd
        if notional_usd is not None
        else _signal_notional_usd(row, spec),
        "_cross_sectional_group": row.get(spec.rules.cross_sectional.group_column)
        if spec.rules.cross_sectional.group_column is not None
        else None,
        "_allocation_volatility": row.get(spec.rules.portfolio.allocation_volatility_column)
        if spec.rules.portfolio.allocation_volatility_column is not None
        else None,
        "_allocation_beta": row.get(spec.rules.portfolio.allocation_beta_column)
        if spec.rules.portfolio.allocation_beta_column is not None
        else None,
        "_portfolio_target_total_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.target_total_position_weight_column
        )
        if spec.rules.portfolio.target_total_position_weight_column is not None
        else None,
        "_portfolio_max_total_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_total_position_weight_column
        )
        if spec.rules.portfolio.max_total_position_weight_column is not None
        else None,
        "_portfolio_max_long_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_long_position_weight_column
        )
        if spec.rules.portfolio.max_long_position_weight_column is not None
        else None,
        "_portfolio_max_short_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_short_position_weight_column
        )
        if spec.rules.portfolio.max_short_position_weight_column is not None
        else None,
        "_portfolio_max_abs_net_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_abs_net_position_weight_column
        )
        if spec.rules.portfolio.max_abs_net_position_weight_column is not None
        else None,
        "_portfolio_max_symbol_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_symbol_position_weight_column
        )
        if spec.rules.portfolio.max_symbol_position_weight_column is not None
        else None,
        "_portfolio_max_group_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_group_position_weight_column
        )
        if spec.rules.portfolio.max_group_position_weight_column is not None
        else None,
        "_portfolio_max_group_abs_net_position_weight": _optional_float_from_row(
            row, spec.rules.portfolio.max_group_abs_net_position_weight_column
        )
        if spec.rules.portfolio.max_group_abs_net_position_weight_column is not None
        else None,
        "_portfolio_group": row.get(spec.rules.portfolio.group_column)
        if spec.rules.portfolio.group_column is not None
        else None,
        "_portfolio_turnover_weight": row.get(spec.rules.portfolio.turnover_weight_column)
        if spec.rules.portfolio.turnover_weight_column is not None
        else None,
        "reason_codes": effective_reason_codes,
        "block_reasons": [],
    }
