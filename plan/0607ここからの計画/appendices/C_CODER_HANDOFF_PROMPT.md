<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# Appendix C Coder Handoff Prompt

以下をそのままコーダーへ渡せる。

---

## 目的

`marketlens-strike` に Layer 2.2 DAG Compiler foundation を追加する。対象は NASDAQ / NDX 単独研究の `HYP-NDX-001 Open Gap Residual`。

## 重要境界

今回やるのは、2.2 DAG artifact基盤と、その前段の最小contractだけ。

やらない:

```text
external API
Bitget network
Trade[XYZ] readiness
backtest
Strategy Lab export
strategy_signals.parquet
PaperIntentPreview
paper/live order
wallet/signing/exchange write
```

## 実装対象

```text
docs/research/ndx/
configs/research_layer_2_2/ndx/
schemas/research_*.schema.json
schemas/core_dag.v1.schema.json
src/sis/research/hypothesis/
src/sis/research/dag/
tests/research/
src/sis/commands/research.py
```

## CLI

追加してよいCLI:

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
```

## Done

```text
- HYP-NDX-001 core_dag.yamlをvalidateできる
- forbidden edge linterがoutcome→treatmentとfuture→signalを拒否できる
- counter DAGが最低6つある
- core_dag.json / core_dag.mmd / data_requirements.yaml / reportを出せる
- tests/research がpass
- scripts/check_current_docs.py がpass
- ./scripts/check がpass
```

## Stop

次が必要なら止めて別タスク化。

```text
external API
new dependency
paper/live
Strategy Lab export
feature/residual builder
backtest
Trade[XYZ] readiness
```
