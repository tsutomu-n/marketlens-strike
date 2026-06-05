<!--
作成日: 2026-05-29_22:07 JST
更新日: 2026-06-05_08:11 JST
-->

# Archetype Required Inputs

売買発生シグナルのarchetypeごとに、最低限必要な入力列と検査を固定します。

## Trend Continuation

| required | examples |
|---|---|
| price | close, high, low |
| trend | long_ma, ma_slope, higher_high_low |
| risk | realized_vol, spread_bps |
| invalidation | recent_swing_low/high |

Minimum checks:

- trend判定が未来を見ていない。
- range期間での損失が測られている。
- baselineはMA crossまたはDonchian。

## Pullback Resume

| required | examples |
|---|---|
| trend | long_ma, ma_slope |
| pullback | distance_to_ma, retracement_pct |
| resume | short_momentum, candle structure |
| invalidation | pullback_low/high |

Minimum checks:

- entry直後の逆行幅を見る。
- high-vol/panicでの発火を除外する。
- baselineはtrend中の常時longまたは単純MA反発。

## Breakout With Retest

| required | examples |
|---|---|
| range | range_high, range_low |
| breakout | breakout_flag |
| retest | retest_hold_flag |
| liquidity | spread_bps, volume |

Minimum checks:

- breakout candleだけで入っていない。
- false breakout率を測る。
- baselineはsimple breakout。

## Mean Reversion

| required | examples |
|---|---|
| fair value | ma, vwap, band_mid |
| deviation | z_score, band_position |
| regime | range_flag, trend_flag |
| stop | trend_break_condition |

Minimum checks:

- trend regimeで止める。
- panic/high volで止める。
- baselineはsimple RSIまたはband reversal。

## Volatility Expansion

| required | examples |
|---|---|
| compression | atr_percentile, band_width |
| expansion | range_break, volume_expansion |
| price | high, low, close |
| execution risk | spread_bps, gap flag |

Minimum checks:

- event gap直後を除外する。
- slippage x2を見る。
- baselineはDonchian breakout。

## Regime Filtered Signal

| required | examples |
|---|---|
| base signal | signal_id, side, trigger |
| regime | trend, range, panic, unknown |
| filter | allowed_regimes |
| skipped pnl | virtual_pnl_for_skips |

Minimum checks:

- skipした取引の仮想PnLを保存する。
- skip率だけで有効と判断しない。
- baselineはbase signal without filter。

## Cross-asset Confirmation

| required | examples |
|---|---|
| target | target returns/features |
| related | related asset returns/features |
| timing | observed_at, aligned_ts |
| invalidation | confirmation reversal |

Minimum checks:

- related dataの時刻がtarget decisionより後でない。
- confirmationが遅すぎない。
- baselineはtarget-only signal。

## Event Reaction

| required | examples |
|---|---|
| event | event_ts, first_seen_ts, source |
| reaction | before/after return, volume |
| tradability | spread, liquidity |
| label | event_type, reaction_bucket |

Minimum checks:

- event前から価格が動いていないか確認する。
- first_seen_tsを使う。
- baselineはeventなし同時刻分布。
