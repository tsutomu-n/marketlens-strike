# 1031_Trading with polars

## このノートの扱い

Polarsを高速なデータ処理基盤として扱う。戦略優位性ではなく、検証と特徴量生成の実装選択肢。

## 元ノートの要旨

Polarsを用いたトレーディングデータ処理、集計、特徴量作成に関するメモ。

## 今日時点での補正

Polarsは大規模データやlazy処理に強いが、時系列金融ではソート、時刻型、groupby_dynamic、join_asof、null処理のミスが戦略結果を壊す。

## 理想的ナラティブ / 誤謬リスク

- `OPERATIONAL_COMPLEXITY`: 高速化で検証品質が上がると誤認する。
- `BACKTEST_OVERFIT`: 大量の特徴量生成が容易になる。
- `DATA_VENDOR_DEPENDENCE`: 入力データの品質問題を処理速度で隠す。

## 戦略部品への分解

- `Feature Factory`: rolling、lag、asof join、multi-timeframe集計。
- `Data Quality Gate`: null、重複、時刻ずれ、schema drift。
- `Evaluation Harness`: 大量候補の前処理。
- `Research Assistant`: 特徴量棚卸し。

## 実験に落とすなら

Pandas実装とPolars実装で同じ特徴量が出るかを小データで照合する。lazy最適化前に、時刻順と未来参照がないことを確認する。

## 採用条件

高速化しても結果が変わらず、処理内容がレビュー可能であること。

## 捨て条件

joinやrollingの意味を説明できないまま特徴量が増える場合。

## 現在性チェック

Polars公式user guide、Python API、time series関連APIの現行仕様を確認する。

## 関連 docs

- `../STRATEGY_PARTS_CATALOG.md`

## 原ノート

- `../obsidian_note_copies/05_execution_and_stack/1031_Trading with polars.md`

