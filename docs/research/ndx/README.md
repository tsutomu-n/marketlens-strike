<!--
作成日: 2026-06-08_18:01 JST
更新日: 2026-06-10_15:55 JST
-->

# NDX Research Docs

この directory は NDX Layer 2.2 DAG foundation、Layer 2.3 preflight / feature panel / residual、Layer 2.4 residual validation gate、Layer 2.5 Strategy Lab research-only export の current docs 入口である。正本は `configs/research_layer_2_2/ndx/`、`configs/research_layer_2_3/ndx/`、`configs/research_layer_2_4/ndx/`、`src/sis/research/dag/`、`src/sis/research/ndx/`、`schemas/`、`tests/research/`、CLI help。

## Current Read Order

1. `09_LLM_REVIEW_GATE.md`
2. `10_LAYER_2_3_NDX_PREFLIGHT.md`
3. `11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md`
4. `12_LAYER_2_5_STRATEGY_LAB_RESEARCH_EXPORT.md`
5. `2_2_IMPLEMENTATION_BOUNDARY.md`
6. `LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md`
7. `DATA_SOURCE_CONTRACT.md`
8. `05_TEMPORAL_AVAILABILITY.md`
9. `COUNTER_DAGS.md`
10. `04_CAUSAL_ROLES.md`

## Commands

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-feature-panel --root configs/research_layer_2_2/ndx --input-root tests/fixtures/ndx --out data/research/ndx
uv run sis research-ndx-residual --feature-panel data/research/ndx/ndx_feature_panel.parquet --out data/research/ndx
uv run sis research-ndx-diagnostics --residuals data/research/ndx/open_gap_residuals.parquet --out data/reports
uv run sis research-ndx-residual-validate --root configs/research_layer_2_2/ndx --artifact-dir data/research/ndx --reports-dir data/reports --out data/research/ndx
uv run sis research-ndx-strategy-lab-export --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
```

## Boundary

Layer 2.2 は local/manual review artifact harness である。external API、credentials、feature panel、residual calculation、neutralization、Strategy Lab export、backtest、paper/live order、Trade[XYZ] integration には接続しない。

Layer 2.3 は `APPROVE_2_3`、freeze manifest、`second_review_required=false`、未解決 human decision なしを前提に、fixture-first data source resolution、feature panel、open-gap residual、diagnostics / neutralization pre-report、counter-DAG refutation skeleton を作る local research gate である。

Layer 2.4 は Layer 2.3 artifact の lineage、timestamp、neutralization、counter-DAG refutation を検査し、将来の Strategy Lab research-only export へ進めるかを判定する gate である。現在の default fixture sample は小さいため、期待される実artifact判断は `REVISE_2_3` with `INSUFFICIENT_VALIDATION_ERAS` and `INSUFFICIENT_VALIDATION_SAMPLE` であり、`APPROVE_STRATEGY_LAB_EXPORT` ではない。

Layer 2.5 は Layer 2.4 の `APPROVE_STRATEGY_LAB_EXPORT` と `permits_strategy_lab_research_only_export=true` を前提に、Strategy Lab research-only signal artifact を書く export bridge である。既存 `strategy_signals.parquet` / `strategy_signal_manifest.json` がある場合は、`--replace-existing` がない限り上書きしない。Layer 2.5 も backtest、paper candidate、`PaperIntentPreview`、paper/live order、external API、credentials、dependency追加、NQ / VXN / SOX direct / options / gamma input を扱わない。
