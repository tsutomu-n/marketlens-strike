<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Experiment Cards

再構成ノートを読んだ後、実際に戦略を考えるための実験カードです。主軸はCrypto/DeFi固有の安全確認ではなく、純粋な戦略・売買発生シグナルです。

読み方:

1. まず `S1-S8` のシグナル実験から見る。
2. 次に `R1-R4` のリスク、検証、モデル補助を見る。
3. Crypto/DeFi固有のものは `X1-X3` の特殊ケースとして後段で扱う。

## S1. Trend Continuation Signal

- archetype: trend continuation
- 元ノート: `0212-Trend-Bot`, `戦略2`, `戦略5`
- 仮説: trend regime中だけ同方向signalを採用すると、常時trend followよりレンジ損失が下がる。
- データ: 高流動性銘柄のOHLCV、spread、1h/4h。
- trigger: close > long MA、MA slope > 0、短期momentum再上昇。
- invalidation: swing low割れ、またはMA slope反転。
- baseline: MA cross, Donchian breakout, buy-and-hold。
- 合格: cost 2倍、slippage 2倍でも期待値が残り、DDがbaseline以下。
- 捨て: rangeでの損失がtrend利益を食う。

## S2. Pullback Resume Signal

- archetype: pullback
- 元ノート: `Trend-Bot`, `戦略5`
- 仮説: 上昇trend中の浅い押しからの再上昇だけを拾うと、entry直後の逆行が減る。
- データ: OHLCV、MA20/MA50、swing high/low、短期momentum。
- trigger: price near MA20、MA50 slope > 0、short momentum turns up。
- invalidation: pullback low割れ。
- baseline: trend中に常時long、単純MA20反発。
- 合格: average adverse excursionとmax drawdownがbaselineより改善。
- 捨て: signalが遅く、高値掴みが増える。

## S3. Breakout With Retest Signal

- archetype: breakout
- 元ノート: `Trend-Bot`, `Backtest Trade`
- 仮説: range上抜け直後ではなく、retest成功後に入るとfalse breakoutが減る。
- データ: OHLCV、range high/low、volume、volatility compression。
- trigger: breakout後、旧range上限を維持し、momentumが再開。
- invalidation: range内へ戻る。
- baseline: simple breakout。
- 合格: false breakout率とentry後逆行が下がる。
- 捨て: retest待ちで期待値の大部分を取り逃がす。

## S4. Volatility Compression Expansion Signal

- archetype: volatility expansion
- 元ノート: `戦略1`, `VectorBT`, `バックテストについて`
- 仮説: 低volatility後のrange breakは、通常時breakoutより期待値が残りやすい。
- データ: ATR percentile、band width、range、volume。
- trigger: volatility compression後のrange break。
- invalidation: range内へ戻る。
- baseline: Donchian breakout。
- 合格: cost/slippage込みでsimple breakoutより安定。
- 捨て: event gapや広いspreadで約定前提が崩れる。

## S5. Mean Reversion Signal

- archetype: mean reversion
- 元ノート: `Adaptive Alpha`, `バックテストについて`
- 仮説: range regimeでは行き過ぎからfair valueへ戻る動きが取れる。
- データ: z-score、band、realized volatility、regime。
- trigger: regime == range、z-score extreme、volatilityがpanicでない。
- invalidation: trend regimeへ移行、またはband外で加速。
- baseline: simple RSI。
- 合格: trend日を除外した時だけ期待値が残る。
- 捨て: trend日に大損して総合期待値が消える。

## S6. Regime-filtered Signal

- archetype: regime filter
- 元ノート: `戦略2`, `RiskGuard`
- 仮説: 同じsignalでも、trend/range/panic/unknownで期待値が変わる。
- データ: base signal、realized vol、trend slope、spread。
- trigger: base signal and allowed regime。
- invalidation: regimeがpanicまたはunknownへ変わる。
- baseline: base signal without regime filter。
- 合格: skipした取引の仮想PnLが悪く、通した取引のtail lossが下がる。
- 捨て: skip率が高いだけで、通した取引の期待値が改善しない。

## S7. Cross-asset Confirmation Signal

