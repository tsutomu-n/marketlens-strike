<!--
作成日: 2026-07-04_22:52 JST
更新日: 2026-07-04_22:52 JST
-->

# Pre Actual Cash Real Data Dogfood Blocker

- selected_next_blocker: `TICKER_SOURCE_MISSING_BLOCKS_COST_ADJUSTED_ESTIMATE_AND_EDGE_ACTION`
- decision: `COLLECT_MORE_SOURCES`
- reason_codes: `COST_ADJUSTED_INPUTS_MISSING, DEPTH_SOURCE_MISSING, OPTIONAL_FEATURES_MISSING, EDGE_SELECTED_ACTION_UNKNOWN, BIAS_GUARD_SAMPLE_INSUFFICIENT_OR_NOT_ESTIMABLE, BIAS_GUARD_NOT_PASSING`
- event_count: `10`
- outcome_count: `10`
- source_artifact_origin_counts: `{'existing': 10}`
- replay_artifact_origin_counts: `{'existing': 10}`
- feature_artifact_origin_counts: `{'existing': 10}`
- edge_artifact_origin_counts: `{'existing': 10}`
- selected_action_counts: `{'UNKNOWN': 10}`
- leader_action: `REVERSAL_SHORT`
- leader_beats_no_trade: `True`
- bias_guard_status: `BLOCKED`
- pbo_status: `NOT_ESTIMABLE`

## Why This One

All 10 source_availability artifacts are existing, but ticker is missing for all events. Because cost-adjusted estimate requires event, bars, ticker, and funding, this keeps can_compute_cost_adjusted_estimate=false and selected_action=UNKNOWN. This is lighter to test next than trades/books/replay.

Do not fix trades, books, replay, event definition, and bias sample size in the same step. The next G3 candidate is one light source improvement: ticker first, with funding checked only if ticker alone does not change the cost-adjusted estimate blocker.

This is not profit proof, actual cash readiness, tiny-live readiness, or live trading readiness.
