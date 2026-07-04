<!--
作成日: 2026-07-04_22:52 JST
更新日: 2026-07-04_22:52 JST
-->

# Pre Actual Cash Evidence Decision

- created_at: `2026-07-04T13:52:00Z`
- event_count: `10`
- outcome_count: `10`
- main_source_gaps: `books:10, cash_ledger:10, live_measurement:10, replay:10, ticker:10, trades:10`
- selected_action_counts: `{'UNKNOWN': 10}`
- leader_action: `REVERSAL_SHORT`
- leader_beats_no_trade: `True`
- bias_guard_status: `BLOCKED`
- pbo_status: `NOT_ESTIMABLE`
- actual_cash_used: `false`
- profit_proven: `false`
- actual_cash_readiness_claimed: `false`
- tiny_live_readiness_claimed: `false`
- live_trading_readiness_claimed: `false`
- decision: `COLLECT_MORE_SOURCES`
- reason_codes: `COST_ADJUSTED_INPUTS_MISSING, DEPTH_SOURCE_MISSING, OPTIONAL_FEATURES_MISSING, EDGE_SELECTED_ACTION_UNKNOWN, BIAS_GUARD_SAMPLE_INSUFFICIENT_OR_NOT_ESTIMABLE, BIAS_GUARD_NOT_PASSING`
- next_action: trades、books、ticker、funding、replay、cost inputs など不足 source を追加収集する。

This pack is a pre-actual-cash candidate handling gate only. It does not prove profit, actual cash readiness, tiny-live readiness, or live trading readiness.
