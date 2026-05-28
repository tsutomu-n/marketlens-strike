# Obsidian Vault: Strategy Ideas for marketlens-strike

Source vault: `/home/tn/Docs/algo/obsidian-vault`

目的:
- ノート一覧を読むだけで終わらせず、`marketlens-strike` で試す候補戦略へ落とす。
- ここでは「優位性がありそうな完成戦略」ではなく、「実験する価値がある仮説」を並べる。
- 各案は `発想` `使うノート` `最初の実装イメージ` `最初の検証観点` の4点でまとめる。

前提:
- まずは research-first。即実弾ではなく、再現可能なバックテスト/リプレイで候補を削る。
- 予測モデルは売買判断の全部を持たせず、フィルタ、配分、停止条件に寄せる。
- 板情報は方向予測より、見送り判断と執行品質改善に使う。

## 1. Trend Filtered Pullback

- 発想:
  - 長期足で `trend/range` を判定し、トレンド時だけ短期押し目/戻りを取る。
  - 順張りの無駄撃ちを減らすことが目的。
- 使うノート:
  - `0212-Trend-Bot.md`
  - `0714-Adaptive-Alpha-Trendトレードプログラム.md`
  - `0721-RiskGuard Crypto Engine(RGCE).md`
- 最初の実装イメージ:
  - 4H: ADX, 200MA, MACD で稼働可否を決める。
  - 15m or 5m: RSI 押し目、BB タッチ、短期 MA 反転で入る。
  - 損切りは ATR ベース、利確は分割 + trailing。
- 最初の検証観点:
  - `全期間稼働` と `trend 時のみ稼働` で、取引回数、勝率、PF、MDD がどう変わるか。

## 2. Trend Plus Order Book Confirmation

- 発想:
  - 方向はテクニカル、タイミングは板。
  - ブレイク直後の飛びつきを減らし、板の偏りがある時だけエントリーする。
- 使うノート:
  - `0212-Trend-Bot.md`
  - `0714-トレード戦略-Order-Book.md`
  - `0722-PyBotters.md`
- 最初の実装イメージ:
  - 長期トレンド条件を満たしたら監視モードへ。
  - 短期では order book imbalance、bid/ask depth slope、直近の板吸収を見る。
  - 条件が弱いときは見送る。
- 最初の検証観点:
  - 板フィルタあり/なしで、約定後の adverse move、スリッページ、勝率が改善するか。

## 3. Regime Switcher

- 発想:
  - 市場を `trend` `range` `high-vol trend` `panic` などに分類し、使う戦略を切り替える。
  - 1本のロジックを万能化するより現実的。
- 使うノート:
  - `0721-LightGBM パラメータチューニング.md`
  - `0725-時系列-予測モデル.md`
  - `0711-IRIS金融.md`
  - `1221-テクニカルを超えて.md`
- 最初の実装イメージ:
  - 特徴量: ADX, realized vol, spread proxy, order book imbalance summary, volume spike。
  - ラベル: 未来 N 本の方向ではなく、次の期間が trend/range/high-vol のどれか。
  - 戦略選択器として使う。
- 最初の検証観点:
  - regime classifier を噛ませる前後で、戦略の MDD と trade frequency がどう変わるか。

## 4. Anomaly Skip Filter

- 発想:
  - シグナルを増やすのではなく、危ない局面を除外する。
  - とくに crypto では「やらないこと」の価値が大きい。
- 使うノート:
  - `0714-Adaptive-Alpha-Trendトレードプログラム.md`
  - `0721-RiskGuard Crypto Engine(RGCE).md`
  - `0906_モンテカルロ.md`
- 最初の実装イメージ:
  - Isolation Forest か単純な外れ値スコアで、急変・薄商い・異常スプレッドを検出。
  - 異常スコアが閾値超えなら新規停止。
- 最初の検証観点:
  - 異常フィルタ追加で tail loss が減るか。
  - 平均リターンは多少落ちても、CVaR と MDD が改善するか。

## 5. Breakout Retest With Liquidity

- 発想:
  - 高値/安値ブレイク自体ではなく、ブレイク後の retest 成功を狙う。
  - 板を使い、だましブレイクを落とす。
- 使うノート:
  - `0714-トレード戦略-Order-Book.md`
  - `0722-PyBotters.md`
  - `1031_Trading with polars.md`
- 最初の実装イメージ:
  - 過去 N 本高値更新を検知。
  - retest 時に bid/ask imbalance が継続、かつ出来高維持で入る。
  - stop は breakout level 割れ。
- 最初の検証観点:
  - 単純 breakout と比較して、whipsaw 回数と expectancy がどう変わるか。

## 6. Multi-Strategy Allocation

- 発想:
  - `順張り` `短期 mean reversion` `イベント監視` の複数戦略を持ち、配分を変える。
  - 単一戦略のドローダウンに依存しない。
- 使うノート:
  - `1114_ポートフォリオ最適化.md`
  - `0906_モンテカルロ.md`
  - `0721-RiskGuard Crypto Engine(RGCE).md`
- 最初の実装イメージ:
  - 各戦略を独立で評価し、rolling Sharpe, drawdown, correlation から capital allocation を決める。
  - 最小分散や max-sharpe をそのまま使うのでなく、上限制約付き配分にする。
