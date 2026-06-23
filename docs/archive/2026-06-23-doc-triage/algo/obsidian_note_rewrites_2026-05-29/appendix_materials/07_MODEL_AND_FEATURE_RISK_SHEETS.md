<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Model And Feature Risk Sheets

ML、時系列モデル、高速backtest、Polars feature処理を、理想的ナラティブではなく検査対象として扱うための資料です。

## 1. LightGBM Risk Sheet

| risk | 何が起きるか | 対策 |
|---|---|---|
| parameter alias | 古いメモの名前や別名を誤用する | 実装直前に公式Parametersを確認 |
| leaf-wise overfit | 木が深くなり過学習する | `num_leaves`, `max_depth`, `min_data_in_leaf` をセットで見る |
| accuracy trap | AUC/accuracyは良いが売買で負ける | cost後PnL、DD、turnoverで評価 |
| label leakage | future return情報がfeatureに混ざる | feature timeとlabel timeを分離 |
| unstable importance | foldごとに重要特徴量が変わる | walk-forward別のimportanceを比較 |

使い方:

- 最初から方向予測の主役にしない。
- まず `trade / skip` の補助filter、risk regime、volatility bucketに使う。
- logistic regressionやrule baselineより複雑にする価値があるかを見る。

## 2. Time-series Model Risk Sheet

| risk | 補正 |
|---|---|
| 予測値をそのまま売買にする | signal候補またはfeatureに留める |
| 多変量モデルの入力時点が揃っていない | observed_atを揃える |
| forecast residualに未来actualを使う | residualは過去確定後だけ使う |
| regime変化で壊れる | fold別、期間別に評価 |

## 3. Polars Feature Factory Risk Sheet

| risk | 例 | 対策 |
|---|---|---|
| sort忘れ | rolling結果が壊れる | symbol/timeでsort |
| join_asofの方向ミス | future eventを結合 | backward/strategyを明記 |
| timezone混在 | 日付境界がずれる | UTCに固定 |
| null処理 | 欠損を売買可能値にする | null rateを記録 |
| lazy planの見落とし | 意図しない計算順 | 小データ期待値テスト |

最低限のテスト:

```text
small fixture
expected feature values
no feature_time > decision_time
null/missing behavior
```

## 4. VectorBT Screening Risk Sheet

| risk | 補正 |
|---|---|
| vectorized resultを実約定と誤認 | 一次スクリーニングに限定 |
| candle priceで必ず約定 | spread/slippage/fill rateを別検査 |
| parameter gridから最良だけ採用 | neighborhoodとwalk-forwardを見る |
| portfolio constraintsなし | exposure, turnover, liquidity capを見る |

## 5. Model Adoption Gate

MLや高度モデルを採用する条件:

```text
rule baselineよりcost後で改善
walk-forwardで改善方向が残る
feature importanceが説明可能
parameter近傍で壊れない
paper observationで想定差が説明可能
```

不採用:

```text
in-sampleだけ良い
accuracyだけ良い
複雑さの理由が説明できない
liveで取得できないfeatureに依存
```
