# 0721-LightGBM パラメータチューニング

## このノートの扱い

LightGBMを価格予測の主役にする資料ではなく、特徴量候補を評価する補助モデルとチューニング危険管理の資料として扱う。

## 元ノートの要旨

LightGBMのパラメータ、学習率、木の深さ、正則化、探索手法などを扱う。

## 今日時点での補正

LightGBMは強力だが、金融時系列ではチューニング自由度が高く、リークと過学習が先に問題になる。パラメータ探索より先に、ラベル定義、時系列分割、purge/embargo、特徴量の利用可能時点を固定する。

## 理想的ナラティブ / 誤謬リスク

- `PREDICTION_OVERCLAIM`: 高性能モデルなら相場を読めるという前提。
- `BACKTEST_OVERFIT`: ハイパーパラメータ探索で過去に合わせる。
- `DATA_VENDOR_DEPENDENCE`: 学習時点で存在しなかった特徴量を混ぜる危険。

## 戦略部品への分解

- `Feature Scorer`: どの特徴量が安定して効くかを見る。
- `Participation Filter`: シグナルを通す/見送る確率補助。
- `Model Risk Guard`: 時系列CV、feature importance安定性、drift監視。
- `Evaluation Harness`: baseline超過分だけを見る。

## 実験に落とすなら

LightGBMの前に、ルールベースとロジスティック回帰を作る。LightGBMはAUCやaccuracyではなく、取引コスト込みの期待値改善で評価する。

## 採用条件

単純モデルを上回り、期間を変えても重要特徴量と方向性が大きく崩れないこと。

## 捨て条件

チューニング後だけ改善し、未使用期間や別銘柄で劣化する場合。

## 現在性チェック

LightGBMの公式パラメータ仕様とPython APIは実装前に確認する。

## 関連 docs

- `../RESEARCH_VALIDATION_PLAYBOOK.md`

## 原ノート

- `../obsidian_note_copies/03_model_research/0721-LightGBM パラメータチューニング.md`

