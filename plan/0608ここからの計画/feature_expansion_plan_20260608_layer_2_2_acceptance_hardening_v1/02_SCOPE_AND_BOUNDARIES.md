<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 02_SCOPE_AND_BOUNDARIES

## 対象

```text
Layer:
  2.2 acceptance / exit gate hardening

Target DAG:
  HYP-NDX-001

Target repo surface:
  configs/research_layer_2_2/ndx/
  src/sis/research/dag/
  src/sis/research/hypothesis/
  schemas/layer_2_2_*.schema.json
  schemas/llm_dag_review.v1.schema.json
  tests/research/
  docs/research/ndx/
```

## 非対象

```text
Layer 2.3以降:
  feature panel
  Open Gap Residual builder
  expected gap model
  neutralization
  counter-DAG refutation with real data

Strategy Lab:
  strategy_signals.parquet
  EvaluationPlan
  TrialLedger
  PaperCandidatePack

Execution:
  paper/live/order path
  Trade[XYZ] order path
  Bitget demo network
  wallet / signing / exchange write
```

## 外部API / credentials方針

```text
external_api: 禁止
credentials: 禁止
provider SDK: 追加禁止
pyproject.toml / uv.lock: 原則変更禁止
CI変更: 禁止
```

## 旧ZIPの扱い

```text
feature_expansion_plan_20260607_layer_2_2_v2.zip:
  historical design background / checklist

feature_expansion_plan_20260608_layer_2_2_exit_gate_v5_final.zip:
  historical design background / checklist

どちらも、現Repoに対する新規実装指示として読まない。
```
