# 1026_Backtest_Trade!

## このノートの扱い

バックテスト環境構築のメモとして扱う。戦略評価ではなく、検証の土台。

## 元ノートの要旨

バックテストやトレード検証に関する実装・環境メモ。

## 今日時点での補正

バックテスト環境で最初に固定すべきは、データ、時刻、手数料、スリッページ、約定ルール、評価期間。戦略コードより前に検証契約を決める。

## 理想的ナラティブ / 誤謬リスク

- `BACKTEST_OVERFIT`: 何度も試すほど良い過去を見つける。
- `EXECUTION_GAP`: ローソク足の価格で都合よく約定する。
- `OPERATIONAL_COMPLEXITY`: 環境構築が目的化する。

## 戦略部品への分解

- `Evaluation Harness`: split、cost、slippage、metrics。
- `Data Quality Gate`: 欠損、重複、時刻、銘柄生存バイアス。
- `Experiment Scorecard`: 仮説、期間、結果、判断を記録。
- `Risk Guard`: 実運用前のpaper observation条件。

## 実験に落とすなら

最初に「同じ入力なら同じ結果が出る」ことを確認する。次に、手数料を2倍、slippageを2倍にしても候補が残るかを見る。

## 採用条件

結果だけでなく、データ範囲、コスト、除外条件、失敗理由が再現可能に残ること。

## 捨て条件

手元でしか再現できない、またはデータ取得時点が記録されない場合。

## 現在性チェック

使うバックテストライブラリ、データ取得先、取引所仕様を確認する。

## 関連 docs

- `../EXPERIMENT_SCORECARD.md`

## 原ノート

- `../obsidian_note_copies/05_execution_and_stack/1026_Backtest_Trade!.md`

