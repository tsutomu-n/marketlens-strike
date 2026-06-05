<!--
作成日: 2026-05-29_22:07 JST
更新日: 2026-06-05_08:11 JST
-->

# Signal Reject Reason Taxonomy

候補を落とす理由は固定コードで残します。自由文だけにすると、後から同じ失敗を量産します。

## SPEC

| code | meaning |
|---|---|
| `SPEC_NO_INVALIDATION` | invalidationがない |
| `SPEC_NO_BASELINE` | baselineがない |
| `SPEC_TRIGGER_AMBIGUOUS` | triggerが曖昧 |
| `SPEC_TOO_COMPLEX` | 初期候補として複雑すぎる |
| `SPEC_SIGNAL_ORDER_MIXED` | signalとorderが混ざっている |

## DATA

| code | meaning |
|---|---|
| `DATA_NOT_AVAILABLE` | 必要データが取得できない |
| `DATA_HISTORY_TOO_SHORT` | 履歴が短い |
| `DATA_LIVE_ONLY` | liveでしか確認できず初期検証に不向き |
| `DATA_OBSERVED_AT_MISSING` | 利用可能時刻が分からない |
| `DATA_MISSINGNESS_HIGH` | 欠損率が高い |

## SIGNAL

| code | meaning |
|---|---|
| `SIGNAL_LATE_ENTRY` | signalが遅い |
| `SIGNAL_FALSE_BREAKOUT` | false breakoutが多い |
| `SIGNAL_RANGE_CHOP` | rangeで往復損が多い |
| `SIGNAL_TREND_AGAINST` | 強trendに逆らう |
| `SIGNAL_SCORE_UNDEFINED` | scoreの意味が不明 |

## BACKTEST

| code | meaning |
|---|---|
| `BACKTEST_LEAKAGE_RISK` | リークの疑い |
| `BACKTEST_COST_FRAGILE` | cost/slippage込みで消える |
| `BACKTEST_TRADE_COUNT_LOW` | 取引数が少なすぎる |
| `BACKTEST_PARAMETER_POINT_ONLY` | 最適点だけ良い |
| `BACKTEST_WALK_FORWARD_FAIL` | walk-forwardで残らない |

## PAPER

| code | meaning |
|---|---|
| `PAPER_FILL_GAP_UNEXPLAINED` | paperとbacktestの約定差が説明できない |
| `PAPER_PRICE_REF_UNCLEAR` | 価格参照が曖昧 |
| `PAPER_SKIP_NOT_LOGGED` | skip理由が記録されていない |
| `PAPER_TOO_SHORT` | 観測期間が短い |

## RISK

| code | meaning |
|---|---|
| `RISK_NO_STOP_CONDITION` | 停止条件がない |
| `RISK_TAIL_LOSS_HIGH` | tail lossが大きい |
| `RISK_EXPOSURE_UNBOUNDED` | exposure上限がない |
| `RISK_LIVE_REQUIRED_TOO_EARLY` | 早すぎるlive依存 |

## PROMOTION

| code | meaning |
|---|---|
| `PROMOTION_EVIDENCE_MISSING` | 次gateへ進める証跡がない |
| `PROMOTION_GATE_NOT_PASSED` | gate checklist未通過 |
| `PROMOTION_BLOCKER_OPEN` | promotion blockerが残っている |
| `PROMOTION_OWNERLESS` | owner/reviewerが不明 |

## OPS

| code | meaning |
|---|---|
| `OPS_BACKLOG_INCONSISTENT` | backlogとcandidate sheetの状態が矛盾 |
| `OPS_EVIDENCE_PATH_MISSING` | evidence pathが存在しない |
| `OPS_STATUS_INVALID` | workflowにないstatus |
| `OPS_REJECT_CODE_UNKNOWN` | taxonomyにないreject code |

## DUP

| code | meaning |
|---|---|
| `DUP_SIMILAR_SIGNAL` | 既存候補とほぼ同じ |
| `DUP_SAME_ARCHETYPE_INPUTS` | archetypeと入力が同一 |
| `DUP_SUPERSEDED` | より単純な候補で代替可能 |

## Usage

Reject recordには、最低1つのtaxonomy codeと短い証拠を残す。

```text
reject_reason_code: BACKTEST_COST_FRAGILE
evidence: cost x2でnet returnが負になり、DD改善も消えた
```
