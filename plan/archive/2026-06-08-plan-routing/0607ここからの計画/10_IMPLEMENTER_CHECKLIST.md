<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 10 Implementer Checklist

## 1. 実装前

```text
[ ] README.mdを読んだ
[ ] 01_GOAL.mdを読んだ
[ ] 02_SCOPE_AND_BOUNDARIES.mdを読んだ
[ ] 外部API禁止を理解した
[ ] paper/live禁止を理解した
[ ] Strategy Lab exportは今回対象外と理解した
```

## 2. ファイル作成

```text
[ ] docs/research/ndx/ を作った
[ ] configs/research_layer_2_2/ndx/ を作った
[ ] src/sis/research/hypothesis/ を作った
[ ] src/sis/research/dag/ を作った
[ ] tests/research/ を作った
[ ] schemas/ に必要なthin schemaを追加した
```

## 3. Contract実装

```text
[ ] Scope model
[ ] Seed model
[ ] MechanismPart model
[ ] VariableInventory model
[ ] CausalRole model
[ ] TemporalAvailability model
[ ] CoreDag model
[ ] CounterDag model
```

## 4. Loader / Validator

```text
[ ] YAML loader
[ ] duplicate id check
[ ] unknown reference check
[ ] role enum check
[ ] temporal layer check
[ ] self-loop check
[ ] duplicate edge check
```

## 5. Linter

```text
[ ] outcome -> treatment_candidate を拒否
[ ] t_after_close -> t_after_open を拒否
[ ] forbidden_edgesの違反を拒否
[ ] counter DAG不足をwarning
[ ] data requirement不足をwarning
```

## 6. Export

```text
[ ] core_dag.json
[ ] core_dag.mmd
[ ] counter_dags.md
[ ] data_requirements.yaml
[ ] ndx_core_dag_report.md
```

## 7. CLI

```text
[ ] research-dag-validate
[ ] research-dag-export
[ ] invalid configでexit code 2
[ ] valid configでexit code 0
```

## 8. Safety

```text
[ ] external APIを呼んでいない
[ ] credentialsを読んでいない
[ ] pyproject.tomlを変えていない
[ ] uv.lockを変えていない
[ ] src/sis/executionを変えていない
[ ] src/sis/paperを変えていない
[ ] src/sis/backtestを変えていない
[ ] src/sis/venues/trade_xyzを変えていない
[ ] data/research/strategy_signals.parquetを生成していない
[ ] PaperIntentPreviewを生成していない
```

## 9. Verification

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 10. PR Descriptionに書くこと

```text
Purpose:
  Layer 2.2 DAG Compiler foundation for HYP-NDX-001.

Changed:
  docs/config/schema/src/tests list.

Verification:
  commands run.

Not included:
  external API, Strategy Lab export, paper/live order, backtest, residual builder.

Stop conditions:
  none triggered.
```

## 11. 完了判断

```text
[ ] コーダーがこの資料だけでPRを切れる
[ ] Reviewerがこの資料だけでreviewできる
[ ] 2.2の前段contractが揃っている
[ ] Core DAGがvalidate/lint/exportできる
[ ] 2.3以降へ進まなくても完成扱いできる
```
