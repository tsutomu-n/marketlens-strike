<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 03_CURRENT_REPO_CONTEXT

## 現Repoで確認すべき事実

現在のRepoには、少なくとも以下が存在する前提で監査する。

```text
configs/research_layer_2_2/ndx/
  scope.yaml
  seed_registry.yaml
  mechanism_parts.yaml
  data_sources.yaml
  variable_inventory.yaml
  causal_roles.yaml
  temporal_availability.yaml
  core_dag.yaml
  counter_dags.yaml

src/sis/research/dag/
  contracts.py
  loader.py
  validator.py
  linter.py
  export.py
  report.py
  counter.py
  data_requirements.py
  review_contracts.py
  review_pack.py
  review_import.py
  exit_gate.py
  freeze_manifest.py

tests/research/
  test_core_dag_*.py
  test_llm_review_*.py
  test_layer22_exit_gate.py
  test_research_layer22_review_commands.py
```

## 現在の正本順位

```text
1. src/
2. tests/
3. schemas/
4. configs/
5. CLI help
6. docs/current
7. plan/archive
```

`plan/archive`内の旧ZIP展開物は、現在の実装正本ではない。

## 既存CLI

以下が現行CLIとして存在するか確認する。

```bash
uv run sis research-layer22-validate --help
uv run sis research-layer22-export --help
uv run sis research-layer22-review-pack --help
uv run sis research-layer22-review-import --help
uv run sis research-layer22-exit-gate --help
```

## 現在の重要な設計境界

Layer 2.2 review harness は、local/manual review plumbingである。これにより、alpha、feature-panel readiness、residual correctness、Strategy Lab export readiness、backtest readiness、paper/live readinessは証明されない。
