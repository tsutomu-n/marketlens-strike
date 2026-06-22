<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# MarketLens Strike Crypto Perp MVP 最終実装ハンドオフ

## 結論

このパッケージを、Crypto Perp 拡張の実装正本として使用する。

この計画は、以前の次の資料を置き換える。

- Draft PR #2 の旧 `Crypto Perp Personal Edge Lab Implementation Plan`
- 旧ZIP `marketlens-strike-crypto-perp-personal-edge-plan-2026-06-20.zip`
- PR #2 上の「CP-00〜CP-10をそのまま実装」という旧指示
- 「全損許容だからレバレッジを上げる」という解釈

最初から巨大な研究基盤を建設しない。完成順は次の3段階とする。

```text
MVP-A: public data で event を検出・凍結・表示する
MVP-B: 判断を結果より前に記録し、方向中立に outcome を確定する
MVP-C: 隔離した 5〜25 USD で実約定を測り、simulation を補正する
```

MarketLens Strike の役割は、勝てそうな物語を増やすことではない。

```text
観測
-> 小額実測
-> 不一致の特定
-> 早期棄却または次実験
```

までの時間を短くすることが目的である。

## 読む順番

1. `01_FINAL_IMPLEMENTATION_PLAN.md`
2. `02_ARTIFACT_AND_DATA_CONTRACTS.md`
3. `03_FILE_BY_FILE_MAP.md`
4. `04_TEST_AND_ACCEPTANCE_PLAN.md`
5. `05_OSS_RESEARCH_COMPETITION_NOTES.md`
6. `06_OPERATIONS_AND_TINY_LIVE_RUNBOOK.md`
7. `07_TASK_CHAIN.yaml`
8. `08_CODER_PROMPT.md`
9. `09_DECISION_LOG.md`
10. `10_SOURCE_INDEX.md`

補助設定:

- `examples/bitget_personal_edge_lab.example.yaml`
- `examples/tiny_live_measurement.example.yaml`
- `examples/env.crypto_perp.example`

## 実装開始前に必ず行うこと

```bash
git status --short
git rev-parse HEAD
uv sync --dev --locked
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

結果を最初のPR本文へ保存する。既存失敗がある場合は、新機能の失敗と混ぜない。

## 実装順

`07_TASK_CHAIN.yaml` の `M00` から順番に進める。一度に複数の大規模sliceを混ぜない。

```text
M00 current truth / supersession
M01 domain foundation + config + Hypothesis
M02 Bitget public probe + immutable raw snapshot
M03 universe diff + broad 15m history
M04 event capture + event card (MVP-A)
M05 candidate-only 1m / trades / books recorder
M06 prospective decision + outcome ledger (MVP-B)
M07 validation accelerator pack
M08 credentialed read-only + order preview
M09 tiny live execution calibration (MVP-C, separate explicit approval)
M10 actual cash ledger + replay calibration
M11 hypothesis tournament + existing Workbench bridge
```

## 絶対境界

市場損失と運用事故を分ける。

許容可能:

- 明示的に隔離した実験予算が市場変動で0になること
- 高い分散、低勝率、大きなドローダウン
- 仮説が失敗し、実験費を失うこと

許容しない:

- API key漏洩
- 出金権限付きkey
- wrong symbol / wrong side / wrong decimal
- duplicate order
- unbounded retry
- cross-margin spillover
- 自動追加入金
- stale signalによる発注
- reconciliation不能のまま次注文

`M09` より前は exchange write を実装しない。`M09` は別の明示承認がない限り実行しない。

## コーダーの成果報告

各taskごとに次を報告する。

```text
Task ID
変更ファイル
新CLI
新artifact/schema
テスト実行結果
未解決事項
境界確認
次taskへ進めるか
```
