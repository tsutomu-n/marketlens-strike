<!--
作成日: 2026-06-20_20:40 JST
更新日: 2026-06-20_20:40 JST
-->

# コーダーへ渡す指示

以下をそのまま渡す。

---

MarketLens Strikeへ `Crypto Perp Truth-Cycle MVP` を実装してください。

最初にこのZIPを展開し、`00_READ_ME_FIRST.md`から順に読んでください。以前のPR #2旧計画や旧ZIPではなく、このパッケージを正本にしてください。

実装は `07_TASK_CHAIN.yaml` のM00から順番に、原則1task=1PRで進めてください。

## 目的

Bitget USDT Perpについて、次のtruth cycleを最短で完成させます。

```text
public event detection
-> event-time snapshot
-> prospective SHORT/LONG/NO_TRADE decision
-> matured outcome
-> isolated 5〜25 USD actual execution measurement
-> actual cash ledger and simulation calibration
```

急騰後shortが勝つという前提を置かないでください。reversal short、continuation long、no-tradeを同じevent setで比較してください。

## 優先順位

```text
1. 実市場から学ぶまでの時間
2. actual fill / fee / cash
3. failure/restart/idempotency
4. artifact lineage
5. UIや抽象化
```

## 禁止

```text
旧CP-00〜10巨大計画の実装開始
全銘柄L2常時保存
Strategy Lab v2全面移行
Svelte UI
ML/LLM optimizer
reference venue先行実装
自動戦略発注
networkを通常CIで使用
secretのlog/artifact保存
```

## OSS

- Hypothesisはdev dependencyとして採用。
- Tardis sampleはgolden fixture。
- pybottersは別workspaceでnative WSと24h比較後に採用判断。
- FreqtradeはGPLv3の外部sidecar。coreへimport/copyしない。
- HummingbotはBitget connectorの参考。公式Bitget v3 docsを正本とする。
- hftbacktest、River、NautilusTraderは採用条件が発生するまで入れない。

## Live boundary

M09コードはmockで実装・テストしてよいが、実ネットワークlive measurementはユーザーの別明示承認が必要です。

市場損失は隔離budget内で許容します。次は許容しません。

```text
wrong symbol/side/decimal
duplicate order
blind retry
cross margin
auto top-up
reconciliation failure後の次entry
withdrawal-capable key
```

## 各PRで報告

```text
Task ID
目的
変更ファイル
新CLI/artifact/schema
テストコマンドと結果
boundary確認
既知の不足
次taskへ進めるか
```

## Baseline

実装開始前と各milestoneで次を実行してください。

```bash
uv sync --dev --locked
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

ドキュメントよりcode/tests/schema/config/lock/CLI helpを正本としてください。

---
