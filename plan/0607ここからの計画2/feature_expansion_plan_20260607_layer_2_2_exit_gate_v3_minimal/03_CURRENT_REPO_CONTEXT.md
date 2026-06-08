<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 03_CURRENT_REPO_CONTEXT

## 参照したRepo前提

この計画は、会話内で提供された `marketlens-strike` repo dump と既存計画資料を前提にする。

## 現在のRepo境界

`marketlens-strike` は Python 3.13 CLI workspace で、backtest-first strategy research、Strategy Research Lab、paper operations、venue-neutral execution contracts、Trade[XYZ] read-only evidence collection、safety gates を含む。

確認済みの現行境界。

```text
data/research/strategy_signals.parquet:
  Strategy Lab canonical signal artifact

data/research/signals.csv:
  legacy export only

PaperIntentPreview:
  paper-only preview
  live orderではない

JSON Schema:
  thin guard

runtime validation:
  Pydantic model が正本

wallet/signing/exchange write/production live:
  out of scope
```

## 現行CLI surface

既存資料上の現行CLI。

```text
strategy-preview
evaluate-strategy-lab
build-paper-candidate-pack
promotion-decision
build-paper-intent-preview
paper-from-intents
bot-preview
collect-trade-xyz-quotes
phase-gate-review
validate-artifacts
diagnose-quotes
```

## 現在の検証方針

固定pass countを計画書に残さない。作業時点で次を実行する。

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

## 既存実装への接続位置

今回の実装は Strategy Lab より前の review gate として置く。

```text
Layer 2.2 artifacts
  -> Exit Gate Review
  -> APPROVE_2_3 / REVISE_2_2 / REJECT_SEED
```

Strategy Lab へはまだ接続しない。

## 既存パスとの関係

```text
src/sis/research/dag/:
  今回の主実装先

src/sis/research/hypothesis/:
  既にPhase A/Bで作成済み前提

src/sis/research/strategy_lab/:
  no-touch

src/sis/research_protocol/:
  no-touch

src/sis/commands/research.py:
  CLI追加時のみedit
```

## 既存設計から継承する考え方

```text
- code/tests/schema/config/CLI helpが正本
- docs/planは補助
- runtime validationはPydantic
- JSON Schemaはthin guard
- external APIやlive orderへ広げない
- ./scripts/checkを最後に通す
```
