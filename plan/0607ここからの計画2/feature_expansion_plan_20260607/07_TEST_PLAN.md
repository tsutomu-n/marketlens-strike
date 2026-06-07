<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 07 Test Plan

## 方針

先にテストを書く。外部API・credentialsなしで完結する。

```text
Unit tests:
  contracts / loaders / validators / linter / exporters

CLI tests:
  Phase B7で最小限

Integration-like tests:
  configs/research_layer_2_2/ndx/*.yaml を読み、validate / lint / export する
```

## 最小テストコマンド

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
```

最終確認:

```bash
./scripts/check
```

## Test groups

### A tests

```bash
uv run pytest -q \
  tests/research/test_seed_registry.py \
  tests/research/test_mechanism_parts.py \
  tests/research/test_data_source_contract.py \
  tests/research/test_variable_inventory.py \
  tests/research/test_causal_roles.py \
  tests/research/test_temporal_availability.py
```

期待:

```text
- YAMLを読める。
- 必須field欠損でfail。
- unknown roleでfail。
- variable_inventoryとcausal_rolesの矛盾でfail。
- temporal layer逆行を検出できる。
```

### B tests

```bash
uv run pytest -q \
  tests/research/test_core_dag_contracts.py \
  tests/research/test_core_dag_loader.py \
  tests/research/test_core_dag_validator.py \
  tests/research/test_core_dag_linter.py \
  tests/research/test_core_dag_export.py \
  tests/research/test_counter_dags.py
```

期待:

```text
- HYP-NDX-001 configがpass。
- 危険edge fixtureがfail。
- Mermaid / JSON / report を生成できる。
```

### CLI tests

Phase B7でCLIを追加した場合だけ。

```bash
uv run pytest -q tests/research/test_research_layer22_commands.py
```

期待:

```text
- validate command exits 0 for valid config。
- invalid config exits 2。
- export command writes expected files。
- command does not call network。
```

## Negative fixtures

作るfixture例:

```text
tests/fixtures/research_layer_2_2/invalid_unknown_node.yaml
tests/fixtures/research_layer_2_2/invalid_self_loop.yaml
tests/fixtures/research_layer_2_2/invalid_outcome_to_treatment.yaml
tests/fixtures/research_layer_2_2/invalid_future_to_signal.yaml
tests/fixtures/research_layer_2_2/invalid_role_mismatch.yaml
tests/fixtures/research_layer_2_2/invalid_counter_dag_missing.yaml
```

## Full check

```bash
./scripts/check
```

`./scripts/check` は最終PR前に必須。作業中の小PRでは `tests/research` と docs checker を先に回す。

## 合格時に出すべきメモ

PR本文には以下を書く。

```text
Verification:
  uv run pytest -q tests/research
  uv run python scripts/check_current_docs.py
  ./scripts/check

Generated artifacts checked:
  data/research/ndx/core_dag.json
  data/research/ndx/core_dag.mmd
  data/research/ndx/data_requirements.yaml
  data/reports/ndx_core_dag_report.md

Out of scope confirmed:
  no external API
  no credentials
  no paper/live order
  no backtest
  no Strategy Lab export
```
