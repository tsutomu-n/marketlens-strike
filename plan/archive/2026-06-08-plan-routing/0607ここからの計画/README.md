<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# README

## 結論

この計画は、`marketlens-strike` に **Layer 2.2 DAG Compiler** を追加するための実装資料である。

今回の完成扱いは、売買戦略・バックテスト・paper order・live order ではない。完成扱いは次である。

```text
NASDAQ / NDX の研究Seedを、
Scope → Seed → Mechanism Parts → Variable Inventory → Causal Role → Temporal Availability → Core DAG
の順で機械可読化し、
DAG validator / forbidden-edge linter / counter-DAG / data-requirements / Mermaid report まで生成できる。
```

## この計画で作るもの

```text
Phase A:
  2.2以前の最小contract
  - scope
  - seed registry
  - mechanism parts
  - variable inventory
  - causal role assignment
  - temporal availability

Phase B:
  2.2本体
  - core DAG schema
  - loader / validator
  - forbidden-edge linter
  - HYP-NDX-001 core DAG
  - counter DAG
  - data requirement export
  - DAG report export

Phase C:
  後続のための設計だけ
  - feature panel
  - open gap residual
  - neutralization report
  - Strategy Lab export
```

## この計画で作らないもの

```text
今回やらない:
  - Bitget credentialed network smoke
  - demo order submit / cancel / fill sync
  - Trade[XYZ] readiness 解消
  - backtest_data_ready=true
  - PaperIntentPreview生成
  - live order / exchange write
  - wallet / signing
  - NQ futures ingestion
  - options / gamma / 0DTE
  - NOTEARS / PCMCI / DoWhy 実行
```

## コーダー向けの読み順

```text
1. 01_GOAL.md
2. 02_SCOPE_AND_BOUNDARIES.md
3. 03_TASKS.md
4. 04_ACCEPTANCE.md
5. 05_EXTERNAL_API_POLICY.md
6. 07_TARGET_FILE_MAP.md
7. 08_TEST_PLAN.md
8. 09_SCHEMA_AND_CONFIG_SKETCHES.md
9. 10_IMPLEMENTER_CHECKLIST.md
10. appendices/
```

## 実装先の原則

```text
汎用2.2基盤:
  src/sis/research/hypothesis/
  src/sis/research/dag/

NDX専用設定:
  configs/research_layer_2_2/ndx/

NDX専用docs:
  docs/research/ndx/

schema:
  schemas/research_hypothesis_*.schema.json
  schemas/core_dag.v1.schema.json

tests:
  tests/research/test_hypothesis_*.py
  tests/research/test_core_dag_*.py
```

## 最初のPRで触ってよい範囲

```text
触ってよい:
  - docs/research/ndx/
  - configs/research_layer_2_2/ndx/
  - schemas/research_hypothesis_*.schema.json
  - schemas/core_dag.v1.schema.json
  - src/sis/research/hypothesis/
  - src/sis/research/dag/
  - src/sis/commands/research.py
  - tests/research/
  - scripts/check_current_docs.py

原則触らない:
  - src/sis/backtest/
  - src/sis/paper/
  - src/sis/execution/
  - src/sis/venues/trade_xyz/
  - src/sis/bot/
  - pyproject.toml
  - uv.lock
```

## 完了時の代表コマンド

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 最重要の停止条件

```text
次のどれかが必要になったら、そのPRでは止める:
  - 外部API接続
  - credentials
  - pyproject依存追加
  - paper/live order生成
  - strategy_signals.parquet生成
  - Trade[XYZ] readiness変更
  - backtest engine変更
```
