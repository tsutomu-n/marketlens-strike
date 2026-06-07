<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 07 Target File Map

## 1. 追加するディレクトリ

```text
docs/research/ndx/
configs/research_layer_2_2/ndx/
src/sis/research/hypothesis/
src/sis/research/dag/
tests/research/
```

## 2. 追加するdocs

```text
docs/research/ndx/
  00_SCOPE.md
  01_SEED_REGISTRY.md
  02_MECHANISM_PARTS.md
  03_VARIABLE_INVENTORY.md
  04_CAUSAL_ROLES.md
  05_TEMPORAL_AVAILABILITY.md
  HYP_NDX_001_OPEN_GAP_RESIDUAL.md
  COUNTER_DAGS.md
  2_2_IMPLEMENTATION_BOUNDARY.md
```

全Markdownはrepoルール通り、先頭に以下を置く。

```markdown
<!--
作成日: YYYY-MM-DD_HH:mm JST
更新日: YYYY-MM-DD_HH:mm JST
-->
```

## 3. 追加するconfig

```text
configs/research_layer_2_2/ndx/
  scope.yaml
  seed_registry.yaml
  mechanism_parts.yaml
  variable_inventory.yaml
  causal_roles.yaml
  temporal_availability.yaml
  core_dag.yaml
  counter_dags.yaml
```

## 4. 追加するschema

```text
schemas/
  research_scope.v1.schema.json
  research_seed_registry.v1.schema.json
  research_mechanism_parts.v1.schema.json
  research_variable_inventory.v1.schema.json
  research_causal_roles.v1.schema.json
  research_temporal_availability.v1.schema.json
  core_dag.v1.schema.json
  counter_dag.v1.schema.json
```

JSON Schemaは薄いguardでよい。詳細validationはPydantic modelを正本にする。

## 5. 追加するPython module

```text
src/sis/research/hypothesis/
  __init__.py
  scope_contracts.py
  scope_loader.py
  seed_contracts.py
  seed_loader.py
  mechanism_contracts.py
  mechanism_loader.py
  variable_contracts.py
  variable_loader.py
  role_contracts.py
  role_validator.py
  temporal_contracts.py
  temporal_validator.py

src/sis/research/dag/
  __init__.py
  contracts.py
  loader.py
  validator.py
  errors.py
  rules.py
  linter.py
  counter.py
  data_requirements.py
  export.py
  report.py
```

## 6. 変更する可能性があるPython module

```text
src/sis/commands/research.py
src/sis/cli.py
```

追加CLIを登録する場合のみ。

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
```

## 7. 追加するtests

```text
tests/research/
  test_hypothesis_scope.py
  test_seed_registry.py
  test_mechanism_parts.py
  test_variable_inventory.py
  test_causal_roles.py
  test_temporal_availability.py
  test_core_dag_contracts.py
  test_core_dag_validator.py
  test_core_dag_linter.py
  test_ndx_core_dag_config.py
  test_counter_dags.py
  test_core_dag_export.py
  test_data_requirements_export.py
  test_research_dag_commands.py
```

## 8. 変更しないファイル

```text
src/sis/backtest/**
src/sis/paper/**
src/sis/execution/**
src/sis/venues/trade_xyz/**
src/sis/bot/**
configs/trade_xyz_*.yaml
configs/fee_model*.yaml
pyproject.toml
uv.lock
```

## 9. Generated artifacts

```text
data/research/ndx/
  core_dag.json
  core_dag.mmd
  counter_dags.md
  data_requirements.yaml

data/reports/
  ndx_core_dag_report.md
```

生成物はgit管理外。テストでは `tmp_path` を使う。

## 10. ファイルサイズ制約

新規・大幅編集Pythonファイルは800行以下を目安にする。責務が大きくなったら、loader / validator / linter / exportへ分割する。
