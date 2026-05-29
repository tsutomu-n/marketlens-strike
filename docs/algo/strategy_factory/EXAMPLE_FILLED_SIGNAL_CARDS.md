# Example Filled Signal Cards

記入済みサンプルです。実データではなく、書き方の例です。

## SIG-001 Trend Pullback Resume

```md
# Signal Candidate: SIG-001 Trend Pullback Resume

## Status

- status: specified
- next_gate: data-ready
- duplicate_key: pullback:liquid-major:4h:ma-pullback

## Hypothesis

- one_sentence_hypothesis: 上昇trend中の浅い押しからの再上昇だけを拾うと、常時trend longよりentry直後の逆行が減る。
- archetype: pullback
- market: liquid major markets
- symbol_universe: high-liquidity symbols only
- timeframe: 4h
- holding_horizon: 1-6 bars
- side: long

## Signal Contract

- required_inputs: close, sma20, sma50, sma50_slope, short_momentum, recent_swing_low, spread_bps, data_status
- trigger: close > sma50 and sma50_slope > 0 and near sma20 and short_momentum_turns_up
- invalidation: recent_swing_low break
- no_trade_conditions: data_status != valid, panic regime, wide spread
- signal_output_columns: ts_signal, symbol, side, timeframe, reason, score, invalidation_price

## Baseline

- baseline_name: trend_always_long_when_above_sma50
- baseline_logic: close > sma50ならlong候補
- why_fair: 同じtrend前提でpullback条件の追加価値を見るため

## Reject Rules

- taxonomy_codes: BACKTEST_COST_FRAGILE, SIGNAL_LATE_ENTRY, BACKTEST_TRADE_COUNT_LOW
```

## SIG-002 Breakout With Retest

```md
# Signal Candidate: SIG-002 Breakout With Retest

- status: idea
- archetype: breakout
- one_sentence_hypothesis: range上抜け後のretest成功を待つと、simple breakoutよりfalse breakoutが減る。
- required_inputs: range_high, range_low, breakout_flag, retest_hold_flag, volume, spread_bps
- trigger: breakout then retest holds then momentum resumes
- invalidation: range_highを再び下回る
- no_trade_conditions: event_gap, wide_spread, insufficient_range_history
- baseline: simple breakout
- taxonomy_codes_if_rejected: SIGNAL_FALSE_BREAKOUT, BACKTEST_TRADE_COUNT_LOW
```

## SIG-003 Mean Reversion In Range

```md
# Signal Candidate: SIG-003 Mean Reversion In Range

- status: idea
- archetype: mean-reversion
- one_sentence_hypothesis: range regimeではz-score extremeからfair valueへ戻る候補がある。
- required_inputs: z_score, band_mid, regime, realized_vol, spread_bps
- trigger: regime == range and abs(z_score) > threshold
- invalidation: regime changes to trend or price accelerates outside band
- no_trade_conditions: panic, strong trend, wide spread
- baseline: simple RSI
- taxonomy_codes_if_rejected: SIGNAL_TREND_AGAINST, RISK_TAIL_LOSS_HIGH
```

## Rejected Bad Signal Example

```md
# Signal Candidate: REJ-001 LLM Says Buy

- status: rejected
- archetype: event
- one_sentence_hypothesis: LLMが上がると言ったら買う。
- trigger: unclear natural language output
- invalidation: none
- baseline: none
- reject_reason_code:
  - SPEC_NO_INVALIDATION
  - SPEC_NO_BASELINE
  - SPEC_TRIGGER_AMBIGUOUS
  - SIGNAL_SCORE_UNDEFINED
- evidence: 再現可能なtrigger、baseline、invalidationがない。
```