- 最初の検証観点:
  - 単独戦略ベストより、合成戦略の equity curve が滑らかになるか。

## 7. Feature Factory Search

- 発想:
  - 指標を1個ずつ足すより、特徴量の束を作って当たり外れを探す。
  - 研究効率の改善が主目的。
- 使うノート:
  - `1031_Trading with polars.md`
  - `0721-LightGBM パラメータチューニング.md`
  - `0710-VectorBT.md`
- 最初の実装イメージ:
  - Polars で大量特徴量を一括生成。
  - LightGBM importance や permutation importance で候補を落とす。
  - vectorbt でルール化できるものだけ軽検証。
- 最初の検証観点:
  - 追加特徴量が out-of-sample で効くか。
  - importance が高くても実売買ルール化すると崩れないか。

## 8. GA Threshold Search

- 発想:
  - ルールの骨格は人間が決め、閾値だけ探索アルゴリズムに任せる。
  - 直感依存の閾値設定を減らす。
- 使うノート:
  - `0902-Genetic Alogo for Trading.md`
  - `0710-VectorBT.md`
  - `1117_バックテストについて.md`
- 最初の実装イメージ:
  - 最適化対象: ADX threshold、ATR multiplier、take-profit split、time stop、board imbalance threshold。
  - 適合度: CAGR 単体ではなく `Sharpe - penalty(MDD, turnover, instability)`。
- 最初の検証観点:
  - in-sample だけ良い閾値になっていないか。
  - fold 間のばらつきと sensitivity が小さいか。

## 9. News Activated Watchlist

- 発想:
  - ニュースを売買シグナル化するのではなく、「今日は何を見るべきか」を決める。
  - 平時は待機、イベント日は監視強化。
- 使うノート:
  - `1107_自動化された暗号通貨ニュースで稼ぐ方法.md`
  - `0702-cryptofetch.md`
  - `1103_Crawl4AI LLM Friendly Web Crawler & Scrapper.md`
  - `1129-Firecrawl.md`
- 最初の実装イメージ:
  - ニュース/アナウンス/オンチェーン話題量で銘柄ごとの event score を作る。
  - score 上位だけ intraday strategy を稼働。
- 最初の検証観点:
  - 全銘柄常時監視に対して、watchlist 制限で hit rate と capital efficiency が上がるか。

## 10. Exchange Specific Execution Edge

- 発想:
  - 汎用戦略より、Bybit/Solana/Hyperliquid の癖に合わせた執行最適化を狙う。
  - 方向優位が小さくても execution edge で残せる可能性がある。
- 使うノート:
  - `0722-PyBotters.md`
  - `1129-Solanaトレーディングボット.md`
  - `1202-JitoとSolana.md`
  - `0905-M15戦略 for Hyperliquid Prep.md`
- 最初の実装イメージ:
  - venue ごとに order type、post-only/passive 比率、キャンセル頻度、時間帯別 fill quality を分ける。
  - 戦略ロジックと venue adapter を分離する。
- 最初の検証観点:
  - 同じシグナルでも venue 別に fill quality と realized PnL が違うか。

## 11. Drawdown Aware Position Sizing

- 発想:
  - エントリー改善より、連敗局面で size を落とす。
  - 資金曲線の破壊を防ぐ方が先。
- 使うノート:
  - `0721-RiskGuard Crypto Engine(RGCE).md`
  - `1114_ポートフォリオ最適化.md`
  - `0906_モンテカルロ.md`
- 最初の実装イメージ:
  - rolling drawdown、realized vol、hit rate 低下で size を自動縮小。
  - fixed fractional と Kelly 派生の中間を狙う。
- 最初の検証観点:
  - CAGR は落ちても MDD と recovery time が改善するか。

## 12. Research Stack First

- 発想:
  - 戦略アイデア不足より、検証スタック不足で止まるリスクが高い。
  - 先に試行速度を上げる。
- 使うノート:
  - `1117_バックテストについて.md`
  - `0710-VectorBT.md`
  - `1031_Trading with polars.md`
- 最初の実装イメージ:
  - `Polars -> feature generation`
  - `VectorBT -> 仮説の粗選別`
  - `より重い backtester -> 生き残り候補だけ移管`
- 最初の検証観点:
  - 1週間で回せる仮説数が何倍になるか。
  - research loop のボトルネックが計算か、データ整形か、可視化かを把握する。

## まず優先して試すなら

- 優先1: `Trend Filtered Pullback`
  - 理由: シンプルで、既存ノートの材料が最も揃っている。
- 優先2: `Trend Plus Order Book Confirmation`
  - 理由: 差別化しやすく、execution 改善が狙える。
- 優先3: `Anomaly Skip Filter`
  - 理由: 攻めるより守る方が先に効く可能性が高い。
- 優先4: `Research Stack First`
  - 理由: 以降の全戦略の試行回数を増やせる。

## 現時点の結論

- 一番筋が良いのは、`長期トレンドフィルタ + 短期エントリー + リスクガード + 板確認` の4層構造。
- ML は主役ではなく、`regime判定` `異常検知` `配分調整` に置く方が崩れにくい。
- strategy edge と execution edge を分離して考えるべきで、vault の材料もその方向に揃っている。
