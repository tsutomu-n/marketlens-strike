# Component Cards

各部品を、入力、出力、捨て条件、誤用で固定するためのカードです。

## Universe Selector

| item | content |
|---|---|
| 役割 | 対象銘柄を選ぶ |
| 入力 | registry, quote coverage, spread, depth, session |
| 出力 | `selected`, `rejected(reason)` |
| 捨て条件 | データ不足、取引不能、流動性不足、履歴が短い |
| 誤用 | 後から生き残った銘柄だけを使う |

## Data Quality Gate

| item | content |
|---|---|
| 役割 | 使ってよいデータか判定する |
| 入力 | timestamp, price columns, source timestamp, missing/null, source confidence |
| 出力 | `valid`, `stale`, `missing`, `untrusted` |
| 捨て条件 | oracle/source時刻欠落、価格欠損、異常な重複、timezone不明 |
| 誤用 | 欠損をforward fillして売買可能データにする |

## Feature Factory

| item | content |
|---|---|
| 役割 | signal/riskに使う特徴量を作る |
| 入力 | OHLCV, quote, order book, event calendar, cross-asset series |
| 出力 | feature frame |
| 捨て条件 | feature timeがdecision timeより後、rolling計算の未来参照 |
| 誤用 | 高速処理できることを正しさと混同する |

## Regime Detector

| item | content |
|---|---|
| 役割 | 戦略を通常稼働/縮小/停止する環境を決める |
| 入力 | volatility, spread, depth, trend slope, event flags |
| 出力 | `trend`, `range`, `panic`, `thin_liquidity`, `unknown` |
| 捨て条件 | unknownをnormal扱いしている |
| 誤用 | regimeを方向予測として扱う |

## Signal Generator

| item | content |
|---|---|
| 役割 | entry候補を出す |
| 入力 | feature frame, regime, data status |
| 出力 | `ts_signal`, `symbol`, `side`, `timeframe`, `reason`, `score` |
| 捨て条件 | invalidationなし、reasonなし、data_statusなし |
| 誤用 | signalを注文命令として扱う |

## Participation Filter

| item | content |
|---|---|
| 役割 | 良さそうなsignalでも入らない条件を作る |
| 入力 | spread, slippage estimate, liquidity, regime, event, data status |
| 出力 | `allow`, `skip(reason)` |
| 捨て条件 | skipした取引の仮想PnLを記録していない |
| 誤用 | skip率が高いだけで有効だと判断する |

## Position Sizer

| item | content |
|---|---|
| 役割 | 損失上限から数量を決める |
| 入力 | equity, risk_per_trade, entry_ref, invalidation_price, liquidity cap |
| 出力 | `quantity`, `risk_amount`, `size_reason` |
| 捨て条件 | stop distanceがない、流動性capがない |
| 誤用 | ML scoreが高い時に安易にサイズを増やす |

## Exit Module

| item | content |
|---|---|
| 役割 | いつ閉じるかを決める |
| 入力 | position, price, invalidation, trail, max holding, risk state |
| 出力 | `hold`, `exit(reason)` |
| 捨て条件 | entryだけありexitがない |
| 誤用 | stop lossで損失が必ず限定できると考える |

## Execution Planner

| item | content |
|---|---|
| 役割 | 戦略判断を注文計画へ変換する |
| 入力 | strategy decision, risk decision, sizing, price reference |
| 出力 | `ExecutionPlan(action, symbol, quantity, notes)` |
| 捨て条件 | stale data時にenterが出る |
| 誤用 | adapterに戦略判断を混ぜる |

## Evaluation Harness

| item | content |
|---|---|
| 役割 | 候補を採用/棄却する |
| 入力 | trades, decision log, cost model, baseline |
| 出力 | scorecard, reject/continue |
| 捨て条件 | in-sampleだけ、gross returnだけ |
| 誤用 | 最良結果を代表値として扱う |
