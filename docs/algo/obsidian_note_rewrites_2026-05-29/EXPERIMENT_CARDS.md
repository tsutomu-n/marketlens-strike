# Experiment Cards

再構成ノートを読んだ後、実際に戦略を考えるための実験カードです。売買実装ではなく、仮説検証の順番です。

## E1. Trend Baseline

- 元ノート: `0212-Trend-Bot`, `戦略2`, `戦略5`
- 仮説: 高流動性ペアでは、単純トレンドフォローにレジーム停止とExit改善を足すとDDが下がる。
- データ: BTC/ETH、現物またはperp、1h/4h、手数料込み。
- 比較: MA cross, Donchian breakout, AlphaTrend相当。
- 合格: cost 2倍、slippage 2倍でも期待値が残る。
- 捨て: レンジ損失が大トレンド利益を食う。

## E2. Volatility Sizing

- 元ノート: `戦略1`, `Adaptive Alpha`
- 仮説: vol target/ATR sizingは総利益よりDDと破綻確率を改善する。
- データ: E1と同じ。
- 比較: fixed size vs ATR size vs realized volatility target。
- 合格: 利益が多少落ちてもDD、連敗時損失、tail lossが改善。
- 捨て: high-vol局面でサイズ縮小が遅れる。

## E3. Order Book Participation Filter

- 元ノート: `Order-Book`, `PyBotters`, `cryptofetch`
- 仮説: 板情報は方向予測より、約定コスト削減に使う方が有効。
- データ: top-of-book、depth、spread、trade prints、約定シミュレーション。
- 比較: シグナル全採用 vs spread/depth/imbalance filter。
- 合格: 実現slippage、約定失敗率、悪い時間帯の損失が下がる。
- 捨て: 板条件が短寿命で再現できない。

## E4. On-chain Regime Filter

- 元ノート: `戦略3`
- 仮説: オンチェーン指標は短期予測ではなく、中期リスク縮小に効く。
- データ: 日次オンチェーン指標、価格、funding、open interest。
- 比較: 価格only vs 価格 + 1指標ずつ。
- 合格: 未使用期間でDDまたは過熱局面の損失が下がる。
- 捨て: データ遅延/改訂を入れると効果が消える。

## E5. LightGBM Participation Model

- 元ノート: `LightGBM`, `Adaptive Alpha`
- 仮説: LightGBMは価格方向ではなく、取引する/しないのフィルタとして使うと有効な場合がある。
- データ: E1特徴量 + E3/E4の一部。
- 比較: rule baseline, logistic regression, LightGBM。
- 合格: walk-forwardでcost込み期待値が改善し、重要特徴量が安定。
- 捨て: AUCは高いが売買変換で消える。

## E6. Backtest Integrity

- 元ノート: `VectorBT`, `Backtest Trade`, `バックテストについて`, `Polars`
- 仮説: 結果の良さより、再現性とリーク排除が先。
- データ: 小さいfixtureと実データの両方。
- 比較: pandas vs polars、vectorized vs event-like。
- 合格: 小データで特徴量と売買結果が完全一致。
- 捨て: join/rolling/asofの時刻意味を説明できない。

## E7. Token Safety Observer

- 元ノート: `SOLANA`, `Solanaトレーディングボット`
- 仮説: 未知tokenを買う前に、危険tokenを除外する観測器が必要。
- データ: token metadata、mint/freeze authority、LP、holder、transfer fee、価格推移。
- 比較: フィルタなし候補 vs safety filter候補。
- 合格: 後から見て危険だったtokenを高率で除外できる。
- 捨て: 売却可能性を事前に確認できない。

## E8. Jito Execution Observation

- 元ノート: `JitoとSolana`
- 仮説: Jitoは収益源ではなく、実行品質を測る対象。
- データ: simulation、landed/not landed、latency、tip、failure reason。
- 比較: standard tx vs Jito route。
- 合格: tip込みでもslippageまたは失敗率が改善。
- 捨て: tip/失敗/インフラ費用で期待値が消える。

## E9. News Event Study

- 元ノート: `自動化された暗号通貨ニュースで稼ぐ方法`
- 仮説: ニュース自動化は収益ではなくイベント観測に使える。
- データ: event timestamp、source、first seen、price/volume/spread before-after。
- 比較: event type別のforward return分布。
- 合格: 十分なサンプルで、見送り/観測に使える分類が作れる。
- 捨て: 紹介収益や記事生成が目的化する。

## E10. Multi-Asset Risk Allocation

- 元ノート: `戦略4`, `ポートフォリオ最適化`
- 仮説: 複雑な最適化より、上限ルールとvol targetが先。
- データ: BTC/ETHから始め、大型銘柄を段階追加。
- 比較: equal weight, vol target, risk cap, simple risk parity。
- 合格: 銘柄追加でDDが悪化せず、急落時の同時損失が制限される。
- 捨て: 平時だけ分散し、急落時に相関が1へ近づく。

