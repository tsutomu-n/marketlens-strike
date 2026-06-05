<!--
作成日: 2026-05-31_07:20 JST
更新日: 2026-06-05_08:11 JST
-->

# Strategy Archetype Coverage Matrix

この文書は、`strategy_authoring_spec.v1` で生成しうる戦略タイプを「コードを正」として棚卸しするための coverage matrix です。

正本は次です。

- `src/sis/research/strategy_lab/authoring/`
- `src/sis/backtest/bridge.py`
- `src/sis/backtest/signals.py`
- `src/sis/research/strategy_lab/specs.py`
- `schemas/strategy_authoring_spec.v1.schema.json`
- `schemas/strategy_authoring_bundle.v1.schema.json`
- `tests/strategy_authoring/`

この matrix は completion audit 用です。ここに載っている「対応済み」は paper-only authoring / backtest / preview の意味であり、live order、wallet signing、exchange write、venue queue replay、収益保証の意味ではありません。

## Coverage Summary

| Archetype | Status | Main DSL surface | Evidence |
| --- | --- | --- | --- |
| Trend following / moving average cross | Supported | `derived_features`, `entry`, `value_column`, `crosses_above`, `rising` | `test_authoring_derived_features_support_ema_crossover_inputs`, `test_authoring_derived_features_support_macd_stochastic_and_adx_inputs`, `test_authoring_conditions_support_cross_trend_and_consecutive_operators` |
| Momentum / relative strength | Supported | `rolling_return`, `cumulative_return`, `slope`, `cross_sectional_rank`, `risk_adjusted_score` | `test_authoring_derived_features_support_return_volatility_and_shape_inputs`, `test_authoring_derived_features_support_cross_sectional_standardization` |
| Mean reversion | Supported | `rsi`, `rolling_zscore`, `distance_from_ma`, `mean_reversion_score`, Bollinger features | `test_authoring_derived_features_support_rsi_mean_reversion_inputs`, `test_authoring_derived_features_support_return_volatility_and_shape_inputs` |
| Breakout / channel / volatility breakout | Supported | Donchian, Keltner, Bollinger, ATR, true range, `volume_zscore` | `test_authoring_derived_features_support_breakout_channel_inputs`, `test_authoring_derived_features_support_channel_envelope_and_volume_inputs`, `test_authoring_derived_features_support_atr_volatility_inputs` |
| Volatility filter / volatility targeting | Supported | `realized_vol`, `annualized_volatility`, `downside_volatility`, `sizing.volatility_target` | `test_authoring_sizing_volatility_target_scales_position_weight`, `test_authoring_derived_features_support_return_volatility_and_shape_inputs` |
| Pair trade / spread / relative value | Supported | `rolling_spread_zscore`, `rolling_corr`, `rolling_beta`, `tracking_error`, `information_ratio`, `multi_leg` | `test_authoring_derived_features_support_cross_asset_pair_inputs`, `test_authoring_derived_features_support_benchmark_active_risk_inputs`, `test_authoring_multi_leg_expands_anchor_signal_into_pair_trade_legs` |
| Hedge / basket / multi-leg strategy | Supported | `rules.multi_leg`, per-leg side / weight / notional / exit / order / execution overrides | `test_authoring_backtest_summarizes_multi_leg_groups`, `test_authoring_multi_leg_supports_dynamic_hedge_ratio_columns`, `test_authoring_multi_leg_supports_leg_exit_overrides`, `test_authoring_multi_leg_supports_leg_order_overrides`, `test_authoring_multi_leg_supports_leg_execution_overrides` |
| Long / short fixed direction | Supported | `rules.side: long`, `rules.side: short` | fixed-side authoring tests in `tests/strategy_authoring/` |
| Long / short row-driven direction | Supported | `rules.side: auto`, `rules.side_column`, `long_entry`, `short_entry` | side-column / long-short branch tests in `tests/strategy_authoring/` |
| Cross-sectional top-bottom rotation | Supported | `rules.cross_sectional.long_top_n`, `short_bottom_n`, fractions, score thresholds | `test_authoring_cross_sectional_top_bottom_rotation_filters_middle_rank`, `test_authoring_cross_sectional_fraction_rotation_selects_quantile_tails`, `test_authoring_cross_sectional_score_thresholds_filter_weak_tails` |
| Group-aware rotation | Supported | `rules.cross_sectional.group_column`, group rank / z-score / demean features | `test_authoring_cross_sectional_group_top_bottom_rotation_filters_per_group`, `test_authoring_derived_features_support_group_cross_sectional_standardization` |
| Dollar-neutral / beta-neutral / group-neutral portfolio | Supported | `rules.portfolio.allocation_method`, `allocation_beta_column`, `group_column`, target total weight | `test_authoring_portfolio_dollar_neutral_allocation_balances_long_short_gross`, `test_authoring_portfolio_beta_neutral_allocation_balances_beta_exposure`, `test_authoring_portfolio_group_neutral_allocation_balances_each_group` |
| Event-driven / calendar-window strategy | Supported | `rules.event_windows`, calendar derived features, `temporal` filters | `test_authoring_event_window_allow_blocks_outside_or_missing_event`, `test_authoring_event_window_block_blocks_inside_blackout`, `test_authoring_derived_features_support_ichimoku_and_calendar_inputs` |
| Regime-aware strategy | Supported | `entry` category checks, `regime_overrides`, `regime_transition_score` | `test_authoring_regime_overrides_adjust_risk_sizing_and_execution`, `test_authoring_derived_features_support_onchain_sentiment_event_and_factor_inputs` |
| Quality / ensemble / composite factor | Supported | `ensemble_vote_count`, `ensemble_vote_ratio`, `data_quality_blend`, weighted score terms | `test_authoring_derived_features_support_quality_ensemble_capacity_inputs` |
| Flow / carry / funding / liquidity | Supported | `funding_bps`, `carry_adjusted_return`, `liquidity_depth_ratio`, `liquidity_stress`, `net_exchange_flow` | `test_authoring_derived_features_support_flow_carry_liquidity_and_vol_inputs` |
| Options / skew / volatility risk premium | Supported as feature-driven paper signal | `vol_risk_premium`, `put_call_skew`, `entry`, `hold`, `execution` gates | `test_authoring_derived_features_support_flow_carry_liquidity_and_vol_inputs` |
| On-chain / sentiment / fundamental event factor | Supported as feature-driven paper signal | `onchain_activity_ratio`, `sentiment_weighted_score`, `event_surprise`, `fundamental_value_gap` | `test_authoring_derived_features_support_onchain_sentiment_event_and_factor_inputs` |
| Execution-aware strategy | Supported | spread, depth, latency, queue, borrow, tax, turnover, capacity, crowding, fee-edge gates | `test_authoring_derived_features_support_execution_constraint_inputs`, execution profile / gate tests |
| Risk-throttled strategy | Supported | `rules.risk_throttle`, drawdown, daily loss, loss streak, cooldown | `test_authoring_risk_throttle_blocks_drawdown_daily_loss_and_loss_streak`, `test_authoring_risk_throttle_can_use_row_threshold_columns`, `test_authoring_risk_throttle_cooldown_blocks_following_signals` |
| Position-state strategy | Supported | `rules.position`, marker requirements, opposing-position and pyramiding controls | `test_authoring_position_rules_close_marker_releases_open_state`, position overlap tests |
| Reversal / close / reduce / add / rebalance lifecycle | Supported | `rules.close`, `rules.reduce`, `rules.add`, `rules.rebalance`, `exit_on_*_signal` | `test_authoring_position_rules_close_marker_releases_open_state`, `test_authoring_reduce_only_order_reduces_only_opposing_open_position`, exit-on-signal tests in `tests/strategy_authoring/` |
| Stop-loss / take-profit / trailing / partial exit | Supported | `rules.exit.*`, row-level bps columns, exit priority | `test_authoring_partial_take_profit_and_position_weight_affect_backtest`, `test_strategy_authoring_trailing_stop_can_exit_before_horizon`, `test_strategy_authoring_min_holding_minutes_defers_early_stop_loss` |
| Bracket / OCO-like lifecycle | Supported paper-only | `rules.bracket.enabled`, break-even, time stop, partial-profit break-even | `test_strategy_authoring_bracket_oco_take_profit_records_lifecycle`, `test_strategy_authoring_bracket_can_use_row_stop_column_as_exit_control`, `test_strategy_authoring_bracket_break_even_stop_can_exit_after_arm` |
| Market / limit / stop-market order simulation | Supported paper-only | `rules.order.entry_type`, offset columns, TIF, timeout, post-only, reduce-only | `test_authoring_multi_leg_supports_leg_order_overrides`, order lifecycle tests in `tests/strategy_authoring/` |
| Parameter sweep / optimizer | Supported paper-only | `optimizer.parameter_sweep`, dotted `selection_metric`, `selection_direction: auto` | optimizer tests in `tests/strategy_authoring/` |
| Multi-strategy bundle comparison | Supported paper-only | `strategy_authoring_bundle.v1`, fixed / equal / risk-parity allocation | bundle tests in `tests/strategy_authoring/` |

