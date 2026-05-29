# Signal Design Playbook

この付録は、純粋な「売買発生シグナル」を設計するための作業資料です。Crypto/DeFi固有の話ではなく、株式、ETF、先物、FX、暗号資産のどれにも使える形にします。

## 1. Signalの定義

Signalは「注文」ではありません。

```text
Signal = 特定時刻に、特定銘柄で、特定方向の候補が出たという記録
```

最低限の出力:

```text
ts_signal
symbol
side
timeframe
reason
score
invalidation_price
```

Signalが出た後に通るもの:

```text
Signal
  -> Participation Filter
  -> Position Sizer
  -> Risk Guard
  -> Execution Planner
```

## 2. Signalを作る前に固定すること

| item | 決める内容 |
|---|---|
| market | どの市場か |
| universe | どの銘柄群か |
| timeframe | 1m, 5m, 1h, 4h, 1dなど |
| holding horizon | どれくらい持つ想定か |
| side | long only, short only, both |
| baseline | 何と比較するか |
| invalidation | どこで仮説が壊れるか |
| no-trade condition | 入ってはいけない条件 |

## 3. Signal Archetypes

| archetype | 狙い | 典型入力 | よくある失敗 |
|---|---|---|---|
| Trend Continuation | 既存trendに乗る | MA slope, breakout, ADX | 遅れて高値掴み |
| Pullback Resume | trend中の押し目再開 | MA, swing, short momentum | レンジで往復ビンタ |
| Breakout | range抜け | high/low, volatility compression | false breakout |
| Mean Reversion | 行き過ぎ修正 | z-score, RSI, band | trendに逆張り |
| Volatility Expansion | 静から動への変化 | range, ATR, volume | event gapで約定悪化 |
| Regime Shift | 環境変化の検出 | vol, correlation, slope | signalとregimeを混同 |
| Cross-asset Lead Lag | 先行系列を見る | related asset returns | timestampずれ/リーク |
| Event Reaction | event後の反応を見る | event time, surprise, price reaction | event前情報の混入 |

## 4. Signal Output Contract

```csv
ts_signal,symbol,side,timeframe,reason,score,invalidation_price
2026-01-01T00:00:00+00:00,QQQ,long,4h,trend_pullback_resume,0.42,99.20
```

`score` は確信度ではなく、候補の優先度です。scoreが高いからサイズを大きくする、とはしない。

## 5. Good Signalの条件

- 発火理由が1文で説明できる。
- 発火時点で使えるデータだけで作られている。
- invalidation priceまたはinvalidation conditionがある。
- baselineとの差分が小さい。
- no-trade conditionがある。
- signal後の逆行幅を測れる。
- skipされたsignalも記録できる。

## 6. Bad Signalの典型

| bad signal | 問題 |
|---|---|
| `LLMが上がると言った` | 再現性と検証可能性がない |
| `score > 0.8なら買い` | scoreの意味と損失上限がない |
| `ニュースが良いから買い` | event時刻、反応済み価格、約定可能性が曖昧 |
| `高騰しているから買い` | trend continuationとpanic chaseが混ざる |
| `下がりすぎだから買い` | mean reversionと落ちるナイフが混ざる |
| `複数指標が一致したから買い` | 相関した指標を重複カウントしている |

## 7. Signal Review Questions

1. そのsignalは何と比べて優れている想定か。
2. signal発火時点で、そのデータは本当に利用可能か。
3. signalが外れた時、何をもって外れとするか。
4. entry直後の最大逆行幅を見るか。
5. signalが出たが入らなかったケースを保存するか。
6. scoreは方向、品質、優先度のどれを表すか。
7. signalはfilterなしでも意味があるか、filter込みで初めて意味があるか。

## 8. First Implementation Target

最初に作るなら、次のような小さいsignalがよい。

```text
Trend Pullback Resume

precondition:
  data_status == valid
  regime == trend

long:
  close > sma_50
  sma_50_slope > 0
  abs(distance_to_sma20_pct) <= 0.01
  short_momentum_turns_up == true

output:
  side = long
  timeframe = 4h
  reason = trend_pullback_resume
  invalidation_price = recent_swing_low
```

これは勝てる戦略の主張ではない。検証しやすい最小シグナルの例です。
