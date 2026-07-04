<!--
作成日: 2026-07-04_22:52 JST
更新日: 2026-07-04_23:27 JST
-->

# Pre Actual Cash Real Data Dogfood Blocker

- selected_next_blocker: `DEPTH_SOURCE_MISSING_BLOCKS_OPTIONAL_FEATURES_AND_BIAS_INTERPRETATION`
- completed_blocker: `TICKER_SOURCE_MISSING_BLOCKS_COST_ADJUSTED_ESTIMATE_AND_EDGE_ACTION`
- decision: `COLLECT_MORE_SOURCES`
- reason_codes: `DEPTH_SOURCE_MISSING, OPTIONAL_FEATURES_MISSING, BIAS_GUARD_SAMPLE_INSUFFICIENT_OR_NOT_ESTIMABLE, BIAS_GUARD_NOT_PASSING`
- event_count: `10`
- outcome_count: `10`
- source_artifact_origin_counts: `{'existing': 10}`
- replay_artifact_origin_counts: `{'existing': 10}`
- feature_artifact_origin_counts: `{'existing': 10}`
- edge_artifact_origin_counts: `{'existing': 10}`
- can_compute_cost_adjusted_estimate_count: `10`
- ticker_missing_event_count: `0`
- selected_action_counts: `{'NO_TRADE': 8, 'REVERSAL_SHORT': 2}`
- unknown_selected_action_count: `0`
- leader_action: `REVERSAL_SHORT`
- leader_beats_no_trade: `True`
- bias_guard_status: `BLOCKED`
- pbo_status: `NOT_ESTIMABLE`

## What Changed

The G3 ticker source pass connected explicit local ticker proxy source refs into the 10 per-event `source_availability.json` artifacts. Ticker is no longer missing, `can_compute_cost_adjusted_estimate=true` for all 10 events, and edge selection no longer returns `UNKNOWN`.

The ticker proxy is derived from the local public 5m candle row at or before each event cutoff. It is not an exchange ticker snapshot, actual cash evidence, fill evidence, measured slippage, live readiness, or profit proof.

## Why This One

The remaining source blocker is depth and optional microstructure: trades, books, and replay are still missing for all 10 events, so `can_compute_depth=false`, OFI/trade-sign-imbalance are unavailable, and the candidate remains a pre-actual-cash source triage result.

Bias guard is still blocked and PBO is not estimable with this 10-event sample. Do not turn this into a 30-event expansion, trades/books/replay expansion, actual cash work, tiny-live work, or live trading work without a separate explicit instruction.

This is not profit proof, actual cash readiness, tiny-live readiness, or live trading readiness.
