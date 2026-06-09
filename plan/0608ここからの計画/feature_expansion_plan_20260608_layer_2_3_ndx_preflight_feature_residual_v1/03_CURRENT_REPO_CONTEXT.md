<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 03_CURRENT_REPO_CONTEXT

## 現Repo前提

現Repoでは、Layer 2.2 DAG foundation と manual review gate が実装済みである前提で進める。

確認済み構造:

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
  counter.py
  data_requirements.py
  exit_gate.py
  export.py
  freeze_manifest.py
  linter.py
  loader.py
  report.py
  review_contracts.py
  review_import.py
  review_pack.py
  validator.py

src/sis/research/hypothesis/
  data source / scope / seed / mechanism / role / temporal / variable contracts

tests/research/
  Layer 2.2 validation / linter / review / exit gate tests
```

## 現行CLI

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
```

## 既存境界

`research.dag` は DAG artifact、counter-DAG、temporal availability、manual review gate を扱うが、feature panel、residual calculation、backtest、paper/live orderは扱わない。Layer 2.3はこの境界の外に新しく `src/sis/research/ndx/` として作る。

## 既存Strategy Lab境界

Strategy Lab は以下の順で進むが、本PRではここに接続しない。

```text
StrategyExperimentSpec
  -> StrategySignalRecord
  -> EvaluationPlan
  -> TrialRecord / TrialLedger
  -> TradeCandidate
  -> PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview
  -> paper-from-intents
```

`data/research/strategy_signals.parquet` はStrategy Labの正本だが、本計画では生成しない。
