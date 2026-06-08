<!--
作成日: 2026-06-08_18:01 JST
更新日: 2026-06-08_18:01 JST
-->

# NDX Research Docs

この directory は NDX Layer 2.2 DAG foundation と manual review gate の current docs 入口である。正本は `configs/research_layer_2_2/ndx/`、`src/sis/research/dag/`、`schemas/`、`tests/research/`、CLI help。

## Current Read Order

1. `09_LLM_REVIEW_GATE.md`
2. `2_2_IMPLEMENTATION_BOUNDARY.md`
3. `LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md`
4. `DATA_SOURCE_CONTRACT.md`
5. `05_TEMPORAL_AVAILABILITY.md`
6. `COUNTER_DAGS.md`
7. `04_CAUSAL_ROLES.md`

## Commands

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
```

## Boundary

Layer 2.2 は local/manual review artifact harness である。external API、credentials、feature panel、residual calculation、neutralization、Strategy Lab export、backtest、paper/live order、Trade[XYZ] integration は別タスクとして扱う。
