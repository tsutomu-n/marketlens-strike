<!--
作成日: 2026-07-05_10:24 JST
更新日: 2026-07-05_13:26 JST
-->

# App Terms Glossary 2026-07-05

## 結論

この文書は、`marketlens-strike` の current docs を読むための用語集です。実装有無や readiness の正本ではありません。

| 用語 | この repo での意味 | 誤読してはいけないこと |
|---|---|---|
| artifact | CLI や builder が出す JSON / Markdown / HTML / Parquet などの生成物 | artifact があるだけで実運用可能という意味ではない |
| current docs | `scripts/check_current_docs.py` が strict check する現行入口 | checker green は本文の全意味が最新という保証ではない |
| archive | historical context として残す古い docs / plans | current proof として読まない |
| backtest | 過去データや fixture で戦略を検査すること | 将来利益の保証ではない |
| paper-only preview | 本番資金を使わない仮の注文意図 | live order permission ではない |
| Strategy Review | existing artifact を人間が読むための packet / decision record にする surface | paper / live の許可証ではない |
| `READ_ONLY_GO` | read-only gate の判定 | account readiness, wallet readiness, exchange-write readiness ではない |
| `READY_FOR_HUMAN_REVIEW` | 人間レビューへ渡せる状態 | 自動採用や注文許可ではない |
| Crypto Perp Backtest Candidate Pack | actual cash なしの simulation evidence pack | profit proof, paper permission, tiny-live readiness, live readiness ではない |
| no-cash goal progress | お金を使わない段階の進捗。implementation / routing と evidence quality を分けて読む | 単一の%を profit readiness や live readiness と読むこと |
| actual cash | 実約定や ledger に基づく cash result | before-cost proxy や simulation estimate とは別物 |
| tiny-live | 小額・限定条件つきの実ネットワーク測定領域 | 通常の live trading ではない |
| Trade[XYZ] | 実装済み venue-specific surface / historical context | repo の default product axis ではない |
| venue-neutral | 特定 venue の注文口を前提にしない設計軸 | venue 実装がないという意味ではない |

## 確認コマンド

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
```
