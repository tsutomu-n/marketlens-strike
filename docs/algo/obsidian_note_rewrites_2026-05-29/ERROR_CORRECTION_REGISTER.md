<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Error Correction Register

原ノートおよび前回リライトを読む時に、特に修正して扱うべき点です。

| 対象 | 原ノートにある/出やすい主張 | 修正 |
|---|---|---|
| Adaptive Alpha / ML | LightGBMや深層学習で未来価格を高精度に予測する | 価格予測ではなく、参加可否・レジーム・リスク縮小の補助に限定する |
| VaR | VaRは最大損失を予測する | VaRは指定信頼水準の損失分位点。最大損失ではない。tail lossはESやstressで見る |
| Stop Loss | 損失を限定できる | gap、流動性枯渇、API遅延、slippageで想定より悪く約定する |
| Order Book | 板から大きな優位性を得られる | 板は短寿命。方向予測より、参加見送り・サイズ制限・約定コスト推定に使う |
| Jito | bundleなら安全にatomic実行できる | slot境界、tip、leader、失敗、未着地、費用がある。収益源ではなく実行制約 |
| Jito旧記述 | GTO/G2/Cheetoなどの表記 | 原ノートの転記/音声認識誤りの可能性が高い。Jito公式docsで確認する |
| Jito旧数値 | stakeやslot比率が固定値のように書かれる | 古い動画時点の値。現在値として使わない |
| Solana bot | 条件に合うtokenを自動購入する | 危険。paper observation、token safety、manual approval、資金上限が先 |
| Private key | 設定ファイルに置けばよい | 実運用では隔離、権限最小化、ログマスク、空wallet、secret管理が必須 |
| Passive income news | 自動ニュースで持続的収入 | 取引戦略ではない。広告/紹介/規約/著作権/金融プロモーションの話 |
| VectorBT | デモ戦略や最適化で高スコアなら有望 | vectorized backtestは一次スクリーニング。約定モデルとコストで再検証する |
| PyBotters | API接続できればbotが作れる | 注文冪等性、再接続、状態同期、エラー時停止が本体 |
| Polars | 高速化で検証品質が上がる | join/rolling/asofの時刻ミスがリークになる。結果一致テストが先 |
| Portfolio optimization | 最適化で分散できる | 暗号資産では相関が急上昇する。上限ルールとvol targetが先 |
| GA / agent | 自律探索で良い戦略を発見できる | 探索自由度が過学習を増やす。仮説生成に限定する |
