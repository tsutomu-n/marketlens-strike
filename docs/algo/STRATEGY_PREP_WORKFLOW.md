# Strategy Preparation Workflow

目的: 戦略アイデアを実装に進める前に、必要な材料、データ、仮説、検証条件を揃える。

## 0. 準備の完了条件

次が揃うまで、戦略実装へ進まない。

- 仮説が1文で書けている。
- 対象市場、対象銘柄、時間軸が明確。
- 必要データと取得方法が明確。
- 特徴量、ラベル、baselineが定義済み。
- 使う部品が [STRATEGY_PARTS_CATALOG.md](STRATEGY_PARTS_CATALOG.md) から選ばれている。
- 捨て条件が先に決まっている。
- secret、外部副作用、攻撃的用途がない。

## 1. Hypothesis Intake

最初に書くもの:

- 仮説名。
- 1文の主張。
- どの非効率を狙うか。
- なぜ今も残る可能性があるか。
- 反証されたらどう見えるか。

例:

```text
仮説: 長期トレンド方向に沿った押し目だけを、板の厚みが戻った時に入ると、単純な押し目買いよりentry直後の逆行が減る。
```

注意:

- 「勝率が高そう」は仮説ではない。
- 「動画で勝っていた」は根拠ではない。
- 「どの条件なら負けるか」まで書けない仮説は保留する。

## 2. Market And Data Definition

決めるもの:

- market: CEX, DEX, Solana, Pump.fun, stock, FXなど。
- universe: 固定銘柄、流動性上位、イベント発生銘柄、テーマ銘柄。
- timeframe: 1m, 5m, 15m, 1h, 4h, 1dなど。
- data source: OHLCV, order book, WebSocket, on-chain, news, social。
- data availability: backtestで取れるか、paper/liveでしか取れないか。
- data risk: 欠損、遅延、API制限、仕様変更、secret requirement。

最低限のデータ表:

| field | meaning | source | available in backtest | leak risk | notes |
| --- | --- | --- | --- | --- | --- |
| timestamp | event or bar time | collector | yes | high if corrected later | timezone固定 |
| symbol/token | target id | exchange/API | yes | low | chain idも必要 |
| price/ohlcv | price series | exchange/API | yes | medium | 確定足だけ使う |
| liquidity/spread | tradability | order book/DEX | partial | medium | liveとの差に注意 |
| authority/risk | token safety | chain/API | partial | low | 取れない時はsafe扱いしない |

## 3. Label And Target Definition

モデルやスコアを使う場合、目的変数を先に固定する。

候補:

- future return over N bars。
- max favorable excursion。
- max adverse excursion。
- trend continuation probability。
- volatility regime。
- unsafe token event。
- slippage bucket。

避けるもの:

- 後から都合よく変えるラベル。
- 約定できない価格を使うラベル。
- 手数料前のリターンだけを見るラベル。
- 未来の高値安値を使った過度に楽観的なラベル。

## 4. Baseline First

新しい部品を評価する前にbaselineを作る。

baseline例:

- Buy and hold。
- 常時trend pullback。
- 板フィルタなし。
- risk guardなし。
- fixed size。
- random entry with same trade count。

比較の原則:

- baselineより複雑な案は、複雑さに見合う改善が必要。
- returnだけでなく、MDD、CVaR、turnover、trade count、slippage sensitivityを見る。

## 5. Parts Selection

戦略候補は次の順に組み立てる。

1. Universe Selector
2. Data Collector
3. Feature Factory
4. Regime Detector
5. Signal Generator
6. Participation Filter
7. Position Sizer
8. Exit Module
9. Risk Guard
10. Evaluation Harness
11. Monitoring Layer

Meme/Solana系では、`Signal Generator` より前に `Token Safety Filter` を入れる。

## 6. Experiment Pack

実験に進む前に、1候補ごとに次を揃える。

- hypothesis。
- dataset definition。
- feature list。
- label definition。
- baseline。
- candidate logic。
- cost/slippage assumptions。
- expected failure modes。
- stop conditions。
- acceptance threshold。
- source notes。

この形式は [EXPERIMENT_SCORECARD.md](EXPERIMENT_SCORECARD.md) を使う。

## 7. Prioritization

候補は次の順で優先する。

1. データが安全に取れる。
2. baseline比較がしやすい。
3. live実行なしでも検証できる。
4. secretや外部副作用がない。
5. 部品として他戦略へ再利用できる。
6. failure modeが明確。

低優先にするもの:

- 勝率や利益主張だけが根拠のもの。
- 実弾または秘密鍵がないと検証できないもの。
- 取得できないデータに依存するもの。
- 攻撃的、詐欺的、不正利用に近いもの。

## 8. Strategy Prep Backlog

まず作る候補:

1. `Trend + OrderBook Confirmation`
   - 理由: 比較対象が明確で、主要銘柄で検証しやすい。
2. `Regime + RiskGuard Trend System`
   - 理由: 売買ロジックを増やさず、DD改善に効く可能性がある。
3. `Pump.fun Event Watcher`
   - 理由: 売買せず観測でき、Meme系の誇張を検証可能なデータに変えられる。
4. `Solana Token Safety Gate`
   - 理由: 収益化より先に、参加してはいけない対象を落とせる。
5. `Feature Factory + Walk-Forward Gate`
   - 理由: 今後の全戦略に使い回せる検証基盤になる。

## 9. Do Not Start Yet

次は、準備段階では始めない。

- live trading。
- private keyを使うDEX execution。
- sniper誘引やrug設計。
- LLMの判断だけで売買。
- secretを含むノートの生コピー。
- 勝率主張だけに基づく実装。
