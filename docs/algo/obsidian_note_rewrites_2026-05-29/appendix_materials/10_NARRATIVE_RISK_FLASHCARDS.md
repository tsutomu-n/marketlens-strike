# Narrative Risk Flashcards

理想的ナラティブを見つけた時に、実装可能な検査へ変換するためのカードです。

## Card 1: AIなら勝てる

| front | back |
|---|---|
| AIなら高精度に予測できる | accuracyではなくcost後PnL、DD、turnover、walk-forwardで見る |
| 修正 | MLは最初から方向予測の主役にせず、filter/risk/anomaly補助に使う |

## Card 2: Bot化すれば優位性

| front | back |
|---|---|
| 自動化すれば機会を逃さない | 自動化は損失、重複注文、stale data発注も自動化する |
| 修正 | read-only -> paper -> canaryの順にする |

## Card 3: 低遅延なら勝てる

| front | back |
|---|---|
| Jitoや高速経路で有利 | tip、失敗、slot境界、landing未保証、競争がある |
| 修正 | execution quality observationとして比較する |

## Card 4: Backtestが良い

| front | back |
|---|---|
| backtestのequity curveが綺麗 | 約定、cost、leakage、parameter overfitが未確認 |
| 修正 | cost x2、slippage x2、walk-forward、paper gapを見る |

## Card 5: 勝率が高い

| front | back |
|---|---|
| 勝率が高いから安全 | tail lossや損益比で負ける |
| 修正 | worst trade、CVaR、loss streak、DDを見る |

## Card 6: Tokenを早く買えばよい

| front | back |
|---|---|
| 新規tokenを早く買えばedge | 売れない、凍結、mint、holder集中、LP薄い可能性 |
| 修正 | token safetyとsellability simulationを先に置く |

## Card 7: パラメータ最適化で改善

| front | back |
|---|---|
| 最適値で良い結果 | 一点最適は過剰最適化の可能性 |
| 修正 | parameter neighborhoodとfold別安定性を見る |

## Card 8: 高速処理で品質が上がる

| front | back |
|---|---|
| Polars/VectorBTで高速化すれば研究が進む | 速度は正しさではない |
| 修正 | 小データ期待値、時刻順、join、rolling、null処理を検査する |