## Signal Lifecycle Coverage

| Signal intent | Status | Surface | Boundary |
| --- | --- | --- | --- |
| Entry long / short | Supported | `entry`, `long_entry`, `short_entry`, `side`, `side_column` | Creates paper signal rows, not live orders. |
| Hold / no-trade | Supported | `hold`, `side: none`, `block_reasons` | Preserved in artifacts and excluded from backtest entries. |
| Explicit close | Supported | `close`, `exit_on_close_signal` | Closes paper position; close marker does not open a reverse trade. |
| Reduce | Supported | `reduce`, `exit_on_reduce_signal`, `reduce_fraction` | Reduces paper exposure only. |
| Add | Supported | `add`, `exit_on_add_signal`, `add_fraction` | Adds to paper exposure in lifecycle, not as a separate independent entry. |
| Rebalance | Supported | `rebalance`, `exit_on_rebalance_signal`, `rebalance_target_fraction`, `rebalance_min_delta_fraction` | Resizes paper exposure; small drift can become `rebalance_band_skip`. |

## Coverage Boundaries

| Area | Status | Reason |
| --- | --- | --- |
| Live order submission | Out of scope | Strategy Authoring is paper-only and sets `live_order_submitted: false`. |
| Wallet signing / exchange write | Out of scope | No wallet or exchange write path is part of Strategy Lab authoring. |
| Broker position based live rebalance | Out of scope | Current rebalance is paper lifecycle resize, not broker-state rebalance. |
| Live multi-leg atomic execution | Out of scope | `multi_leg` creates paper signal legs and group metrics only. |
| Live OCO / bracket order | Out of scope | Bracket is paper lifecycle simulation. |
| Full order book event replay | Out of scope | Execution quality uses feature snapshot gates; queue priority replay is not implemented. |
| Profitability / live-ready claim | Out of scope | Artifacts are research evidence, not profitability or live-readiness proof. |
| Arbitrary user Python / formula execution | Intentionally unsupported | DSL is declarative and schema-validated to avoid unsafe execution. |
| External model artifact loading / pickle | Intentionally unsupported | `model_score` is paper-only linear scoring; no arbitrary model load. |

## Completion Evidence

Final completion evidence for the paper-only Strategy Authoring scope is recorded in `14_COMPLETION_EVIDENCE_LEDGER.md`.

Final audit result:

- All matrix test names were mechanically checked against `tests/strategy_authoring/`.
- No missing evidence test names were found.
- No newly found unsupported paper-only archetype remained outside the supported rows or explicit boundary rows above.
- Live execution, broker queue replay, exchange write, and profitability / live-ready claims remain outside Strategy Authoring unless a separate live-readiness design is approved.
