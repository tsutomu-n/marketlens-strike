<!--
作成日: 2026-05-29_21:49 JST
更新日: 2026-06-05_08:11 JST
-->

# Signal Review Scorecard

シグナル候補を同じ物差しで評価するための資料です。売買発生シグナルだけに焦点を当てます。

## 1. Signal Intake Template

```md
# Signal Candidate: <name>

- one sentence:
- archetype: trend | pullback | breakout | mean reversion | volatility | regime | cross-asset | event
- symbol universe:
- timeframe:
- side:
- required data:
- trigger:
- invalidation:
- no-trade conditions:
- baseline:
- expected failure:
```

## 2. Pre-backtest Score

| item | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| clarity | 説明不能 | 曖昧 | 条件はある | 1文で明確 |
| data availability | 取れない | liveのみ | historyあり | history/live両方 |
| timing correctness | future混入 | 不明 | 一部確認 | observed_at明確 |
| invalidation | なし | 曖昧 | 条件あり | price/condition明確 |
| baseline | なし | 弱い | あり | 公平で単純 |
| simplicity | 複雑 | 指標過多 | 中程度 | 小さい差分 |

優先:

- 14点以上: 検証へ進める。
- 10-13点: 条件を絞ってから検証。
- 9点以下: 保留または捨てる。

## 3. Backtest Review

| metric | baseline | signal | pass/fail |
|---|---:|---:|---|
| trade count | | | |
| net return after cost | | | |
| max drawdown | | | |
| average adverse excursion | | | |
| worst trade | | | |
| profit factor | | | |
| turnover | | | |
| cost x2 result | | | |
| slippage x2 result | | | |

特に見るもの:

- entry直後の逆行が減っているか。
- signal後の期待値がcost後で残るか。
- trade countが少なすぎないか。
- DD改善だけで期待値を殺していないか。

## 4. Signal Failure Labels

失敗したsignalを分類する。

| label | meaning |
|---|---|
| `late_entry` | signalが遅く、すでに伸び切っていた |
| `false_breakout` | breakoutが続かなかった |
| `range_chop` | rangeで往復損 |
| `trend_against` | 強trendに逆張りした |
| `wide_spread` | signalは良いが約定条件が悪い |
| `stale_data` | data freshness問題 |
| `event_gap` | eventで価格が飛んだ |
| `invalidation_missing` | 失敗条件が未定義 |

## 5. Continue / Reject Decision

Continue:

```text
baselineよりcost後改善
entry直後逆行が減る
walk-forwardで改善方向が残る
invalidationが機能する
paperで価格差が説明できる
```

Reject:

```text
cost込みで消える
skip/filter前提でしか成り立たないのにskip記録がない
invalidationがない
最適parameter一点だけ良い
trade countが少なすぎる
```
