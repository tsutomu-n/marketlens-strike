# 0721-RiskGuard Crypto Engine(RGCE)

## このノートの扱い

利益を出すエンジンではなく、戦略を止める・縮小する・隔離するための安全部品として扱う。

## 元ノートの要旨

APIキー保護、データ統合、異常検知、テキスト処理、リスク監視など、暗号資産botの周辺防御機能をまとめている。

## 今日時点での補正

RGCEの価値は「勝つこと」ではなく「壊れ方を制限すること」。戦略本体とは分離し、すべてのbot候補に共通で適用する横断部品にする。

## 理想的ナラティブ / 誤謬リスク

- `OPERATIONAL_COMPLEXITY`: 防御機能を多く足せば安全になるという前提。
- `SECURITY_SECRET`: APIキー保護を暗号化だけで済ませる危険。
- `DATA_VENDOR_DEPENDENCE`: 複数データソース統合時の欠損や遅延を軽視しやすい。

## 戦略部品への分解

- `Security Guard`: secret管理、権限分離、ログマスク。
- `Risk Guard`: 日次損失、連敗、急変、API障害停止。
- `Monitoring Layer`: heartbeat、latency、data freshness、alert。
- `Data Quality Gate`: 欠損、重複、異常値、タイムスタンプずれ検知。

## 実験に落とすなら

利益指標ではなく、障害注入テストをする。価格欠損、API 429、約定失敗、遅延拡大、急落、秘密情報ログ混入を模擬し、止まるかを見る。

## 採用条件

各戦略に依存せず、同じ停止契約で適用できること。

## 捨て条件

監視が複雑すぎて、異常時に人間が何をすればよいか分からない場合。

## 現在性チェック

取引所API権限、IP制限、secret保管方式、通知サービス仕様を実装前に確認する。

## 関連 docs

- `../STRATEGY_PARTS_CATALOG.md`
- `../RESEARCH_VALIDATION_PLAYBOOK.md`

## 原ノート

- `../obsidian_note_copies/01_core_trend/0721-RiskGuard Crypto Engine(RGCE).md`

