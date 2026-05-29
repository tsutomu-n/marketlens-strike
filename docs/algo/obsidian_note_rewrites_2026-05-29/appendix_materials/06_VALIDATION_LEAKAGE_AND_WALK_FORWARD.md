# Validation, Leakage, Walk-forward

良く見える戦略候補を捨てるための資料です。

## 1. Leakage Examples

| pattern | 何が悪いか | 修正 |
|---|---|---|
| close前にその足のcloseを使う | decision時点で未確定 | 次足以降で使う |
| future high/lowでlabelを作り、その情報をfeatureへ混ぜる | 未来情報 | featureとlabel作成を分離 |
| 全期間で標準化してからsplit | test期間情報がtrainに入る | train期間だけでfit |
| rollingがsort前に走る | 時系列順が壊れる | symbol/timeでsortしてからrolling |
| on-chain値の確定後データを過去時点に使う | 後から分かった情報 | observed_atを持つ |

## 2. Time Split

悪い例:

```text
random split
```

金融時系列では、未来と過去が混ざるため避ける。

最低限:

```text
train: 2025-01-01..2025-06-30
gap:   2025-07-01..2025-07-07
test:  2025-07-08..2025-08-31
```

`gap` は、特徴量のlookbackや注文/約定遅延の混入を避けるために置く。

## 3. Walk-forward Template

| fold | train | gap | test | result | decision |
|---|---|---|---|---|---|
| 1 | Jan-Mar | 3 days | Apr | pending | pending |
| 2 | Feb-Apr | 3 days | May | pending | pending |
| 3 | Mar-May | 3 days | Jun | pending | pending |

見ること:

- 各foldで改善方向が同じか。
- 最良foldだけで判断していないか。
- parameterがfoldごとに飛んでいないか。

## 4. Cost And Slippage Stress

| stress | reason |
|---|---|
| fee x2 | 手数料見積もりが甘い可能性 |
| spread x2 | 平均spreadでは悪条件を見逃す |
| slippage x2 | 実約定はbacktestより悪化しやすい |
| fill rate down | 約定不能を無視しない |
| latency delay | signalからentryまでの劣化を見る |

採用不可:

```text
base caseのみ良い
cost x2で期待値が消える
slippage x2でDDが急増
```

## 5. Parameter Neighborhood

最適値だけを見るのではなく、近傍を見る。

| parameter | chosen | neighbors |
|---|---:|---|
| sma_short | 20 | 15, 18, 22, 25 |
| sma_long | 50 | 40, 45, 55, 60 |
| max_spread_bps | 8 | 5, 6, 10, 12 |

良い候補:

- 近傍でも改善方向が残る。
- 成績が一点に集中しない。
- trade countが極端に減らない。

## 6. Skip PnL Review

Participation Filterは、skipした取引も評価する。

| skip reason | skipped count | virtual pnl | interpretation |
|---|---:|---:|---|
| SPREAD_TOO_WIDE | 12 | -0.04 | filter useful |
| EVENT_BLACKOUT | 5 | 0.01 | maybe too strict |
| PANIC | 3 | -0.08 | filter useful |

filterなし成績だけでは判断しない。

## 7. Paper / Backtest Gap

| item | backtest assumption | paper observation | gap |
|---|---|---|---|
| entry price | mark price | observed executable price | pending |
| fill | always filled | sometimes no fill | pending |
| slippage | fixed bps | variable | pending |
| latency | zero | observed delay | pending |

gapが説明できない場合、liveへ進まない。
