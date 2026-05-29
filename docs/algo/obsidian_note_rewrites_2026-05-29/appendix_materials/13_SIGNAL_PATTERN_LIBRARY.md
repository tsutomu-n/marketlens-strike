# Signal Pattern Library

売買発生シグナルの候補パターン集です。各パターンは完成戦略ではなく、検証するための候補です。

## 1. Trend Continuation

| item | content |
|---|---|
| 仮説 | trendが成立している時、短期ノイズ後に同方向へ続く |
| inputs | MA slope, higher high/low, ADX, volatility |
| long trigger | close > long MA and short momentum turns up |
| invalidation | swing low割れ |
| no-trade | range, panic, wide spread |
| baseline | MA crossover, buy-and-hold |
| reject | rangeで損失が大きい、cost込みで消える |

## 2. Pullback Resume

| item | content |
|---|---|
| 仮説 | 上昇trend中の浅い押しは再上昇候補になる |
| inputs | MA20, MA50, distance to MA, swing low |
| trigger | price near MA20 and short momentum recovers |
| invalidation | pullback low割れ |
| no-trade | MA50 slope <= 0 |
| baseline | trend中に常時long |
| reject | entry直後の逆行がbaselineより大きい |

## 3. Breakout With Retest

| item | content |
|---|---|
| 仮説 | range上抜け後のretest成功は継続しやすい |
| inputs | range high/low, volume, volatility compression |
| trigger | breakout -> retest holds -> momentum resumes |
| invalidation | range内へ戻る |
| no-trade | breakout candleだけで即entry |
| baseline | simple breakout |
| reject | false breakout率が下がらない |

## 4. Volatility Compression Expansion

| item | content |
|---|---|
| 仮説 | 低volatility後の拡大は方向性が出やすい |
| inputs | ATR percentile, band width, volume |
| trigger | compression then range break |
| invalidation | range内へ戻る |
| no-trade | event gap直後 |
| baseline | Donchian breakout |
| reject | slippage込みで期待値が消える |

## 5. Mean Reversion To Fair Value

| item | content |
|---|---|
| 仮説 | range regimeでは行き過ぎが戻る |
| inputs | z-score, band, realized vol, regime |
| trigger | z-score extreme and regime == range |
| invalidation | trend regimeへ移行 |
| no-trade | strong trend, panic |
| baseline | simple RSI |
| reject | trend日に大損する |

## 6. Regime Filtered Signal

| item | content |
|---|---|
| 仮説 | 同じsignalでもregimeで期待値が変わる |
| inputs | base signal, regime, volatility, spread |
| trigger | base signal and allowed regime |
| invalidation | regime changes to panic/unknown |
| no-trade | unknown regime |
| baseline | base signal without regime filter |
| reject | skipした取引の方が良い |

## 7. Cross-asset Confirmation

| item | content |
|---|---|
| 仮説 | 関連資産の動きがtargetのsignal品質を補助する |
| inputs | target return, related asset return, timestamp aligned data |
| trigger | target signal and related confirmation |
| invalidation | related move reverses |
| no-trade | timestamps not aligned |
| baseline | target-only signal |
| reject | confirmationが遅すぎる、またはリーク |

## 8. Signal Selection Rule

最初に選ぶべきもの:

```text
simple
explainable
few inputs
clear invalidation
baseline exists
can be paper observed
```

後回し:

```text
LLM-only signal
multi-model ensemble
reinforcement learning
complex portfolio optimization
execution-speed edge
```