- archetype: cross-asset confirmation
- 元ノート: `戦略4`, `ポートフォリオ最適化`
- 仮説: 関連資産の方向やrisk-on/offが、target signalの品質を補助する。
- データ: target OHLCV、related asset return、timestamp aligned features。
- trigger: target signal and related asset confirmation。
- invalidation: related confirmationが反転。
- baseline: target-only signal。
- 合格: timestampを正しく揃えてもsignal品質が改善する。
- 捨て: related dataが遅すぎる、または未来情報が混ざる。

## S8. Event Reaction Signal

- archetype: event reaction
- 元ノート: `自動化された暗号通貨ニュースで稼ぐ方法`
- 仮説: ニュースやイベントは、即売買ではなく反応後の継続/反転分類に使える。
- データ: event timestamp、first seen、source、price/volume/spread before-after。
- trigger: event後の価格反応とvolume expansion。
- invalidation: event前から価格が織り込み済み。
- baseline: eventなし同時刻分布。
- 合格: 十分なサンプルで、見送り/観測/候補分類が作れる。
- 捨て: 紹介収益や記事生成が目的化する。

## R1. Volatility Sizing

- role: position sizing
- 元ノート: `戦略1`, `Adaptive Alpha`
- 仮説: vol target/ATR sizingは総利益よりDDと破綻確率を改善する。
- 比較: fixed size vs ATR size vs realized volatility target。
- 合格: 利益が多少落ちてもDD、連敗時損失、tail lossが改善。
- 捨て: high-vol局面でサイズ縮小が遅れる。

## R2. Order Book Participation Filter

- role: participation filter
- 元ノート: `Order-Book`, `PyBotters`, `cryptofetch`
- 仮説: 板情報は方向予測より、約定コスト削減に使う方が有効。
- データ: top-of-book、depth、spread、trade prints、約定シミュレーション。
- 比較: シグナル全採用 vs spread/depth/imbalance filter。
- 合格: 実現slippage、約定失敗率、悪い時間帯の損失が下がる。
- 捨て: 板条件が短寿命で再現できない。

## R3. LightGBM Participation Model

- role: model-assisted filter
- 元ノート: `LightGBM`, `Adaptive Alpha`
- 仮説: LightGBMは価格方向ではなく、取引する/しないのフィルタとして使うと有効な場合がある。
- データ: signal outcome、volatility、spread、regime、time-of-day。
- 比較: rule baseline, logistic regression, LightGBM。
- 合格: walk-forwardでcost込み期待値が改善し、重要特徴量が安定。
- 捨て: AUCは高いが売買変換で消える。

## R4. Backtest Integrity

- role: evaluation harness
- 元ノート: `VectorBT`, `Backtest Trade`, `バックテストについて`, `Polars`
- 仮説: 結果の良さより、再現性とリーク排除が先。
- データ: 小さいfixtureと実データの両方。
- 比較: pandas vs polars、vectorized vs event-like。
- 合格: 小データで特徴量と売買結果が完全一致。
- 捨て: join/rolling/asofの時刻意味を説明できない。

## X1. On-chain Regime Filter

- type: Crypto/DeFi specific
- 元ノート: `戦略3`
- 仮説: オンチェーン指標は短期予測ではなく、中期リスク縮小に効く。
- データ: 日次オンチェーン指標、価格、funding、open interest。
- 比較: 価格only vs 価格 + 1指標ずつ。
- 合格: 未使用期間でDDまたは過熱局面の損失が下がる。
- 捨て: データ遅延/改訂を入れると効果が消える。

## X2. Token Safety Observer

- type: Crypto/DeFi specific
- 元ノート: `SOLANA`, `Solanaトレーディングボット`
- 仮説: 未知tokenを買う前に、危険tokenを除外する観測器が必要。
- データ: token metadata、mint/freeze authority、LP、holder、transfer fee、価格推移。
- 比較: フィルタなし候補 vs safety filter候補。
- 合格: 後から見て危険だったtokenを高率で除外できる。
- 捨て: 売却可能性を事前に確認できない。

## X3. Jito Execution Observation

- type: Crypto/DeFi specific
- 元ノート: `JitoとSolana`
- 仮説: Jitoは収益源ではなく、実行品質を測る対象。
- データ: simulation、landed/not landed、latency、tip、failure reason。
- 比較: standard tx vs Jito route。
- 合格: tip込みでもslippageまたは失敗率が改善。
- 捨て: tip/失敗/インフラ費用で期待値が消える。
