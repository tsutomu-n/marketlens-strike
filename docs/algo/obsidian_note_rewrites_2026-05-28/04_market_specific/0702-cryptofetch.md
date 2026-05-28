# 0702-cryptofetch

## このノートの扱い

暗号資産データ取得ツールの設計メモとして扱う。戦略そのものではなく、データ取得、認証、設定、欠損管理の部品。

## 元ノートの要旨

APIキーを環境変数で扱い、取引所やデータソースから暗号資産データを取得するツールの構想。

## 今日時点での補正

データ取得ツールは「取れたらよい」ではなく、取得時刻、遅延、欠損、rate limit、API仕様変更、再現性を記録できる必要がある。

## 理想的ナラティブ / 誤謬リスク

- `DATA_VENDOR_DEPENDENCE`: APIが安定して取れる前提。
- `SECURITY_SECRET`: APIキーを環境変数に置けば十分という前提。
- `OPERATIONAL_COMPLEXITY`: 複数取引所対応で保守面が増える。

## 戦略部品への分解

- `Data Collector`: OHLCV、ticker、order book、funding、open interest。
- `Data Quality Gate`: 欠損、重複、遅延、時刻ずれ。
- `Security Guard`: secretはログに出さない、権限を最小化する。
- `Monitoring Layer`: rate limit、API error、freshness。

## 実験に落とすなら

1取引所、1銘柄、1時間足から開始し、1週間の取得成功率と欠損率を測る。取引はしない。

## 採用条件

同じ期間のデータを再取得した時に差分が説明できること。

## 捨て条件

API障害や欠損時に静かに古いデータを返す場合。

## 現在性チェック

対象取引所API、認証、rate limit、商用利用可否を確認する。

## 関連 docs

- `../STRATEGY_PARTS_CATALOG.md`

## 原ノート

- `../obsidian_note_copies/04_market_specific/0702-cryptofetch.md`

