<!--
作成日: 2026-07-06_18:03 JST
更新日: 2026-07-11_18:35 JST
-->

# Crypto Perp No-Cash Backtest Gate v1

## 結論

`crypto-perp-no-cash-backtest-gate` は、no-cash backtest evidence pack を Paper Observation 手前で読むための local gate です。

この gate は Paper Observation の最終許可を出しません。`NO_CASH_BACKTEST_HOLD` は「human review に残してよい no-cash local simulation 候補」という意味であり、paper order permission、profit proof、actual cash readiness、tiny-live readiness、live readiness ではありません。

## Stage Order

```text
No-cash backtest evidence pack
  -> no-cash backtest gate
  -> human review for paper observation
  -> Paper Observation
  -> Actual Cash evidence
```

## CLI

```bash
uv run sis crypto-perp-no-cash-backtest-gate \
  --decision data/crypto_perp/backtest_candidate_pack/latest/decision.json \
  --data-availability data/crypto_perp/backtest_candidate_pack/latest/data_availability_ledger.json \
  --backtest data/crypto_perp/backtest_candidate_pack/latest/backtest_result.json \
  --stress data/crypto_perp/backtest_candidate_pack/latest/stress_result.json \
  --rolling-stability data/crypto_perp/backtest_candidate_pack/latest/rolling_stability_result.json \
  --out data/crypto_perp/no_cash_backtest_gate/latest
```

stdout always reports no external side effects:

```text
network_attempted=false
exchange_write_used=false
live_order_submitted=false
actual_cash_used=false
paper_permission_granted=false
permits_paper_order=false
permits_live_order=false
profit_proven=false
```

## Decisions

- `NO_CASH_BACKTEST_COLLECT_MORE_DATA`
- `NO_CASH_BACKTEST_REVISE`
- `NO_CASH_BACKTEST_REJECT`
- `NO_CASH_BACKTEST_HOLD`

There is no `PROMOTE_TO_PAPER`, `READY_FOR_PAPER_ORDER`, or `READY_FOR_LIVE` decision.

## What It Blocks

The gate keeps blockers machine-readable across input, candidate, event, source, and metric scopes. It blocks or records at least:

- legacy or missing `evidence_grade_summary`
- current `BACKTEST_COLLECT_MORE_DATA`
- critical source missing
- future signal source usage
- event sample below gate threshold
- rolling stability sample insufficiency
- PBO uncomputed、not estimable、missing、unknown
- non-positive after-cost backtest total
- non-positive stress total
- `NO_TRADE` not beaten after cost
- too few simulated trades
- `UNKNOWN` selected actions
- missing selected action rows
- overlapping positions whose capital/exposure has not been accounted
- missing books / trades / replay as known gaps when not required

## Boundary

This artifact does not require API credentials, wallet, signing, exchange write, cash ledger, actual cash source, or credentialed read. Missing sources are never zero-filled. `NO_TRADE` remains a valid result and is never replaced by a trade action.

## Bias Guard / PBO Defense-In-Depth

No-cash gateはcandidate decisionだけを信頼せず、`bias_guard_status`と`pbo_status`を直接検査します。guard `BLOCKED`は`NO_CASH_BACKTEST_REJECT`、guard missing / NOT_RUN / unknownは`NO_CASH_BACKTEST_COLLECT_MORE_DATA`です。PBOは`COMPUTED_PASS`だけが通過可能です。`INPUT_THRESHOLD_MET`とlegacy `ESTIMATED`は未計算なので`PBO_NOT_COMPUTED`としてCOLLECTへ落とします。PASS guardのwarning codeはblockerへ変換せずsummaryとknown gapsへ残します。

## Current Runtime Result

```text
gate_decision=NO_CASH_BACKTEST_REJECT
reason_codes=BIAS_GUARD_BLOCKED,BIAS_GUARD_FAILED_sample_sufficient_for_pbo,BACKTEST_CANDIDATE_PACK_REJECT,POSITION_OVERLAP_NOT_ACCOUNTED,INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET,SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION,PBO_NOT_ESTIMABLE_OR_MISSING
bias_guard_status=BLOCKED
pbo_status=NOT_ESTIMABLE
```

guard BLOCKEDを最優先でREJECTし、candidateとPBOの停止理由も欠落させません。正の名目損益だけを根拠にHOLDへ昇格しません。
