# 0714-Adaptive-Alpha-Trendトレードプログラム

## このノートの扱い

巨大な「全部入り戦略構想」としてではなく、特徴量、異常検知、ML、リスク管理、評価の部品カタログとして扱う。

## 元ノートの要旨

AlphaTrendを中心に、データ処理、特徴量エンジニアリング、Isolation Forest、LightGBM、VaR/ES、ストップロス、バックテスト、マルチ時間軸、センチメント、強化学習、オルタナティブデータまで展開している。

## 今日時点での補正

価値は「必要部品が広く列挙されている」点にある。一方で、機能を増やすほど良くなるという物語が強い。現代的には、AlphaTrend自体を勝ち筋と見るより、トレンド候補を作る1特徴量として扱い、MLやRLは最後に回すべき。

## 理想的ナラティブ / 誤謬リスク

- `PREDICTION_OVERCLAIM`: MLで未来価格を高精度に予測できるという表現がある。
- `OPERATIONAL_COMPLEXITY`: データ、特徴量、異常検知、ML、RL、代替データを同時に足しすぎる。
- `BACKTEST_OVERFIT`: パラメータ、特徴量、モデル選択の自由度が大きい。
- `DATA_VENDOR_DEPENDENCE`: ニュース、SNS、代替データは取得コストと遅延が無視されやすい。

## 戦略部品への分解

- `Feature Factory`: AlphaTrend、ATR、RSI、MACD、出来高、時間軸特徴量。
- `Anomaly Filter`: データエラー、急変、板飛び、異常出来高。
- `Model Layer`: 予測ではなく、取引可否や確信度の補助。
- `Risk Guard`: VaR/ESではなく、まず固定リスク、日次停止、連敗停止。
- `Evaluation Harness`: ウォークフォワード、反復検証、コスト込み評価。

## 実験に落とすなら

最初の実験は「AlphaTrend単体が、同じ期間の単純MA/Donchian/ATR breakoutを上回るか」に限定する。次に、異常検知を入れた場合にDDが下がるかを見る。MLは、ベースラインを上回る余地が確認されてから。

## 採用条件

特徴量を増やすほど良いのではなく、部品追加ごとに out-of-sample の改善理由が説明できること。

## 捨て条件

モデルや特徴量を増やした時だけ過去成績が改善し、未使用期間や別銘柄で劣化する場合。

## 現在性チェック

LightGBM、scikit-learn、深層学習ライブラリ、データAPIの現行仕様は実装前に公式情報で確認する。

## 関連 docs

- `../STRATEGY_PARTS_CATALOG.md`
- `../EXPERIMENT_SCORECARD.md`

## 原ノート

- `../obsidian_note_copies/01_core_trend/0714-Adaptive-Alpha-Trendトレードプログラム.md`

