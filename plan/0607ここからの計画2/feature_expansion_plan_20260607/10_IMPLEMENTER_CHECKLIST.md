<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 10 Implementer Checklist

## 事前確認

```text
[ ] `git status --short --branch --untracked-files=all` を確認した。
[ ] `uv run sis --help` でCLI構造を確認した。
[ ] `AGENTS.md` を読んだ。
[ ] `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md` を読んだ。
[ ] 今回 paper/live/backtest/Strategy Lab export に触らないことを確認した。
```

## Phase A

```text
[ ] configs/research_layer_2_2/ndx/scope.yaml を作った。
[ ] seed_registry.yaml を作った。
[ ] mechanism_parts.yaml を作った。
[ ] data_sources.yaml を作った。
[ ] variable_inventory.yaml を作った。
[ ] causal_roles.yaml を作った。
[ ] temporal_availability.yaml を作った。
[ ] src/sis/research/hypothesis/ に contracts / loader / validator を作った。
[ ] tests/research/test_seed_registry.py を追加した。
[ ] tests/research/test_mechanism_parts.py を追加した。
[ ] tests/research/test_variable_inventory.py を追加した。
[ ] tests/research/test_causal_roles.py を追加した。
[ ] tests/research/test_temporal_availability.py を追加した。
[ ] `uv run pytest -q tests/research` が通った。
```

## Phase B

```text
[ ] schemas/core_dag.v1.schema.json を作った。
[ ] src/sis/research/dag/contracts.py を作った。
[ ] dag loader / validator を作った。
[ ] linter rules v2 を実装した。
[ ] configs/research_layer_2_2/ndx/core_dag.yaml を作った。
[ ] configs/research_layer_2_2/ndx/counter_dags.yaml を作った。
[ ] counter-DAG最低8本を登録した。
[ ] data_requirements exporter を作った。
[ ] Mermaid / JSON / Markdown report exporter を作った。
[ ] research-layer22-validate CLIを追加した、またはPython APIで代替した。
[ ] research-layer22-export CLIを追加した、またはPython APIで代替した。
[ ] tests/research/test_core_dag_linter.py で危険edgeを落とせることを確認した。
[ ] `uv run pytest -q tests/research` が通った。
```

## 生成物確認

```text
[ ] data/research/ndx/core_dag.json が生成できた。
[ ] data/research/ndx/core_dag.mmd が生成できた。
[ ] data/research/ndx/counter_dags.md が生成できた。
[ ] data/research/ndx/data_requirements.yaml が生成できた。
[ ] data/reports/ndx_core_dag_report.md が生成できた。
```

## 境界確認

```text
[ ] 外部APIを呼んでいない。
[ ] credentialsを使っていない。
[ ] pyproject.toml / uv.lock を変更していない。
[ ] src/sis/backtest/ を変更していない。
[ ] src/sis/paper/ を変更していない。
[ ] src/sis/execution/ を変更していない。
[ ] src/sis/venues/trade_xyz/ を変更していない。
[ ] data/research/strategy_signals.parquet を生成していない。
[ ] PaperIntentPreviewを生成していない。
```

## 最終検証

```text
[ ] uv run pytest -q tests/research
[ ] uv run python scripts/check_current_docs.py
[ ] ./scripts/check
```

## PR本文に書くこと

```text
Purpose:
  Implement Layer 0-2.2 Research DAG Compiler foundation for HYP-NDX-001.

Verification:
  uv run pytest -q tests/research
  uv run python scripts/check_current_docs.py
  ./scripts/check

Generated:
  data/research/ndx/core_dag.json
  data/research/ndx/core_dag.mmd
  data/research/ndx/data_requirements.yaml
  data/reports/ndx_core_dag_report.md

Out of scope:
  external API, credentials, backtest, Strategy Lab export, paper/live order.
```
