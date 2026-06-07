<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 06 Target File Map

## Create

```text
configs/research_layer_2_2/ndx/scope.yaml
configs/research_layer_2_2/ndx/seed_registry.yaml
configs/research_layer_2_2/ndx/mechanism_parts.yaml
configs/research_layer_2_2/ndx/data_sources.yaml
configs/research_layer_2_2/ndx/variable_inventory.yaml
configs/research_layer_2_2/ndx/causal_roles.yaml
configs/research_layer_2_2/ndx/temporal_availability.yaml
configs/research_layer_2_2/ndx/core_dag.yaml
configs/research_layer_2_2/ndx/counter_dags.yaml
```

```text
schemas/research_seed_registry.v1.schema.json
schemas/research_mechanism_parts.v1.schema.json
schemas/research_variable_inventory.v1.schema.json
schemas/research_causal_roles.v1.schema.json
schemas/research_temporal_availability.v1.schema.json
schemas/core_dag.v1.schema.json
```

```text
src/sis/research/hypothesis/__init__.py
src/sis/research/hypothesis/contracts.py
src/sis/research/hypothesis/loader.py
src/sis/research/hypothesis/validator.py
src/sis/research/hypothesis/mechanisms.py
src/sis/research/hypothesis/variables.py
src/sis/research/hypothesis/causal_roles.py
src/sis/research/hypothesis/temporal.py
```

```text
src/sis/research/dag/__init__.py
src/sis/research/dag/contracts.py
src/sis/research/dag/loader.py
src/sis/research/dag/validator.py
src/sis/research/dag/errors.py
src/sis/research/dag/linter.py
src/sis/research/dag/rules.py
src/sis/research/dag/counter.py
src/sis/research/dag/data_requirements.py
src/sis/research/dag/export.py
src/sis/research/dag/report.py
```

```text
docs/research/ndx/00_SCOPE.md
docs/research/ndx/01_SEED_REGISTRY.md
docs/research/ndx/02_MECHANISM_PARTS.md
docs/research/ndx/03_DATA_SOURCE_CONTRACT.md
docs/research/ndx/04_VARIABLE_INVENTORY.md
docs/research/ndx/05_CAUSAL_ROLES.md
docs/research/ndx/06_TEMPORAL_AVAILABILITY.md
docs/research/ndx/07_CORE_DAG.md
docs/research/ndx/08_COUNTER_DAGS.md
```

```text
tests/research/test_seed_registry.py
tests/research/test_mechanism_parts.py
tests/research/test_data_source_contract.py
tests/research/test_variable_inventory.py
tests/research/test_causal_roles.py
tests/research/test_temporal_availability.py
tests/research/test_core_dag_contracts.py
tests/research/test_core_dag_loader.py
tests/research/test_core_dag_validator.py
tests/research/test_core_dag_linter.py
tests/research/test_core_dag_export.py
tests/research/test_counter_dags.py
tests/research/test_research_layer22_commands.py
```

## Edit

```text
src/sis/commands/research.py
  Phase B7で research-layer22-validate / research-layer22-export を追加する場合のみ編集。
```

```text
src/sis/cli.py
  通常は編集しない。既存の commands/research.py registration patternで足りない場合だけ最小編集。
```

```text
scripts/check_current_docs.py
  docs/research/ndx/ を current docs checker 対象にする判断をした場合のみ編集。
  対象にしないなら編集不要。
```

## Generated / Runtime

```text
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/counter_dags.md
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
```

## No Touch

```text
src/sis/backtest/
src/sis/paper/
src/sis/execution/
src/sis/venues/trade_xyz/
src/sis/bot/
src/sis/real_market/providers/
src/sis/research/strategy_lab/  # 今回は参照のみ。変更しない。
src/sis/research_protocol/      # 今回は参照のみ。変更しない。
pyproject.toml
uv.lock
.github/workflows/ci.yml
configs/fee_model.trade_xyz.yaml
configs/trade_xyz_data_collection.yaml
```

## Dependency policy

```text
依存追加なし。
既存 dependencies の範囲で実装する。
```
